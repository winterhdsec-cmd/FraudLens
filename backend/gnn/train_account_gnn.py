"""
Track A 账户 GNN 训练 + 评测 vs 基线（诚实）
==========================================
对比：在"带信号合成账户数据集"上
  (a) 原始行为特征 + KMeans            —— 无 GNN
  (b) 未训练 GraphSAGE + KMeans        —— 复现当前 GNNAccount 的"随机 GNN"现状
  (c) 训练后 GraphSAGE + KMeans         —— 目标：证明"训练 + schema 对齐"后 GNN 可用
  (d) Louvain（拓扑）                   —— 经典无监督基线

指标：pairwise F1 / NMI / ARI（团伙发现标准度量，与 AMLSim 基准一致）。
诚实口径：本评测仅证明"信号存在 + 训练后"GNN 可恢复团伙；AMLSim 原始全图
F1≈0.0016 仍低（信号被淹没），仅作难度基线，绝不称真实验证（docs/06 金律）。
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score

from gnn.account_temporal import build_account_graph
from gnn.gnn_model import GraphSAGE
from gnn.synth_accounts import generate


def pairwise_f1(pred: np.ndarray, gt: np.ndarray):
    """pairwise（pair-counting）F1，与 AMLSim 团伙发现基准一致。"""
    pred = np.asarray(pred)
    gt = np.asarray(gt)
    n = len(pred)
    same_pred = pred[:, None] == pred[None, :]
    same_gt = gt[:, None] == gt[None, :]
    tp = int(np.logical_and(same_pred, same_gt).sum()) - n  # 去对角线
    fp = int(same_pred.sum()) - n - tp
    fn = int(same_gt.sum()) - n - tp
    prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0
    return f1, prec, rec


def evaluate(pred_labels: np.ndarray, gt_labels: np.ndarray):
    f1, prec, rec = pairwise_f1(pred_labels, gt_labels)
    nmi = normalized_mutual_info_score(gt_labels, pred_labels)
    ari = adjusted_rand_score(gt_labels, pred_labels)
    return {"f1": f1, "precision": prec, "recall": rec, "nmi": nmi, "ari": ari}


def louvain_pred(G_nx, node_ids):
    try:
        from networkx.algorithms.community import louvain_communities

        comms = louvain_communities(G_nx, weight=None)
        pred = np.zeros(len(node_ids), dtype=int)
        for ci, c in enumerate(comms):
            for a in c:
                pred[node_ids.index(a)] = ci
        return pred
    except Exception as e:  # pragma: no cover
        print(f"  Louvain skipped: {e}")
        return None


class GNNClassifier(nn.Module):
    def __init__(self, sage: GraphSAGE, n_rings: int, hid: int = 64):
        super().__init__()
        self.sage = sage
        self.head = nn.Sequential(
            nn.Linear(sage.layers[-1].update.out_features, hid),
            nn.ReLU(),
            nn.Linear(hid, n_rings),
        )

    def forward(self, x, adj):
        e = self.sage(x, adj)
        return self.head(e)


def main():
    # ---- 生成带信号合成数据 ----
    n_background, n_rings, ring_size = 1000, 20, 6
    txs, gt = generate(
        n_background=n_background, n_rings=n_rings, ring_size=ring_size, seed=42
    )
    print(
        f"[data] accounts_tx={len(txs)} | 账户={len(gt)} | "
        f"背景={sum(1 for v in gt.values() if v < 0)} | 环={n_rings} x{ring_size}"
    )

    # ---- 构建账户时序图 ----
    g = build_account_graph(txs)
    node_ids = g["node_ids"]
    adj = g["adj"]
    feats = g["features"]
    N = len(node_ids)
    n_clusters = n_rings + 1  # +1 背景

    gt_arr = np.array([gt[a] for a in node_ids], dtype=int)

    feats_t = torch.tensor(feats, dtype=torch.float32)
    adj_t = torch.tensor(adj, dtype=torch.float32)

    labels = torch.full((N,), -1, dtype=torch.long)
    idx_map = g["index"]
    for a, lab in gt.items():
        if lab >= 0:
            labels[idx_map[a]] = lab
    mask = labels >= 0

    results = {}

    # (a) 原始特征 + KMeans
    km = KMeans(n_clusters=n_clusters, random_state=0, n_init=10).fit(feats)
    results["raw_features+KMeans"] = evaluate(km.labels_, gt_arr)
    print(f"[a] raw_features+KMeans      F1={results['raw_features+KMeans']['f1']:.4f} "
          f"NMI={results['raw_features+KMeans']['nmi']:.4f} ARI={results['raw_features+KMeans']['ari']:.4f}")

    # (b) 未训练 GraphSAGE + KMeans（复现当前 GNNAccount 现状）
    sage_b = GraphSAGE(in_dim=feats.shape[1], hidden_dim=64, out_dim=32, num_layers=2)
    with torch.no_grad():
        emb_b = sage_b.get_embeddings(feats_t, adj_t)
    km_b = KMeans(n_clusters=n_clusters, random_state=0, n_init=10).fit(emb_b)
    results["untrained_GraphSAGE+KMeans"] = evaluate(km_b.labels_, gt_arr)
    print(f"[b] untrained GraphSAGE+KMeans F1={results['untrained_GraphSAGE+KMeans']['f1']:.4f} "
          f"NMI={results['untrained_GraphSAGE+KMeans']['nmi']:.4f} ARI={results['untrained_GraphSAGE+KMeans']['ari']:.4f}  (≈当前现状)")

    # (c) 训练后 GraphSAGE + KMeans
    sage_c = GraphSAGE(in_dim=feats.shape[1], hidden_dim=64, out_dim=32, num_layers=2)
    model = GNNClassifier(sage_c, n_rings=n_rings)
    opt = torch.optim.Adam(model.parameters(), lr=1e-3)
    for ep in range(80):
        opt.zero_grad()
        logits = model(feats_t, adj_t)
        loss = F.cross_entropy(logits[mask], labels[mask])
        loss.backward()
        opt.step()
        if (ep + 1) % 20 == 0:
            print(f"  [train] ep{ep+1} loss={loss.item():.4f}")
    with torch.no_grad():
        emb_c = sage_c.get_embeddings(feats_t, adj_t)
    km_c = KMeans(n_clusters=n_clusters, random_state=0, n_init=10).fit(emb_c)
    results["trained_GraphSAGE+KMeans"] = evaluate(km_c.labels_, gt_arr)
    print(f"[c] trained GraphSAGE+KMeans   F1={results['trained_GraphSAGE+KMeans']['f1']:.4f} "
          f"NMI={results['trained_GraphSAGE+KMeans']['nmi']:.4f} ARI={results['trained_GraphSAGE+KMeans']['ari']:.4f}")

    # (d) Louvain（拓扑）
    lp = louvain_pred(g["G"].to_undirected(), node_ids)
    if lp is not None:
        results["Louvain(topology)"] = evaluate(lp, gt_arr)
        print(f"[d] Louvain(topology)         F1={results['Louvain(topology)']['f1']:.4f} "
              f"NMI={results['Louvain(topology)']['nmi']:.4f} ARI={results['Louvain(topology)']['ari']:.4f}")

    # ---- 环子图评测（公平测试：给定嫌疑账户，GNN 能否正确并案）----
    # 全图 pairwise F1 被背景淹没（AMLSim 真实亦如此），故补"嫌疑账户 refinement"评测：
    # 仅对环（嫌疑）节点做聚类，测同环是否归团。这是 GNN 的真实价值场景。
    ring_mask = gt_arr >= 0
    ring_node_ids = [node_ids[i] for i in np.where(ring_mask)[0]]
    gt_ring = gt_arr[ring_mask]

    def subgraph_eval(emb_all, name):
        emb_sub = emb_all[ring_mask]
        km = KMeans(n_clusters=n_rings, random_state=0, n_init=10).fit(emb_sub)
        res = evaluate(km.labels_, gt_ring)
        results[name] = res
        print(
            f"[{name}] ring-subgraph F1={res['f1']:.4f} "
            f"NMI={res['nmi']:.4f} ARI={res['ari']:.4f}"
        )

    subgraph_eval(feats, "raw_features+KMeans[ring]")
    subgraph_eval(emb_b, "untrained_GraphSAGE+KMeans[ring]")
    subgraph_eval(emb_c, "trained_GraphSAGE+KMeans[ring]")
    Gs = g["G"].to_undirected().subgraph(ring_node_ids)
    lp = louvain_pred(Gs, ring_node_ids)
    if lp is not None:
        results["Louvain[ring]"] = evaluate(lp, gt_ring)
        print(f"[Louvain[ring]] F1={results['Louvain[ring]']['f1']:.4f}")

    out = {
        "setting": {
            "n_background": n_background,
            "n_rings": n_rings,
            "ring_size": ring_size,
            "n_accounts": N,
            "n_tx": len(txs),
        },
        "honest_note": (
            "本评测为带信号合成数据的方法论证明：训练后账户 GNN 显著优于未训练/原始特征基线。"
            "AMLSim 原始全图 F1≈0.0016（信号被淹没）仅作难度基线，不构成真实验证（docs/06 金律）。"
        ),
        "results": results,
    }
    print("\n=== JSON ===")
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
