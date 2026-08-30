# -*- coding: utf-8 -*-
"""增量匹配器快速冒烟：真值分组建画像 → 流式匹配新案，验证门控正确性（不跑 GNN）。"""
import os, sys, json
sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import synthetic_data as sd
from incremental_matcher import build_gang_profiles, match_cases_batch

kwargs = dict(n_gangs=5, cases_per_gang=8,
              cross_gang_account_share=0.15, intra_share_prob=0.75, attr_noise=0.25)
cases, _tx, gt = sd.generate_synthetic_dataset(**kwargs)

# 真值分组 → 已知画像（仅验证匹配器，非最终验证流程）
from collections import defaultdict
by_gang = defaultdict(list)
for c in cases:
    by_gang[gt[c["case_id"]]].append(c)

gangs_members = {}
stream = []
for g, members in by_gang.items():
    n_lib = 4
    gangs_members[f"G{g}"] = members[:n_lib]
    stream.extend(members[n_lib:])

profiles = build_gang_profiles(gangs_members)
print("画像数:", len(profiles))
for gid, p in profiles.items():
    print(f"  {gid}: n={p.n_members}, accounts={sorted(p.account_pool)[:4]}..., centroid={'有' if p.script_centroid is not None else '无'}")

matches = match_cases_batch(profiles, stream)
print("\n新案:", len(stream), " 匹配:", len(matches), " 挂不上:", len(stream) - len(matches))

# 匹配正确性：挂到的画像是否为真值同团伙
correct = 0
wrong = 0
for cid, m in matches.items():
    gid = m["gang_id"]
    true_g = gt[cid]
    members_true = {gt[x["case_id"]] for x in gangs_members[gid]}
    ok = true_g in members_true
    correct += ok
    wrong += (not ok)
    print(f"  {cid} true=G{true_g} -> {gid} members_true={members_true} sim={m['score']:.3f} acc={m['matched_accounts']} {'OK' if ok else 'WRONG'}")

print(f"\n匹配精度: {correct}/{correct+wrong} = {correct/(correct+wrong):.2f}")
held = [c["case_id"] for c in stream if c["case_id"] not in matches]
print("挂不上案例数:", len(held), held[:20])
