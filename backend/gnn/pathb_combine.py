"""
Path B · 实验 1：A2×C 交叉验证组合（AMLSim 锚点扩线）
================================================================
组合思路：
  A2（kcore-louvain，拓扑）出"核心子图候选团伙"；
  C（规则探测器）在 A2 候选内做"规则排序"，识别最可疑的候选；
  评测组合是否优于单方法（A2 的 F1、C 的 AUC/precision@k）。

方法对比：
  - A2 单独（kmin=4）：pairwise F1
  - C 单独：规则分数 top-k / AUC
  - A2+C：仅在 A2 核心成员上计算 C 分数 → 排序 → top-k 命中率；
          以及"A2 候选团伙内规则分均值"排序 → 团伙级评估
诚实口径：无监督、固定参数、不针对 GT 调优；AMLSim 公开合成基准非真实验证。

输出：backend/gnn/pathb_combine_results.json
"""
from __future__ import annotations

import json
import os
import sys
import time
from collections import defaultdict

import networkx as nx
import numpy as np
from networkx.algorithms.community import louvain_communities
from sklearn.metrics import roc_auc_score

BACKEND = os.path.dirname(os.path.abspath(__file__))
for p in (BACKEND, os.path.dirname(BACKEND)):
    if p not in sys.path:
        sys.path.insert(0, p)

from gnn.account_temporal import build_account_graph  # noqa: E402
from gnn.adapters.amlsim_adapter import load_amlsim  # noqa: E402

DATA_DIR = os.path.join(BACKEND, "amlsim_real", "canonical")
OUT_PATH = os.path.join(BACKEND, "pathb_combine_results.json")
N_ANCHOR_RINGS, K_HOP, MAX_NODES = 60, 2, 8000
KMIN = 4  # A2 最佳 kmin（来自首轮实验，非调优——首轮即固定并如实报告）


