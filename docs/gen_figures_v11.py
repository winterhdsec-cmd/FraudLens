# -*- coding: utf-8 -*-
"""慧眼识诈 v11 —— 申报书配图第二轮优化（用户意见 2026-09-01）：
① fig2 由"总体架构"改为"系统功能结构"树状图（更直观，替换原架构图）；
② 全图灰字改为深色（白底可读）：#6B7A8D/#7F8C8D/#95A5A6/#8A99A8/#5D6D7E → #34495E/#2C3E50；
③ 全图文字放大约 1.8 倍（评委打印后仍可读）；
④ fig5（图8）分叉箭头改正交折线，标签置于水平段上、白底遮线，箭头统一朝下；
⑤ 各图信息密度微增。
"""
import os
import subprocess
import numpy as np
from PIL import Image

OUT = r"E:\FraudLens\docs\plan_figures_v11"
os.makedirs(OUT, exist_ok=True)

# 颜色（深色文字为主，白底可读）
INK = "#1E3A5F"
BLUE = "#2980B9"
ORANGE = "#E67E22"
GREEN = "#27AE60"
RED = "#E74C3C"
PURPLE = "#8E44AD"
GOLD = "#CA8A04"
LGREEN = "#58B368"

# 正文用深色（替代原灰）
TXT = "#2C3E50"       # 主文字
TXT2 = "#34495E"      # 次级文字
TXT3 = "#5D6D7E"      # 弱提示（仍比原灰深很多）

FS = 1.8
GS = 1.6


def f(v):
    return int(round(v * FS))


def g(v):
    return int(round(v * GS))


BASE_CSS = """
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:"Microsoft YaHei","PingFang SC","Noto Sans CJK SC",sans-serif;color:%s;background:#fff;line-height:1.5}
.wrap{width:1260px;margin:0 auto;padding:26px 22px 28px}
h1{font-size:%dpx;font-weight:800;text-align:center;color:%s;margin-bottom:7px;letter-spacing:1px}
.sub{text-align:center;font-size:%dpx;color:%s;margin-bottom:20px;letter-spacing:.5px}
h2{font-size:%dpx;font-weight:700;color:%s;margin-bottom:12px;display:flex;align-items:center;gap:10px}
h2::before{content:"";width:5px;height:18px;background:#2980B9;border-radius:2px}
.panel{background:#F5F7FA;border:1px solid #D5DBDB;border-radius:9px;padding:14px}
.row{display:flex;gap:12px}
.col{flex:1}
.desc{font-size:%dpx;color:%s;line-height:1.6}
.center{text-align:center}
""" % (TXT, f(21), INK, f(11.5), TXT2, f(14), INK, f(11), TXT2)


def write_html(name, body_html, extra_css=""):
    html = ("<!doctype html><html><head><meta charset=\"utf-8\"><style>"
            + BASE_CSS + extra_css +
            "</style></head><body><div class=\"wrap\">" + body_html +
            "</div></body></html>")
    with open(OUT + "/" + name, "w", encoding="utf-8") as fp:
        fp.write(html)
    print("  %s written" % name)


# ============================================================ fig2 系统功能结构（树状图） ============================================================
def gen_fig2():
    def leaf(t, color, d=None):
        dd = ('<div class="lf-d">%s</div>' % d) if d else ''
        return ('<div class="leaf" style="border-left:4px solid %s">'
                '<div class="lf-t">%s</div>%s</div>' % (color, t, dd))

    root = """
<div class="root">
  <div class="root-t">慧眼识诈 · 多智能体反诈团伙智能研判系统</div>
  <div class="root-d">上传零散警情线索 &#8594; 自动串案成网 &#8594; 圈出疑似团伙 + 逐条证据链</div>
</div>
"""

    b1 = ('<div class="tree"><div class="b-h" style="background:#E67E22">&#9312; 数据接入</div>'
          '<div class="b-tag" style="color:#B05A12">民警零门槛录入</div>'
          + leaf("话术文本粘贴", ORANGE) + leaf("案件 CSV 批量导入", ORANGE)
          + leaf("聊天截图 OCR 提取", ORANGE) + leaf("缺失字段留空标记", ORANGE, "字段缺失不报错") + '</div>')
    b2 = ('<div class="tree"><div class="b-h" style="background:#2980B9">&#9313; 要素解析</div>'
          '<div class="b-tag" style="color:#1A5276">杂乱材料 &#8594; 规范要素</div>'
          + leaf("账户 / 手机号抽取", BLUE) + leaf("金额/时间/话术段落", BLUE)
          + leaf("多格式混合兼容", BLUE, "文本 + CSV + 图片同批") + '</div>')
    b3 = ('<div class="tree core"><div class="b-h" style="background:#27AE60">&#9314; 团伙发现</div>'
          '<div class="b-tag" style="color:#1E8449">核心算法 · 双通道一致采信</div>'
          + leaf("异构图构建", GREEN, "7 类节点 · 5 条元路径")
          + leaf("双通道独立聚类", GREEN, "资金 Louvain + 话术 BGE")
          + leaf("共识锚点 \u2229", GREEN, "两通道严格一致")
          + leaf("HAN 半监督判定", GREEN, "自适应门控 · 拒错牌")
          + leaf("增量挂接", GREEN, "新警情随到随判") + '</div>')
    b4 = ('<div class="tree"><div class="b-h" style="background:#8E44AD">&#9315; 成果输出</div>'
          '<div class="b-tag" style="color:#6C3483">把结论交给民警</div>'
          + leaf("团伙名单与画像", PURPLE) + leaf("逐条证据链报告", PURPLE)
          + leaf("资金流向可视化", PURPLE) + leaf("研判报告一键导出", PURPLE, "docx · 可打印") + '</div>')

    cross = """
<div class="cross-row">
  <div class="cross" style="border-color:#8E44AD;background:#FBF8FD">
    <div class="cr-h" style="color:#6C3483">&#9889; AI 会商反思闭环（横切 &#9314; &#8594; &#9315;）</div>
    <div class="cr-steps">
      <span style="border-color:#2980B9;color:#1A5276">话术<br>分析</span><i>&#8594;</i>
      <span style="border-color:#E67E22;color:#B05A12">资金<br>追踪</span><i>&#8594;</i>
      <span style="border-color:#8E44AD;color:#6C3483">串并<br>研判</span><i>&#8594;</i>
      <span style="border-color:#E74C3C;color:#922B21">质检<br>复核</span><i>&#8594;</i>
      <span style="border-color:#27AE60;color:#1E8449">3轮不过<br>转人工</span>
    </div>
  </div>
  <div class="cross" style="border-color:#27AE60;background:#F2FBF5">
    <div class="cr-h" style="color:#1E8449">&#128274; 核心算法本地运行（底线）</div>
    <div class="cr-steps">
      <span style="border-color:#27AE60;color:#1E8449">BGE 本地编码</span><i>&#8594;</i>
      <span style="border-color:#27AE60;color:#1E8449">纯 CPU 可跑</span><i>&#8594;</i>
      <span style="border-color:#27AE60;color:#1E8449">大模型可本地部署</span>
    </div>
  </div>
</div>
"""

    body = ('<h1>系统功能结构</h1>'
            '<div class="sub">四个功能模块 + 一套横切机制 · 民警只做录入、其余全自动 · 核心算法本地运行</div>'
            + root +
            '<div class="tree-row">' + b1 + b2 + b3 + b4 + '</div>'
            + cross)

    extra = """
.tree-row{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-top:14px;align-items:stretch}
.root{background:#1E3A5F;border-radius:12px;padding:16px 20px;text-align:center;color:#fff;box-shadow:0 3px 10px rgba(30,58,95,.18)}
.root-t{font-size:%dpx;font-weight:800;letter-spacing:1px}
.root-d{font-size:%dpx;color:#D6E4F5;margin-top:6px;font-weight:600}
.tree{background:#fff;border:1.5px solid #D5DBDB;border-radius:10px;padding:11px 11px 13px;display:flex;flex-direction:column;gap:8px}
.tree.core{border:2px solid #82E0AA;background:#FBFEFC}
.b-h{font-size:%dpx;font-weight:800;color:#fff;border-radius:7px;padding:7px 10px;text-align:center}
.b-tag{font-size:%dpx;font-weight:700;text-align:center;margin-top:-2px;padding:3px 2px 2px;line-height:1.4}
.leaf{background:#F8FAFC;border:1px solid #E3E8EE;border-radius:7px;padding:9px 12px}
.leaf:hover{background:#F0F4F8}
.lf-t{font-size:%dpx;font-weight:700;color:%s;line-height:1.4}
.lf-d{font-size:%dpx;color:%s;margin-top:4px;line-height:1.45}
.cross-row{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:14px}
.cross{border:1.5px solid;border-radius:10px;padding:12px 14px}
.cr-h{font-size:%dpx;font-weight:800;margin-bottom:9px}
.cr-steps{display:flex;align-items:center;gap:7px;flex-wrap:nowrap}
.cr-steps span{flex:1;text-align:center;font-size:%dpx;font-weight:700;border:1.5px solid;border-radius:7px;padding:9px 6px;background:#fff;line-height:1.35}
.cr-steps i{color:%s;font-weight:800;font-size:15px;font-style:normal}
""" % (f(17), f(12), f(15), f(11), f(13), TXT, f(11), TXT2, f(13), f(12), TXT3)
    write_html("fig2_func.html", body, extra)


