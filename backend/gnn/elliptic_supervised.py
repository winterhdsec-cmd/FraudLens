"""
Elliptic 有监督训练/微调评测（temporal split）。

背景：无监督冷启动在 Elliptic 上已证伪（AUC≈0.14-0.40 < 随机 0.5，
见 eval_framework.run_node_fraud_eval 与 gnn/results/elliptic_results.json）。
本模块给"真实域内训练"一条路：Elliptic 自带 46,564 条 licit/illicit 标注，
按时间步做时序划分（train: timestep≤31，test: >31 —— 用过去抓未来的真实
AML 设定），训练两类模型对照：
  GCN(features+graph) —— 2 层稀疏 GCN，图结构 + 165 维特征
  MLP(features only)  —— 同结构 MLP，仅特征（隔离"图结构"的增量）
在测试集上报告 illicit 类 P/R/F1/误报率/AUC。诚实标注：这是"域内监督"评测，
证明系统在拿到标注后能否工作；不混淆为"零样本通用能力"。
"""
import os
from typing import Any, Dict, List, Tuple

import numpy as np

from gnn.eval_framework import _auc_rank, _load_local

TRAIN_TS_MAX = 31  # Elliptic 标准时序划分：前 31 个时间步训练


class EllipticSupervisedError(Exception):
    pass


def _load(directory: str):
    adapter_mod = _load_local("elliptic_adapter", "gnn/adapters/elliptic_adapter.py")
    account_ids, edges, labels, features = adapter_mod.load_elliptic(directory, with_features=True)
    if features is None:
        raise EllipticSupervisedError("有监督训练需要特征文件 elliptic_txs_features.csv")
    # adapter 返回 feats[:,1:]：列0=timestep，列1..=165 维特征
    timestep = features[:, 0].astype(np.int64)
    X = features[:, 1:].astype(np.float32)
    return account_ids, edges, labels, X, timestep


def _split(account_ids, labels, timestep) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """按时间步划分标注子集，返回 (train_idx, test_idx, y_all)。"""
    n = len(account_ids)
    y_all = np.zeros(n, dtype=np.int64)
    labeled = []
    for i, a in enumerate(account_ids):
        v = labels.get(a, -1)
        if v in (0, 1):
            labeled.append(i)
            y_all[i] = v
    labeled = np.asarray(labeled, dtype=np.int64)
    if len(labeled) == 0:
        raise EllipticSupervisedError("无 0/1 标注账户")
    ts = timestep[labeled]
    train_idx = labeled[ts <= TRAIN_TS_MAX]
    test_idx = labeled[ts > TRAIN_TS_MAX]
    if len(train_idx) == 0 or len(test_idx) == 0:
        raise EllipticSupervisedError(
            f"时序划分后训练/测试为空（train={len(train_idx)}, test={len(test_idx)}）")
    return train_idx, test_idx, y_all


def _normalized_adj(n: int, edges: np.ndarray):
    import scipy.sparse as sp
    rows = np.concatenate([edges[:, 0], edges[:, 1]])
    cols = np.concatenate([edges[:, 1], edges[:, 0]])
    A = sp.csr_matrix((np.ones(len(rows)), (rows, cols)), shape=(n, n))
    A = A + sp.identity(n, format="csr")
    d = np.asarray(A.sum(axis=1)).flatten()
    dinv = np.zeros_like(d)
    np.power(d, -0.5, where=d > 0, out=dinv)
    return sp.diags(dinv) @ A @ sp.diags(dinv)


def _to_torch_sparse(A_csr):
    import torch
    coo = A_csr.tocoo()
    idx = torch.LongTensor(np.vstack([coo.row, coo.col]))
    val = torch.FloatTensor(coo.data)
    return torch.sparse_coo_tensor(idx, val, A_csr.shape).coalesce()


def _make_model(use_graph: bool, in_dim: int, hidden: int):
    import torch.nn as nn
    import torch.nn.functional as F

    if use_graph:
        class _GCN2(nn.Module):
            def __init__(self, d, h):
                super().__init__()
                self.w1 = nn.Linear(d, h)
                self.w2 = nn.Linear(h, 1)
                self.drop = nn.Dropout(0.5)

            def forward(self, A, X):
                h = F.relu(A @ self.w1(X))
                h = self.drop(h)
                return (A @ self.w2(h)).view(-1)
        return _GCN2(in_dim, hidden)
    else:
        class _MLP2(nn.Module):
            def __init__(self, d, h):
                super().__init__()
                self.w1 = nn.Linear(d, h)
                self.w2 = nn.Linear(h, 1)
                self.drop = nn.Dropout(0.5)

            def forward(self, X):
                h = F.relu(self.w1(X))
                h = self.drop(h)
                return self.w2(h).view(-1)
        return _MLP2(in_dim, hidden)


