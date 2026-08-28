"""
Path B · 分支 B：GAE 重构误差异常检测（DOMINANT 化改造）
================================================================
思路：训练一个无监督图自编码器（GCN 编码器 + 特征/邻接双解码头），
模型学的是"正常账户长什么样"；异常分数 = 重构误差（重建得越差 ≈
越偏离正常模式 ≈ 越可疑）。无需任何团伙标签，抗域偏移。

与 DOMINANT（Ding et al., WSDM 2019）对齐：
  loss     = alpha * 特征重构MSE + (1-alpha) * 邻接重构BCE（正边+采样负边）
  score    = (1-alpha) * 特征误差 + alpha * 结构误差

诚实口径：
- 重构误差 ≠ 洗钱判定，只是"可疑度排序线索"，必须与分支 C 规则交叉验证；
- AMLSim 为公开合成基准，结果不构成"真实警务数据验证通过"；
- 不针对 GT 调超参，全部用固定默认值，如实报告。

输出：backend/gnn/pathb_gae_anomaly_results.json
"""
from __future__ import annotations

import json
import os
import sys
import time

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

BACKEND = os.path.dirname(os.path.abspath(__file__))
for p in (BACKEND, os.path.dirname(BACKEND)):
    if p not in sys.path:
        sys.path.insert(0, p)

from gnn.account_temporal import build_account_graph  # noqa: E402
from gnn.adapters.amlsim_adapter import load_amlsim  # noqa: E402

DATA_DIR = os.path.join(BACKEND, "amlsim_real", "canonical")
OUT_PATH = os.path.join(BACKEND, "pathb_gae_anomaly_results.json")
N_ANCHOR_RINGS = 60
K_HOP = 2
MAX_NODES = 8000
EPOCHS = 100
LR = 1e-3
ALPHA = 0.5          # 特征 vs 结构 重构权重（DOMINANT 默认）
HIDDEN = 64
LATENT = 32
N_NEG_SAMPLES = 1000  # 负边采样数（邻接 BCE）

torch.manual_seed(42)
np.random.seed(42)


class GCNLayer(nn.Module):
    """单层图卷积：X' = ReLU(A_hat @ X @ W)。A_hat = D^-1/2 A D^-1/2（稀疏乘）。"""

    def __init__(self, in_dim: int, out_dim: int):
        super().__init__()
        self.w = nn.Linear(in_dim, out_dim, bias=False)

    def forward(self, x: torch.Tensor, a_hat: torch.Tensor) -> torch.Tensor:
        h = a_hat @ x          # 邻居聚合 [N, in]
        return F.relu(self.w(h))


class GAEAnomaly(nn.Module):
    """GCN 编码器 + 特征/邻接双解码头（DOMINANT 结构）。"""

    def __init__(self, in_dim: int, hidden: int = HIDDEN, latent: int = LATENT):
        super().__init__()
        self.gc1 = GCNLayer(in_dim, hidden)
        self.gc2 = GCNLayer(hidden, latent)
        # 特征解码
        self.feat_dec = nn.Sequential(
            nn.Linear(latent, hidden), nn.ReLU(), nn.Linear(hidden, in_dim))
        # 邻接解码：内积 Z @ Z^T

    def encode(self, x: torch.Tensor, a_hat: torch.Tensor) -> torch.Tensor:
        h = self.gc1(x, a_hat)
        return self.gc2(h, a_hat)

    def decode_feat(self, z: torch.Tensor) -> torch.Tensor:
        return self.feat_dec(z)

    def decode_adj(self, z: torch.Tensor) -> torch.Tensor:
        return z @ z.t()


def normalize_adj(adj_coo: torch.Tensor, n: int) -> torch.Tensor:
    """A -> D^-1/2 A D^-1/2 稀疏归一化。"""
    idx = adj_coo._indices() if adj_coo.is_sparse else adj_coo.nonzero().t()
    vals = adj_coo._values().float() if adj_coo.is_sparse else torch.ones(idx.size(1))
    deg = torch.zeros(n)
    deg.index_add_(0, idx[0], vals)
    deg.index_add_(0, idx[1], vals)
    deg_inv_sqrt = torch.where(deg > 0, deg.pow(-0.5), torch.zeros_like(deg))
    w = vals * deg_inv_sqrt[idx[0]] * deg_inv_sqrt[idx[1]]
    return torch.sparse_coo_tensor(idx, w, (n, n))