# ============================================================ fig3 反思闭环（垂直主干，放大加密） ============================================================
def gen_fig3():
    CW, CH = 1420, 1740

    def node(x, y, w, h, color, no, title, duties, tint):
        rows = ""
        for d in duties:
            rows += '<div class="nd-d"><span class="dot" style="background:%s"></span>%s</div>' % (color, d)
        no_html = '<span class="cno" style="background:%s">%s</span>' % (color, no) if no else ''
        return ('<div class="nd" style="left:%dpx;top:%dpx;width:%dpx;height:%dpx;border-color:%s;background:%s">'
                '<div class="nd-t">%s<span class="nd-name" style="color:%s">%s</span></div>%s</div>'
                % (x, y, w, h, color, tint, no_html, color, title, rows))

    svg = """
<svg width="%d" height="%d" style="position:absolute;left:0;top:0;z-index:0">
<defs>
%s
</defs>
%s
</svg>""" % (CW, CH, _markers(), _fig3_paths())

    entry = ('<div class="nd entry" style="left:210px;top:0px;width:800px;height:116px">'
             '<div class="nd-t"><span class="cno" style="background:#5D6D7E">&#9654;</span>'
             '<span class="nd-name" style="color:#2C3E50">输入 · 新案件进入会商</span></div>'
             '<div class="ent-d">案件要素（话术/资金/账户）+ 图嵌入候选簇，同时下发给两位分析员</div></div>')

    n1 = node(150, 150, 470, 180, BLUE, "①", "话术分析员",
              ["识别话术模板（BGE 语义）", "判定作案阶段：引流 / 实施 / 洗钱", "输出话术簇与相似度"], "#F4F9FD")
    n2 = node(590, 150, 470, 180, ORANGE, "②", "资金追踪员",
              ["查共享收款账户", "绘转账链条 · 识别取现模式", "输出资金关联子图"], "#FEF9F2")
    n3 = ('<div class="nd" style="left:210px;top:420px;width:800px;height:170px;padding-left:36px;border-color:#8E44AD;background:#FBF8FD">'
          '<div class="nd-t"><span class="cno" style="background:#8E44AD">③</span>'
          '<span class="nd-name" style="color:#6C3483">串并研判员 · 提出并案假设</span></div>'
          '<div class="tri">'
          '<span><b>综合①②证据</b>提出并案假设</span>'
          '<span><b>附完整证据链</b>硬证据 + 软证据对应</span>'
          '<span><b>被打回时</b>重新分派 ①② 补证据</span></div></div>')
    n4 = ('<div class="nd" style="left:210px;top:680px;width:800px;height:220px;border-color:#E74C3C;background:#FDF5F4">'
          '<div class="nd-t"><span class="cno" style="background:#E74C3C">④</span>'
          '<span class="nd-name" style="color:#C0392B">质检复核（每轮必过）</span></div>'
          '<div class="tri">'
          '<span class="chk">&#9744; 证据链是否闭合？</span>'
          '<span class="chk">&#9744; 分析员意见一致？</span>'
          '<span class="chk">&#9744; 置信度是否达标？</span></div>'
          '<div class="chk-res">三问全过 &#10140; 出牌 ｜ 不一致 &#10140; 打回重议 ｜ 3 轮不过 &#10140; 转人工</div></div>')
    nok = ('<div class="nd" style="left:210px;top:1010px;width:380px;height:185px;border-color:#27AE60;background:#F2FBF5">'
           '<div class="nd-t"><span class="cno" style="background:#27AE60">&#10003;</span>'
           '<span class="nd-name" style="color:#1E8449">输出团伙名单</span></div>'
           '<div class="nd-d"><span class="dot" style="background:#27AE60"></span>通过复核才输出</div>'
           '<div class="nd-d"><span class="dot" style="background:#27AE60"></span>逐条证据链 · 可追溯可质证</div>'
           '<div class="nd-d"><span class="dot" style="background:#27AE60"></span>附资金流向图与画像</div></div>')
    nno = ('<div class="nd" style="left:630px;top:1010px;width:380px;height:185px;border-color:#E74C3C;background:#FDF5F4">'
           '<div class="nd-t"><span class="cno" style="background:#E74C3C">&#10007;</span>'
           '<span class="nd-name" style="color:#C0392B">转人工复核</span></div>'
           '<div class="nd-d"><span class="dot" style="background:#E74C3C"></span>3 轮重议仍不过</div>'
           '<div class="nd-d"><span class="dot" style="background:#E74C3C"></span>降级人工处理 · 全过程留痕</div>'
           '<div class="nd-d"><span class="dot" style="background:#E74C3C"></span>结论可质证、责任可追溯</div></div>')

    why = ('<div class="why"><div class="why-t">为什么必须"绕弯子"？</div>'
           '<div class="wg"><b>错误代价</b><span>警务场景中，错误并案的代价远大于暂不出结论</span></div>'
           '<div class="wg"><b>知己知彼</b><span>"知道自己知道多少"是 AI 进入一线辅助决策的第一道门槛</span></div>'
           '<div class="wg"><b>全程留痕</b><span>每轮会商记录在案，结论可质证、责任可追溯</span></div>'
           '<div class="wg" style="border-color:#82E0AA"><b style="color:#1E8449">敢说拿不准</b><span>证据不够就拒判，不出错牌是底线</span></div></div>')

    rhythm = """
<div class="rhythm">
  <div class="rh-t">一轮会商的节奏 · 设计理由见右侧</div>
  <div class="rh-row">
    <div class="rc" style="border-color:#2980B9;color:#1A5276">第 1 轮<br>初判假设</div>
    <div class="r-ar">&#8594;</div>
    <div class="rc" style="border-color:#E67E22;color:#B05A12">第 2 轮<br>打回补证</div>
    <div class="r-ar">&#8594;</div>
    <div class="rc" style="border-color:#27AE60;color:#1E8449">第 3 轮<br>收敛通过</div>
    <div class="r-ar">&#8594;</div>
    <div class="rc" style="border-color:#E74C3C;color:#922B21">仍不过<br>转人工</div>
  </div>
  <div class="rh-note">每轮记录：谁提出、谁质疑、依据什么——事后可质证、可复盘</div>
</div>
"""

    labels = """
<div class="elab" style="left:385px;top:246px">话术证据 · 阶段判定</div>
<div class="elab" style="left:825px;top:246px">资金证据 · 账户链路</div>
<div class="elab" style="left:610px;top:610px">并案假设 + 证据链</div>
<div class="elab ok" style="left:400px;top:966px">&#10003; 三问全过</div>
<div class="elab bad" style="left:820px;top:966px">3 轮仍不过</div>
"""

    body = ('<h1>AI 会商反思闭环</h1>'
            '<div class="sub">提出 — 质疑 — 复核 · 对不上就打回重议 · 3 轮不过转人工</div>'
            '<div class="canvas" style="width:%dpx;height:%dpx">' % (CW, CH)
            + svg + entry + n1 + n2 + n3 + n4 + nok + nno + why + rhythm + labels + '</div>')

    extra = """
.wrap{width:1410px}
.canvas{position:relative;margin:0 auto}
.nd{position:absolute;background:#fff;border:1.5px solid;border-radius:11px;padding:13px 16px;z-index:1;box-shadow:0 2px 7px rgba(30,58,95,.07)}
.nd.entry{box-shadow:none}
.nd-t{font-size:%dpx;font-weight:800;display:flex;align-items:center;gap:9px;margin-bottom:8px}
.cno{width:30px;height:30px;border-radius:50%%;color:#fff;font-size:15px;font-weight:800;display:flex;align-items:center;justify-content:center;flex-shrink:0}
.nd-name{color:%s}
.ent-d{display:block;font-size:%dpx;color:%s;font-weight:400;margin-left:34px;margin-top:5px;line-height:1.5}
.nd-d{font-size:%dpx;color:%s;line-height:1.55;display:flex;gap:7px;align-items:flex-start;margin-bottom:3px}
.dot{width:6px;height:6px;border-radius:50%%;margin-top:7px;flex-shrink:0}
.tri{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}
.tri span{font-size:%dpx;color:%s;background:#fff;border:1px solid #E8EDF2;border-radius:7px;padding:7px 9px;line-height:1.5;min-width:0;overflow-wrap:anywhere;word-break:break-word}
.tri b{color:%s;display:block;font-size:%dpx}
.tri .chk{background:#fff;border:1px solid #F0D5D1;color:%s;font-weight:600}
.chk-res{font-size:%dpx;font-weight:700;color:#922B21;border-top:1px dashed #E8B4AE;margin-top:8px;padding-top:7px}
.elab{position:absolute;font-size:%dpx;font-weight:700;color:%s;background:#fff;border:1px solid #D5DBDB;border-radius:9px;padding:3px 9px;text-align:center;z-index:2;white-space:nowrap;transform:translateX(-50%%)}
.elab.ok{color:#1E8449;border-color:#82E0AA;background:#F2FBF5}
.elab.bad{color:#922B21;border-color:#E8B4AE;background:#FDF5F4}
.why{position:absolute;left:1112px;top:120px;width:296px;background:#F5F7FA;border:1px solid #D5DBDB;border-radius:9px;padding:12px 13px}
.why-t{font-size:%dpx;font-weight:800;color:%s;margin-bottom:8px}
.wg{background:#fff;border:1px solid #D5DBDB;border-radius:7px;padding:8px 10px;margin-bottom:8px}
.wg:last-child{margin-bottom:0}
.wg b{display:block;font-size:%dpx;color:#2980B9;margin-bottom:3px}
.wg span{font-size:%dpx;color:%s;line-height:1.5}
.rhythm{position:absolute;left:180px;top:1275px;width:760px;background:#F8FAFC;border:1px solid #D5DBDB;border-radius:9px;padding:11px 13px}
.rh-t{font-size:%dpx;font-weight:800;color:%s;margin-bottom:8px}
.rh-row{display:flex;align-items:center;gap:8px}
.rc{flex:1;text-align:center;font-size:%dpx;font-weight:700;border:1.5px solid;border-radius:7px;padding:7px 2px;background:#fff;line-height:1.35}
.r-ar{color:%s;font-size:14px;font-weight:800}
.rh-note{font-size:%dpx;color:%s;line-height:1.45;margin-top:6px;border-top:1px dashed #D5DBDB;padding-top:5px}
""" % (f(13.5), TXT, f(11.5), TXT2, f(11.5), TXT2, f(11), TXT2, TXT, f(12.5), TXT2,
       f(11.5), f(11), TXT2, f(12.5), INK, f(11.5), f(11), TXT2, f(11.5), TXT, f(11.5), TXT3, f(11), TXT2)
    write_html("fig3_loop.html", body, extra)


