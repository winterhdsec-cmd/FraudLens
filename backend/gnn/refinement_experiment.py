"""
Refinement（扩线）实验 — Track A 延伸（诚实版）
================================================
核心问题：真实反诈是"给一条线索（锚点账户）→ 在嫌疑邻居子图里精准扩线并案"，
而非"在 4 万账户里盲扫所有团伙"。本实验验证 GNN 在该实战设定下是否真有用。

(1) 合成信号账户集（每环带**独立金额签名**，模拟真实团伙各自资金模式）：
    - 比较 [原始特征+KMeans, 未训练GNN, 训练后GNN, Louvain(纯拓扑)]
      在"嫌疑子图（锚点 k 跳邻居）"上的环恢复 F1。
    - 关键假设：当环间拓扑交叉噪声升高时，纯拓扑 Louvain 下降，
      而训练后 GNN（用行为/金额特征）维持或反超 → 证明 GNN 的扩线增量价值。

(2) AMLSim 大规模锚点 refinement（诚实外部验证）：
    - 取真实洗钱环节点为锚点，构建 k 跳嫌疑邻居子图；
    - 比较 训练后GNN vs Louvain vs KMeans 在子图内恢复环的 F1；
    - 对比盲扫基线 F1≈0.002（docs/04_论文进度.md §七）。

诚实口径：合成 = 方法论证明（信号存在 + 训练后 GNN 可用）；
AMLSim 真实 = 外部难度基线，结果无论高低如实写，绝不称"真实验证"（docs/06 金律）。
"""
from __future__ import annotations

import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score

from gnn.account_temporal import build_account_graph
from gnn.gnn_model import GraphSAGE
from gnn.adapters.amlsim_adapter import load_amlsim


# ---------- 通用工具 ----------
def pairwise_f1(pred, gt):
    pred = np.asarray(pred)
    gt = np.asarray(gt)
    n = len(pred)
    same_pred = pred[:, None] == pred[None, :]
    same_gt = gt[:, None] == gt[None, :]
    tp = int(np.logical_and(same_pred, same_gt).sum()) - n
    fp = int(same_pred.sum()) - n - tp
    fn = int(same_gt.sum()) - n - tp
    prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0
    return f1, prec, rec


def evaluate(pred, gt):
    f1, prec, rec = pairwise_f1(pred, gt)
    return {
        "f1": f1,
        "precision": prec,
        "recall": rec,
        "nmi": normalized_mutual_info_score(gt, pred),
        "ari": adjusted_rand_score(gt, pred),
    }


def louvain_pred(G_nx, node_ids):
    try:
        from networkx.algorithms.community import louvain_communities

        comms = louvain_communities(G_nx, weight=None)
        pred = np.zeros(len(node_ids), dtype=int)
        for ci, c in enumerate(comms):
            for a in c:
                pred[node_ids.index(a)] = ci
        return pred
    except Exception as e:  # pragma: no cover
        print(f"  Louvain skipped: {e}")
        return None


class GNNClassifier(nn.Module):
    def __init__(self, sage, n_classes, hid=64):
        super().__init__()
        self.sage = sage
        self.head = nn.Sequential(
            nn.Linear(sage.layers[-1].update.out_features, hid),
            nn.ReLU(),
            nn.Linear(hid, n_classes),
        )

    def forward(self, x, adj):
        return self.head(self.sage(x, adj))


