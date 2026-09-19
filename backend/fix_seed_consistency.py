"""修复历史种子数据中的逻辑一致性缺陷（Task #158 附属）。

背景：上一轮 `seed_empty_tables.py` 生成 `merge_suggestions` 与 `freeze_approvals` 时，
状态类字段与时间/批语字段各自独立随机，导致以下 4 类逻辑自相矛盾的记录：

  V1  pending   却带 reviewed_by / reviewed_at   （"未复核"却有复核痕迹）
  V2  终态      缺 reviewed_at                    （"已复核"却无复核时间）
  V3  终态      缺 reviewed_by                    （"已复核"却无复核人）
  V4  reviewed_at < created_at                    （复核早于创建）

  V5  freeze_approvals: decision='pending' 却写着"同意冻结"这类已表决批语
  V6  freeze_approvals: 同一工单中间层级 pending 却存在更高层级

根因已在 `seed_empty_tables.py` 修掉（新增 `rand_dt_after` + decision/comment 联动）。
本脚本用于就地修复**已经落库**的存量数据，不回滚、不重灌。

用法：
    python fix_seed_consistency.py --dry-run   # 只报告，不改
    python fix_seed_consistency.py             # 执行修复
"""
import argparse
import os
import random
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv  # noqa: E402

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_ROOT, ".env"))
load_dotenv(os.path.join(_ROOT, "backend", "key.env"))

from database import db  # noqa: E402
from database.models import MergeSuggestion, User  # noqa: E402
from sqlalchemy import text as T  # noqa: E402

# 与 seed_empty_tables.build_freeze_chain 中的批语保持一致
APPROVE_COMMENTS = [
    "案情清楚、紧急程度高，同意冻结。",
    "涉案账户资金仍在流动，同意立即冻结。",
    "证据链完整，同意按流程冻结。",
    "同意，注意同步告知开户行。",
]
PENDING_COMMENTS = [
    "补充被害人陈述后再次提交。",
    "涉案金额需与银行流水二次核对，暂缓表决。",
    "待补充上级审批意见后表决。",
]


def audit_merges():
    rows = MergeSuggestion.query.all()
    return {
        "total": len(rows),
        "v1": [s for s in rows if s.status == "pending"
               and (s.reviewed_by is not None or s.reviewed_at is not None)],
        "v2": [s for s in rows if s.status in ("approved", "rejected") and s.reviewed_at is None],
        "v3": [s for s in rows if s.status in ("approved", "rejected") and s.reviewed_by is None],
        "v4": [s for s in rows if s.reviewed_at and s.created_at and s.reviewed_at < s.created_at],
    }


def audit_approvals():
    rows = db.session.execute(T(
        "SELECT id, order_id, approval_level, decision, comment, created_at "
        "FROM freeze_approvals ORDER BY order_id, approval_level, id"
    )).fetchall()
    v5, v6, v7 = [], [], []
    by_order = {}
    for r in rows:
        rid, order_id, lvl, decision, comment, created_at = r
        by_order.setdefault(order_id, []).append(r)
        if decision == "pending" and comment and comment in APPROVE_COMMENTS:
            v5.append((rid, comment))
        if decision == "approved" and comment and comment in PENDING_COMMENTS:
            v5.append((rid, comment))
    for order_id, items in by_order.items():
        for i, r in enumerate(items):
            if r[3] == "pending" and i < len(items) - 1:
                v6.append((order_id, r[2], [x[2] for x in items[i + 1:]]))
        # 层级时间必须递增
        prev = None
        for r in items:
            if prev and r[5] and prev[5] and r[5] < prev[5]:
                v7.append((order_id, prev[2], r[2]))
            prev = r
    return {"total": len(rows), "v5": v5, "v6": v6, "v7": v7}


