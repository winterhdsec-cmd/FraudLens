"""
Elliptic 真实比特币反洗钱数据集适配器（Webber et al., KDD 2019）。

把 Elliptic 交易图转换成 FraudLens 评测输入：
- account_ids : 节点列表（对齐特征文件行序，映射为 "a0".."aN-1"）
- edges       : np.ndarray (E, 2) int32 —— 有向交易边（txId1 -> txId2 的账户中心映射）
- labels      : Dict[account_id, int] —— 1=非法(illicit), 0=合法(licit), -1=未知(unknown)
- features    : np.ndarray (N, F) float32 或 None（文件缺失时返回 None，评测退化为结构特征）

数据格式（Kaggle 官方 / HF 镜像同构）：
  elliptic_txs_features.csv : 无表头，列0=txId, 列1=timestep, 列2..=166 维特征（可含 NaN）
  elliptic_txs_edgelist.csv : 表头 txId1,txId2，有向边
  elliptic_txs_classes.csv  : 表头 txId,class，class ∈ {'1'(illicit), '2'(licit), 'unknown'}
统计：203,769 笔交易 / 234,355 条有向边 / 49 个时间步 / 非法约 9.8%。

注意：本数据集项目 2026-07-30 已下载于 backend/data/datasets/elliptic/，
train_han.py / experiment_elliptic.py / experiment_elliptic_refine.py /
pathb_elliptic.py 均已有使用记录（盲扫 F1≈0.016，扩线特征KMeans F1=0.720）。
本适配器把标签语义统一为 1/0/-1，供 eval_framework.run_node_fraud_eval 做
"节点级欺诈检测"（top-k P/R/F1 + AUC），与既有社区/扩线协议互补。
"""
import os
from typing import Dict, List, Optional, Tuple

import numpy as np


class EllipticFormatError(Exception):
    pass


def load_elliptic(directory: str, with_features: bool = True):
    """解析 Elliptic 目录，返回 (account_ids, edges, labels, features)。

    features 为 None 表示特征文件缺失（评测退化为纯结构风险）。
    """
    cls_path = os.path.join(directory, "elliptic_txs_classes.csv")
    edge_path = os.path.join(directory, "elliptic_txs_edgelist.csv")
    feat_path = os.path.join(directory, "elliptic_txs_features.csv")
    if not (os.path.isfile(cls_path) and os.path.isfile(edge_path)):
        raise EllipticFormatError(
            "缺少 elliptic_txs_classes.csv / elliptic_txs_edgelist.csv（Elliptic 必需文件）")

    try:
        import pandas as pd
    except ImportError as e:
        raise EllipticFormatError(f"需要 pandas 读取 Elliptic: {e}")

    # ---- 特征（可选）----
    features: Optional[np.ndarray] = None
    if with_features and os.path.isfile(feat_path):
        feats = pd.read_csv(feat_path, header=None).values
        tx_ids = feats[:, 0].astype(np.int64)
        features = np.nan_to_num(feats[:, 1:].astype(np.float32), nan=0.0,
                                 posinf=0.0, neginf=0.0)
    else:
        tx_ids = None

    # ---- 标签 ----
    cls = pd.read_csv(cls_path, header=0).values
    _map = {"1": 1, "2": 0, "unknown": -1}  # illicit=1, licit=0, unknown=-1
    labels = {int(r[0]): _map.get(str(r[1]).strip(), -1) for r in cls}

    # ---- 节点清单（以特征文件行序为准；缺失特征文件时用标签文件 txId 全集）----
    if tx_ids is not None:
        id_list = [int(t) for t in tx_ids]
    else:
        id_list = sorted(labels.keys())
    n = len(id_list)
    id2idx = {t: i for i, t in enumerate(id_list)}

    # ---- 边 ----
    edges_df = pd.read_csv(edge_path, header=0).values.astype(np.int64)
    rows: List[Tuple[int, int]] = []
    for s, d in edges_df:
        si, di = id2idx.get(int(s)), id2idx.get(int(d))
        if si is None or di is None or si == di:
            continue
        rows.append((si, di))
    if not rows:
        raise EllipticFormatError("边表为空或全部被过滤")

    account_ids = [f"a{i}" for i in range(n)]
    label_map = {account_ids[i]: labels.get(id_list[i], -1) for i in range(n)}
    return account_ids, np.asarray(rows, dtype=np.int32), label_map, features
