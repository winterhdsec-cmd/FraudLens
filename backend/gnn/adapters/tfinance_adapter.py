"""
T-Finance 公开基准适配器（Tang et al., ICML 2022, "Rethinking Graph Neural Networks
for Anomaly Detection"，即 BWGNN 论文附带数据集）。

把 T-Finance 金融交易异常检测数据集转换成 FraudLens 评测输入：
- account_ids : 账户节点列表。T-Finance 节点为 0..N-1 匿名账户，这里统一映射为 "a0".."aN-1"
- edges       : np.ndarray (E, 2) int32 —— 有向交易边 (src_idx, dst_idx)
- labels      : Dict[account_id, int] —— 0=正常账户, 1=异常账户（欺诈者/洗钱嫌疑人/在线赌博）
- features    : np.ndarray (N, 10) float32 —— 官方 10 维匿名特征（注册日期/交易活动/交互频次等）

数据来源与格式（诚实标注）：
- 官方仓库 https://github.com/Wenqin740/Rethinking-Anomaly-Detection 的 Google Drive
  提供 DGL 图格式 zip（dataset/tfinance 目录）。本开发环境网络无法访问 Drive，
  故适配器支持两类**明文 CSV**布局（大量复现仓库采用，fetch_tfinance.py 也做转换）：
    1) 规范布局（scripts/fetch_tfinance.py 的产出）：
         features.csv   : 特征矩阵（行号即账户 id，可带 f0,f1.. 表头）
         edges.csv      : 边表 src,dst（可带表头）
         labels.txt     : 每行一个 0/1，顺序与 features.csv 对齐
    2) BWGNN 复现布局：
         tf_fin.csv      / tf_fin_edges.csv / tf_fin_label.txt（语义同上）
- T-Finance 统计：39,357 节点 / 21,222,543 有向边 / 异常账户 4.58%。
  注意：T-Finance 边只表示"存在交易关系"，**无金额字段**，故本适配器统一 amount=1
  （权重即交易条数），与 AMLSim 适配器返回 4 元组 edges 的接口不同，评测见
  eval_framework.run_tfinance_eval。

评测语义提醒：T-Finance 是**账户级 0/1 标注**，不是"团伙环"标注，因此评测走
"节点级欺诈检测"（P/R/F1/误报率/AUC），与 AMLSim 的社区聚类评测互补。
"""
import csv
import os
from typing import Dict, List, Tuple, Any

import numpy as np

_LAYOUT_CANONICAL = "canonical"
_LAYOUT_TF_FIN = "tf_fin"


class TFinanceFormatError(Exception):
    pass


def _detect_layout(directory: str) -> str:
    if os.path.isfile(os.path.join(directory, "features.csv")):
        return _LAYOUT_CANONICAL
    if os.path.isfile(os.path.join(directory, "tf_fin.csv")):
        return _LAYOUT_TF_FIN
    raise TFinanceFormatError(
        "目录中未找到 features.csv 或 tf_fin.csv（T-Finance 明文格式）。"
        "请先运行 scripts/fetch_tfinance.py 下载并整理数据。")


def _read_features(path: str) -> List[List[float]]:
    feats: List[List[float]] = []
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        rd = csv.reader(f)
        for r in rd:
            if not r:
                continue
            try:
                row = [float(x) for x in r if x.strip() != ""]
            except ValueError:
                continue  # 表头行 f0,f1,... 或非数字行
            if len(row) < 2:
                continue
            feats.append(row)
    if not feats:
        raise TFinanceFormatError(f"特征文件为空或无法解析: {path}")
    return feats


def _load_edges(path: str, n: int) -> np.ndarray:
    rows: List[Tuple[int, int]] = []
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        rd = csv.reader(f)
        for r in rd:
            if not r or len(r) < 2:
                continue
            a, b = r[0].strip(), r[1].strip()
            if a.lower() in ("src", "source", "from") or b.lower() in ("dst", "dest", "to"):
                continue  # 表头
            try:
                i, j = int(a), int(b)
            except ValueError:
                continue
            if i == j or i < 0 or j < 0 or i >= n or j >= n:
                continue
            rows.append((i, j))
    if not rows:
        raise TFinanceFormatError(f"边表为空或全部被过滤: {path}")
    return np.asarray(rows, dtype=np.int32)


def _read_labels(path: str) -> List[int]:
    out: List[int] = []
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        for ln in f:
            ln = ln.strip()
            if not ln:
                continue
            try:
                out.append(1 if int(float(ln)) > 0 else 0)
            except ValueError:
                raise TFinanceFormatError(f"标签行无法解析: {ln!r}")
    return out


def load_tfinance(directory: str):
    """解析 T-Finance 目录，返回 (account_ids, edges, labels, features)。

    edges 为 np.ndarray (E,2) int32；labels 为 Dict[account_id, int]。
    """
    layout = _detect_layout(directory)
    if layout == _LAYOUT_CANONICAL:
        feat_file, edge_file, label_file = "features.csv", "edges.csv", "labels.txt"
    else:
        feat_file, edge_file, label_file = "tf_fin.csv", "tf_fin_edges.csv", "tf_fin_label.txt"

    feats = _read_features(os.path.join(directory, feat_file))
    n = len(feats)
    edges = _load_edges(os.path.join(directory, edge_file), n)
    labels = _read_labels(os.path.join(directory, label_file))
    if len(labels) != n:
        raise TFinanceFormatError(
            f"标签数 {len(labels)} != 节点数 {n}（文件: {label_file}）")

    account_ids = [f"a{i}" for i in range(n)]
    label_map = {account_ids[i]: labels[i] for i in range(n)}
    feat_arr = np.asarray(feats, dtype=np.float32)
    return account_ids, edges, label_map, feat_arr