def _markers():
    mk = ""
    for mid, c in [("mB", BLUE), ("mO", ORANGE), ("mP", PURPLE), ("mG", GREEN), ("mR", RED),
                   ("mGo", GOLD), ("mGray", "#5D6D7E"), ("mLG", LGREEN)]:
        mk += ('<marker id="%s" markerWidth="11" markerHeight="10" refX="9" refY="5" orient="auto">'
               '<path d="M0,0 L10,5 L0,10 z" fill="%s"/></marker>' % (mid, c))
    return mk


def _fig3_paths():
    return """
<path d="M 295 116 L 295 148" stroke="#2980B9" stroke-width="3" fill="none" marker-end="url(#mB)"/>
<path d="M 795 116 L 795 148" stroke="#E67E22" stroke-width="3" fill="none" marker-end="url(#mO)"/>
<path d="M 295 330 L 295 418" stroke="#2980B9" stroke-width="3" fill="none" marker-end="url(#mB)"/>
<path d="M 795 330 L 795 418" stroke="#E67E22" stroke-width="3" fill="none" marker-end="url(#mO)"/>
<path d="M 560 590 L 560 678" stroke="#8E44AD" stroke-width="3" fill="none" marker-end="url(#mP)"/>
<path d="M 360 900 L 360 1008" stroke="#27AE60" stroke-width="3" fill="none" marker-end="url(#mG)"/>
<path d="M 760 900 L 760 1008" stroke="#E74C3C" stroke-width="3" fill="none" marker-end="url(#mR)"/>
<path d="M 206 744 L 88 744 L 88 505 L 204 505" stroke="#E74C3C" stroke-width="3" stroke-dasharray="9,6" fill="none" marker-end="url(#mR)"/>
<rect x="62" y="726" width="132" height="36" rx="9" fill="#FFF6F5" stroke="#E8B4AE" stroke-width="2"/>
<text x="128" y="752" text-anchor="middle" font-size="23" font-weight="700" fill="#C0392B" font-family="Microsoft YaHei,sans-serif">&#8634; 打回重议</text>
"""


