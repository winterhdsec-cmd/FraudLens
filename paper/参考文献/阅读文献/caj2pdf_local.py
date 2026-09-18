# -*- coding: utf-8 -*-
"""KDH(CAJ) -> PDF 本地转换脚本
原理：KDH 文件 = 前254字节头 + XOR(密钥"FZHMEI")加密的 PDF，
解密后用 PyMuPDF 自动重建 xref 并保存为标准 PDF。
"""
import os
import sys
import fitz

KDH_PASSPHRASE = b"FZHMEI"


def kdh_to_pdf(src: str, dst: str) -> None:
    with open(src, "rb") as fp:
        origin = fp.read()

    # 跳过 254 字节头部，逐字节 XOR 解密
    origin = origin[254:]
    output = bytearray(len(origin))
    keylen = len(KDH_PASSPHRASE)
    for i, b in enumerate(origin):
        output[i] = b ^ KDH_PASSPHRASE[i % keylen]
    output = bytes(output)

    # 截断到 %%EOF
    eofpos = output.rfind(b"%%EOF")
    if eofpos < 0:
        raise RuntimeError(f"%%EOF mark not found in {src}")
    pdf_data = output[: eofpos + 5]

    tmp = dst + ".tmp"
    with open(tmp, "wb") as fp:
        fp.write(pdf_data)

    # 用 PyMuPDF 打开并重写（自动修复 xref）
    doc = fitz.open(tmp)
    doc.save(dst, garbage=4, deflate=True)
    n_pages = doc.page_count
    doc.close()
    os.remove(tmp)
    print(f"[OK] {os.path.basename(src)} -> {os.path.basename(dst)} ({n_pages} pages)")


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python caj2pdf_local.py <file.caj|dir> [output_dir]")
        sys.exit(1)
    target = sys.argv[1]
    out_dir = sys.argv[2] if len(sys.argv) > 2 else os.path.dirname(os.path.abspath(target))

    if os.path.isdir(target):
        files = [os.path.join(target, f) for f in os.listdir(target) if f.lower().endswith(".caj")]
    else:
        files = [target]

    os.makedirs(out_dir, exist_ok=True)
    ok, fail = 0, []
    for f in files:
        dst = os.path.join(out_dir, os.path.splitext(os.path.basename(f))[0] + ".pdf")
        try:
            kdh_to_pdf(f, dst)
            ok += 1
        except Exception as e:
            fail.append((f, str(e)))
            print(f"[FAIL] {os.path.basename(f)}: {e}")
    print(f"\nDone: {ok}/{len(files)} converted.")
    if fail:
        print("Failed files:")
        for f, e in fail:
            print(f"  {f}: {e}")


if __name__ == "__main__":
    main()
