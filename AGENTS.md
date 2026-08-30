# AGENTS.md — FraudLens 项目 AI 协作指令

_任何 AI 助手（TRAE / WorkBuddy / Cursor / Claude 等）在本仓库工作前，必须先读完本文件。_

## 项目是什么

FraudLens：面向公安反诈中心的智能辅助研判系统。上传诈骗线索（话术文本/CSV/截图）→ 多智能体流水线分析 → 基于图神经网络（GNN）在异构图（案件-受害者-手机号-诈骗类型-城市）上发现诈骗团伙。

当前目标（按优先级）：
1. 2026 国创赛（高教主赛道·本科生组·创意组·人工智能+类别）。**校内报名 9/15 截止，9/17 评审**；国赛系统 9/25 截止。
2. 中文论文一篇："基于多智能体与图神经网络的反诈团伙发现"（打比赛 + 院级科研用，不冲核心/顶刊）。
3. 方法类发明专利 1-2 件，主张落在"多智能体反思闭环"与"客观置信度门控"。先申请占优先权日，论文后发（避免公开破坏新颖性）。

## 环境（勿猜，照抄）

- 项目根目录：`E:\FraudLens`（后端 `backend/`，前端 `frontend/` Vue3，GNN 实验 `backend/gnn/`）
- **跑实验只用**：`C:/Users/hd/AppData/Local/Programs/Python/Python310/python.exe`（CPU-only torch）。不要用 `backend/venv`，那是运行时环境不是实验环境。
- Windows + Git Bash。文件路径一律用正斜杠 `/`。
- BGE 模型本地路径：`backend/bge-large-zh-v1.5`（真模型，已接通，禁止外部 API 上传案件数据）。

## 必须记住的事实（旧文档有误导，以代码为准）

- 编排层现为 LangGraph StateGraph 真反思闭环（`backend/agents/orchestrator.py:27`），早期"没用 LangGraph、手写顺序编排器"的描述已过时。改任何编排逻辑前先读代码。
- GNN（GraphSAGE / HAN）已真实跑通，是核心亮点。
- **2026-08-29 重大修正**：当天 15:00 之前产出的所有 HAN/消融/阈值实验结论**全部作废**——当时文本通道静默降级用 hash 向量冒充 BGE 语义嵌入（任意两案余弦≈0.036），且 `hash()` 逐进程随机化导致结果不可复现。两坑均已修（`graph_builder.py` 的 `_direct_bge_encode` + `_det_hash`）。可信基线数据从 `probe_v5_realbge.json` 开始。
- HAN 的元路径邻接已改为 5 条独立矩阵；语义注意力是否真正生效仍未严格验证，动它之前先做消融。

## 已完成的算法层工作（2026-08-29，详见 docs/算法层交接.md）

- P1：种子固定 + sha256 确定性 hash → 跨进程完全可复现（已验证 PYTHONHASHSEED=0/7 结果一致）。
- P2：BYOL 免负样本预训练分支（`han_model.py` `mode="byol"`），默认仍是 GraphCL。
- P3：**共识伪标签半监督**（核心成果，申报书主推）：资金链 Louvain + 话术 BGE-KMeans 严格一致的交集作高置信锚点（>25% 案件数的巨社区弃用——"客观置信度门控"落地），锚点监督微调 HAN 分类头，hybrid 出牌（锚点用标签、非锚点 GNN argmax）。代码：`eval_framework.py` 的 `_consensus_anchor_labels` / `baseline_gnn_han_semi`。
- 已知边界（诚实，不许在申报材料里掩盖；数字为**自适应 k 全量版 22:43**，完整表见 docs/算法层交接.md 第二节）——① 干净 P0：hybrid 0.913 < selfsup 0.922（锚点仍略分裂，tau 合并实验证明无稳健修法，不作脆弱调参，作 limitation）；② 200 案 P3：hybrid **0.656** 已是该规模最优方法，但绝对水平仍低于 40 案场景（Louvain 分辨率极限）→ 主要靠增量匹配架构解决（待办#2），非继续调 res；③ P1 轻噪：fund(规则) 0.819 仍反超 hybrid 0.756——规则在轻噪下本就很强，半监督价值在重噪/碰撞场景更突出；④ P5 极端信号：seed7 曾触发"共识锚点不足"门控拒出牌，adaptive k 后恢复出牌（0.555 仍弱）——门控有效防止脏锚点扩散，P5 均值已恢复 n=3，极端 seed 绝对低值作 limitation 保留、勿掩盖。
- **P4 自适应 k 门控优化（2026-08-30，已完成，全量 3-seed 22:43 落盘 `experiment_semi_results.json`）**：P1/P3 轻噪场景下，轮廓系数低估话术 k → 共识巨簇超 25% 门控被整类弃用 → 锚点覆盖仅 0.6/0.54。`eval_framework.py::_consensus_anchor_labels` 新增"巨簇触发 k 重估"：默认 k 下存在巨簇时，沿更细 k 扫描到"无巨簇弃用"为止（数据自身触发，非测试集反推）。seed42 快验 P1 hybrid 0.582→0.775、P3 hybrid 0.382→0.660；**全量重跑：P3 0.4655→0.6561（+0.19）、P1 0.6922→0.7564、P0 hybrid 0.812→0.913，P5 由 n=2 恢复 n=3（seed7 门控缓解）；P2/P4 无巨簇、结果不变（0.9487/0.9811）**。完整 mean±std 表见 docs/算法层交接.md 第二节。

