"""
Track A 盲扫全图 F1 实验（诚实版，#C47 / #147）
=============================================
目标：把 docs 中引用的「AMLSim 盲扫全图 F1≈0.002」从常量落成**真实可复现数值**，
并在真实全图（4.3 万账户 / ~440 万笔 / 1305 个洗钱环）上诚实测试两类缓解：
  - 加权邻接（#C44，资金强度加权）
  - 金额边剪枝（仅保留高金额边，弱化背景噪声）
以及标准盲扫方法：Louvain（纯拓扑）、raw 特征 + KMeans、未训练/训练后 GNN + KMeans。

关键诚实口径（金律）：
  - 本实验为**外部难度基线复现**，不构成"真实警务数据验证通过"。
  - 背景（约 4.3 万）为单一大类，pairwise F1 对背景碎片化极敏感；
    若缓解仍无法改变结构劣势，如实记录阴性结果（这正是开放问题的诚实结论）。
  - 额外报告 ring_only_f1（仅在涉案节点上对同环恢复），作为更公平的 GNN 判别力诊断。

规模注意：43k 节点稠密邻接 ~7.6GB 必 OOM，故 build_account_graph(sparse_adj=True)
走 torch 稀疏 COO（无需 scipy）。边以生成器喂入避免 440 万字典列表爆内存。
"""
from __future__ import annotations

import os
import sys
import json
import time

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from sklearn.cluster import KMeans
from sklearn.metrics import normalized_mutual_info_score, adjusted_rand_score

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gnn.account_temporal import build_account_graph
from gnn.gnn_model import GraphSAGE
from gnn.adapters.amlsim_adapter import load_amlsim

torch.manual_seed(0)
np.random.seed(0)

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "amlsim_real", "canonical")
OUT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "blind_sweep_results.json")
GNN_EPOCHS = 50


# ---------- 高效 pairwise F1（列联表，避免 43k×43k 巨阵 OOM） ----------
def _compact(labels):
    """把任意标签集合（含 -1 背景/非涉案节点）压缩为 0..K-1 紧凑整数。
    关键：背景(-1)不可直接进 bincount（负元素报错），也不能丢弃（会虚增 F1）。
    压缩后背景成为独立一类，保留在列联表中，结果诚实。"""
    uniq = {v: i for i, v in enumerate(sorted(set(labels.tolist())))}
    return np.array([uniq[v] for v in labels.tolist()], dtype=np.int64)


