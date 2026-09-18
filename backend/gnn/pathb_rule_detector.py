"""
Path B · 分支 C：AMLSim 风格规则探测器（无监督 + 可解释）
================================================================
目标：实现 AMLSim 论文风格的硬规则可疑度打分，作为
  (1) 分支 B（GAE 重构误差）的交叉验证器；
  (2) 给民警的"为什么标记它"的解释层——每条规则可解释。

规则集（基于 AMLSim 洗钱环行为模式 + 反诈实务）：
  R1 金额整分：单账户有大量"整额"入账（金额为 1e3/1e4 量级整数的交易占比高）
  R2 快进快出：入账后很短时间内出账（资金停留时间短）——洗钱典型
  R3 多跳环：账户处于短环（有向环，长度 <= 4）——资金回流
  R4 出入失衡：入账总额/笔数 vs 出账差异大（"过账"账户）
  R5 大额集中：单笔金额显著高于该账户中位数（离群大额）

打分：每规则输出 0~1 归一化可疑度，加权合成 final_score。
无监督：不针对 GT 调规则权重（全部用固定默认值），如实报告。

诚实口径：规则抓到"模式明显"的环，抓不到隐蔽环——这本身是边界认知素材；
AMLSim 为公开合成基准，不构成"真实警务数据验证通过"。

输出：backend/gnn/pathb_rule_results.json
"""
from __future__ import annotations

import json
import os
import sys
import time
from collections import defaultdict

import numpy as np

BACKEND = os.path.dirname(os.path.abspath(__file__))
for p in (BACKEND, os.path.dirname(BACKEND)):
    if p not in sys.path:
        sys.path.insert(0, p)

from gnn.adapters.amlsim_adapter import load_amlsim  # noqa: E402

DATA_DIR = os.path.join(BACKEND, "amlsim_real", "canonical")
OUT_PATH = os.path.join(BACKEND, "pathb_rule_results.json")
N_ANCHOR_RINGS = 60
K_HOP = 2
MAX_NODES = 8000


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
    sub_txs = [(s, d, amt, ts) for (s, d, amt, ts) in edges
               if s in sub_set and d in sub_set]
    sub_gt = {a: gt.get(a, -1) for a in sub_accounts}
    return sub_txs, sub_gt, len(anchors)