def fix_merges(dry_run):
    a = audit_merges()
    print(f"\n[MergeSuggestion] 共 {a['total']} 条")
    print(f"  V1 pending 带复核痕迹 : {len(a['v1'])} 条 {[s.id for s in a['v1']]}")
    print(f"  V2 终态缺复核时间     : {len(a['v2'])} 条 {[s.id for s in a['v2']]}")
    print(f"  V3 终态缺复核人       : {len(a['v3'])} 条 {[s.id for s in a['v3']]}")
    print(f"  V4 复核早于创建       : {len(a['v4'])} 条 "
          f"{[(s.id, str(s.created_at)[:16], str(s.reviewed_at)[:16]) for s in a['v4']]}")

    if dry_run:
        print("  （dry-run，未修改）")
        return 0

    user_ids = [u[0] for u in db.session.query(User.id).all()] or [1]
    changed = 0
    cap = datetime.now() - timedelta(hours=1)

    for s in a["v1"]:
        s.reviewed_by = None
        s.reviewed_at = None
        changed += 1
    for s in a["v2"] + a["v3"]:
        if s.reviewed_by is None:
            s.reviewed_by = random.choice(user_ids)
        if s.reviewed_at is None:
            base = s.created_at or (datetime.now() - timedelta(days=30))
            delta = timedelta(days=random.randint(1, 30), hours=random.randint(0, 23))
            cand = base + delta
            s.reviewed_at = cand if cand < cap else cap
        changed += 1
    # V4 最后处理，覆盖上面可能写入的倒置时间
    for s in a["v4"]:
        base = s.created_at
        delta = timedelta(days=random.randint(1, 30), hours=random.randint(0, 23))
        cand = base + delta
        s.reviewed_at = cand if cand < cap else cap
        if s.reviewed_by is None:
            s.reviewed_by = random.choice(user_ids)
        changed += 1

    db.session.commit()
    print(f"  → 已修复 {changed} 条（去重前计数）")
    return changed


def fix_approvals(dry_run):
    a = audit_approvals()
    print(f"\n[freeze_approvals] 共 {a['total']} 条")
    print(f"  V5 decision/批语矛盾  : {len(a['v5'])} 条 {a['v5']}")
    print(f"  V6 pending 后仍有上级 : {len(a['v6'])} 条 {a['v6']}")
    print(f"  V7 层级时间倒置       : {len(a['v7'])} 条 {a['v7']}")

    if dry_run:
        print("  （dry-run，未修改）")
        return 0

    changed = 0
    # V5：按 decision 重写批语
    for rid, _ in a["v5"]:
        row = db.session.execute(T(
            "SELECT decision FROM freeze_approvals WHERE id=:i"), {"i": rid}).fetchone()
        if not row:
            continue
        decision = row[0]
        comment = (random.choice(APPROVE_COMMENTS) if decision == "approved"
                   else random.choice(PENDING_COMMENTS))
        db.session.execute(T("UPDATE freeze_approvals SET comment=:c WHERE id=:i"),
                           {"c": comment, "i": rid})
        changed += 1

    # V6：中间层级 pending → 改为 approved 并补已表决批语
    #     （保留"存在上级层级"的事实，不删行，避免破坏审计链完整性）
    for order_id, lvl, _higher in a["v6"]:
        rows = db.session.execute(T(
            "SELECT id FROM freeze_approvals WHERE order_id=:o AND approval_level=:l "
            "AND decision='pending'"), {"o": order_id, "l": lvl}).fetchall()
        for (rid,) in rows:
            db.session.execute(T(
                "UPDATE freeze_approvals SET decision='approved', comment=:c WHERE id=:i"),
                {"c": random.choice(APPROVE_COMMENTS), "i": rid})
            changed += 1

    # V7：层级时间改为递增
    orders = db.session.execute(T(
        "SELECT DISTINCT order_id FROM freeze_approvals")).fetchall()
    for (order_id,) in orders:
        rows = db.session.execute(T(
            "SELECT id, approval_level, created_at FROM freeze_approvals "
            "WHERE order_id=:o ORDER BY approval_level, id"), {"o": order_id}).fetchall()
        prev = None
        for rid, lvl, created in rows:
            if prev is not None and created and prev and created < prev:
                new_dt = prev + timedelta(hours=random.randint(2, 48))
                cap = datetime.now() - timedelta(hours=1)
                if new_dt > cap:
                    new_dt = cap
                db.session.execute(T(
                    "UPDATE freeze_approvals SET created_at=:d WHERE id=:i"),
                    {"d": new_dt, "i": rid})
                created = new_dt
                changed += 1
            prev = created

    db.session.commit()
    print(f"  → 已修复 {changed} 条")
    return changed


