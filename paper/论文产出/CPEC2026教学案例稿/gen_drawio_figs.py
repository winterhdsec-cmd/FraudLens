# -*- coding: utf-8 -*-
"""生成 FraudLens 论文三张科研图的 draw.io XML（.drawio）。
坐标由程序计算，统一美观标准：
  方正矩形 + 浅灰 panel + 灰色标题栏 + 白节点 + 黑细边框 + 黑色箭头 + 虚线反馈环。
所有节点文字为单行（XML 合法，draw.io 按 whiteSpace=wrap 自动折行），避免 <br> 导致的解析问题。
"""
import os
import xml.sax.saxutils as su
from xml.dom import minidom

OUT_DIR = r"E:/FraudLens/paper/论文产出/CPEC2026教学案例稿"

# ---- 调色板（学术黑白灰 + 浅蓝灰内核）----
C_PANEL = "#f0f2f5"
C_PANEL_TITLE = "#cdd3dc"
C_CORE = "#e3e9f2"
C_CORE_TITLE = "#aebfd4"
C_NODE = "#ffffff"
C_BAR = "#eef1f5"
C_EDGE = "#333333"
FONT = "Microsoft YaHei"


class G:
    def __init__(self):
        self.cells = []
        self._n = 0

    def _id(self):
        self._n += 1
        return f"c{self._n}"

    @staticmethod
    def _esc(text):
        return su.escape(text)

    def panel(self, x, y, w, h, title, core=False):
        fill = C_CORE if core else C_PANEL
        tfill = C_CORE_TITLE if core else C_PANEL_TITLE
        pid = self._id()
        self.cells.append(
            f'<mxCell id="{pid}" value="" style="rounded=0;whiteSpace=wrap;html=1;fillColor={fill};strokeColor={C_EDGE};strokeWidth=1.5;" vertex="1" parent="1"><mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>')
        tid = self._id()
        self.cells.append(
            f'<mxCell id="{tid}" value="{self._esc(title)}" style="rounded=0;whiteSpace=wrap;html=1;fillColor={tfill};strokeColor={C_EDGE};strokeWidth=1;fontSize=13;fontStyle=1;fontFamily={FONT};align=center;verticalAlign=middle;" vertex="1" parent="1"><mxGeometry x="{x}" y="{y}" width="{w}" height="26" as="geometry"/></mxCell>')
        return pid

    def node(self, x, y, w, h, text, fill=C_NODE, fontSize=10, bold=False):
        fs = "1" if bold else "0"
        nid = self._id()
        self.cells.append(
            f'<mxCell id="{nid}" value="{self._esc(text)}" style="rounded=0;whiteSpace=wrap;html=1;fillColor={fill};strokeColor={C_EDGE};strokeWidth=1;fontSize={fontSize};fontStyle={fs};fontFamily={FONT};align=center;verticalAlign=middle;" vertex="1" parent="1"><mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>')
        return nid

    def diamond(self, x, y, w, h, text, fontSize=10):
        did = self._id()
        self.cells.append(
            f'<mxCell id="{did}" value="{self._esc(text)}" style="rhombus;whiteSpace=wrap;html=1;fillColor={C_NODE};strokeColor={C_EDGE};strokeWidth=1;fontSize={fontSize};fontFamily={FONT};align=center;verticalAlign=middle;" vertex="1" parent="1"><mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>')
        return did

    def bar(self, x, y, w, h, text, fontSize=10):
        bid = self._id()
        self.cells.append(
            f'<mxCell id="{bid}" value="{self._esc(text)}" style="rounded=0;whiteSpace=wrap;html=1;fillColor={C_BAR};strokeColor={C_EDGE};strokeWidth=1.5;fontSize={fontSize};fontStyle=1;fontFamily={FONT};align=center;verticalAlign=middle;" vertex="1" parent="1"><mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>')
        return bid

    def caption(self, x, y, w, text, fontSize=13):
        cid = self._id()
        self.cells.append(
            f'<mxCell id="{cid}" value="{self._esc(text)}" style="text;html=1;strokeColor=none;fontSize={fontSize};fontStyle=1;fontFamily={FONT};align=center;verticalAlign=middle;" vertex="1" parent="1"><mxGeometry x="{x}" y="{y}" width="{w}" height="22" as="geometry"/></mxCell>')
        return cid

    def edge(self, src, dst, label="", dashed=False, waypoints=None):
        eid = self._id()
        d = "dashed=1;" if dashed else ""
        lab = f'value="{self._esc(label)}"' if label else 'value=""'
        srcattr = f' source="{src}"' if src else ''
        dstattr = f' target="{dst}"' if dst else ''
        if waypoints:
            pts = "".join(f'<mxPoint x="{px}" y="{py}"/>' for px, py in waypoints)
            wp = f'<mxGeometry relative="1" as="geometry"><Array as="points">{pts}</Array></mxGeometry>'
        else:
            wp = f'<mxGeometry relative="1" as="geometry"/>'
        self.cells.append(
            f'<mxCell id="{eid}" {lab} style="edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;endArrow=block;{d}strokeColor={C_EDGE};fontSize=10;fontFamily={FONT};" edge="1" parent="1"{srcattr}{dstattr}>{wp}</mxCell>')
        return eid

    def to_xml(self):
        body = "\n    ".join(self.cells)
        return (f'<mxGraphModel dx="1000" dy="700" grid="1" gridSize="10" guides="1" '
                f'tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" '
                f'pageWidth="900" pageHeight="650" math="0" shadow="0">\n  <root>\n    '
                f'<mxCell id="0"/>\n    <mxCell id="1" parent="0"/>\n    {body}\n  </root>\n</mxGraphModel>')