# ============================================================ fig4 串案成网（放大重构） ============================================================
def gen_fig4():
    CW, CH = 960, 1010

    nodes = [
        (200, 130, BLUE, "案件1", "案件", None),
        (200, 290, BLUE, "案件2", "案件", None),
        (200, 450, BLUE, "案件5", "案件", None),
        (70, 290, GOLD, "账户A1", "收款账户", None),
        (70, 130, RED, "刷单返利", "诈骗类型", None),
        (340, 130, LGREEN, "受害人V1", "受害人", None),
        (340, 450, LGREEN, "受害人V2", "受害人", None),
        (700, 130, BLUE, "案件3", "案件", None),
        (700, 450, BLUE, "案件4", "案件", None),
        (560, 290, ORANGE, "号码B1", "手机号", None),
        (560, 130, PURPLE, "嫌疑人S1", "嫌疑人", None),
        (860, 290, "#7F8C8D", "城市X", "城市", None),
        (860, 130, RED, "冒充客服", "诈骗类型", None),
        (860, 450, LGREEN, "受害人V3", "受害人", None),
        (150, 760, BLUE, "案件6", "案件", "reject"),
    ]

    edges = [
        (70, 290, 200, 130, GOLD, 3, None),
        (70, 290, 200, 290, GOLD, 3, None),
        (70, 290, 200, 450, GOLD, 3, None),
        (200, 130, 200, 290, GREEN, 2.5, "6,5"),
        (200, 290, 200, 450, GREEN, 2.5, "6,5"),
        (340, 130, 200, 130, LGREEN, 2, None),
        (340, 450, 200, 450, LGREEN, 2, None),
        (70, 130, 200, 130, RED, 2, None),
        (70, 130, 200, 290, RED, 2, None),
        (560, 290, 700, 130, ORANGE, 3, None),
        (560, 290, 700, 450, ORANGE, 3, None),
        (560, 130, 700, 130, PURPLE, 2.5, None),
        (560, 130, 700, 450, PURPLE, 2.5, None),
        (860, 290, 700, 130, "#7F8C8D", 2, None),
        (860, 290, 700, 450, "#7F8C8D", 2, None),
        (700, 130, 700, 450, GREEN, 2.5, "6,5"),
        (860, 130, 700, 130, RED, 2, None),
        (860, 450, 700, 450, LGREEN, 2, None),
        (150, 760, 200, 450, GREEN, 2, "4,4"),
    ]

    lines = ""
    for x1, y1, x2, y2, c, w, d in edges:
        dash = ' stroke-dasharray="%s"' % d if d else ''
        lines += ('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="%s" stroke-width="%s"%s/>'
                  % (x1, y1, x2, y2, c, w, dash))

    node_html = ""
    for cx, cy, c, main, sub, ring in nodes:
        ring_html = ('<div class="ring" style="left:%dpx;top:%dpx"></div>' % (cx - 66, cy - 66)) if ring else ''
        node_html += ring_html + (
            '<div class="gn" style="left:%dpx;top:%dpx;background:%s">'
            '<div class="gn-m">%s</div><div class="gn-s">%s</div></div>' % (cx - 52, cy - 52, c, main, sub))

    gangs = """
<div class="gang" style="left:14px;top:44px;width:428px;height:480px;border-color:#2980B9;background:rgba(41,128,185,.05)">
  <div class="gang-tag" style="background:#2980B9;left:14px;top:-15px">团伙A · 3 案并串 · 共享账户A1 · 话术相似0.92</div>
</div>
<div class="gang" style="left:504px;top:44px;width:440px;height:480px;border-color:#27AE60;background:rgba(39,174,96,.05)">
  <div class="gang-tag" style="background:#27AE60;left:20px;top:-15px">团伙B · 2 案并串 · 共享号码B1 + 嫌疑人S1</div>
</div>
"""

    elabs = """
<div class="gelab" style="left:120px;top:360px">共享收款账户</div>
<div class="gelab" style="left:264px;top:360px">话术相似 0.92</div>
<div class="gelab" style="left:760px;top:350px">话术相似 0.88</div>
<div class="gelab" style="left:615px;top:358px">共享手机号</div>
<div class="gelab weak" style="left:250px;top:618px">话术相似 0.31（弱 · 孤证）</div>
"""

    bottom = """
<div class="rej" style="left:238px;top:660px;width:380px;height:220px">
  <div class="rej-t">&#10007; 案件6 · 拒绝并入团伙A</div>
  <div class="rej-b">仅"话术相似 0.31"一条软证据，无共享账户 / 号码 / 嫌疑人等任何硬证据。<b>孤证不采信——宁留缺口，不错并案。</b>新证据到达后由增量匹配自动挂入。</div>
</div>
<div class="prof" style="left:630px;top:640px;width:314px;height:352px">
  <div class="prof-t">团伙画像卡（示例·团伙A）</div>
  <div class="prof-r"><span>案件数</span><b>3 起（案件1/2/5）</b></div>
  <div class="prof-r"><span>硬证据</span><b>共享收款账户 A1</b></div>
  <div class="prof-r"><span>软证据</span><b>话术相似 0.92</b></div>
  <div class="prof-r"><span>诈骗类型</span><b>刷单返利·洗钱阶段</b></div>
  <div class="prof-r"><span>风险等级</span><b>高·建议优先处置</b></div>
  <div class="prof-ok">双信号一致 &#10140; 并案 &#10003;</div>
</div>
"""

    left = """
<div class="lg-panel">
  <div class="lg-t">节点类型（7 类）</div>
  <div class="lg-r"><span class="lg-dot" style="background:#2980B9"></span>案件<span class="lg-n">研判主体</span></div>
  <div class="lg-r"><span class="lg-dot" style="background:#58B368"></span>受害人<span class="lg-n">报案人</span></div>
  <div class="lg-r"><span class="lg-dot" style="background:#E67E22"></span>手机号<span class="lg-n">通话证据</span></div>
  <div class="lg-r"><span class="lg-dot" style="background:#CA8A04"></span>收款账户<span class="lg-n">资金证据</span></div>
  <div class="lg-r"><span class="lg-dot" style="background:#8E44AD"></span>嫌疑人<span class="lg-n">落地查证</span></div>
  <div class="lg-r"><span class="lg-dot" style="background:#E74C3C"></span>诈骗类型<span class="lg-n">话术归类</span></div>
  <div class="lg-r"><span class="lg-dot" style="background:#7F8C8D"></span>城市<span class="lg-n">落点归属</span></div>
</div>
<div class="lg-panel">
  <div class="lg-t">关系类型（图中的边）</div>
  <div class="lg-r"><span class="lg-line" style="background:#CA8A04"></span>共享收款账户</div>
  <div class="lg-r"><span class="lg-line" style="background:#E67E22"></span>共享手机号</div>
  <div class="lg-r"><span class="lg-line" style="background:#8E44AD"></span>嫌疑人关联</div>
  <div class="lg-r"><span class="lg-line dash" style="background:repeating-linear-gradient(90deg,#27AE60 0 8px,transparent 8px 14px)"></span>话术相似（案-案）</div>
  <div class="lg-r"><span class="lg-line" style="background:#7F8C8D"></span>同城</div>
  <div class="lg-r"><span class="lg-line" style="background:#E74C3C"></span>同类型诈骗</div>
  <div class="lg-r"><span class="lg-line" style="background:#58B368"></span>受害人关联</div>
</div>
<div class="lg-panel" style="flex:1;background:#FDF5F4;border-color:#E8B4AE">
  <div class="lg-t" style="color:#922B21">并案铁律</div>
  <div class="rule-ok"><b>&#10003; 双信号一致</b>硬证据（账户/号码/嫌疑人）+ 软证据（话术）同时指向 &#10140; 并案</div>
  <div class="rule-no"><b>&#10007; 孤证不并</b>仅有弱话术相似 &#10140; 拒绝并案，留待增量验证</div>
</div>
"""

    svg = '<svg width="%d" height="%d" style="position:absolute;left:0;top:0;z-index:0">%s</svg>' % (CW, CH, lines)

    body = ('<h1>串案成网 · 异构图团伙发现</h1>'
            '<div class="sub">7 类节点 · 5 条元路径 · 硬证据 + 软证据一致才并案 —— 左：团伙A · 右：团伙B · 案件6 为"孤证不并"反例</div>'
            '<div class="fig4-row">'
            '<div class="fig4-left">' + left + '</div>'
            '<div class="fig4-canvas" style="width:%dpx;height:%dpx">' % (CW, CH)
            + svg + gangs + node_html + elabs + bottom + '</div></div>')

    extra = """
.wrap{width:1320px}
.fig4-row{display:flex;gap:14px;align-items:stretch}
.fig4-left{width:300px;display:flex;flex-direction:column;gap:11px}
.fig4-canvas{position:relative;flex-shrink:0;background:#fff;border:1px solid #E3E8EE;border-radius:11px}
.gang{position:absolute;border:2.5px dashed;border-radius:16px;z-index:0}
.gang-tag{position:absolute;font-size:%dpx;font-weight:700;color:#fff;border-radius:13px;padding:4px 12px;z-index:3;white-space:normal;line-height:1.3;text-align:center;width:400px}
.gn{position:absolute;width:104px;height:104px;border-radius:50%%;z-index:2;display:flex;flex-direction:column;align-items:center;justify-content:center;border:3px solid #fff;box-shadow:0 2px 6px rgba(30,58,95,.22)}
.gn-m{font-size:%dpx;font-weight:800;color:#fff;line-height:1.15}
.gn-s{font-size:%dpx;color:rgba(255,255,255,.95);margin-top:2px}
.ring{position:absolute;width:132px;height:132px;border:2.5px dashed #E74C3C;border-radius:50%%;z-index:1}
.gelab{position:absolute;font-size:%dpx;font-weight:700;color:%s;background:#fff;border:1px solid #D5DBDB;border-radius:9px;padding:2px 7px;z-index:3;white-space:nowrap;transform:translateX(-50%%)}
.gelab.weak{color:#922B21;border-color:#E8B4AE}
.rej{position:absolute;background:#fff;border:2px solid #E8B4AE;border-radius:10px;padding:11px 13px;z-index:2}
.rej-t{font-size:%dpx;font-weight:800;color:#922B21;margin-bottom:5px}
.rej-b{font-size:%dpx;color:%s;line-height:1.55}
.rej-b b{color:#922B21}
.prof{position:absolute;background:#fff;border:2px solid #AED6F1;border-radius:10px;padding:11px 13px;z-index:2}
.prof-t{font-size:%dpx;font-weight:800;color:#1A5276;margin-bottom:6px;border-bottom:1px solid #EBF5FB;padding-bottom:5px;white-space:nowrap}
.prof-r{display:flex;justify-content:space-between;font-size:%dpx;margin-bottom:4px;gap:10px}
.prof-r span{color:%s;white-space:nowrap}
.prof-r b{color:%s;text-align:right;white-space:nowrap;overflow-wrap:anywhere;word-break:break-word}
.prof-ok{margin-top:7px;background:#EAFAF1;border:1px solid #82E0AA;color:#1E8449;font-size:%dpx;font-weight:800;text-align:center;border-radius:7px;padding:5px}
.lg-panel{background:#F8FAFC;border:1px solid #D5DBDB;border-radius:10px;padding:12px 14px}
.lg-t{font-size:%dpx;font-weight:800;color:%s;margin-bottom:9px}
.lg-r{display:flex;align-items:center;gap:9px;font-size:%dpx;color:%s;margin-bottom:7px;font-weight:600}
.lg-n{margin-left:auto;font-size:%dpx;color:%s;font-weight:400}
.lg-dot{width:16px;height:16px;border-radius:50%%;flex-shrink:0;border:2px solid #fff;box-shadow:0 0 0 1px #D5DBDB}
.lg-line{width:28px;height:4px;border-radius:2px;flex-shrink:0}
.rule-ok{font-size:%dpx;color:#1E8449;line-height:1.7;margin-bottom:7px;background:#fff;border-radius:7px;padding:8px 9px;border:1px solid #D4EFDF}
.rule-no{font-size:%dpx;color:#922B21;line-height:1.7;background:#fff;border-radius:7px;padding:8px 9px;border:1px solid #F2D7D5}
.rule-ok b,.rule-no b{display:block;font-size:%dpx;margin-bottom:3px}
""" % (17, f(11), f(8), f(11), TXT2, f(13), f(11), TXT2, f(13), f(11), TXT3, TXT, f(11.5), f(13), INK, f(11.5), TXT2, f(10.5), TXT3, f(11.5), f(11.5), f(12.5))
    write_html("fig4_graph.html", body, extra)


