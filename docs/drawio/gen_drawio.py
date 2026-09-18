# -*- coding: utf-8 -*-
"""Generate fig2..fig8 drawio XML for FraudLens proposal (v3, low-text structural diagrams).
Run: python gen_drawio.py  -> writes figN_*.drawio next to this file. fig1 is hand-authored."""
import os

OUT = os.path.dirname(os.path.abspath(__file__))

F = "fontFamily=Microsoft YaHei;"
BOX = "rounded=0;whiteSpace=wrap;html=1;fontSize=17;" + F
TXT = "text;html=1;fontSize=17;" + F
EDGE = ("edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;strokeWidth=2;"
        "strokeColor=#666666;fontSize=15;verticalAlign=middle;" + F)

def xesc(s):
    t = s.replace("\n", "\x01")
    t = t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    return t.replace("\x01", "&lt;br&gt;")

def V(cid, x, y, w, h, value="", style=BOX):
    return (f'<mxCell id="{cid}" value="{xesc(value)}" style="{style}" vertex="1" parent="1">'
            f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry" /></mxCell>')

def E(cid, src, tgt, value="", style=EDGE, points=None):
    return (f'<mxCell id="{cid}" value="{xesc(value)}" style="{style}" edge="1" parent="1" '
            f'source="{src}" target="{tgt}"><mxGeometry relative="1" as="geometry">'
            + (('<Array as="points">' + "".join(f'<mxPoint x="{a}" y="{b}" />' for a, b in points) + '</Array>') if points else '')
            + '</mxGeometry></mxCell>')

def L(cid, x1, y1, x2, y2, style="endArrow=none;html=1;strokeWidth=2;strokeColor=#333333;"):
    return (f'<mxCell id="{cid}" style="{style}" edge="1" parent="1">'
            f'<mxGeometry relative="1" as="geometry">'
            f'<mxPoint x="{x1}" y="{y1}" as="sourcePoint" /><mxPoint x="{x2}" y="{y2}" as="targetPoint" />'
            '</mxGeometry></mxCell>')

def diagram(name, cells):
    # 自动在内容包围盒外 40px 处放两个 1x1 透明锚点：
    # page=0 导出按内容包围盒裁剪，贴边元素的描边会被裁掉，锚点撑出安全边距。
    import re as _re
    x0, y0, x1, y1 = [], [], [], []
    for c in cells:
        for m in _re.finditer(r'<mxGeometry x="(-?\d+)" y="(-?\d+)" width="(\d+)" height="(\d+)"', c):
            x, y, w, h = map(int, m.groups())
            x0.append(x); y0.append(y); x1.append(x + w); y1.append(y + h)
        for m in _re.finditer(r'<mxPoint x="(-?\d+)" y="(-?\d+)" as="(?:source|target)Point"', c):
            x, y = map(int, m.groups())
            x0.append(x); y0.append(y); x1.append(x); y1.append(y)
    pad = "fillColor=none;strokeColor=none;html=1;"
    if x0:
        cells = ([V("__p1", min(x0) - 40, min(y0) - 40, 1, 1, "", pad),
                  V("__p2", max(x1) + 40, max(y1) + 40, 1, 1, "", pad)] + list(cells))
    head = ('<mxfile host="app.diagrams.net" version="24.0.0" type="device">\n'
            f'  <diagram id="{name}" name="{name}">\n'
            '    <mxGraphModel dx="1400" dy="700" grid="0" gridSize="10" guides="1" tooltips="1" '
            'connect="1" arrows="1" fold="1" page="0" pageScale="1" pageWidth="1600" pageHeight="900" '
            'math="0" shadow="0">\n      <root>\n        <mxCell id="0" />\n        <mxCell id="1" parent="0" />\n')
    body = "\n".join("        " + c for c in cells)
    return head + body + "\n      </root>\n    </mxGraphModel>\n  </diagram>\n</mxfile>\n"

def band(cid, x, y, w, h, fill="#F7F7F7", stroke="#BFBFBF"):
    return V(cid, x, y, w, h, "", f"rounded=0;html=1;fillColor={fill};strokeColor={stroke};")

# ---------------- fig2 四层架构 ----------------
def fig2():
    c = []
    blue, green, gold = "#6C8EBF", "#82B366", "#D79B00"
    c.append(band("b1", 120, 40, 1300, 150, "#FAFBFD", blue))
    c.append(band("b2", 120, 240, 1300, 180, "#FAFBFD", blue))
    c.append(band("b3", 120, 470, 1300, 130, "#F8FBF7", green))
    c.append(band("b4", 120, 650, 1300, 140, "#FFFDF8", gold))
    c.append(V("l1", 140, 50, 300, 32, "① 线索进来", TXT + "fontStyle=1;fontSize=18;fontColor=#2F5B8F;"))
    c.append(V("l2", 140, 252, 300, 32, "② 数字分析员团队", TXT + "fontStyle=1;fontSize=18;fontColor=#2F5B8F;"))
    c.append(V("l3", 140, 482, 300, 32, "③ 织网找团", TXT + "fontStyle=1;fontSize=18;fontColor=#4F7A3A;"))
    c.append(V("l4", 140, 662, 300, 32, "④ 结果输出", TXT + "fontStyle=1;fontSize=18;fontColor=#B07C00;"))
    for i, t in enumerate(["话术文本", "案件表格", "聊天截图"]):
        c.append(V(f"in{i}", 170 + i * 390, 100, 330, 70, t, BOX + "fillColor=#DAE8FC;strokeColor=" + blue + ";"))
    for i, t in enumerate(["整理线索", "拆解话术", "追踪资金", "提出串并", "反思质检"]):
        c.append(V(f"ag{i}", 150 + i * 252, 315, 212, 70, t, BOX + "fillColor=" + blue + ";strokeColor=" + blue + ";fontColor=#FFFFFF;fontStyle=1;"))
    c.append(V("net", 170, 515, 1200, 64, "把案件、账户、号码、话术、城市连成一张关系网，自动圈出团伙",
               BOX + "fillColor=#D5E8D4;strokeColor=" + green + ";fontStyle=1;"))
    for i, t in enumerate(["团伙清单", "团伙画像", "研判报告", "资金流向图"]):
        c.append(V(f"out{i}", 170 + i * 320, 700, 280, 70, t, BOX + "fillColor=#FFF2CC;strokeColor=" + gold + ";"))
    # 深色实心条+白字（text 样式的 fontBackground 在 CLI 导出中不渲染，白字会隐形）
    c.append(V("priv", 120, 820, 1300, 56, "全程本地部署 · 案件数据不出公安网",
               BOX + "fillColor=#333333;strokeColor=#333333;fontColor=#FFFFFF;fontStyle=1;fontSize=18;"))
    c.append(E("e12", "b1", "b2", "", EDGE + "exitX=0.5;exitY=1;entryX=0.5;entryY=0;strokeWidth=3;"))
    c.append(E("e23", "b2", "b3", "", EDGE + "exitX=0.5;exitY=1;entryX=0.5;entryY=0;strokeWidth=3;"))
    c.append(E("e34", "b3", "b4", "", EDGE + "exitX=0.5;exitY=1;entryX=0.5;entryY=0;strokeWidth=3;"))
    for i in range(4):
        c.append(E(f"pe{i}", f"ag{i}", f"ag{i+1}", "", EDGE + "exitX=1;exitY=0.5;entryX=0;entryY=0.5;"))
    c.append(E("fb", "ag4", "ag0", "对不上就退回重查",
               "edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;dashed=1;strokeWidth=2;strokeColor=#B85450;"
               "fontColor=#B85450;fontSize=15;" + F + "exitX=0.5;exitY=1;entryX=0.5;entryY=1;",
               points=[(1156, 408), (256, 408)]))
    return c

# ---------------- fig3 三专家 + 证据复核闭环 ----------------
def fig3():
    c = []
    blue, green, red = "#6C8EBF", "#82B366", "#B85450"
    for i, t in enumerate(["话术分析员", "资金追踪员", "串并研判员"]):
        c.append(V(f"x{i}", 80 + i * 380, 40, 300, 80, t, BOX + "fillColor=#DAE8FC;strokeColor=" + blue + ";fontStyle=1;"))
    c.append(V("agg", 470, 190, 300, 70, "汇总三方线索", BOX + "fillColor=#F5F5F5;strokeColor=#999999;"))
    c.append(V("dia", 470, 320, 300, 150, "证据对得上吗", "rhombus;whiteSpace=wrap;html=1;fontSize=17;fontStyle=1;" + F + "fillColor=#FFF2CC;strokeColor=#D6B656;"))
    c.append(V("ok", 400, 560, 440, 80, "采纳：出具串并建议\n附完整证据链", BOX + "fillColor=#D5E8D4;strokeColor=" + green + ";fontStyle=1;"))
    c.append(V("rej", 920, 340, 280, 110, "退回相关专家\n重新查证", BOX + "fillColor=#F8CECC;strokeColor=" + red + ";fontColor=#7A2E2A;"))
    c.append(V("man", 60, 340, 280, 110, "反复对不上\n转人工民警判断", BOX + "fillColor=#F5F5F5;strokeColor=#999999;fontColor=#595959;"))
    for i in range(3):
        c.append(E(f"xe{i}", f"x{i}", "agg", "", EDGE + "exitX=0.5;exitY=1;entryX=0.5;entryY=0;"))
    c.append(E("ad", "agg", "dia", "", EDGE + "exitX=0.5;exitY=1;entryX=0.5;entryY=0;"))
    c.append(E("dog", "dia", "ok", "对得上", EDGE + "exitX=0.5;exitY=1;entryX=0.5;entryY=0;fontColor=#4F7A3A;fontStyle=1;"))
    c.append(E("rj", "dia", "rej", "对不上", "edgeStyle=orthogonalEdgeStyle;html=1;rounded=0;dashed=1;strokeWidth=2;strokeColor=" + red + ";fontColor=" + red + ";fontSize=15;" + F + "exitX=1;exitY=0.5;entryX=0.5;entryY=1;"))
    c.append(E("rb", "rej", "x2", "", "edgeStyle=orthogonalEdgeStyle;html=1;rounded=0;dashed=1;strokeWidth=2;strokeColor=" + red + ";" + F + "exitX=0.5;exitY=0;entryX=1;entryY=0.5;"))
    c.append(E("mn", "dia", "man", "反复不一致", "edgeStyle=orthogonalEdgeStyle;html=1;rounded=0;dashed=1;strokeWidth=2;strokeColor=#999999;fontColor=#595959;fontSize=15;" + F + "exitX=0;exitY=0.5;entryX=0.5;entryY=0;"))
    return c

# ---------------- fig4 异构关系网 ----------------
def fig4():
    c = []
    blue, green, orange, gray, red = "#6C8EBF", "#82B366", "#D79B00", "#999999", "#B85450"
    c.append(V("cA", 60, 80, 510, 380, "", "rounded=1;html=1;fillColor=#F4F8FD;strokeColor=" + blue + ";dashed=1;"))
    c.append(V("cB", 580, 140, 400, 300, "", "rounded=1;html=1;fillColor=#F6FBF5;strokeColor=" + green + ";dashed=1;"))
    c.append(V("tA", 75, 90, 300, 30, "自动圈出 · 疑似团伙A", TXT + "fontStyle=1;fontSize=16;fontColor=#2F5B8F;"))
    # tB 右移到 x=680：灰色 e9(同城→案件4) 在文字带 y150-180 处 x≈645-657，
    # 标题从 680 起排可完全避开连线
    c.append(V("tB", 680, 150, 290, 30, "自动圈出 · 疑似团伙B", TXT + "fontStyle=1;fontSize=16;fontColor=#4F7A3A;"))
    cs = "whiteSpace=wrap;html=1;fontSize=16;" + F + "fillColor=#FFFFFF;strokeColor="
    c.append(V("a1", 110, 160, 100, 60, "案件1", cs + blue + ";"))
    c.append(V("a2", 250, 150, 100, 60, "案件2", cs + blue + ";"))
    c.append(V("a3", 150, 290, 100, 60, "案件3", cs + blue + ";"))
    c.append(V("acc", 330, 250, 130, 70, "共享账户", "ellipse;whiteSpace=wrap;html=1;fontSize=16;" + F + "fillColor=#FFFFFF;strokeColor=" + blue + ";"))
    # 注：scr 原 x=320 与 a2(260,130,100,60) 重叠，右移至 390（cA 同步加宽到 510）
    c.append(V("scr", 390, 130, 140, 70, "同一话术", "rhombus;whiteSpace=wrap;html=1;fontSize=16;" + F + "fillColor=#FFF2CC;strokeColor=" + orange + ";"))
    c.append(V("b1", 630, 200, 100, 60, "案件4", cs + green + ";"))
    c.append(V("b2", 790, 300, 100, 60, "案件5", cs + green + ";"))
    c.append(V("ph", 640, 350, 130, 70, "来电号码", "ellipse;whiteSpace=wrap;html=1;fontSize=16;" + F + "fillColor=#FFFFFF;strokeColor=" + green + ";"))
    c.append(V("city", 470, 30, 140, 70, "同城", "shape=hexagon;perimeter=hexagonPerimeter2;whiteSpace=wrap;html=1;fontSize=16;" + F + "fillColor=#F5F5F5;strokeColor=" + gray + ";"))
    c.append(V("iso", 1080, 300, 100, 60, "案件6", cs + gray + ";fontColor=#595959;"))
    ce = "endArrow=none;html=1;strokeWidth=2;" + F
    # e1 起点下移到 a1 右缘中下，从 a2 底缘下方穿过（间隙约 6px）
    c.append(L("e1", 210, 200, 400, 270, ce + "strokeColor=" + blue + ";"))
    c.append(L("e2", 350, 210, 430, 250, ce + "strokeColor=" + blue + ";"))
    c.append(L("e3", 250, 320, 330, 295, ce + "strokeColor=" + blue + ";"))
    # e4 从 a1 右下角出发，沿 a2 底缘下方（间隙约 12px）接到菱形底点
    c.append(L("e4", 210, 225, 460, 200, ce + "strokeColor=" + orange + ";"))
    c.append(L("e5", 350, 165, 388, 165, ce + "strokeColor=" + orange + ";"))
    c.append(L("e6", 730, 235, 840, 320, ce + "strokeColor=" + green + ";"))
    c.append(L("e7", 700, 260, 690, 350, ce + "strokeColor=" + green + ";"))
    # e8 改接案件1顶缘中点，走线从 a2 上方 20px 间隙通过，不再擦角
    c.append(L("e8", 470, 60, 150, 160, ce + "strokeColor=#CCCCCC;"))
    c.append(L("e9", 610, 65, 665, 200, ce + "strokeColor=#CCCCCC;"))
    c.append(L("e10", 890, 330, 1080, 330, ce + "strokeColor=" + red + ";dashed=1;"))
    c.append(V("note", 900, 240, 280, 50, "只有一条弱关联\n孤证不并", TXT + "fontSize=16;fontStyle=1;fontColor=" + red + ";"))
    c.append(band("lg", 60, 560, 1140, 90, "#FAFAFA", "#D9D9D9"))
    c.append(V("s1", 90, 592, 26, 26, "", cs + blue + ";"))
    c.append(V("t1", 126, 590, 90, 30, "案件", TXT))
    c.append(V("s2", 260, 588, 40, 34, "", "ellipse;html=1;fillColor=#FFFFFF;strokeColor=" + green + ";"))
    c.append(V("t2", 310, 590, 160, 30, "账户 / 号码", TXT))
    c.append(V("s3", 500, 588, 40, 34, "", "rhombus;html=1;fillColor=#FFF2CC;strokeColor=" + orange + ";"))
    c.append(V("t3", 550, 590, 130, 30, "话术类型", TXT))
    c.append(L("s4", 710, 605, 770, 605, ce + "strokeColor=" + red + ";dashed=1;"))
    c.append(V("t4", 780, 590, 280, 30, "弱关联（不采信为并案依据）", TXT + "fontColor=#595959;"))
    return c

# ---------------- fig5 共识锚点 + 门控 ----------------
def fig5():
    c = []
    blue, gold, red = "#6C8EBF", "#D6B656", "#B85450"
    c.append(V("root", 500, 40, 350, 70, "同一批零散案件", BOX + "fillColor=#F5F5F5;strokeColor=#999999;"))
    c.append(V("f1", 240, 170, 300, 80, "按资金往来\n分堆", BOX + "fillColor=#DAE8FC;strokeColor=" + blue + ";fontStyle=1;"))
    c.append(V("f2", 810, 170, 300, 80, "按话术风格\n分堆", BOX + "fillColor=#DAE8FC;strokeColor=" + blue + ";fontStyle=1;"))
    c.append(V("dia", 555, 300, 340, 150, "两路分的一致吗", "rhombus;whiteSpace=wrap;html=1;fontSize=17;fontStyle=1;" + F + "fillColor=#FFF2CC;strokeColor=" + gold + ";"))
    c.append(V("anch", 530, 510, 390, 70, "一致的部分：高置信锚点", BOX + "fillColor=#FFF2CC;strokeColor=" + gold + ";fontStyle=1;"))
    c.append(V("learn", 530, 615, 390, 70, "图网络照着锚点学习", BOX + "fillColor=#D5E8D4;strokeColor=#82B366;"))
    c.append(V("appl", 530, 720, 390, 70, "把结论推广到全部案件", BOX + "fillColor=#D5E8D4;strokeColor=#82B366;"))
    c.append(V("drop", 1010, 330, 300, 90, "不一致的分堆\n直接舍弃", BOX + "fillColor=#F8CECC;strokeColor=" + red + ";fontColor=#7A2E2A;"))
    c.append(band("safe", 60, 500, 400, 290, "#FBEAE9", red))
    c.append(V("sh", 80, 512, 360, 34, "三道保险 · 宁缺毋滥", TXT + "fontStyle=1;fontSize=18;fontColor=" + red + ";"))
    c.append(V("s1t", 80, 556, 370, 100,
               "① 只剩一个案件的“堆”：不采信\n② 一堆超过四分之一：整堆弃用\n③ 共识太少：本轮拒绝出结论",
               TXT + "fontSize=16;fontColor=#7A2E2A;align=left;spacingLeft=6;"))
    c.append(E("r1", "root", "f1", "", EDGE + "exitX=0.25;exitY=1;entryX=0.5;entryY=0;"))
    c.append(E("r2", "root", "f2", "", EDGE + "exitX=0.75;exitY=1;entryX=0.5;entryY=0;"))
    c.append(E("d1", "f1", "dia", "", EDGE + "exitX=0.5;exitY=1;entryX=0.35;entryY=0.35;"))
    c.append(E("d2", "f2", "dia", "", EDGE + "exitX=0.5;exitY=1;entryX=0.65;entryY=0.35;"))
    c.append(E("y1", "dia", "anch", "一致", EDGE + "exitX=0.5;exitY=1;entryX=0.5;entryY=0;fontColor=#4F7A3A;fontStyle=1;"))
    c.append(E("l1", "anch", "learn", "", EDGE + "exitX=0.5;exitY=1;entryX=0.5;entryY=0;"))
    c.append(E("l2", "learn", "appl", "", EDGE + "exitX=0.5;exitY=1;entryX=0.5;entryY=0;"))
    c.append(E("n1", "dia", "drop", "不一致", "edgeStyle=orthogonalEdgeStyle;html=1;rounded=0;dashed=1;strokeWidth=2;strokeColor=" + red + ";fontColor=" + red + ";fontSize=15;" + F + "exitX=1;exitY=0.5;entryX=0;entryY=0.5;"))
    return c

# ---------------- fig6 柱状对比 ----------------
def fig6():
    c = []
    base, scale = 520, 400
    names = ["纯文本聚类", "单一资金规则", "自学习图网络", "纯图网络模型", "按图索诈\n（本系统）"]
    vals = [0.50, 0.82, 0.57, 0.89, 0.95]
    fills = ["#BFBFBF", "#A6A6A6", "#999999", "#808080", "#B85450"]
    c.append(L("ax", 90, 100, 90, base, "endArrow=none;html=1;strokeWidth=2;strokeColor=#333333;"))
    c.append(L("ay", 90, base, 1160, base, "endArrow=none;html=1;strokeWidth=2;strokeColor=#333333;"))
    for gv in (0.5, 1.0):
        y = int(base - gv * scale)
        c.append(L("g" + str(gv), 90, y, 1160, y, "endArrow=none;html=1;strokeWidth=1;strokeColor=#E0E0E0;dashed=1;"))
        c.append(V("gl" + str(gv), 20, y - 15, 60, 30, str(gv), TXT + "align=right;fontSize=15;fontColor=#595959;"))
    c.append(V("yttl", 14, 240, 220, 30, "分组正确率（满分1）", "text;html=1;horizontal=0;fontSize=16;fontColor=#333333;" + F))
    for i, (n, v, f) in enumerate(zip(names, vals, fills)):
        x = 140 + i * 210
        h = int(v * scale)
        y = base - h
        c.append(V("bar%d" % i, x, y, 160, h, "", "html=1;fillColor=" + f + ";strokeColor=none;"))
        lab = "0.95 ★" if i == 4 else "%.2f" % v
        col = f if i == 4 else "#333333"
        c.append(V("vl%d" % i, x - 20, y - 40, 200, 32, lab, TXT + "align=center;fontSize=20;fontStyle=1;fontColor=" + col + ";"))
        ncol = "#B85450;fontStyle=1;" if i == 4 else "#333333;"
        c.append(V("nm%d" % i, x - 25, base + 12, 210, 66, n, TXT + "align=center;fontSize=16;fontColor=" + ncol))
    return c

# ---------------- fig7 定位象限 ----------------
def fig7():
    c = []
    gray, green = "#999999", "#82B366"
    c.append(L("hx", 90, 430, 1090, 430, "endArrow=classic;html=1;strokeWidth=2;strokeColor=#333333;"))
    # 注：竖直边按向下方向画、箭头放起点，视觉等价（规避导出边角情况）
    c.append(L("vy", 570, 50, 570, 790, "startArrow=classic;startFill=1;endArrow=none;html=1;strokeWidth=2;strokeColor=#333333;"))
    c.append(V("al", 80, 442, 220, 30, "通用情报大平台", TXT + "fontSize=16;fontColor=#595959;"))
    c.append(V("ar", 890, 442, 200, 30, "反诈一线专用", TXT + "fontSize=16;fontColor=#595959;align=right;"))
    # 注：id 不能叫 "at"——draw.io CLI 导出对 id="at" 报 Export failed（保留字级冲突）
    c.append(V("atop", 585, 52, 160, 30, "事前预警", TXT + "fontSize=16;fontColor=#595959;"))
    c.append(V("ab", 585, 752, 220, 30, "案发后串并研判", TXT + "fontSize=16;fontColor=#595959;"))
    pill = "rounded=1;arcSize=40;whiteSpace=wrap;html=1;fontSize=16;fillColor=#F0F0F0;strokeColor=" + gray + ";fontColor=#595959;"
    c.append(V("q1", 170, 160, 280, 60, "金融风控平台（同盾）", pill))
    c.append(V("q2", 680, 160, 280, 60, "银行 / 运营商预警", pill))
    c.append(V("q3", 130, 300, 280, 60, "通用知识图谱平台", pill))
    c.append(V("q4", 170, 580, 280, 60, "电子取证平台（美亚）", pill))
    c.append(V("me", 700, 560, 330, 100, "★ 按图索诈\n案发后 · 一线反诈专用", "rounded=1;arcSize=20;whiteSpace=wrap;html=1;" + F + "fillColor=#D5E8D4;strokeColor=" + green + ";fontStyle=1;fontSize=18;"))
    return c

# ---------------- fig8 路线图 ----------------
def fig8():
    c = []
    green, blue, gray = "#82B366", "#6C8EBF", "#999999"
    c.append(L("tl", 80, 270, 1390, 270, "endArrow=classic;html=1;strokeWidth=3;strokeColor=#666666;"))
    nodes = [("n1", 250, green), ("n2", 710, blue), ("n3", 1170, gray)]
    for nid, x, col in nodes:
        c.append(V(nid, x - 18, 252, 36, 36, "", "ellipse;html=1;fillColor=" + col + ";strokeColor=none;"))
    cards = [
        ("cd1", 80, 60, 380, 150, "#EEF7EC", green, "已完成", "全流程系统可运行\n真实难度数据验证\n本地私有化部署"),
        ("cd2", 520, 340, 380, 150, "#EBF2FB", blue, "进行中", "一线民警试点试用\n反诈中心走访调研\n专利申请跟进"),
        ("cd3", 980, 60, 360, 150, "#F5F5F5", gray, "下一步", "推广更多县市验证\n接入更多线索类型\n沉淀一线打法规范"),
    ]
    for cid, x, y, w, h, fill, stroke, head, body in cards:
        c.append(V(cid, x, y, w, h, "", "rounded=1;html=1;fillColor=" + fill + ";strokeColor=" + stroke + ";"))
        c.append(V(cid + "h", x + 16, y + 12, 200, 34, head, TXT + "fontStyle=1;fontSize=19;fontColor=" + stroke + ";"))
        c.append(V(cid + "b", x + 16, y + 52, w - 32, 92, body, TXT + "fontSize=16;align=left;fontColor=#333333;"))
    c.append(E("c1", "n1", "cd1", "", "endArrow=none;html=1;dashed=1;strokeColor=#BFBFBF;" + F + "exitX=0.5;exitY=0;entryX=0.5;entryY=1;"))
    c.append(E("c2", "n2", "cd2", "", "endArrow=none;html=1;dashed=1;strokeColor=#BFBFBF;" + F + "exitX=0.5;exitY=1;entryX=0.5;entryY=0;"))
    c.append(E("c3", "n3", "cd3", "", "endArrow=none;html=1;dashed=1;strokeColor=#BFBFBF;" + F + "exitX=0.5;exitY=0;entryX=0.45;entryY=1;"))
    return c

figs = {
    "fig2_arch": fig2(),
    "fig3_loop": fig3(),
    "fig4_graph": fig4(),
    "fig5_semi": fig5(),
    "fig6_bars": fig6(),
    "fig7_quadrant": fig7(),
    "fig8_roadmap": fig8(),
}
for name, cells in figs.items():
    path = os.path.join(OUT, name + ".drawio")
    with open(path, "w", encoding="utf-8") as f:
        f.write(diagram(name, cells))
    print("written", path)
print("OK")
