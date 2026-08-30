"""
增量团伙匹配验证：确认"先画像匹配、挂不上的攒批重聚类"相对全量重聚类效果不掉。

流程（诚实两阶段，避免用真值标签喂已知库造成假优势）：
  1. 生成合成数据 → 每团伙前一半 = 已知库 L，后一半 = 流式新案 S
  2. 阶段一：对 L 跑真实 GangDetector.detect → 得到**带误差**的"已有团伙"聚类
  3. 阶段二：把 S 按 chunk 流式喂入
       - 由当前已知团伙成员案件建画像（账户池 + 话术 BGE 质心）
       - 新案先匹配（资金共享 + 话术余弦，双信号一致才挂，复用共识门控哲学）
       - 挂不上的攒批(>=2)跑 GangDetector.detect → 新团伙
  4. 全量基线：对 L+S 直接 GangDetector.detect → pairwise F1
  5. 判定"效果不掉"：F1_incremental >= F1_full - 0.02（容忍噪声），且 matched 精度足够高

用法
----
    python verify_incremental.py                  # P2_hard + P3_200
    python verify_incremental.py --presets p2     # 快测
    python verify_incremental.py --chunks 2 --epochs 100
"""
import argparse
import json
import os
import sys
import time
from collections import defaultdict
from typing import Any, Dict, List

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)

import synthetic_data as sd  # noqa: E402
import eval_framework as ef  # noqa: E402
from incremental_matcher import (  # noqa: E402
    DEFAULT_TEXT_THRESHOLD,
    build_gang_profiles,
    match_cases_batch,
)

PRESETS: List[Dict[str, Any]] = [
    {"name": "P2_hard_40", "desc": "重噪 40 案（5 团伙×8）",
     "kwargs": dict(n_gangs=5, cases_per_gang=8,
                    cross_gang_account_share=0.15, intra_share_prob=0.75, attr_noise=0.25)},
    {"name": "P3_200", "desc": "轻噪 200 案（10 团伙×20）",
     "kwargs": dict(n_gangs=10, cases_per_gang=20,
                    cross_gang_account_share=0.05, intra_share_prob=0.9, attr_noise=0.1)},
]


def _split_library_stream(cases: List[Dict], gt: Dict[str, int], frac: float = 0.5):
    by_gang: Dict[int, List[Dict]] = defaultdict(list)
    for c in cases:
        by_gang[gt[c["case_id"]]].append(c)
    library, stream = [], []
    for _, members in by_gang.items():
        n_lib = max(2, int(len(members) * frac))
        library.extend(members[:n_lib])
        stream.extend(members[n_lib:])
    return library, stream


def _cluster_labels(gangs: List[Dict], all_ids: List[str]) -> Dict[str, int]:
    labels: Dict[str, int] = {}
    for gi, g in enumerate(gangs):
        for cid in g.get("case_ids", []):
            labels[cid] = gi
    # 未入团的孤立案件：各自成单例（诚实计入，不因漏标被排除在 F1 外）
    nxt = len(gangs)
    for cid in all_ids:
        if cid not in labels:
            labels[cid] = nxt
            nxt += 1
    return labels


def _make_detector(mode: str):
    from gnn.gang_detector import GangDetector
    if mode == "louvain":
        # 纯 Louvain（use_deep_clustering=False）：小规模可正确分团，
        # 用于验证"已知团伙合理分离时，增量匹配是否不掉精度"
        return GangDetector(community_method="louvain", use_deep_clustering=False)
    # production：与生产路由一致的默认（deep_clustering=True，community_method 参数被覆盖）
    return GangDetector(community_method="louvain")


