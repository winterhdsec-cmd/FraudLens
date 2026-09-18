"""
Elliptic 真实基准评测入口。

用法：
    python scripts/eval_elliptic.py [--dir <数据目录>] [--no-features]

数据目录默认 backend/data/datasets/elliptic（项目 2026-07-30 已下载，含完整特征）。
结果打印表格并写入 backend/gnn/results/elliptic_results.json。
"""
import argparse
import json
import os
import sys

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND)

from gnn.eval_framework import run_elliptic_eval, fmt_node_fraud  # noqa: E402

DEFAULT_DIR = os.path.join(BACKEND, "data", "datasets", "elliptic")


def main():
    ap = argparse.ArgumentParser(description="Elliptic 节点级欺诈检测评测")
    ap.add_argument("--dir", default=os.environ.get("ELLIPTIC_DIR", DEFAULT_DIR))
    ap.add_argument("--no-features", action="store_true",
                    help="不加载 690MB 特征文件，退化为纯结构风险（更快）")
    args = ap.parse_args()

    if not os.path.isdir(args.dir):
        print(f"[!] 数据目录不存在: {args.dir}")
        print("    数据应在 backend/data/datasets/elliptic/（项目已下载）")
        sys.exit(1)

    result = run_elliptic_eval(args.dir, with_features=not args.no_features)
    if "error" in result:
        print(f"[!] 评测失败: {result['error']}")
        sys.exit(2)

    print(fmt_node_fraud(result))

    out_dir = os.path.join(BACKEND, "gnn", "results")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "elliptic_results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\n结果已写入: {out_path}")


if __name__ == "__main__":
    main()
