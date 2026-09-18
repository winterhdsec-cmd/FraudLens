"""
Path B · 实验 2：扩线参数敏感性扫描（AMLSim）
================================================================
扫描：k_hop ∈ {1, 2, 3} × n_anchor_rings ∈ {30, 60, 120}
方法：A2 kcore-louvain(kmin=4) 的 pairwise F1；C 规则合成分的 AUC。
目的：回答"扩线设定对无监督方法有多敏感"——结果随锚点/子图参数
剧烈变化（honest_note 已提示），量化这一敏感性是诚实报告的关键部分。

诚实口径：全部无监督、固定方法参数；AMLSim 公开合成基准非真实验证。

输出：backend/gnn/pathb_sensitivity_results.json
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
OUT_PATH = os.path.join(BACKEND, "pathb_sensitivity_results.json")
MAX_NODES = 8000
KMIN = 4
KHOPS = [1, 2, 3]
N_ANCHOR_LIST = [30, 60, 120]


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
    return sub_txs, sub_gt, len(anchors)


def a2_pred(G_nx, node_ids, kmin=KMIN):
    core = nx.core_number(G_nx)
    core_set = {a for a in node_ids if core.get(a, 0) >= kmin}
    if len(core_set) < 3:
        return np.full(len(node_ids), -1, dtype=int)
    Gc = G_nx.subgraph(sorted(core_set)).copy()
    comms = louvain_communities(Gc, weight=None)
    idx_of = {a: i for i, a in enumerate(node_ids)}
    pred = np.full(len(node_ids), -1, dtype=int)
    for ci, c in enumerate(comms):
        for a in c:
            if a in idx_of:
                pred[idx_of[a]] = ci
    return pred


def rule_auc(sub_txs, node_ids, gt_arr):
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
    scores = []
    for a in node_ids:
        s = {"R1": 0.0, "R2": 0.0, "R3": 0.0, "R4": 0.0, "R5": 0.0}
        ins, outs = in_amt.get(a, []), out_amt.get(a, [])
        if ins:
            whole = sum(1 for v in ins if v > 0 and v % 1000 == 0)
            s["R1"] = min(whole / max(len(ins), 1) * 2.0, 1.0)
        if ins and outs and in_ts and out_ts:
            it, ot = sorted(in_ts.get(a, [])), sorted(out_ts.get(a, []))
            fast = 0
            for t_in in it:
                for t_out in ot:
                    if 0 <= (t_out - t_in) <= 1.0:
                        fast += 1
                        break
            s["R2"] = min(fast / max(len(it), 1) * 2.0, 1.0)
        if a in adj_out and a in adj_in:
            s["R3"] = _has_short_cycle(a, adj_out, 4)
        in_t, out_t = sum(ins), sum(outs)
        denom = max(in_t, out_t, 1e-9)
        s["R4"] = min(abs(in_t - out_t) / denom * 2.0, 1.0)
        if ins:
            med = float(np.median(ins))
            if med > 0:
                big = sum(1 for v in ins if v >= med * 5)
                s["R5"] = min(big / max(len(ins), 1) * 2.0, 1.0)
        final = 0.30 * s["R1"] + 0.25 * s["R2"] + 0.25 * s["R3"] + 0.10 * s["R4"] + 0.10 * s["R5"]
        scores.append(final)
    y_bin = (gt_arr >= 0).astype(int)
    if y_bin.sum() > 0 and y_bin.sum() < len(y_bin) and len(set(scores)) > 1:
        return round(float(roc_auc_score(y_bin, np.array(scores))), 4)
    return None


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


def main():
    t0 = time.time()
    print("[load] AMLSim canonical ...", flush=True)
    account_ids, edges, gt = load_amlsim(DATA_DIR)
    print(f"[load] accounts={len(account_ids)} edges={len(edges)}", flush=True)

    grid = {}
    for kh in KHOPS:
        for na in N_ANCHOR_LIST:
            sub_txs, sub_gt, n_anchors = extract_anchor_subgraph(
                account_ids, edges, gt, n_anchor_rings=na, k_hop=kh, max_nodes=MAX_NODES)
            g = build_account_graph(sub_txs)
            node_ids = g["node_ids"]
            G_nx = g["G"].to_undirected()
            G_nx.remove_edges_from(nx.selfloop_edges(G_nx))
            gt_arr = np.array([sub_gt[a] for a in node_ids], dtype=int)
            n = len(node_ids)
            n_ring = int((gt_arr >= 0).sum())

            pred = a2_pred(G_nx, node_ids, kmin=KMIN)
            f1_a2, _, _ = pairwise_f1(pred, gt_arr)
            auc_c = rule_auc(sub_txs, node_ids, gt_arr)

            key = f"k{kh}_a{na}"
            grid[key] = {"k_hop": kh, "n_anchor_rings": na, "n_sub": n,
                         "n_rings_sub": n_ring, "ring_ratio": round(n_ring / max(n, 1), 4),
                         "A2_F1": round(f1_a2, 4), "C_rule_AUC": auc_c}
            print(f"  {key}: n={n} rings={n_ring} ratio={n_ring/max(n,1):.3f} "
                  f"A2_F1={f1_a2:.4f} C_AUC={auc_c}", flush=True)

    setting = {
        "data_dir": DATA_DIR, "k_hops": KHOPS, "n_anchor_list": N_ANCHOR_LIST,
        "max_nodes": MAX_NODES, "kmin": KMIN, "blind_baseline_f1": 0.002,
        "note": "Path B 实验 2：扩线参数敏感性。结果随锚点/子图参数剧烈变化属预期（honest_note），"
                "本表量化该敏感性；AMLSim 公开合成基准，不构成真实验证通过。",
    }
    out = {"setting": setting, "grid": grid, "elapsed_s": round(time.time() - t0, 1)}
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"\n[saved] {OUT_PATH} ({time.time()-t0:.1f}s)")


if __name__ == "__main__":
    main()
