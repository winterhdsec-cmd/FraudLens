# -*- coding: utf-8 -*-
"""HITL 复核流程验证（分派 → 出意见 → 完成复核 + 状态门控）。

为什么单独测：库里 review_tasks 曾**全部停在 pending**，说明 assign/resolve
这两步从来没被走过 —— 没走过的状态机最容易带病（同止付冻结流程的教训）。
实测确实发现：已完成的复核可被重新分派、且后一次结论会**静默覆盖**前一次。

覆盖：
  R1  列表/详情可用，能查到新建任务
  R2  分派 pending → assigned，受理人落库
  R3  出意见后状态 pending → in_review
  R4  resolve 缺 review_result → 400（不是 500）
  R5  resolve 成功 → resolved，且完成时追加一条结论意见（共 2 条）
  R6  **反向断言**：已 resolved 的任务不得再 assign（原为 200，会留下
      「已分派却已有结论」的矛盾状态）
  R7  **反向断言**：已 resolved 的任务不得再 resolve（原为 200，会静默覆盖原结论）
  R8  未知 review_id → 404（不是 5xx）
  R9  未认证访问被拒
"""
import os
import sys
import uuid

os.environ.setdefault("JWT_SECRET_KEY", "verify-script-only-not-a-real-secret")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv  # noqa: E402

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_ROOT, ".env"))
load_dotenv(os.path.join(_ROOT, "backend", "key.env"))

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text as T  # noqa: E402

import main  # noqa: E402
from database import db  # noqa: E402
from database.models import Case  # noqa: E402
from database.workflow_models import ReviewTask, ReviewOpinion  # noqa: E402
from routes.deps import get_current_user  # noqa: E402

PASS, FAIL = [], []


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))


def fresh_task(review_id):
    """用**独立连接**读取任务状态。

    为什么不直接用 db.session：它是 thread-local 的，TestClient 在另一个线程里
    跑 ASGI 应用并提交事务；主线程这条 session 可能仍持有旧快照，导致读到的
    是"提交前"的状态（本轮实测：resolve 已成功但读出来还是 assigned）。
    独立连接读的是当前真实落库状态，与断言意图一致。
    """
    with db.engine.connect() as conn:
        return conn.execute(T(
            "SELECT status, review_result, resolved_at, assigned_to_name "
            "FROM review_tasks WHERE review_id=:r"), {"r": review_id}).fetchone()


def fresh_count(sql, params):
    with db.engine.connect() as conn:
        return conn.execute(T(sql), params).scalar()


ADMIN = {"id": 1, "username": "verify_admin", "role": "admin", "department": "反诈中心"}
db.init_app()
main.app.dependency_overrides[get_current_user] = lambda: ADMIN
client = TestClient(main.app)

print("=" * 74)
print("HITL 复核流程验证")
print("=" * 74)