def _fit(use_graph: bool, A_t, X_t, train_idx, y_train, epochs: int, hidden: int,
         lr: float, seed: int):
    import torch
    torch.manual_seed(seed)
    model = _make_model(use_graph, X_t.shape[1], hidden)
    opt = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=5e-4)
    pos = float(y_train.sum())
    neg = float(len(y_train) - pos)
    pos_w = torch.tensor(max(neg / pos, 1.0)) if pos > 0 else torch.tensor(1.0)
    lossf = torch.nn.BCEWithLogitsLoss(pos_weight=pos_w)
    t_idx = torch.LongTensor(train_idx)
    yt = torch.FloatTensor(y_train)
    for _ in range(epochs):
        model.train()
        opt.zero_grad()
        logits = model(A_t, X_t) if use_graph else model(X_t)
        loss = lossf(logits[t_idx], yt)
        loss.backward()
        opt.step()
    return model


def _prf_threshold(y_true: np.ndarray, probs: np.ndarray):
    """在阈值 0.5 下计算 P/R/F1 + 误报率。"""
    pred = (probs > 0.5).astype(int)
    tp = int(((y_true == 1) & (pred == 1)).sum())
    fp = int(((y_true == 0) & (pred == 1)).sum())
    fn = int(((y_true == 1) & (pred == 0)).sum())
    p = tp / (tp + fp) if (tp + fp) else 0.0
    r = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * p * r / (p + r) if (p + r) else 0.0
    fpr = fp / max(int((y_true == 0).sum()), 1)
    return (round(p, 4), round(r, 4), round(f1, 4), round(fpr, 4))


def run_elliptic_supervised_eval(directory: str, epochs: int = 150, hidden: int = 64,
                                 lr: float = 0.01, seed: int = 0) -> Dict[str, Any]:
    """Elliptic 域内有监督评测：GCN(特征+图) vs MLP(纯特征)，时序划分。"""
    try:
        import torch  # noqa: F401
    except ImportError:
        return {"error": "torch 不可用，无法跑有监督训练"}

    account_ids, edges, labels, X, timestep = _load(directory)
    n = len(account_ids)
    train_idx, test_idx, y_all = _split(account_ids, labels, timestep)
    y_train = y_all[train_idx]
    y_test = y_all[test_idx]

    # 特征标准化（只用训练集统计量，防泄漏）
    from sklearn.preprocessing import StandardScaler
    sc = StandardScaler().fit(X[train_idx])
    Xn = sc.transform(X)

    A = _normalized_adj(n, edges)
    import torch
    A_t = _to_torch_sparse(A)
    X_t = torch.FloatTensor(Xn)

    methods: Dict[str, Any] = {}
    for use_graph, name in ((True, "GCN(features+graph)"), (False, "MLP(features only)")):
        model = _fit(use_graph, A_t, X_t, train_idx, y_train,
                     epochs=epochs, hidden=hidden, lr=lr, seed=seed)
        model.eval()
        with torch.no_grad():
            logits = model(A_t, X_t) if use_graph else model(X_t)
            probs = torch.sigmoid(logits[test_idx]).numpy()
        p, r, f1, fpr = _prf_threshold(y_test, probs)
        methods[name] = {
            "precision": p, "recall": r, "f1": f1,
            "fpr_误报率": fpr, "auc": _auc_rank(y_test, probs),
            "n_test": int(len(y_test)), "n_test_anomaly": int(y_test.sum()),
        }

    return {
        "dataset": {
            "n_accounts": n, "n_edges": int(len(edges)),
            "n_labeled": int(len(train_idx) + len(test_idx)),
            "n_train": int(len(train_idx)), "n_test": int(len(test_idx)),
            "n_train_anomaly": int(y_train.sum()), "n_test_anomaly": int(y_test.sum()),
            "split": f"temporal (train timestep≤{TRAIN_TS_MAX}, test >{TRAIN_TS_MAX})",
            "source": "Elliptic (Webber et al., KDD 2019)",
            "note": "域内有监督评测：证明拿到标注后能否工作，不混淆为零样本通用能力",
        },
        "methods": methods,
    }


def fmt_supervised(result: Dict[str, Any]) -> str:
    lines = ["", "=" * 70,
             f"Elliptic 有监督训练评测（{result['dataset']['source']}）",
             f"数据集: 节点={result['dataset']['n_accounts']} 边={result['dataset']['n_edges']} "
             f"标注={result['dataset']['n_labeled']}",
             f"划分: {result['dataset']['split']}",
             f"训练: {result['dataset']['n_train']}（异常 {result['dataset']['n_train_anomaly']}） | "
             f"测试: {result['dataset']['n_test']}（异常 {result['dataset']['n_test_anomaly']}）",
             "=" * 70]
    header = f"{'方法':<24}{'P':>7}{'R':>7}{'F1':>8}{'误报率':>8}{'AUC':>8}"
    lines.append(header)
    lines.append("-" * 70)
    for name, m in result["methods"].items():
        lines.append(f"{name:<24}{m['precision']:>7.3f}{m['recall']:>7.3f}"
                     f"{m['f1']:>8.3f}{m['fpr_误报率']:>8.3f}{m['auc']:>8.3f}")
    lines.append("-" * 70)
    lines.append("注: 阈值 0.5 下 P/R/F1；AUC 无阈值。GCN-MLP 之差 = 图结构的增量。")
    return "\n".join(lines)
