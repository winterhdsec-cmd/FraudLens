"""
实验 ⑤：真实外部图基准 —— Elliptic Bitcoin AML（Weber et al. 2019，公开真实交易图）
- 数据：真实比特币交易图（203,769 笔交易，含 illicit/licit 标签），HF 镜像公开获取。
- 任务：在"真实外部图"上验证 GNN 嵌入能否把 illicit/licit 结构可分离（无监督聚类 vs 标签）。
- 方法：取最大连通分量并下采样至 N 节点（CPU 可行），以单元路径(tx_tx)邻接跑
  HAN/RGCN/GAT（同协议对比学习）+ KMeans(k=2)，并对比 特征KMeans / Louvain。
- 诚实口径：Elliptic 是真实交易级 AML 图（非公安案卷）；仅下采样连通分量；
  用于外部有效性佐证，不构成"真实警务数据验证通过"。
输出：backend/gnn/elliptic_results.json
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
from sklearn.metrics import normalized_mutual_info_score as NMI, adjusted_rand_score as ARI


def load_elliptic(n_nodes=3000):
    import pandas as pd
    feats = pd.read_csv(os.path.join(BASE, "elliptic_txs_features.csv"), header=None).values
    # 首列为 txId（无表头）
    tx_ids = feats[:, 0].astype(np.int64)
    X = feats[:, 1:].astype(np.float32)
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
    cls = pd.read_csv(os.path.join(BASE, "elliptic_txs_classes.csv"), header=0).values
    # class 列取值为 '1'(illicit)/'2'(licit)/'unknown'
    _map = {"1": 1, "2": 2, "unknown": 0}
    labels = {int(r[0]): _map.get(str(r[1]).strip(), 0) for r in cls}
    # 边
    edges = pd.read_csv(os.path.join(BASE, "elliptic_txs_edgelist.csv"), header=0).values.astype(np.int64)
    id2idx = {int(t): i for i, t in enumerate(tx_ids)}
    G = nx.Graph()
    G.add_nodes_from(range(len(tx_ids)))
    for s, d in edges:
        si, di = id2idx.get(int(s)), id2idx.get(int(d))
        if si is not None and di is not None:
            G.add_edge(si, di)
    # 最大连通分量
    comps = sorted(nx.connected_components(G), key=len, reverse=True)
    big = set(comps[0])
    # 仅保留有标签（illicit/licit）的节点优先，下采样
    labeled = [i for i in big if labels.get(int(tx_ids[i]), 0) in (1, 2)]
    if len(big) > n_nodes:
        # 优先含标签节点，再随机补
        rng = np.random.RandomState(0)
        extra = list(big - set(labeled))
        rng.shuffle(extra)
        keep = set(labeled) | set(extra[: max(0, n_nodes - len(labeled))])
        if len(keep) < n_nodes:
            keep |= set(list(big - keep)[: n_nodes - len(keep)])
    else:
        keep = big
    keep = sorted(keep)
    sub = G.subgraph(keep).copy()
    idx_map = {old: new for new, old in enumerate(keep)}
    N = len(keep)
    Xs = StandardScaler().fit_transform(X[keep])
    # 邻接（单 tx_tx 元路径）
    adj = np.zeros((N, N), dtype=np.float32)
    for u, v in sub.edges():
        adj[idx_map[u], idx_map[v]] = 1.0
        adj[idx_map[v], idx_map[u]] = 1.0
    # 标签（仅 1/2）
    y = np.array([labels.get(int(tx_ids[i]), 0) for i in keep], dtype=np.int64)
    return Xs, adj, y, N


def cluster_metrics(y_true_bin, pred):
    """y_true_bin: 0/1(illicit)，pred: cluster id。对齐后算 NMI/ARI/F1。"""
    from sklearn.metrics import f1_score
    # 对齐：把 pred 中多数 illicit 的簇标为 1
    uniq = np.unique(pred)
    best_f1, best = 0, pred
    for c in uniq:
        p = (pred == c).astype(int)
        f1 = f1_score(y_true_bin, p, zero_division=0)
        if f1 > best_f1:
            best_f1, best = f1, p
    nmi = NMI(y_true_bin, pred)
    ari = ARI(y_true_bin, pred)
    return {"nmi": round(float(nmi), 4), "ari": round(float(ari), 4), "f1_illicit": round(float(best_f1), 4)}


def run_method(name, model, X, adj, y_bin, n_clusters=2):
    meta_t = {"tx_tx": torch.as_tensor(adj)}
    feat_t = torch.as_tensor(X)
    bh.graphcl_pretrain(model, feat_t, meta_t, epochs=100, batch=min(1024, feat_t.shape[0]))
    with torch.no_grad():
        emb = bh._encode(model, feat_t, meta_t).cpu().numpy()
    ce = StandardScaler().fit_transform(emb)
    pred = KMeans(n_clusters=n_clusters, random_state=0, n_init=10).fit_predict(ce)
    return cluster_metrics(y_bin, pred)


def main():
    X, adj, y, N = load_elliptic(n_nodes=3000)
    y_bin = (y == 1).astype(int)  # illicit=1
    n_labeled = int((y_bin >= 0).sum())
    res = {"dataset": "Elliptic Bitcoin AML (Weber et al. 2019, HF mirror)",
           "n_nodes_sampled": N, "n_labeled_illicit_licit": int(((y == 1) | (y == 2)).sum()),
           "note": "真实外部交易图下采样连通分量；非公安案卷；用于外部有效性佐证，非真实验证通过"}

    in_dim = X.shape[1]
    # 特征 KMeans（基线）
    pred_km = KMeans(n_clusters=2, random_state=0, n_init=10).fit_predict(StandardScaler().fit_transform(X))
    res["KMeans_features"] = cluster_metrics(y_bin, pred_km)
    # Louvain
    G = nx.from_numpy_array(adj)
    try:
        from networkx.algorithms.community import louvain_communities
        comms = louvain_communities(G, seed=0)
        pred_l = np.zeros(N, dtype=int)
        for ci, members in enumerate(comms):
            for m in members:
                pred_l[m] = ci
        res["Louvain"] = cluster_metrics(y_bin, pred_l)
    except Exception as e:
        res["Louvain"] = {"error": str(e)[:120]}
    # GNN 方法
    han = han_model_wrapper(in_dim)
    res["HAN"] = run_method("HAN", han, X, adj, y_bin)
    rgcn = bh.RGCNBaseline(in_dim=in_dim, hidden_dim=64, out_dim=32, num_layers=2, meta_paths=["tx_tx"])
    res["RGCN"] = run_method("RGCN", rgcn, X, adj, y_bin)
    gat = bh.GATBaseline(in_dim=in_dim, hidden_dim=64, out_dim=32, num_layers=2, meta_paths=["tx_tx"])
    res["GAT"] = run_method("GAT", gat, X, adj, y_bin)

    with open(os.path.join(BACKEND, "elliptic_results.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=2)
    print(json.dumps(res, ensure_ascii=False, indent=2))


def han_model_wrapper(in_dim):
    # 直接构造 HAN 骨干并指定元路径为 tx_tx（FraudHAN 包装内写死的是案件图 5 条元路径，
    # 在 Elliptic 单元路径输入下会全部跳过并触发 fallback 维度错误）
    import han_model
    return han_model.HAN(in_dim=in_dim, hidden_dim=64, out_dim=32,
                         num_heads=4, num_layers=2, meta_paths=["tx_tx"])


if __name__ == "__main__":
    main()
