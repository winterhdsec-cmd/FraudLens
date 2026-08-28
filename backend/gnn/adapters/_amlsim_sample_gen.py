"""
按 IBM/AMLSim 文档 schema 复现一份格式一致的样本数据（账户中心）。

用途：本开发环境无 Maven，无法直接运行官方 Java 生成器。此脚本产出与
AMLSim 输出同 schema 的 CSV（accounts.csv / transactions.csv / ground_truth.csv /
alerts.csv），使适配器与账户中心评测可端到端验证。论文中如实标注：
"采用与 IBM/AMLSim 相同数据模型生成的基准（schema-compatible benchmark）"；
若后续用官方生成器产出真实 CSV，直接放入同目录即可复用同一条管线。

生成的洗钱拓扑（typology）：scatter-gather
  多个马甲账户(mule) -> 归集账户(collector) -> 多个分流账户(payout)
同一 typology 内的账户构成一个"团伙"(真值环)。
背景账户间随机生成噪声交易（含少量跨环边，模拟误共享）。
"""
import csv
import os
import random
from typing import Dict, List, Tuple


def generate(directory: str,
             n_rings: int = 8,
             mules_per_ring: int = 6,
             payouts_per_ring: int = 3,
             n_noise_accounts: int = 200,
             cross_ring_prob: float = 0.05,
             cross_ring_laundering: float = 0.10,
             seed: int = 42) -> Tuple[List[str], List[Tuple[str, str, float, float]], Dict[str, int]]:
    rd = random.Random(seed)
    os.makedirs(directory, exist_ok=True)

    accounts: List[str] = []
    edges: List[Tuple[str, str, float, float]] = []
    gt: Dict[str, int] = {}
    alert_txids: List[str] = []
    tx_counter = [0]
    ring_accounts_all: List[str] = []

    def new_tx(s, d, amt, ttype):
        tx_counter[0] += 1
        tx_id = f"T{tx_counter[0]:07d}"
        edges.append((s, d, round(amt, 2), float(tx_counter[0])))
        return tx_id

    # 洗钱环
    for ring in range(n_rings):
        prefix = f"R{ring:02d}"
        collector = f"{prefix}C"
        mules = [f"{prefix}M{i}" for i in range(mules_per_ring)]
        payouts = [f"{prefix}P{i}" for i in range(payouts_per_ring)]
        ring_accounts = [collector] + mules + payouts
        ring_accounts_all.extend(ring_accounts)
        for a in ring_accounts:
            accounts.append(a)
            gt[a] = ring
        # mule -> collector
        for m in mules:
            amt = rd.uniform(5_000, 80_000)
            tid = new_tx(m, collector, amt, "TRANSFER")
            alert_txids.append(tid)
        # collector -> payout
        for p in payouts:
            amt = rd.uniform(20_000, 150_000)
            tid = new_tx(collector, p, amt, "TRANSFER")
            alert_txids.append(tid)

    # 跨环洗钱边（真实场景：资金马甲/归集账户常被多个团伙复用，制造结构干扰）
    n_cross_l = int(len(ring_accounts_all) * cross_ring_laundering)
    for _ in range(max(n_cross_l, 1)):
        a = rd.choice(ring_accounts_all)
        others = [x for x in ring_accounts_all if gt[x] != gt[a]]
        if not others:
            continue
        b = rd.choice(others)
        new_tx(a, b, rd.uniform(2_000, 40_000), "TRANSFER")

    # 背景（噪声）账户
    noise_accounts = [f"N{i:04d}" for i in range(n_noise_accounts)]
    for a in noise_accounts:
        accounts.append(a)
        gt[a] = -1
    # 背景内部随机交易
    for _ in range(int(n_noise_accounts * 0.8)):
        s = rd.choice(noise_accounts)
        d = rd.choice(noise_accounts)
        if s != d:
            new_tx(s, d, rd.uniform(500, 50_000), "TRANSFER")
    # 跨环噪声边（少量，模拟账户误共享/干扰）
    ring_accounts_all = [a for a in accounts if gt[a] != -1]
    cross_n = int(len(ring_accounts_all) * cross_ring_prob)
    for _ in range(max(cross_n, 1)):
        a = rd.choice(ring_accounts_all)
        b = rd.choice(noise_accounts)
        new_tx(a, b, rd.uniform(1_000, 30_000), "TRANSFER")

    # ---- 写 CSV ----
    def _w(name, header, rows):
        with open(os.path.join(directory, name), "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(header)
            w.writerows(rows)

    # accounts.csv
    _w("accounts.csv", ["ACCOUNT_ID", "ACCOUNT_TYPE"],
       [[a, "TRANSFER" if a.startswith(("R", "N")) else "CASH"] for a in accounts])

    # transactions.csv
    tx_rows = []
    for i, (s, d, amt, t) in enumerate(edges, 1):
        tx_rows.append([f"T{i:07d}", int(t), s, d, f"{amt:.2f}", "TRANSFER"])
    _w("transactions.csv",
       ["TX_ID", "TIMESTAMP", "SENDER_ACCOUNT_ID", "RECEIVER_ACCOUNT_ID", "AMOUNT", "TX_TYPE"],
       tx_rows)

    # ground_truth.csv
    _w("ground_truth.csv", ["ACCOUNT_ID", "RING_ID"],
       [[a, gt[a]] for a in accounts])

    # alerts.csv（被预警的交易 = 洗钱交易）
    _w("alerts.csv", ["TX_ID", "ALERT"],
       [[tid, 1] for tid in alert_txids])

    return accounts, edges, gt


if __name__ == "__main__":
    out = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)))), "gnn", "amlsim_sample")
    acc, ed, g = generate(out)
    print(f"生成 AMLSim 格式样本: accounts={len(acc)} edges={len(ed)} "
          f"rings={len(set(v for v in g.values() if v >= 0))}")
