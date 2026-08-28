"""一次性脚本：用真实 BGE-large 本地嵌入重算 Semantic 基线（clean + hard），
回填 eval_results.json，替换原先的 TF-IDF 代理值。复用 eval_framework 原函数保证数据集 100% 一致。
"""
import os
import sys
import json

sys.path.insert(0, "/app/gnn")  # 让 import eval_framework 可解析
import eval_framework as ef

RESULTS = "/app/gnn/eval_results.json"


def recompute(cross: float):
    cases, accounts_tx, gt = ef.load_dataset(
        seed=42, n_gangs=5, cases_per_gang=8,
        cross=cross, intra=1.0, attr_noise=0.0)
    X, ids = ef.case_feature_matrix(cases)
    n_true = len(set(gt.values()))
    sem_pred, sem_notes = ef.baseline_semantic(cases, ids, n_true)
    metrics = ef.compute_metrics(gt, sem_pred)
    return metrics, sem_notes


def main():
    with open(RESULTS) as f:
        data = json.load(f)

    summary = []
    for key, cross in [("clean", 0.0), ("hard", 0.2)]:
        metrics, notes = recompute(cross)
        data[key]["baselines"]["Semantic"] = metrics
        # 去掉旧的 TF-IDF 代理标注，补真实状态
        data[key]["notes"] = [
            n for n in data[key].get("notes", [])
            if "TF-IDF代理" not in n
        ]
        status = notes[-1] if notes else "语义基线=BGE-large 本地嵌入"
        data[key]["notes"].append(status)
        summary.append((key, metrics["f1"], status))

    with open(RESULTS, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print("DONE")
    for key, f1, status in summary:
        print(f"  {key:6s} Semantic F1={f1:.4f}  | {status}")


if __name__ == "__main__":
    main()
