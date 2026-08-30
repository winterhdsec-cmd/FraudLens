"""
P3 半监督 HAN 正式实验（多 seed × 多难度，产出可申报/可入表的干净数据）

背景
----
v5 探针（真 BGE + 确定性 hash）证实：纯 GraphCL 自监督 HAN 在噪声/话术碰撞
场景大幅退化（P2 -0.309），自监督目标与团伙发现任务不对齐。本实验验证
"资金链+话术共识伪标签 → GNN 半监督" 是否能反转，并对比三种出牌方式：
  - hybrid  : 锚点案件直接用伪标签，仅非锚点案件用 GNN argmax（F1 下限=锚点质量）
  - argmax  : 全部案件用微调后分类头 argmax
  - emb_km  : 微调后嵌入 + KMeans(真实团伙数)

多 seed 报告 mean±std，满足申报书/论文可复现要求。

用法
----
    python experiment_semi.py                 # 3 seed × 6 预设
    python experiment_semi.py --seeds 42      # 单 seed 快测
    python experiment_semi.py --out semi_x.json
"""
import argparse
import json
import os
import statistics
import sys
import time
from typing import Any, Dict, List

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import eval_framework as ef  # noqa: E402

# 六种难度预设（与探针 v5 对齐）
PRESETS: List[Dict[str, Any]] = [
    {"name": "P0_clean_40", "desc": "干净 40 案",
     "kwargs": dict(n_gangs=5, cases_per_gang=8)},
    {"name": "P1_light_40", "desc": "轻噪 40 案",
     "kwargs": dict(n_gangs=5, cases_per_gang=8,
                    cross_gang_account_share=0.05, intra_share_prob=0.9, attr_noise=0.1)},
    {"name": "P2_hard_40", "desc": "重噪 40 案",
     "kwargs": dict(n_gangs=5, cases_per_gang=8,
                    cross_gang_account_share=0.15, intra_share_prob=0.75, attr_noise=0.25)},
    {"name": "P3_200", "desc": "轻噪 200 案",
     "kwargs": dict(n_gangs=10, cases_per_gang=20,
                    cross_gang_account_share=0.05, intra_share_prob=0.9, attr_noise=0.1)},
    {"name": "P4_collide_40", "desc": "话术强碰撞 40 案",
     "kwargs": dict(n_gangs=5, cases_per_gang=8, shared_script_pool=2)},
    {"name": "P5_collide_noise", "desc": "强碰撞+轻噪 40 案",
     "kwargs": dict(n_gangs=5, cases_per_gang=8, shared_script_pool=2,
                    cross_gang_account_share=0.05, intra_share_prob=0.9, attr_noise=0.1)},
]


def _mean_std(vals: List[float]):
    if not vals:
        return 0.0, 0.0
    m = statistics.mean(vals)
    s = statistics.pstdev(vals) if len(vals) > 1 else 0.0
    return round(m, 4), round(s, 4)


