"""种子数据逻辑一致性回归测试（Task #158 附属）。

与 `_verify_merge_panel.py` 的区别：本脚本**直接查库**，不依赖 API 层，
用于守护一个跨会话的长期不变量——种子数据不得出现自相矛盾的状态/时间组合。

覆盖的不变量：
  merge_suggestions
    I1  status='pending'         → reviewed_by IS NULL 且 reviewed_at IS NULL
    I2  status IN (approved,rejected) → reviewed_at IS NOT NULL
    I3  status IN (approved,rejected) → reviewed_by IS NOT NULL
    I4  reviewed_at >= created_at（不得早于创建）
    I5  created_at / similarity 非空，similarity ∈ (0,1]
    I6  status ∈ {pending, approved, rejected}
    I7  case_id_a != case_id_b（不得自己和自己并案）

  freeze_approvals
    I8  decision='pending'   → comment 不得为"同意…"类已表决批语
    I9  decision='approved'  → comment 不得为"暂缓/补充后再提交"类未表决批语
    I10 decision ∈ {pending, approved, rejected}
    I11 同一工单内审批层级递增时，时间不得倒置
    I12 同一工单若某层级 pending，则不应存在更高层级（不得越级流转）

  freeze_receipts
    I13 冻结到期时间（如有）应晚于创建时间

任一不变量失败即退出码 1，可直接接入 CI。
"""
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv  # noqa: E402

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_ROOT, ".env"))
load_dotenv(os.path.join(_ROOT, "backend", "key.env"))

from database import db  # noqa: E402
from database.models import MergeSuggestion  # noqa: E402
from sqlalchemy import text as T  # noqa: E402

APPROVE_MARKERS = ("同意", "已核实", "符合冻结条件")
PENDING_MARKERS = ("暂缓", "再次提交", "待补充", "二次核对")

PASS, FAIL = [], []


def check(name, violations, detail_fn=None):
    ok = not violations
    (PASS if ok else FAIL).append(name)
    msg = f"  [{'PASS' if ok else 'FAIL'}] {name}"
    if not ok:
        shown = violations[:4]
        extra = f" ...等 {len(violations)} 条" if len(violations) > 4 else ""
        msg += f" — 违规 {len(violations)} 条：{shown}{extra}"
    print(msg)


db.init_app()

print("=" * 74)
print("种子数据逻辑一致性回归测试")
print("=" * 74)

# ────────────────────────── merge_suggestions ──────────────────────────
print("\n[merge_suggestions]")
ms = MergeSuggestion.query.all()
print(f"  样本量：{len(ms)} 条")

check("I1 pending 不得带复核人/复核时间",
      [(s.id, s.reviewed_by, s.reviewed_at) for s in ms
       if s.status == "pending" and (s.reviewed_by is not None or s.reviewed_at is not None)])

check("I2 终态必须有复核时间",
      [s.id for s in ms if s.status in ("approved", "rejected") and s.reviewed_at is None])

check("I3 终态必须有复核人",
      [s.id for s in ms if s.status in ("approved", "rejected") and s.reviewed_by is None])

check("I4 复核时间不得早于创建时间",
      [(s.id, str(s.created_at), str(s.reviewed_at)) for s in ms
       if s.reviewed_at and s.created_at and s.reviewed_at < s.created_at])

check("I5 created_at / similarity 合法性",
      [(s.id, s.similarity) for s in ms
       if s.created_at is None or s.similarity is None or not (0 < s.similarity <= 1)])

check("I6 状态取值合法",
      [(s.id, s.status) for s in ms if s.status not in ("pending", "approved", "rejected")])

check("I7 不得自己与自己并案",
      [s.id for s in ms if s.case_id_a == s.case_id_b])

# ────────────────────────── freeze_approvals ──────────────────────────
print("\n[freeze_approvals]")
fa = db.session.execute(T(
    "SELECT id, order_id, approval_level, decision, comment, created_at "
    "FROM freeze_approvals ORDER BY order_id, approval_level, id"
)).fetchall()
print(f"  样本量：{len(fa)} 条")

check("I8 pending 不得配已表决批语",
      [(r[0], r[4]) for r in fa
       if r[3] == "pending" and r[4] and any(m in r[4] for m in APPROVE_MARKERS)])

check("I9 approved 不得配未表决批语",
      [(r[0], r[4]) for r in fa
       if r[3] == "approved" and r[4] and any(m in r[4] for m in PENDING_MARKERS)])

check("I10 decision 取值合法",
      [(r[0], r[3]) for r in fa if r[3] not in ("pending", "approved", "rejected")])

by_order = defaultdict(list)
for r in fa:
    by_order[r[1]].append(r)

v11, v12 = [], []
for oid, items in by_order.items():
    items = sorted(items, key=lambda x: (x[2] or 0, x[0]))
    # 时间倒置
    for i in range(1, len(items)):
        prev, cur = items[i - 1], items[i]
        if prev[5] and cur[5] and cur[5] < prev[5]:
            v11.append((oid, prev[2], cur[2]))
    # 越级流转
    for i, r in enumerate(items):
        if r[3] == "pending" and i < len(items) - 1:
            v12.append((oid, r[2], [x[2] for x in items[i + 1:]]))

check("I11 同一工单层级时间不得倒置", v11)
check("I12 pending 层级后不得存在更高层级", v12)

# ────────────────────────── freeze_receipts ──────────────────────────
print("\n[freeze_receipts]")
fr = db.session.execute(T(
    "SELECT id, order_id, execution_status, created_at, freeze_until FROM freeze_receipts"
)).fetchall()
print(f"  样本量：{len(fr)} 条")

check("I13 冻结到期时间应晚于创建时间",
      [(r[0], str(r[3]), str(r[4])) for r in fr
       if r[4] and r[3] and r[4] < r[3]])

check("I14 execution_status 非空",
      [r[0] for r in fr if not r[2]])

# ────────────────────────── 汇总 ──────────────────────────
print("\n" + "=" * 74)
print(f"结果：{len(PASS)} 通过 / {len(FAIL)} 失败")
if FAIL:
    print("失败项：")
    for f in FAIL:
        print("  -", f)
    sys.exit(1)
print("全部不变量成立 ✓")
sys.exit(0)
