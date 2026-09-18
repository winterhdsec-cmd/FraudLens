"""
诊断：HAN text 通道的二值化阈值（0.5）是否合理

背景
----
探针实验发现：Semantic(script)（BGE 话术嵌入 + KMeans）在重噪场景 F1=0.7773，
而 HAN（含 case_text_case 文本元路径）只有 0.5536，且 dual_channel_gain 为负
（P1 -0.0348 / P2 -0.0456），即"加上话术通道反而更差"。

怀疑根因
--------
graph_builder.py:522-555 `_metapath_text()` 把 BGE 余弦相似度**二值化**：
    if sim >= 0.5: 连边(1.0) else 不连(0.0)
连续相似度被压成 0/1，细粒度判别信息全部丢失；
且 BGE 中文嵌入的相似度普遍偏高，0.5 阈值可能连出近似全连通的图，
图聚合后导致过度平滑（over-smoothing），嵌入趋同。

本脚本量化验证：
  - 同团伙 / 跨团伙话术相似度的分布
  - 不同阈值下的连边率（同团伙 vs 跨团伙）与建图后的平均度

用法
----
python diag_text_channel.py                 # 默认测 P2 重噪配置
python diag_text_channel.py --preset P0     # 测干净配置
"""
import argparse
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import numpy as np  # noqa: E402
import eval_framework as ef  # noqa: E402


# 注意：这里是 generate_synthetic_dataset() 的真实参数名，
# 与 eval_framework.run_all() 的简写（cross / intra）不同
PRESETS = {
    "P0": dict(n_gangs=5, cases_per_gang=8, seed=42,
               cross_gang_account_share=0.0, intra_share_prob=1.0,
               attr_noise=0.0),
    "P1": dict(n_gangs=5, cases_per_gang=8, seed=42,
               cross_gang_account_share=0.05, intra_share_prob=0.9,
               attr_noise=0.10),
    "P2": dict(n_gangs=5, cases_per_gang=8, seed=42,
               cross_gang_account_share=0.15, intra_share_prob=0.75,
               attr_noise=0.25),
}


def bge_embed(texts):
    """与 eval_framework.baseline_semantic 一致的 BGE 编码（取 [CLS]）"""
    import torch
    from transformers import AutoTokenizer, AutoModel
    model_path = os.path.join(ef.BACKEND, "bge-large-zh-v1.5")
    tok = AutoTokenizer.from_pretrained(model_path)
    model = AutoModel.from_pretrained(model_path)
    enc = tok(texts, padding=True, truncation=True, max_length=128,
              return_tensors="pt")
    with torch.no_grad():
        out = model(**enc)
    return out.last_hidden_state[:, 0, :].cpu().numpy()


def main() -> int:
    ap = argparse.ArgumentParser(description="HAN 文本通道阈值诊断")
    ap.add_argument("--preset", default="P2", choices=list(PRESETS),
                    help="数据配置（默认 P2 重噪）")
    args = ap.parse_args()

    kwargs = PRESETS[args.preset]
    cases, _tx, gt = ef.sd_mod.generate_synthetic_dataset(**kwargs)

    texts = ef.case_scripts(cases)
    emb = bge_embed(texts)
    norm = emb / (np.linalg.norm(emb, axis=1, keepdims=True) + 1e-9)
    S = norm @ norm.T

    ids = [c["case_id"] for c in cases]
    n = len(ids)

    intra, inter = [], []
    for i in range(n):
        for j in range(i + 1, n):
            s = float(S[i, j])
            if gt[ids[i]] == gt[ids[j]]:
                intra.append(s)
            else:
                inter.append(s)
    intra = np.array(intra)
    inter = np.array(inter)

    print(f"\n{'=' * 72}")
    print(f"话术文本相似度诊断  配置={args.preset}  {len(cases)} 案 / "
          f"{len(set(gt.values()))} 团伙")
    print("=" * 72)
    print(f"同团伙对 {len(intra):>5}: mean={intra.mean():.4f}  "
          f"min={intra.min():.4f}  max={intra.max():.4f}")
    print(f"跨团伙对 {len(inter):>5}: mean={inter.mean():.4f}  "
          f"min={inter.min():.4f}  max={inter.max():.4f}")
    print(f"区分度（同团伙均值 - 跨团伙均值）: {intra.mean() - inter.mean():+.4f}")

    print(f"\n{'=' * 72}")
    print("不同阈值下的建图效果（当前实现用 0.5）")
    print("=" * 72)
    print(f"{'阈值':>6}{'同团伙连边率':>14}{'跨团伙连边率':>14}"
          f"{'平均度':>12}{'判别比':>10}")
    print("-" * 72)
    for th in [0.3, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95]:
        a = float((intra >= th).mean()) if len(intra) else 0.0
        b = float((inter >= th).mean()) if len(inter) else 0.0
        A = (S >= th).astype(float)
        np.fill_diagonal(A, 0.0)
        deg = float(A.sum(axis=1).mean())
        ratio = (a / b) if b > 0 else float("inf")
        mark = "  <== 当前实现" if abs(th - 0.5) < 1e-9 else ""
        print(f"{th:>6.2f}{a:>14.3f}{b:>14.3f}"
              f"{deg:>9.1f}/{n - 1:<2}{ratio:>10.2f}{mark}")

    print(f"\n说明：")
    print("  - 同团伙连边率应接近 1，跨团伙连边率应接近 0")
    print("  - 判别比 = 同团伙连边率 / 跨团伙连边率，越大越好")
    print("  - 平均度接近 n-1 说明图近似全连通，图聚合会严重过度平滑")
    return 0


if __name__ == "__main__":
    sys.exit(main())
