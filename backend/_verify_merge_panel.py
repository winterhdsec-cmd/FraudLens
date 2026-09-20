"""并案建议面板（Task #158）端到端验证。

覆盖：
  1. GET /api/merges 默认/pending/approved/rejected/all 过滤与 summary 统计
  2. 分页参数 limit/offset
  3. 每条记录含两侧案件标题/受害人/风险与复核元数据
  4. 数据语义一致性：pending 必须无复核人/复核时间；非 pending 必须有复核时间
  5. POST /api/merges/{id}/reject 成功路径 + 幂等拒绝（重复驳回返回 400）+ 不存在返回 400
  6. 驳回后 summary 计数同步变化
  7. 未认证访问被拒
  8. POST /api/merges/confirm 对不存在团伙返回 400（不误建关联）

用 TestClient（ASGI 直连）执行，避免占用端口。
"""
import os
import sys

os.environ.setdefault("JWT_SECRET_KEY", "verify-script-only-not-a-real-secret")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv  # noqa: E402

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# 只加载 key.env —— 与 main.py 保持一致（main.py 只 load_dotenv('backend/key.env')）。
# 此前这里还加载了根目录 .env，而 python-dotenv 默认 override=False：**先加载者胜出**，
# 于是 .env 里的 REDIS_PASSWORD 等值会盖过 key.env，造出与生产不一致的配置环境
# （曾据此把「Redis 密码不一致 → 单次调用 10 秒」误判为线上缺陷；实际那是脚本特有环境，
#   真实启动实测 2ms。教训：验证脚本的配置加载方式必须与被测程序一致）。
load_dotenv(os.path.join(_ROOT, 'backend', 'key.env'))

from fastapi.testclient import TestClient  # noqa: E402

import main  # noqa: E402
from database import db  # noqa: E402
from database.models import MergeSuggestion, GangCaseRelation  # noqa: E402
from routes.deps import get_current_user  # noqa: E402

PASS, FAIL = [], []


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))


FAKE_USER = {"id": 1, "username": "verify_admin", "role": "admin"}


def make_client():
    main.app.dependency_overrides[get_current_user] = lambda: FAKE_USER
    return TestClient(main.app)


def cleanup(client):
    main.app.dependency_overrides.pop(get_current_user, None)


db.init_app()

print("=" * 72)
print("并案建议面板端到端验证")
print("=" * 72)

