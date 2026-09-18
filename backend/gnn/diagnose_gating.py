"""共识锚点门控诊断：看清 min_size / max_size 门控在纯度和覆盖率间的真实权衡。

只用于理解机制，不进入方法参数（方法只用数据自身统计量，GT 仅诊断用）。
对每个预设输出：
  - fund 社区数、script 轮廓 k、共识簇大小分布
  - min_size=2 时锚点覆盖率 + GT 纯度（按簇多数票加权）
  - 被弃单例簇数、以及"单例案与其 fund 社区多数成员是否同 GT"（放宽 min_size=1 的安全性）
  - 巨簇(>25%)弃用数
  - min_size=1 时覆盖率 + GT 纯度（放宽的净效果）

用法: python diagnose_gating.py [p0,p1,p2,p3]
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


def _script_labels(cases):
    import torch
    from transformers import AutoTokenizer, AutoModel
    from sklearn.preprocessing import StandardScaler
    from sklearn.cluster import KMeans
    model_path = os.path.join(os.path.dirname(HERE), "bge-large-zh-v1.5")
    scripts = ef.case_scripts(cases)
    tok = AutoTokenizer.from_pretrained(model_path)
    md = AutoModel.from_pretrained(model_path)
    enc = tok(scripts, padding=True, truncation=True, max_length=128, return_tensors="pt")
    with torch.no_grad():
        emb = md(**enc).last_hidden_state[:, 0, :].numpy()
    emb_s = StandardScaler().fit_transform(emb.astype(np.float32))
    k = ef._estimate_n_clusters(emb_s)
    sc = KMeans(n_clusters=k, random_state=0, n_init=10).fit_predict(emb_s)
    return {c["case_id"]: int(l) for c, l in zip(cases, sc)}, k, emb


def _purity_of_clusters(clusters, gt):
    """簇列表的 GT 纯度：每簇多数票占比，按簇大小加权。"""
    if not clusters:
        return 0.0, 0
    tot = 0
    ok = 0
    n_impure = 0
    for mem in clusters:
        votes = Counter(gt[c] for c in mem if c in gt)
        if not votes:
            continue
        maj = votes.most_common(1)[0][1]
        tot += len(mem)
        ok += maj
        if maj < len(mem):
            n_impure += 1
    return (ok / tot if tot else 0.0), n_impure


def diagnose(preset_name: str, kwargs: dict):
    cases, tx, gt = ef.sd_mod.generate_synthetic_dataset(seed=42, **kwargs)
    ids = [c["case_id"] for c in cases]
    n_true = len(set(gt.values()))
    print(f"\n===== {preset_name} ({kwargs})  n={len(cases)}  n_true={n_true} =====")

    builder = ef.gb_mod.FraudGraphBuilder(use_db=False, use_cache=False, use_text_channel=False)
    G = builder.build_graph(cases, accounts_tx=tx)
    fund = ef._louvain_case_labels(G)
    script, k_script, emb = _script_labels(cases)
    n_fund = len(set(fund.values()))
    print(f"fund 社区数={n_fund}  script 轮廓 k={k_script}")

    # 共识簇
    by_pair: dict = {}
    for cid in ids:
        if cid not in fund:
            continue
        by_pair.setdefault((fund[cid], script[cid]), []).append(cid)
    sizes = sorted(len(v) for v in by_pair.values())
    print("共识簇大小分布:", sizes)

    max_size = int(len(cases) * 0.25)
    singles = [m for m in by_pair.values() if len(m) == 1]
    big = [m for m in by_pair.values() if len(m) > max_size]
    kept2 = [m for m in by_pair.values() if 2 <= len(m) <= max_size]
    kept1 = [m for m in by_pair.values() if 1 <= len(m) <= max_size]
    cov2 = sum(len(m) for m in kept2) / len(cases)
    cov1 = sum(len(m) for m in kept1) / len(cases)
    pur2, impure2 = _purity_of_clusters(kept2, gt)
    pur1, impure1 = _purity_of_clusters(kept1, gt)
    print(f"max_size(25%)={max_size}  巨簇弃用={len(big)}  单例簇数={len(singles)}")
    print(f"[min_size=2] 锚点簇={len(kept2)}  覆盖率={cov2:.3f}  GT纯度={pur2:.3f}  不纯簇={impure2}")
    print(f"[min_size=1] 锚点簇={len(kept1)}  覆盖率={cov1:.3f}  GT纯度={pur1:.3f}  不纯簇={impure1}")

    # 单例案安全性：单例案与其 fund 社区多数成员是否同 GT？
    fund_members: dict = {}
    for cid, c in fund.items():
        fund_members.setdefault(c, []).append(cid)
    single_correct = 0
    single_total = 0
    for m in singles:
        cid = m[0]
        fc = fund[cid]
        others = [x for x in fund_members[fc] if x != cid]
        if not others:
            continue
        votes = Counter(gt[x] for x in others if x in gt)
        if not votes:
            continue
        single_total += 1
        if votes.most_common(1)[0][0] == gt.get(cid):
            single_correct += 1
    print(f"单例案与其 fund 社区多数同 GT: {single_correct}/{single_total}"
          + (f" = {single_correct/single_total:.3f}" if single_total else ""))

    # fund 社区纯净度（GT 口径）：fund 社区是否跨 GT 团伙
    fund_impure = 0
    for _, mem in fund_members.items():
        gts = set(gt[c] for c in mem if c in gt)
        if len(gts) > 1:
            fund_impure += 1
    print(f"fund 社区跨 GT 团伙数: {fund_impure}/{n_fund}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("presets", default="p0,p1,p2,p3", nargs="?",
                    help="逗号分隔: p0/p1/p2/p3/p4/p5")
    args = ap.parse_args()
    req = [x.strip().lower() for x in args.presets.split(",") if x.strip()]
    for p in PRESETS:
        tag = p["name"].split("_")[0].lower()
        if tag in req:
            diagnose(p["name"], p["kwargs"])


if __name__ == "__main__":
    main()
