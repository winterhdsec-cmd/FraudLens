"""一键回归：跑全部验证脚本并汇总结果。

用法：
    python run_verifications.py            # 跑全部
    python run_verifications.py chat seed  # 只跑名称含 chat / seed 的

为什么需要它：验证脚本分散在 backend/ 下，逐个手跑容易漏；且部分脚本会拉起
内置 Redis、BGE 模型（耗时较长），需要一个统一入口按序执行并汇总通过/失败，
便于提交前自检与复赛前回归。

退出码：0 = 全部通过；1 = 有失败。
"""
import os
import subprocess
import sys
import time
from pathlib import Path

BACKEND = Path(__file__).resolve().parent
PYTHON = sys.executable or "python"

# (脚本, 说明, 是否有副作用)
# 注：会拉起 Redis/BGE 的脚本耗时长（30~90s），已按"轻→重"排序。
SUITE = [
    ("_verify_seed_consistency.py", "种子数据逻辑一致性不变量", False),
    ("_smoke_frontend_api.py", "前端全部 GET 接口巡检", False),
    ("_verify_persons_collision.py", "重点人员碰撞比对（含停用排除反断言）", False),
    ("_verify_freeze_executor.py", "止付冻结执行器字段兼容+审批门控+端到端", True),
    ("_verify_review_flow.py", "HITL 复核流程+状态门控（防结论被覆盖）", True),
    ("_verify_alert_flow.py", "预警处置状态门控（防处置时间被覆盖）", False),
    ("_verify_demo_reset.py", "演示数据一键复位（权限/确认串/幂等）", False),
    ("_verify_merge_panel.py", "并案建议面板（列表/过滤/驳回/鉴权）", True),
    ("_verify_seed_api.py", "脱敏数据 API 可见性与覆盖率", False),
    ("_verify_chat_memory.py", "会话记忆持久化（Redis 真实路径）", True),
    ("_e2e_chat_memory.py", "会话记忆持久化路由层 E2E + 侧边栏契约", True),
]

# 汇总时从各脚本尾部抓取"结果"行
RESULT_HINTS = ("结果", "全部通过", "结果:", "全部不变量成立")


def extract_summary(text: str) -> str:
    """从脚本输出里抓一行结果摘要。"""
    for line in reversed(text.splitlines()):
        s = line.strip()
        if not s:
            continue
        if "通过" in s or "失败" in s or "异常" in s:
            return s
    return "(未捕获到结果行)"


def run_one(script: str, desc: str) -> tuple:
    path = BACKEND / script
    if not path.exists():
        return script, desc, None, "脚本不存在", 0.0

    t0 = time.time()
    try:
        proc = subprocess.run(
            [PYTHON, "-u", str(path)],
            cwd=str(BACKEND),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=600,
        )
        out = (proc.stdout or "") + (proc.stderr or "")
        return script, desc, proc.returncode, extract_summary(out), time.time() - t0
    except subprocess.TimeoutExpired:
        return script, desc, 1, "超时（>600s）", time.time() - t0
    except Exception as e:  # noqa: BLE001
        return script, desc, 1, f"执行异常：{e}", time.time() - t0


def main() -> int:
    filters = sys.argv[1:]
    suite = [s for s in SUITE
             if not filters or any(f.lower() in s[0].lower() for f in filters)]

    if not suite:
        print(f"没有匹配的脚本。可用关键词：{', '.join(s[0] for s in SUITE)}")
        return 1

    print("=" * 78)
    print("FraudLens 回归验证")
    print(f"Python: {PYTHON}")
    print(f"计划执行 {len(suite)} 个脚本")
    print("=" * 78)
    results = []
    for i, (script, desc, _side) in enumerate(suite, 1):
        print(f"\n[{i}/{len(suite)}] {script} — {desc}")
        print("-" * 78)
        script, desc, code, summary, cost = run_one(script, desc)
        ok = code == 0
        results.append((script, desc, ok, summary, cost, code))
        print(f"  {'PASS' if ok else 'FAIL'}  {summary}   （{cost:.1f}s）")

    print("\n" + "=" * 78)
    print("汇总")
    print("=" * 78)
    width = max(len(r[0]) for r in results)
    passed = sum(1 for r in results if r[2])
    for script, desc, ok, summary, cost, code in results:
        print(f"  [{'PASS' if ok else 'FAIL'}] {script:<{width}}  {summary}  ({cost:.1f}s)")

    print("-" * 78)
    print(f"共 {len(results)} 个脚本：{passed} 通过 / {len(results) - passed} 失败")
    if passed != len(results):
        print("\n失败脚本：")
        for script, _d, ok, summary, _c, code in results:
            if not ok:
                print(f"  - {script}（退出码 {code}）：{summary}")
    print("=" * 78)
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
