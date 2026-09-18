"""
Path B · 组合实验：短环 ∩ k-core 核心（"高置信资金链团伙"）
================================================================
假设：短环成员（资金链信号）∩ k-core 核心（结构稠密）的节点
既"有资金回流"又"结构可靠"，precision 应高于任一单方法。

同时输出"命中的候选环明细"（供民警视角人工验证）：
对每个预测候选集合，列出其命中的真值环成员及其交易结构（金额/时间），
人工判断"像不像洗钱"——这是论文/答辩最加分的诚实验证材料。

设定：k=1 扩线 / 120 锚点 / 2748 节点子图（与 pathb_pipeline 同口径）。
评测：节点级 precision/recall/F1，对照单方法（短环 / kcore 单独）。

输出：backend/gnn/pathb_combine_final_results.json
"""
from __future__ import annotations

import json
import os
import sys
import time
from collections import defaultdict

import networkx as nx
import numpy as np

BACKEND = os.path.dirname(os.path.abspath(__file__))
for p in (BACKEND, os.path.dirname(BACKEND)):
    if p not in sys.path:
        sys.path.insert(0, p)

from networkx.algorithms.community import louvain_communities  # noqa: E402
from gnn.account_temporal import build_account_graph  # noqa: E402
from gnn.adapters.amlsim_adapter import load_amlsim  # noqa: E402

