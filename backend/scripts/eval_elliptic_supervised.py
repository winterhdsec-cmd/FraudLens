"""
Elliptic 有监督训练评测入口。

用法：
    python scripts/eval_elliptic_supervised.py [--dir <数据目录>] [--epochs 150]

数据目录默认 backend/data/datasets/elliptic。结果打印表格并写入
backend/gnn/results/elliptic_supervised_results.json。
"""
import argparse
import json
import os
import sys

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND)

from gnn.elliptic_supervised import run_elliptic_supervised_eval, fmt_supervised  # noqa: E402

DEFAULT_DIR = os.path.join(BACKEND, "data", "datasets", "elliptic")


def main():
    ap = argparse.ArgumentParser(description="Elliptic 有监督训练评测")
    ap.add_argument("--dir", default=os.environ.get("ELLIPTIC_DIR", DEFAULT_DIR))
    ap.add_argument("--epochs", type=int, default=150)
    ap.add_argument("--hidden", type=int, default=64)
    args = ap.parse_args()

    if not os.path.isdir(args.dir):
        print(f"[!] 数据目录不存在: {args.dir}")
        sys.exit(1)

    result = run_elliptic_supervised_eval(args.dir, epochs=args.epochs, hidden=args.hidden)
    if "error" in result:
        print(f"[!] 评测失败: {result['error']}")
        sys.exit(2)

    print(fmt_supervised(result))

    out_dir = os.path.join(BACKEND, "gnn", "results")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "elliptic_supervised_results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\n结果已写入: {out_path}")


if __name__ == "__main__":
    main()
