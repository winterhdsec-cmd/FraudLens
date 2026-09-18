"""
实验 ③：经验加权置信度门控 —— 系数敏感性分析（诚实重命名：原"客观置信度"实为
手工设定的 4 因子启发式加权，此处更名为"经验加权/启发式置信度门控"）

- 构造代表性团伙集合（真团伙应冻结 vs 假团伙不应冻结，含"高规模无回流"难例）。
- 在多种权重方案与蒙特卡洛扰动下，报告 误冻率 / 漏冻率 的稳健性。
- 诚实结论：手工权重对噪声稳健，但本质是启发式，无法判别"高规模无资金回流"假团伙，
  故论文将"引入强化学习/监督学习优化门控系数"列为未来工作。
输出：backend/gnn/gating_sensitivity_results.json
"""
import json, os
import numpy as np

BACKEND = os.path.dirname(os.path.abspath(__file__))

# 4 因子：规模、金额、账户数、资金回流闭环标志（归一化 0~1；回流为 0/1）
GATE = 0.5

# 代表性团伙：(名称, [scale, amount, acc, reflux], 真值应冻结?)
GANGS = [
    ("G1_true",  [0.90, 0.80, 0.70, 1], True),
    ("G2_true",  [0.70, 0.60, 0.50, 1], True),
    ("G3_true",  [0.60, 0.50, 0.40, 0], True),
    ("F1_false_highscale_noreflux", [0.80, 0.90, 0.80, 0], False),  # 已知难例
    ("F2_false_low", [0.20, 0.10, 0.10, 0], False),
]

SCHEMES = {
    "current(0.30/0.20/0.20/0.30)": [0.30, 0.20, 0.20, 0.30],
    "uniform(0.25x4)":              [0.25, 0.25, 0.25, 0.25],
    "scale_heavy(0.40/0.15/0.15/0.30)": [0.40, 0.15, 0.15, 0.30],
    "reflux_heavy(0.20/0.15/0.15/0.50)": [0.20, 0.15, 0.15, 0.50],
    "amount_heavy(0.20/0.40/0.20/0.20)": [0.20, 0.40, 0.20, 0.20],
    "acc_heavy(0.20/0.20/0.40/0.20)":     [0.20, 0.20, 0.40, 0.20],
}


def decide(feats, w):
    conf = float(np.dot(w, feats))
    return conf >= GATE, conf


def metrics_for_weights(w):
    false_freeze = 0   # 不应冻结却被冻结
    miss = 0           # 应冻结却未冻结
    total = len(GANGS)
    for _, feats, truth in GANGS:
        freeze, _ = decide(feats, w)
        if freeze and not truth:
            false_freeze += 1
        if (not freeze) and truth:
            miss += 1
    return {
        "false_freeze_rate": round(false_freeze / total, 4),
        "miss_rate": round(miss / total, 4),
        "false_freeze_n": false_freeze,
        "miss_n": miss,
        "total": total,
    }


def main():
    schemes_out = {}
    for name, w in SCHEMES.items():
        confs = {g[0]: round(float(np.dot(w, g[1])), 3) for g in GANGS}
        schemes_out[name] = {"weights": w, "gang_confidences": confs,
                             "metrics": metrics_for_weights(w)}

    # 蒙特卡洛扰动：每个权重 Uniform(-0.05,0.05) 后归一化，200 次
    rng = np.random.RandomState(0)
    ff_rates, miss_rates = [], []
    for _ in range(200):
        w = np.array([0.30, 0.20, 0.20, 0.30]) + rng.uniform(-0.05, 0.05, size=4)
        w = np.clip(w, 0.01, None)
        w = w / w.sum()
        m = metrics_for_weights(w)
        ff_rates.append(m["false_freeze_rate"])
        miss_rates.append(m["miss_rate"])
    montecarlo = {
        "n_trials": 200,
        "false_freeze_rate_mean": round(float(np.mean(ff_rates)), 4),
        "false_freeze_rate_std": round(float(np.std(ff_rates)), 4),
        "miss_rate_mean": round(float(np.mean(miss_rates)), 4),
        "miss_rate_std": round(float(np.std(miss_rates)), 4),
        "note": "手工权重 ±0.05 扰动下，误冻率/漏冻率波动很小，说明系数对噪声稳健；"
                "但绝对水平（尤其高规模无回流难例）由权重结构决定，非自适应学习所得。",
    }

    # 阈值灵敏性：在 current 权重下扫描 gate ∈ [0.30,0.40,0.50,0.60,0.70] 的 误冻率/漏冻率 权衡
    w_cur = np.array([0.30, 0.20, 0.20, 0.30])
    threshold_sweep = []
    for g in [0.30, 0.40, 0.50, 0.60, 0.70]:
        ff = sum(1 for _, feats, truth in GANGS
                 if (np.dot(w_cur, feats) >= g) and not truth)
        ms = sum(1 for _, feats, truth in GANGS
                 if (np.dot(w_cur, feats) < g) and truth)
        threshold_sweep.append({"gate": g, "false_freeze_rate": round(ff / len(GANGS), 4),
                                "miss_rate": round(ms / len(GANGS), 4),
                                "false_freeze_n": ff, "miss_n": ms})

    out = {
        "config": {"gate": GATE, "gangs": [g[0] for g in GANGS],
                   "note": "经验加权(启发式)置信度门控系数敏感性；非真实数据验证，仅结构稳健性分析"},
        "schemes": schemes_out,
        "montecarlo_perturbation": montecarlo,
        "threshold_sweep_current_weights": threshold_sweep,
    }
    with open(os.path.join(BACKEND, "gating_sensitivity_results.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print("=== 各权重方案下的门控表现 ===")
    for name, s in schemes_out.items():
        m = s["metrics"]
        print(f"  {name:38s} 误冻率={m['false_freeze_rate']} 漏冻率={m['miss_rate']} 权重={s['weights']}")
    print("\n=== 蒙特卡洛扰动(±0.05, 200次) ===")
    print(f"  误冻率={montecarlo['false_freeze_rate_mean']}±{montecarlo['false_freeze_rate_std']}  "
          f"漏冻率={montecarlo['miss_rate_mean']}±{montecarlo['miss_rate_std']}")
    print("\n=== 阈值扫描(current 权重) ===")
    for r in threshold_sweep:
        print(f"  gate={r['gate']}  误冻率={r['false_freeze_rate']}  漏冻率={r['miss_rate']}")
    print("\n结论：", montecarlo["note"])


if __name__ == "__main__":
    main()