## 待办（按顺序）

1. **✔ 3-seed 全量实验已完成（自适应 k 版，22:43 落盘 `experiment_semi_results.json` + 日志 `experiment_semi_adaptive.log`）**：mean±std 表已回填 docs/算法层交接.md。自适应 k 全量生效——P3 0.4655→0.6561、P1 0.6922→0.7564、P5 恢复 n=3；P2 重噪 hybrid 0.949±0.041 仍为主推，P0 干净 selfsup 0.922 最优，P4 hybrid 0.981。 `experiment_semi.py` 已加**增量落盘 + `--resume` 断点续跑**（损失收敛到单个 seed）。申报书素材数字已就位。
2. **✔ 增量匹配已完成**（实现 + 验证，详见 docs/算法层交接.md 第四节）：`backend/gnn/incremental_matcher.py`（团伙画像=账户池+BGE话术质心，资金共享+话术余弦**双信号一致**才挂，宁缺毋滥）+ `routes/gangs.py` 接入 `mode='auto'|'full'` + 顺带修复 `graph_builder` 账户 dict bug（`str(dict)` 导致 share_account 从未触发）。Louvain 模式两预设验证：**P3 轻噪 200 案增量反超全量 8 分**（0.609 vs 0.526——阶段一 Louvain 过合并 6 团，流式补回 10 团）；**P2 重噪低 6 分**（25% 无账户案件单信号不采信→攒批丢召回，门控有意取舍）。验收口径"账户信号足的数据上效果不掉"成立。
3. **✔ 申报书已出黑白学术版（v11 定稿，13 页质检全过）**（2026-08-30 深夜）：`docs/项目计划书（已填写）.docx`，生成脚本 `docs/fill_template_v2.py`（幂等整体重写，改格式只动脚本再重跑管线 docx→PDF→PNG 逐页复检，管线须带 `$LASTEXITCODE` 守卫）。排版铁律：正文纯黑白、颜色只进配图；标题严格"一、/（一）/1./（1）"四级论文体系；上图下表（图题/表题一律置上，表注按学术惯例置下）、三线表。v11 轮已完成：全文去口语化（三种子/种子7/半监督混合策略/纯CPU环境，删"落盘"等黑话）、图题置上且题图同页、表1 单页+表注整段不拆行。关键机制（Word 对图片段落和单元格内段落均不执行 keepNext/keepLines，唯一可靠=表格行级 `cantSplit`）：图题+图、表注块各自包进无边框单格嵌套表并 cantSplit，`_squash_after_tbl` 压掉 add_table 尾随空段落的空白。"图内 PNG 小表英文（hybrid/fund）被目检误判为 Word 表内容"是坑，拿不准用 pypdfium2 提取 PDF 文本层核实。写作与排版规范已固化为 Skill `contest-proposal-writing`（用户级 `~/.trae-cn/skills/`，v11 机制已全部回填）。剩余：用户次日内容纠错；fig6 等 PNG 图内英文小表风格是否统一改，待用户拍板。
4. 反诈中心走访调研（补申报书"个人成长 30 分"的实证短板，警校身份是护城河）。

## 前端 / UI 线（2026-08-29，详见 docs/前端UI交接.md）

用户反馈的 10 个前端可视性问题已全部处理并推送（commit `39b4ad9`）。接手前端前先读 `docs/前端UI交接.md`，尤其第二节"关键陷阱"（reportlab 中文字体/全表 FONTNAME、rd-* 类名前缀防污染、路由名 capital-flow、auth 前缀、token 走 store.js、中文 gang_id 需 URL 编码）。UI 线遗留待办（用户表 stress_user 未删、团伙 docx 缺接口、#8 功能收敛待拍板）列在该文档第五节。UI 改动与上面算法待办互不重叠，勿混提交。

## 协作风格（项目所有者要求）

- 默认中文，直接给结论，不绕弯。技术深度优先于文采。
- 明确区分"已实现"与"建议/待办"，不夸大已实现能力——2026 国创赛评审对无实证材料一票否决。
- 代码改动前先讲改动点 + 回归风险，再给实现。
- 实验基线至少四组（KMeans / HDBSCAN-only / 纯语义聚类 / 当前 GNN）+ 消融（去反思回退、去 GNN、去置信度门控）。
- 学术用语贴近公安反诈一线（串并案、引流/实施/洗钱、话术模板）。
- 方案按"学生数周内可完成"的工程量给，避免需大型算力或商业数据。
- 个人信息本地处理为前提，不主动上传外部 API（除已声明的 DeepSeek 云端分析）。