DATA_DIR = os.path.join(BACKEND, "amlsim_real", "canonical")
OUT_PATH = os.path.join(BACKEND, "pathb_combine_final_results.json")
N_ANCHOR_RINGS, K_HOP, MAX_NODES = 120, 1, 8000
KMIN_LIST = [2, 3, 4]
MAX_CYCLE_LEN = 6
N_INSPECT = 10  # 民警视角抽验候选数


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
    H = np.bincount(pred * n_gt + gt, minlength=n_pred * n_gt).reshape(n_pred, n_gt).astype(np.int64)
    c2 = H * (H - 1) // 2
    TP = int(c2.sum())
    row, col = H.sum(axis=1), H.sum(axis=0)
    FP = int((row * (row - 1) // 2).sum()) - TP
    FN = int((col * (col - 1) // 2).sum()) - TP
    prec = TP / (TP + FP) if (TP + FP) > 0 else 0.0
    rec = TP / (TP + FN) if (TP + FN) > 0 else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0
    return f1, prec, rec


def node_prf(pred_members, gt_members):
    pred, gt = set(pred_members), set(gt_members)
    tp = len(pred & gt)
    prec = tp / len(pred) if pred else 0.0
    rec = tp / max(len(gt), 1)
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0
    return round(prec, 4), round(rec, 4), round(f1, 4)


def extract_anchor_subgraph(account_ids, edges, gt, n_anchor_rings, k_hop, max_nodes):
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
    return sub_txs, sub_gt, anchors


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


def on_short_cycle_mask(G_dir, node_ids, max_len=MAX_CYCLE_LEN):
    adj_out = defaultdict(list)
    for u, v in G_dir.edges():
        adj_out[u].append(v)
    mask = np.zeros(len(node_ids), dtype=bool)
    for i, a in enumerate(node_ids):
        if _has_short_cycle(a, adj_out, max_len):
            mask[i] = True
    return mask


def main():
    t0 = time.time()
    print("[load] AMLSim canonical ...", flush=True)
    account_ids, edges, gt = load_amlsim(DATA_DIR)
    sub_txs, sub_gt, anchors = extract_anchor_subgraph(
        account_ids, edges, gt, N_ANCHOR_RINGS, K_HOP, MAX_NODES)
    print(f"[subgraph] anchors={len(anchors)} txs={len(sub_txs)} nodes={len(sub_gt)}", flush=True)

    g = build_account_graph(sub_txs)
    node_ids = g["node_ids"]
    G_dir = g["G"]
    G_und = G_dir.to_undirected()
    G_und.remove_edges_from(nx.selfloop_edges(G_und))
    gt_arr = np.array([sub_gt[a] for a in node_ids], dtype=int)
    ring_mask = gt_arr >= 0
    gt_members = set(node_ids[i] for i in range(len(node_ids)) if ring_mask[i])
    n, n_ring = len(node_ids), int(ring_mask.sum())
    print(f"[build] nodes={n} edges_dir={G_dir.number_of_edges()} rings={n_ring} "
          f"ratio={n_ring/n:.3f}", flush=True)

    # 短环成员
    cyc_mask = on_short_cycle_mask(G_dir, node_ids)
    cycle_members = set(node_ids[i] for i in range(len(node_ids)) if cyc_mask[i])
    print(f"[short-cycle] members={len(cycle_members)}", flush=True)
    p_c, r_c, f_c = node_prf(cycle_members, gt_members)
    print(f"  short-cycle alone: P={p_c} R={r_c} F1={f_c}", flush=True)

    core = nx.core_number(G_und)
    results = {"setting": {}, "combine": {}, "single": {}, "inspection": {}}
    results["setting"] = {
        "data_dir": DATA_DIR, "n_anchor_rings": N_ANCHOR_RINGS, "k_hop": K_HOP,
        "max_nodes": MAX_NODES, "n_subgraph_nodes": n, "n_in_rings": n_ring,
        "ring_ratio": round(n_ring / n, 4), "max_cycle_len": MAX_CYCLE_LEN,
        "blind_baseline_f1": 0.002,
        "note": "Path B 组合实验：短环∩kcore。无监督固定参数；AMLSim 公开合成基准非真实验证。",
    }
    results["single"]["short_cycle"] = {"precision": p_c, "recall": r_c, "F1": f_c}

    # kcore 单独（budget=全核心）与 组合（短环∩kcore）
    for kmin in KMIN_LIST:
        core_set = {a for a in node_ids if core.get(a, 0) >= kmin}
        # kcore 单独
        if len(core_set) >= 3:
            p_k, r_k, f_k = node_prf(core_set, gt_members)
            results["single"][f"kcore{kmin}"] = {"n": len(core_set), "precision": p_k,
                                                 "recall": r_k, "F1": f_k}
            print(f"  kcore{kmin} alone: n={len(core_set)} P={p_k} R={r_k} F1={f_k}", flush=True)
        # 组合：短环 ∩ kcore
        comb = cycle_members & core_set
        if len(comb) >= 3:
            p_x, r_x, f_x = node_prf(comb, gt_members)
            results["combine"][f"short∩kcore{kmin}"] = {"n": len(comb), "precision": p_x,
                                                        "recall": r_x, "F1": f_x}
            print(f"  short∩kcore{kmin}: n={len(comb)} P={p_x} R={r_x} F1={f_x}", flush=True)

    # 民警视角验证：抽命中真值环的候选（从组合最优 kmin 或短环中抽）
    best_kmin = max(KMIN_LIST, key=lambda k: results["combine"].get(
        f"short∩kcore{k}", {}).get("F1", 0))
    comb_best = cycle_members & {a for a in node_ids if core.get(a, 0) >= best_kmin}
    # 按真值环分组统计命中情况
    ring_of = defaultdict(list)
    for a in comb_best:
        rid = sub_gt.get(a, -1)
        if rid >= 0:
            ring_of[rid].append(a)
    ring_hits = sorted(ring_of.items(), key=lambda x: -len(x[1]))[:N_INSPECT]
    print(f"  [inspect] top {len(ring_hits)} hit rings from short∩kcore{best_kmin}", flush=True)

    tx_by_pair = {}
    for tx in sub_txs:
        tx_by_pair[(tx["from_account"], tx["to_account"])] = tx
    inspections = []
    for rid, members in ring_hits:
        members_set = set(members)
        in_edges, out_edges = [], []
        for tx in sub_txs:
            s, d = tx["from_account"], tx["to_account"]
            if s in members_set and d in members_set:
                in_edges.append({"from": s, "to": d, "amount": tx.get("amount"),
                                 "ts": tx.get("timestamp")})
            elif s in members_set:
                out_edges.append({"from": s, "to": d, "amount": tx.get("amount"),
                                  "ts": tx.get("timestamp")})
        inspections.append({
            "ring_id": int(rid), "n_members_hit": len(members),
            "n_ring_total": sum(1 for a in node_ids if sub_gt.get(a) == rid),
            "members": sorted(members)[:12],
            "n_internal_edges": len(in_edges),
            "n_outgoing_edges": len(out_edges),
            "sample_internal_edges": in_edges[:8],
        })
        print(f"    ring {rid}: hit={len(members)} internal_edges={len(in_edges)} "
              f"out={len(out_edges)}", flush=True)
    results["inspection"]["best_kmin"] = best_kmin
    results["inspection"]["rings"] = inspections

    out = {"setting": results["setting"], "single": results["single"],
           "combine": results["combine"], "inspection": results["inspection"],
           "elapsed_s": round(time.time() - t0, 1)}
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"\n[saved] {OUT_PATH} ({time.time()-t0:.1f}s)")


if __name__ == "__main__":
    main()
