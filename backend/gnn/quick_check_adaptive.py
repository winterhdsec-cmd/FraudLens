"""自适应 k 门控端到端快速验证：单 seed 跑 P1/P3 半监督，与旧基线对比。"""
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import eval_framework as ef

PRESETS = [
    {"name": "P1_light_40", "desc": "轻噪 40 案", "baseline_hybrid": 0.5821,
     "kwargs": dict(n_gangs=5, cases_per_gang=8,
                    cross_gang_account_share=0.05, intra_share_prob=0.9, attr_noise=0.1)},
    {"name": "P3_200", "desc": "轻噪 200 案", "baseline_hybrid": 0.3816,
     "kwargs": dict(n_gangs=10, cases_per_gang=20,
                    cross_gang_account_share=0.05, intra_share_prob=0.9, attr_noise=0.1)},
]

SEED = 42


def main():
    for p in PRESETS:
        cases, tx, gt = ef.sd_mod.generate_synthetic_dataset(seed=SEED, **p["kwargs"])
        n_true = len(set(gt.values()))
        print(f"\n===== {p['name']} ({p['desc']})  seed={SEED}  n_true={n_true} =====")

        anchors = ef._consensus_anchor_labels(cases, tx)
        if anchors is None:
            print("  锚点不足，门控拒出牌（None）")
            continue
        n_anchor = len(anchors)
        n_case = len(cases)
        nclu = len(set(anchors.values()))
        print(f"  锚点案件={n_anchor}/{n_case}  覆盖={n_anchor/n_case:.3f}  锚点簇={nclu}")

        p_hy = ef.baseline_gnn_han_semi(cases, tx, epochs=60, hybrid=True)
        f1_hy = ef.compute_metrics(gt, p_hy)["f1"] if "__error__" not in p_hy else None
        p_am = ef.baseline_gnn_han_semi(cases, tx, epochs=60, hybrid=False)
        f1_am = ef.compute_metrics(gt, p_am)["f1"] if "__error__" not in p_am else None

        print(f"  hybrid = {f1_hy:.4f}  (旧基线 {p['baseline_hybrid']:.4f})  "
              f"delta {f1_hy - p['baseline_hybrid']:+.4f}")
        print(f"  argmax = {f1_am:.4f}")


if __name__ == "__main__":
    main()