# ===================== 图2：工作流图（三列 panel + 审计条 + 反馈环）=====================
def build_fig2():
    g = G()
    PW, PH, TH = 120, 300, 26
    xs = [20, 160, 300]
    titles = ["阶段1 学情/案情输入", "阶段2 FraudLens 系统内核", "阶段3 人机协同决策"]
    for i, x in enumerate(xs):
        g.panel(x, 60, PW, PH, titles[i], core=(i == 1))

    NW, NH, GAP, NY0 = 104, 76, 14, 60 + TH + 10  # 96
    labels = [
        ["选择实验 Lab（1–4）", "提交案情 / 启动研判", "失败场景诚实反思"],
        ["预处理：案情清洗 / 字段对齐",
         "BGE 嵌入 + HAN 构图（语义通道 / 结构通道）",
         "LangGraph 反思闭环：plan→preprocess→analyze→cluster→reflect"],
        ["规则 vs AI 建议对比（Lab1 / Lab2）",
         "冻卡决策与伦理权衡（Lab3）",
         "边界认知与诚实反思（Lab4）"],
    ]
    nodes = [[], [], []]
    for i, x in enumerate(xs):
        nx = x + (PW - NW) / 2
        for j in range(3):
            ny = NY0 + j * (NH + GAP)
            nid = g.node(nx, ny, NW, NH, labels[i][j], fontSize=9.5)
            nodes[i].append(nid)
            if j > 0:
                g.edge(nodes[i][j - 1], nid)

    g.edge(nodes[0][2], nodes[1][2], "案情输入")
    g.edge(nodes[1][2], nodes[2][2], "候选结果")

    bar = g.bar(20, 380, 400, 40,
                "审计日志 → 加权评价量表 + 思政 / 伦理映射 → 回流（研—训—评）", fontSize=10)
    g.edge(nodes[2][2], bar, "决策记录")

    n1x = xs[0] + (PW - NW) / 2
    n1y = NY0 + 2 * (NH + GAP)
    g.edge(None, None, "评价 / 反思回流", dashed=True,
           waypoints=[(20, 400), (20, 442), (n1x - 18, 442), (n1x - 18, n1y + NH / 2)])

    g.caption(20, 448, 400, "图2 FraudLens 反诈研判教学工作流图")
    return g.to_xml()


