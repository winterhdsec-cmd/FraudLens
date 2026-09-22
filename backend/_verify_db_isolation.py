"""数据库隔离级别与事务卫生回归（防「启动即锁库」与「读到陈旧数据」复发）。

背景 —— 2026-09-22 演示前自检实测出的两个真实缺陷，同源（thread-local session
被复用、事务从不结束）：

  ① **启动即埋雷（最严重）**：`main.py` 启动时在 daemon 后台线程里跑数据初始化，
     其中 `database/seed.py::_do_alert_data()` 的 `.delete()` 即使在 0 行命中时
     InnoDB 也会留下表级意向锁，紧接着 `if count > 0: return` **不结束事务**；
     该线程跑完即闲置 → `alert_records` 被**永久持锁** → 之后任何写该表的请求
     都 Lock wait timeout（默认 50s）→ 500。
     实测：后端起来后立刻试写该表，3 秒超时被卡死；停服后挂起事务归零。

  ② **读到陈旧数据**：MySQL 默认 REPEATABLE READ，事务一开始后续查询都读同一快照；
     而 session 被同一工作线程复用 → 别的请求刚 INSERT 并提交的预警，
     `GET /api/alerts` **看不到**（实测写入前 87 条、写后仍 87 条）。

本脚本把这两点钉成长期护栏：
  I1 engine 的隔离级别是 READ COMMITTED（否则①的快照刷新与②都会复发）
  I2 跨连接可见性：A 连接写入并提交后，B 连接**立刻**能读到
  I3 事务卫生：一个"写了又回滚"的连接不会把表锁住，另一个连接仍能立即写入
  I4 启动后的 `alert_records` 上没有长期挂起的持锁事务（直接查 information_schema）
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv  # noqa: E402

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# 只加载 key.env —— 与 main.py 一致（不加载根目录 .env，避免造出与生产不一致的环境）
load_dotenv(os.path.join(_ROOT, 'backend', 'key.env'))

from sqlalchemy import text as T  # noqa: E402

from database import db  # noqa: E402

db.init_app()

PASS, FAIL = [], []


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))


def main():
    probe_id = None

    print("\n[I1] engine 隔离级别必须为 READ COMMITTED")
    db.session.remove()
    with db.engine.connect() as conn:
        lvl = conn.execute(T("SELECT @@transaction_isolation")).scalar()
    # MySQL 返回的是连字符写法（READ-COMMITTED），归一化后再比
    norm = str(lvl or "").upper().replace("-", " ").replace("_", " ").strip()
    check("隔离级别 = READ COMMITTED", norm == "READ COMMITTED",
          f"实际 {lvl}（REPEATABLE READ 会导致读到陈旧快照）")

    print("\n[I2] 跨连接可见性：A 写入并提交 → B 立刻能读到")
    with db.engine.begin() as conn:
        conn.execute(T(
            "INSERT INTO alert_records (alert_type, case_id, matched_case_id, matched_entities,"
            " confidence, resolved, created_at) VALUES"
            " ('ISOLATION_PROBE', 'CASE_A', 'CASE_B', '[]', 0.61, 0, NOW())"))
        probe_id = conn.execute(T("SELECT LAST_INSERT_ID()")).scalar()

    db.session.remove()
    with db.engine.connect() as conn:
        seen = conn.execute(T(
            "SELECT COUNT(*) FROM alert_records WHERE id = :i"), {"i": probe_id}).scalar()
    check("新写入的记录立即可见", seen == 1,
          f"查到 {seen} 条（0 表示被旧快照挡住）")

    print("\n[I3] 事务卫生：写了又回滚的连接不得锁住该表")
    # 模拟 _do_alert_data 的现场：写一句但不提交，然后回滚；另一连接应能立刻写
    before_trx = None
    with db.engine.connect() as conn:
        trans = conn.begin()
        conn.execute(T(
            "INSERT INTO alert_records (alert_type, case_id, matched_case_id, matched_entities,"
            " confidence, resolved, created_at) VALUES"
            " ('TX_PROBE', 'CASE_C', 'CASE_D', '[]', 0.5, 0, NOW())"))
        trans.rollback()

    t0 = time.perf_counter()
    locked = False
    try:
        with db.engine.begin() as conn:
            conn.execute(T("SET innodb_lock_wait_timeout = 3"))
            conn.execute(T(
                "INSERT INTO alert_records (alert_type, case_id, matched_case_id, matched_entities,"
                " confidence, resolved, created_at) VALUES"
                " ('TX_PROBE2', 'CASE_E', 'CASE_F', '[]', 0.5, 0, NOW())"))
    except Exception as e:  # noqa: BLE001
        locked = True
        print(f"      异常: {type(e).__name__}: {str(e)[:80]}")
    elapsed = (time.perf_counter() - t0) * 1000
    check("回滚后该表可立即写入（未被锁住）", not locked, f"耗时 {elapsed:.0f}ms")

    print("\n[I4] 不能有**长时间持锁**的事务（空闲只读事务不算问题）")
    # 判据必须同时满足「活得久」+「真的持有锁」。
    # 实测：READ COMMITTED 下的空闲只读事务 trx_rows_locked=0 且
    # performance_schema.data_locks 为空（不持锁、快照逐语句刷新），只占一个池连接，
    # 属正常现象；真正致命的是「持锁且长期不结束」——那会把后续写操作卡到 lock wait timeout。
    with db.engine.connect() as conn:
        locked = conn.execute(T("""
            SELECT t.trx_mysql_thread_id, TIMESTAMPDIFF(SECOND, t.trx_started, NOW()) AS secs,
                   l.OBJECT_NAME, l.LOCK_MODE
            FROM information_schema.innodb_trx t
            JOIN performance_schema.data_locks l
              ON l.ENGINE_TRANSACTION_ID = t.trx_id
            WHERE TIMESTAMPDIFF(SECOND, t.trx_started, NOW()) > 30
        """)).fetchall()
    check("无超过 30 秒的持锁事务", not locked,
          f"发现 {[(r[0], r[1], r[2], r[3]) for r in locked]}" if locked else "")

    with db.engine.connect() as conn:
        idle = conn.execute(T("""
            SELECT COUNT(*) FROM information_schema.innodb_trx
            WHERE TIMESTAMPDIFF(SECOND, trx_started, NOW()) > 30
        """)).scalar()
    print(f"      （附注：另有 {idle} 个空闲只读事务，READ COMMITTED 下不持锁、无害）")

    # ---------------- 清理 ----------------
    db.session.remove()
    with db.engine.begin() as conn:
        n = conn.execute(T(
            "DELETE FROM alert_records WHERE alert_type IN"
            " ('ISOLATION_PROBE','TX_PROBE','TX_PROBE2','VISIBILITY_PROBE','TRX_PROBE')")).rowcount
        _ = n
    db.session.remove()
    with db.engine.connect() as conn:
        left = conn.execute(T(
            "SELECT COUNT(*) FROM alert_records WHERE alert_type IN"
            " ('ISOLATION_PROBE','TX_PROBE','TX_PROBE2','VISIBILITY_PROBE','TRX_PROBE')")).scalar()
    print(f"\n  [清理] 探针记录残留 {left} 条（应为 0）")

    print("\n" + "=" * 62)
    if FAIL:
        print(f"结果：{len(PASS)} 通过 / {len(FAIL)} 失败")
        for f in FAIL:
            print(f"   ✗ {f}")
        return 1
    print(f"结果：{len(PASS)}/{len(PASS)} 全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
