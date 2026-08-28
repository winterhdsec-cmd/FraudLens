"""
带信号合成账户数据集 (Track A)
=============================
生成"带清晰欺诈环"的账户交易数据，用于诚实演示：
  "当图结构 / 信号对时，训练后的 GNN 能高 F1 恢复团伙"。

构成：
  - 背景账户：随机小额交易（模拟正常经济活动）
  - 资金环：每个环内账户按可识别模式（显著区别于背景的金额分布）形成有向循环 +
    环内额外互转（增加结构密度）+ 少量与背景的跨谈（模拟真实混杂噪声）
  - 真实标签 gt：账户 -> 环 id（背景为 -1）

注意：AMLSim 原始全图（F1≈0.0016）仅作难度基线，本生成器与它无关，
用于演示"信号存在时 GNN 可用"，绝不冒充真实验证（docs/06 金律）。
"""
from __future__ import annotations

from typing import Dict, List, Tuple

import numpy as np


def generate(
    n_background: int = 1200,
    n_rings: int = 20,
    ring_size: int = 6,
    p_bg: float = 0.0006,
    seed: int = 42,
    ring_amount_mu: float = 50000.0,
    ring_amount_sigma: float = 3000.0,
    bg_amount_mu: float = 2000.0,
    bg_amount_sigma: float = 1500.0,
    cross_talk: float = 0.25,
) -> Tuple[List[Dict[str, str]], Dict[str, int]]:
    rng = np.random.default_rng(seed)
    n_total = n_background + n_rings * ring_size
    accounts = [f"A{i:05d}" for i in range(n_total)]
    gt: Dict[str, int] = {a: -1 for a in accounts[:n_background]}

    txs: List[Dict[str, str]] = []
    base = 1_700_000_000.0  # 某参考 epoch
    ring_nodes = accounts[n_background:]

    for r in range(n_rings):
        members = ring_nodes[r * ring_size : (r + 1) * ring_size]
        for m in members:
            gt[m] = r
        # 主循环（有向环，金额显著区别于背景）
        for k in range(ring_size):
            src = members[k]
            dst = members[(k + 1) % ring_size]
            amt = max(float(rng.normal(ring_amount_mu, ring_amount_sigma)), 1.0)
            ts = base + k * 3600.0 + float(rng.uniform(0, 1800))
            txs.append(
                {"from_account": src, "to_account": dst, "amount": amt, "timestamp": ts}
            )
        # 环内额外互转（增加结构密度）
        for _ in range(max(1, ring_size // 2)):
            a = members[int(rng.integers(ring_size))]
            b = members[int(rng.integers(ring_size))]
            if a != b:
                txs.append(
                    {
                        "from_account": a,
                        "to_account": b,
                        "amount": max(float(rng.normal(ring_amount_mu, ring_amount_sigma)), 1.0),
                        "timestamp": base + float(rng.uniform(0, 24 * 3600)),
                    }
                )

    # 背景随机交易
    bg = accounts[:n_background]
    n_bg_tx = int(n_background * n_background * p_bg)
    for _ in range(n_bg_tx):
        src = bg[int(rng.integers(n_background))]
        dst = bg[int(rng.integers(n_background))]
        if src == dst:
            continue
        amt = max(float(rng.normal(bg_amount_mu, bg_amount_sigma)), 1.0)
        txs.append(
            {
                "from_account": src,
                "to_account": dst,
                "amount": amt,
                "timestamp": base + float(rng.uniform(0, 30 * 24 * 3600)),
            }
        )

    # 跨谈：环节点与背景少量交易（噪声，模拟真实混杂）
    for r in range(n_rings):
        members = ring_nodes[r * ring_size : (r + 1) * ring_size]
        for m in members:
            if rng.random() < cross_talk:
                dst = bg[int(rng.integers(n_background))]
                txs.append(
                    {
                        "from_account": m,
                        "to_account": dst,
                        "amount": max(float(rng.normal(bg_amount_mu, bg_amount_sigma)), 1.0),
                        "timestamp": base + float(rng.uniform(0, 30 * 24 * 3600)),
                    }
                )

    rng.shuffle(txs)
    return txs, gt
