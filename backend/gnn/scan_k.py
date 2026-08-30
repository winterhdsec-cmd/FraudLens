"""k 扫描诊断：看 script 聚类 k 取多少时共识锚点最优，哪个内部指标能选出来。

诊断校准用 GT 判断"最优 k"（覆盖率×纯度的最好折衷），再对比各内部指标
（silhouette / davies_bouldin / calinski_harabasz / 与 fund_n 对齐）在最优 k
附近的表现。方法实现最终只用内部指标，本脚本仅用于选择指标。

用法: python scan_k.py p1,p4
"""
import argparse
import os
import sys
from collections import Counter

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import numpy as np  # noqa: E402
import eval_framework as ef  # noqa: E402
from experiment_semi import PRESETS  # noqa: E402
from sklearn.cluster import KMeans  # noqa: E402
from sklearn.preprocessing import StandardScaler  # noqa: E402
from sklearn.metrics import (silhouette_score, davies_bouldin_score,  # noqa: E402
                             calinski_harabasz_score)


def _bge_emb(cases):
    import torch
    from transformers import AutoTokenizer, AutoModel
    model_path = os.path.join(os.path.dirname(HERE), "bge-large-zh-v1.5")
    scripts = ef.case_scripts(cases)
    tok = AutoTokenizer.from_pretrained(model_path)
    md = AutoModel.from_pretrained(model_path)
    enc = tok(scripts, padding=True, truncation=True, max_length=128, return_tensors="pt")
    with torch.no_grad():
        return md(**enc).last_hidden_state[:, 0, :].numpy()


def _consensus_for_k(fund, ids, sc):
    sc_map = {cid: int(l) for cid, l in zip(ids, sc)}
    by_pair = {}
    for cid in ids:
        if cid not in fund:
            continue
        by_pair.setdefault((fund[cid], sc_map[cid]), []).append(cid)
    return by_pair


def _cov_pur(by_pair, gt, n, max_size):
    kept = [m for m in by_pair.values() if 2 <= len(m) <= max_size]
    cov = sum(len(m) for m in kept) / n
    tot = ok = 0
    impure = 0
    for m in kept:
        votes = Counter(gt[c] for c in m if c in gt)
        if not votes:
            continue
        maj = votes.most_common(1)[0][1]
        tot += len(m); ok += maj
        if maj < len(m):
            impure += 1
    return cov, (ok / tot if tot else 0.0), impure, len(kept)


def scan(preset_name: str, kwargs: dict):
    cases, tx, gt = ef.sd_mod.generate_synthetic_dataset(seed=42, **kwargs)
    ids = [c["case_id"] for c in cases]
    n = len(cases)
    n_true = len(set(gt.values()))
    max_size = int(n * 0.25)
    print(f"\n===== {preset_name}  n={n}  n_true={n_true}  max_size={max_size} =====")

    builder = ef.gb_mod.FraudGraphBuilder(use_db=False, use_cache=False, use_text_channel=False)
    G = builder.build_graph(cases, accounts_tx=tx)
    fund = ef._louvain_case_labels(G)
    n_fund = len(set(fund.values()))
    print(f"fund 社区数={n_fund}")

    emb = _bge_emb(cases)
    emb_s = StandardScaler().fit_transform(emb.astype(np.float32))
    # 内部指标列：cov/pur 用 GT 评估哪个 k 最好（仅诊断）
    print(f"{'k':>3} {'sil':>7} {'db':>7} {'ch':>8} {'cov':>6} {'pur':>6} {'impure':>6} {'nclu':>5} {'bigdrop':>8}")
    rows = {}
    best = None
    for k in range(2, min(11, n // 2) + 1):
        sc = KMeans(n_clusters=k, random_state=0, n_init=10).fit_predict(emb_s)
        bp = _consensus_for_k(fund, ids, sc)
        cov, pur, impure, nclu = _cov_pur(bp, gt, n, max_size)
        big = [m for m in bp.values() if len(m) > max_size]
        bigdrop = sum(len(m) for m in big) / n
        sil = silhouette_score(emb_s, sc)
        db = davies_bouldin_score(emb_s, sc)
        ch = calinski_harabasz_score(emb_s, sc)
        rows[k] = (cov, pur, impure, nclu, bigdrop)
        print(f"{k:>3} {sil:>7.3f} {db:>7.3f} {ch:>8.0f} {cov:>6.3f} {pur:>6.3f} {impure:>6} {nclu:>5} {bigdrop:>8.3f}")
        score = cov * pur if pur > 0 else 0.0
        if best is None or score > best[1]:
            best = (k, score)
    print(f"=> 诊断最优 k={best[0]} (score={best[1]:.3f})")

    # 模拟启发式：默认 silhouette 峰 k_sil；若其共识巨簇弃用率>0，
    # 在 [k_sil+1..] 扫"无巨簇且共识簇数最多"的 k（无监督判据）
    sil_peak = max(range(2, min(11, n // 2) + 1),
                   key=lambda k: silhouette_score(emb_s, KMeans(n_clusters=k, random_state=0, n_init=10).fit_predict(emb_s)))
    def _nclu_unseen(k):
        sc = KMeans(n_clusters=k, random_state=0, n_init=10).fit_predict(emb_s)
        bp = _consensus_for_k(fund, ids, sc)
        return len(bp)
    k_heur = sil_peak
    if rows[sil_peak][4] > 0:  # 巨簇弃用率 > 0
        cands = [k for k in range(sil_peak + 1, min(11, n // 2) + 1)
                 if rows[k][4] == 0]
        if cands:
            k_heur = max(cands, key=lambda k: _nclu_unseen(k))
    h_cov, h_pur, h_imp, h_nclu, _ = rows[k_heur]
    print(f"=> 现有 silhouette 峰 k={sil_peak}")
    print(f"=> 启发式选中 k={k_heur}  覆盖={h_cov:.3f} 纯度={h_pur:.3f} 不纯簇={h_imp} nclu={h_nclu}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("presets", default="p0,p1,p2,p3,p4,p5", nargs="?")
    args = ap.parse_args()
    req = [x.strip().lower() for x in args.presets.split(",") if x.strip()]
    for p in PRESETS:
        if p["name"].split("_")[0].lower() in req:
            scan(p["name"], p["kwargs"])


if __name__ == "__main__":
    main()
