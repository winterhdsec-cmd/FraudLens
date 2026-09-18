# -*- coding: utf-8 -*-
"""生成论文附录配图（学术黑白风格，适合Word嵌入）"""
import sys, os
sys.stdout.reconfigure(encoding="utf-8")
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'SimSun']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['figure.dpi'] = 150

OUT = r'E:\FraudLens\paper\论文产出\技术稿fraudlens_outline\figs'
os.makedirs(OUT, exist_ok=True)

# ============ 图1：系统三层架构 ============
def fig_arch():
    fig, ax = plt.subplots(figsize=(8, 4.2))
    ax.set_xlim(0, 10); ax.set_ylim(0, 6.2); ax.axis('off')
    layers = [
        (4.6, '交互层', 'Vue3 + Element Plus + ECharts + vis-network'),
        (3.0, '决策协同层', 'FastAPI + LangGraph 反思闭环\nplan → preprocess → analyze → cluster → reflect'),
        (1.4, '数据模型层', 'MySQL + Redis + 本地 BGE（数据不出域）\n+ 云端 LLM（可降级旁路）'),
    ]
    for y, name, desc in layers:
        box = FancyBboxPatch((0.8, y), 8.4, 1.15, boxstyle='round,pad=0.06',
                             linewidth=1.2, edgecolor='black', facecolor='#f2f2f2')
        ax.add_patch(box)
        ax.text(5.0, y+0.62, name, ha='center', va='center', fontsize=12, fontweight='bold')
        ax.text(5.0, y+0.22, desc, ha='center', va='center', fontsize=9)
    for y1, y2 in [(4.6, 4.15), (3.0, 2.55)]:
        ax.annotate('', xy=(5.0, y2), xytext=(5.0, y1),
                    arrowprops=dict(arrowstyle='-|>', lw=1.2, color='black'))
    ax.text(5.0, 0.35, '数据不出域：关系数据存本地 MySQL，图与向量为可重建的派生视图，云端 LLM 仅脱敏旁路且默认关闭',
            ha='center', va='center', fontsize=8.5, style='italic')
    ax.set_title('图1  系统三层架构', fontsize=11, pad=8)
    plt.tight_layout()
    plt.savefig(os.path.join(OUT, 'fig1_arch.png'), bbox_inches='tight')
    plt.close()

# ============ 图2：两级研判闭环 ============
def fig_two_level():
    fig, ax = plt.subplots(figsize=(8, 3.2))
    ax.set_xlim(0, 16); ax.set_ylim(0, 4.6); ax.axis('off')
    boxes = [
        (0.5, '案件级研判\n（HAN 异构图聚类）\n输出团伙', '#e8eef7'),
        (5.0, '团伙锚点\n（case / account 节点）', '#eaf7ea'),
        (9.5, '账户级扩线\n（GraphSAGE，k 跳\n嫌疑子图）', '#fdf0e2'),
        (13.5, '冻卡 / 并案\n决策', '#fdeaea'),
    ]
    for x, label, fc in boxes:
        box = FancyBboxPatch((x, 1.2), 2.9, 2.0, boxstyle='round,pad=0.05',
                             linewidth=1.2, edgecolor='black', facecolor=fc)
        ax.add_patch(box)
        ax.text(x+1.45, 2.2, label, ha='center', va='center', fontsize=9.5)
    for x1, x2, lab in [(3.4, 5.0, '串并案'), (7.9, 9.5, '扩线种子'), (12.4, 13.5, '嫌疑子图')]:
        ax.annotate('', xy=(x2, 2.2), xytext=(x1, 2.2),
                    arrowprops=dict(arrowstyle='-|>', lw=1.2, color='black'))
        ax.text((x1+x2)/2, 2.75, lab, ha='center', va='center', fontsize=8.5)
    ax.text(8.0, 0.5, '两级闭环：案件串并案锁定团伙锚点，再以锚点驱动账户扩线，而非在全体账户上盲扫',
            ha='center', va='center', fontsize=8.5, style='italic')
    ax.set_title('图2  两级研判闭环：案件级串并案（HAN）输出团伙锚点，驱动账户级扩线（GraphSAGE）恢复同伙网络',
                 fontsize=10, pad=8)
    plt.tight_layout()
    plt.savefig(os.path.join(OUT, 'fig2_twolevel.png'), bbox_inches='tight')
    plt.close()

