"""
Track A 账户 GNN 优化实验 (v2, 诚实)
===================================
对比：
  (B)  baseline : 二值邻接 + 旧训练(2层/out32/80ep/CE)         —— 复现 train_account_gnn 现状(~0.344)
  (E1) weighted : 加权邻接(log1p金额) + GraphSAGE(3层/out64) + 300ep StepLR
  (E2) +SupCon  : 在 E1 基础上加监督对比损失(同环近/异环远)辅助分类头

评测聚焦"环子图 F1"——给定嫌疑(环)账户，GNN 能否正确并案，这是 GNN 的真实价值场景。
诚实口径同 train_account_gnn.py：合成数据方法论证明；AMLSim 全图 F1≈0.0016 仅难度基线，
绝不称真实验证（docs/06 金律）。
"""
from __future__ import annotations

import json
import os
import random
import sys

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gnn.account_temporal import build_account_graph
from gnn.gnn_model import GraphSAGE
from gnn.synth_accounts import generate


def pairwise_f1(pred, gt):
    pred = np.asarray(pred)
    gt = np.asarray(gt)
    n = len(pred)
    sp = pred[:, None] == pred[None, :]
    sg = gt[:, None] == gt[None, :]
    tp = int(np.logical_and(sp, sg).sum()) - n
    fp = int(sp.sum()) - n - tp
    fn = int(sg.sum()) - n - tp
    p = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    r = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f = 2 * p * r / (p + r) if (p + r) > 0 else 0.0
    return f, p, r


def evaluate(pred, gt):
    f, p, r = pairwise_f1(pred, gt)
    return {
        "f1": f,
        "precision": p,
        "recall": r,
        "nmi": normalized_mutual_info_score(gt, pred),
        "ari": adjusted_rand_score(gt, pred),
    }


def louvain_pred(G, node_ids):
    try:
        from networkx.algorithms.community import louvain_communities

        comms = louvain_communities(G, weight=None)
        pred = np.zeros(len(node_ids), dtype=int)
        for ci, c in enumerate(comms):
            for a in c:
                pred[node_ids.index(a)] = ci
        return pred
    except Exception as e:  # pragma: no cover
        print(f"  Louvain skipped: {e}")
        return None


def supcon_loss(emb, labels, tau=0.5):
    """仅对环节点(>=0)计算监督对比损失：同环拉近、异环推远。"""
    emb = F.normalize(emb, dim=1)
    sim = emb @ emb.T / tau  # (M,M)
    M = emb.size(0)
    same = (labels.unsqueeze(0) == labels.unsqueeze(1)).float()
    eye = torch.eye(M, device=emb.device)
    pos = same - eye  # 排除自身
    exp = torch.exp(sim)
    denom = (exp * (1 - eye)).sum(1) + 1e-8
    numer = (exp * pos.clamp(min=0)).sum(1) + 1e-8
    return (-torch.log(numer / denom)).mean()


