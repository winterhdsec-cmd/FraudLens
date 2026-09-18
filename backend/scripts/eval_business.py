#!/usr/bin/env python3
"""FraudLens 业务主链路端到端评测脚本（B-L4）。

用途：用带标签的合成案情集跑完整 `/agent-analyze` 主链路（analyst → cluster），
量化两项指标，作为业务就绪度的回归基线：
  1) 实体抽取 P/R/F1（账户 / 手机号 / 微信 / QQ 四类，宏平均）
  2) 团伙发现 BCubed-P / R / F1（对比 ground-truth 团伙划分）

设计纪律（与 docs/14 一致）：
  - 默认 llm_client=None，走本地正则抽取路径（数据不出域、可复现、零外部依赖）。
  - use_gnn=False，实体关联聚类为优先路径（B-L2），不触发 GNN/torch。
  - 回流闭环（B-L3）可通过 --accounts-tx 注入账户流转边做 best-effort 验证；
    缺 torch 或该路径异常时跳过并提示，不影响核心���标。

运行：
  cd backend
  python scripts/eval_business.py                 # 核心指标
  python scripts/eval_business.py --accounts-tx /path/to/tx.json   # 额外验证回流闭环
  python scripts/eval_business.py --out report.json

退出码：核心指标满足回归门（macro_entity_F1>=0.7 且 gang_BCubed_F1>=0.9）则 0，否则 1。
"""
import argparse
import json
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.dirname(HERE)  # .../backend
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)

FIXTURE_DEFAULT = os.path.join(BACKEND, "tests", "fixtures", "cases_labeled.json")

ENTITY_TYPES = ["bank_accounts", "phone_numbers", "wechat_ids", "qq_numbers"]


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def entity_metrics(gold: dict, pred: dict):
    """逐类算 P/R/F1，再宏平均。gold/pred: {case_id: {entity_type: [values]}}。"""
    per_type = {}
    for t in ENTITY_TYPES:
        tp = fp = fn = 0
        for cid in gold:
            g = set(gold.get(cid, {}).get(t, []) or [])
            p = set(pred.get(cid, {}).get(t, []) or [])
            tp += len(g & p)
            fp += len(p - g)
            fn += len(g - p)
        P = tp / (tp + fp) if (tp + fp) else 0.0
        R = tp / (tp + fn) if (tp + fn) else 0.0
        F = 2 * P * R / (P + R) if (P + R) else 0.0
        per_type[t] = {"P": round(P, 4), "R": round(R, 4), "F1": round(F, 4),
                       "tp": tp, "fp": fp, "fn": fn}
    macro_f1 = sum(per_type[t]["F1"] for t in ENTITY_TYPES) / len(ENTITY_TYPES)
    return per_type, macro_f1


def bcubed(gold_map: dict, pred_map: dict):
    """BCubed 指标。gold_map/pred_map: {item: cluster_id}。"""
    items = set(gold_map) & set(pred_map)
    if not items:
        return (0.0, 0.0, 0.0)
    p_sum = r_sum = 0.0
    for i in items:
        g = set(j for j in gold_map if gold_map[j] == gold_map[i])
        p = set(j for j in pred_map if pred_map[j] == pred_map[i])
        inter = len(g & p)
        p_sum += inter / len(p)
        r_sum += inter / len(g)
    n = len(items)
    P = p_sum / n
    R = r_sum / n
    F = 2 * P * R / (P + R) if (P + R) else 0.0
    return (P, R, F)


def run_pipeline(cases, accounts_tx=None):
    """跑主链路，返回 OrchestratorAgent.process 的结果。"""
    from agents.orchestrator import OrchestratorAgent
    orch = OrchestratorAgent(llm_client=None, use_gnn=False)
    ctx = {}
    if accounts_tx is not None:
        ctx["accounts_tx"] = accounts_tx
    return orch.process(cases, context=ctx)


