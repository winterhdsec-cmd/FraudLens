# -*- coding: utf-8 -*-
"""生成项目计划书配图（5 张）：白底深色字、公安蓝青色系、中文清晰。"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Circle
import numpy as np

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Noto Sans SC"]
plt.rcParams["axes.unicode_minus"] = False

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "plan_figures")
os.makedirs(OUT, exist_ok=True)

# 配色（公安蓝 + 青 + 警示橙红）
C_BLUE = "#1e5aa8"
C_CYAN = "#0e9aa7"
C_DARK = "#2b3a4a"
C_TEXT = "#333333"
C_ORANGE = "#e8833a"
C_RED = "#d64545"
C_GREEN = "#2e9e6b"
C_BG = "#f7fafc"
C_GRID = "#d5dee6"

BOX = dict(boxstyle="round,pad=0.35,rounding_size=0.12", linewidth=1.5)


def _new_ax(w=10, h=5.2):
    fig, ax = plt.subplots(figsize=(w, h), dpi=200)
    ax.set_xlim(0, w); ax.set_ylim(0, h)
    ax.axis("off")
    fig.patch.set_facecolor("white")
    return fig, ax


def _box(ax, x, y, w, h, text, fc="#eaf2fb", ec=C_BLUE, fs=12, bold=False, sub=None, subfs=9):
    p = FancyBboxPatch((x, y), w, h, **BOX,
                       fc=fc, ec=ec, mutation_aspect=1.0)
    ax.add_patch(p)
    ax.text(x + w / 2, y + h / 2 + (0.16 if sub else 0), text,
            ha="center", va="center", fontsize=fs, color=C_TEXT, fontweight="bold" if bold else "normal")
    if sub:
        ax.text(x + w / 2, y + h / 2 - 0.34, sub, ha="center", va="center",
                fontsize=subfs, color="#5a6b7a")


def _arrow(ax, x1, y1, x2, y2, color=C_BLUE, lw=2.2):
    a = FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=16,
                        color=color, lw=lw, shrinkA=0, shrinkB=0)
    ax.add_patch(a)


# ============================================================
# 图1：系统工作流程总览（项目简介用）
# ============================================================
fig, ax = _new_ax(11.5, 4.6)
steps = [
    ("线索上传", "话术文本 · CSV\n截图 · 笔录"),
    ("多智能体分析", "话术 / 资金 / 线索\n交叉智能研判"),
    ("关系网构建", "案件与手机号、账户、\n受害者等自动关联"),
    ("团伙发现", "图神经网络自动发现\n抱团作案案件"),
    ("预警处置", "串并案线索 · 风险预警\n一键派单"),
]
bx, by, bw, bh = 0.25, 1.5, 2.0, 1.7
for i, (t, s) in enumerate(steps):
    x = bx + i * (bw + 0.32)
    fc = "#eaf2fb" if i != 3 else "#fff4e5"
    ec = C_BLUE if i != 3 else C_ORANGE
    _box(ax, x, by, bw, bh, t, fc=fc, ec=ec, fs=13, bold=True, sub=s, subfs=9)
    if i < 4:
        _arrow(ax, x + bw + 0.02, by + bh / 2, x + bw + 0.30, by + bh / 2)
# 顶部标题条
ax.add_patch(FancyBboxPatch((0.25, 3.85), 11.0, 0.55, **BOX, fc="#1e5aa8", ec="#1e5aa8"))
ax.text(5.75, 4.125, "FraudLens 反诈智能研判系统 · 一站式工作流程",
        ha="center", va="center", fontsize=14, color="white", fontweight="bold")
# 底部说明
ax.text(5.75, 0.75, "民警只需录入一条线索，系统自动完成从个案到团伙的关联研判，全程本地化处理、保障公民个人信息安全",
        ha="center", va="center", fontsize=10.5, color="#5a6b7a")
plt.tight_layout()
plt.savefig(os.path.join(OUT, "fig1_workflow.png"), bbox_inches="tight", facecolor="white")
plt.close()

# ============================================================
# 图2：反诈现状痛点对比（项目背景用）
# ============================================================
fig, ax = _new_ax(11.5, 4.9)
# 左：传统方式
ax.text(1.3, 4.35, "传统研判方式", ha="center", fontsize=14, fontweight="bold", color="#8a5a3a")
ax.add_patch(FancyBboxPatch((0.3, 0.4), 5.0, 3.7, **BOX, fc="#fbf3ea", ec="#d9b28a"))
left = ["个案孤立、逐案侦查", "依赖民警个人经验", "团伙更换账号难识破", "话术千变万化难比对"]
ly = 3.3
for t in left:
    ax.add_patch(Circle((0.75, ly), 0.14, fc="#e0a56d", ec="none"))
    ax.text(0.75, ly, "×", ha="center", va="center", fontsize=12, color="white", fontweight="bold")
    ax.text(1.05, ly, t, ha="left", va="center", fontsize=12, color=C_TEXT)
    ly -= 0.72

# 右：本方案
ax.text(8.2, 4.35, "FraudLens 智能研判", ha="center", fontsize=14, fontweight="bold", color=C_BLUE)
ax.add_patch(FancyBboxPatch((6.2, 0.4), 5.0, 3.7, **BOX, fc="#eaf2fb", ec="#8fb3dd"))
right = ["案件自动关联成网", "多智能体交叉印证", "换号换账户也能串并", "话术语义智能比对"]
ry = 3.3
for t in right:
    ax.add_patch(Circle((6.65, ry), 0.14, fc=C_GREEN, ec="none"))
    ax.text(6.65, ry, "√", ha="center", va="center", fontsize=12, color="white", fontweight="bold")
    ax.text(6.95, ry, t, ha="left", va="center", fontsize=12, color=C_TEXT)
    ry -= 0.72

# 中间对比箭头
_arrow(ax, 5.35, 2.4, 6.15, 2.4, color="#8a5a3a", lw=2.5)
ax.text(5.75, 2.05, "vs", ha="center", va="center", fontsize=13, fontweight="bold", color="#8a5a3a")
plt.tight_layout()
plt.savefig(os.path.join(OUT, "fig2_painpoint.png"), bbox_inches="tight", facecolor="white")
plt.close()

# ============================================================
# 图3：多智能体分工协作（项目主要内容用）
# ============================================================
fig, ax = _new_ax(11.5, 6.4)
# 输入层
ax.text(5.75, 5.95, "输入层", fontsize=12, fontweight="bold", color=C_DARK)
ax.add_patch(FancyBboxPatch((0.8, 5.25), 9.9, 0.75, **BOX, fc="#eef6f1", ec=C_GREEN))
ax.text(5.75, 5.62, "诈骗线索输入：话术文本 · CSV 案件数据 · 截图/图片（全程本地处理）",
        ha="center", va="center", fontsize=12, color=C_TEXT)

# 分析层（三个智能体）
ax.text(5.75, 4.62, "分析层 · 专业分工", fontsize=12, fontweight="bold", color=C_DARK)
agents = [
    ("线索识别智能体", "提取手机号、账户、受害者、诈骗类型等关键要素"),
    ("话术分析智能体", "语义比对话术模板，识别引流、实施、洗钱套路"),
    ("资金链分析智能体", "追踪资金往来，发现账户共享与转账链条"),
]
aw = 3.0; ah = 1.15; ax0 = 0.8
for i, (t, s) in enumerate(agents):
    x = ax0 + i * (aw + 0.45)
    _box(ax, x, 3.35, aw, ah, t, fc="#eaf2fb", ec=C_BLUE, fs=12, bold=True, sub=s, subfs=8.6)

# 协作层
ax.text(5.75, 2.62, "协作层 · 反思校验", fontsize=12, fontweight="bold", color=C_DARK)
ax.add_patch(FancyBboxPatch((0.8, 1.55), 9.9, 1.0, **BOX, fc="#fff4e5", ec=C_ORANGE))
ax.text(5.75, 2.05, "团伙画像智能体 + 反思校验智能体：多智能体交叉印证、自我纠错，", ha="center", va="center", fontsize=12, color=C_TEXT)
ax.text(5.75, 1.78, "对低置信度的研判结果果断拒出牌，宁可少报、不可错报", ha="center", va="center", fontsize=10.5, color="#a05c20")

# 输出层
ax.text(5.75, 1.05, "输出层", fontsize=12, fontweight="bold", color=C_DARK)
ax.add_patch(FancyBboxPatch((0.8, 0.3), 9.9, 0.75, **BOX, fc="#fdf0f0", ec=C_RED))
ax.text(5.75, 0.675, "团伙画像 · 串并案建议 · 风险预警 · 一键派单",
        ha="center", va="center", fontsize=12, color=C_TEXT, fontweight="bold")

# 层间箭头
_arrow(ax, 5.75, 5.22, 5.75, 4.62, color="#9fb6cc")
_arrow(ax, 5.75, 3.32, 5.75, 2.62, color="#9fb6cc")
_arrow(ax, 5.75, 1.52, 5.75, 1.05, color="#9fb6cc")
# 分析层向上分支到协作层
for x in [1.55, 5.75, 9.95]:
    _arrow(ax, x, 3.32, x, 2.62, color="#c9d6e4", lw=1.6)
plt.tight_layout()
plt.savefig(os.path.join(OUT, "fig3_agents.png"), bbox_inches="tight", facecolor="white")
plt.close()

# ============================================================
# 图4：异构图关系网示意（项目主要内容用）
# ============================================================
fig, ax = _new_ax(11.5, 6.0)
ax.set_xlim(0, 11.5); ax.set_ylim(0, 6.0)

# 案件节点（两个团伙，各 3 个案件）
gangA_cases = [(2.0, 4.6), (3.0, 3.6), (1.4, 3.3)]
gangB_cases = [(8.2, 4.4), (9.4, 3.6), (8.6, 2.9)]
# 实体节点
accountA = (4.3, 4.3)   # 共享账户A
accountB = (7.0, 4.6)   # 共享账户B
phoneA = (2.6, 2.2)     # 共享手机号A
phoneB = (9.2, 2.0)     # 共享手机号B
city = (5.6, 5.2)       # 城市
type_ = (5.2, 1.7)      # 诈骗类型
victim = (6.0, 3.0)     # 受害者

# 团伙圈
ax.add_patch(plt.Circle((2.9, 3.6), 2.05, fc="#eaf2fb", ec="#7aa2d4", ls="--", lw=1.8, alpha=0.55))
ax.add_patch(plt.Circle((8.7, 3.6), 1.95, fc="#eafaf1", ec="#6fc29a", ls="--", lw=1.8, alpha=0.55))
ax.text(1.0, 5.55, "团伙 A：以话术与资金账户双重关联识别", fontsize=10, color="#3a6fb5", fontweight="bold")
ax.text(7.4, 5.55, "团伙 B：共享账户+手机号串并", fontsize=10, color="#2e9e6b", fontweight="bold")

def _node(x, y, label, fc, ec, r=0.34):
    ax.add_patch(Circle((x, y), r, fc=fc, ec=ec, lw=1.5))
    ax.text(x, y, label, ha="center", va="center", fontsize=8.6, color="white", fontweight="bold")

def _edge(p1, p2, color="#b9c6d4", lw=1.4):
    ax.plot([p1[0], p2[0]], [p1[1], p2[1]], color=color, lw=lw, zorder=1)

# 团伙A 案件
for c in gangA_cases:
    _node(*c, "案A", "#1e5aa8", "#1e5aa8")
for c in gangB_cases:
    _node(*c, "案B", "#2e9e6b", "#2e9e6b")
# 实体
_node(*accountA, "账户", "#0e9aa7", "#0e9aa7", 0.30)
_node(*accountB, "账户", "#0e9aa7", "#0e9aa7", 0.30)
_node(*phoneA, "手机号", "#8a6bb5", "#8a6bb5", 0.30)
_node(*phoneB, "手机号", "#8a6bb5", "#8a6bb5", 0.30)
_node(*city, "城市", "#e8833a", "#e8833a", 0.30)
_node(*type_, "诈骗类型", "#d64545", "#d64545", 0.30)
_node(*victim, "受害者", "#e0a56d", "#d98a4a", 0.30)

# 连线（团伙A 共享账户A、手机号A）
for c in gangA_cases:
    _edge(c, accountA); _edge(c, phoneA); _edge(c, city); _edge(c, type_)
for c in gangB_cases:
    _edge(c, accountB); _edge(c, phoneB); _edge(c, city); _edge(c, type_)
_edge(victim, accountA); _edge(victim, accountB)

# 图例
ax.text(1.0, 0.45, "共享资金账户、共享手机号、同城、同类话术——案件被自动串并成团伙",
        fontsize=10.5, color="#5a6b7a")
plt.tight_layout()
plt.savefig(os.path.join(OUT, "fig4_graph.png"), bbox_inches="tight", facecolor="white")
plt.close()

# ============================================================
# 图5：重噪场景效果对比（项目创新点用）——真实实验数据
# ============================================================
fig, ax = _new_ax(9.5, 5.4)
methods = ["传统资金链\n规则方法", "传统聚类\n(KMeans)", "自监督图神经网络\n(无标签监督)", "本方案\n(共识伪标签半监督)"]
f1s = [0.82, 0.50, 0.57, 0.95]
colors = ["#9db4cc", "#9db4cc", "#9db4cc", C_ORANGE]
bars = ax.bar(range(4), f1s, width=0.58, color=colors, edgecolor="#7a8ca0", lw=0.8, zorder=3)
for i, (m, v) in enumerate(zip(methods, f1s)):
    ax.text(i, v + 0.03, f"{v:.2f}", ha="center", va="bottom", fontsize=13, fontweight="bold", color=C_DARK)
ax.set_xticks(range(4))
ax.set_xticklabels(methods, fontsize=10.5, color=C_TEXT)
ax.set_ylim(0, 1.15)
ax.set_ylabel("团伙识别效果（F1 分数）", fontsize=11, color=C_TEXT)
ax.set_title("高干扰（重噪）案件数据下的团伙识别效果对比", fontsize=14, fontweight="bold", color=C_DARK, pad=14)
ax.spines[["top", "right"]].set_visible(False)
ax.grid(axis="y", color=C_GRID, lw=0.8, zorder=0)
ax.set_facecolor("white")
# 图注
ax.text(4.75, -0.20, "注：真实警情数据常带噪声与干扰，本方案在最难的重噪场景仍保持 0.95 的高识别率（3 次重复实验均值）",
        ha="center", va="top", fontsize=9.5, color="#5a6b7a")
plt.tight_layout()
plt.savefig(os.path.join(OUT, "fig5_result.png"), bbox_inches="tight", facecolor="white")
plt.close()

# ============================================================
# 图6：团队分工（项目组介绍用）
# ============================================================
fig, ax = _new_ax(10.5, 4.4)
ax.add_patch(FancyBboxPatch((0.4, 3.35), 9.7, 0.8, **BOX, fc="#1e5aa8", ec="#1e5aa8"))
ax.text(5.25, 3.75, "项目团队 · 湖北警官学院信息安全专业本科生（多专业能力互补）",
        ha="center", va="center", fontsize=12.5, color="white", fontweight="bold")
roles = [
    ("算法与模型", "机器学习 · 图神经网络\n半监督学习 · 多智能体"),
    ("系统开发", "前后端开发 · 数据可视化\n接口设计与部署"),
    ("调研与验证", "反诈一线需求调研\n实验设计与数据分析"),
    ("文档与统筹", "方案撰写 · 进度管理\n资源协调"),
]
rw, rh = 2.25, 1.55; x0 = 0.4
for i, (t, s) in enumerate(roles):
    x = x0 + i * (rw + 0.15)
    _box(ax, x, 1.05, rw, rh, t, fc="#eaf2fb", ec=C_BLUE, fs=12, bold=True, sub=s, subfs=8.6)
ax.text(5.25, 0.5, "团队既懂技术实现，又深入反诈一线调研，保证系统做得出来、用得上",
        ha="center", va="center", fontsize=10.5, color="#5a6b7a")
plt.tight_layout()
plt.savefig(os.path.join(OUT, "fig6_team.png"), bbox_inches="tight", facecolor="white")
plt.close()

# ============================================================
# 图7：发展前景三阶段路线（项目研究前景用）
# ============================================================
fig, ax = _new_ax(11.5, 4.2)
stages = [
    ("近期 · 试点验证", "对接反诈中心真实警情，\n在实际数据上验证与迭代", "#2e9e6b"),
    ("中期 · 深化拓展", "覆盖引流/实施/洗钱全链条画像，\n支持跨区域协查", C_BLUE),
    ("远期 · 推广应用", "形成标准化智能串并案工具，\n服务反诈一线民警", C_ORANGE),
]
sw, sh = 3.3, 2.2; x0 = 0.35
for i, (t, s, c) in enumerate(stages):
    x = x0 + i * (sw + 0.3)
    ax.add_patch(FancyBboxPatch((x, 1.5), sw, sh, **BOX, fc="#f6f9fc", ec=c))
    ax.add_patch(FancyBboxPatch((x, 3.2), sw, 0.5, **BOX, fc=c, ec=c))
    ax.text(x + sw / 2, 3.45, t, ha="center", va="center", fontsize=12, color="white", fontweight="bold")
    ax.text(x + sw / 2, 2.6, s, ha="center", va="center", fontsize=10, color=C_TEXT)
    if i < 2:
        _arrow(ax, x + sw + 0.05, 2.6, x + sw + 0.25, 2.6, color="#9fb6cc", lw=2.2)
ax.text(5.75, 0.6, "三步走路径清晰：先在真实一线验证价值，再逐步深化、规模推广",
        ha="center", va="center", fontsize=10.5, color="#5a6b7a")
plt.tight_layout()
plt.savefig(os.path.join(OUT, "fig7_future.png"), bbox_inches="tight", facecolor="white")
plt.close()

print("DONE:", [f for f in os.listdir(OUT)])