def audit_orders():
    """freeze_orders 状态与 freeze_receipts 是否自洽。

    V8  工单 status='failed' 却存在 success/pending 回执（"失败"与"有进展"矛盾）
    V9  工单 status='executed' 却存在非 success 回执
    V10 工单有回执但缺 executed_at；或 executed_at 早于 approved_at
    """
    rows = db.session.execute(T(
        "SELECT order_id, status, approved_at, executed_at FROM freeze_orders"
    )).fetchall()
    v8, v9, v10 = [], [], []
    for order_id, status, approved_at, executed_at in rows:
        recs = db.session.execute(T(
            "SELECT execution_status FROM freeze_receipts WHERE order_id=:o"
        ), {"o": order_id}).fetchall()
        st = [r[0] for r in recs]
        succ = sum(1 for x in st if x == 'success')
        pend = sum(1 for x in st if x in ('pending', 'processing'))
        if status == 'failed' and (succ > 0 or pend > 0):
            v8.append((order_id, status, st))
        if status == 'executed' and any(x != 'success' for x in st):
            v9.append((order_id, st))
        if st and executed_at is None:
            v10.append((order_id, '有回执但缺 executed_at'))
        elif approved_at and executed_at and executed_at < approved_at:
            v10.append((order_id, f'executed_at({executed_at}) < approved_at({approved_at})'))
    return {"total": len(rows), "v8": v8, "v9": v9, "v10": v10}


def derive_status(statuses):
    """与 routes/workflow.py::_derive_freeze_status 保持同一口径。"""
    if not statuses:
        return None  # 无回执不动（可能确实还没执行）
    success = sum(1 for x in statuses if x == 'success')
    pending = sum(1 for x in statuses if x in ('pending', 'processing'))
    if success == len(statuses):
        return 'executed'
    if success > 0 or pending > 0:
        return 'partial'
    return 'failed'


def fix_orders(dry_run):
    a = audit_orders()
    print(f"\n[freeze_orders] 共 {a['total']} 条")
    print(f"  V8 failed 却有 success/pending 回执 : {len(a['v8'])} 条 {[(x[0], x[2]) for x in a['v8']]}")
    print(f"  V9 executed 却有非 success 回执      : {len(a['v9'])} 条 {a['v9']}")
    print(f"  V10 executed_at 缺失或早于 approved  : {len(a['v10'])} 条 {a['v10']}")

    if dry_run:
        print("  （dry-run，未修改）")
        return 0

    rows = db.session.execute(T("SELECT order_id, status FROM freeze_orders")).fetchall()
    changed = 0
    for order_id, status in rows:
        st = [r[0] for r in db.session.execute(T(
            "SELECT execution_status FROM freeze_receipts WHERE order_id=:o"
        ), {"o": order_id}).fetchall()]
        target = derive_status(st)
        if target and target != status:
            db.session.execute(T("UPDATE freeze_orders SET status=:s WHERE order_id=:o"),
                               {"s": target, "o": order_id})
            print(f"    {order_id}: {status} → {target}（回执 {st}）")
            changed += 1
    db.session.commit()
    print(f"  → 已修正 {changed} 条")
    return changed


def main():
    ap = argparse.ArgumentParser(description="修复种子数据逻辑一致性缺陷")
    ap.add_argument("--dry-run", action="store_true", help="只报告，不修改")
    args = ap.parse_args()

    db.init_app()
    if args.dry_run:
        print("=" * 60)
        print("DRY RUN — 仅审计，不写入")
        print("=" * 60)
    else:
        print("=" * 60)
        print("修复模式 — 将写入数据库")
        print("=" * 60)

    n1 = fix_merges(args.dry_run)
    n2 = fix_approvals(args.dry_run)
    n3 = fix_orders(args.dry_run)

    print("\n" + "=" * 60)
    if args.dry_run:
        print("审计完成。去掉 --dry-run 即可执行修复。")
        return 0

    print(f"修复完成：merge_suggestions {n1} 处、freeze_approvals {n2} 处、freeze_orders {n3} 处")
    print("\n复检：")
    a1 = audit_merges()
    a2 = audit_approvals()
    a3 = audit_orders()
    bad1 = len(a1["v1"]) + len(a1["v2"]) + len(a1["v3"]) + len(a1["v4"])
    bad2 = len(a2["v5"]) + len(a2["v6"]) + len(a2["v7"])
    bad3 = len(a3["v8"]) + len(a3["v9"]) + len(a3["v10"])
    print(f"  merge_suggestions 残留违规：{bad1}")
    print(f"  freeze_approvals  残留违规：{bad2}")
    print(f"  freeze_orders     残留违规：{bad3}")
    total_bad = bad1 + bad2 + bad3
    print("  " + ("全部干净 ✓" if total_bad == 0 else f"仍有 {total_bad} 项违规，请检查 ✗"))
    return 0 if total_bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
