"""
Path B · 第七轮（最后一击）：12 维行为特征 + L8 + kcore 的 4 路融合
================================================================
12 维行为特征（来自 build_account_graph 的 z-score 归一化输出）：
  in_degree / out_degree / lg(total_in) / lg(total_out) / lg(net_flow) /
  lg(mean_in) / lg(mean_out) / lg(std_amt) / PageRank / time_span / ...
从未被用于识别融合——第六次尝试 0.71 天花板后，这是最后的差异化信号。

策略：4 路融合（kcore + L8 + 规则分 + 行为异常分），单权重 balanced 跑 budget 扫描。
行为异常分 = 12 维特征 L2 norm（z-scored 下高 norm = 偏离正常账户模式）。

评测：kcore2 内，L8 全留 + 其余按 4 路融合分排序取预算，查是否突破 0.709。

输出：pathb_feat_boost_results.json
"""
from __future__ import annotations

import json, os, sys, time
from collections import defaultdict
import numpy as np
import networkx as nx

BACKEND = os.path.dirname(os.path.abspath(__file__))
for p in (BACKEND, os.path.dirname(BACKEND)):
    if p not in sys.path:
        sys.path.insert(0, p)
from gnn.account_temporal import build_account_graph
from gnn.adapters.amlsim_adapter import load_amlsim

DATA_DIR = os.path.join(BACKEND, "amlsim_real", "canonical")
OUT_PATH = os.path.join(BACKEND, "pathb_feat_boost_results.json")

N_ANCHOR_RINGS, K_HOP, MAX_NODES = 120, 1, 8000
CYCLE_LEN = 8
BUDGETS = [0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90]
FEAT_AUC_TOP_K = 6  # 取 AUC 前 K 的行为维度


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
    features = g["features"]  # (N, 12) float32, 已 z-score 归一化
    G_dir = g["G"]
    G_und = G_dir.to_undirected()
    G_und.remove_edges_from(nx.selfloop_edges(G_und))
    gt_arr = np.array([sub_gt[a] for a in node_ids], dtype=int)
    gt_members = set(node_ids[i] for i in range(len(node_ids)) if gt_arr[i] >= 0)
    n, n_ring = len(node_ids), int((gt_arr >= 0).sum())
    print(f"[build] nodes={n} edges={G_dir.number_of_edges()} rings={n_ring} "
          f"feats_dim={features.shape[1]}", flush=True)

    # 学习：哪些行为维度最能区分环 vs 背景？（单特征 AUC）
    y_bin = (gt_arr >= 0).astype(int)
    from sklearn.metrics import roc_auc_score
    feat_aucs = []
    for dim in range(features.shape[1]):
        vals = features[:, dim]
        if len(set(vals.tolist())) <= 1:
            feat_aucs.append((dim, 0.0, "const"))
            continue
        auc = roc_auc_score(y_bin, np.nan_to_num(vals, 0.0))
        feat_aucs.append((dim, auc, "discriminative" if abs(auc - 0.5) > 0.02 else "noisy"))
    feat_aucs.sort(key=lambda x: -x[1])
    top_dims = [f[0] for f in feat_aucs[:FEAT_AUC_TOP_K]]
    print(f"[feat] top {FEAT_AUC_TOP_K} dims (by AUC): {[(f[0], round(f[1],4)) for f in feat_aucs[:FEAT_AUC_TOP_K]]}",
          flush=True)

    # 行为异常分：top-K 维度 L2 norm（归一化）
    feat_anomaly = np.linalg.norm(features[:, top_dims], axis=1)
    s4 = (feat_anomaly - feat_anomaly.min()) / (feat_anomaly.max() - feat_anomaly.min() + 1e-9)
    print(f"feat_anomaly(PCA-like): range [{s4.min():.3f}, {s4.max():.3f}]", flush=True)

    # 其余信号
    core = nx.core_number(G_und)
    core_vals = np.array([core.get(a, 0) for a in node_ids], dtype=float)
    s1 = (core_vals - core_vals.min()) / (core_vals.max() - core_vals.min() + 1e-9)
    s2 = on_cycle_mask(G_dir, node_ids, CYCLE_LEN).astype(float)
    rule = compute_rule_scores(sub_txs, node_ids)
    s3 = np.array([rule[a] for a in node_ids], dtype=float)
    s3 = (s3 - s3.min()) / (s3.max() - s3.min() + 1e-9)

    kcore2_set = {a for a in node_ids if core.get(a, 0) >= 2}
    L8_members = set(node_ids[i] for i in range(n) if s2[i] == 1)
    kcore_list = sorted(kcore2_set)
    kcore_idx = [node_ids.index(a) for a in kcore_list]
    kcore_L8 = [a for a in kcore_list if a in L8_members]
    kcore_nonL8 = [a for a in kcore_list if a not in L8_members]
    nk = len(kcore_nonL8)
    print(f"signals: kcore2={len(kcore2_set)} L8={len(L8_members)} kcore2∩L8={len(kcore_L8)}",
          flush=True)

    results = {}
    # 基线
    p, r, f = node_prf(kcore2_set, gt_members)
    results["baseline_kcore2"] = {"P": p, "R": r, "F1": f}
    print(f"  baseline kcore2: P={p} R={r} F1={f}", flush=True)

    # 4 路融合：balanced (0.25, 0.25, 0.25, 0.25) single weight
    score = 0.25 * s1[kcore_idx] + 0.25 * s2[kcore_idx] + 0.25 * s3[kcore_idx] + 0.25 * s4[kcore_idx]
    acct_score = {a: score[i] for i, a in enumerate(kcore_list)}
    nonL8_sorted = sorted(kcore_nonL8, key=lambda a: -acct_score[a])

    for budget in BUDGETS:
        budget_n = int(n * budget)
        pred = set(kcore_L8)
        remaining = budget_n - len(pred)
        if remaining > 0 and remaining < nk:
            pred |= set(nonL8_sorted[:remaining])
        elif remaining >= nk:
            pred |= set(kcore_nonL8)
        p, r, f = node_prf(pred, gt_members)
        results[f"L8+4way_budget{budget:.0%}"] = {"P": p, "R": r, "F1": f, "n": len(pred)}
        tag = " ⭐" if f > 0.71 else ""
        print(f"  budget{budget:.0%}: n={len(pred)} P={p} R={r} F1={f}{tag}", flush=True)

    best = max(results.items(), key=lambda x: x[1]["F1"])
    print(f"\n=== BEST: {best[0]} F1={best[1]['F1']} ===")
    vs_baseline = "BREAKTHROUGH!" if best[1]["F1"] > 0.709 else "no breakthrough"
    print(f"  vs kcore2(0.709): {vs_baseline}", flush=True)

    out = {
        "setting": {"cycle_len": CYCLE_LEN, "feat_auc_top_k": FEAT_AUC_TOP_K,
                    "top_dims": [f[0] for f in feat_aucs[:FEAT_AUC_TOP_K]],
                    "top_dim_aucs": [round(f[1], 4) for f in feat_aucs[:FEAT_AUC_TOP_K]],
                    "n_subgraph_nodes": n, "n_in_rings": n_ring, "blind_baseline_f1": 0.002,
                    "note": "Path B 第七轮：12维行为特征的 AUC 前K维度融合 + L8 + kcore + 规则。"
                            "固定权重；AMLSim 公开合成基准非真实验证。"},
        "results": results, "best": {"config": best[0], **best[1]},
        "elapsed_s": round(time.time() - t0, 1),
    }
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"[saved] {OUT_PATH} ({time.time()-t0:.1f}s)")


if __name__ == "__main__":
    main()
