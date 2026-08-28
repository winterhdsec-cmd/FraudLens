import xml.etree.ElementTree as ET
import os

OUT = "E:/FraudLens/paper/论文产出/CPEC2026教学案例稿"
files = ["fig_arch.drawio", "fig_workflow.drawio", "fig_education_loop.drawio"]


def rects(path):
    tree = ET.parse(path)
    root = tree.getroot()
    out = []
    for cell in root.iter("mxCell"):
        geo = cell.find("mxGeometry")
        if geo is None:
            continue
        try:
            x = float(geo.get("x"))
            y = float(geo.get("y"))
            w = float(geo.get("width"))
            h = float(geo.get("height"))
        except (TypeError, ValueError):
            continue
        val = cell.get("value") or ""
        style = cell.get("style") or ""
        out.append((x, y, w, h, val, style))
    return out


def overlap_area(a, b):
    x = max(a[0], b[0])
    y = max(a[1], b[1])
    xx = min(a[0] + a[2], b[0] + b[2])
    yy = min(a[1] + a[3], b[1] + b[3])
    if xx <= x or yy <= y:
        return 0
    return (xx - x) * (yy - y)


def contains(a, b):
    return (a[0] <= b[0] and a[1] <= b[1]
            and a[0] + a[2] >= b[0] + b[2]
            and a[1] + a[3] >= b[1] + b[3])


for f in files:
    rs = rects(os.path.join(OUT, f))
    print(f"\n=== {f} : {len(rs)} rects ===")
    problems = 0
    for i in range(len(rs)):
        for j in range(i + 1, len(rs)):
            a, b = rs[i], rs[j]
            ov = overlap_area(a, b)
            if ov == 0:
                continue
            if contains(a, b) or contains(b, a):
                continue
            amin = min(a[2] * a[3], b[2] * b[3])
            if ov / amin > 0.25:
                problems += 1
                print(f"  [重叠] '{a[4][:12]}' vs '{b[4][:12]}' 重叠={ov:.0f} ({100*ov/amin:.0f}%)")
    if problems == 0:
        print("  OK 无显著非包含重叠")
