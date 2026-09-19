"""止付冻结执行器 · 字段名兼容与状态推导回归测试。

守护一个真实发生过的缺陷：
`MockFreezeExecutor.execute()` 曾按 `t.get("account")` / `t.get("bank")` 取值，
而前端与创建接口写的是 `account_number` / `bank_name` →
`if not account: continue` 把**每个账户都跳过** → 返回 0 条回执 →
工单状态恒为 `failed`。三张线上工单全都卡在 failed，止付冻结主线从未产出回执。
可怕之处：它不报错、不抛异常，只是"静默什么都不做"，肉眼极难发现。

覆盖：
  E1  前端真实字段名（account_number/bank_name/account_name）能正确出回执
  E2  早期字段名（account/bank/holder）仍兼容
  E3  纯字符串形式的 target_accounts 兼容
  E4  单个 dict（非列表）兼容
  E5  无有效账号时返回空列表（而非抛异常）
  E6  每个账户一条回执，账号/开户行/户名正确落到回执
  E7  冻结期限约 6 个月（法定冻结期限）
  E8  状态推导口径：全 success → executed；含 pending → partial；全 failed → failed
  E9  端到端：创建 → 提交审批 → 批准 → 状态 executed 且回执数 == 账户数
  E10 端到端回归护栏：新工单执行后不得出现"回执为 0"（正是历史缺陷的表现）
"""
import os
import sys
from datetime import datetime, timedelta

os.environ.setdefault("JWT_SECRET_KEY", "verify-script-only-not-a-real-secret")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv  # noqa: E402

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_ROOT, ".env"))
load_dotenv(os.path.join(_ROOT, "backend", "key.env"))

from fastapi.testclient import TestClient  # noqa: E402

import main  # noqa: E402
from database import db  # noqa: E402
from database.models import Case  # noqa: E402
from database.workflow_models import FreezeOrder, FreezeReceipt  # noqa: E402
from routes.deps import get_current_user  # noqa: E402
from routes.workflow import _derive_freeze_status  # noqa: E402
from tools.freeze_executor import MockFreezeExecutor  # noqa: E402
from sqlalchemy import text as T  # noqa: E402

PASS, FAIL = [], []


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))


class FakeOrder:
    """最小工单替身：执行器只用到 order_id 与 target_accounts。"""
    def __init__(self, target_accounts):
        self.order_id = "FRZ_TEST_0001"
        self.target_accounts = target_accounts


class FakeReceipt:
    def __init__(self, status):
        self.execution_status = status


print("=" * 74)
print("止付冻结执行器 · 字段兼容与状态推导")
print("=" * 74)

ex = MockFreezeExecutor()

# ── E1 前端真实字段名 ──
print("\n[E1] 前端真实字段名 account_number / bank_name / account_name")
rs = ex.execute(FakeOrder([
    {"account_number": "6228480402564890018", "account_name": "张*明", "bank_name": "农业银行"},
    {"account_number": "6217001234567890123", "account_name": "李*华", "bank_name": "建设银行"},
]))
check("产出 2 条回执（而非 0 条）", len(rs) == 2, f"实际 {len(rs)} 条（0 条即历史缺陷复现）")
check("账号正确", rs[0].target_account == "6228480402564890018", rs[0].target_account)
check("开户行正确", rs[0].bank_name == "农业银行", rs[0].bank_name)
check("户名落到消息里", "张*明" in rs[0].execution_message, rs[0].execution_message[:50])
check("状态为 success", all(r.execution_status == "success" for r in rs))

# ── E2 早期字段名 ──
print("\n[E2] 早期字段名 account / bank / holder（向后兼容）")
rs2 = ex.execute(FakeOrder([{"account": "6222999999990001", "bank": "工商银行", "holder": "王*"}]))
check("产出 1 条回执", len(rs2) == 1, f"实际 {len(rs2)}")
if rs2:
    check("账号正确", rs2[0].target_account == "6222999999990001", rs2[0].target_account)
    check("开户行正确", rs2[0].bank_name == "工商银行", rs2[0].bank_name)

