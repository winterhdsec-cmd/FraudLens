"""
FraudLens 办案工作流端到端验收测试
==================================
覆盖：立案 → 侦查 → 研判 → 止付工单 → 审批 → 冻结执行 → 结案归档 → 时间线

用法：
    python scripts/e2e_workflow_test.py [--base http://localhost:5003] [--no-gnn]

退出码 0 表示全链路通过；非 0 表示有失败步骤（详见输出）。
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from typing import Any, Dict, Optional


BASE = "http://localhost:5003"
TOKEN: Optional[str] = None
PASS = 0
FAIL = 0


def _req(method: str, path: str, body: Any = None, timeout: int = 30) -> Dict[str, Any]:
    url = BASE + path
    data = None
    headers = {"Content-Type": "application/json"}
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    if body is not None:
        data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return {"_raw": raw, "_status": resp.status}
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            return json.loads(raw)
        except Exception:
            return {"_error": raw, "_status": e.code}
    except Exception as e:
        return {"_error": str(e)}


def step(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    tag = "[PASS]" if cond else "[FAIL]"
    if cond:
        PASS += 1
    else:
        FAIL += 1
    line = f"{tag} {name}"
    if detail:
        line += f"  |  {detail}"
    print(line)


def transition(cid: str, to_status: str, reason: str = "") -> Dict[str, Any]:
    return _req("POST", f"/api/workflow/cases/{cid}/transition",
                {"to_status": to_status, "reason": reason}, timeout=15)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://localhost:5003")
    parser.add_argument("--no-gnn", action="store_true")
    args = parser.parse_args()

    global BASE, TOKEN
    BASE = args.base

    print("=" * 70)
    print("FraudLens 办案工作流 E2E 验收测试")
    print("=" * 70)

    # 1. 登录
    r = _req("POST", "/api/auth/demo-login", timeout=15)
    TOKEN = r.get("access_token")
    step("1. 演示登录", bool(TOKEN), f"user={r.get('user', {}).get('username')}")

    # 2. 取案件（优先选"待立案"状态的案件，确保完整流转链路可测）
    r = _req("GET", "/api/cases?limit=50", timeout=15)
    cases = r.get("cases") or []
    step("2. 获取案件列表", len(cases) > 0, f"count={len(cases)}")
    if not cases:
        print("无案件可测，终止。请先 seed 数据。")
        return 1
    # 查询每个案件的 lifecycle，优先选"待立案"
    case = None
    for c in cases[:20]:
        lc = _req("GET", f"/api/workflow/cases/{c['case_id']}/lifecycle", timeout=8)
        if lc.get("current_status") == "待立案":
            case = c
            break
    if not case:
        case = cases[0]  # 退而求其次
    cid = case["case_id"]
    print(f"    选用案件: {cid} | {case.get('title', '')[:30]}")

    # 3. 生命周期初始状态
    r = _req("GET", f"/api/workflow/cases/{cid}/lifecycle", timeout=15)
    cur = r.get("current_status", "")
    avail = r.get("available_transitions") or []
    step("3. 查询生命周期", r.get("success", False), f"current={cur} available={avail}")

    # 4. 状态流转到"待研判"
    # 按状态机逐步流转：待立案→已立案→侦查中→待研判
    # 智能跳过：若当前状态已在路径中或之后，从当前状态开始流转
    path = ["待立案", "已立案", "侦查中", "待研判"]
    # 找到当前状态在路径中的位置
    try:
        cur_idx = path.index(cur)
    except ValueError:
        # 当前状态不在路径中（如"研判完成"），尝试流转到"侦查中"
        cur_idx = 2  # 从"侦查中"开始
        path = ["侦查中", "待研判"]
    else:
        path = path[cur_idx + 1:]  # 从下一个状态开始流转

    cur_lower = cur
    for target in path:
        if cur_lower == target:
            continue
        r = transition(cid, target, f"E2E 流转到 {target}")
        ok = r.get("success", False)
        step(f"4.x 流转 {cur_lower} → {target}", ok, r.get("error", ""))
        if not ok:
            r2 = _req("GET", f"/api/workflow/cases/{cid}/lifecycle", timeout=10)
            cur_lower = r2.get("current_status", "")
            print(f"    流转后状态刷新: {cur_lower}")
        else:
            cur_lower = target

    # 5. 发起研判（可能较慢，长超时）
    print("    发起研判中（可能耗时 30-90s，含 LLM/Agent 调用）...")
    t0 = time.time()
    r = _req("POST", f"/api/workflow/cases/{cid}/investigations",
             {"use_gnn": not args.no_gnn}, timeout=180)
    elapsed = time.time() - t0
    inv_ok = r.get("success", False)
    conf = r.get("confidence")
    gate = r.get("gate_decision")
    step("5. 发起研判", inv_ok, f"耗时={elapsed:.1f}s confidence={conf} gate={gate}")
    if inv_ok:
        tid = r.get("task_id")
        print(f"    研判任务: {tid} | confidence={conf} | gate={gate}")

    # 6. 查询研判任务列表
    r = _req("GET", f"/api/workflow/investigations?case_id={cid}", timeout=15)
    tasks = r.get("tasks") or []
    step("6. 查询研判任务列表", len(tasks) > 0, f"count={len(tasks)}")

    # 7. 创建止付冻结工单
    freeze_payload = {
        "case_id": cid,
        "action_type": "冻结",
        "freeze_amount": 50000.0,
        "legal_basis": "《中华人民共和国反电信网络诈骗法》第十一条、第十二条",
        "reason": "E2E 测试：涉案资金紧急冻结，防止转移",
        "target_accounts": [
            {"account_number": "6228480402564890018",
             "account_name": "测试账户A", "bank_name": "农业银行"},
        ],
    }
    r = _req("POST", "/api/workflow/freeze-orders", freeze_payload, timeout=15)
    order = r.get("order")
    oid = order.get("order_id") if order else None
    step("7. 创建止付冻结工单", bool(oid), f"order_id={oid}")
    if not oid:
        print(f"    创建失败: {r}")
        # 仍继续后续流程验证

    # 8. 提交审批
    flow_id = None
    if oid:
        r = _req("POST", f"/api/workflow/freeze-orders/{oid}/submit", {}, timeout=15)
        flow_id = r.get("flow_id")
        step("8. 提交审批", bool(flow_id), f"flow_id={flow_id} | {r.get('error','')}")
    else:
        step("8. 提交审批", False, "无工单，跳过")

    # 9. 审批通过（触发冻结执行回调）
    if flow_id:
        r = _req("POST", f"/api/workflow/approvals/{flow_id}/approve",
                 {"comment": "E2E 测试审批通过"}, timeout=30)
        step("9. 审批通过", r.get("success", False),
             f"status={r.get('status')} | {r.get('error','')}")

    # 10. 查询工单详情（含回执）
    if oid:
        r = _req("GET", f"/api/workflow/freeze-orders/{oid}", timeout=15)
        order_detail = r.get("order") or {}
        receipts = r.get("receipts") or []
        step("10. 工单回执验证",
             order_detail.get("status") in ("executed", "partial", "approved", "failed"),
             f"order_status={order_detail.get('status')} receipts={len(receipts)}")

    # 11. 查询待审批列表
    r = _req("GET", "/api/workflow/approvals/pending", timeout=15)
    step("11. 查询待审批列表", r.get("success", False), f"pending={r.get('total', 0)}")

    # 12. 查询复核任务（低置信可能自动创建）
    r = _req("GET", f"/api/workflow/reviews?case_id={cid}", timeout=15)
    reviews = r.get("reviews") or []
    step("12. 查询复核任务", r.get("success", False), f"reviews={len(reviews)}")

    # 13. 流转到结案归档：研判完成→待结案→已归档
    r = _req("GET", f"/api/workflow/cases/{cid}/lifecycle", timeout=10)
    cur = r.get("current_status", "")
    if cur == "研判完成":
        r = transition(cid, "待结案", "E2E 研判后结案")
        step("13.a 流转 研判完成→待结案", r.get("success", False), r.get("error", ""))
        r = transition(cid, "已归档", "E2E 结案归档")
        step("13.b 流转 待结案→已归档", r.get("success", False), r.get("error", ""))
    elif cur == "研判中":
        # 研判未完成，手动推进
        r = transition(cid, "研判完成", "E2E 手动推进研判完成")
        step("13.a 流转 研判中→研判完成", r.get("success", False), r.get("error", ""))
        r = transition(cid, "待结案", "E2E 结案")
        step("13.b 流转 研判完成→待结案", r.get("success", False), r.get("error", ""))
        r = transition(cid, "已归档", "E2E 归档")
        step("13.c 流转 待结案→已归档", r.get("success", False), r.get("error", ""))
    else:
        print(f"    案件当前状态 {cur}，跳过结案流转")

    # 14. 时间线验证
    r = _req("GET", f"/api/workflow/cases/{cid}/timeline", timeout=15)
    timeline = r.get("timeline") or []
    step("14. 办案时间线", len(timeline) >= 3,
         f"events={len(timeline)} types={[e.get('type') for e in timeline[:5]]}")

    # 15. 文书下载（PDF，二进制响应需特殊处理）
    if oid:
        url = f"{BASE}/api/workflow/freeze-orders/{oid}/document?format=pdf"
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {TOKEN}"})
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                pdf_bytes = resp.read()
                ct = resp.headers.get("Content-Type", "")
                ok = len(pdf_bytes) > 1000 and "pdf" in ct.lower()
                step("15. 文书下载(PDF)", ok, f"size={len(pdf_bytes)} type={ct}")
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            step("15. 文书下载(PDF)", False, f"HTTP {e.code}: {body[:200]}")
        except Exception as e:
            step("15. 文书下载(PDF)", False, str(e)[:200])

    # 总结
    print("=" * 70)
    print(f"E2E 验收结果: {PASS} 通过 / {FAIL} 失败")
    print("=" * 70)
    return 0 if FAIL == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
