"""
Path B · 最优组合管道：团伙 + 资金链双目标（AMLSim 锚点扩线）
================================================================
目标：提高"找到团伙"和"找到资金链"的准确率（precision）与找回率（recall）。

管道（基于前两轮实验的最优组件）：
  1. 扩线：k=1、锚点 120 环（实验 2 甜点，子图 2,748 节点，A2 F1 达 0.35）
  2. 团伙候选：k-core 分解（kmin 扫描 2/3/4，如实全报）+ k-core 子图 Louvain 社区
     + 社区级规则分（C 的账户分均值）→ 输出候选团伙及排序
  3. 资金链候选：有向图强连通分量 SCC（size>=3，资金回流环）+ 规则分排序
  4. 组合：SCC 环成员 ∩ k-core 核心 → "高置信资金链团伙"

评测（升级为实战口径——民警拿到候选清单的准确率）：
  - 团伙级：候选团伙 top-K 成员 vs 真值环成员 的节点级 precision/recall/F1
  - 资金链级：候选 SCC 环 vs 真值环 的节点级 precision/recall/F1
  - 对照：盲扫基线 0.002、单方法（A2 / C / SCC）

诚实口径：无监督、固定参数；AMLSim 公开合成基准，不构成真实警务数据验证通过。

输出：backend/gnn/pathb_pipeline_results.json
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

BACKEND = os.path.dirname(os.path.abspath(__file__))
for p in (BACKEND, os.path.dirname(BACKEND)):
    if p not in sys.path:
        sys.path.insert(0, p)

from gnn.account_temporal import build_account_graph  # noqa: E402
from gnn.adapters.amlsim_adapter import load_amlsim  # noqa: E402

DATA_DIR = os.path.join(BACKEND, "amlsim_real", "canonical")
OUT_PATH = os.path.join(BACKEND, "pathb_pipeline_results.json")
N_ANCHOR_RINGS, K_HOP, MAX_NODES = 120, 1, 8000  # 甜点设定
KMIN_LIST = [2, 3, 4]
TOP_K_RATIOS = [0.05, 0.10, 0.20]  # 候选清单规模（占子图比例）


# ---------- 评测工具 ----------
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


def node_prf(pred_members, gt_ring_members, total_gt):
    """节点级 precision/recall/F1：pred_members 是预测候选集合，
    gt_ring_members 是子图内全部真值环成员。"""
    pred = set(pred_members)
    gt = set(gt_ring_members)
    tp = len(pred & gt)
    prec = tp / len(pred) if pred else 0.0
    rec = tp / max(len(gt), 1)
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0
    return round(prec, 4), round(rec, 4), round(f1, 4)


# ---------- 扩线子图 ----------
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


# ---------- C 规则分 ----------
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


def _fund_reflux_ratio(G_dir, community, max_cycle_len=6):
    """社区内资金回流强度：成员中"处于短有向环"的比例（BFS 逐点判断，
    线性复杂度，避免 simple_cycles 的指数枚举）——衡量该社区作为
    "资金链/洗钱环"的可疑度。返回 0~1。"""
    adj_out = defaultdict(list)
    for u, v in G_dir.edges():
        adj_out[u].append(v)
    covered = 0
    for a in community:
        if _has_short_cycle(a, adj_out, max_cycle_len):
            covered += 1
    return round(covered / max(len(community), 1), 4)


def _on_short_cycle_mask(G_dir, node_ids, max_len=6):
    """返回布尔数组：节点是否处于长度<=max_len 的有向环上（BFS 线性）。"""
    adj_out = defaultdict(list)
    for u, v in G_dir.edges():
        adj_out[u].append(v)
    mask = np.zeros(len(node_ids), dtype=bool)
    for i, a in enumerate(node_ids):
        if _has_short_cycle(a, adj_out, max_len):
            mask[i] = True
    return mask


# ---------- 管道 ----------
def main():
    t0 = time.time()
    print("[load] AMLSim canonical ...", flush=True)
    account_ids, edges, gt = load_amlsim(DATA_DIR)
    print(f"[load] accounts={len(account_ids)} edges={len(edges)}", flush=True)

    sub_txs, sub_gt, anchors = extract_anchor_subgraph(
        account_ids, edges, gt, N_ANCHOR_RINGS, K_HOP, MAX_NODES)
    print(f"[subgraph] anchors={len(anchors)} txs={len(sub_txs)} nodes={len(sub_gt)}", flush=True)

    g = build_account_graph(sub_txs)
    node_ids = g["node_ids"]
    G_dir = g["G"]                      # 有向图（资金流向）
    G_und = G_dir.to_undirected()
    G_und.remove_edges_from(nx.selfloop_edges(G_und))
    gt_arr = np.array([sub_gt[a] for a in node_ids], dtype=int)
    ring_mask = gt_arr >= 0
    gt_members = set(node_ids[i] for i in range(len(node_ids)) if ring_mask[i])
    n, n_ring = len(node_ids), int(ring_mask.sum())
    print(f"[build] nodes={n} edges_und={G_und.number_of_edges()} "
          f"edges_dir={G_dir.number_of_edges()} rings={n_ring} ratio={n_ring/n:.3f}", flush=True)

    scores = compute_rule_scores(sub_txs, node_ids)
    results = {"setting": {}, "gang_level": {}, "fund_chain_level": {}, "component_ablation": {}}
    results["setting"] = {
        "data_dir": DATA_DIR, "n_anchor_rings": N_ANCHOR_RINGS, "k_hop": K_HOP,
        "max_nodes": MAX_NODES, "n_subgraph_nodes": n, "n_in_rings": n_ring,
        "ring_ratio": round(n_ring / n, 4), "blind_baseline_f1": 0.002,
        "note": "Path B 最优组合管道：k=1 扩线 + k-core 候选 + 规则排序 + SCC 资金链环。"
                "无监督固定参数；AMLSim 公开合成基准，不构成真实验证通过。",
    }

    # ============ 团伙级：k-core 候选 + 社区规则分排序（节点预算版） ============
    for kmin in KMIN_LIST:
        core = nx.core_number(G_und)
        core_set = {a for a in node_ids if core.get(a, 0) >= kmin}
        if len(core_set) < 3:
            continue
        Gc = G_und.subgraph(sorted(core_set)).copy()
        comms = louvain_communities(Gc, weight=None)
        comms = [c for c in comms if len(c) >= 3]
        # 社区级规则分（成员规则分均值）+ 资金回流比
        gang_scores = []
        for ci, c in enumerate(comms):
            sc = [scores[a]["final"] for a in c]
            reflux = _fund_reflux_ratio(G_dir, c)
            gang_scores.append((ci, c, float(np.mean(sc)), reflux))
        gang_scores.sort(key=lambda x: x[1], reverse=True)

        # 按节点预算取候选（覆盖更多真环，提升 recall）
        for k_ratio in TOP_K_RATIOS:
            budget = int(n * k_ratio)
            pred_members, budget_used = set(), 0
            for _, c, _, _ in gang_scores:
                if budget_used >= budget:
                    break
                pred_members |= set(c)
                budget_used += len(c)
            prec, rec, f1 = node_prf(pred_members, gt_members, n_ring)
            results["gang_level"][f"kcore{kmin}_budget{k_ratio:.0%}"] = {
                "n_gangs_cand": len([1 for _, c, _, _ in gang_scores if set(c) & pred_members]),
                "n_nodes_cand": len(pred_members),
                "precision": prec, "recall": rec, "F1": f1}
            print(f"  gang kcore{kmin} budget{k_ratio:.0%}: cand={len(pred_members)} "
                  f"P={prec} R={rec} F1={f1}", flush=True)

    # ============ 资金链级：有向强连通分量（SCC）+ 有向环检测 ============
    # SCC 放宽 size>=2
    scc_list = [c for c in nx.strongly_connected_components(G_dir) if len(c) >= 2]
    scc_scores = []
    for c in scc_list:
        sc = [scores[a]["final"] for a in c]
        scc_scores.append((c, float(np.mean(sc))))
    scc_scores.sort(key=lambda x: x[1], reverse=True)
    print(f"  SCC: total={len(scc_list)} size>=2", flush=True)

    # 短环成员检测（BFS 线性，替代 simple_cycles 指数枚举）
    cycle_mask = _on_short_cycle_mask(G_dir, node_ids, max_len=6)
    cycle_members = set(node_ids[i] for i in range(len(node_ids)) if cycle_mask[i])
    print(f"  on-short-cycle members: {len(cycle_members)} (len<=6, BFS)", flush=True)

    for k_ratio in TOP_K_RATIOS:
        k_scc = max(int(len(scc_scores) * k_ratio), 1)
        pred_members = set()
        for c, _ in scc_scores[:k_scc]:
            pred_members |= set(c)
        prec, rec, f1 = node_prf(pred_members, gt_members, n_ring)
        results["fund_chain_level"][f"SCC_top{k_ratio:.0%}"] = {
            "n_scc_cand": k_scc, "n_nodes_cand": len(pred_members),
            "precision": prec, "recall": rec, "F1": f1}
        print(f"  fund SCC top{k_ratio:.0%}: scc={k_scc} cand={len(pred_members)} "
              f"P={prec} R={rec} F1={f1}", flush=True)

    # 有向环成员整体作为资金链候选
    if cycle_members:
        prec, rec, f1 = node_prf(cycle_members, gt_members, n_ring)
        results["fund_chain_level"]["cycles_len<=6_all"] = {
            "n_nodes_cand": len(cycle_members), "precision": prec, "recall": rec, "F1": f1}
        print(f"  fund cycles(all): cand={len(cycle_members)} P={prec} R={rec} F1={f1}", flush=True)

    # ============ 组合：SCC ∩ kcore（高置信资金链团伙）============
    core = nx.core_number(G_und)
    scc_core = []
    for c, sc_mean in scc_scores:
        inter = {a for a in c if core.get(a, 0) >= 3}
        if len(inter) >= 3:
            scc_core.append((inter, sc_mean))
    scc_core.sort(key=lambda x: x[1], reverse=True)
    for k_ratio in TOP_K_RATIOS:
        k_sc = max(int(len(scc_core) * k_ratio), 1)
        pred_members = set()
        for c, _ in scc_core[:k_sc]:
            pred_members |= set(c)
        prec, rec, f1 = node_prf(pred_members, gt_members, n_ring)
        results["fund_chain_level"][f"SCC∩kcore3_top{k_ratio:.0%}"] = {
            "n_cand": k_sc, "n_nodes_cand": len(pred_members),
            "precision": prec, "recall": rec, "F1": f1}
        print(f"  fund SCC∩kcore3 top{k_ratio:.0%}: cand={k_sc} nodes={len(pred_members)} "
              f"P={prec} R={rec} F1={f1}", flush=True)

    # ============ 对照：pairwise F1（与历史口径可比）============
    pred_l = np.zeros(n, dtype=int)
    core = nx.core_number(G_und)
    core_set = {a for a in node_ids if core.get(a, 0) >= 4}
    if len(core_set) >= 3:
        Gc = G_und.subgraph(sorted(core_set)).copy()
        comms = louvain_communities(Gc, weight=None)
        idx_of = {a: i for i, a in enumerate(node_ids)}
        pred_l = np.full(n, -1, dtype=int)
        for ci, c in enumerate(comms):
            for a in c:
                if a in idx_of:
                    pred_l[idx_of[a]] = ci
    f1_pair, p_pair, r_pair = pairwise_f1(pred_l, gt_arr)
    results["component_ablation"]["A2_kcore4_pairwiseF1"] = round(f1_pair, 4)
    print(f"  [ctrl] A2 kcore4 pairwise F1={f1_pair:.4f}", flush=True)

    out = {"setting": results["setting"], "gang_level": results["gang_level"],
           "fund_chain_level": results["fund_chain_level"],
           "component_ablation": results["component_ablation"],
           "elapsed_s": round(time.time() - t0, 1)}
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"\n[saved] {OUT_PATH} ({time.time()-t0:.1f}s)")


if __name__ == "__main__":
    main()
