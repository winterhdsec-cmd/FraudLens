"""
T-Finance 数据集下载 + 规范化脚本。

把 T-Finance（Tang et al., ICML 2022, BWGNN）整理成 FraudLens 评测的规范布局：
    <out>/
      features.csv   10 维匿名特征（行号即账户 id）
      edges.csv      src,dst 有向交易边
      labels.txt     每行 0/1（0=正常, 1=异常账户）

用法：
    python scripts/fetch_tfinance.py                     # 尝试官方 Google Drive（需网络可达 Drive）
    python scripts/fetch_tfinance.py --url <镜像zip>     # 从任意镜像下载 zip（GitHub 等）
    python scripts/fetch_tfinance.py --dir <已下载目录>  # 已有明文数据目录，仅规范化为规范布局

官方来源：https://github.com/Wenqin740/Rethinking-Anomaly-Detection
（Google Drive 文件夹，DGL 图格式 zip；本脚本若检出 DGL graph.bin 且环境有 dgl 会自动转换，
否则给出人工指引。国内网络无法访问 Drive 时，请搜索 GitHub 上 "tf_fin.csv" 类明文镜像，
用 --url 或 --dir 接入。）
"""
import argparse
import csv
import glob
import os
import shutil
import sys
import tempfile
import urllib.request
import zipfile

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_OUT = os.path.join(BACKEND, "tfinance_real")
OFFICIAL_FOLDER = "1PpNwvZx_YRSCDiHaBUmRIS3x1rZR7fMr"
EXPECT = {"n": 39357, "edges": 21222543, "anomaly_ratio": 0.0458}


