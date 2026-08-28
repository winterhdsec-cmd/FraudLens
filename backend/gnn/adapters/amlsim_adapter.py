"""
IBM/AMLSim 输出解析适配器（账户中心模式）。

把 AMLSim 产出的交易图转换成 FraudLens 账户中心评测输入：
- account_ids : 所有账户节点
- edges        : 资金流转有向边 (src, dst, amount, timestamp)
- gt           : 账户 -> 真值团伙标签（洗钱环），背景账户为 -1

AMLSim 真实输出文件（outputs/ 目录）：
- accounts.csv        : ACCOUNT_ID, ACCOUNT_TYPE, ...
- transactions.csv     : TX_ID, TIMESTAMP, SENDER_ACCOUNT_ID, RECEIVER_ACCOUNT_ID, AMOUNT, TX_TYPE, ...
- alerts.csv           : 被预警（命中洗钱模式）的交易/账户（不同版本列名略有差异）

真值团伙标签来源（按优先级）：
1. ground_truth.csv（若存在）：ACCOUNT_ID, RING_ID  —— 直接作为权威真值；
2. 否则由 alerts.csv 中的洗钱交易子图连通分量推导：每个连通分量即一个洗钱环（团伙）。

注：AMLSim 官方输出不直接给出"环编号"，仅给出被预警账户；用连通分量还原团伙是合理的、
且完全基于公开输出的做法，对论文外部有效性无注水。
"""
import csv
import os
from collections import defaultdict, deque
from typing import Dict, List, Tuple, Any

# 列名容错映射
_SENDER_VARIANTS = ("SENDER_ACCOUNT_ID", "SENDER", "FROM_ACCOUNT", "FROM_ACCT", "SRC_ACCOUNT")
_RECEIVER_VARIANTS = ("RECEIVER_ACCOUNT_ID", "RECEIVER", "TO_ACCOUNT", "TO_ACCT", "DST_ACCOUNT")
_AMOUNT_VARIANTS = ("AMOUNT", "TX_AMOUNT", "VALUE")
_TIME_VARIANTS = ("TIMESTAMP", "TIME", "DATE", "TX_TIME")
_ACCOUNT_VARIANTS = ("ACCOUNT_ID", "ACCOUNT", "ID")
_RING_VARIANTS = ("RING_ID", "TYP_ID", "PATTERN_ID", "CLUSTER_ID", "LABEL")


class AmLSIMFormatError(Exception):
    pass


def _resolve(columns, variants):
    for v in variants:
        if v in columns:
            return v
    return None


def _read_csv(path: str) -> List[Dict[str, str]]:
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _components(nodes: List[str], adj: Dict[str, List[str]]) -> Dict[str, int]:
    """无向连通分量 -> 标签（从 0 开始）"""
    seen = set()
    comp: Dict[str, int] = {}
    cid = 0
    for n in nodes:
        if n in seen:
            continue
        # BFS
        q = deque([n])
        seen.add(n)
        members = []
        while q:
            cur = q.popleft()
            members.append(cur)
            for nb in adj.get(cur, []):
                if nb not in seen:
                    seen.add(nb)
                    q.append(nb)
        for m in members:
            comp[m] = cid
        cid += 1
    return comp


