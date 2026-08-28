"""
实验 ⑤-b：Elliptic 真实图上的扩线（refinement）设定
- 对照 experiment_elliptic.py 的盲扫设定（全部方法 F1≈0.01-0.15）。
- 扩线设定：以少量 illicit 锚点（模拟 AML 告警）为起点取 k 跳嫌疑子图，
  在子图内做 illicit/licit 二类恢复（KMeans/Louvain/GNN 同协议）。
- 诚实口径：真实交易图非公安案卷；锚点取自标签（模拟告警先验）；
  用于验证"盲扫失效→扩线可用"的设定迁移在真实图上是否复现，非"真实验证通过"。
输出：backend/gnn/elliptic_refine_results.json
"""
import sys, os, json
import numpy as np
import torch

BASE = "E:/FraudLens/backend/data/datasets/elliptic"
BACKEND = "E:/FraudLens/backend/gnn"
for p in (BACKEND, os.path.dirname(BACKEND)):
    if p not in sys.path:
        sys.path.insert(0, p)

import networkx as nx
import baselines_hetero as bh
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import f1_score, normalized_mutual_info_score as NMI


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


def run_gnn(model, X, adj, y_bin):
    meta_t = {"tx_tx": torch.as_tensor(adj)}
    feat_t = torch.as_tensor(X)
    bh.graphcl_pretrain(model, feat_t, meta_t, epochs=100, batch=min(1024, feat_t.shape[0]))
    with torch.no_grad():
        emb = bh._encode(model, feat_t, meta_t).cpu().numpy()
    ce = StandardScaler().fit_transform(emb)
    pred = KMeans(n_clusters=2, random_state=0, n_init=10).fit_predict(ce)
    return cluster_f1(y_bin, pred), round(float(NMI(y_bin, pred)), 4)


def main():
    X, G, y = load_full()
    illicit = np.where(y == 1)[0]
    rng = np.random.RandomState(0)

    # 多组锚点试验：每次取 n_anchor 个 illicit 锚点，2 跳子图（上限 2000 节点）
    N_TRIALS, N_ANCHOR, K_HOP, CAP = 5, 10, 2, 2000
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
        # 仅统计有标签比例
        n_lab = int(((y[keep] == 1) | (y[keep] == 2)).sum())
        Xs = StandardScaler().fit_transform(X[keep])
        adj = np.zeros((n, n), dtype=np.float32)
        sg = G.subgraph(keep)
        for u, v in sg.edges():
            adj[idx[u], idx[v]] = 1.0
            adj[idx[v], idx[u]] = 1.0

        rec = {"trial": t, "n_sub": n, "n_labeled": n_lab,
               "illicit_ratio": round(float(yb.mean()), 4)}
        pred_km = KMeans(n_clusters=2, random_state=0, n_init=10).fit_predict(Xs)
        rec["KMeans_f1"] = cluster_f1(yb, pred_km)
        try:
            from networkx.algorithms.community import louvain_communities
            comms = louvain_communities(nx.from_numpy_array(adj), seed=0)
            pl = np.zeros(n, dtype=int)
            for ci, mem in enumerate(comms):
                for m in mem:
                    pl[m] = ci
            rec["Louvain_f1"] = cluster_f1(yb, pl)
        except Exception as e:
            rec["Louvain_f1"] = None
        import han_model
        han = han_model.HAN(in_dim=Xs.shape[1], hidden_dim=64, out_dim=32,
                            num_heads=4, num_layers=2, meta_paths=["tx_tx"])
        rec["HAN_f1"], rec["HAN_nmi"] = run_gnn(han, Xs, adj, yb)
        trials.append(rec)
        print(json.dumps(rec, ensure_ascii=False))

    def agg(k):
        v = np.array([r[k] for r in trials if r[k] is not None], dtype=float)
        return {"mean": round(float(v.mean()), 4), "std": round(float(v.std(ddof=1)), 4)} if len(v) > 1 else {}

    res = {"setting": f"refinement: {N_ANCHOR} illicit anchors, {K_HOP}-hop, cap {CAP}, {N_TRIALS} trials",
           "note": "真实 Elliptic 图扩线设定；锚点取自标签模拟 AML 告警；非真实警务验证通过",
           "trials": trials,
           "summary": {"KMeans": agg("KMeans_f1"), "Louvain": agg("Louvain_f1"),
                        "HAN": agg("HAN_f1"), "illicit_ratio": agg("illicit_ratio")}}
    with open(os.path.join(BACKEND, "elliptic_refine_results.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=2)
    print("=== SUMMARY ===")
    print(json.dumps(res["summary"], ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