# ===================== 图1：架构图（环绕式仿 LLMDS）=====================
def build_fig1():
    g = G()
    # 中央内核
    CX, CY, CW, CH = 170, 130, 200, 250
    g.panel(CX, CY, CW, CH, "LangGraph 反诈研判内核", core=True)
    NH, GAP, NW = 34, 8, 180
    NX = CX + (CW - NW) / 2
    NY0 = CY + 26 + 12
    core_nodes = ["规划 Plan",
                  "预处理 Preprocess（字段对齐 / 数据脱敏）",
                  "分析 Analyze（结构通道 / 文本通道）",
                  "聚类 Cluster",
                  "反思 Reflect（置信度评估 / 规则触发）"]
    cn = []
    for j, t in enumerate(core_nodes):
        ny = NY0 + j * (NH + GAP)
        nid = g.node(NX, ny, NW, NH, t, fontSize=9.5)
        cn.append(nid)
        if j > 0:
            g.edge(cn[j - 1], nid)
    g.edge(cn[4], cn[0], "置信度低 / 规则触发 → 返回规划", dashed=True)

    # 数据层（上）
    DX, DY, DW, DH = 170, 20, 200, 95
    g.panel(DX, DY, DW, DH, "数据层 / 模型支撑")
    sw, sh, gx, gy = 56, 24, 6, 5
    sx0, sy0 = DX + 8, DY + 26 + 8
    data = ["MySQL（案情库/流水）", "Redis 缓存", "BGE-large 本地嵌入",
            "DeepSeek 云端大模型", "GNN 双通道（GraphSAGE/HAN）"]
    dn = []
    for k, t in enumerate(data):
        r, c = divmod(k, 3)
        dx = sx0 + c * (sw + gx)
        dy = sy0 + r * (sh + gy)
        dn.append(g.node(dx, dy, sw, sh, t, fontSize=8))

    # 交互层（左）
    IX, IY, IW, IH = 20, 130, 130, 250
    g.panel(IX, IY, IW, IH, "交互 / 输入层")
    iw, ih, ig = 114, 44, 8
    ix0, iy0 = IX + 8, IY + 26 + 10
    inter = ["民警研判界面（Vue3+Element Plus）",
             "关系图谱可视化（ECharts+vis-network）", "案情录入", "研判请求发起"]
    inn = []
    for k, t in enumerate(inter):
        iy = iy0 + k * (ih + ig)
        inn.append(g.node(ix0, iy, iw, ih, t, fontSize=9))

    # 应用服务（右）
    AX, AY, AW, AH = 450, 130, 130, 250
    g.panel(AX, AY, AW, AH, "应用服务")
    ax0, ay0 = AX + 8, AY + 26 + 10
    appn = ["候选结果", "规则 vs AI 建议对比", "冻卡决策",
            "人工审核 · 审计日志 · 可视化"]
    ann = []
    for k, t in enumerate(appn):
        ay = ay0 + k * (ih + ig)
        ann.append(g.node(ax0, ay, iw, ih, t, fontSize=9))

    # 决策菱形
    dia = g.diamond(380, 285, 70, 44, "置信度足够？", fontSize=9)
    g.edge(cn[3], dia)
    g.edge(dia, ann[0], "是")
    g.edge(dia, cn[0], "否", dashed=True)

    # 顶部反馈环（虚线）
    g.edge(None, None, "人工审核反馈 Human-in-the-loop", dashed=True,
           waypoints=[(AX + AW / 2, AY), (AX + AW / 2, 12), (IX + IW / 2, 12), (IX + IW / 2, IY)])

    # 底部支撑条
    g.bar(20, 400, 560, 40,
          "工程可信保障：数据不出域 · RBAC 鉴权 · 审计溯源 · 可解释性 · 多级降级", fontSize=10)

    g.caption(20, 450, 560, "图1 FraudLens 反诈研判系统总体架构图")
    return g.to_xml()


