"""
Path B · 第六轮冲刺：短环 L=8 新信号突破 0.71 上限
================================================================
背景：短环 L≤8 发现 recall 0.61（vs L≤6 的 0.40），此前融合实验均用 L≤6。
这一轮用 L=8 的更强环信号做多种结合策略，目标是突破 kcore2 F1=0.709。

策略（5 种未探索方向）：
  S1 硬交集：kcore2 ∩ L8 短环（只保留双信号节点）— 预期高 P 中 R
  S2 混合留存：kcore2 内，L8 成员全留 + 其余按融合分排序取 top（保 L8 recall 地板）
  S3 并集融合：kcore2 ∪ L8 全部节点，按融合分取 top-k — 预期最大 recall
  S4 社区过滤：kcore2 内 Louvain 社区，按"短环比例 + 规则分"排序取 top-k
  S5 软加权 Kmin×L8：kmin 2/3/4 全核心分别与 L8 做软交集（保留各自 kcore 但与 L8 交集排序）

全部固定参数，如实全报。AMLSim 公开合成基准非真实验证。
输出：backend/gnn/pathb_final_push_results.json
"""
from __future__ import annotations

import json, os, sys, time
from collections import defaultdict
import numpy as np
import networkx as nx
from networkx.algorithms.community import louvain_communities

BACKEND = os.path.dirname(os.path.abspath(__file__))
for p in (BACKEND, os.path.dirname(BACKEND)):
    if p not in sys.path:
        sys.path.insert(0, p)
from gnn.account_temporal import build_account_graph
from gnn.adapters.amlsim_adapter import load_amlsim

DATA_DIR = os.path.join(BACKEND, "amlsim_real", "canonical")
OUT_PATH = os.path.join(BACKEND, "pathb_final_push_results.json")
N_ANCHOR_RINGS, K_HOP, MAX_NODES = 120, 1, 8000
CYCLE_LEN = 8
TOP_K_RATIOS = [0.30, 0.50, 0.70, 0.90]
WEIGHTS = [
    ("balanced", (0.34, 0.33, 0.33)),
    ("structure_dom", (0.5, 0.3, 0.2)),
    ("cycle_dom", (0.2, 0.5, 0.3)),
]


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


def on_cycle_mask(G_dir, node_ids, max_len):
    adj_out = defaultdict(list)
    for u, v in G_dir.edges():
        adj_out[u].append(v)
    mask = np.zeros(len(node_ids), dtype=bool)
    for i, a in enumerate(node_ids):
        if _has_short_cycle(a, adj_out, max_len):
            mask[i] = True
    return mask


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
        scores[a] = final
    return scores


def node_prf(pred, gt):
    pred, gt = set(pred), set(gt)
    tp = len(pred & gt)
    prec = tp / len(pred) if pred else 0.0
    rec = tp / max(len(gt), 1)
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0
    return round(prec, 4), round(rec, 4), round(f1, 4)