case = db.session.query(Case).first()
db.session.rollback()
rid = None
try:
    if not case:
        check("存在可测案件", False, "库中无案件")
    else:
        rid = "REV_VERIFY_%s" % uuid.uuid4().hex[:8]
        db.session.add(ReviewTask(review_id=rid, case_id=case.case_id, gang_id="",
                                  confidence=0.62, original_gate_decision="待人工复核",
                                  review_snapshot={"verify": True}, status="pending"))
        db.session.commit()
        print(f"\n测试任务 {rid}（案件 {case.case_id}）")

        def status_of():
            row = fresh_task(rid)
            return row[0] if row else "?"

        print("\n[R1] 列表 / 详情")
        r = client.get("/api/workflow/reviews")
        ids = [x["review_id"] for x in (r.json().get("reviews") or [])]
        check("列表 HTTP 200", r.status_code == 200, f"{r.status_code}")
        check("列表中能查到新任务", rid in ids)
        r = client.get(f"/api/workflow/reviews/{rid}")
        check("详情 HTTP 200", r.status_code == 200, f"{r.status_code}")
        d = r.json().get("review") or r.json()
        for k in ("review_id", "case_id", "status", "confidence", "opinions"):
            if k not in d:
                check(f"详情含字段 {k}", False, f"实际键 {sorted(d.keys())}")
                break
        else:
            check("详情含前端所读字段", True)

        print("\n[R2] 分派")
        r = client.post(f"/api/workflow/reviews/{rid}/assign",
                        json={"assigned_to_id": 1, "assigned_to_name": "张三",
                              "assigned_department": "反诈中心"})
        check("分派 HTTP 200", r.status_code == 200, f"{r.status_code}")
        row = fresh_task(rid)
        check("状态变为 assigned", row[0] == "assigned", f"实际 {row[0]}")
        check("受理人落库", row[3] == "张三", f"实际 {row[3]!r}")
        with db.engine.connect() as _c:
            _aa = _c.execute(T("SELECT assigned_at FROM review_tasks WHERE review_id=:r"),
                             {"r": rid}).scalar()
        check("assigned_at 已写", _aa is not None)

        print("\n[R3] 添加复核意见")
        r = client.post(f"/api/workflow/reviews/{rid}/opinions",
                        json={"opinion_type": "confirm", "comment": "验证意见"})
        check("出意见 HTTP 200", r.status_code == 200, f"{r.status_code}")
        # 已分派（assigned）再出意见：按现状保持 assigned —— 前端筛选页签只提供
        # 待分派/已分派/已完成三档，并不使用 in_review，故此处记录而非要求推进。
        check("已 assigned 的任务出意见后仍为 assigned",
              status_of() == "assigned", f"实际 {status_of()}")

        print("\n[R3b] pending 任务出意见应推进为 in_review")
        rid_p = "REV_VERIFY_P_%s" % uuid.uuid4().hex[:6]
        db.session.add(ReviewTask(review_id=rid_p, case_id=case.case_id, gang_id="",
                                  confidence=0.5, original_gate_decision="待人工复核",
                                  review_snapshot={}, status="pending"))
        db.session.commit()
        try:
            r = client.post(f"/api/workflow/reviews/{rid_p}/opinions",
                            json={"opinion_type": "comment", "comment": "未分派先出意见"})
            check("出意见 HTTP 200", r.status_code == 200, f"{r.status_code}")
            row_p = fresh_task(rid_p)
            check("状态由 pending 推进为 in_review",
                  row_p and row_p[0] == "in_review", f"实际 {row_p[0] if row_p else '?'}")
        finally:
            with db.engine.begin() as conn:
                conn.execute(T("DELETE FROM review_opinions WHERE review_id=:r"), {"r": rid_p})
                conn.execute(T("DELETE FROM review_tasks WHERE review_id=:r"), {"r": rid_p})

        print("\n[R4] 缺 review_result 应 400（不是 500）")
        r = client.post(f"/api/workflow/reviews/{rid}/resolve", json={"comment": "x"})
        check("HTTP 400", r.status_code == 400, f"实际 {r.status_code}（500 即异常被吞）")

        print("\n[R5] 完成复核")
        r = client.post(f"/api/workflow/reviews/{rid}/resolve",
                        json={"review_result": "confirmed_merge", "comment": "确认并案",
                              "trigger_reanalysis": False})
        check("resolve HTTP 200", r.status_code == 200, f"{r.status_code}")
        row = fresh_task(rid)
        check("状态变为 resolved", row[0] == "resolved", f"实际 {row[0]}")
        check("review_result 落库", row[1] == "confirmed_merge", f"实际 {row[1]!r}")
        check("resolved_at 已写", row[2] is not None)
        n_op = fresh_count("SELECT COUNT(*) FROM review_opinions WHERE review_id=:r", {"r": rid})
        check("意见共 2 条（1 人工 + 1 完成时追加）", n_op == 2, f"实际 {n_op}")

        print("\n[R6] 反向断言：已完成的复核不得再分派")
        r = client.post(f"/api/workflow/reviews/{rid}/assign",
                        json={"assigned_to_name": "李四"})
        check("HTTP 400（原为 200，会留下「已分派却已有结论」的矛盾状态）",
              r.status_code == 400, f"实际 {r.status_code}")
        row = fresh_task(rid)
        check("状态未被改回 assigned", row[0] == "resolved", f"实际 {row[0]}")
        check("受理人未被改写", row[3] == "张三", f"实际 {row[3]!r}")

        print("\n[R7] 反向断言：已完成的复核不得再定论（防结论被覆盖）")
        r = client.post(f"/api/workflow/reviews/{rid}/resolve",
                        json={"review_result": "split_gang"})
        check("HTTP 400（原为 200，会静默覆盖原结论）",
              r.status_code == 400, f"实际 {r.status_code}")
        row = fresh_task(rid)
        check("原结论未被覆盖", row[1] == "confirmed_merge", f"实际 {row[1]!r}")

        print("\n[R8] 未知 review_id")
        r = client.post("/api/workflow/reviews/REV_NO_SUCH_VERIFY/assign", json={})
        check("assign 未知 id → 404", r.status_code == 404, f"实际 {r.status_code}")
        r = client.post("/api/workflow/reviews/REV_NO_SUCH_VERIFY/resolve",
                        json={"review_result": "split_gang"})
        check("resolve 未知 id → 404", r.status_code == 404, f"实际 {r.status_code}")
        r = client.get("/api/workflow/reviews/REV_NO_SUCH_VERIFY")
        check("detail 未知 id 不 5xx", r.status_code < 500, f"实际 {r.status_code}")

    print("\n[R9] 鉴权")
    main.app.dependency_overrides.pop(get_current_user, None)
    anon = TestClient(main.app)
    r = anon.get("/api/workflow/reviews")
    check("未带 token 被拒（401/403）", r.status_code in (401, 403), f"实际 {r.status_code}")

finally:
    main.app.dependency_overrides.pop(get_current_user, None)
    db.session.rollback()
    if rid:
        with db.engine.begin() as conn:
            conn.execute(T("DELETE FROM review_opinions WHERE review_id=:r"), {"r": rid})
            conn.execute(T("DELETE FROM review_tasks WHERE review_id=:r"), {"r": rid})
        left = fresh_count("SELECT COUNT(*) FROM review_tasks WHERE review_id=:r", {"r": rid})
        print(f"\n  [清理] 测试任务残留 {left} 条（应为 0）")

print("\n" + "=" * 74)
print(f"结果：{len(PASS)} 通过 / {len(FAIL)} 失败")
if FAIL:
    print("失败项：")
    for f in FAIL:
        print("  -", f)
    sys.exit(1)
print("全部通过 ✓")
sys.exit(0)
