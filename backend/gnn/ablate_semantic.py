"""HAN 语义注意力消融：learn（学习元路径权重）vs mean（固定等权平均）。

验证"语义注意力是否真实生效"：若 learn 相对 mean 无 F1 优势且学到的 β≈等权，
则语义注意力实际是惰性的（诚实结论，防申报/论文夸大）；若有优势则坐实机制。
同时输出学到的 β 分布（哪些元路径被加权），供论文机制解释。
"""
import json
import os
import sys
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import eval_framework as ef

PRESETS = [
    {"name": "P0_clean_40", "kwargs": dict(n_gangs=5, cases_per_gang=8)},
    {"name": "P1_light_40", "kwargs": dict(n_gangs=5, cases_per_gang=8,
                                          cross_gang_account_share=0.05, intra_share_prob=0.9, attr_noise=0.1)},
    {"name": "P2_hard_40", "kwargs": dict(n_gangs=5, cases_per_gang=8,
                                          cross_gang_account_share=0.15, intra_share_prob=0.75, attr_noise=0.25)},
    {"name": "P3_200", "kwargs": dict(n_gangs=10, cases_per_gang=20,
                                      cross_gang_account_share=0.05, intra_share_prob=0.9, attr_noise=0.1)},
    {"name": "P4_collide_40", "kwargs": dict(n_gangs=5, cases_per_gang=8, shared_script_pool=2)},
    {"name": "P5_collide_noise", "kwargs": dict(n_gangs=5, cases_per_gang=8, shared_script_pool=2,
                                                cross_gang_account_share=0.05, intra_share_prob=0.9, attr_noise=0.1)},
]

META_PATH_NAMES = ["account", "perpetrator", "type", "city", "text"]
SEED = 42


def _beta_stats(beta):
    """β 非均匀度：max-min 与 std（越大说明学习到越强的元路径区分）。"""
    if not beta:
        return None
    import statistics
    return {"beta": [round(b, 4) for b in beta],
            "range": round(max(beta) - min(beta), 4),
            "std": round(statistics.pstdev(beta), 4)}


def main():
    results = []
    print(f"===== 语义注意力消融  seed={SEED}  模式 = learn(学习) / mean(等权) =====")
    for p in PRESETS:
        cases, tx, gt = ef.sd_mod.generate_synthetic_dataset(seed=SEED, **p["kwargs"])
        n_true = len(set(gt.values()))
        row = {"preset": p["name"], "n_cases": len(cases), "n_true": n_true}
        print(f"\n--- {p['name']}  n={len(cases)} n_true={n_true} ---")
        for mode in ["learn", "mean"]:
            t0 = time.time()
            pred = ef.baseline_gnn_han(cases, tx, n_true, epochs=60,
                                       semantic_attention_mode=mode)
            if "__error__" in pred:
                print(f"  {mode}: ERR {pred['__error__']}")
                row[mode] = None
                continue
            f1 = ef.compute_metrics(gt, pred)["f1"]
            bs = _beta_stats(pred.get("__beta__"))
            row[mode] = {"f1": round(f1, 4), "secs": round(time.time() - t0, 1)}
            if bs:
                row[mode]["beta_stats"] = bs
            print(f"  {mode}: f1={f1:.4f}  β={bs}")
        if row.get("learn") and row.get("mean"):
            row["delta_learn_minus_mean"] = round(
                row["learn"]["f1"] - row["mean"]["f1"], 4)
        results.append(row)

    out = {"seed": SEED, "meta_paths": META_PATH_NAMES, "results": results}
    path = os.path.join(HERE, "ablate_semantic.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"\n结果已写入: {path}")

    print("\n===== 汇总 =====")
    print(f"{'预设':<16}{'learn':>8}{'mean':>8}{'delta':>8}   β范围(std)")
    for r in results:
        lf = r.get("learn", {}).get("f1") if r.get("learn") else None
        mf = r.get("mean", {}).get("f1") if r.get("mean") else None
        dl = r.get("delta_learn_minus_mean")
        bs = (r.get("learn") or {}).get("beta_stats") or {}
        print(f"{r['preset']:<16}"
              f"{lf if lf is None else f'{lf:.4f}':>8}"
              f"{mf if mf is None else f'{mf:.4f}':>8}"
              f"{dl if dl is None else f'{dl:+.4f}':>8}"
              f"   {bs.get('range', '-')} ({bs.get('std', '-')})")


if __name__ == "__main__":
    main()
