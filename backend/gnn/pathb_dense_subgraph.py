"""
Path B · 分支 A：无监督稠密子图发现（AMLSim 锚点扩线设定）
================================================================
目标：不依赖任何团伙标签，仅用图拓扑做"可疑稠密子图"发现，
验证"盲扫失效 → 扩线可用"的设定迁移在纯无监督下是否复现。

方法（全部无监督）：
  A1 dense-louvain : Louvain 社区 + 社区密度打分，稠密社区保留为团伙，稀疏节点归背景
  A2 kcore-louvain : k-core 分解，仅在 k>=kmin 核心子图上 Louvain
  A3 kcore-dense   : k-core 分层后，各核心层内再按稠密社区聚类

评测协议（与 amlsim_refinement_results.json 的 spread 设定完全同口径）：
  60 环锚点 / k=2 跳 / max_nodes=8000
  指标：pairwise F1 + ring_only_F1 + precision/recall + NMI/ARI
  诚实对照：盲扫基线 F1≈0.002；扩线 Louvain(topology) F1≈0.1106

诚实口径：无监督方法不调阈值到最优——每个阈值都如实报告，不挑选。
任何结果都不构成"真实警务数据验证通过"。

输出：backend/gnn/pathb_dense_results.json
"""
from __future__ import annotations

import json
import os
import sys
import time

import numpy as np

BACKEND = os.path.dirname(os.path.abspath(__file__))
for p in (BACKEND, os.path.dirname(BACKEND)):
    if p not in sys.path:
        sys.path.insert(0, p)

import networkx as nx  # noqa: E402
from networkx.algorithms.community import louvain_communities  # noqa: E402
from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score  # noqa: E402

from gnn.account_temporal import build_account_graph  # noqa: E402
from gnn.adapters.amlsim_adapter import load_amlsim  # noqa: E402

DATA_DIR = os.path.join(BACKEND, "amlsim_real", "canonical")
OUT_PATH = os.path.join(BACKEND, "pathb_dense_results.json")
N_ANCHOR_RINGS = 60
K_HOP = 2
MAX_NODES = 8000


# ---------- 高效 pairwise F1（列联表，避免 43k×43k 巨阵 OOM） ----------
def _compact(labels):
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


# ---------- 锚点扩线子图提取（与 refinement_experiment 同口径） ----------
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

    seen = set()
    frontier = list(anchors)
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
    sub_txs = [
        {"from_account": s, "to_account": d, "amount": amt, "timestamp": ts}
        for (s, d, amt, ts) in edges
        if s in sub_set and d in sub_set
    ]
    sub_gt = {a: gt.get(a, -1) for a in sub_accounts}
    return sub_txs, sub_gt, len(anchors)


# ---------- 无监督方法 ----------
def dense_louvain_pred(G_nx, node_ids, min_density=2.0):
    """A1：Louvain 社区 + 密度打分。
    社区平均度 >= min_density 的保留为独立团伙，其余节点全部归背景(-1)。
    min_density 是固定规则参数（不针对 GT 调优），多个值都会报告。"""
    comms = louvain_communities(G_nx, weight=None)
    idx_of = {a: i for i, a in enumerate(node_ids)}
    pred = np.full(len(node_ids), -1, dtype=int)
    cid = 0
    for c in comms:
        sub = G_nx.subgraph(c)
        n = sub.number_of_nodes()
        m = sub.number_of_edges()
        density = (2.0 * m) / n if n > 0 else 0.0  # 平均度
        if density >= min_density and n >= 3:
            for a in c:
                if a in idx_of:
                    pred[idx_of[a]] = cid
            cid += 1
    return pred


def kcore_louvain_pred(G_nx, node_ids, kmin=2):
    """A2：k-core 分解，仅在 k>=kmin 核心子图上 Louvain。
    核心外节点归背景(-1)。"""
    core = nx.core_number(G_nx)
    core_nodes = [a for a in node_ids if core.get(a, 0) >= kmin]
    if len(core_nodes) < 3:
        return np.full(len(node_ids), -1, dtype=int)
    Gc = G_nx.subgraph(core_nodes).copy()
    comms = louvain_communities(Gc, weight=None)
    idx_of = {a: i for i, a in enumerate(node_ids)}
    pred = np.full(len(node_ids), -1, dtype=int)
    for ci, c in enumerate(comms):
        for a in c:
            if a in idx_of:
                pred[idx_of[a]] = ci
    return pred


def kcore_plus_dense_pred(G_nx, node_ids, kmin=3, min_density=2.5):
    """A3：k-core 核心子图 + 稠密社区过滤（A1 与 A2 的组合）。"""
    core = nx.core_number(G_nx)
    core_nodes = [a for a in node_ids if core.get(a, 0) >= kmin]
    if len(core_nodes) < 3:
        return np.full(len(node_ids), -1, dtype=int)
    Gc = G_nx.subgraph(core_nodes).copy()
    comms = louvain_communities(Gc, weight=None)
    idx_of = {a: i for i, a in enumerate(node_ids)}
    pred = np.full(len(node_ids), -1, dtype=int)
    cid = 0
    for c in comms:
        sub = Gc.subgraph(c)
        n = sub.number_of_nodes()
        m = sub.number_of_edges()
        density = (2.0 * m) / n if n > 0 else 0.0
        if density >= min_density and n >= 3:
            for a in c:
                if a in idx_of:
                    pred[idx_of[a]] = cid
            cid += 1
    return pred


