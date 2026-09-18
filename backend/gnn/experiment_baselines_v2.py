"""
实验 ④：异构图基线公平对比（HAN vs RGCN vs GAT）+ 规模扩展
- 三模型同协议：同 features/meta_path_adjacency、同 GraphCL 对比学习、同 KMeans 评测。
- 扩展规模：15 个种子 × {cross=0.0,0.2,0.4}；并附 scale 鲁棒性（n_gangs∈{5,8,10}）。
- 诚实口径：全部为合成案件图验证；用于回答"异构图注意力 vs 简单异构图传播"，
  不构成真实数据验证。
输出：backend/gnn/baseline_v2_results.json
"""
import sys, os, json
import numpy as np
import torch

BACKEND = os.path.dirname(os.path.abspath(__file__))
for p in (BACKEND, os.path.dirname(BACKEND)):
    if p not in sys.path:
        sys.path.insert(0, p)

import eval_framework as ef
import graph_builder as gb_mod
import han_model
import baselines_hetero as bh
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans

SEEDS = [42, 7, 123, 1, 2, 3, 10, 20, 33, 55, 99, 256, 777, 888, 1024]
CROSS = [0.0, 0.2, 0.4]
EPOCHS = 100
N_GANGS_DEFAULT = 5
CASES_PER_GANG = 8


def build_inputs(cases, accounts_tx, use_text=True):
    builder = gb_mod.FraudGraphBuilder(use_db=False, use_cache=False, use_text_channel=use_text)
    G = builder.build_graph(cases, accounts_tx=accounts_tx)
    features = builder.get_node_features()
    meta_np = builder.get_meta_path_adjacency()
    if features is None or len(features) < 3 or not meta_np:
        return None
    feat_t = torch.as_tensor(np.asarray(features, dtype=np.float32))
    meta_t = {k: torch.as_tensor(np.asarray(v, dtype=np.float32)) for k, v in meta_np.items()}
    case_ids = [n for n, d in G.nodes(data=True) if d.get("node_type") == "case"]
    case_idx = [builder.node_to_idx[n] for n in case_ids]
    return feat_t, meta_t, case_ids, case_idx


def embed_predict(model, feat_t, meta_t, case_ids, case_idx, n_true):
    ce = bh.extract_case_embeddings(model, feat_t, meta_t, case_idx, scaler=StandardScaler())
    pred_arr = KMeans(n_clusters=n_true, random_state=0, n_init=10).fit_predict(ce)
    pred = {cid: int(lab) for cid, lab in zip(case_ids, pred_arr)}
    return pred


def run_one(cases, accounts_tx, gt, use_text=True, epochs=EPOCHS):
    built = build_inputs(cases, accounts_tx, use_text=use_text)
    if built is None:
        return None
    feat_t, meta_t, case_ids, case_idx = built
    n_true = len(set(gt.values()))
    mp_keys = list(meta_t.keys())
    in_dim = feat_t.shape[1]
    out = {}

    # HAN（训练其 .han 编码器）
    han = han_model.FraudHAN(in_dim=in_dim, hidden_dim=64, embedding_dim=32,
                             num_classes=10, num_heads=4, num_layers=2)
    enc = han.han
    bh.graphcl_pretrain(enc, feat_t, meta_t, epochs=epochs, batch=min(256, feat_t.shape[0]))
    out["HAN"] = ef.compute_metrics(gt, embed_predict(enc, feat_t, meta_t, case_ids, case_idx, n_true))

    # RGCN
    rgcn = bh.RGCNBaseline(in_dim=in_dim, hidden_dim=64, out_dim=32, num_layers=2, meta_paths=mp_keys)
    bh.graphcl_pretrain(rgcn, feat_t, meta_t, epochs=epochs, batch=min(256, feat_t.shape[0]))
    out["RGCN"] = ef.compute_metrics(gt, embed_predict(rgcn, feat_t, meta_t, case_ids, case_idx, n_true))

    # GAT
    gat = bh.GATBaseline(in_dim=in_dim, hidden_dim=64, out_dim=32, num_layers=2, meta_paths=mp_keys)
    bh.graphcl_pretrain(gat, feat_t, meta_t, epochs=epochs, batch=min(256, feat_t.shape[0]))
    out["GAT"] = ef.compute_metrics(gt, embed_predict(gat, feat_t, meta_t, case_ids, case_idx, n_true))

    # 上下文基线（非 GNN）
    X, ids = ef.case_feature_matrix(cases)
    out["KMeans"] = ef.compute_metrics(gt, ef.baseline_kmeans(X, ids, n_true))
    sem_pred, _ = ef.baseline_semantic(cases, ids, n_true)
    out["Semantic"] = ef.compute_metrics(gt, sem_pred)
    cur_pred = ef.baseline_current_system(cases, accounts_tx, use_fund=True)
    out["CurrentSystem"] = ef.compute_metrics(gt, cur_pred)
    return out