def run_preset(name: str, kwargs: Dict[str, Any], chunks: int = 2,
               epochs: int = 100, text_threshold: float = DEFAULT_TEXT_THRESHOLD,
               detector_mode: str = "production") -> Dict[str, Any]:
    cases, _accounts_tx, gt = sd.generate_synthetic_dataset(**kwargs)
    library, stream = _split_library_stream(cases, gt, 0.5)
    case_by_id = {c["case_id"]: c for c in cases}

    # 阶段一：已知库检测（真实管线，带误差）
    t0 = time.time()
    det = _make_detector(detector_mode)
    r1 = det.detect(library, use_gnn=True, training_epochs=epochs)
    phase1_gangs = r1.get("gangs", []) or []
    t_phase1 = time.time() - t0

    known: Dict[str, List[str]] = {}
    # gang_id 前缀隔离：阶段一检测器与攒批检测器都从社区索引 0 起编 GANG_xxx，
    # 直接复用会 key 碰撞覆盖 known（F1/精度全污染），故各自加命名空间前缀。
    for gi, g in enumerate(phase1_gangs):
        gid = f"LIB-{gi}"
        known[gid] = [c for c in g.get("case_ids", []) if c in case_by_id]

    label_of: Dict[str, int] = {}
    labels: Dict[str, int] = {}
    counter = [0]

    def _register(gid: str, members: List[str]):
        if gid not in label_of:
            label_of[gid] = counter[0]
            counter[0] += 1
        for cid in members:
            labels[cid] = label_of[gid]

    for gid, members in known.items():
        _register(gid, members)

    matches_all: Dict[str, Dict] = {}
    held_ids: List[str] = []
    step_log: List[Dict[str, Any]] = []
    chunk_size = max(1, (len(stream) + chunks - 1) // chunks)

    for step, i in enumerate(range(0, len(stream), chunk_size)):
        chunk = stream[i:i + chunk_size]
        gangs_members = {gid: [case_by_id[c] for c in m] for gid, m in known.items() if m}
        profiles = build_gang_profiles(gangs_members)
        matches = match_cases_batch(profiles, chunk, text_threshold=text_threshold)
        matches_all.update(matches)
        for cid, m in matches.items():
            _register(m["gang_id"], [cid])

        unmatched = [c for c in chunk if c["case_id"] not in matches]
        held_ids.extend(c["case_id"] for c in unmatched)

        new_gangs = []
        if len(unmatched) >= 2:
            det2 = _make_detector(detector_mode)
            rb = det2.detect(unmatched, use_gnn=True, training_epochs=epochs)
            new_gangs = rb.get("gangs", []) or []
            for gi, g in enumerate(new_gangs):
                gid = f"STEP{step}-{gi}"
                members = [c for c in g.get("case_ids", []) if c in case_by_id]
                known[gid] = members
                _register(gid, members)

        step_log.append({
            "step": step, "chunk_cases": len(chunk),
            "matched": len(matches), "held": len(unmatched),
            "new_gangs": len(new_gangs),
            "known_gangs_after": len(known),
        })

    # 未匹配且未入团（held 单例）→ 各自单例，诚实计入
    for cid in held_ids:
        if cid not in labels:
            labels[cid] = counter[0]
            counter[0] += 1

    inc_f1 = ef.pairwise_f1(gt, labels)

    # 全量基线
    t0 = time.time()
    det_full = _make_detector(detector_mode)
    rf = det_full.detect(cases, use_gnn=True, training_epochs=epochs)
    full_labels = _cluster_labels(rf.get("gangs", []) or [], [c["case_id"] for c in cases])
    full_f1 = ef.pairwise_f1(gt, full_labels)
    t_full = time.time() - t0

    # 匹配精度：matched 案件是否挂到正确的已知团伙（按该团伙成员真值多数票）
    match_correct = 0
    for cid, m in matches_all.items():
        members = known.get(m["gang_id"], [])
        member_gts = [gt[c] for c in members if c in gt]
        if not member_gts:
            continue
        majority = max(set(member_gts), key=member_gts.count)
        if majority == gt.get(cid):
            match_correct += 1
    match_prec = match_correct / len(matches_all) if matches_all else 1.0

    return {
        "preset": name,
        "desc": next(p["desc"] for p in PRESETS if p["name"] == name),
        "n_cases": len(cases), "n_library": len(library), "n_stream": len(stream),
        "text_threshold": text_threshold,
        "f1_full": round(full_f1, 4),
        "f1_incremental": round(inc_f1, 4),
        "delta": round(inc_f1 - full_f1, 4),
        "hold_ok": round(inc_f1 >= full_f1 - 0.02, 2),
        "match_precision": round(match_prec, 4),
        "matched_cases": len(matches_all),
        "held_cases": len(held_ids),
        "hold_ratio": round(len(held_ids) / len(stream), 4) if stream else 0.0,
        "phase1_gangs": len(phase1_gangs),
        "final_gangs": len(known),
        "time_phase1_s": round(t_phase1, 1),
        "time_full_s": round(t_full, 1),
        "step_log": step_log,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--presets", default="p2,p3",
                    help="逗号分隔: p2 / p3")
    ap.add_argument("--chunks", type=int, default=2)
    ap.add_argument("--epochs", type=int, default=100)
    ap.add_argument("--text-threshold", type=float, default=DEFAULT_TEXT_THRESHOLD)
    ap.add_argument("--detector-mode", default="production",
                    choices=["production", "louvain"],
                    help="production=生产默认(deep_clustering)；louvain=纯Louvain(小规模正确分团，验证增量匹配)")
    ap.add_argument("--out", default="verify_incremental_results.json")
    args = ap.parse_args()

    tag_map = {'p2': 'P2', 'p3': 'P3'}
    req = [tag_map[x.strip().lower()] for x in args.presets.split(',')
           if x.strip().lower() in tag_map]
    if not req:
        print("无匹配预设，请用 --presets p2,p3")
        return
    selected = [p for p in PRESETS if any(r in p["name"] for r in req)]
    if not selected:
        print("无匹配预设，请用 --presets p2,p3")
        return

    results = []
    for p in selected:
        print(f"\n===== {p['name']} ({p['desc']}) =====", flush=True)
        r = run_preset(p["name"], p["kwargs"], chunks=args.chunks,
                       epochs=args.epochs, text_threshold=args.text_threshold,
                       detector_mode=args.detector_mode)
        results.append(r)
        print(json.dumps({k: v for k, v in r.items() if k != "step_log"},
                         ensure_ascii=False, indent=2))
        print("step_log:", json.dumps(r["step_log"], ensure_ascii=False))

    out_path = os.path.join(HERE, args.out)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n结果已落盘: {out_path}")


if __name__ == "__main__":
    main()