# ---------- (1) 合成：每环独立金额签名 ----------
def gen_distinct(
    n_background=1200,
    n_rings=20,
    ring_size=6,
    p_bg=0.0006,
    seed=42,
    global_mu=50000.0,
    amount_spread=40000.0,   # 每环 mu 的离散度 → 金额成为可区分信号
    bg_mu=2000.0,
    bg_sigma=1500.0,
    cross_talk=0.25,
):
    """生成每环带独立金额签名的合成账户交易数据。"""
    rng = np.random.default_rng(seed)
    ring_mus = rng.normal(global_mu, amount_spread, size=n_rings)
    n_total = n_background + n_rings * ring_size
    accounts = [f"A{i:05d}" for i in range(n_total)]
    gt = {a: -1 for a in accounts[:n_background]}
    txs = []
    base = 1_700_000_000.0
    ring_nodes = accounts[n_background:]

    for r in range(n_rings):
        members = ring_nodes[r * ring_size : (r + 1) * ring_size]
        mu_r = ring_mus[r]
        for m in members:
            gt[m] = r
        # 主循环（有向环，金额~该环专属 mu）
        for k in range(ring_size):
            src = members[k]
            dst = members[(k + 1) % ring_size]
            amt = max(float(rng.normal(mu_r, 3000.0)), 1.0)
            txs.append({"from_account": src, "to_account": dst,
                        "amount": amt, "timestamp": base + k * 3600.0})
        # 环内额外互转（结构密度）
        for _ in range(max(1, ring_size // 2)):
            a = members[int(rng.integers(ring_size))]
            b = members[int(rng.integers(ring_size))]
            if a != b:
                txs.append({"from_account": a, "to_account": b,
                            "amount": max(float(rng.normal(mu_r, 3000.0)), 1.0),
                            "timestamp": base + float(rng.uniform(0, 86400))})

    bg = accounts[:n_background]
    for _ in range(int(n_background * n_background * p_bg)):
        src = bg[int(rng.integers(n_background))]
        dst = bg[int(rng.integers(n_background))]
        if src == dst:
            continue
        txs.append({"from_account": src, "to_account": dst,
                    "amount": max(float(rng.normal(bg_mu, bg_sigma)), 1.0),
                    "timestamp": base + float(rng.uniform(0, 30 * 86400))})

    # 跨谈：环节点与背景少量交易（噪声）
    for r in range(n_rings):
        members = ring_nodes[r * ring_size : (r + 1) * ring_size]
        for m in members:
            if rng.random() < cross_talk:
                dst = bg[int(rng.integers(n_background))]
                txs.append({"from_account": m, "to_account": dst,
                            "amount": max(float(rng.normal(bg_mu, bg_sigma)), 1.0),
                            "timestamp": base + float(rng.uniform(0, 30 * 86400))})

    rng.shuffle(txs)
    return txs, gt


def run_synthetic(cross_talk, seed=42):
    # 固定 GNN 权重初始化与训练随机性（数据已由 gen_distinct 内部 default_rng(seed) 固定）。
    torch.manual_seed(seed)
    np.random.seed(seed)
    random.seed(seed)
    txs, gt = gen_distinct(cross_talk=cross_talk, seed=seed)
    g = build_account_graph(txs)
    node_ids = g["node_ids"]
    adj = g["adj"]
    feats = g["features"]
    N = len(node_ids)
    gt_arr = np.array([gt[a] for a in node_ids], dtype=int)
    n_rings = len(set(v for v in gt.values() if v >= 0))

    feats_t = torch.tensor(feats, dtype=torch.float32)
    adj_t = torch.tensor(adj, dtype=torch.float32)

    # 嫌疑子图：环节点 + 其 1 跳邻居（模拟"锚点扩线"检索到的范围）
    ring_idx = [i for i, v in enumerate(gt_arr) if v >= 0]
    nb = set(ring_idx)
    for i in ring_idx:
        a = node_ids[i]
        for nb_acct in list(g["G"].successors(a)) + list(g["G"].predecessors(a)):
            nb.add(node_ids.index(nb_acct))
    sub = np.array(sorted(nb))
    gt_sub = gt_arr[sub]
    feats_sub = feats[sub]
    feats_sub_t = torch.tensor(feats_sub, dtype=torch.float32)
    # 子图邻接
    sub_idx = {int(j): k for k, j in enumerate(sub)}
    adj_sub = np.zeros((len(sub), len(sub)), dtype=np.float32)
    for i in range(len(sub)):
        a = node_ids[sub[i]]
        for nb_acct in list(g["G"].successors(a)) + list(g["G"].predecessors(a)):
            if nb_acct in sub_idx:
                adj_sub[i, sub_idx[nb_acct]] = 1.0
    sym = (adj_sub + adj_sub.T) > 0
    adj_sub = sym.astype(np.float32)
    adj_sub_t = torch.tensor(adj_sub, dtype=torch.float32)

    n_clusters = n_rings + 1
    res = {}

    # 原始特征 + KMeans
    km = KMeans(n_clusters=n_clusters, random_state=0, n_init=10).fit(feats_sub)
    res["raw+KMeans"] = evaluate(km.labels_, gt_sub)

    # 未训练 GNN
    sage_b = GraphSAGE(in_dim=feats.shape[1], hidden_dim=64, out_dim=32, num_layers=2)
    with torch.no_grad():
        emb_b = sage_b.get_embeddings(feats_sub_t, adj_sub_t)
    km_b = KMeans(n_clusters=n_clusters, random_state=0, n_init=10).fit(emb_b)
    res["untrained_GNN+KMeans"] = evaluate(km_b.labels_, gt_sub)

    # 训练后 GNN
    sage_c = GraphSAGE(in_dim=feats.shape[1], hidden_dim=64, out_dim=32, num_layers=2)
    labels = torch.full((len(sub),), -1, dtype=torch.long)
    for k, j in enumerate(sub):
        if gt_arr[j] >= 0:
            labels[k] = gt_arr[j]
    mask = labels >= 0
    model = GNNClassifier(sage_c, n_classes=n_rings + 1)
    opt = torch.optim.Adam(model.parameters(), lr=1e-3)
    for _ in range(80):
        opt.zero_grad()
        logits = model(feats_sub_t, adj_sub_t)
        loss = F.cross_entropy(logits[mask], labels[mask])
        loss.backward()
        opt.step()
    with torch.no_grad():
        emb_c = sage_c.get_embeddings(feats_sub_t, adj_sub_t)
    km_c = KMeans(n_clusters=n_clusters, random_state=0, n_init=10).fit(emb_c)
    res["trained_GNN+KMeans"] = evaluate(km_c.labels_, gt_sub)

    # Louvain（纯拓扑，子图）
    Gs = g["G"].to_undirected().subgraph([node_ids[j] for j in sub])
    lp = louvain_pred(Gs, [node_ids[j] for j in sub])
    if lp is not None:
        res["Louvain(topology)"] = evaluate(lp, gt_sub)

    summary = {k: round(v["f1"], 4) for k, v in res.items()}
    print(f"[synthetic cross_talk={cross_talk}] ring_subgraph F1: {summary}")
    return {"n_accounts": N, "n_subgraph": len(sub), "n_rings": n_rings,
            "cross_talk": cross_talk, "results": res}


# ---------- (2) AMLSim 大规模锚点 refinement ----------
def run_amlsim_refinement(directory, max_rings=60, k_hop=2, max_nodes=8000, seed=42):
    print(f"[amlsim] loading {directory} ...")
    account_ids, edges, gt = load_amlsim(directory)
    ring_accounts = [a for a, l in gt.items() if l >= 0]
    if not ring_accounts:
        return {"error": "no ring ground truth found (no ground_truth/alerts)"}

    # 邻接（无向）用于 k 跳 BFS
    adj = {}
    for s, d, _, _ in edges:
        adj.setdefault(s, []).append(d)
        adj.setdefault(d, []).append(s)

    # 选锚点：按环分组，每环取首个账户，最多 max_rings 环
    ring_of = {}
    for a in ring_accounts:
        ring_of.setdefault(gt[a], []).append(a)
    chosen_rings = list(ring_of.keys())[:max_rings]
    anchors = [ring_of[r][0] for r in chosen_rings]

    # k 跳 BFS，限制子图规模
    seen = set()
    frontier = list(anchors)
    for _ in range(k_hop):
        nxt = []
        for a in frontier:
            for nb in adj.get(a, []):
                if nb not in seen:
                    seen.add(nb)
                    nxt.append(nb)
                    if len(seen) >= max_nodes:
                        break
            if len(seen) >= max_nodes:
                break
        frontier = nxt
        if len(seen) >= max_nodes:
            break
    sub_accounts = list(seen)
    print(f"[amlsim] subgraph nodes={len(sub_accounts)} (anchors={len(anchors)}, k={k_hop})")

    # 子图交易
    sub_set = set(sub_accounts)
    sub_txs = [
        {"from_account": s, "to_account": d, "amount": amt, "timestamp": ts}
        for (s, d, amt, ts) in edges
        if s in sub_set and d in sub_set
    ]
    sub_gt = {a: gt.get(a, -1) for a in sub_accounts}

    # 把真实 RING_ID（稀疏、可能很大，如 549/2553）重映射为紧凑 0..K-1，
    # 否则分类头按 n_classes=distinct+1 建，cross_entropy 会因标签越界崩溃。
    present_rings = sorted({v for v in sub_gt.values() if v >= 0})
    if not present_rings:
        return {"error": "子图内无环真值（锚点未覆盖到洗钱环），无法评测"}
    ring2c = {r: i for i, r in enumerate(present_rings)}
    n_rings_sub = len(present_rings)

    g = build_account_graph(sub_txs)
    node_ids = g["node_ids"]
    feats = g["features"]
    gt_arr = np.array([sub_gt[a] for a in node_ids], dtype=int)

    feats_t = torch.tensor(feats, dtype=torch.float32)
    adj_t = torch.tensor(g["adj"], dtype=torch.float32)

    res = {}
    km = KMeans(n_clusters=n_rings_sub + 1, random_state=0, n_init=10).fit(feats)
    res["raw+KMeans"] = evaluate(km.labels_, gt_arr)

    sage_c = GraphSAGE(in_dim=feats.shape[1], hidden_dim=64, out_dim=32, num_layers=2)
    labels = torch.full((len(node_ids),), -1, dtype=torch.long)
    for i, a in enumerate(node_ids):
        if sub_gt[a] >= 0:
            labels[i] = ring2c[sub_gt[a]]
    mask = labels >= 0
    model = GNNClassifier(sage_c, n_classes=n_rings_sub + 1)
    opt = torch.optim.Adam(model.parameters(), lr=1e-3)
    for _ in range(80):
        opt.zero_grad()
        logits = model(feats_t, adj_t)
        loss = F.cross_entropy(logits[mask], labels[mask])
        loss.backward()
        opt.step()
    with torch.no_grad():
        emb_c = sage_c.get_embeddings(feats_t, adj_t)
    km_c = KMeans(n_clusters=n_rings_sub + 1, random_state=0, n_init=10).fit(emb_c)
    res["trained_GNN+KMeans"] = evaluate(km_c.labels_, gt_arr)

    Gs = g["G"].to_undirected()
    lp = louvain_pred(Gs, node_ids)
    if lp is not None:
        res["Louvain(topology)"] = evaluate(lp, gt_arr)

    summary = {k: round(v["f1"], 4) for k, v in res.items()}
    print(f"[amlsim refinement] F1: {summary}  (盲扫基线≈0.002, docs/04 §七)")
    return {
        "directory": directory,
        "n_subgraph": len(node_ids),
        "n_rings_sub": n_rings_sub,
        "k_hop": k_hop,
        "blind_baseline_f1": 0.002,
        "results": res,
    }


def run_amlsim_refinement_focused(directory, n_rings=60, k_hop=1, max_nodes=6000, seed=42):
    """聚焦子图变体（解释 0.784/0.822 的来源，仅供诚实对照）：直接取选定环的'成员本身'
    作为并案范围，再加 k 跳邻居。此设定下环是清晰连通分量，F1 偏高，但属于退化评测
    （已知团伙成员而非仅凭锚点扩线），不构成真实扩线验证。"""
    from collections import defaultdict as _dd

    print(f"[amlsim-focused] loading {directory} ...")
    account_ids, edges, gt = load_amlsim(directory)

    ring_members = _dd(list)
    for a, l in gt.items():
        if l >= 0:
            ring_members[l].append(a)
    chosen = list(ring_members.keys())[:n_rings]

    adj = _dd(list)
    for s, d, _, _ in edges:
        adj[s].append(d)
        adj[d].append(s)

    # 子图 = 选定环所有成员 + k 跳邻居
    sub = set()
    for r in chosen:
        for a in ring_members[r]:
            sub.add(a)
    frontier = list(sub)
    for _ in range(k_hop):
        nxt = []
        for a in frontier:
            for nb in adj.get(a, []):
                if nb not in sub:
                    sub.add(nb)
                    nxt.append(nb)
                    if len(sub) >= max_nodes:
                        break
            if len(sub) >= max_nodes:
                break
        frontier = nxt
        if len(sub) >= max_nodes:
            break

    sub_accounts = list(sub)
    sub_set = set(sub_accounts)
    sub_txs = [
        {"from_account": s, "to_account": d, "amount": amt, "timestamp": ts}
        for (s, d, amt, ts) in edges
        if s in sub_set and d in sub_set
    ]
    sub_gt = {a: gt.get(a, -1) for a in sub_accounts}

    present_rings = sorted({v for v in sub_gt.values() if v >= 0})
    if not present_rings:
        return {"error": "聚焦子图内无环真值"}
    ring2c = {r: i for i, r in enumerate(present_rings)}
    n_rings_sub = len(present_rings)

    g = build_account_graph(sub_txs)
    node_ids = g["node_ids"]
    feats = g["features"]
    gt_arr = np.array([sub_gt[a] for a in node_ids], dtype=int)

    feats_t = torch.tensor(feats, dtype=torch.float32)
    adj_t = torch.tensor(g["adj"], dtype=torch.float32)

    res = {}
    km = KMeans(n_clusters=n_rings_sub + 1, random_state=0, n_init=10).fit(feats)
    res["raw+KMeans"] = evaluate(km.labels_, gt_arr)

    sage_c = GraphSAGE(in_dim=feats.shape[1], hidden_dim=64, out_dim=32, num_layers=2)
    torch.manual_seed(seed)
    np.random.seed(seed)
    random.seed(seed)
    labels = torch.full((len(node_ids),), -1, dtype=torch.long)
    for i, a in enumerate(node_ids):
        if sub_gt[a] >= 0:
            labels[i] = ring2c[sub_gt[a]]
    mask = labels >= 0
    model = GNNClassifier(sage_c, n_classes=n_rings_sub + 1)
    opt = torch.optim.Adam(model.parameters(), lr=1e-3)
    for _ in range(80):
        opt.zero_grad()
        logits = model(feats_t, adj_t)
        loss = F.cross_entropy(logits[mask], labels[mask])
        loss.backward()
        opt.step()
    with torch.no_grad():
        emb_c = sage_c.get_embeddings(feats_t, adj_t)
    km_c = KMeans(n_clusters=n_rings_sub + 1, random_state=0, n_init=10).fit(emb_c)
    res["trained_GNN+KMeans"] = evaluate(km_c.labels_, gt_arr)

    Gs = g["G"].to_undirected()
    lp = louvain_pred(Gs, node_ids)
    if lp is not None:
        res["Louvain(topology)"] = evaluate(lp, gt_arr)

    summary = {k: round(v["f1"], 4) for k, v in res.items()}
    print(f"[amlsim-focused] F1: {summary}  (n_subgraph={len(node_ids)}, n_rings={n_rings_sub})")
    return {
        "directory": directory,
        "variant": "focused(ring_members+k_hop)",
        "n_subgraph": len(node_ids),
        "n_rings_sub": n_rings_sub,
        "k_hop": k_hop,
        "blind_baseline_f1": 0.002,
        "results": res,
    }


def main():
    out = {"honest_note": (
        "Refinement（扩线）实验：验证 GNN 在'给定锚点→嫌疑子图并案'实战设定下的价值。"
        "合成数据证明训练后 GNN 可用；AMLSim 真实数据仅作外部难度基线，不称真实验证。")}

    # (1) 合成噪声扫描
    sweep = []
    for ct in (0.25, 0.5, 0.75):
        sweep.append(run_synthetic(cross_talk=ct, seed=42))
    out["synthetic_sweep"] = sweep

    # (2) AMLSim 大规模 refinement（诚实外部验证）
    amlsim_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "amlsim_real")
    if os.path.isdir(amlsim_dir):
        try:
            out["amlsim_refinement"] = run_amlsim_refinement(amlsim_dir)
        except Exception as e:
            out["amlsim_refinement"] = {"error": str(e)}
    else:
        out["amlsim_refinement"] = {"error": f"directory not found: {amlsim_dir}"}

    print("\n=== JSON ===")
    print(json.dumps(out, ensure_ascii=False, indent=2))

    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "refinement_results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"[saved] {out_path}")


def main_seeded(seeds=(42, 0, 1, 2, 3), cross_talks=(0.25, 0.75)):
    """多 seed 复现合成 refinement 数字（论文 tab:refinement 合成列），报告均值±std。

    AMLSim 真实样本列（0.784/0.822）属外部验证，其加载路径此前报错，单独在 #C50 处理，
    此处仅复现纯合成部分，避免引入未经验证的真实数据声明。
    """
    out = {}
    for ct in cross_talks:
        method_f1 = {}
        for sd in seeds:
            r = run_synthetic(cross_talk=ct, seed=sd)
            for m, v in r["results"].items():
                method_f1.setdefault(m, []).append(v["f1"])
        agg = {}
        for m, vals in method_f1.items():
            agg[m] = {
                "mean": round(float(np.mean(vals)), 4),
                "std": round(float(np.std(vals)), 4),
                "vals": [round(x, 4) for x in vals],
            }
        out[f"ct={ct}"] = agg
        print(f"[seeded {ct}] {agg}")
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "refinement_seeded_results.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(
            {"honest_note": "合成 refinement 多 seed 复现，对应论文 tab:refinement 合成列。",
             "seeds": list(seeds), "cross_talks": list(cross_talks), "results": out},
            f, ensure_ascii=False, indent=2,
        )
    print(f"\n[saved] {path}")