# ============ 图3：资金链双通道 ============
def fig_dual():
    fig, ax = plt.subplots(figsize=(7, 4.2))
    ax.set_xlim(0, 10); ax.set_ylim(0, 8); ax.axis('off')
    boxes = [
        (0.6, 6.0, '结构通道\n账户交易图\n（边=金额 log1p 加权）', '#e8eef7'),
        (5.4, 6.0, '文本通道\n话术/案情\n（BGE 嵌入）', '#eaf7ea'),
        (3.0, 3.2, 'HAN\n语义注意力融合', '#fdf0e2'),
        (3.0, 0.6, '团伙聚类\n（案件串并）', '#fdeaea'),
    ]
    for x, y, label, fc in boxes:
        box = FancyBboxPatch((x, y), 3.4, 1.5, boxstyle='round,pad=0.05',
                             linewidth=1.2, edgecolor='black', facecolor=fc)
        ax.add_patch(box)
        ax.text(x+1.7, y+0.75, label, ha='center', va='center', fontsize=9.5)
    ax.annotate('', xy=(3.0, 4.7), xytext=(2.3, 6.0),
                arrowprops=dict(arrowstyle='-|>', lw=1.2, color='black'))
    ax.annotate('', xy=(6.0, 4.7), xytext=(6.7, 6.0),
                arrowprops=dict(arrowstyle='-|>', lw=1.2, color='black'))
    ax.annotate('', xy=(4.7, 2.1), xytext=(4.7, 3.2),
                arrowprops=dict(arrowstyle='-|>', lw=1.2, color='black'))
    ax.text(5.0, 0.1, '双通道：结构通道编码资金流向拓扑，文本通道编码话术/案情语义，HAN 以语义注意力自适应加权两路及元路径重要性',
            ha='center', va='center', fontsize=8.5, style='italic')
    ax.set_title('图3  资金链双通道设计：结构通道（金额加权交易图）与文本通道（BGE 语义嵌入）经 HAN 语义注意力融合',
                 fontsize=10, pad=8)
    plt.tight_layout()
    plt.savefig(os.path.join(OUT, 'fig3_dual.png'), bbox_inches='tight')
    plt.close()

# ============ 图4：LangGraph 反思闭环 ============
def fig_reflection():
    fig, ax = plt.subplots(figsize=(8, 2.8))
    ax.set_xlim(0, 16); ax.set_ylim(0, 4.2); ax.axis('off')
    nodes = ['plan', 'preprocess', 'analyze', 'cluster', 'reflect']
    xs = [0.5, 3.3, 6.1, 8.9, 11.7]
    for x, name in zip(xs, nodes):
        box = FancyBboxPatch((x, 1.4), 2.0, 1.1, boxstyle='round,pad=0.05',
                             linewidth=1.2, edgecolor='black', facecolor='#f2f2f2')
        ax.add_patch(box)
        ax.text(x+1.0, 1.95, name, ha='center', va='center', fontsize=10)
    for x1, x2 in zip(xs[:-1], xs[1:]):
        ax.annotate('', xy=(x2, 1.95), xytext=(x1+2.0, 1.95),
                    arrowprops=dict(arrowstyle='-|>', lw=1.2, color='black'))
    # END box
    box = FancyBboxPatch((14.3, 1.4), 1.4, 1.1, boxstyle='round,pad=0.05',
                         linewidth=1.2, edgecolor='black', facecolor='#dddddd')
    ax.add_patch(box)
    ax.text(15.0, 1.95, 'END', ha='center', va='center', fontsize=10)
    ax.annotate('', xy=(14.3, 1.95), xytext=(13.7, 1.95),
                arrowprops=dict(arrowstyle='-|>', lw=1.2, color='black'))
    # 回连弧线
    ax.annotate('', xy=(6.1, 3.3), xytext=(11.7, 3.3),
                arrowprops=dict(arrowstyle='-|>', lw=1.2, color='black',
                                connectionstyle='arc3,rad=-0.35'))
    ax.text(8.9, 3.75, '未收敛：回连重算', ha='center', va='center', fontsize=8.5)
    ax.text(12.9, 2.75, '收敛', ha='center', va='center', fontsize=8.5)
    ax.set_title('图4  LangGraph 反思闭环编排（反思节点经条件边回连 analyze 触发重算）',
                 fontsize=10, pad=8)
    plt.tight_layout()
    plt.savefig(os.path.join(OUT, 'fig4_reflection.png'), bbox_inches='tight')
    plt.close()

# ============ 图5：合成数据基线对比（柱状图） ============
def fig_baselines():
    methods = ['KMeans', 'HDBSCAN', 'Semantic', 'Louvain', 'GraphSAGE', 'HAN(ours)']
    clean = [0.9122, 0.8888, 0.9076, 0.8884, 0.4061, 1.0000]
    hard = [0.9368, 0.8966, 0.9367, 0.8616, 0.3043, 0.9154]
    clean_e = [0.1075, 0.1046, 0.1134, 0.0911, 0.2127, 0.0000]
    hard_e = [0.1363, 0.1298, 0.1331, 0.0874, 0.0000, 0.1214]
    x = np.arange(len(methods))
    w = 0.36
    fig, ax = plt.subplots(figsize=(8, 4.0))
    b1 = ax.bar(x-w/2, clean, w, yerr=clean_e, capsize=3, label='Clean', color='white', edgecolor='black', hatch='//')
    b2 = ax.bar(x+w/2, hard, w, yerr=hard_e, capsize=3, label='Hard', color='#d9d9d9', edgecolor='black')
    ax.set_ylabel('Macro-F1')
    ax.set_ylim(0, 1.18)
    ax.set_xticks(x); ax.set_xticklabels(methods, fontsize=9, rotation=18, ha='right')
    ax.legend(loc='upper left', fontsize=9)
    ax.grid(axis='y', linestyle='--', alpha=0.5)
    ax.set_title('图5  合成数据基线对比（10 seeds mean±std）', fontsize=11, pad=8)
    plt.tight_layout()
    plt.savefig(os.path.join(OUT, 'fig5_baselines.png'), bbox_inches='tight')
    plt.close()

