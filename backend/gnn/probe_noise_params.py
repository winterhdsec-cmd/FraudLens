"""
第 0 步：噪声参数探针（零改动验证）

目的
----
验证"加噪声后，KMeans / HDBSCAN / Semantic 三个基线是否会分化"。

当前问题：三个独立基线在干净合成数据上给出逐位相同的指标
（NMI 0.8973 / ARI 0.8340 / F1 0.8615），无法用于申报与论文。

假设：根因是合成数据过于干净（cross=0, intra=1.0, attr_noise=0），
同团伙案件的类型/城市/账户完全一致，导致任何方法都给出相同划分。

本脚本不修改任何现有代码，仅复用 eval_framework.run_all() 已透传的
cross / intra / attr_noise / n_gangs / cases_per_gang 参数做扫描。

用法
----
    # 只跑干净基线，验证脚本可跑通并测量耗时
    python probe_noise_params.py --quick

    # 跑完整探针网格
    python probe_noise_params.py

    # 指定输出文件
    python probe_noise_params.py --out my_probe.json

环境
----
需 torch + hdbscan + transformers（backend/venv 缺这些包），
请用 C:\\Users\\hd\\AppData\\Local\\Programs\\Python\\Python310\\python.exe
"""
import argparse
import json
import os
import sys
import time
from typing import Any, Dict, List

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import eval_framework as ef  # noqa: E402  (需在 sys.path 设置后导入)


# 探针网格：从"干净"逐级加噪，最后一级同时扩规模
PROBE_GRID: List[Dict[str, Any]] = [
    {
        "name": "P0_clean_40",
        "desc": "干净基线（复现当前 40 案设定，用于对照）",
        "kwargs": dict(seed=42, n_gangs=5, cases_per_gang=8,
                       cross=0.0, intra=1.0, attr_noise=0.0),
    },
    {
        "name": "P1_noise_40",
        "desc": "同规模轻噪：跨团伙共享账户 5% / 团内共享率 90% / 属性噪声 10%",
        "kwargs": dict(seed=42, n_gangs=5, cases_per_gang=8,
                       cross=0.05, intra=0.9, attr_noise=0.1),
    },
    {
        "name": "P2_noise_40_hard",
        "desc": "同规模重噪：跨团伙共享 15% / 团内共享率 75% / 属性噪声 25%",
        "kwargs": dict(seed=42, n_gangs=5, cases_per_gang=8,
                       cross=0.15, intra=0.75, attr_noise=0.25),
    },
    {
        "name": "P3_noise_200",
        "desc": "扩规模加噪：10 团伙 x 20 案 = 200（卡在 GraphCL 256 上限内）",
        "kwargs": dict(seed=42, n_gangs=10, cases_per_gang=20,
                       cross=0.05, intra=0.9, attr_noise=0.1),
    },
    {
        "name": "P4_collide_40",
        "desc": "强模板碰撞：5 团伙共用 2 种话术（黑产话术包流通）",
        "kwargs": dict(seed=42, n_gangs=5, cases_per_gang=8,
                       cross=0.0, intra=1.0, attr_noise=0.0,
                       script_pool=2),
    },
    {
        "name": "P5_collide_noise_40",
        "desc": "强碰撞+轻噪：话术池 2 + 跨团伙 5% / 团内 90% / 属性噪声 10%",
        "kwargs": dict(seed=42, n_gangs=5, cases_per_gang=8,
                       cross=0.05, intra=0.9, attr_noise=0.1,
                       script_pool=2),
    },
]

# 原始三个纯聚类基线（用于判断"三基线雷同"这个老问题是否解决）
BASELINE_KEYS = ["KMeans", "HDBSCAN-only", "Semantic"]
# 新增：话术版语义基线（检验话术文本本身的判别力）
SCRIPT_KEY = "Semantic(script)"
# 参与分化判定的全部聚类基线
CLUSTER_KEYS = BASELINE_KEYS + [SCRIPT_KEY]
# 完整方法列表（能跑出来的都会打印）
ALL_KEYS = CLUSTER_KEYS + [
    "CurrentSystem(fund)", "CurrentGNN(GraphSAGE)", "CurrentGNN(HAN-true)"
]


def _fmt(v: Any, width: int = 7) -> str:
    """把指标格式化成定宽字符串，None 或缺失显示为 '-'"""
    if v is None:
        return "-".rjust(width)
    return f"{float(v):.4f}".rjust(width)


def three_baselines_diverged(result: Dict[str, Any]) -> bool:
    """判断各聚类基线是否已经分化。

    判定：参与比较的聚类基线 F1（4 位小数）不全相等 -> 已分化。
    注意：返回值同时反映"原始三基线"是否分化（老问题是否解决）。
    """
    bl = result.get("baselines", {})
    vals = []
    for k in CLUSTER_KEYS:
        if k in bl and "f1" in bl[k]:
            vals.append(round(float(bl[k]["f1"]), 4))
    if len(vals) < 2:
        return False  # 数据不足，不算分化
    return len(set(vals)) > 1