# ── E3 纯字符串 ──
print("\n[E3] target_accounts 为纯字符串列表")
rs3 = ex.execute(FakeOrder(["6222001111222233"]))
check("产出 1 条回执", len(rs3) == 1, f"实际 {len(rs3)}")
if rs3:
    check("账号正确", rs3[0].target_account == "6222001111222233")

# ── E4 单个 dict ──
print("\n[E4] target_accounts 为单个 dict（非列表）")
rs4 = ex.execute(FakeOrder({"account_number": "6222004444555566", "bank_name": "中国银行"}))
check("产出 1 条回执", len(rs4) == 1, f"实际 {len(rs4)}")

# ── E5 空/无有效账号 ──
print("\n[E5] 无有效账号")
check("空列表 → 空结果", ex.execute(FakeOrder([])) == [])
check("空 dict → 空结果", ex.execute(FakeOrder([{}])) == [])
check("None → 空结果", ex.execute(FakeOrder(None)) == [])
check("账号为空串被跳过", ex.execute(FakeOrder([{"account_number": "  "}])) == [])

# ── E7 冻结期限 ──
print("\n[E7] 冻结期限（法定 6 个月）")
if rs:
    days = (rs[0].freeze_until - datetime.utcnow()).days
    check("期限约 180 天", 175 <= days <= 185, f"{days} 天")

# ── E8 状态推导口径 ──
print("\n[E8] 状态推导口径（pending 不得算作 failed）")
check("全 success → executed", _derive_freeze_status([FakeReceipt("success")] * 2) == "executed")
check("success + failed → partial", _derive_freeze_status(
    [FakeReceipt("success"), FakeReceipt("failed")]) == "partial")
check("仅 pending → partial（历史误判为 failed）", _derive_freeze_status(
    [FakeReceipt("pending")]) == "partial")
check("全 failed → failed", _derive_freeze_status([FakeReceipt("failed")] * 2) == "failed")
check("空回执 → failed", _derive_freeze_status([]) == "failed")

# ── E11 审批门控：未审批的工单任何人都不得执行 ──
print("\n[E11] 审批门控（admin 也不得绕过审批执行冻结）")
db.init_app()
ADMIN = {"id": 1, "username": "verify_admin", "role": "admin", "department": ""}
main.app.dependency_overrides[get_current_user] = lambda: ADMIN
client = TestClient(main.app)
case = db.session.query(Case).first()
db.session.rollback()
gate_oid = None
flow2 = None
try:
    r = client.post("/api/workflow/freeze-orders", json={
        "case_id": case.case_id, "action_type": "冻结",
        "target_accounts": [{"account_number": "6222009999888877", "bank_name": "邮储银行"}],
        "legal_basis": "反诈法", "reason": "门控用例", "freeze_amount": 10000,
    })
    gate_oid = r.json()["order"]["order_id"]

    rg = client.post(f"/api/workflow/freeze-orders/{gate_oid}/execute")
    check("admin 执行 draft 工单被拒（400）", rg.status_code == 400,
          f"status={rg.status_code}（200 即审批绕过漏洞复现）")
    db.session.rollback()
    o = db.session.query(FreezeOrder).filter_by(order_id=gate_oid).first()
    check("draft 工单状态未被改动", o is not None and o.status == "draft",
          f"实际 {o.status if o else '?'}")
    check("未产生任何回执",
          db.session.query(FreezeReceipt).filter_by(order_id=gate_oid).count() == 0)

    r2 = client.post(f"/api/workflow/freeze-orders/{gate_oid}/submit", json={})
    flow2 = r2.json().get("flow_id")
    rg2 = client.post(f"/api/workflow/freeze-orders/{gate_oid}/execute")
    check("admin 执行 pending_approval 工单被拒（400）", rg2.status_code == 400,
          f"status={rg2.status_code}（200 即审批绕过漏洞复现）")