client = make_client()
try:
    # ── 1. 基础列表 ──
    print("\n[1] GET /api/merges 基础列表")
    r = client.get("/api/merges", params={"status": "all"})
    check("HTTP 200", r.status_code == 200, f"status={r.status_code}")
    body = r.json()
    check("success=True", body.get("success") is True)
    all_items = body.get("suggestions", [])
    total = body.get("total", 0)
    check("total>0（数据已填充）", total > 0, f"total={total}")
    check("返回条数与 total 一致", len(all_items) == total, f"len={len(all_items)} total={total}")

    summary = body.get("summary", {})
    check("summary 含四类计数", all(k in summary for k in ("pending", "approved", "rejected", "total")),
          str(summary))
    check("summary 各类之和 == total",
          summary.get("pending", 0) + summary.get("approved", 0) + summary.get("rejected", 0) == total,
          f"{summary}")

    # ── 2. 状态过滤 ──
    print("\n[2] 状态过滤")
    for st in ("pending", "approved", "rejected"):
        rr = client.get("/api/merges", params={"status": st})
        items = rr.json().get("suggestions", [])
        ok = all(i["status"] == st for i in items)
        check(f"status={st} 全部为该状态", ok, f"n={len(items)}")
        check(f"status={st} 条数 == summary", len(items) == summary.get(st, 0),
              f"len={len(items)} summary={summary.get(st)}")

    # ── 3. 字段完整性 ──
    print("\n[3] 字段完整性")
    required = ["id", "case_id_a", "case_id_b", "similarity", "reason", "status",
                "case_a_title", "case_b_title", "case_a_victim", "case_b_victim",
                "reviewed_by", "reviewed_at", "created_at"]
    sample = all_items[0] if all_items else {}
    missing = [k for k in required if k not in sample]
    check("全部必需字段存在", not missing, f"missing={missing}")
    if all_items:
        titled = [i for i in all_items if i.get("case_a_title")]
        check("案件标题已回填（非空）", len(titled) == len(all_items),
              f"{len(titled)}/{len(all_items)}")
        sorted_ok = all(all_items[i]["similarity"] >= all_items[i + 1]["similarity"]
                        for i in range(len(all_items) - 1))
        check("按相似度降序排列", sorted_ok)
        check("相似度在合理区间 (0,1]", all(0 < i["similarity"] <= 1 for i in all_items))

    # ── 4. 语义一致性 ──
    print("\n[4] 语义一致性（核心修复项）")
    bad_pending = [i for i in all_items
                   if i["status"] == "pending" and (i["reviewed_by"] or i["reviewed_at"])]
    check("pending 均无复核人/复核时间", not bad_pending,
          f"违规 {len(bad_pending)} 条：{[(i['id'], i['reviewed_by'], i['reviewed_at']) for i in bad_pending[:3]]}")
    bad_decided = [i for i in all_items
                   if i["status"] in ("approved", "rejected") and not i["reviewed_at"]]
    check("approved/rejected 均有复核时间", not bad_decided,
          f"违规 {len(bad_decided)} 条：{[(i['id'], i['status']) for i in bad_decided[:3]]}")

    # ── 5. 分页 ──
    print("\n[5] 分页")
    r1 = client.get("/api/merges", params={"status": "all", "limit": 3, "offset": 0})
    p1 = r1.json().get("suggestions", [])
    check("limit=3 返回 3 条", len(p1) == 3, f"len={len(p1)}")
    r2 = client.get("/api/merges", params={"status": "all", "limit": 3, "offset": 3})
    p2 = r2.json().get("suggestions", [])
    check("offset=3 与首页无重叠", {i["id"] for i in p1}.isdisjoint({i["id"] for i in p2}))
    check("分页 total 不变", r1.json().get("total") == total)

    # ── 6. 驳回（成功路径） ──
    print("\n[6] 驳回并案建议")
    pend = client.get("/api/merges", params={"status": "pending"}).json().get("suggestions", [])
    if not pend:
        check("存在待研判建议用于测试", False, "无 pending 数据，跳过驳回用例")
    else:
        target = pend[-1]
        before_pending = len(pend)
        rr = client.post(f"/api/merges/{target['id']}/reject",
                         json={"reason": "验证脚本：两名受害人无资金往来"})
        check("驳回 HTTP 200", rr.status_code == 200, f"status={rr.status_code} {rr.text[:120]}")
        check("驳回 success=True", rr.json().get("success") is True)
        check("返回状态为 rejected", rr.json().get("data", {}).get("status") == "rejected")

        after = client.get("/api/merges", params={"status": "pending"}).json().get("suggestions", [])
        check("pending 数量减 1", len(after) == before_pending - 1,
              f"{before_pending} -> {len(after)}")
        check("被驳回项已不在 pending 中", target["id"] not in {i["id"] for i in after})

        rej = client.get("/api/merges", params={"status": "rejected"}).json().get("suggestions", [])
        rec = next((i for i in rej if i["id"] == target["id"]), None)
        check("已出现在 rejected 列表", rec is not None)
        if rec:
            check("reason 已追加驳回理由", "验证脚本" in (rec["reason"] or ""), rec["reason"][:80])
            check("reviewed_at 已写入", bool(rec["reviewed_at"]))
            check("reviewed_by 已写入", rec["reviewed_by"] == FAKE_USER["id"])

        # ── 7. 幂等与异常 ──
        print("\n[7] 驳回幂等与异常")
        rr2 = client.post(f"/api/merges/{target['id']}/reject", json={"reason": "重复驳回"})
        check("重复驳回返回 400", rr2.status_code == 400, f"status={rr2.status_code}")
        check("重复驳回错误信息明确", "pending" in (rr2.json().get("error") or ""),
              rr2.json().get("error", "")[:80])

        rr3 = client.post("/api/merges/99999999/reject", json={"reason": "x"})
        check("不存在 ID 返回 400", rr3.status_code == 400, f"status={rr3.status_code}")

        # 还原：把测试驳回项改回 pending，避免污染演示数据
        s = MergeSuggestion.query.filter_by(id=target["id"]).first()
        if s:
            s.status = "pending"
            s.reviewed_by = None
            s.reviewed_at = None
            original_reason = (s.reason or "")
            marker = "；驳回理由：验证脚本：两名受害人无资金往来"
            if marker in original_reason:
                s.reason = original_reason.replace(marker, "")[:200]
            db.session.commit()
            print(f"  [INFO] 已还原建议 #{target['id']} 为 pending")

    # ── 8. confirm 异常路径 ──
    print("\n[8] 采纳（confirm）异常路径")
    pend2 = client.get("/api/merges", params={"status": "pending"}).json().get("suggestions", [])
    if pend2:
        t = pend2[0]
        before_rel = GangCaseRelation.query.count()
        rc = client.post("/api/merges/confirm",
                         json={"case_id_a": t["case_id_a"], "case_id_b": t["case_id_b"],
                               "gang_id": "__NO_SUCH_GANG__"})
        check("不存在的团伙返回 400", rc.status_code == 400, f"status={rc.status_code}")
        check("未创建任何团伙关联（无副作用）",
              GangCaseRelation.query.count() == before_rel,
              f"{before_rel} -> {GangCaseRelation.query.count()}")
        check("建议状态未被改动",
              MergeSuggestion.query.filter_by(id=t["id"]).first().status == "pending")

    # ── 9. 未认证访问 ──
    print("\n[9] 鉴权")
    main.app.dependency_overrides.pop(get_current_user, None)
    anon = TestClient(main.app)
    ra = anon.get("/api/merges")
    check("未带 token 访问被拒（401/403）", ra.status_code in (401, 403), f"status={ra.status_code}")

finally:
    cleanup(client)

print("\n" + "=" * 72)
print(f"结果：{len(PASS)} 通过 / {len(FAIL)} 失败")
if FAIL:
    print("失败项：")
    for f in FAIL:
        print("  -", f)
    sys.exit(1)
print("全部通过")