def main():
    ap = argparse.ArgumentParser(description="FraudLens 业务主链路端到端评测 (B-L4)")
    ap.add_argument("--fixture", default=FIXTURE_DEFAULT, help="带标签案情 fixtures JSON")
    ap.add_argument("--out", default=None, help="输出评测报告 JSON 路径")
    ap.add_argument("--accounts-tx", default=None,
                    help="可选：账户流转边 JSON 文件，用于 best-effort 验证资金回流闭环(B-L3)")
    ap.add_argument("--amlsim", default=None,
                    help="可选：AMLSim 输出目录，验证'真实材料接入'资金流导入/回流闭环管线（诚实口径：不直接声称能自动发现 AMLSim 洗钱环）")
    args = ap.parse_args()

    # ── AMLSim 模式：验证真实材料接入的导入/回流闭环管线（诚实口径） ──
    if args.amlsim:
        from gnn.adapters import amlsim_to_accounts_tx
        import networkx as nx
        accounts_tx, stats = amlsim_to_accounts_tx(args.amlsim)
        DG = nx.DiGraph()
        for t in accounts_tx:
            DG.add_edge(f"account_{t['from_account']}", f"account_{t['to_account']}")
        try:
            n_cycles = len(list(nx.simple_cycles(DG)))
        except Exception:
            n_cycles = 0
        report = {
            "source": "amlsim",
            "ingestion": stats,
            "flow_graph": {
                "nodes": DG.number_of_nodes(),
                "edges": DG.number_of_edges(),
                "reflux_cycles": n_cycles,
            },
            "honest_note": (
                "AMLSim 为账户中心数据；本系统主链路（基于案件共享实体关联）不直接适用，"
                "且 GNN/图聚类在真实账户中心已知全法失效(F1≈0.002-0.010)。"
                "本评测仅验证资金流导入与回流闭环管线的正确性，不声称能自动发现 AMLSim 洗钱环。"
            ),
        }
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    fx = load_json(args.fixture)
    cases = fx["cases"]
    gt = fx["ground_truth"]

    accounts_tx = None
    if args.accounts_tx:
        accounts_tx = load_json(args.accounts_tx).get("accounts_tx")

    result = run_pipeline(cases, accounts_tx=accounts_tx)

    # 实体抽取：从主链路返回的 analyzed_cases 取 extracted_entities
    pred_entities = {}
    for c in result.get("cases", []):
        cid = c.get("case_id")
        pred_entities[cid] = c.get("extracted_entities", {}) or {}

    per_type, macro_f1 = entity_metrics(gt["entities"], pred_entities)

    # 团伙发现 BCubed
    pred_gangs = result.get("gangs", [])
    pred_map, pred_groups = {}, defaultdict(list)
    for gi, g in enumerate(pred_gangs):
        for cid in g.get("case_ids", []):
            pred_map[cid] = gi
            pred_groups[gi].append(cid)
    gold_map = {}
    for gi, g in enumerate(gt["gangs"]):
        for cid in g["case_ids"]:
            gold_map[cid] = gi
    P, R, F = bcubed(gold_map, pred_map)

    report = {
        "status": result.get("status"),
        "n_cases": len(cases),
        "n_gangs_pred": len(pred_gangs),
        "n_gangs_gold": len(gt["gangs"]),
        "entity_extraction": {
            "per_type": per_type,
            "macro_f1": round(macro_f1, 4),
        },
        "gang_bcubed": {
            "precision": round(P, 4),
            "recall": round(R, 4),
            "f1": round(F, 4),
        },
        "predicted_gangs": [
            {"gang_id": g.get("gang_id"), "case_ids": g.get("case_ids"),
             "fraud_type": g.get("fraud_type"),
             "evidence_chain_len": len(g.get("evidence_chain", []))}
            for g in pred_gangs
        ],
    }

    if args.accounts_tx:
        reflux = [
            {
                "gang_id": g.get("gang_id"),
                "is_reflux": g.get("is_reflux"),
                "reflux_cycles": g.get("reflux_cycles"),
                "freeze_candidates": g.get("freeze_candidates"),
            }
            for g in pred_gangs
        ]
        report["reflux_blobs"] = reflux

    print(json.dumps(report, ensure_ascii=False, indent=2))

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"\n[written] {args.out}")

    ok = macro_f1 >= 0.7 and F >= 0.9
    print(f"\n[REGRESSION GATE] macro_entity_F1={macro_f1:.3f} (>=0.7) | "
          f"gang_BCubed_F1={F:.3f} (>=0.9) => {'PASS' if ok else 'CHECK'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
