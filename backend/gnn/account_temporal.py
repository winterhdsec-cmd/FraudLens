"""
账户时序图构建器 (Track A)
=========================
将 accounts_tx -> 账户时序图：
  - 节点 = 账户
  - 边   = 有向时序交易（边特征 = 金额/时间）
  - 节点特征 = 行为统计（出入度/金额分布/时间跨度/PageRank 等）
  - 邻接 = 对称化拓扑（供 GraphSAGE 消息传递捕获环连通性）

解决 HAN 为"案情图"设计、AMLSim 为"纯账户交易网"导致的 schema 错位根因。
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

import networkx as nx
import numpy as np


def _parse_ts(ts: Any) -> Optional[float]:
    """宽松解析时间戳：None/空 -> None；int/float -> epoch；字符串尝试常见格式或数值。"""
    if ts is None:
        return None
    if isinstance(ts, (int, float)):
        return float(ts)
    s = str(ts).strip()
    if not s:
        return None
    try:
        import datetime as _dt

        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
            try:
                return _dt.datetime.strptime(s, fmt).timestamp()
            except ValueError:
                continue
    except Exception:
        pass
    try:
        v = float(s)
        if v > 1e12:  # 毫秒 -> 秒
            v /= 1000.0
        return v
    except ValueError:
        return None


def build_account_graph(
    accounts_tx: List[Dict[str, Any]],
    use_log_amount: bool = True,
    symmetrize_adj: bool = True,
    weighted: bool = False,
    sparse_adj: bool = False,
) -> Dict[str, Any]:
    """构建账户时序图。

    Returns:
        {
            "node_ids": List[str],
            "index":    Dict[str, int],
            "adj":      np.ndarray (N,N) float32（sparse_adj=False，默认）
                       / torch.sparse_coo_tensor (N,N)（sparse_adj=True，防大规模图 OOM）,
            "features": np.ndarray (N,12) float32 (已 z-score 归一),
            "G":        nx.DiGraph,
        }
    """
    G = nx.DiGraph()
    edge_w: Dict = {}
    for tx in accounts_tx:
        src = tx.get("from_account") or tx.get("sender")
        dst = tx.get("to_account") or tx.get("receiver")
        if src is None or dst is None:
            continue
        amt = float(tx.get("amount") or 0.0)
        ts = _parse_ts(tx.get("timestamp"))
        G.add_edge(src, dst, amount=amt, ts=ts)
        if weighted:
            edge_w[(src, dst)] = edge_w.get((src, dst), 0.0) + amt

    node_ids = list(G.nodes())
    n = len(node_ids)
    idx = {a: i for i, a in enumerate(node_ids)}

    # 邻接矩阵（weighted=True 时按交易金额 log1p 加权，让消息传递偏向强资金链）
    if sparse_adj:
        # 大规模图（如 AMLSim 全图 4.3 万节点）稠密矩阵会 OOM；改用 torch 稀疏 COO。
        # 无需 scipy：直接从边表构造稀疏张量。
        import torch as _torch

        rows, cols, vals = [], [], []
        for u, v, d in G.edges(data=True):
            ui = idx[u]
            vi = idx[v]
            w = math.log1p(d.get("amount", 0.0)) if weighted else 1.0
            rows.append(ui)
            cols.append(vi)
            vals.append(w)
            if symmetrize_adj:
                rows.append(vi)
                cols.append(ui)
                vals.append(w)
        if rows:
            _idx_t = _torch.tensor([rows, cols], dtype=_torch.long)
            _val_t = _torch.tensor(vals, dtype=_torch.float32)
            adj = _torch.sparse_coo_tensor(_idx_t, _val_t, (n, n), check_invariants=False).coalesce()
        else:
            adj = _torch.sparse_coo_tensor((2, 0), [], (n, n), check_invariants=False).coalesce()
    else:
        adj = np.zeros((n, n), dtype=np.float32)
        if weighted:
            for (u, v), w in edge_w.items():
                adj[idx[u], idx[v]] = math.log1p(w)
        else:
            for u, v in G.edges():
                adj[idx[u], idx[v]] = 1.0
        if symmetrize_adj:
            if weighted:
                sym = (adj + adj.T) / 2.0
            else:
                sym = (adj + adj.T) > 0
            adj = sym.astype(np.float32)

    # 行为节点特征（12 维）
    feats = np.zeros((n, 12), dtype=np.float32)
    pg = (
        nx.pagerank(nx.Graph(G), alpha=0.85)
        if n > 1
        else {a: 1.0 / n for a in node_ids}
    )

    def lg(x: float) -> float:
        return math.log1p(abs(x)) if use_log_amount else x

    for i, a in enumerate(node_ids):
        in_edges = list(G.in_edges(a, data=True))
        out_edges = list(G.out_edges(a, data=True))
        in_amt = [d["amount"] for _, _, d in in_edges]
        out_amt = [d["amount"] for _, _, d in out_edges]
        in_ts = [d["ts"] for _, _, d in in_edges if d["ts"] is not None]
        out_ts = [d["ts"] for _, _, d in out_edges if d["ts"] is not None]
        total_in = sum(in_amt)
        total_out = sum(out_amt)
        mean_in = float(np.mean(in_amt)) if in_amt else 0.0
        mean_out = float(np.mean(out_amt)) if out_amt else 0.0
        all_amt = in_amt + out_amt
        std_amt = float(np.std(all_amt)) if all_amt else 0.0
        n_tx = len(in_amt) + len(out_amt)
        all_ts = in_ts + out_ts
        span = (max(all_ts) - min(all_ts)) if len(all_ts) > 1 else 0.0
        gaps = np.diff(sorted(all_ts)) if len(all_ts) > 1 else np.array([0.0])
        mean_gap = float(np.mean(gaps)) if gaps.size else 0.0
        feats[i] = [
            G.in_degree(a),
            G.out_degree(a),
            lg(total_in),
            lg(total_out),
            lg(total_out - total_in),
            lg(mean_in),
            lg(mean_out),
            lg(std_amt),
            n_tx,
            span / 86400.0,
            mean_gap / 86400.0,
            pg.get(a, 0.0),
        ]

    # z-score 归一
    mu = feats.mean(axis=0, keepdims=True)
    sd = feats.std(axis=0, keepdims=True)
    sd[sd == 0] = 1.0
    feats = (feats - mu) / sd

    return {
        "node_ids": node_ids,
        "index": idx,
        "adj": adj,
        "features": feats,
        "G": G,
    }