def summarize(records):
    models = ["HAN", "RGCN", "GAT", "KMeans", "Semantic", "CurrentSystem"]
    summary = {}
    for m in models:
        vals = [r[m]["f1"] for r in records if r and m in r]
        if vals:
            summary[m] = {"f1_mean": round(float(np.mean(vals)), 4),
                          "f1_std": round(float(np.std(vals)), 4),
                          "n": len(vals)}
    return summary


def main():
    records = []
    for cross in CROSS:
        for seed in SEEDS:
            cases, accounts_tx, gt = ef.load_dataset(seed=seed, n_gangs=N_GANGS_DEFAULT,
                                                    cases_per_gang=CASES_PER_GANG, cross=cross)
            try:
                res = run_one(cases, accounts_tx, gt)
            except Exception as e:
                res = {"__error__": f"{type(e).__name__}: {str(e)[:160]}"}
            rec = {"seed": seed, "cross": cross}
            if res and "__error__" not in res:
                rec.update(res)
            else:
                rec["__error__"] = res.get("__error__", "unknown") if res else "none"
            records.append(rec)
            print(f"cross={cross} seed={seed} -> "
                  f"HAN={rec.get('HAN',{}).get('f1')} RGCN={rec.get('RGCN',{}).get('f1')} "
                  f"GAT={rec.get('GAT',{}).get('f1')}")

    # scale 鲁棒性：n_gangs ∈ {5,8,10}，固定 cross=0.2，5 个种子
    scale_records = []
    for n_g in [5, 8, 10]:
        for seed in [42, 7, 123, 256, 1024]:
            cases, accounts_tx, gt = ef.load_dataset(seed=seed, n_gangs=n_g,
                                                    cases_per_gang=CASES_PER_GANG, cross=0.2)
            try:
                res = run_one(cases, accounts_tx, gt)
                row = {"n_gangs": n_g, "seed": seed}
                if res and "__error__" not in res:
                    for m in ["HAN", "RGCN", "GAT"]:
                        row[m] = res[m]["f1"]
                    scale_records.append(row)
            except Exception as e:
                scale_records.append({"n_gangs": n_g, "seed": seed, "error": str(e)[:120]})

    out = {
        "config": {"seeds": SEEDS, "cross": CROSS, "epochs": EPOCHS,
                   "n_gangs_default": N_GANGS_DEFAULT, "cases_per_gang": CASES_PER_GANG,
                   "note": "合成案件图；HAN/RGCN/GAT 同协议对比学习+KMeans评测；非真实数据验证"},
        "per_seed": records,
        "summary": summarize(records),
        "scale_robustness": scale_records,
        "scale_summary": {str(g): _mean_f1(scale_records, g) for g in [5, 8, 10]},
    }
    with open(os.path.join(BACKEND, "baseline_v2_results.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print("\n=== SUMMARY (F1 mean±std) ===")
    for m, s in out["summary"].items():
        print(f"  {m:14s}: {s['f1_mean']} ± {s['f1_std']}  (n={s['n']})")
    print("=== SCALE ROBUSTNESS (HAN/RGCN/GAT mean F1) ===")
    for g, sv in out["scale_summary"].items():
        print(f"  n_gangs={g}: {sv}")


def _mean_f1(scale_records, n_g):
    rows = [r for r in scale_records if r.get("n_gangs") == n_g and "HAN" in r]
    if not rows:
        return None
    return {m: round(float(np.mean([r[m] for r in rows])), 4) for m in ["HAN", "RGCN", "GAT"]}


if __name__ == "__main__":
    main()