finally:
    db.session.rollback()
    if gate_oid:
        db.session.execute(T("DELETE FROM freeze_receipts WHERE order_id=:o"), {"o": gate_oid})
        if flow2:
            db.session.execute(T("DELETE FROM approval_nodes WHERE flow_id=:f"), {"f": flow2})
            db.session.execute(T("DELETE FROM approval_flows WHERE flow_id=:f"), {"f": flow2})
        db.session.execute(T("DELETE FROM freeze_orders WHERE order_id=:o"), {"o": gate_oid})
        db.session.commit()

# ── E9/E10 端到端 ──
print("\n[E9/E10] 端到端：创建 → 提交 → 批准 → executed 且有回执")
oid = flow = None
try:
    r = client.post("/api/workflow/freeze-orders", json={
        "case_id": case.case_id, "action_type": "冻结",
        "target_accounts": [
            {"account_number": "6228480402564890018", "account_name": "张*明", "bank_name": "农业银行"},
            {"account_number": "6217001234567890123", "account_name": "李*华", "bank_name": "建设银行"},
        ],
        "legal_basis": "反诈法", "reason": "执行器回归", "freeze_amount": 260000,
    })
    check("创建工单 HTTP 200", r.status_code == 200, f"status={r.status_code}")
    oid = r.json()["order"]["order_id"]

    r = client.post(f"/api/workflow/freeze-orders/{oid}/submit", json={})
    check("提交审批 HTTP 200", r.status_code == 200, f"status={r.status_code}")
    flow = r.json().get("flow_id")

    for _ in range(5):
        fl = client.get(f"/api/workflow/approvals/{flow}").json()
        fobj = fl.get("flow") or {}
        if fobj.get("status") == "approved":
            break
        rr = client.post(f"/api/workflow/approvals/{flow}/approve", json={"comment": "同意"})
        if rr.status_code != 200:
            break

    db.session.rollback()
    o = db.session.query(FreezeOrder).filter_by(order_id=oid).first()
    n_rec = db.session.query(FreezeReceipt).filter_by(order_id=oid).count()
    check("审批通过后状态为 executed", o is not None and o.status == "executed",
          f"实际 {o.status if o else '?'}（failed 即历史缺陷）")
    check("回执条数 == 账户数 (2)", n_rec == 2, f"实际 {n_rec}（0 即历史缺陷）")
    check("E10 回归护栏：回执不得为 0", n_rec > 0, "回执为 0 正是历史缺陷的表现")

    rc = client.get(f"/api/workflow/freeze-orders/{oid}/receipts").json().get("receipts", [])
    check("回执接口可读且开户行非空",
          len(rc) == 2 and all(x.get("bank_name") for x in rc),
          f"{[(x.get('bank_name'), x.get('execution_status')) for x in rc]}")

finally:
    main.app.dependency_overrides.pop(get_current_user, None)
    db.session.rollback()
    if oid:
        db.session.execute(T("DELETE FROM freeze_receipts WHERE order_id=:o"), {"o": oid})
        if flow:
            db.session.execute(T("DELETE FROM approval_nodes WHERE flow_id=:f"), {"f": flow})
            db.session.execute(T("DELETE FROM approval_flows WHERE flow_id=:f"), {"f": flow})
        db.session.execute(T("DELETE FROM freeze_orders WHERE order_id=:o"), {"o": oid})
        db.session.commit()
        left = db.session.query(FreezeOrder).filter_by(order_id=oid).count()
        print(f"\n  [清理] 测试工单残留 {left} 条（应为 0）")

print("\n" + "=" * 74)
print(f"结果：{len(PASS)} 通过 / {len(FAIL)} 失败")
if FAIL:
    print("失败项：")
    for f in FAIL:
        print("  -", f)
    sys.exit(1)
print("全部通过 ✓")
sys.exit(0)
