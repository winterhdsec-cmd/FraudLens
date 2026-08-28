"""
Path B · 实验 3：Elliptic 真实交易图复跑 A2/C（无监督）
================================================================
复用 experiment_elliptic_refine.py 的加载与扩线协议（5 trials × 10 illicit
锚点 × 2 跳，cap 2000），在其上复跑 Path B 的两种无监督方法：
  A2 kcore-louvain(kmin=4)：二分类恢复（cluster_f1 同协议）
  C 规则探测器：合成分 AUC + top-k precision
对照：已有 Elliptic 盲扫（全部方法 F1≈0.01-0.15）与扩线 Louvain/KMeans/HAN。

诚实口径：Elliptic 是真实交易级 AML 图（非公安案卷）；锚点取自标签模拟告警；
结果验证"盲扫失效→扩线可用"在真实图上是否复现，非"真实验证通过"。

输出：backend/gnn/pathb_elliptic_results.json
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
from sklearn.metrics import f1_score, roc_auc_score
from sklearn.preprocessing import StandardScaler

BASE = "E:/FraudLens/backend/data/datasets/elliptic"
BACKEND = os.path.dirname(os.path.abspath(__file__))
OUT_PATH = os.path.join(BACKEND, "pathb_elliptic_results.json")

N_TRIALS, N_ANCHOR, K_HOP, CAP = 5, 10, 2, 2000
KMIN = 4


def load_full():
    import pandas as pd
    feats = pd.read_csv(os.path.join(BASE, "elliptic_txs_features.csv"), header=None).values
    tx_ids = feats[:, 0].astype(np.int64)
    X = np.nan_to_num(feats[:, 1:].astype(np.float32), nan=0.0, posinf=0.0, neginf=0.0)
    cls = pd.read_csv(os.path.join(BASE, "elliptic_txs_classes.csv"), header=0).values
    _map = {"1": 1, "2": 2, "unknown": 0}
    labels = {int(r[0]): _map.get(str(r[1]).strip(), 0) for r in cls}
    edges = pd.read_csv(os.path.join(BASE, "elliptic_txs_edgelist.csv"), header=0).values.astype(np.int64)
    id2idx = {int(t): i for i, t in enumerate(tx_ids)}
    G = nx.Graph()
    G.add_nodes_from(range(len(tx_ids)))
    for s, d in edges:
        si, di = id2idx.get(int(s)), id2idx.get(int(d))
        if si is not None and di is not None:
            G.add_edge(si, di)
    y = np.array([labels.get(int(t), 0) for t in tx_ids], dtype=np.int64)
    return X, G, y


def cluster_f1(y_bin, pred):
    best = 0.0
    for c in np.unique(pred):
        f1 = f1_score(y_bin, (pred == c).astype(int), zero_division=0)
        best = max(best, f1)
    return round(float(best), 4)


def a2_cluster_f1(G_sub, keep_idx, yb):
    """A2 kcore-louvain 二分类恢复：核心子图 Louvain 社区 vs 背景。"""
    Gc = G_sub.copy()
    Gc.remove_edges_from(nx.selfloop_edges(Gc))
    core = nx.core_number(Gc)
    core_nodes = [a for a in Gc.nodes() if core.get(a, 0) >= KMIN]
    n = len(keep_idx)
    if len(core_nodes) < 3:
        return 0.0
    Gk = Gc.subgraph(core_nodes).copy()
    comms = louvain_communities(Gk, weight=None)
    pred = np.zeros(n, dtype=int)  # 默认背景 0
    for ci, c in enumerate(comms):
        for a in c:
            pred[keep_idx[a]] = ci + 1  # 社区 1..K，背景 0
    return cluster_f1(yb, pred)


def rule_scores_elliptic(adj, feats):
    """Elliptic 无金额/时序（边无权重），规则退化为可用子集：
    R3 短环（图结构）、R5 特征离群（交易特征离群度）。
    诚实注明：R1/R2/R4 需金额时序，Elliptic 数据缺失，不适用。"""
    n = adj.shape[0]
    g = nx.from_numpy_array(adj)
    scores = np.zeros(n)
    for i in range(n):
        r3 = 1.0 if _has_short_cycle(i, g, 4) else 0.0
        feats_i = feats[i]
        med = np.median(feats_i)
        mad = np.median(np.abs(feats_i - med)) + 1e-9
        outlier_ratio = float(np.mean(np.abs(feats_i - med) > 5 * mad))
        scores[i] = 0.5 * r3 + 0.5 * min(outlier_ratio * 3.0, 1.0)
    return scores


def _has_short_cycle(start, g, max_len):
    from collections import deque
    visited = {start}
    q = deque([(start, 0)])
    while q:
        node, depth = q.popleft()
        if depth + 1 > max_len:
            continue
        for nb in g.neighbors(node):
            if nb == start:
                return 1.0
            if nb not in visited:
                visited.add(nb)
                q.append((nb, depth + 1))
    return 0.0


def main():
    t0 = time.time()
    print("[load] Elliptic ...", flush=True)
    X, G, y = load_full()
    illicit = np.where(y == 1)[0]
    rng = np.random.RandomState(0)
    print(f"[load] nodes={len(y)} illicit={len(illicit)}", flush=True)

    trials = []
    for t in range(N_TRIALS):
        anchors = rng.choice(illicit, size=N_ANCHOR, replace=False)
        sub_nodes = set(anchors.tolist())
        frontier = set(anchors.tolist())
        for _ in range(K_HOP):
            nxt = set()
            for u in frontier:
                nxt |= set(G.neighbors(u))
            frontier = nxt - sub_nodes
            sub_nodes |= nxt
            if len(sub_nodes) > CAP:
                break
        keep = sorted(sub_nodes)[:CAP]
        idx = {o: i for i, o in enumerate(keep)}
        n = len(keep)
        yb = (y[keep] == 1).astype(int)
        Xs = StandardScaler().fit_transform(X[keep])
        adj = np.zeros((n, n), dtype=np.float32)
        sg = G.subgraph(keep)
        for u, v in sg.edges():
            adj[idx[u], idx[v]] = 1.0
            adj[idx[v], idx[u]] = 1.0
        G_sub = nx.from_numpy_array(adj)

        rec = {"trial": t, "n_sub": n, "n_labeled": int(((y[keep] == 1) | (y[keep] == 2)).sum()),
               "illicit_ratio": round(float(yb.mean()), 4)}
        rec["A2_kcore_f1"] = a2_cluster_f1(G_sub, idx, yb)
        rscore = rule_scores_elliptic(adj, Xs)
        if yb.sum() > 0 and yb.sum() < n and len(set(rscore.tolist())) > 1:
            rec["C_rule_AUC"] = round(float(roc_auc_score(yb, rscore)), 4)
        else:
            rec["C_rule_AUC"] = None
        # C top-k precision（规则分排序）
        k = max(int(n * 0.2), 1)
        topk = np.argsort(-rscore)[:k]
        rec["C_rule_prec@20%"] = round(float(yb[topk].mean()), 4)
        trials.append(rec)
        print(f"  trial {t}: n={n} illicit_ratio={rec['illicit_ratio']} "
              f"A2_f1={rec['A2_kcore_f1']} C_AUC={rec['C_rule_AUC']} "
              f"C_prec20={rec['C_rule_prec@20%']}", flush=True)

    def agg(k):
        v = np.array([r[k] for r in trials if r[k] is not None], dtype=float)
        return {"mean": round(float(v.mean()), 4), "std": round(float(v.std(ddof=1)), 4)} if len(v) > 1 else {}

    res = {
        "setting": f"Elliptic refinement: {N_ANCHOR} illicit anchors, {K_HOP}-hop, cap {CAP}, {N_TRIALS} trials, kmin={KMIN}",
        "note": "Path B 实验 3：Elliptic 真实图复跑 A2/C（无监督）。锚点取自标签模拟 AML 告警；"
                "Elliptic 无金额/时序，规则 C 退化为 R3短环+R5特征离群；非真实警务验证通过。",
        "trials": trials,
        "summary": {"A2_kcore_f1": agg("A2_kcore_f1"), "C_rule_AUC": agg("C_rule_AUC"),
                    "C_rule_prec20": agg("C_rule_prec@20%"), "illicit_ratio": agg("illicit_ratio")},
    }
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=2)
    print("\n=== SUMMARY ===")
    print(json.dumps(res["summary"], ensure_ascii=False, indent=1))
    print(f"[saved] {OUT_PATH} ({time.time()-t0:.1f}s)")


if __name__ == "__main__":
    main()
