"""前端全部 GET 接口巡检测试。

从 `frontend/src` 抽出的真实调用清单里，挑出**只读 GET** 端点，
用库中真实主键逐个请求，报告 4xx/5xx 与非预期响应结构。

设计取舍：
  - 只测 GET（幂等、无副作用），POST/PUT/DELETE 会改数据，不在此巡检范围。
  - 需要真实 ID 的路径从数据库取实际值填充，而非硬编码，避免"测了个不存在的 ID"。
  - 401/403 视为"路由存在且鉴权生效"，但会单列，便于区分"未实现"与"已保护"。
"""
import os
import re
import sys

os.environ.setdefault("JWT_SECRET_KEY", "verify-script-only-not-a-real-secret")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv  # noqa: E402

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_ROOT, ".env"))
load_dotenv(os.path.join(_ROOT, "backend", "key.env"))

from fastapi.testclient import TestClient  # noqa: E402

import main  # noqa: E402
from database import db  # noqa: E402
from database.models import (  # noqa: E402
    Case, Gang, AnalysisSession, MergeSuggestion,
)
from routes.deps import get_current_user  # noqa: E402

FAKE_USER = {"id": 1, "username": "smoke_admin", "role": "admin"}

OK, BAD, PROTECTED = [], [], []


def hit(client, method, path, note=""):
    try:
        r = client.get(path, timeout=60)
    except Exception as e:  # noqa: BLE001
        BAD.append((path, "EXC", str(e)[:90], note))
        print(f"  [EXC ] {path} — {str(e)[:80]}")
        return None
    if r.status_code in (401, 403):
        PROTECTED.append((path, r.status_code))
        print(f"  [AUTH] {path} — {r.status_code}")
    elif r.status_code >= 400:
        BAD.append((path, r.status_code, r.text[:110].replace("\n", " "), note))
        print(f"  [FAIL] {path} — {r.status_code} {r.text[:90]}")
    else:
        OK.append(path)
        return r.json() if "json" in r.headers.get("content-type", "") else None
    return None


db.init_app()

print("=" * 76)
print("前端 GET 接口巡检")
print("=" * 76)

# ── 取真实主键 ──
real_case = db.session.query(Case.case_id).first()
case_id = real_case[0] if real_case else "FC20260522001"
real_gang = db.session.query(Gang.gang_id).first()
gang_id = real_gang[0] if real_gang else "G0001"
real_sess = db.session.query(AnalysisSession.session_id).first()
sess_id = real_sess[0] if real_sess else "S0001"
print(f"  真实样例：case={case_id}  gang={gang_id}  session={sess_id}")

main.app.dependency_overrides[get_current_user] = lambda: FAKE_USER
client = TestClient(main.app)

try:
    print("\n[基础设施]")
    hit(client, "GET", "/health")

    print("\n[鉴权 / 系统]")
    for p in ["/api/auth/me", "/api/auth/users", "/api/auth/logs",
              "/api/settings/api-key"]:
        hit(client, "GET", p)

    print("\n[案件]")
    for p in ["/api/cases", "/api/cases/stats",
              f"/api/cases/{case_id}", f"/api/cases/{case_id}/radar"]:
        hit(client, "GET", p)

    print("\n[团伙 / 并案]")
    for p in ["/api/gangs", "/api/gangs/review-results",
              f"/api/gangs/{gang_id}", f"/api/gangs/{gang_id}/radar",
              "/api/merges", "/api/merges/pending"]:
        hit(client, "GET", p)

    print("\n[资金 / 看板 / 检索]")
    for p in ["/api/capital/flows", "/api/capital/stats", "/api/dashboard",
              "/api/search?q=诈骗", "/api/search/advanced?type=phone&value=138"]:
        hit(client, "GET", p)

    print("\n[会话 / 对话]")
    for p in ["/api/sessions", f"/api/sessions/{sess_id}",
              "/api/chat/sessions", "/api/chat/intents",
              f"/api/chat/sessions/{sess_id}/history"]:
        hit(client, "GET", p)

    print("\n[工作流]")
    for p in ["/api/workflow/investigations", "/api/workflow/reviews",
              "/api/workflow/freeze-orders", "/api/workflow/approvals",
              "/api/workflow/approvals/pending",
              f"/api/workflow/cases/{case_id}/lifecycle",
              f"/api/workflow/cases/{case_id}/timeline"]:
        hit(client, "GET", p)

    print("\n[重点人员 / 派单 / 复核]")
    for p in ["/api/persons/key", "/api/dispatch/list", "/api/reviews/pending"]:
        hit(client, "GET", p)

    print("\n[导入留痕]")
    for p in ["/api/import-fund-flow/history",
              "/api/import-fund-flow/history?row_limit=0",
              "/api/import-fund-flow/history?source_file=AMLSim"]:
        hit(client, "GET", p)

    # ── 深度校验：并案建议字段 ──
    print("\n[字段级校验]")
    r = client.get("/api/merges", params={"status": "all"})
    if r.status_code == 200:
        body = r.json()
        need = {"id", "case_id_a", "case_id_b", "similarity", "status", "reason",
                "case_a_title", "case_b_title", "summary"}
        miss = need - set(body.keys() | (set(body.get("suggestions", [{}])[0].keys())
                                        if body.get("suggestions") else set()))
        print(f"  [{'PASS' if not miss else 'FAIL'}] /api/merges 字段完整"
              + (f" — 缺 {miss}" if miss else ""))
        if miss:
            BAD.append(("/api/merges 字段", "MISS", str(miss), ""))

    r = client.get("/api/workflow/freeze-orders")
    if r.status_code == 200:
        d = r.json()
        orders = d.get("orders") or d.get("data") or []
        if orders:
            oid = orders[0].get("order_id")
            if oid:
                hit(client, "GET", f"/api/workflow/freeze-orders/{oid}")
                hit(client, "GET", f"/api/workflow/freeze-orders/{oid}/receipts")

    # ── 空库安全：不存在的 ID 不应 500 ──
    print("\n[空数据健壮性]")
    for p in ["/api/cases/__NO_SUCH_CASE__",
              "/api/gangs/__NO_SUCH_GANG__",
              "/api/chat/sessions/__NO_SUCH_SESSION__/history"]:
        try:
            rr = client.get(p, timeout=30)
            ok = rr.status_code < 500
            print(f"  [{'PASS' if ok else 'FAIL'}] {p} — {rr.status_code}（不应 5xx）")
            if not ok:
                BAD.append((p, rr.status_code, "不存在的 ID 返回 5xx", ""))
        except Exception as e:  # noqa: BLE001
            print(f"  [FAIL] {p} — EXC {str(e)[:70]}")
            BAD.append((p, "EXC", str(e)[:90], ""))

finally:
    main.app.dependency_overrides.pop(get_current_user, None)

print("\n" + "=" * 76)
print(f"结果：{len(OK)} 正常 / {len(BAD)} 异常 / {len(PROTECTED)} 需鉴权")
if BAD:
    print("\n异常明细：")
    for item in BAD:
        print("  -", item)
print("\n" + ("全部通过 ✓" if not BAD else f"存在 {len(BAD)} 个问题 ✗"))
sys.exit(1 if BAD else 0)