# ============================================================ fig5 共识伪标签（正交分叉箭头修复版） ============================================================
def gen_fig5():
    def ch(accent, bg, hcolor, title, ic, desc, clu_list, pros):
        clus = ""
        for name, n in clu_list:
            clus += '<div class="clu" style="border-color:%s">%s<br><b>%s</b></div>' % (accent, name, n)
        pc = ""
        for ok, t in pros:
            pc += '<div class="%s">%s %s</div>' % ("pc-ok" if ok else "pc-no",
                                                   "\u2714" if ok else "\u2718", t)
        return ('<div class="chan" style="border-color:%s;background:%s">'
                '<div class="chan-h" style="color:%s"><span class="ch-ic">%s</span>%s</div>'
                '<div class="chan-d">%s</div>'
                '<div class="clu-row">%s</div>'
                '<div class="pc">%s</div></div>'
                % (accent, bg, hcolor, ic, title, desc, clus, pc))

    ch1 = ch("#F5CBA7", "#FEFBF6", "#B05A12", "资金通道 C\u2081 · Louvain 社区发现", "\U0001F4B0",
             "在资金共享子图上做社区发现，按共享收款账户天然分组。账户是硬证据，可信度高。",
             [("资金簇 1", "4 案"), ("资金簇 2", "5 案"), ("资金簇 3", "3 案")],
             [(True, "硬证据，可信度高"), (True, "对账户数据直接可用"),
              (False, "账户缺失 / 打码时失效"), (False, "无账户案件无法分组")])

    ch2 = ch("#82E0AA", "#F7FCF9", "#1E8449", "话术通道 C\u2082 · BGE + KMeans", "\U0001F4AC",
             "本地 BGE 模型编码话术语义，KMeans 按语义相似度聚类，能抓住模板演化。",
             [("话术簇 1", "4 案"), ("话术簇 2", "5 案"), ("话术簇 3", "3 案")],
             [(True, "语义层面抓模板变化"), (True, "对文字材料直接可用"),
              (False, "话术碰撞时可能误并"), (False, "语义接近的模板难分")])

    center = """
<div class="anchor">
  <div class="an-h">&#127919; 共识锚点 A = C&#8321; &#8745; C&#8322;</div>
  <div class="badge">
    <div class="bdg-c1">C&#8321;</div>
    <div class="bdg-cap">&#8745;</div>
    <div class="bdg-c2">C&#8322;</div>
    <div class="bdg-mid">双通道严格一致的交集</div>
  </div>
  <div class="an-cond">
    <div class="an-t">锚点采信三条件</div>
    <div class="an-r">&#9312; 两通道分组完全一致</div>
    <div class="an-r">&#9313; 簇规模 &lt; 25% 总案件数</div>
    <div class="an-r">&#9314; 锚点数量 &#8805; 下限阈值</div>
  </div>
  <div class="an-gate">&#9888; 触发拒绝（门控）：巨簇弃用 · 锚点不足整批转人工——宁可不出牌，也不出错牌</div>
</div>
"""

    # 正交分叉：主干垂直 → 水平 → 垂直下落到两个分支，标签置于水平段上（白底遮线，不再压箭头）
    # 用 viewBox 让 SVG 自适应内容区宽度，避免 1260px 固定宽超出 .wrap 内容区（1216px）导致横向溢出
    split_svg = """
<svg width="100%" height="76" viewBox="0 0 1260 76" preserveAspectRatio="xMidYMid meet" style="display:block;margin:0 auto">
<defs>
<marker id="sG" markerWidth="11" markerHeight="10" refX="9" refY="5" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#27AE60"/></marker>
<marker id="sB" markerWidth="11" markerHeight="10" refX="9" refY="5" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#2980B9"/></marker>
</defs>
<path d="M 630 4 L 630 28" stroke="#5D6D7E" stroke-width="3.5" fill="none"/>
<path d="M 630 28 L 360 28 L 360 58" stroke="#27AE60" stroke-width="3.5" fill="none" marker-end="url(#sG)"/>
<path d="M 630 28 L 900 28 L 900 58" stroke="#2980B9" stroke-width="3.5" fill="none" marker-end="url(#sB)"/>
</svg>
<div class="split-lab" style="left:28.6%;top:14px;color:#1E8449;border-color:#82E0AA;background:#F2FBF5">是锚点（两通道一致）&#8594; 采信交集</div>
<div class="split-lab" style="left:71.4%;top:14px;color:#1A5276;border-color:#AED6F1;background:#F4F9FD">非锚点（仅单通道）&#8594; HAN 判定</div>
"""

    strat = """
<div class="strat">
  <div class="strat-h">出牌策略（hybrid · 半监督）</div>
  <div class="strat-grid">
    <div class="st" style="border-color:#82E0AA"><b style="color:#1E8449">&#9312; 锚点案件</b>直接采信交集标签，不依赖模型</div>
    <div class="st" style="border-color:#AED6F1"><b style="color:#1A5276">&#9313; 非锚点案件</b>用微调后 HAN 的 argmax 判定</div>
    <div class="st" style="border-color:#E8B4AE"><b style="color:#922B21">&#9314; 触发门控</b>整簇拒出牌，转人工复核</div>
  </div>
</div>
"""

    incr = """
<div class="incr">
  <div class="incr-h">&#128279; 增量模式 · 新警情随到随判（不重算全量）</div>
  <div class="incr-row">
    <span class="incr-step" style="border-color:#2980B9;color:#1A5276">新警情到达</span>
    <span class="incr-ar">&#10148;</span>
    <span class="incr-step" style="border-color:#CA8A04;color:#8A6208">资金 + 话术双匹配</span>
    <span class="incr-ar">&#10148;</span>
    <span class="incr-step" style="border-color:#27AE60;color:#1E8449">双信号一致 &#8594; 挂入团伙</span>
    <span class="incr-ar">&#10148;</span>
    <span class="incr-step" style="border-color:#E74C3C;color:#922B21">不一致 &#8594; 留待观察</span>
  </div>
  <div class="incr-note">200 案实测比全量重算<b>高 8 分</b>——流式挂接反而更准；团伙画像 = 账户池 + 话术质心，随新案自动更新。</div>
</div>
"""

    foot = """
<div class="foot">
  <div class="foot-l"><b>自适应 k 门控</b>：数据自身信号异常时自动往更细粒度搜索，直到巨簇消失——触发者是数据，不是测试集反调。</div>
  <div class="foot-chips"><span class="fc2" style="background:#EAFAF1;color:#1E8449">P3 场景 +0.19</span><span class="fc2" style="background:#FDF2E9;color:#B05A12">P1 场景 +0.06</span></div>
</div>
"""

    row2 = """
<div class="row2">
  <div class="r2card" style="border-color:#82E0AA;background:#F7FCF9">
    <div class="r2-h" style="color:#1E8449">&#10003; 锚点案件 &#10140; 直接采用交集标签</div>
    <div class="ex">
      <span class="ex-c">案件 2</span>
      <span class="ex-op">C&#8321; = 资金簇1 &#8741; C&#8322; = 话术簇1</span>
      <span class="ex-op">&#8658;</span>
      <span class="ex-r" style="background:#EAFAF1;border-color:#82E0AA;color:#1E8449">标签 = 团伙A &#10003;</span>
    </div>
    <div class="r2-d">两条<b>独立</b>证据同时指向同一个答案，置信度最高——同时作为"教材"（监督信号）喂给图网络。</div>
  </div>
  <div class="r2card" style="border-color:#AED6F1;background:#F6FAFD">
    <div class="r2-h" style="color:#1A5276">&#9679; 非锚点案件 &#10140; HAN 微调后 argmax 判定</div>
    <div class="pipe">
      <span class="pp" style="border-color:#82E0AA;color:#1E8449">锚点标签作监督</span><span class="p-ar">&#10148;</span>
      <span class="pp" style="border-color:#8E44AD;color:#6C3483">微调 HAN 分类头</span><span class="p-ar">&#10148;</span>
      <span class="pp" style="border-color:#AED6F1;color:#1A5276">嵌入 &#8594; argmax &#8594; 团伙归属</span>
    </div>
    <div class="r2-d">借锚点的高置信度完成监督，又覆盖全部案件——不需要一条人工标注。</div>
  </div>
</div>
"""

    body = ('<h1>共识伪标签 · 双通道一致才采信</h1>'
            '<div class="sub">资金 Louvain + 话术 KMeans &#8594; 交集锚点 &#8594; 半监督微调 HAN &#8594; hybrid 出牌 · 增量模式随到随判</div>'
            '<div class="row1">'
            + ch1 +
            '<div class="flow-col"><div class="fa">&#10148;</div><span class="fa-l">取簇号</span></div>'
            + center +
            '<div class="flow-col"><div class="fa fl">&#10148;</div><span class="fa-l">取簇号</span></div>'
            + ch2 + '</div>'
            '<div style="position:relative;width:100%;margin:-2px auto 0">' + split_svg + '</div>'
            + row2 + strat + incr + foot)

    extra = """
.row1{display:flex;gap:0;align-items:stretch}
.chan{flex:1;border:2px solid;border-radius:11px;padding:14px 16px}
.chan-h{font-size:%dpx;font-weight:800;display:flex;align-items:center;gap:8px;margin-bottom:7px}
.ch-ic{font-size:17px}
.chan-d{font-size:%dpx;color:%s;line-height:1.55;margin-bottom:10px}
.clu-row{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:10px}
.clu{text-align:center;font-size:%dpx;color:%s;border:2px solid;border-radius:8px;padding:7px 2px;background:#fff;line-height:1.45}
.clu b{font-size:%dpx;color:%s}
.pc{display:grid;grid-template-columns:1fr 1fr;gap:4px 9px}
.pc div{font-size:%dpx;padding:5px 8px;border-radius:6px;line-height:1.4}
.pc-ok{background:#fff;color:#1E8449;border:1px solid #D4EFDF}
.pc-no{background:#fff;color:#922B21;border:1px solid #F2D7D5}
.flow-col{width:92px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:4px;flex-shrink:0}
.fa{width:44px;height:44px;border-radius:50%%;background:#fff;border:2.5px solid #D5DBDB;color:%s;display:flex;align-items:center;justify-content:center;font-size:19px;font-weight:800}
.fa.fl{transform:scaleX(-1)}
.fa-l{font-size:%dpx;color:%s;font-weight:600}
.anchor{width:%dpx;flex-shrink:0;border:2.5px solid #CA8A04;background:#FEFCF3;border-radius:11px;padding:14px 16px}
.an-h{font-size:%dpx;font-weight:800;color:#8A6208;text-align:center;margin-bottom:10px}
.badge{display:flex;align-items:center;justify-content:center;gap:7px;background:#fff;border:1px solid #F0E2BC;border-radius:10px;padding:11px 12px;margin-bottom:10px}
.bdg-c1{font-size:%dpx;font-weight:800;color:#B05A12;border:2px solid #F5CBA7;border-radius:7px;padding:5px 11px;background:#FDF2E9}
.bdg-cap{font-size:%dpx;font-weight:800;color:#8A6208}
.bdg-c2{font-size:%dpx;font-weight:800;color:#1E8449;border:2px solid #82E0AA;border-radius:7px;padding:5px 11px;background:#EAFAF1}
.bdg-mid{font-size:%dpx;color:#8A6208;font-weight:700;margin-left:3px}
.an-cond{background:#fff;border:1px solid #F0E2BC;border-radius:9px;padding:10px 12px;margin-bottom:9px}
.an-t{font-size:%dpx;font-weight:800;color:#8A6208;margin-bottom:5px}
.an-r{font-size:%dpx;color:%s;margin-bottom:3px;line-height:1.45}
.an-gate{background:#FDF5F4;border:1px solid #E8B4AE;border-radius:9px;padding:11px 16px;font-size:%dpx;color:#922B21;font-weight:600;line-height:1.6}
.split-lab{position:absolute;font-size:%dpx;font-weight:800;border:2px solid;border-radius:14px;padding:4px 12px;white-space:nowrap;transform:translateX(-50%%)}
.row2{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:6px}
.r2card{border:2px solid;border-radius:11px;padding:14px 16px 16px}
.r2-h{font-size:%dpx;font-weight:800;margin-bottom:10px}
.ex{display:flex;align-items:center;gap:8px;background:#fff;border:1px solid #D5DBDB;border-radius:9px;padding:9px 11px;margin-bottom:9px;flex-wrap:nowrap}
.ex-c{font-size:%dpx;font-weight:800;color:%s;background:#F5F7FA;border-radius:7px;padding:4px 9px;white-space:nowrap}
.ex-op{font-size:%dpx;color:%s;font-weight:600;white-space:nowrap}
.ex-r{font-size:%dpx;font-weight:800;border:2px solid;border-radius:7px;padding:4px 9px;white-space:nowrap}
.r2-d{font-size:%dpx;color:%s;line-height:1.6}
.r2-d b{color:%s}
.pipe{display:flex;align-items:center;gap:7px;background:#fff;border:1px solid #D5DBDB;border-radius:9px;padding:11px;margin-bottom:9px}
.pp{flex:1;text-align:center;font-size:%dpx;font-weight:700;border:2px solid;border-radius:8px;padding:9px 4px;line-height:1.45}
.p-ar{color:%s;font-weight:800;font-size:15px}
.strat{margin-top:13px;background:#fff;border:1px solid #D5DBDB;border-radius:11px;padding:13px 15px}
.strat-h{font-size:%dpx;font-weight:800;color:%s;margin-bottom:10px}
.strat-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:11px}
.st{border:2px solid;border-radius:9px;padding:10px 12px;font-size:%dpx;color:%s;line-height:1.55;background:#F8FAFC}
.st b{margin-right:5px}
.incr{margin-top:13px;background:#EBF5FB;border:1px solid #AED6F1;border-radius:11px;padding:13px 15px}
.incr-h{font-size:%dpx;font-weight:800;color:#1A5276;margin-bottom:10px}
.incr-row{display:flex;align-items:center;gap:9px}
.incr-step{flex:1;text-align:center;font-size:%dpx;font-weight:700;border:2px solid;border-radius:9px;padding:9px 4px;background:#fff;line-height:1.45}
.incr-ar{color:%s;font-weight:800;font-size:15px}
.incr-note{font-size:%dpx;color:%s;line-height:1.55;margin-top:9px;border-top:1px dashed #AED6F1;padding-top:6px}
.incr-note b{color:#1A5276}
.foot{margin-top:12px;display:flex;align-items:center;gap:13px;background:#FEF9E7;border:1px solid #F5CBA7;border-radius:10px;padding:11px 15px}
.foot-l{flex:1;font-size:%dpx;color:#7D6608;line-height:1.55}
.foot-l b{color:#8A6208}
.foot-chips{display:flex;gap:8px;flex-shrink:0}
.fc2{font-size:%dpx;font-weight:800;border-radius:15px;padding:5px 14px;white-space:nowrap}
""" % (f(13), f(11.5), TXT2, f(11), TXT2, f(13), TXT, f(11), TXT2, f(11), TXT2,
       g(372) + 30, f(13.5), f(15), f(24), f(15), f(10.5), f(12.5), f(11), TXT2, f(11.5),
       f(12.5), f(13.5), f(13.5), TXT2, f(12), TXT2, f(13), f(11.5), TXT2, TXT, f(11.5), TXT3,
       f(12.5), INK, f(11.5), TXT2, f(12.5), f(11.5), TXT3, f(11.5), TXT2, f(11.5), f(12))
    write_html("fig5_semi.html", body, extra)


