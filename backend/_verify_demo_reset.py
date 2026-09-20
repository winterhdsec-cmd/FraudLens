"""演示数据一键复位（POST /api/system/demo-reset）回归验证。

覆盖：
  R1 仅管理员可执行（analyst → 403）
  R2 缺确认串 → 400，且**数据未被改动**（先证明"没确认就动不了"）
  R3 管理员 + confirm=RESET → 200 且两步脚本都成功
  R4 复位结果与独立读库的行数一致（接口自报数字不能自证）
  R5 复位后数据干净：无「测试/E2E」残留、冻结工单状态自洽
  R6 审计留痕已写入（operation_logs 出现 demo_reset）
  R7 **幂等**：再复位一次，行数不变（"撤销键"必须可重复按）

读库一律用独立连接（subprocess 在别的进程提交，db.session 会读到旧快照）。
"""
import json
import os
import sys
import uuid

os.environ.setdefault('JWT_SECRET_KEY', 'test-secret')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv  # noqa: E402

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# 只加载 key.env —— 与 main.py 保持一致（main.py 只 load_dotenv('backend/key.env')）。
# 此前这里还加载了根目录 .env，而 python-dotenv 默认 override=False：**先加载者胜出**，
# 于是 .env 里的 REDIS_PASSWORD 等值会盖过 key.env，造出与生产不一致的配置环境
# （曾据此把「Redis 密码不一致 → 单次调用 10 秒」误判为线上缺陷；实际那是脚本特有环境，
#   真实启动实测 2ms。教训：验证脚本的配置加载方式必须与被测程序一致）。
load_dotenv(os.path.join(_ROOT, 'backend', 'key.env'))

import main  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text as T  # noqa: E402

from database import db  # noqa: E402
from routes.deps import get_current_user  # noqa: E402

db.init_app()

PASS, FAIL = [], []


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))


TABLES = ["persons", "accounts", "phones", "evidence_items",
          "freeze_approvals", "freeze_receipts", "imported_fund_flows",
          "merge_suggestions", "review_opinions"]


def read_counts(conn):
    return {t: conn.execute(T(f"SELECT COUNT(*) FROM `{t}`")).scalar() for t in TABLES}


def fresh_counts():
    """独立连接读取（新事务 → 能看到子进程刚提交的数据）。"""
    db.session.remove()
    with db.engine.connect() as conn:
        return read_counts(conn)