# ============ 图6：同协议异构图基线（折线图） ============
def fig_hetero():
    cross = [0.0, 0.2, 0.4]
    data = {
        'RGCN': [0.908, 0.856, 0.794],
        'GAT': [0.942, 0.878, 0.819],
        'HAN(ours)': [0.985, 0.894, 0.875],
        'KMeans': [0.942, 0.958, 0.913],
        'Semantic': [0.939, 0.953, 0.909],
        'Louvain': [0.905, 0.844, 0.836],
    }
    markers = ['o', 's', '^', 'D', 'v', 'P']
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    for (name, vals), mk in zip(data.items(), markers):
        lw = 2.0 if name == 'HAN(ours)' else 1.2
        ax.plot(cross, vals, marker=mk, lw=lw, label=name)
    ax.set_xlabel('cross-talk 干扰程度')
    ax.set_ylabel('Macro-F1')
    ax.set_ylim(0.70, 1.0)
    ax.set_xticks(cross)
    ax.legend(fontsize=8.5, ncol=3, loc='lower left')
    ax.grid(linestyle='--', alpha=0.5)
    ax.set_title('图6  同协议异构图基线在跨团伙干扰下的 Macro-F1 曲线（15 seeds）', fontsize=10, pad=8)
    plt.tight_layout()
    plt.savefig(os.path.join(OUT, 'fig6_hetero.png'), bbox_inches='tight')
    plt.close()

# ============ 图7：反思闭环消融（柱状图） ============
def fig_reflection_ablation():
    labels = ['无反思', '有反思']
    f1 = [0.3228, 0.8353]
    std = [0.199, 0.029]
    fig, ax = plt.subplots(figsize=(5.5, 3.8))
    bars = ax.bar(labels, f1, yerr=std, capsize=5, color=['white', '#d9d9d9'], edgecolor='black', hatch=['//', ''])
    for bar, v in zip(bars, f1):
        ax.text(bar.get_x()+bar.get_width()/2, v+0.03, f'{v:.3f}', ha='center', fontsize=10)
    ax.set_ylabel('平均 Macro-F1')
    ax.set_ylim(0, 1.0)
    ax.grid(axis='y', linestyle='--', alpha=0.5)
    ax.set_title('图7  反思闭环消融（10 seeds，cross=0.2）', fontsize=11, pad=8)
    plt.tight_layout()
    plt.savefig(os.path.join(OUT, 'fig7_reflection_ablation.png'), bbox_inches='tight')
    plt.close()

# ============ 图8：扩线设定团伙恢复 F1（柱状图） ============
def fig_refinement():
    groups = ['合成 ct=0.25', '合成 ct=0.75', 'AMLSim 样本']
    kmeans = [0.112, 0.168, 0.124]
    untrained = [0.107, 0.123, None]
    trained = [0.131, 0.178, 0.003]
    louvain = [0.507, 0.175, 0.111]
    x = np.arange(3)
    w = 0.19
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    ax.bar(x-1.5*w, kmeans, w, label='原始特征+KMeans', color='white', edgecolor='black', hatch='//')
    ax.bar(x-0.5*w, [v if v is not None else 0 for v in untrained], w, label='未训练 GNN', color='#e8eef7', edgecolor='black')
    ax.bar(x+0.5*w, trained, w, label='训练后 GNN', color='#d9d9d9', edgecolor='black')
    ax.bar(x+1.5*w, louvain, w, label='Louvain', color='#fdeaea', edgecolor='black')
    ax.set_xticks(x); ax.set_xticklabels(groups, fontsize=9)
    ax.set_ylabel('环恢复 F1')
    ax.set_ylim(0, 0.95)
    ax.legend(fontsize=8, ncol=2, loc='upper right')
    ax.grid(axis='y', linestyle='--', alpha=0.5)
    ax.set_title('图8  扩线设定下的团伙（资金环）恢复 F1', fontsize=11, pad=8)
    plt.tight_layout()
    plt.savefig(os.path.join(OUT, 'fig8_refinement.png'), bbox_inches='tight')
    plt.close()

fig_arch()
fig_two_level()
fig_dual()
fig_reflection()
fig_baselines()
fig_hetero()
fig_reflection_ablation()
fig_refinement()
print('8 张图已生成到', OUT)
for f in sorted(os.listdir(OUT)):
    print(' ', f, os.path.getsize(os.path.join(OUT, f)))