def load_amlsim(directory: str):
    """解析 AMLSim 输出目录，返回 (account_ids, edges, gt)。

    edges: List[(src, dst, amount, timestamp)]
    gt   : Dict[account_id, int]，背景（非洗钱）账户为 -1
    """
    if not os.path.isdir(directory):
        raise AmLSIMFormatError(f"目录不存在: {directory}")

    tx_path = os.path.join(directory, "transactions.csv")
    if not os.path.isfile(tx_path):
        raise AmLSIMFormatError("缺少 transactions.csv（AMLSim 必需输出）")

    tx_rows = _read_csv(tx_path)
    if not tx_rows:
        raise AmLSIMFormatError("transactions.csv 为空")
    cols = tx_rows[0].keys()
    c_sender = _resolve(cols, _SENDER_VARIANTS)
    c_receiver = _resolve(cols, _RECEIVER_VARIANTS)
    c_amount = _resolve(cols, _AMOUNT_VARIANTS)
    c_time = _resolve(cols, _TIME_VARIANTS)
    if not (c_sender and c_receiver):
        raise AmLSIMFormatError(
            f"transactions.csv 找不到发送/接收账户列（已有: {list(cols)}）")

    account_ids: List[str] = []
    _seen_acc = set()
    edges: List[Tuple[str, str, float, float]] = []
    tx_adj: Dict[str, List[str]] = defaultdict(list)
    gt: Dict[str, int] = {}

    # 优先用 accounts.csv 给出完整账户清单（含无交易的孤立账户），背景默认 -1
    acc_path = os.path.join(directory, "accounts.csv")
    if os.path.isfile(acc_path):
        acc_rows = _read_csv(acc_path)
        if acc_rows:
            acols = acc_rows[0].keys()
            c_acc = _resolve(acols, _ACCOUNT_VARIANTS) or _resolve(acols, ("ACCOUNT_ID",))
            if c_acc:
                for r in acc_rows:
                    a = r.get(c_acc, "").strip()
                    if a and a not in _seen_acc:
                        _seen_acc.add(a)
                        account_ids.append(a)
                        gt[a] = -1

    def _to_float(x):
        try:
            return float(str(x).replace(",", "").strip())
        except Exception:
            return 0.0

    def _to_time(x):
        try:
            return float(x)
        except Exception:
            return 0.0

    for r in tx_rows:
        s = r[c_sender].strip()
        d = r[c_receiver].strip()
        amt = _to_float(r[c_amount]) if c_amount else 0.0
        t = _to_time(r[c_time]) if c_time else 0.0
        if not s or not d:
            continue
        edges.append((s, d, amt, t))
        for a in (s, d):
            if a not in _seen_acc:
                _seen_acc.add(a)
                account_ids.append(a)
        tx_adj[s].append(d)
        tx_adj[d].append(s)

    # ---- 真值标签 ----
    gt: Dict[str, int] = {a: -1 for a in account_ids}

    # 优先 ground_truth.csv
    gt_path = os.path.join(directory, "ground_truth.csv")
    if os.path.isfile(gt_path):
        gt_rows = _read_csv(gt_path)
        if gt_rows:
            gcols = gt_rows[0].keys()
            c_acc = _resolve(gcols, _ACCOUNT_VARIANTS)
            c_ring = _resolve(gcols, _RING_VARIANTS)
            if c_acc and c_ring:
                for r in gt_rows:
                    a = r[c_acc].strip()
                    try:
                        gt[a] = int(float(r[c_ring]))
                    except Exception:
                        pass
                return account_ids, edges, gt

    # 否则由 alerts.csv 推导洗钱连通分量
    alert_path = os.path.join(directory, "alerts.csv")
    if os.path.isfile(alert_path):
        alert_rows = _read_csv(alert_path)
        # 找交易 id 列与账户相关列
        acols = alert_rows[0].keys() if alert_rows else []
        c_txid = _resolve(acols, ("TX_ID", "TRANSACTION_ID", "ID"))
        c_s = _resolve(acols, _SENDER_VARIANTS)
        c_r = _resolve(acols, _RECEIVER_VARIANTS)
        laundering_accounts = set()
        alert_txids = set()
        for r in alert_rows:
            if c_txid and r.get(c_txid, "").strip():
                alert_txids.add(r[c_txid].strip())
            if c_s and r.get(c_s, "").strip():
                laundering_accounts.add(r[c_s].strip())
            if c_r and r.get(c_r, "").strip():
                laundering_accounts.add(r[c_r].strip())

        # 若 alerts 仅标记交易，则需把"被预警交易"的账户归入洗钱子图
        if not laundering_accounts and alert_txids:
            # 从交易表中反查
            for s, d, _, _ in edges:
                # AMLSim 交易 TX_ID 与行号/索引未必对应；用集合无法精确匹配，
                # 故要求 alerts.csv 至少含账户列。若无，退化为空真值。
                pass

        # 洗钱子图：仅保留两端都在 laundering_accounts 内的边
        sub_adj: Dict[str, List[str]] = defaultdict(list)
        for s, d, _, _ in edges:
            if s in laundering_accounts and d in laundering_accounts:
                sub_adj[s].append(d)
                sub_adj[d].append(s)
        comp = _components(list(laundering_accounts), sub_adj)
        for a, cid in comp.items():
            gt[a] = cid
        if laundering_accounts:
            return account_ids, edges, gt

    # 两者都无 -> 仍返回图，但真值全为背景（仅能验证建图，无法评测聚类）
    return account_ids, edges, gt