# ===================== 图3：AI 赋能反诈教学实践闭环（三角 + 中央闭环 + 边界 panel + 底栏）=====================
def build_fig3():
    g = G()
    # 顶部三角
    stu = g.node(70, 20, 90, 44, "学生（准民警）", fontSize=11, bold=True)
    ta = g.node(200, 10, 130, 56, "FraudLens 智能助教（规划 · BGE · GNN · 反思 Agent）",
                fill=C_CORE, fontSize=9)
    tea = g.node(380, 20, 90, 44, "教师", fontSize=11, bold=True)
    g.edge(stu, ta, "提问 / 获得建议")
    g.edge(ta, tea, "配置任务 / 获取学情")
    g.edge(stu, tea, "反馈 / 评价", dashed=True)

    # 中央大 panel
    CX, CY, CW, CH = 130, 95, 270, 220
    g.panel(CX, CY, CW, CH, "反诈研判实训闭环")
    TH = 26
    lab_w, lab2_w = 75, 90
    lab_h, lab2_h = 54, 44
    cx_mid = CX + (CW - lab2_w) / 2  # 220
    l1 = g.node(CX + 10, CY + TH + 18, lab_w, lab_h,
                "Lab1 情境导入（真实案情库 / 合成数据 AMLSim 1,305 环）", fontSize=8)
    l2 = g.node(cx_mid, CY + TH + 8, lab2_w, lab2_h,
                "Lab2 工具辅助串并案（规则引擎/BGE/HAN/GraphSAGE）", fontSize=8)
    l3 = g.node(CX + CW - lab_w - 10, CY + TH + 18, lab_w, lab_h,
                "Lab3 冻卡决策与伦理权衡", fontSize=8)
    l4 = g.node(cx_mid, CY + CH - lab2_h - 10, lab2_w, lab2_h,
                "Lab4 边界认知与诚实反思", fontSize=8)
    ev = g.node(cx_mid, CY + TH + (CH - TH) / 2 - 19, lab2_w, 38,
                "评价回流（加权评价 + 思政/伦理映射）", fontSize=8)

    g.edge(l1, l2)
    g.edge(l2, l3)
    g.edge(l3, l4)
    g.edge(l4, ev)
    g.edge(ev, l1, "", dashed=True)

    # 右侧边界 panel
    BX, BY, BW, BH = 420, 95, 110, 220
    g.panel(BX, BY, BW, BH, "AI 能力边界（诚实反思）")
    ba = g.node(BX + 8, BY + TH + 10, BW - 16, 88,
                "AI 可辅助：嵌入检索 · 聚类归集 · 生成候选 · 规则对比 · 过程性评价", fontSize=8)
    bb = g.node(BX + 8, BY + TH + 104, BW - 16, 88,
                "AI 不可靠 / 须教师把关：全图判定 · 因果定责 · 最终执法决策 · 伦理责任归属", fontSize=8)
    g.edge(ba, l2, "", dashed=True)
    g.edge(ba, l3, "", dashed=True)
    g.edge(bb, l4, "", dashed=True)

    # 底部育人横条
    g.bar(130, 330, 400, 40,
          "育人目标：算法边界认知 · 伦理决策素养 · 课程思政（科技向善）", fontSize=10)

    g.caption(130, 380, 400, "图3 AI 赋能反诈教学实践闭环")
    return g.to_xml()


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    figs = {
        "fig_arch.drawio": build_fig1(),
        "fig_workflow.drawio": build_fig2(),
        "fig_education_loop.drawio": build_fig3(),
    }
    for name, xml in figs.items():
        path = os.path.join(OUT_DIR, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(xml)
        minidom.parseString(xml)  # 校验 XML 良构
        print(f"OK  {name}: {xml.count('<mxCell')} cells")
    print("ALL DONE")


if __name__ == "__main__":
    main()
