"""预警处置（POST /api/alerts/{id}/resolve）状态机回归验证。

为什么测它：这是第三处「状态机能被重复流转」的候选。前两处（止付冻结、HITL 复核）
都已修并加了护栏；预警处置此前**没有终态门控** —— 对已处置的预警再调一次，
`resolved_at` 会被静默覆盖成新时间，而它是处置留痕。

覆盖：
  R1 不存在的预警 → 404
  R2 首次处置 → 200，resolved=True、resolved_at 落库
  R3 **重复处置 → 400，且 resolved_at 不被覆盖**（核心断言）
  R4 已处置的预警不再出现在活跃列表（get_active_alerts 过滤 resolved）
  R5 未处置的预警仍在活跃列表里（反向断言，防"整个列表都空"的假通过）
  R6 处置不改变原始记录的其他字段（case_id / alert_type 不被改写）

读库一律用独立连接（TestClient 在另一线程提交事务，db.session 会读到旧快照）。
"""
import os
import sys

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


def main_test():
    client = TestClient(main.app)
    main.app.dependency_overrides[get_current_user] = lambda: {
        "id": 1, "username": "admin", "role": "admin", "department": "反诈中心"
    }

    db.session.remove()
    with db.engine.connect() as conn:
        case_id = conn.execute(T("SELECT case_id FROM cases LIMIT 1")).scalar()
        matched = conn.execute(T(
            "SELECT case_id FROM cases WHERE case_id <> :c LIMIT 1"), {"c": case_id}).scalar()
    if not case_id or not matched:
        print("!! 缺少样例案件，跳过")
        return 0

    alert_id = None

    print("\n[R0] 自建一条未处置预警")
    with db.engine.begin() as conn:
        conn.execute(T(
            "INSERT INTO alert_records (alert_type, case_id, matched_case_id, matched_entities,"
            " confidence, resolved, created_at) VALUES"
            " ('SHARED_PHONE', :c, :m, '[]', 0.77, 0, NOW())"), {"c": case_id, "m": matched})
        alert_id = conn.execute(T("SELECT LAST_INSERT_ID()")).scalar()
    check("测试预警已创建", bool(alert_id), f"id={alert_id}")

    try:
        print("\n[R5-pre] 未处置时应出现在活跃列表")
        r = client.get("/api/alerts")
        active_ids = [a.get('id') for a in (r.json().get('alerts') or [])]
        check("HTTP 200", r.status_code == 200, f"{r.status_code}")
        check("新建的预警在活跃列表中", alert_id in active_ids, f"列表共 {len(active_ids)} 条")

        print("\n[R1] 不存在的预警 → 404")
        r = client.post("/api/alerts/99999999/resolve")
        check("HTTP 404", r.status_code == 404, f"实际 {r.status_code}")

        print("\n[R2] 首次处置")
        r = client.post(f"/api/alerts/{alert_id}/resolve")
        check("HTTP 200", r.status_code == 200, f"实际 {r.status_code}")

        db.session.remove()
        with db.engine.connect() as conn:
            row = conn.execute(T(
                "SELECT resolved, resolved_at, case_id, alert_type FROM alert_records WHERE id=:i"),
                {"i": alert_id}).first()
        first_resolved_at = row[1]
        check("resolved 置为真", bool(row[0]), f"resolved={row[0]}")
        check("resolved_at 已写入", first_resolved_at is not None, f"{first_resolved_at}")

        print("\n[R3] 重复处置 → 400，且 resolved_at 不被覆盖（核心断言）")
        r = client.post(f"/api/alerts/{alert_id}/resolve")
        check("HTTP 400（原为 200 并静默覆盖处置时间）", r.status_code == 400, f"实际 {r.status_code}")
        check("返回体说明原因", "已处置" in str(r.json().get("error", "")),
              str(r.json().get("error"))[:60])

        db.session.remove()
        with db.engine.connect() as conn:
            again = conn.execute(T(
                "SELECT resolved_at FROM alert_records WHERE id=:i"), {"i": alert_id}).scalar()
        check("resolved_at 未被覆盖", again == first_resolved_at,
              f"首次 {first_resolved_at} / 现在 {again}")

        print("\n[R4] 已处置的预警不再出现在活跃列表")
        r = client.get("/api/alerts")
        active_ids = [a.get('id') for a in (r.json().get('alerts') or [])]
        check("已从活跃列表移除", alert_id not in active_ids, f"列表共 {len(active_ids)} 条")

        print("\n[R6] 处置不改写其他字段")
        db.session.remove()
        with db.engine.connect() as conn:
            now_row = conn.execute(T(
                "SELECT case_id, alert_type FROM alert_records WHERE id=:i"), {"i": alert_id}).first()
        check("case_id 未变", now_row[0] == row[2], f"{now_row[0]} vs {row[2]}")
        check("alert_type 未变", now_row[1] == row[3], f"{now_row[1]} vs {row[3]}")

    finally:
        if alert_id:
            db.session.remove()
            with db.engine.begin() as conn:
                conn.execute(T("DELETE FROM alert_records WHERE id=:i"), {"i": alert_id})
            db.session.remove()
            with db.engine.connect() as conn:
                left = conn.execute(T(
                    "SELECT COUNT(*) FROM alert_records WHERE id=:i"), {"i": alert_id}).scalar()
            print(f"\n  [清理] 测试预警残留 {left} 条（应为 0）")

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