def compute_rule_scores(sub_txs, accounts):
    """对子图内每个账户算 5 条规则可疑度，返回 {account: {rule: 0~1, final: 0~1}}。"""
    # 入账/出账记录
    in_amt = defaultdict(list)
    out_amt = defaultdict(list)
    in_ts = defaultdict(list)
    out_ts = defaultdict(list)
    adj_out = defaultdict(list)   # 出边邻居
    adj_in = defaultdict(list)    # 入边邻居
    for s, d, amt, ts in sub_txs:
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
        # R1：整额占比（金额是 1e3/1e4 量级的整数倍）
        if ins:
            whole = sum(1 for v in ins if v > 0 and v % 1000 == 0)
            s["R1_int_split"] = min(whole / max(len(ins), 1) * 2.0, 1.0)
        # R2：快进快出（入账后 <= 1 时间单位内出账的占比）
        if ins and outs and in_ts and out_ts:
            it, ot = sorted(in_ts.get(a, [])), sorted(out_ts.get(a, []))
            fast = 0
            for t_in in it:
                for t_out in ot:
                    if 0 <= (t_out - t_in) <= 1.0:
                        fast += 1
                        break
            s["R2_fast_flow"] = min(fast / max(len(it), 1) * 2.0, 1.0)
        # R3：短环（长度 <= 4 的有向环，DFS 限制深度）
        if a in adj_out and a in adj_in:
            s["R3_short_cycle"] = _has_short_cycle(a, adj_out, 4)
        # R4：出入失衡（|in_total - out_total| / max 大）
        in_t, out_t = sum(ins), sum(outs)
        denom = max(in_t, out_t, 1e-9)
        s["R4_imbalance"] = min(abs(in_t - out_t) / denom * 2.0, 1.0)
        # R5：大额离群（单笔 > 中位数 * 5）
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
    """BFS 判断 start 是否在长度 <= max_len 的有向环中。"""
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

    sub_txs, sub_gt, n_anchors = extract_anchor_subgraph(account_ids, edges, gt)
    print(f"[subgraph] anchors={n_anchors} txs={len(sub_txs)} nodes={len(sub_gt)}", flush=True)

    accounts = list(sub_gt.keys())
    scores = compute_rule_scores(sub_txs, accounts)

    gt_arr = np.array([sub_gt[a] for a in accounts], dtype=int)
    ring_mask = gt_arr >= 0
    n_ring = int(ring_mask.sum())
    n = len(accounts)
    print(f"[eval] nodes={n} in_rings={n_ring}", flush=True)

    # ---- 评测 1：top-k 命中（规则分数作为可疑度排序） ----
    order = sorted(accounts, key=lambda a: scores[a]["final"], reverse=True)
    results = {"topk_hit": {}, "rule_diagnostics": {}}
    for k_ratio in [0.05, 0.1, 0.2]:
        k = max(int(n * k_ratio), 1)
        topk = order[:k]
        hit = sum(1 for a in topk if sub_gt[a] >= 0)
        results["topk_hit"][f"top{k_ratio:.0%}"] = {
            "k": k, "hits_in_rings": hit, "ring_coverage": round(hit / max(n_ring, 1), 4),
            "precision_at_k": round(hit / k, 4)}
        print(f"  top{k_ratio:.0%}(k={k}): ring_hits={hit}/{n_ring} prec@{k_ratio:.0%}={hit/k:.4f}", flush=True)

    # ---- 评测 2：AUC（规则分 vs 是否在环内） ----
    from sklearn.metrics import roc_auc_score
    y_bin = ring_mask.astype(int)
    score_arr = np.array([scores[a]["final"] for a in accounts])
    if y_bin.sum() > 0 and y_bin.sum() < len(y_bin):
        results["auc"] = round(float(roc_auc_score(y_bin, score_arr)), 4)
        print(f"  AUC = {results['auc']}", flush=True)

    # ---- 评测 3：每条规则单独 AUC（诊断哪条规则有效） ----
    for rule in ["R1_int_split", "R2_fast_flow", "R3_short_cycle", "R4_imbalance", "R5_large_outlier"]:
        r_arr = np.array([scores[a][rule] for a in accounts])
        if y_bin.sum() > 0 and y_bin.sum() < len(y_bin) and len(set(r_arr.tolist())) > 1:
            results["rule_diagnostics"][rule] = round(float(roc_auc_score(y_bin, r_arr)), 4)
            print(f"  {rule} AUC = {results['rule_diagnostics'][rule]}", flush=True)

    setting = {
        "data_dir": DATA_DIR, "n_anchor_rings": N_ANCHOR_RINGS, "k_hop": K_HOP,
        "max_nodes": MAX_NODES, "n_subgraph_nodes": n, "n_in_rings": n_ring,
        "weights": {"R1": 0.30, "R2": 0.25, "R3": 0.25, "R4": 0.10, "R5": 0.10},
        "blind_baseline_f1": 0.002,
        "note": "Path B 分支 C：AMLSim 风格规则探测器（无监督可解释）。"
                "规则权重为固定默认值，不针对 GT 调优；规则抓到模式明显的环，抓不到隐蔽环。"
                "AMLSim 为公开合成基准，不构成真实验证通过。",
    }
    out = {"setting": setting, "results": results, "elapsed_s": round(time.time() - t0, 1)}
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"\n[saved] {OUT_PATH}  ({time.time()-t0:.1f}s)")


if __name__ == "__main__":
    main()