def run_one(cfg: Dict[str, Any]) -> Dict[str, Any]:
    """跑单组配置，返回结果 + 耗时"""
    print(f"\n{'=' * 78}")
    print(f"[{cfg['name']}] {cfg['desc']}")
    print(f"参数: {cfg['kwargs']}")
    print("-" * 78)
    t0 = time.time()
    try:
        res = ef.run_all(**cfg["kwargs"])
        elapsed = time.time() - t0
        res["_probe"] = {
            "name": cfg["name"],
            "desc": cfg["desc"],
            "params": cfg["kwargs"],
            "elapsed_sec": round(elapsed, 2),
            "diverged": three_baselines_diverged(res),
        }
        print(f"耗时 {elapsed:.1f}s   "
              f"数据集: {res['dataset']['n_cases']} 案 / "
              f"{res['dataset']['n_gangs']} 团伙")
        return res
    except Exception as e:
        elapsed = time.time() - t0
        print(f"!! 失败 ({elapsed:.1f}s): {type(e).__name__}: {e}")
        return {
            "_probe": {
                "name": cfg["name"],
                "desc": cfg["desc"],
                "params": cfg["kwargs"],
                "elapsed_sec": round(elapsed, 2),
                "error": f"{type(e).__name__}: {e}",
                "diverged": False,
            }
        }


def print_summary(results: List[Dict[str, Any]]) -> None:
    """打印跨配置的对比表，重点是三基线是否分化"""
    print(f"\n\n{'=' * 82}")
    print("汇总：聚类基线分化检查（F1）")
    print("  KMeans / HDBSCAN / Sem(attr)=结构化字段 / Sem(script)=话术文本")
    print("=" * 82)
    header = (f"{'配置':<16}{'KMeans':>9}{'HDBSCAN':>10}"
              f"{'Sem(attr)':>11}{'Sem(script)':>13}{'分化?':>8}")
    print(header)
    print("-" * 82)
    for res in results:
        p = res.get("_probe", {})
        name = p.get("name", "?")
        if "error" in p:
            print(f"{name:<16}{'-- 失败 --':>51}")
            continue
        bl = res.get("baselines", {})
        row = (f"{name:<16}"
               f"{_fmt(bl.get('KMeans', {}).get('f1'), 9)}"
               f"{_fmt(bl.get('HDBSCAN-only', {}).get('f1'), 10)}"
               f"{_fmt(bl.get('Semantic', {}).get('f1'), 11)}"
               f"{_fmt(bl.get(SCRIPT_KEY, {}).get('f1'), 13)}")
        row += f"{'YES' if p.get('diverged') else 'NO':>8}"
        print(row)

    print(f"\n{'=' * 78}")
    print("完整基线对比（F1）")
    print("=" * 78)
    for res in results:
        p = res.get("_probe", {})
        if "error" in p:
            continue
        bl = res.get("baselines", {})
        print(f"\n[{p['name']}] {p['desc']}")
        for k in ALL_KEYS:
            if k in bl:
                m = bl[k]
                print(f"  {k:<26} NMI={_fmt(m.get('nmi'))} "
                      f"ARI={_fmt(m.get('ari'))} F1={_fmt(m.get('f1'))} "
                      f"clusters={m.get('n_clusters')}")

    # 消融增益（判断两项消融是否仍为 0）
    print(f"\n{'=' * 78}")
    print("消融增益")
    print("=" * 78)
    for res in results:
        p = res.get("_probe", {})
        ab = res.get("ablation", {})
        if not ab:
            continue
        print(f"[{p['name']}] "
              f"fund_chain_gain_f1={ab.get('fund_chain_gain_f1', '-')}  "
              f"dual_channel_gain_f1={ab.get('dual_channel_gain_f1', '-')}")

    # 关键判断：GNN 相对纯聚类到底有没有优势（决定申报叙事能否成立）
    print(f"\n{'=' * 82}")
    print("关键判断：HAN 是否优于全部聚类基线")
    print("=" * 82)
    for res in results:
        p = res.get("_probe", {})
        bl = res.get("baselines", {})
        if "error" in p or "CurrentGNN(HAN-true)" not in bl:
            continue
        han = bl["CurrentGNN(HAN-true)"]["f1"]
        cl = {k: bl[k]["f1"] for k in CLUSTER_KEYS if k in bl}
        if not cl:
            continue
        best_k = max(cl, key=lambda k: cl[k])
        best_v = cl[best_k]
        verdict = "优于" if han > best_v else "不及"
        print(f"[{p['name']:<16}] HAN={han:.4f}  "
              f"vs 最佳聚类={best_k}({best_v:.4f})  "
              f"差值={han - best_v:+.4f}  -> {verdict}")


def main() -> int:
    ap = argparse.ArgumentParser(description="噪声参数探针（零改动验证）")
    ap.add_argument("--quick", action="store_true",
                    help="只跑 P0 干净基线，用于测通断与耗时")
    ap.add_argument("--out", default="probe_noise_results.json",
                    help="结果输出文件名（默认 probe_noise_results.json）")
    args = ap.parse_args()

    grid = PROBE_GRID[:1] if args.quick else PROBE_GRID
    print(f"探针配置数: {len(grid)}  (--quick={args.quick})")

    results = [run_one(cfg) for cfg in grid]

    print_summary(results)

    out_path = os.path.join(HERE, args.out)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n结果已写入: {out_path}")

    # 结论提示
    diverged = [r["_probe"]["name"] for r in results
                if r.get("_probe", {}).get("diverged")]
    if diverged:
        print(f"\n结论: 加噪后三基线已分化于 {diverged}")
        print("      -> 无需新增难度因子，可直接进入业务指标 + 难度梯度 + 出图")
    else:
        print("\n结论: 加噪后三基线仍未分化")
        print("      -> 需要新增难度因子（shared_script_pool / role_heterogeneity 等）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
