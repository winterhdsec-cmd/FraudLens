"""社区级过滤快速实验：kcore2 内 Louvain 社区按规则分均值排序取 top-k"""
import sys, os, time
from collections import defaultdict
import numpy as np
import networkx as nx
sys.path.insert(0, r"E:\FraudLens\backend")
sys.path.insert(0, r"E:\FraudLens\backend\gnn")
from networkx.algorithms.community import louvain_communities
from gnn.account_temporal import build_account_graph
from gnn.adapters.amlsim_adapter import load_amlsim

BACKEND = r"E:\FraudLens\backend\gnn"
DATA_DIR = os.path.join(BACKEND, "amlsim_real", "canonical")
t0 = time.time()
account_ids, edges, gt = load_amlsim(DATA_DIR)

N_A, K_H, MAX_N = 120, 1, 8000
ring_accounts = [a for a, l in gt.items() if l >= 0]
adj = defaultdict(list)
for s, d, _, _ in edges:
    adj[s].append(d)
    adj[d].append(s)
ring_of = defaultdict(list)
for a in ring_accounts:
    ring_of[gt[a]].append(a)
anchors = [ring_of[r][0] for r in list(ring_of.keys())[:N_A]]
seen, frontier = set(), list(anchors)
for _ in range(K_H):
    nxt = []
    for a in frontier:
        for nb in adj.get(a, []):
            if nb not in seen:
                seen.add(nb)
                nxt.append(nb)
                if len(seen) >= MAX_N:
                    break
        if len(seen) >= MAX_N:
            break
    frontier = nxt
    if len(seen) >= MAX_N:
        break
sub = list(seen)
sub_set = set(sub)
sub_txs = [{"from_account": s, "to_account": d, "amount": amt, "timestamp": ts}
           for (s, d, amt, ts) in edges if s in sub_set and d in sub_set]
sub_gt = {a: gt.get(a, -1) for a in sub}

g = build_account_graph(sub_txs)
node_ids = g["node_ids"]
G_dir = g["G"]
G_und = G_dir.to_undirected()
G_und.remove_edges_from(nx.selfloop_edges(G_und))
gt_arr = np.array([sub_gt[a] for a in node_ids], dtype=int)
gt_members = set(node_ids[i] for i in range(len(node_ids)) if gt_arr[i] >= 0)


def rule_scores(sub_txs, accounts):
    in_amt, out_amt = defaultdict(list), defaultdict(list)
    in_ts, out_ts = defaultdict(list), defaultdict(list)
    for tx in sub_txs:
        s, d = tx["from_account"], tx["to_account"]
        amt, ts = tx.get("amount"), tx.get("timestamp")
        out_amt[s].append(float(amt))
        in_amt[d].append(float(amt))
        if ts is not None:
            out_ts[s].append(float(ts))
            in_ts[d].append(float(ts))
    sc = {}
    for a in accounts:
        v = 0.0
        ins, outs = in_amt.get(a, []), out_amt.get(a, [])
        if ins and outs and in_ts and out_ts:
            it, ot = sorted(in_ts.get(a, [])), sorted(out_ts.get(a, []))
            fast = 0
            for ti in it:
                for to in ot:
                    if 0 <= (to - ti) <= 1.0:
                        fast += 1
                        break
            v += 0.5 * min(fast / max(len(it), 1) * 2.0, 1.0)
        if ins:
            med = float(np.median(ins))
            if med > 0:
                big = sum(1 for x in ins if x >= med * 5)
                v += 0.5 * min(big / max(len(ins), 1) * 2.0, 1.0)
        sc[a] = v
    return sc


scores = rule_scores(sub_txs, node_ids)

core = nx.core_number(G_und)
core_set = {a for a in node_ids if core.get(a, 0) >= 2}
Gc = G_und.subgraph(sorted(core_set)).copy()
comms = louvain_communities(Gc, weight=None)
comms = [c for c in comms if len(c) >= 3]
gang_scores = [(c, float(np.mean([scores[a] for a in c])), len(c)) for c in comms]
gang_scores.sort(key=lambda x: -x[1])
print("kcore2 内社区数:", len(comms))


def node_prf(pred, gt):
    pred, gt = set(pred), set(gt)
    tp = len(pred & gt)
    prec = tp / len(pred) if pred else 0.0
    rec = tp / max(len(gt), 1)
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0
    return round(prec, 4), round(rec, 4), round(f1, 4)


print("=== 社区级 top-k（规则分均值）===")
for frac in [0.2, 0.35, 0.5, 0.7]:
    kc = max(int(len(gang_scores) * frac), 1)
    pred = set()
    for c, s_mean, sz in gang_scores[:kc]:
        pred |= set(c)
    p, r, f = node_prf(pred, gt_members)
    print(f"  top{frac:.0%} 社区: n={len(pred)} P={p} R={r} F1={f}")

p, r, f = node_prf(core_set, gt_members)
print(f"  [ctrl] 全 kcore2 核心: P={p} R={r} F1={f}")
print(f"  ({time.time()-t0:.0f}s)")