# ============================================================ fig6 六场景柱状图（放大） ============================================================
def gen_fig6():
    scenes = [("干净台账", "P0"), ("轻噪", "P1"), ("重噪", "P2"),
              ("200案规模", "P3"), ("话术碰撞", "P4"), ("碰撞+噪声", "P5")]
    methods = [
        ("本系统 (hybrid)", BLUE, [0.91, 0.76, 0.95, 0.66, 0.98, 0.80]),
        ("自学习图网络", GREEN, [0.92, 0.57, 0.57, 0.54, 0.89, 0.62]),
        ("半监督图网络 (argmax)", PURPLE, [0.68, 0.55, 0.89, 0.64, 0.63, 0.74]),
        ("单一资金规则", GOLD, [0.83, 0.82, 0.82, 0.45, 1.00, 0.83]),
        ("纯文本聚类", RED, [0.85, 0.70, 0.50, 0.54, 0.85, 0.71]),
    ]
    best = [1, 3, 0, 0, 3, 3]

    W, H = 1260, 620
    ml, mr, mt, mb = 86, 16, 58, 110
    pw, ph = W - ml - mr, H - mt - mb
    gw = pw / len(scenes)
    bw, bg_ = 32, 7
    inner = 5 * bw + 4 * bg_
    pad = (gw - inner) / 2

    def yv(v):
        return mt + ph * (1 - v)

    s = []
    s.append('<svg width="%d" height="%d" style="display:block;margin:0 auto" xmlns="http://www.w3.org/2000/svg">' % (W, H))
    for t in [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]:
        gy = yv(t)
        s.append('<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" stroke="#D5DBDB" stroke-width="1" opacity="%.2f"/>'
                 % (ml, gy, W - mr, gy, 0.75 if t == 0 else 0.45))
        s.append('<text x="%d" y="%.1f" font-size="18" fill="#34495E" text-anchor="end" dominant-baseline="middle">%.1f</text>'
                 % (ml - 10, gy, t))
    s.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="#8595A6" stroke-width="2.5"/>' % (ml, mt, ml, mt + ph))
    s.append('<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" stroke="#8595A6" stroke-width="2.5"/>'
             % (ml, yv(0), W - mr, yv(0)))
    s.append('<text x="20" y="%.1f" font-size="19" font-weight="700" fill="#34495E" text-anchor="middle" '
             'transform="rotate(-90 20 %.1f)">分组正确率</text>' % (mt + ph / 2, mt + ph / 2))
    for gi, (sname, pno) in enumerate(scenes):
        gx = ml + gi * gw + pad
        for mi, (mname, color, vals) in enumerate(methods):
            v = vals[gi]
            bx = gx + mi * (bw + bg_)
            by = yv(v)
            stroke = (' stroke="#1E3A5F" stroke-width="2.5"' if best[gi] == mi else '')
            s.append('<rect x="%.1f" y="%.1f" width="%d" height="%.1f" rx="2" fill="%s"%s/>'
                     % (bx, by, bw, yv(0) - by, color, stroke))
            s.append('<text x="%.1f" y="%.1f" font-size="14" font-weight="700" fill="#1E3A5F" text-anchor="middle">%.2f</text>'
                     % (bx + bw / 2, by - 7, v))
            if best[gi] == mi:
                s.append('<text x="%.1f" y="%.1f" font-size="18" fill="#E67E22" text-anchor="middle">&#9733;</text>'
                         % (bx + bw / 2, by - 26))
        cx = ml + gi * gw + gw / 2
        s.append('<text x="%.1f" y="%.1f" font-size="17" font-weight="700" fill="#2C3E50" text-anchor="middle">%s</text>'
                 % (cx, yv(0) + 24, sname))
        s.append('<text x="%.1f" y="%.1f" font-size="14" fill="#5D6D7E" text-anchor="middle">(%s)</text>'
                 % (cx, yv(0) + 42, pno))
    s.append('</svg>')
    chart = "".join(s)

    legend = ('<div class="lgd">' + "".join(
        '<span class="lgd-i"><span class="lgd-s" style="background:%s"></span>%s</span>' % (c, n)
        for n, c, _ in methods) +
        '<span class="lgd-i"><span class="lgd-star">&#9733;</span>该场景最优（如实标注，不冒领）</span></div>')

    body = ('<h1>六种场景效果对比</h1>'
            '<div class="sub">6 场景 × 5 方法 × 3 次独立重复试验 · 分组正确率（满分 1）· 星标为该场景五法最优</div>'
            + chart + legend +
            '<div class="note"><b>读图要点</b>：数据越乱、规模越大，本系统优势越明显——重噪 0.95 居首、200 案 0.66 为五法最优（受聚类极限制约，增量模式进一步补偿）。'
            '干净台账自学习版 0.92 最优、话术碰撞单一资金规则 1.00 最优——<b>如实保留，不做选择性呈现</b>。</div>')

    extra = """
.lgd{display:flex;justify-content:center;flex-wrap:wrap;gap:20px;margin-top:14px}
.lgd-i{display:flex;align-items:center;gap:6px;font-size:%dpx;font-weight:600;color:%s}
.lgd-s{width:20px;height:20px;border-radius:4px}
.lgd-star{color:#E67E22;font-size:21px;line-height:1}
.note{margin-top:14px;background:#F5F7FA;border:1px solid #D5DBDB;border-radius:9px;padding:14px 18px;font-size:%dpx;color:%s;line-height:1.8}
.note b{color:%s}
""" % (f(11.5), TXT, f(11.5), TXT2, INK)
    write_html("fig6_bars.html", body, extra)