def pairwise_f1(pred, gt):
    pred = _compact(np.asarray(pred, dtype=np.int64))
    gt = _compact(np.asarray(gt, dtype=np.int64))
    if pred.size == 0:
        return 0.0, 0.0, 0.0
    n_pred = int(pred.max()) + 1
    n_gt = int(gt.max()) + 1
    flat = pred * n_gt + gt
    H = np.bincount(flat, minlength=n_pred * n_gt).reshape(n_pred, n_gt).astype(np.int64)
    c2 = H * (H - 1) // 2
    TP = int(c2.sum())
    row = H.sum(axis=1)
    col = H.sum(axis=0)
    FP = int((row * (row - 1) // 2).sum()) - TP
    FN = int((col * (col - 1) // 2).sum()) - TP
    prec = TP / (TP + FP) if (TP + FP) > 0 else 0.0
    rec = TP / (TP + FN) if (TP + FN) > 0 else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0
    return f1, prec, rec


def evaluate(pred, gt):
    f1, prec, rec = pairwise_f1(pred, gt)
    gt = np.asarray(gt)
    ring_mask = gt >= 0
    ring_f1 = pairwise_f1(pred[ring_mask], gt[ring_mask])[0] if ring_mask.sum() > 1 else 0.0
    nmi = float(normalized_mutual_info_score(gt, pred)) if len(set(gt.tolist())) > 1 else 0.0
    ari = float(adjusted_rand_score(gt, pred)) if len(set(gt.tolist())) > 1 else 0.0
    return {"f1": f1, "precision": prec, "recall": rec, "ring_only_f1": ring_f1,
            "nmi": nmi, "ari": ari}


def louvain_pred(G_nx, node_ids):
    from networkx.algorithms.community import louvain_communities

    comms = louvain_communities(G_nx, weight=None)
    idx_of = {a: i for i, a in enumerate(node_ids)}
    pred = np.zeros(len(node_ids), dtype=int)
    for ci, c in enumerate(comms):
        for a in c:
            if a in idx_of:
                pred[idx_of[a]] = ci
    return pred


class GNNClassifier(nn.Module):
    def __init__(self, sage, n_classes, hid=64):
        super().__init__()
        self.sage = sage
        self.head = nn.Sequential(
            nn.Linear(sage.layers[-1].update.out_features, hid),
            nn.ReLU(),
            nn.Linear(hid, n_classes),
        )

    def forward(self, x, adj):
        return self.head(self.sage(x, adj))


def to_csr(adj):
    """防御性：COO 转 CSR，确保 torch.sparse.mm 兼容。"""
    if adj.is_sparse and hasattr(adj, "to_sparse_csr"):
        try:
            return adj.to_sparse_csr()
        except Exception:
            return adj
    return adj


def run_gnn(feats, adj, gt_arr, n_rings, epochs=GNN_EPOCHS):
    adj = to_csr(adj)
    feats_t = torch.tensor(feats, dtype=torch.float32)
    labels = torch.full((len(gt_arr),), -1, dtype=torch.long)
    for i, v in enumerate(gt_arr):
        if v >= 0:
            labels[i] = v
    mask = labels >= 0
    n_classes = int(labels[mask].max().item()) + 1 if mask.any() else 1
    sage = GraphSAGE(in_dim=feats.shape[1], hidden_dim=64, out_dim=32, num_layers=2)
    model = GNNClassifier(sage, n_classes=n_classes)
    opt = torch.optim.Adam(model.parameters(), lr=1e-3)
    for _ in range(epochs):
        opt.zero_grad()
        logits = model(feats_t, adj)
        loss = F.cross_entropy(logits[mask], labels[mask])
        loss.backward()
        opt.step()
    with torch.no_grad():
        emb = sage.get_embeddings(feats_t, adj)
    return emb


def cluster_km(emb, n_clusters):
    return KMeans(n_clusters=n_clusters, random_state=0, n_init=3).fit(emb).labels_


def save_partial(results, setting, elapsed):
    out = {
        "setting": setting,
        "honest_note": (
            "AMLSim 全图盲扫：背景(约4.3万)为单一大类，pairwise F1 对背景碎片化极敏感；"
            "本实验把引用常量 0.002 落成真实可复现数值，并测试加权/剪枝缓解，诚实记录是否改善。"
            "不构成真实验证通过。"
        ),
        "results": {k: {kk: round(vv, 4) for kk, vv in v.items()} for k, v in results.items()},
        "elapsed_sec": round(elapsed, 1),
    }
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)


def main():
    t0 = time.time()
    print("[load] AMLSim canonical ...", flush=True)
    account_ids, edges, gt = load_amlsim(DATA_DIR)
    ring_accounts = [a for a, l in gt.items() if l >= 0]
    n_rings = len(set(v for v in gt.values() if v >= 0))
    n_clusters = n_rings + 1
    print(f"[load] accounts={len(account_ids)} edges={len(edges)} rings={n_rings} "
          f"ring_members={len(ring_accounts)}", flush=True)

    setting = {
        "data_dir": DATA_DIR, "n_accounts": len(account_ids), "n_edges": len(edges),
        "n_rings": n_rings, "n_clusters_used": n_clusters, "gnn_epochs": GNN_EPOCHS,
        "note": "盲扫全图：无锚点、无子图限制，方法须从全图结构/特征恢复 1305 个洗钱环。",
    }
    results = {}

    def gen_all():
        for (s, d, amt, ts) in edges:
            yield {"from_account": s, "to_account": d, "amount": amt, "timestamp": ts}

    # ---- (A) 基线：二值邻接 ----
    print("[build] binary sparse graph ...", flush=True)
    g = build_account_graph(gen_all(), weighted=False, sparse_adj=True)
    node_ids = g["node_ids"]
    feats = g["features"]
    adj = g["adj"]
    gt_arr = np.array([gt[a] for a in node_ids], dtype=int)
    print(f"[build] graph nodes={len(node_ids)} edges={int(adj._nnz())}", flush=True)

    print("[run] Louvain ...", flush=True)
    results["Louvain(binary)"] = evaluate(louvain_pred(g["G"].to_undirected(), node_ids), gt_arr)
    save_partial(results, setting, time.time() - t0)

    print("[run] raw_features+KMeans ...", flush=True)
    results["raw_features+KMeans"] = evaluate(cluster_km(feats, n_clusters), gt_arr)
    save_partial(results, setting, time.time() - t0)

    print("[run] untrained_GNN+KMeans ...", flush=True)
    sage_b = GraphSAGE(in_dim=feats.shape[1], hidden_dim=64, out_dim=32, num_layers=2)
    with torch.no_grad():
        emb_b = sage_b.get_embeddings(torch.tensor(feats, dtype=torch.float32), to_csr(adj))
    results["untrained_GNN+KMeans"] = evaluate(cluster_km(emb_b, n_clusters), gt_arr)
    save_partial(results, setting, time.time() - t0)

    print("[run] trained_GNN+KMeans ...", flush=True)
    emb_c = run_gnn(feats, adj, gt_arr, n_rings, epochs=GNN_EPOCHS)
    results["trained_GNN+KMeans"] = evaluate(cluster_km(emb_c, n_clusters), gt_arr)
    save_partial(results, setting, time.time() - t0)

    # ---- (B) 缓解 1：加权邻接（资金强度） ----
    print("[build] weighted sparse graph ...", flush=True)

    def gen_all_w():
        for (s, d, amt, ts) in edges:
            yield {"from_account": s, "to_account": d, "amount": amt, "timestamp": ts}

    g_w = build_account_graph(gen_all_w(), weighted=True, sparse_adj=True)
    emb_w = run_gnn(feats, g_w["adj"], gt_arr, n_rings, epochs=GNN_EPOCHS)
    results["trained_GNN_weighted+KMeans"] = evaluate(cluster_km(emb_w, n_clusters), gt_arr)
    save_partial(results, setting, time.time() - t0)

    # ---- (C) 缓解 2：金额边剪枝（保留 top 20% 金额边） ----
    print("[build] pruned graph (top20% amount) ...", flush=True)
    amounts = np.array([e[2] for e in edges], dtype=float)
    thresh = float(np.quantile(amounts[amounts > 0], 0.8)) if np.any(amounts > 0) else 0.0
    pruned = [e for e in edges if e[2] >= thresh]

    def gen_pruned():
        for (s, d, amt, ts) in pruned:
            yield {"from_account": s, "to_account": d, "amount": amt, "timestamp": ts}

    g_p = build_account_graph(gen_pruned(), weighted=False, sparse_adj=True)
    feats_p = g_p["features"]
    gt_p = np.array([gt[a] for a in g_p["node_ids"]], dtype=int)
    n_rings_p = len(set(v for v in gt_p if v >= 0))
    print(f"[prune] kept {len(pruned)}/{len(edges)} edges, subgraph rings={n_rings_p}", flush=True)

    results["pruned_Louvain"] = evaluate(louvain_pred(g_p["G"].to_undirected(), g_p["node_ids"]), gt_p)
    save_partial(results, setting, time.time() - t0)
    results["pruned_raw+KMeans"] = evaluate(cluster_km(feats_p, n_rings_p + 1), gt_p)
    save_partial(results, setting, time.time() - t0)
    emb_p = run_gnn(feats_p, g_p["adj"], gt_p, n_rings_p, epochs=GNN_EPOCHS)
    results["pruned_trained_GNN+KMeans"] = evaluate(cluster_km(emb_p, n_rings_p + 1), gt_p)
    save_partial(results, setting, time.time() - t0)

    # ---- 汇总 ----
    print("\n=== BLIND-SWEEP RESULTS (full-graph pairwise F1) ===")
    for k, v in results.items():
        print(f"  {k:32s} F1={v['f1']:.4f}  ringF1={v['ring_only_f1']:.4f}  "
              f"NMI={v['nmi']:.4f}  ARI={v['ari']:.4f}")
    print(f"[done] elapsed={round(time.time()-t0,1)}s -> {OUT_PATH}")


if __name__ == "__main__":
    main()
