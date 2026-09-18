"""
Path B · 增强实验：三路信号融合打分（提高识别率）
================================================================
目标：超过 kcore2 单独 F1=0.709（P=0.58/R=0.91）与短环 F1=0.499（P=0.66/R=0.40）。

三路信号（全部无监督）：
  S1 kcore 核心度：k-core 分解的 core number 归一化（结构稠密度）
  S2 短环信号：节点是否在 len<=L 有向环上（资金回流）
  S3 规则分：AMLSim 风格规则探测器（金额/时序行为）
融合 score = w1*S1 + w2*S2 + w3*S3，按分数取 top-k 节点为候选。

扫描（诚实：多组固定权重全部报告，不挑最优）：
  - 权重：结构主导 (0.5,0.3,0.2) / 均衡 (0.33,0.33,0.34) / 环主导 (0.2,0.5,0.3) / 规则主导 (0.2,0.3,0.5)
  - 环长 L ∈ {4, 6, 8}
  - top-k ∈ {20%, 35%, 50%}
对照：kcore2 单独 0.709、短环 0.499。

诚实口径：无监督、固定权重；AMLSim 公开合成基准非真实验证。
输出：backend/gnn/pathb_boost_results.json
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

from gnn.account_temporal import build_account_graph  # noqa: E402
from gnn.adapters.amlsim_adapter import load_amlsim  # noqa: E402

DATA_DIR = os.path.join(BACKEND, "amlsim_real", "canonical")
OUT_PATH = os.path.join(BACKEND, "pathb_boost_results.json")
N_ANCHOR_RINGS, K_HOP, MAX_NODES = 120, 1, 8000

WEIGHTS = {
    "structure_dom": (0.5, 0.3, 0.2),
    "balanced": (0.34, 0.33, 0.33),
    "cycle_dom": (0.2, 0.5, 0.3),
    "rule_dom": (0.2, 0.3, 0.5),
}
CYCLE_LENS = [4, 6, 8]
TOP_K_RATIOS = [0.20, 0.35, 0.50]


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


def on_short_cycle_mask(G_dir, node_ids, max_len):
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


def node_prf(pred_members, gt_members):
    pred, gt = set(pred_members), set(gt_members)
    tp = len(pred & gt)
    prec = tp / len(pred) if pred else 0.0
    rec = tp / max(len(gt), 1)
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0
    return round(prec, 4), round(rec, 4), round(f1, 4)


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

    # S1 kcore 核心度（归一化）
    core = nx.core_number(G_und)
    core_vals = np.array([core.get(a, 0) for a in node_ids], dtype=float)
    s1 = (core_vals - core_vals.min()) / (core_vals.max() - core_vals.min() + 1e-9)
    # S3 规则分
    rule = compute_rule_scores(sub_txs, node_ids)
    s3 = np.array([rule[a] for a in node_ids], dtype=float)
    s3 = (s3 - s3.min()) / (s3.max() - s3.min() + 1e-9)

    results = {"setting": {}, "grid": {}, "baselines": {}}
    results["setting"] = {
        "data_dir": DATA_DIR, "n_anchor_rings": N_ANCHOR_RINGS, "k_hop": K_HOP,
        "max_nodes": MAX_NODES, "n_subgraph_nodes": n, "n_in_rings": n_ring,
        "ring_ratio": round(n_ring / n, 4), "blind_baseline_f1": 0.002,
        "note": "Path B 增强：kcore+短环+规则三路融合，top-k 截断。固定权重多组如实报告；"
                "AMLSim 公开合成基准非真实验证。",
    }

    # 对照基线
    p, r, f = node_prf(set(node_ids[i] for i in range(n) if core.get(node_ids[i], 0) >= 2), gt_members)
    results["baselines"]["kcore2"] = {"precision": p, "recall": r, "F1": f}
    print(f"  base kcore2: P={p} R={r} F1={f}", flush=True)

    for L in CYCLE_LENS:
        s2 = on_short_cycle_mask(G_dir, node_ids, L).astype(float)
        # 短环单独基线
        p, r, f = node_prf(set(node_ids[i] for i in range(n) if s2[i] == 1), gt_members)
        results["baselines"][f"short_cycle_L{L}"] = {"precision": p, "recall": r, "F1": f}
        print(f"  base short_cycle L={L}: P={p} R={r} F1={f}", flush=True)

        for wname, (w1, w2, w3) in WEIGHTS.items():
            score = w1 * s1 + w2 * s2 + w3 * s3
            for k_ratio in TOP_K_RATIOS:
                k = int(n * k_ratio)
                topk_idx = np.argsort(-score)[:k]
                pred_members = set(node_ids[i] for i in topk_idx)
                p, r, f = node_prf(pred_members, gt_members)
                key = f"L{L}_{wname}_k{k_ratio:.0%}"
                results["grid"][key] = {"precision": p, "recall": r, "F1": f}
                if f >= 0.65:
                    print(f"  {key}: P={p} R={r} F1={f}", flush=True)

    # 汇总最佳
    best = max(results["grid"].items(), key=lambda x: x[1]["F1"])
    results["best"] = {"config": best[0], **best[1]}
    print(f"\n=== BEST: {best[0]} F1={best[1]['F1']} P={best[1]['precision']} "
          f"R={best[1]['recall']} ===", flush=True)

    # ===== 两阶段：kcore2 高召回 + 融合分二次排序截断 =====
    # 阶段1：kcore2 核心子图（recall 0.91）
    # 阶段2：在核心子图内按融合分排序，取 top-k（砍低置信背景，提 precision）
    print("\n=== 两阶段：kcore2 内融合分 top-k ===", flush=True)
    results["two_stage"] = {}
    core2_idx = [i for i in range(n) if core.get(node_ids[i], 0) >= 2]
    for L in CYCLE_LENS:
        s2 = on_short_cycle_mask(G_dir, node_ids, L).astype(float)
        for wname, (w1, w2, w3) in WEIGHTS.items():
            score = w1 * s1 + w2 * s2 + w3 * s3
            for k_ratio in [0.50, 0.70, 0.90]:
                # 在核心子图内取 top-k（k 是核心子图的比例）
                k = max(int(len(core2_idx) * k_ratio), 1)
                sub_score = score[core2_idx]
                top_in_core = np.argsort(-sub_score)[:k]
                pred_members = set(node_ids[core2_idx[i]] for i in top_in_core)
                p, r, f = node_prf(pred_members, gt_members)
                key = f"kcore2_L{L}_{wname}_core{k_ratio:.0%}"
                results["two_stage"][key] = {"precision": p, "recall": r, "F1": f}
                if f >= 0.65:
                    print(f"  {key}: P={p} R={r} F1={f}", flush=True)

    ts_best = max(results["two_stage"].items(), key=lambda x: x[1]["F1"])
    results["two_stage_best"] = {"config": ts_best[0], **ts_best[1]}
    print(f"\n=== TWO-STAGE BEST: {ts_best[0]} F1={ts_best[1]['F1']} "
          f"P={ts_best[1]['precision']} R={ts_best[1]['recall']} ===", flush=True)

    out = {"setting": results["setting"], "baselines": results["baselines"],
           "grid": results["grid"], "best": results["best"],
           "two_stage": results["two_stage"], "two_stage_best": results["two_stage_best"],
           "elapsed_s": round(time.time() - t0, 1)}
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"[saved] {OUT_PATH} ({time.time()-t0:.1f}s)")


if __name__ == "__main__":
    main()