def structural_score(z: torch.Tensor, pos_edges: torch.Tensor,
                     neg_edges: torch.Tensor) -> torch.Tensor:
    """节点级结构重构误差：对每个节点，其参与的 (正边+负边) 重建误差均值。
    误差大 = 该节点邻接模式偏离自编码器学到的正常模式。"""
    zt = z.t()
    s = torch.zeros(z.size(0))
    cnt = torch.zeros(z.size(0))
    for e in (pos_edges, neg_edges):
        if e.size(0) == 0:
            continue
        prod = (z[e[:, 0]] * z[e[:, 1]]).sum(dim=1)   # 内积重建值
        err = F.binary_cross_entropy_with_logits(prod, torch.zeros_like(prod) if e is neg_edges else torch.ones_like(prod), reduction="none")
        s.index_add_(0, e[:, 0], err)
        s.index_add_(0, e[:, 1], err)
        cnt.index_add_(0, e[:, 0], torch.ones(e.size(0)))
        cnt.index_add_(0, e[:, 1], torch.ones(e.size(0)))
    return s / cnt.clamp(min=1)


def extract_anchor_subgraph(account_ids, edges, gt, n_anchor_rings=N_ANCHOR_RINGS,
                            k_hop=K_HOP, max_nodes=MAX_NODES):
    ring_accounts = [a for a, l in gt.items() if l >= 0]
    adj = {}
    for s, d, _, _ in edges:
        adj.setdefault(s, []).append(d)
        adj.setdefault(d, []).append(s)
    ring_of = {}
    for a in ring_accounts:
        ring_of.setdefault(gt[a], []).append(a)
    chosen_rings = list(ring_of.keys())[:n_anchor_rings]
    anchors = [ring_of[r][0] for r in chosen_rings]
    seen, frontier = set(), list(anchors)
    for _ in range(k_hop):
        nxt = []
        for a in frontier:
            for nb in adj.get(a, []):
                if nb not in seen:
                    seen.add(nb)
                    nxt.append(nb)
                    if len(seen) >= max_nodes:
                        break
            if len(seen) >= max_nodes:
                break
        frontier = nxt
        if len(seen) >= max_nodes:
            break
    sub_accounts = list(seen)
    sub_set = set(sub_accounts)
    sub_txs = [{"from_account": s, "to_account": d, "amount": amt, "timestamp": ts}
               for (s, d, amt, ts) in edges if s in sub_set and d in sub_set]
    sub_gt = {a: gt.get(a, -1) for a in sub_accounts}
    return sub_txs, sub_gt, len(anchors)