def main_test():
    client = TestClient(main.app)

    # 审计留痕的 user_id 有外键约束指向 users.id，测试必须用**真实存在**的账号，
    # 否则留痕会失败（用假 id 只能测到"留痕失败被兜住"，测不到"留痕成功"）
    db.session.remove()
    with db.engine.connect() as conn:
        row = conn.execute(T(
            "SELECT id, username FROM users WHERE role = 'admin' ORDER BY id LIMIT 1")).first()
    admin_id, admin_name = (row[0], row[1]) if row else (1, 'admin')
    print(f"\n[前置] 留痕用管理员：id={admin_id} username={admin_name}")

    def as_user(role, username="tester"):
        main.app.dependency_overrides[get_current_user] = lambda: {
            "id": admin_id, "username": admin_name if role == "admin" else username,
            "role": role, "department": "反诈中心"
        }
        return client

    print("\n[前置] 复位前的行数快照")
    before = fresh_counts()
    for t in TABLES:
        print(f"    {t:22s} {before[t]:>7d}")

    print("\n[R1] 非管理员不得复位")
    as_user("analyst")
    r = client.post("/api/system/demo-reset", json={"confirm": "RESET"})
    check("HTTP 403", r.status_code == 403, f"实际 {r.status_code}")

    print("\n[R2] 管理员但缺确认串 → 400，且数据必须原样")
    as_user("admin")
    r = client.post("/api/system/demo-reset", json={})
    check("HTTP 400（防误触）", r.status_code == 400, f"实际 {r.status_code}")
    r2 = client.post("/api/system/demo-reset", json={"confirm": "yes"})
    check("确认串内容不对也拒绝", r2.status_code == 400, f"实际 {r2.status_code}")
    after_bad = fresh_counts()
    check("被拒绝时数据零改动", after_bad == before,
          f"差异 {[t for t in TABLES if after_bad[t] != before[t]]}")

    print("\n[R3] 管理员 + confirm=RESET → 复位成功")
    r = client.post("/api/system/demo-reset", json={"confirm": "RESET"})
    check("HTTP 200", r.status_code == 200, f"实际 {r.status_code}")
    data = r.json() if r.status_code == 200 else {}
    check("success=True", data.get("success") is True, json.dumps(data)[:160])
    steps = data.get("steps") or []
    check("两步脚本都执行", len(steps) == 2, f"实际 {len(steps)} 步")
    check("两步都成功", all(s.get("ok") for s in steps),
          "; ".join(f"{s.get('script')}={s.get('ok')}" for s in steps))

    print("\n[R4] 复位结果与独立读库一致")
    after = fresh_counts()
    reported = data.get("counts") or {}
    for t in TABLES:
        print(f"    {t:22s} 实际 {after[t]:>6d}   接口自报 {reported.get(t, '-')}")
    check("9 张表均非空", all(after[t] > 0 for t in TABLES),
          f"空表 {[t for t in TABLES if after[t] == 0]}")
    mism = [t for t in TABLES if t in reported and reported[t] != after[t]]
    check("接口自报行数与实际一致", not mism, f"不一致 {mism}")
    # 复位前后行数应完全一致（固定种子 → 可复现）
    diff = [t for t in TABLES if before[t] != after[t]]
    check("复位前后行数一致（固定种子可复现）", not diff,
          f"变化 {[(t, before[t], after[t]) for t in diff]}")

    print("\n[R5] 复位后数据干净")
    db.session.remove()
    with db.engine.connect() as conn:
        bad_reason = conn.execute(T(
            "SELECT COUNT(*) FROM freeze_orders "
            "WHERE reason LIKE '%测试%' OR reason LIKE '%E2E%' OR reason LIKE '%e2e%'")).scalar()
        check("工单事由无「测试/E2E」", bad_reason == 0, f"违规 {bad_reason}")

        bad_comment = conn.execute(T(
            "SELECT COUNT(*) FROM approval_nodes "
            "WHERE comment LIKE '%测试%' OR comment LIKE '%E2E%'")).scalar()
        check("审批批语无「测试/E2E」", bad_comment == 0, f"违规 {bad_comment}")

        bad_opinion = conn.execute(T(
            "SELECT COUNT(*) FROM review_opinions "
            "WHERE comment LIKE '%测试%' OR comment LIKE '%E2E%'")).scalar()
        check("复核意见无「测试/E2E」", bad_opinion == 0, f"违规 {bad_opinion}")

        # 冻结工单状态与回执须自洽（终态不可逆，见 _verify_seed_consistency）
        # 冻结工单状态与回执须自洽（终态不可逆，同 _verify_seed_consistency 的 I15）
        # 注意列名是 execution_status，不是 status
        bad_state = conn.execute(T(
            "SELECT COUNT(*) FROM freeze_orders o "
            "WHERE o.status = 'failed' AND EXISTS ("
            "  SELECT 1 FROM freeze_receipts r "
            "  WHERE r.order_id = o.order_id "
            "    AND r.execution_status IN ('success','pending','processing'))")).scalar()
        check("failed 工单无 success/pending 回执", bad_state == 0, f"违规 {bad_state}")

    print("\n[R6] 审计留痕")
    db.session.remove()
    with db.engine.connect() as conn:
        n_log = conn.execute(T(
            "SELECT COUNT(*) FROM operation_logs WHERE action = 'demo_reset'")).scalar()
    check("operation_logs 已记录 demo_reset", n_log >= 1, f"记录数 {n_log}")

    print("\n[R7] 幂等：再按一次，行数不变")
    r = client.post("/api/system/demo-reset", json={"confirm": "RESET"})
    check("第二次 HTTP 200", r.status_code == 200, f"实际 {r.status_code}")
    again = fresh_counts()
    diff2 = [t for t in TABLES if after[t] != again[t]]
    check("行数与第一次完全相同", not diff2,
          f"变化 {[(t, after[t], again[t]) for t in diff2]}")

    print("\n" + "=" * 62)
    if FAIL:
        print(f"结果：{len(PASS)} 通过 / {len(FAIL)} 失败")
        for f in FAIL:
            print(f"   ✗ {f}")
        return 1
    print(f"结果：{len(PASS)}/{len(PASS)} 全部通过")
    return 0


if __name__ == "__main__":
    try:
        code = main_test()
    finally:
        main.app.dependency_overrides.pop(get_current_user, None)
    sys.exit(code)