# ---------- 评测工具（与 pathb_dense_subgraph 一致） ----------
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
    row, col = H.sum(axis=1), H.sum(axis=0)
    FP = int((row * (row - 1) // 2).sum()) - TP
    FN = int((col * (col - 1) // 2).sum()) - TP
    prec = TP / (TP + FP) if (TP + FP) > 0 else 0.0
    rec = TP / (TP + FN) if (TP + FN) > 0 else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0
    return f1, prec, rec


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
    chosen = list(ring_of.keys())[:n_anchor_rings]
    anchors = [ring_of[r][0] for r in chosen]
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
    sub = list(seen)
    sub_set = set(sub)
    sub_txs = [{"from_account": s, "to_account": d, "amount": amt, "timestamp": ts}
               for (s, d, amt, ts) in edges if s in sub_set and d in sub_set]
    sub_gt = {a: gt.get(a, -1) for a in sub}
    return sub_txs, sub_gt, len(anchors)


# ---------- A2 核心子图（返回核心成员集合与社区归属） ----------
def a2_core(G_nx, node_ids, kmin=KMIN):
    core = nx.core_number(G_nx)
    core_set = {a for a in node_ids if core.get(a, 0) >= kmin}
    return core_set


# ---------- C 规则分数（复用 pathb_rule_detector 逻辑） ----------
def compute_rule_scores(sub_txs, accounts):
    in_amt, out_amt = defaultdict(list), defaultdict(list)
    in_ts, out_ts = defaultdict(list), defaultdict(list)
    adj_out, adj_in = defaultdict(list), defaultdict(list)
    for tx in sub_txs:
        s, d = tx["from_account"], tx["to_account"]
        amt, ts = tx.get("amount"), tx.get("timestamp")
        out_amt[s].append(float(amt))
        in_amt[d].append(float(amt))
        if ts is not None:
            out_ts[s].append(float(ts))
            in_ts[d].append(float(ts))
        adj_out[s].append(d)
        adj_in[d].append(s)
    scores = {}
    for a in accounts:
        s = {"R1_int_split": 0.0, "R2_fast_flow": 0.0, "R3_short_cycle": 0.0,
             "R4_imbalance": 0.0, "R5_large_outlier": 0.0}
        ins, outs = in_amt.get(a, []), out_amt.get(a, [])
        if ins:
            whole = sum(1 for v in ins if v > 0 and v % 1000 == 0)
            s["R1_int_split"] = min(whole / max(len(ins), 1) * 2.0, 1.0)
        if ins and outs and in_ts and out_ts:
            it, ot = sorted(in_ts.get(a, [])), sorted(out_ts.get(a, []))
            fast = 0
            for t_in in it:
                for t_out in ot:
                    if 0 <= (t_out - t_in) <= 1.0:
                        fast += 1
                        break
            s["R2_fast_flow"] = min(fast / max(len(it), 1) * 2.0, 1.0)
        if a in adj_out and a in adj_in:
            s["R3_short_cycle"] = _has_short_cycle(a, adj_out, 4)
        in_t, out_t = sum(ins), sum(outs)
        denom = max(in_t, out_t, 1e-9)
        s["R4_imbalance"] = min(abs(in_t - out_t) / denom * 2.0, 1.0)
        if ins:
            med = float(np.median(ins))
            if med > 0:
                big = sum(1 for v in ins if v >= med * 5)
                s["R5_large_outlier"] = min(big / max(len(ins), 1) * 2.0, 1.0)
        final = 0.30 * s["R1_int_split"] + 0.25 * s["R2_fast_flow"] + \
                0.25 * s["R3_short_cycle"] + 0.10 * s["R4_imbalance"] + 0.10 * s["R5_large_outlier"]
        scores[a] = {**s, "final": final}
    return scores


def _has_short_cycle(start, adj_out, max_len):
    from collections import deque
    visited = {start}
    q = deque([(start, 0)])
    while q:
        node, depth = q.popleft()
        if depth + 1 > max_len:
            continue
        for nb in adj_out.get(node, []):
            if nb == start:
                return 1.0
            if nb not in visited:
                visited.add(nb)
                q.append((nb, depth + 1))
    return 0.0


def topk_metrics(score_order, accounts, sub_gt, ring_mask, n, n_ring, name, out):
    for k_ratio in [0.05, 0.1, 0.2]:
        k = max(int(n * k_ratio), 1)
        topk = score_order[:k]
        hit = sum(1 for a in topk if sub_gt[a] >= 0)
        out[f"{name}_top{k_ratio:.0%}"] = {"k": k, "hits_in_rings": hit,
                                           "ring_coverage": round(hit / max(n_ring, 1), 4),
                                           "precision_at_k": round(hit / k, 4)}
        print(f"  {name} top{k_ratio:.0%}(k={k}): ring_hits={hit}/{n_ring} "
              f"prec={hit/k:.4f}", flush=True)


def main():
    t0 = time.time()
    print("[load] AMLSim canonical ...", flush=True)
    account_ids, edges, gt = load_amlsim(DATA_DIR)
    print(f"[load] accounts={len(account_ids)} edges={len(edges)}", flush=True)

    sub_txs, sub_gt, n_anchors = extract_anchor_subgraph(account_ids, edges, gt)
    print(f"[subgraph] anchors={n_anchors} txs={len(sub_txs)} nodes={len(sub_gt)}", flush=True)

    g = build_account_graph(sub_txs)
    node_ids = g["node_ids"]
    G_nx = g["G"].to_undirected()
    G_nx.remove_edges_from(nx.selfloop_edges(G_nx))
    gt_arr = np.array([sub_gt[a] for a in node_ids], dtype=int)
    ring_mask = gt_arr >= 0
    n, n_ring = len(node_ids), int(ring_mask.sum())
    print(f"[build] nodes={n} edges={G_nx.number_of_edges()} rings={n_ring} "
          f"ring_ratio={n_ring/n:.3f}", flush=True)

    results = {}

    # ---- A2 单独：pairwise F1 ----
    core_set = a2_core(G_nx, node_ids, kmin=KMIN)
    Gc = G_nx.subgraph(sorted(core_set)).copy()
    comms = louvain_communities(Gc, weight=None)
    idx_of = {a: i for i, a in enumerate(node_ids)}
    pred_a2 = np.full(n, -1, dtype=int)
    for ci, c in enumerate(comms):
        for a in c:
            if a in idx_of:
                pred_a2[idx_of[a]] = ci
    results["A2_kcore(kmin=4)_F1"] = pairwise_f1(pred_a2, gt_arr)[0]
    print(f"  A2 F1 = {results['A2_kcore(kmin=4)_F1']:.4f}", flush=True)

    # ---- C 单独：规则排序 ----
    scores = compute_rule_scores(sub_txs, node_ids)
    score_arr = np.array([scores[a]["final"] for a in node_ids])
    y_bin = ring_mask.astype(int)
    if y_bin.sum() > 0 and y_bin.sum() < n:
        results["C_rule_AUC"] = round(float(roc_auc_score(y_bin, score_arr)), 4)
        print(f"  C AUC = {results['C_rule_AUC']}", flush=True)
    order_c = sorted(node_ids, key=lambda a: scores[a]["final"], reverse=True)
    topk_metrics(order_c, node_ids, sub_gt, ring_mask, n, n_ring, "C_rule", results)

    # ---- A2+C：仅在 A2 核心成员上计算规则分排序 ----
    core_list = [a for a in node_ids if a in core_set]
    if core_list:
        sub_core_score = np.array([scores[a]["final"] for a in core_list])
        core_ring = np.array([sub_gt[a] >= 0 for a in core_list], dtype=int)
        if core_ring.sum() > 0 and core_ring.sum() < len(core_ring) and len(set(sub_core_score.tolist())) > 1:
            results["A2C_core_rule_AUC"] = round(float(roc_auc_score(core_ring, sub_core_score)), 4)
            print(f"  A2+C (core-only) AUC = {results['A2C_core_rule_AUC']}", flush=True)
        order_ac = sorted(core_list, key=lambda a: scores[a]["final"], reverse=True)
        topk_metrics(order_ac, node_ids, sub_gt, ring_mask, n, n_ring, "A2C_core", results)

    # ---- A2+C 交叉：A2 候选团伙内规则分均值 → 团伙级排序 ----
    gang_scores = []
    for ci, c in enumerate(comms):
        sc = [scores[a]["final"] for a in c if a in scores]
        if sc:
            gang_scores.append((ci, float(np.mean(sc)), len(c)))
    gang_scores.sort(key=lambda x: x[1], reverse=True)
    results["A2C_gang_mean_rule"] = {"n_gangs": len(gang_scores),
                                     "top_gangs": [{"gang": gi, "mean_rule": round(m, 3), "size": s}
                                                   for gi, m, s in gang_scores[:10]]}
    print(f"  A2C gang-level: {len(gang_scores)} gangs, top3 mean_rule="
          f"{[round(x[1],3) for x in gang_scores[:3]]}", flush=True)

    setting = {
        "data_dir": DATA_DIR, "n_anchor_rings": N_ANCHOR_RINGS, "k_hop": K_HOP,
        "max_nodes": MAX_NODES, "kmin": KMIN, "n_subgraph_nodes": n,
        "n_in_rings": n_ring, "ring_ratio": round(n_ring / n, 4), "blind_baseline_f1": 0.002,
        "note": "Path B 实验 1：A2×C 交叉验证。A2 出核心子图候选，C 规则在候选内排序。"
                "固定参数不调优；AMLSim 公开合成基准，不构成真实验证通过。",
    }
    out = {"setting": setting, "results": results, "elapsed_s": round(time.time() - t0, 1)}
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"\n[saved] {OUT_PATH} ({time.time()-t0:.1f}s)")


if __name__ == "__main__":
    main()
