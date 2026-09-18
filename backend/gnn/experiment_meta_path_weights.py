"""
元路径语义注意力权重分析实验。
训练 HAN 后提取 semantic_attention 的 beta_i，统计各 cross 下各元路径平均权重。
用于论文 §3.2 / §4.x 元路径重要性分析。
"""
import json
import os
import sys
import numpy as np
import torch

BACKEND = os.path.dirname(os.path.abspath(__file__))
for p in (BACKEND, os.path.dirname(BACKEND)):
    if p not in sys.path:
        sys.path.insert(0, p)

import eval_framework as ef
import graph_builder as gb_mod
import han_model
import baselines_hetero as bh

META_PATH_NAMES = [
    "case_account_case",
    "case_perpetrator_case",
    "case_type_case",
    "case_city_case",
    "case_text_case",
]


def extract_betas(model, feat_t, meta_t):
    """eval 下跑一次 forward，通过 hook 捕获语义注意力 beta。"""
    captured = []
    sem_attn = model.han.semantic_attention
    orig_forward = sem_attn.forward

    def patched_forward(z):
        # 复现 SemanticAttention 内部计算并截获 beta
        w = sem_attn.project(z).mean(dim=1)        # [P, 1]
        beta = torch.softmax(w, dim=0)             # [P, 1]
        captured.append(beta.detach().cpu().numpy().flatten())
        b = beta.unsqueeze(-1).expand(z.shape[0], z.shape[1], z.shape[2])
        return (b * z).sum(dim=0)

    sem_attn.forward = patched_forward
    model.eval()
    with torch.no_grad():
        _ = model.han(feat_t, meta_t)
    sem_attn.forward = orig_forward
    return captured[0]


def run_one(cross, seed):
    cases, accounts_tx, gt = ef.load_dataset(
        seed=seed, n_gangs=5, cases_per_gang=8, cross=cross
    )
    builder = gb_mod.FraudGraphBuilder(use_db=False, use_cache=False, use_text_channel=True)
    G = builder.build_graph(cases, accounts_tx=accounts_tx)
    features = builder.get_node_features()
    meta_np = builder.get_meta_path_adjacency()
    if features is None or len(features) < 3 or not meta_np:
        raise RuntimeError("failed to build graph inputs")
    feat_t = torch.as_tensor(np.asarray(features, dtype=np.float32))
    meta_t = {k: torch.as_tensor(np.asarray(v, dtype=np.float32)) for k, v in meta_np.items()}

    in_dim = feat_t.shape[1]
    n_true = len(set(gt.values()))
    han = han_model.FraudHAN(
        in_dim=in_dim, hidden_dim=64, embedding_dim=32,
        num_classes=10, num_heads=4, num_layers=2
    )
    # 与主实验协议完全一致：GraphCL 自监督预训练（lr=0.001, 100 epoch），
    # 无监督微调，提取语义注意力权重（不引入任何 ground-truth 监督信号）
    trainer = han_model.GraphCLTrainer(han, temperature=0.5, learning_rate=0.001, device="cpu")
    trainer.pretrain(feat_t, meta_t, num_epochs=100, batch_size=min(256, feat_t.shape[0]))

    betas = extract_betas(han, feat_t, meta_t)
    return dict(zip(META_PATH_NAMES, betas.tolist()))


def main():
    crosses = [0.0, 0.2, 0.4]
    seeds = [42, 7, 123, 256, 1024]
    records = []
    for cross in crosses:
        for seed in seeds:
            betas = run_one(cross, seed)
            records.append({"cross": cross, "seed": seed, "betas": betas})
            print(f"cross={cross} seed={seed} betas={betas}")

    summary = {}
    for cross in crosses:
        rows = [r for r in records if abs(r["cross"] - cross) < 1e-9]
        arr = np.array([[r["betas"][mp] for mp in META_PATH_NAMES] for r in rows])
        summary[str(cross)] = {
            "mean": {mp: float(arr[:, i].mean()) for i, mp in enumerate(META_PATH_NAMES)},
            "std": {mp: float(arr[:, i].std(ddof=1)) for i, mp in enumerate(META_PATH_NAMES)},
            "n": len(rows),
        }

    out = {
        "meta_paths": META_PATH_NAMES,
        "records": records,
        "summary": summary,
        "honest_note": (
            "本实验在合成案件数据上训练 HAN 并提取语义注意力 beta_i，"
            "用于验证元路径重要性排序。结果为合成数据上的可解释性分析，"
            "不构成真实警务数据验证。"
        ),
    }
    with open(os.path.join(BACKEND, "meta_path_weights.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print("\n=== 元路径语义注意力 beta_i 平均值 (5 seeds) ===")
    print(f"{'元路径':<22s} {'cross=0.0':>12s} {'cross=0.2':>12s} {'cross=0.4':>12s}")
    for mp in META_PATH_NAMES:
        vals = [summary[str(c)]["mean"][mp] for c in crosses]
        print(f"{mp:<22s} {vals[0]:12.4f} {vals[1]:12.4f} {vals[2]:12.4f}")
    print("saved: meta_path_weights.json")


if __name__ == "__main__":
    main()
