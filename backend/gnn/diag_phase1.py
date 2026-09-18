# -*- coding: utf-8 -*-
"""诊断 GangDetector 在已知库规模为何产出单团（phase1_gangs=1 根因）。"""
import os, sys, json
sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.dirname(HERE)
sys.path.insert(0, HERE); sys.path.insert(0, BACKEND)

import synthetic_data as sd
from collections import defaultdict
from gnn.gang_detector import GangDetector

kwargs = dict(n_gangs=5, cases_per_gang=8,
              cross_gang_account_share=0.15, intra_share_prob=0.75, attr_noise=0.25)
cases, _tx, gt = sd.generate_synthetic_dataset(**kwargs)
by_gang = defaultdict(list)
for c in cases:
    by_gang[gt[c["case_id"]]].append(c)
library, stream = [], []
for g, members in by_gang.items():
    library.extend(members[:4]); stream.extend(members[4:])
print("library:", len(library), "stream:", len(stream))

for use_dc in (True, False):
    det = GangDetector(community_method="louvain" if not use_dc else "louvain",
                       use_deep_clustering=use_dc)
    r = det.detect(library, use_gnn=True, training_epochs=50)
    gangs = r.get("gangs", []) or []
    print(f"\nuse_deep_clustering={use_dc}: gangs={len(gangs)}, stats={r.get('stats')}")
    for g in gangs[:8]:
        print(f"   {g.get('gang_id')}: cases={len(g.get('case_ids', []))}, name={g.get('gang_name')}")
    # 统计每个检测团伙的真值多数
    for g in gangs[:8]:
        cids = g.get("case_ids", [])
        gts = [gt[c] for c in cids if c in gt]
        from collections import Counter
        print(f"     真值分布: {dict(Counter(gts))}")