def main_amlsim():
    """#C50：用 canonical/ 数据独立复现 AMLSim 真实样本扩线 F1（诚实外部验证）。"""
    here = os.path.dirname(os.path.abspath(__file__))
    d = os.path.join(here, "amlsim_real", "canonical")
    print(f"[C50] AMLSim refinement on canonical dir: {d}")
    # 默认扩散设定（锚点 2 跳 BFS，子图易爆炸为伪全图）
    res_spread = run_amlsim_refinement(d)
    # 聚焦设定（环成员本身 + 1 跳，解释 0.784/0.822 退化来源）
    res_focused = run_amlsim_refinement_focused(d)
    out = {
        "honest_note": (
            "AMLSim 大规模账户中心为 IBM 公开合成基准，非真实警务数据；本结果仅作外部难度基线，"
            "不构成'真实警务数据验证通过'。结果随锚点/子图选取参数剧烈变化：默认扩散设定下落回近盲扫量级，"
            "聚焦退化设定（已知环成员）可达高 F1 但属退化评测。"),
        "amlsim_refinement_spread(2hop_to_8000)": res_spread,
        "amlsim_refinement_focused(ring_members+1hop)": res_focused,
    }
    path = os.path.join(here, "amlsim_refinement_results.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"[saved] {path}")
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    import sys

    if "--seeded" in sys.argv:
        main_seeded()
    elif "--amlsim" in sys.argv:
        main_amlsim()
    else:
        main()
