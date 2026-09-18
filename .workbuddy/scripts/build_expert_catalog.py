# -*- coding: utf-8 -*-
import json, os

cache = os.path.expanduser("~/.workbuddy/app/cache/experts")
d = json.load(open(os.path.join(cache, "manifest.json"), encoding="utf-8"))

cats = {c["id"]: c.get("name", {}).get("zh", c.get("name", {}).get("en", c["id"])) for c in d["categories"]}
experts = d["experts"]

def zh(o, key):
    v = o.get(key)
    if isinstance(v, dict):
        return v.get("zh") or v.get("en") or ""
    return v or ""

# 与 FraudLens 项目相关的关键词
KW = ["图神经","gnn","图谱","知识图谱","机器学习","深度","大模型","llm","智能体","agent",
       "论文","学术","写作","文档","专利","安全","合规","法务","隐私","反诈","公安",
       "风控","欺诈","测试","质量","评估","实验","架构","开发","代码","数据","分析",
       "聚类","嵌入","表征","自然语言","nlp"]

def relevant(e):
    txt = (zh(e,"profession") + zh(e,"description") + zh(e,"displayName")).lower()
    return any(k.lower() in txt for k in KW)

# 按分类分组
by_cat = {}
for e in experts:
    by_cat.setdefault(e.get("categoryId","?"), []).append(e)

lines = []
lines.append("# WorkBuddy 专家中心目录（共 %d 个专家 / %d 个分类）\n" % (len(experts), len(cats)))
lines.append("> 数据来源：`~/.workbuddy/app/cache/experts/manifest.json`（专家市场快照，缓存于 2026-07-10）\n")
lines.append("> 用法：在 WorkBuddy 左侧「专家」入口按分类浏览，或用专家名/职业搜索。\n")

# 分类统计
lines.append("## 一、14 个分类及专家数量\n")
lines.append("| 分类ID | 分类名 | 专家数 |")
lines.append("|---|---|---|")
for cid in sorted(cats, key=lambda x: len(by_cat.get(x,[])), reverse=True):
    lines.append("| %s | %s | %d |" % (cid, cats[cid], len(by_cat.get(cid,[]))))
lines.append("")

# 全部专家按分类列出
lines.append("## 二、全部专家清单（按分类）\n")
for cid in sorted(cats, key=lambda x: len(by_cat.get(x,[])), reverse=True):
    lines.append("### %s · %s（%d）\n" % (cid, cats[cid], len(by_cat.get(cid,[]))))
    for e in by_cat[cid]:
        prof = zh(e,"profession"); name = zh(e,"displayName"); desc = zh(e,"description")
        lines.append("- **%s**（%s）：%s" % (prof, name, desc))
    lines.append("")

# 与项目相关
rel = [e for e in experts if relevant(e)]
lines.append("## 三、与 FraudLens 项目相关的专家（关键词匹配，共 %d 个）\n" % len(rel))
lines.append("> 关键词：GNN/图神经/知识图谱、机器学习/大模型、论文/学术写作、专利、安全合规、反诈风控、测试评估、多智能体/架构开发、数据分析等。\n")
# 按分类聚合
rel_by = {}
for e in rel:
    rel_by.setdefault(e.get("categoryId","?"), []).append(e)
for cid in sorted(rel_by, key=lambda x: len(rel_by[x]), reverse=True):
    lines.append("### %s · %s\n" % (cid, cats.get(cid, cid)))
    for e in rel_by[cid]:
        prof = zh(e,"profession"); name = zh(e,"displayName"); desc = zh(e,"description")
        lines.append("- **%s**（%s）：%s  \n  - 默认开场：`%s`" % (prof, name, desc, zh(e,"defaultInitPrompt")[:120]))
    lines.append("")

out = os.path.join("E:/FraudLens", "专家目录.md")
with open(out, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
print("written:", out, "total experts:", len(experts), "relevant:", len(rel))