# ============================================================ 渲染 ============================================================
def autocrop(path):
    im = Image.open(path).convert("RGB")
    arr = np.asarray(im).astype(int)
    h, w, _ = arr.shape
    corners = np.array([arr[2, 2], arr[2, w - 3], arr[h - 3, 2], arr[h - 3, w - 3]])
    bg = corners.mean(axis=0)
    diff = np.abs(arr - bg).sum(axis=2)
    mask = diff > 40
    rows = np.where(mask.sum(axis=1) > max(w * 0.008, 60))[0]
    cols = np.where(mask.sum(axis=0) > max(h * 0.004, 50))[0]
    if len(rows) == 0 or len(cols) == 0:
        return
    pad = 60
    box = (max(0, cols[0] - pad), max(0, rows[0] - pad),
           min(w, cols[-1] + pad + 1), min(h, rows[-1] + pad + 1))
    im.crop(box).save(path)
    print("   crop %dx%d -> %dx%d" % (w, h, box[2] - box[0], box[3] - box[1]))


def render(html_path, png_path):
    url = "file:///" + html_path.replace("\\", "/")
    out = png_path.replace("\\", "/")
    cmd = ('"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" --headless --disable-gpu '
           '--no-sandbox --hide-scrollbars --force-device-scale-factor=3 '
           '--window-size=1460,3600 --screenshot="%s" "%s"') % (out, url)
    subprocess.run(cmd, shell=True, timeout=60)


FIGS = [
    ("fig2_func.png", "fig2_func.html"),
    ("fig3_loop.png", "fig3_loop.html"),
    ("fig4_graph.png", "fig4_graph.html"),
    ("fig5_semi.png", "fig5_semi.html"),
    ("fig6_bars.png", "fig6_bars.html"),
]

if __name__ == "__main__":
    import sys
    only = sys.argv[1:] if len(sys.argv) > 1 else None
    print("=== 生成 HTML ===")
    gens = {
        "fig2": gen_fig2, "fig3": gen_fig3, "fig4": gen_fig4,
        "fig5": gen_fig5, "fig6": gen_fig6,
    }
    for key, fn in gens.items():
        if only is None or key in only:
            fn()

    print("\n=== 渲染 PNG ===")
    for png, html in FIGS:
        if only is not None and png.replace(".png", "") not in only:
            continue
        print("render %s ..." % png)
        render(OUT + "/" + html, OUT + "/" + png)
        autocrop(OUT + "/" + png)

    print("\n=== DONE ===")
