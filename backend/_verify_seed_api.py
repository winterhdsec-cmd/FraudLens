"""G4 数据饱满化 - API 层验证

验证填充后的数据能通过真实 HTTP 接口返回给前端。
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
os.environ.setdefault("JWT_SECRET_KEY", "g4-verify-script-secret")

from fastapi import FastAPI
from fastapi.testclient import TestClient

PASS, FAIL = [], []


def check(name, cond, extra=""):
    (PASS if cond else FAIL).append(name)
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}{(' — ' + extra) if extra else ''}")


def main():
    print("=" * 68)
    print("G4 数据饱满化 · API 层验证")
    print("=" * 68)

    from dotenv import load_dotenv
        # 只加载 key.env，与 main.py 一致（不加载根目录 .env，避免造出与生产不一致的环境）
    load_dotenv("key.env")
    from database import init_db
    init_db()

    from routes.cases import router as cases_router
    from routes.gangs import router as gangs_router
    from routes.workflow import router as workflow_router
    from routes.deps import get_current_user

    app = FastAPI()
    app.include_router(cases_router)
    app.include_router(gangs_router)
    app.include_router(workflow_router)
    app.dependency_overrides[get_current_user] = lambda: {
        "id": 1, "user_id": 1, "username": "admin",
        "role": "admin", "department": "反诈中心",
    }
    c = TestClient(app)

    # --- 1. 案件详情带证据 ---
    print("\n[1] 案件详情 /api/cases/{id} 返回 evidence")
    r = c.get("/api/cases/FC20260522001")
    check("HTTP 200", r.status_code == 200, f"实际 {r.status_code}")
    if r.status_code == 200:
        case = r.json().get("case", {})
        ev = case.get("evidence") or []
        check("evidence 非空", len(ev) > 0, f"实际 {len(ev)}")
        check("含 icon/name/meta 展示字段",
              all(k in ev[0] for k in ("icon", "name", "meta")) if ev else False,
              str(ev[0].keys()) if ev else "空")
    else:
        check("evidence 非空", False, "请求失败")

    # --- 2. 团伙接口（person/account/phone 已填充） ---
    print("\n[2] 团伙列表 /api/gangs")
    r2 = c.get("/api/gangs")
    check("HTTP 200", r2.status_code == 200, f"实际 {r2.status_code}")
    if r2.status_code == 200:
        data = r2.json()
        gangs = data.get("gangs") or data.get("list") or []
        check("团伙列表非空", len(gangs) > 0, f"实际 {len(gangs)}")

    # --- 3. 冻结单回执 ---
    print("\n[3] 冻结回执 /api/workflow/freeze-orders/{id}/receipts")
    r3 = c.get("/api/workflow/freeze-orders")
    check("冻结单列表 HTTP 200", r3.status_code == 200, f"实际 {r3.status_code}")
    orders = []
    if r3.status_code == 200:
        body = r3.json()
        orders = body.get("orders") or body.get("items") or body.get("data") or []
        check("冻结单非空", len(orders) > 0, f"实际 {len(orders)}")
    if orders:
        oid = orders[0].get("order_id")
        r4 = c.get(f"/api/workflow/freeze-orders/{oid}/receipts")
        check("回执接口 HTTP 200", r4.status_code == 200, f"实际 {r4.status_code}")
        if r4.status_code == 200:
            rb = r4.json()
            recs = rb.get("receipts") or rb.get("data") or []
            check("回执非空", len(recs) > 0, f"实际 {len(recs)}")
            if recs:
                tgt = str(recs[0].get("target_account", ""))
                check("回执账号已脱敏", "*" in tgt, tgt)

    # --- 4. 复核任务 + 意见 ---
    print("\n[4] 复核 /api/workflow/reviews")
    r5 = c.get("/api/workflow/reviews")
    check("复核列表 HTTP 200", r5.status_code == 200, f"实际 {r5.status_code}")
    revs = []
    if r5.status_code == 200:
        b = r5.json()
        revs = b.get("reviews") or b.get("items") or b.get("data") or []
        check("复核任务非空", len(revs) > 0, f"实际 {len(revs)}")
    if revs:
        rid = revs[0].get("review_id")
        r6 = c.get(f"/api/workflow/reviews/{rid}")
        check("复核详情 HTTP 200", r6.status_code == 200, f"实际 {r6.status_code}")
        if r6.status_code == 200:
            detail = r6.json()
            task = detail.get("review") or detail.get("data") or detail
            ops = task.get("opinions") or []
            check("复核意见非空", len(ops) > 0, f"实际 {len(ops)}")

    # --- 5. 审批链 ---
    print("\n[5] 审批 /api/workflow/approvals")
    r7 = c.get("/api/workflow/approvals")
    check("审批列表 HTTP 200", r7.status_code == 200, f"实际 {r7.status_code}")

    # --- 6. 案件统计仍正常 ---
    print("\n[6] 回归：案件列表与统计")
    r8 = c.get("/api/cases?page=1&page_size=5")
    check("案件列表 HTTP 200", r8.status_code == 200, f"实际 {r8.status_code}")
    if r8.status_code == 200:
        b = r8.json()
        items = b.get("cases") or b.get("items") or []
        check("案件列表非空", len(items) > 0, f"实际 {len(items)}")
    r9 = c.get("/api/cases/stats")
    check("统计接口 HTTP 200", r9.status_code == 200, f"实际 {r9.status_code}")

    print("\n" + "=" * 68)
    print(f"结果: {len(PASS)} 通过 / {len(FAIL)} 失败")
    for f in FAIL:
        print(f"  - {f}")
    print("=" * 68)
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
