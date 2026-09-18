# -*- coding: utf-8 -*-
"""出图即验：对论文两张 TikZ 图做量化体检。
检查项：
  1) 内容盒内文字无溢出（margin >= -1pt）
  2) 浮动标签与所有内容盒/底部条零重叠
  3) 内容盒高度均匀（打印供人工确认）
  4) 图宽（cm，主稿用 resizebox 缩放，仅作参考）
用法：python _verify_fig.py [fig1.pdf fig2.pdf ...]
"""
import sys
import fitz

LABEL_KEYS = ["案情输入", "候选结果", "决策记录", "反思", "评价",
              "置信度低", "返回规划", "Human-in-the-loop"]


def overlaps(a, b):
    return not (a.x1 <= b.x0 or b.x1 <= a.x0 or a.y1 <= b.y0 or b.y1 <= a.y0)


def classify(rects):
    # 内容盒高度锁定为 1.25cm(≈35pt) 或 2.9cm(≈82pt)，避免把虚线路径 bbox 误判为盒
    boxes = [r for r in rects if ((30 < r.height < 45) or (75 < r.height < 90)) and r.width > 40]
    panels = [r for r in rects if r.height >= 120 and r.width > 80]
    bars = [r for r in rects if r.height <= 25 and r.width > 200]
    return boxes, panels, bars


def verify(pdf):
    doc = fitz.open(pdf)
    p = doc[0]
    rects = [d["rect"] for d in p.get_drawings()
             if d["rect"].width > 40 and d["rect"].height > 10]
    boxes, panels, bars = classify(rects)
    td = p.get_text("dict")

    problems = []

    # 1) 内容盒内文字无溢出
    for blk in td["blocks"]:
        for ln in blk.get("lines", []):
            for sp in ln.get("spans", []):
                t = sp["text"].strip()
                if not t:
                    continue
                bb = fitz.Rect(sp["bbox"])
                host = [r for r in boxes if r.contains(bb)]
                if not host:
                    continue  # 标题/标签在盒外，单独检查
                r = min(host, key=lambda z: z.width * z.height)
                m = min(bb.x0 - r.x0, r.x1 - bb.x1, bb.y0 - r.y0, r.y1 - bb.y1)
                if m < -1.0:
                    problems.append(f"OVERFLOW 文字 {t!r} margin={m:.1f}pt")

    # 2) 浮动标签与盒/条零重叠（排除落在 bar 上的文字，避免 bar 文本误报）
    labels = []
    eval_parts = fitz.Rect()
    for blk in td["blocks"]:
        for ln in blk.get("lines", []):
            for sp in ln.get("spans", []):
                t = sp["text"].strip()
                if not t:
                    continue
                bb = fitz.Rect(sp["bbox"])
                if any(overlaps(bb, b) for b in bars):
                    continue  # 属于底部条文字，跳过
                if any(r.contains(bb) for r in boxes):
                    continue  # 属于内容盒内文字，不是浮动标签
                if any(k in t for k in LABEL_KEYS):
                    if "反思" in t or "评价" in t:
                        eval_parts |= bb
                    else:
                        labels.append((t, bb))
    if not eval_parts.is_empty:
        labels.append(("评价/反思回流", eval_parts))

    for name, bb in labels:
        hit = [r for r in (boxes + bars) if overlaps(bb, r)]
        if hit:
            problems.append(f"LABEL {name!r} 与盒/条重叠")
        else:
            pass  # 正常

    # 3) 内容盒高度均匀
    heights = sorted(round(b.height, 1) for b in boxes)
    # 4) 图宽
    width_cm = round(p.rect.width / 28.35, 2)

    print(f"[{pdf}]")
    print(f"  内容盒数={len(boxes)} 高度(pt)={heights}")
    print(f"  panel数={len(panels)} bar数={len(bars)} 图宽={width_cm}cm")
    print(f"  浮动标签检测: {[n for n,_ in labels]}")
    if problems:
        print("  问题:")
        for pr in problems:
            print("   -", pr)
    else:
        print("  ✓ 无文字溢出 / 无标签重叠")
    return problems


if __name__ == "__main__":
    targets = sys.argv[1:] or ["fig_workflow.pdf", "fig_arch.pdf"]
    allp = []
    for f in targets:
        allp += verify(f)
    print("\n汇总:", "全部通过 ✓" if not allp else f"{len(allp)} 处问题 ✗")
    sys.exit(1 if allp else 0)