def run_one(preset: Dict[str, Any], seed: int) -> Dict[str, Any]:
    """跑单个 (预设, seed)：产出各方法 F1 字典。"""
    cases, tx, gt = ef.sd_mod.generate_synthetic_dataset(seed=seed, **preset["kwargs"])
    n_true = len(set(gt.values()))
    out: Dict[str, Any] = {"seed": seed, "n_true": n_true, "n_cases": len(cases)}

    # 纯自监督 HAN（对照）
    p_han = ef.baseline_gnn_han(cases, tx, n_true, epochs=60)
    out["HAN-selfsup"] = (ef.compute_metrics(gt, p_han)["f1"]
                          if "__error__" not in p_han else None)

    # 半监督：hybrid
    p_hy = ef.baseline_gnn_han_semi(cases, tx, epochs=60, hybrid=True)
    out["HAN-semi-hybrid"] = (ef.compute_metrics(gt, p_hy)["f1"]
                              if "__error__" not in p_hy else None)

    # 半监督：纯 argmax（关 hybrid）
    p_am = ef.baseline_gnn_han_semi(cases, tx, epochs=60, hybrid=False)
    out["HAN-semi-argmax"] = (ef.compute_metrics(gt, p_am)["f1"]
                              if "__error__" not in p_am else None)

    # 参照：资金链（规则上界）+ KMeans 聚类基线
    from sklearn.cluster import KMeans
    from sklearn.preprocessing import StandardScaler
    p_fund = ef.baseline_current_system(cases, tx, use_fund=True)
    out["fund(ref)"] = ef.compute_metrics(gt, p_fund)["f1"]
    X, ids = ef.case_feature_matrix(cases)
    k = ef._estimate_n_clusters(X)
    p_km = {cid: int(l) for cid, l in zip(ids, KMeans(n_clusters=k, random_state=0, n_init=10).fit_predict(X))}
    out["KMeans(ref)"] = ef.compute_metrics(gt, p_km)["f1"]

    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", default="42,7,2024",
                    help="逗号分隔的种子列表")
    ap.add_argument("--presets", default="",
                    help="逗号分隔的预设名过滤（默认全部）")
    ap.add_argument("--out", default="experiment_semi_results.json")
    ap.add_argument("--resume", action="store_true",
                    help="若 out 文件已存在则载入已有结果，跳过已完成的 (preset,seed)")
    args = ap.parse_args()
    seeds = [int(s) for s in args.seeds.split(",") if s.strip()]
    presets = [p for p in PRESETS
               if not args.presets or p["name"] in args.presets.split(",")]

    out_path = os.path.join(HERE, args.out)
    all_results: Dict[str, Any] = {"meta": {
        "seeds": seeds, "presets": [p["name"] for p in presets],
        "ts": time.strftime("%Y-%m-%d %H:%M:%S")}, "raw": {}}

    # 断点续跑：载入既有结果，已完成的 (preset,seed) 不再重跑
    if args.resume and os.path.exists(out_path):
        try:
            with open(out_path, "r", encoding="utf-8") as f:
                old = json.load(f)
            for name in all_results["meta"]["presets"]:
                old_rows = old.get("raw", {}).get(name, [])
                keep = [r for r in old_rows if r["seed"] in seeds]
                if keep:
                    all_results["raw"][name] = keep
            print(f"(resume) 已载入 {out_path}，将跳过已完成的 preset-seed，仅补跑缺失项\n")
        except Exception as e:  # noqa: BLE001
            print(f"(resume 失败，从头跑) 无法读入 {args.out}: {e}\n")

    methods = ["KMeans(ref)", "fund(ref)", "HAN-selfsup",
               "HAN-semi-hybrid", "HAN-semi-argmax"]

    print(f"{'='*90}")
    print(f"半监督 HAN 实验：{len(seeds)} seed × {len(presets)} 预设，方法 = {methods}")
    print(f"{'='*90}\n")

    def save():
        # 增量落盘：每个 seed 完成后即写盘，中断最多丢失当前一个 seed
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(all_results, f, ensure_ascii=False, indent=2)

    for preset in presets:
        name = preset["name"]
        done = {r["seed"]: r for r in all_results["raw"].get(name, [])}
        per_seed = []
        for seed in seeds:
            if seed in done:                      # resume：该 seed 已有结果，跳过
                per_seed.append(done[seed])
                print(f"[{name}] seed={seed}  (resume，跳过)")
                continue
            t0 = time.time()
            r = run_one(preset, seed)
            r["_secs"] = round(time.time() - t0, 1)
            per_seed.append(r)
            all_results["raw"][name] = per_seed
            save()                                # 关键：每跑完一个 seed 立即落盘
            print(f"[{name}] seed={seed}  "
                  + "  ".join(f"{m}={r[m]:.4f}" if r[m] is not None else f"{m}=ERR"
                              for m in methods)
                  + f"  ({r['_secs']}s)")
        all_results["raw"][name] = per_seed

        # 汇总 mean±std（基于已完成的 seed；resume 模式下可能部分完成）
        n_done = len(per_seed)
        tag = "" if n_done == len(seeds) else f"（仅 {n_done}/{len(seeds)} seed）"
        print(f"  → {name} 汇总{tag}:")
        for m in methods:
            vals = [x[m] for x in per_seed if x[m] is not None]
            mu, sd = _mean_std(vals)
            print(f"      {m:<20} {mu:.4f} ± {sd:.4f}")
        print()

    print(f"结果已增量写入: {out_path}")

    # 最终判断表：hybrid vs argmax 谁更稳
    print(f"\n{'='*90}")
    print("最终判断：各预设下最优半监督出牌方式（跨 seed mean）")
    print(f"{'='*90}")
    print(f"{'预设':<22}{'selfsup':>10}{'hybrid':>10}{'argmax':>10}{'fund':>10}{'最优':>16}")
    for preset in presets:
        per = all_results["raw"][preset["name"]]
        means = {}
        for m in ["HAN-selfsup", "HAN-semi-hybrid", "HAN-semi-argmax", "fund(ref)"]:
            vals = [x[m] for x in per if x[m] is not None]
            means[m] = _mean_std(vals)[0]
        best = max(["HAN-selfsup", "HAN-semi-hybrid", "HAN-semi-argmax"],
                   key=lambda m: means[m])
        row = f"{preset['name']:<22}{means['HAN-selfsup']:>10.4f}{means['HAN-semi-hybrid']:>10.4f}{means['HAN-semi-argmax']:>10.4f}{means['fund(ref)']:>10.4f}{best:>16}"
        print(row)


if __name__ == "__main__":
    main()