def main():
    t0 = time.time()
    print("[load] AMLSim canonical ...", flush=True)
    account_ids, edges, gt = load_amlsim(DATA_DIR)
    n_rings = len(set(v for v in gt.values() if v >= 0))
    print(f"[load] accounts={len(account_ids)} edges={len(edges)} rings={n_rings}", flush=True)

    print(f"[subgraph] anchors={N_ANCHOR_RINGS}rings k={K_HOP}hop max_nodes={MAX_NODES}", flush=True)
    sub_txs, sub_gt, n_anchors = extract_anchor_subgraph(account_ids, edges, gt)
    print(f"[subgraph] txs={len(sub_txs)} nodes={len(sub_gt)}", flush=True)

    g = build_account_graph(sub_txs)
    node_ids = g["node_ids"]
    G_nx = g["G"].to_undirected()
    # 移除自环（nx.core_number / Louvain 均不允许自环）
    G_nx.remove_edges_from(nx.selfloop_edges(G_nx))
    gt_arr = np.array([sub_gt[a] for a in node_ids], dtype=int)
    present_rings = len(set(v for v in gt_arr if v >= 0))
    print(f"[build] graph nodes={len(node_ids)} edges={G_nx.number_of_edges()} "
          f"present_rings={present_rings}", flush=True)

    results = {}

    # ---- A1：dense-louvain（固定密度阈值扫描，如实全报） ----
    for md in [1.5, 2.0, 2.5, 3.0]:
        pred = dense_louvain_pred(G_nx, node_ids, min_density=md)
        results[f"A1_dense-louvain(md={md})"] = evaluate(pred, gt_arr)
        print(f"  A1 md={md} F1={results[f'A1_dense-louvain(md={md})']['f1']:.4f} "
              f"ringF1={results[f'A1_dense-louvain(md={md})']['ring_only_f1']:.4f}", flush=True)

    # ---- A2：kcore-louvain（kmin 扫描） ----
    for kmin in [2, 3, 4]:
        pred = kcore_louvain_pred(G_nx, node_ids, kmin=kmin)
        results[f"A2_kcore-louvain(kmin={kmin})"] = evaluate(pred, gt_arr)
        print(f"  A2 kmin={kmin} F1={results[f'A2_kcore-louvain(kmin={kmin})']['f1']:.4f} "
              f"ringF1={results[f'A2_kcore-louvain(kmin={kmin})']['ring_only_f1']:.4f}", flush=True)

    # ---- A3：kcore+dense 组合 ----
    for kmin, md in [(3, 2.5), (4, 3.0)]:
        pred = kcore_plus_dense_pred(G_nx, node_ids, kmin=kmin, min_density=md)
        results[f"A3_kcore+dense(k={kmin},md={md})"] = evaluate(pred, gt_arr)
        print(f"  A3 k={kmin} md={md} F1={results[f'A3_kcore+dense(k={kmin},md={md})']['f1']:.4f} "
              f"ringF1={results[f'A3_kcore+dense(k={kmin},md={md})']['ring_only_f1']:.4f}", flush=True)

    # ---- 对照基线（同子图重跑，保证同口径） ----
    from networkx.algorithms.community import louvain_communities as _lc
    comms = _lc(G_nx, weight=None)
    idx_of = {a: i for i, a in enumerate(node_ids)}
    pred_l = np.zeros(len(node_ids), dtype=int)
    for ci, c in enumerate(comms):
        for a in c:
            if a in idx_of:
                pred_l[idx_of[a]] = ci
    results["baseline_Louvain(topology)"] = evaluate(pred_l, gt_arr)
    print(f"  baseline Louvain F1={results['baseline_Louvain(topology)']['f1']:.4f} "
          f"ringF1={results['baseline_Louvain(topology)']['ring_only_f1']:.4f}", flush=True)

    setting = {
        "data_dir": DATA_DIR, "n_anchor_rings": N_ANCHOR_RINGS, "k_hop": K_HOP,
        "max_nodes": MAX_NODES, "n_subgraph_nodes": len(node_ids),
        "n_subgraph_edges": G_nx.number_of_edges(), "n_present_rings": present_rings,
        "blind_baseline_f1": 0.002,
        "note": "Path B 分支 A：无监督稠密子图发现。阈值扫描如实全报，不针对 GT 选优。"
                "AMLSim 为公开合成基准，不构成真实警务数据验证通过。",
    }
    out = {"setting": setting, "results": results, "elapsed_s": round(time.time() - t0, 1)}
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"\n[saved] {OUT_PATH}  ({time.time()-t0:.1f}s)")
    print("\n=== F1 对比（诚实口径：盲扫基线≈0.002） ===")
    for k, v in results.items():
        print(f"  {k:28s} F1={v['f1']:.4f}  ringF1={v['ring_only_f1']:.4f}")


if __name__ == "__main__":
    main()