def main():
    t0 = time.time()
    print("[load]", flush=True)
    account_ids, edges, gt = load_amlsim(DATA_DIR)
    sub_txs, sub_gt, anchors = extract_anchor_subgraph(
        account_ids, edges, gt, N_ANCHOR_RINGS, K_HOP, MAX_NODES)
    g = build_account_graph(sub_txs)
    node_ids = g["node_ids"]
    G_dir = g["G"]
    G_und = G_dir.to_undirected()
    G_und.remove_edges_from(nx.selfloop_edges(G_und))
    gt_arr = np.array([sub_gt[a] for a in node_ids], dtype=int)
    gt_members = set(node_ids[i] for i in range(len(node_ids)) if gt_arr[i] >= 0)
    n, n_ring = len(node_ids), int((gt_arr >= 0).sum())
    print(f"[build] nodes={n} edges={G_dir.number_of_edges()} rings={n_ring}/{n}", flush=True)

    # 基础信号
    core = nx.core_number(G_und)
    core_vals = np.array([core.get(a, 0) for a in node_ids], dtype=float)
    s1 = (core_vals - core_vals.min()) / (core_vals.max() - core_vals.min() + 1e-9)
    s2 = on_cycle_mask(G_dir, node_ids, CYCLE_LEN).astype(float)
    rule = compute_rule_scores(sub_txs, node_ids)
    s3 = np.array([rule[a] for a in node_ids], dtype=float)
    s3 = (s3 - s3.min()) / (s3.max() - s3.min() + 1e-9)

    # 成员集合
    L8_members = set(node_ids[i] for i in range(n) if s2[i] == 1)
    kcore2_set = {a for a in node_ids if core.get(a, 0) >= 2}
    kcore3_set = {a for a in node_ids if core.get(a, 0) >= 3}
    kcore4_set = {a for a in node_ids if core.get(a, 0) >= 4}
    print(f"signals: kcore2={len(kcore2_set)} kcore3={len(kcore3_set)} kcore4={len(kcore4_set)} "
          f"L8={len(L8_members)}", flush=True)

    results = {"baselines": {}, "strategies": {}, "best": {}}

    # 基线
    for name, s in [("kcore2", kcore2_set), ("kcore3", kcore3_set),
                    ("kcore4", kcore4_set), ("L8", L8_members)]:
        p, r, f = node_prf(s, gt_members)
        results["baselines"][name] = {"P": p, "R": r, "F1": f, "n": len(s)}
        print(f"  baseline {name}(n={len(s)}): P={p} R={r} F1={f}", flush=True)

    # S1 硬交集：kmin×L8
    strategy = {}
    for km_name, kset in [("kcore2", kcore2_set), ("kcore3", kcore3_set),
                           ("kcore4", kcore4_set)]:
        inter = kset & L8_members
        p, r, f = node_prf(inter, gt_members)
        strategy[f"S1_{km_name}_cap_L8"] = {"P": p, "R": r, "F1": f, "n": len(inter)}
        if f >= 0.55:
            print(f"  S1 {km_name}∩L8: n={len(inter)} P={p} R={r} F1={f}", flush=True)

    # S2 混合留存：kcore 内 L8 全留 + 其余按融合分排序取 top（节点预算）
    for km_name, kset in [("kcore2", kcore2_set)]:
        kcore_list = sorted(kset)
        kcore_idx = [node_ids.index(a) for a in kcore_list]
        kcore_L8 = [a for a in kcore_list if a in L8_members]
        kcore_nonL8 = [a for a in kcore_list if a not in L8_members]
        nk = len(kcore_nonL8)
        if nk < 1:
            continue
        for wname, (w1, w2, w3) in WEIGHTS:
            score = w1 * s1[kcore_idx] + w2 * s2[kcore_idx] + w3 * s3[kcore_idx]
            acct_score = {a: score[i] for i, a in enumerate(kcore_list)}
            for k_ratio in TOP_K_RATIOS:
                budget = int(n * k_ratio)
                pred = set(kcore_L8)
                remaining = budget - len(pred)
                if remaining > 0 and remaining < nk:
                    nonL8_score = [(a, acct_score[a]) for a in kcore_nonL8]
                    nonL8_score.sort(key=lambda x: -x[1])
                    pred |= set(x[0] for x in nonL8_score[:remaining])
                elif remaining >= nk:
                    pred |= set(kcore_nonL8)
                p, r, f = node_prf(pred, gt_members)
                key = f"S2_{km_name}+L8_budget{k_ratio:.0%}_{wname}"
                strategy[key] = {"P": p, "R": r, "F1": f, "n": len(pred)}
                if f >= 0.65:
                    print(f"  {key}: n={len(pred)} P={p} R={r} F1={f}", flush=True)

    # S3 并集融合：kcore2 ∪ L8 全部节点按融合分排序取 top-k
    union_set = kcore2_set | L8_members
    union_list = sorted(union_set)
    union_idx = [node_ids.index(a) for a in union_list]
    for wname, (w1, w2, w3) in WEIGHTS:
        score = w1 * s1[union_idx] + w2 * s2[union_idx] + w3 * s3[union_idx]
        for k_ratio in TOP_K_RATIOS:
            k = max(int(n * k_ratio), 1)
            topk_idx = np.argsort(-score)[:min(k, len(score))]
            pred = set(union_list[i] for i in topk_idx)
            p, r, f = node_prf(pred, gt_members)
            key = f"S3_union_kcore2+L8_k{k_ratio:.0%}_{wname}"
            strategy[key] = {"P": p, "R": r, "F1": f, "n": len(pred)}
            if f >= 0.65:
                print(f"  {key}: n={len(pred)} P={p} R={r} F1={f}", flush=True)

    # S4 社区过滤：kcore2 内 Louvain 社区按"短环成员比例+规则"排序
    Gc = G_und.subgraph(sorted(kcore2_set)).copy()
    comms = louvain_communities(Gc, weight=None)
    comms = [c for c in comms if len(c) >= 3]
    comm_scores = []
    for c in comms:
        l8_ratio = sum(1 for a in c if a in L8_members) / max(len(c), 1)
        rule_mean = float(np.mean([rule.get(a, 0) for a in c]))
        comm_scores.append((c, 0.5 * l8_ratio + 0.5 * rule_mean, l8_ratio, rule_mean))
    comm_scores.sort(key=lambda x: -x[1])
    for frac in [0.3, 0.5, 0.7, 1.0]:
        kc = max(int(len(comm_scores) * frac), 1)
        pred = set()
        for c, _, _, _ in comm_scores[:kc]:
            pred |= set(c)
        p, r, f = node_prf(pred, gt_members)
        strategy[f"S4_comm_filter_top{frac:.0%}"] = {"P": p, "R": r, "F1": f, "n": len(pred)}
        print(f"  S4 top{frac:.0%}社区(L8+规则): n={len(pred)} P={p} R={r} F1={f}", flush=True)

    results["strategies"] = strategy

    # 汇总最佳
    best_key = max(strategy.items(), key=lambda x: x[1]["F1"])
    results["best"] = {"config": best_key[0], **best_key[1]}
    baseline_best_key = max(results["baselines"].items(), key=lambda x: x[1]["F1"])
    print(f"\n=== BASELINE BEST: {baseline_best_key[0]} F1={baseline_best_key[1]['F1']} ===")
    print(f"=== STRATEGY BEST: {best_key[0]} F1={best_key[1]['F1']} "
          f"P={best_key[1]['P']} R={best_key[1]['R']} ===")

    setting = {
        "n_subgraph_nodes": n, "n_in_rings": n_ring, "cycle_len": CYCLE_LEN,
        "blind_baseline_f1": 0.002,
        "note": "Path B 第六轮冲刺：L=8 短环信号×kcore×规则的新结合策略。"
                "固定参数如实全报；AMLSim 公开合成基准非真实验证。",
    }
    out = {"setting": setting, "baselines": results["baselines"],
           "strategies": results["strategies"], "best": results["best"],
           "elapsed_s": round(time.time() - t0, 1)}
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"[saved] {OUT_PATH} ({time.time()-t0:.1f}s)")


if __name__ == "__main__":
    main()