def _download(url: str, dest: str) -> None:
    print(f"[1/4] 下载 {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=300) as resp, open(dest, "wb") as f:
        shutil.copyfileobj(resp, f, length=1024 * 1024)
    print(f"      已保存 {dest} ({os.path.getsize(dest) / 1024 / 1024:.1f} MB)")


def _try_gdown_folder(out: str) -> bool:
    try:
        import gdown  # noqa: F401
    except ImportError:
        return False
    print("[1/4] 尝试 gdown 下载官方 Google Drive 文件夹（若网络可达 Drive）")
    try:
        gdown.download_folder(
            f"https://drive.google.com/drive/folders/{OFFICIAL_FOLDER}",
            output=os.path.join(out, "_raw"), quiet=False)
        return True
    except Exception as e:
        print(f"      gdown 失败: {e}")
        return False


def _dgl_to_canonical(directory: str, out: str) -> bool:
    """把 DGL graph.bin（官方格式）转成规范 CSV。需要环境装有 dgl。"""
    try:
        import dgl
        import torch
    except ImportError:
        return False
    candidates = glob.glob(os.path.join(directory, "**", "graph*.bin"), recursive=True)
    if not candidates:
        return False
    print("[3/4] 检测到 DGL graph.bin，转换中...")
    g, _ = dgl.load_graphs(candidates[0])
    g = g[0]
    feat = g.ndata["feature"].numpy()
    label = g.ndata["label"].numpy().argmax(1)
    src, dst = g.edges()
    n = feat.shape[0]
    with open(os.path.join(out, "features.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([f"f{i}" for i in range(feat.shape[1])])
        for row in feat:
            w.writerow([f"{x:.6f}" for x in row])
    with open(os.path.join(out, "edges.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["src", "dst"])
        for i in range(len(src)):
            w.writerow([int(src[i]), int(dst[i])])
    with open(os.path.join(out, "labels.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(str(int(x)) for x in label))
    print(f"      转换完成: {n} 节点, {len(src)} 边 -> {out}")
    return True


def _plain_to_canonical(directory: str, out: str) -> bool:
    """把明文镜像（tf_fin.csv / tf_fin_edges.csv / tf_fin_label.txt 或规范布局）复制/整理为规范布局。"""
    map_in = {
        "features.csv": "features.csv",
        "tf_fin.csv": "features.csv",
        "edges.csv": "edges.csv",
        "tf_fin_edges.csv": "edges.csv",
        "labels.txt": "labels.txt",
        "tf_fin_label.txt": "labels.txt",
    }
    found = False
    os.makedirs(out, exist_ok=True)
    for src_name, dst_name in map_in.items():
        p = os.path.join(directory, src_name)
        if os.path.isfile(p):
            shutil.copyfile(p, os.path.join(out, dst_name))
            found = True
    return found


def _verify(out: str) -> bool:
    print("[4/4] 校验")
    def _count_lines(p):
        if not os.path.isfile(p):
            return 0
        with open(p, "r", encoding="utf-8-sig") as f:
            return sum(1 for _ in f)
    n = max(_count_lines(os.path.join(out, "features.csv")) - 1, 0)
    e = max(_count_lines(os.path.join(out, "edges.csv")) - 1, 0)
    lab = _count_lines(os.path.join(out, "labels.txt"))
    ok_n = abs(n - EXPECT["n"]) / EXPECT["n"] < 0.02
    ok_e = abs(e - EXPECT["edges"]) / EXPECT["edges"] < 0.02
    ok_lab = lab == n and n > 0
    print(f"  节点 {n}（期望≈{EXPECT['n']}，{'OK' if ok_n else '异常'}）")
    print(f"  边   {e}（期望≈{EXPECT['edges']}，{'OK' if ok_e else '异常（镜像可能裁剪，可接受）'}）")
    print(f"  标签 {lab}（需=节点数，{'OK' if ok_lab else '异常'}）")
    return ok_n and ok_lab


def main():
    ap = argparse.ArgumentParser(description="T-Finance 数据集下载与规范化")
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--url", default=None, help="镜像 zip 直链（GitHub 等）")
    ap.add_argument("--dir", default=None, help="已下载的明文/DGL 数据目录（跳过下载）")
    args = ap.parse_args()

    out = os.path.abspath(args.out)
    os.makedirs(out, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="tfinance_")

    # 1) 获取原始文件
    raw_dir = tmp
    if args.dir:
        raw_dir = os.path.abspath(args.dir)
        print("[1/4] 使用已有目录:", raw_dir)
    elif args.url:
        zpath = os.path.join(tmp, "tfinance.zip")
        _download(args.url, zpath)
        print("[2/4] 解压")
        with zipfile.ZipFile(zpath) as z:
            z.extractall(tmp)
    else:
        ok = _try_gdown_folder(out)
        if ok:
            raw_dir = os.path.join(out, "_raw")
        else:
            print("[!] 官方 Drive 不可达。请用下面任一方式：")
            print("    1) 在有网环境访问官方 Drive 后，把 tfinance 目录放好，再运行:")
            print(f"       python scripts/fetch_tfinance.py --dir <目录>")
            print("    2) 找 GitHub 明文镜像 zip 后运行:")
            print(f"       python scripts/fetch_tfinance.py --url <镜像zip直链>")
            shutil.rmtree(tmp, ignore_errors=True)
            sys.exit(1)

    # 2) 在 raw 树里找数据
    if not (_plain_to_canonical(raw_dir, out) or _dgl_to_canonical(raw_dir, out)):
        # 可能在子目录里
        found_sub = False
        for root, _dirs, files in os.walk(raw_dir):
            if any(f in ("tf_fin.csv", "features.csv", "graph.bin") for f in files):
                if _plain_to_canonical(root, out) or _dgl_to_canonical(root, out):
                    found_sub = True
                    break
        if not found_sub:
            print("[!] 未在下载内容中识别出 T-Finance 数据（期待 tf_fin.csv / graph.bin）")
            print("    请人工确认后把文件整理成规范布局放入:", out)
            shutil.rmtree(tmp, ignore_errors=True)
            sys.exit(2)

    shutil.rmtree(tmp, ignore_errors=True)
    if _verify(out):
        print(f"\n完成。数据已就绪: {out}")
        print("运行评测: python scripts/eval_tfinance.py")
    else:
        print("\n[!] 校验未完全通过，请人工检查文件完整性。")


if __name__ == "__main__":
    main()