def main():
    t0 = time.time()
    print("[load] AMLSim canonical ...", flush=True)
    account_ids, edges, gt = load_amlsim(DATA_DIR)
    print(f"[load] accounts={len(account_ids)} edges={len(edges)}", flush=True)

    sub_txs, sub_gt, n_anchors = extract_anchor_subgraph(account_ids, edges, gt)
    print(f"[subgraph] anchors={n_anchors} txs={len(sub_txs)} nodes={len(sub_gt)}", flush=True)

    g = build_account_graph(sub_txs, sparse_adj=True)
    node_ids = g["node_ids"]
    feats = np.asarray(g["features"], dtype=np.float32)
    adj_coo = g["adj"]
    gt_arr = np.array([sub_gt[a] for a in node_ids], dtype=int)
    n = len(node_ids)
    print(f"[build] nodes={n} feats_dim={feats.shape[1]} edges_nnz={int(adj_coo._nnz())}", flush=True)

    # ---- 训练（完全无标签） ----
    x = torch.tensor(feats)
    a_hat = normalize_adj(adj_coo, n)
    idx = adj_coo._indices()
    pos_edges = idx.t().long()
    # 负边采样：随机不存在的边
    neg_pairs = set()
    pos_set = set(map(tuple, pos_edges.tolist()))
    rng = np.random.default_rng(42)
    while len(neg_pairs) < N_NEG_SAMPLES:
        i = rng.integers(0, n, N_NEG_SAMPLES * 4)
        j = rng.integers(0, n, N_NEG_SAMPLES * 4)
        for a, b in zip(i.tolist(), j.tolist()):
            if a == b or (a, b) in pos_set or (b, a) in pos_set:
                continue
            neg_pairs.add((a, b))
            if len(neg_pairs) >= N_NEG_SAMPLES:
                break
    neg_edges = torch.tensor(list(neg_pairs), dtype=torch.long)

    model = GAEAnomaly(in_dim=feats.shape[1])
    opt = torch.optim.Adam(model.parameters(), lr=LR)
    model.train()
    for ep in range(EPOCHS):
        opt.zero_grad()
        z = model.encode(x, a_hat)
        x_rec = model.decode_feat(z)
        feat_loss = F.mse_loss(x_rec, x)
        # 邻接 BCE（正边=1，负边=0）
        pos_logit = (z[pos_edges[:, 0]] * z[pos_edges[:, 1]]).sum(dim=1)
        neg_logit = (z[neg_edges[:, 0]] * z[neg_edges[:, 1]]).sum(dim=1)
        adj_loss = F.binary_cross_entropy_with_logits(
            torch.cat([pos_logit, neg_logit]),
            torch.cat([torch.ones_like(pos_logit), torch.zeros_like(neg_logit)]))
        loss = ALPHA * feat_loss + (1 - ALPHA) * adj_loss
        loss.backward()
        opt.step()
        if (ep + 1) % 20 == 0:
            print(f"  [train] ep={ep+1}/{EPOCHS} loss={loss.item():.4f} "
                  f"feat={feat_loss.item():.4f} adj={adj_loss.item():.4f}", flush=True)

    # ---- 异常分数 ----
    model.eval()
    with torch.no_grad():
        z = model.encode(x, a_hat)
        x_rec = model.decode_feat(z)
        feat_err = (x_rec - x).pow(2).mean(dim=1)          # [N]
        struct_err = structural_score(z, pos_edges, neg_edges)  # [N]
        # 归一化后加权合成
        feat_err_n = (feat_err - feat_err.min()) / (feat_err.max() - feat_err.min() + 1e-9)
        struct_err_n = (struct_err - struct_err.min()) / (struct_err.max() - struct_err.min() + 1e-9)
        score = (1 - ALPHA) * feat_err_n + ALPHA * struct_err_n
    score_np = score.numpy()
    gt_arr_np = np.asarray(gt_arr)

    # ---- 评测 1：top-k 命中率（无监督排序能力） ----
    ring_mask = gt_arr_np >= 0
    n_ring = int(ring_mask.sum())
    results = {"topk_hit": {}, "auc": None}
    for k_ratio in [0.05, 0.1, 0.2]:
        k = max(int(n * k_ratio), 1)
        topk = np.argsort(-score_np)[:k]
        hit = int(ring_mask[topk].sum())
        results["topk_hit"][f"top{k_ratio:.0%}"] = {
            "k": k, "hits_in_rings": hit, "ring_coverage": round(hit / max(n_ring, 1), 4),
            "precision_at_k": round(hit / k, 4)}
        print(f"  [eval] top{k_ratio:.0%}(k={k}): ring_hits={hit}/{n_ring} "
              f"precision@{k_ratio:.0%}={hit/k:.4f}", flush=True)

    # ---- 评测 2：score 阈值 → 二分类（无监督 AUC 参考） ----
    from sklearn.metrics import roc_auc_score
    y_bin = (gt_arr_np >= 0).astype(int)
    if y_bin.sum() > 0 and y_bin.sum() < len(y_bin):
        results["auc"] = round(float(roc_auc_score(y_bin, score_np)), 4)
        print(f"  [eval] AUC(anomaly_score vs in-ring) = {results['auc']}", flush=True)

    setting = {
        "data_dir": DATA_DIR, "n_anchor_rings": N_ANCHOR_RINGS, "k_hop": K_HOP,
        "max_nodes": MAX_NODES, "n_subgraph_nodes": n, "epochs": EPOCHS, "lr": LR,
        "alpha": ALPHA, "hidden": HIDDEN, "latent": LATENT, "n_neg_samples": N_NEG_SAMPLES,
        "blind_baseline_f1": 0.002,
        "note": "Path B 分支 B：无监督 GAE 重构误差异常检测（DOMINANT 化）。"
                "重构误差为可疑度线索非洗钱判定；AMLSim 为公开合成基准，不构成真实验证通过。",
    }
    out = {"setting": setting, "results": results, "elapsed_s": round(time.time() - t0, 1)}
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"\n[saved] {OUT_PATH}  ({time.time()-t0:.1f}s)")


if __name__ == "__main__":
    main()