def run_once(setting, weighted, n_layers, out_dim, epochs, lr, use_supcon, seed=42):
    # 关键修复：此前仅 generate() 用 seed 固定了数据，GNN 权重初始化与训练未固定，
    # 导致同脚本 F1 在 0.648~0.866 间摆动（不可复现）。现固定全部随机源。
    torch.manual_seed(seed)
    np.random.seed(seed)
    random.seed(seed)
    n_bg, n_rings, rs = 1000, 20, 6
    txs, gt = generate(n_background=n_bg, n_rings=n_rings, ring_size=rs, seed=seed)
    g = build_account_graph(txs, weighted=weighted)
    node_ids = g["node_ids"]
    adj = g["adj"]
    feats = g["features"]
    N = len(node_ids)
    n_clusters = n_rings + 1
    gt_arr = np.array([gt[a] for a in node_ids], dtype=int)
    ft = torch.tensor(feats, dtype=torch.float32)
    at = torch.tensor(adj, dtype=torch.float32)

    labels = torch.full((N,), -1, dtype=torch.long)
    for a, lab in gt.items():
        if lab >= 0:
            labels[g["index"][a]] = lab
    mask = labels >= 0

    # (a) raw features + KMeans（无 GNN）
    km = KMeans(n_clusters=n_clusters, random_state=0, n_init=10).fit(feats)
    res_raw = evaluate(km.labels_, gt_arr)
    print(
        f"  [{setting}] raw_features+KMeans F1={res_raw['f1']:.4f} "
        f"NMI={res_raw['nmi']:.4f} ARI={res_raw['ari']:.4f}"
    )

    # GNN
    sage = GraphSAGE(
        in_dim=feats.shape[1],
        hidden_dim=64,
        out_dim=out_dim,
        num_layers=n_layers,
        dropout=0.3,
    )
    head = nn.Sequential(nn.Linear(out_dim, 64), nn.ReLU(), nn.Linear(64, n_rings))
    opt = torch.optim.Adam(
        list(sage.parameters()) + list(head.parameters()), lr=lr
    )
    sched = torch.optim.lr_scheduler.StepLR(opt, step_size=max(epochs // 3, 1), gamma=0.5)
    for ep in range(epochs):
        opt.zero_grad()
        emb = sage(ft, at)
        logits = head(emb)
        loss_ce = F.cross_entropy(logits[mask], labels[mask])
        if use_supcon and int(mask.sum()) > 1:
            loss_sc = supcon_loss(emb[mask], labels[mask])
            loss = loss_ce + 0.5 * loss_sc
        else:
            loss = loss_ce
        loss.backward()
        opt.step()
        sched.step()
    with torch.no_grad():
        emb = sage(ft, at).cpu().numpy()

    km_g = KMeans(n_clusters=n_clusters, random_state=0, n_init=10).fit(emb)
    res_gnn = evaluate(km_g.labels_, gt_arr)
    print(
        f"  [{setting}] gnn+KMeans(full)      F1={res_gnn['f1']:.4f} "
        f"NMI={res_gnn['nmi']:.4f} ARI={res_gnn['ari']:.4f}"
    )

    # 环子图评测（GNN 真实价值场景）
    ring_mask = gt_arr >= 0
    gt_ring = gt_arr[ring_mask]
    res = {}
    km_rr = KMeans(n_clusters=n_rings, random_state=0, n_init=10).fit(feats[ring_mask])
    res["ring_subgraph_raw"] = evaluate(km_rr.labels_, gt_ring)
    km_rg = KMeans(n_clusters=n_rings, random_state=0, n_init=10).fit(emb[ring_mask])
    res["ring_subgraph_gnn"] = evaluate(km_rg.labels_, gt_ring)
    ring_ids = [node_ids[i] for i in np.where(ring_mask)[0]]
    Gs = g["G"].to_undirected().subgraph(ring_ids)
    lp = louvain_pred(Gs, ring_ids)
    if lp is not None:
        res["ring_subgraph_louvain"] = evaluate(lp, gt_ring)
    print(
        f"  [{setting}] ring-subgraph GNN F1={res['ring_subgraph_gnn']['f1']:.4f} "
        f"(raw={res['ring_subgraph_raw']['f1']:.4f})"
    )

    return {
        "setting": setting,
        "weighted": weighted,
        "n_layers": n_layers,
        "out_dim": out_dim,
        "epochs": epochs,
        "use_supcon": use_supcon,
        "raw_features+KMeans": res_raw,
        "gnn+KMeans(full)": res_gnn,
        "ring_subgraph": res,
    }


def main():
    results = {}
    print("=== [B] baseline: 二值邻接 + 旧训练(2层/out32/80ep) ===")
    results["B_baseline"] = run_once(
        "B", weighted=False, n_layers=2, out_dim=32, epochs=80, lr=1e-3, use_supcon=False
    )
    print("=== [E1] 加权邻接 + 增强训练(3层/out64/300ep) ===")
    results["E1_weighted"] = run_once(
        "E1", weighted=True, n_layers=3, out_dim=64, epochs=300, lr=1e-3, use_supcon=False
    )
    print("=== [E2] 加权邻接 + 增强训练 + SupCon ===")
    results["E2_weighted_supcon"] = run_once(
        "E2", weighted=True, n_layers=3, out_dim=64, epochs=300, lr=1e-3, use_supcon=True
    )

    out = {
        "honest_note": (
            "合成数据方法论证明：训练后账户 GNN 在信号明确时可高 F1 恢复团伙。"
            "AMLSim 原始全图 F1≈0.0016（信号被淹没）仅作难度基线，不构成真实验证（docs/06 金律）。"
        ),
        "results": results,
    }
    path = os.path.join(os.path.dirname(__file__), "account_gnn_v2_results.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"\n=== saved {path} ===")
    # 末行汇总
    for k, v in results.items():
        rg = v["ring_subgraph"]["ring_subgraph_gnn"]["f1"]
        print(f"  {k:22s} ring-subgraph F1={rg:.4f}")


def main_seeded(seeds=(42, 0, 1, 2, 3)):
    """多 seed 复现：报告环子图 GNN F1 的均值±std，替代单 seed 硬指标。"""
    settings = {
        "B_baseline": dict(weighted=False, n_layers=2, out_dim=32, epochs=80, lr=1e-3, use_supcon=False),
        "E1_weighted": dict(weighted=True, n_layers=3, out_dim=64, epochs=300, lr=1e-3, use_supcon=False),
        "E2_weighted_supcon": dict(weighted=True, n_layers=3, out_dim=64, epochs=300, lr=1e-3, use_supcon=True),
    }
    agg = {}
    for name, kw in settings.items():
        f1s, raws, fulls = [], [], []
        for sd in seeds:
            r = run_once(name, seed=sd, **kw)
            f1s.append(r["ring_subgraph"]["ring_subgraph_gnn"]["f1"])
            raws.append(r["ring_subgraph"]["ring_subgraph_raw"]["f1"])
            fulls.append(r["gnn+KMeans(full)"]["f1"])
        agg[name] = {
            "seeds": list(seeds),
            "ring_subgraph_gnn": {
                "mean": round(float(np.mean(f1s)), 4),
                "std": round(float(np.std(f1s)), 4),
                "vals": [round(x, 4) for x in f1s],
            },
            "ring_subgraph_raw": {
                "mean": round(float(np.mean(raws)), 4),
                "std": round(float(np.std(raws)), 4),
                "vals": [round(x, 4) for x in raws],
            },
            "gnn_full": {
                "mean": round(float(np.mean(fulls)), 4),
                "std": round(float(np.std(fulls)), 4),
                "vals": [round(x, 4) for x in fulls],
            },
        }
        g = agg[name]["ring_subgraph_gnn"]
        print(
            f"[{name}] ring-subgraph GNN F1 = {g['mean']:.4f} ± {g['std']:.4f} "
            f"(vals={g['vals']})"
        )
    path = os.path.join(os.path.dirname(__file__), "account_gnn_v2_seeded_results.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "honest_note": (
                    "多 seed 复现：此前单 seed=42 的 0.866 是未固定 GNN 训练随机性的偶然样本；"
                    "以下为 5 seed 均值±std，应作为论文引用的稳健估计。"
                ),
                "seeds": list(seeds),
                "results": agg,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )
    print(f"\n[saved] {path}")


if __name__ == "__main__":
    import sys

    if "--seeded" in sys.argv:
        main_seeded()
    else:
        main()
