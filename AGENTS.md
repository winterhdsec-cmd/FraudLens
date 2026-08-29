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
- 已知边界（诚实，不许在申报材料里掩盖）：干净数据 P0 上 hybrid 0.89 < selfsup 1.00（锚点过分裂，轮廓系数选 k 偏细所致，tau 合并实验证明救不了，已决定不做脆弱调参）；200 案规模全方法失效（Louvain 分辨率极限，res=2.0 可缓解但有测试集调参嫌疑，暂作论文 limitation + 消融素材）。

## 待办（按顺序）

1. **3-seed 全量实验**（可能已完成）：`cd E:/FraudLens/backend/gnn && "C:/Users/hd/AppData/Local/Programs/Python/Python310/python.exe" experiment_semi.py --seeds 42,7,2024 --out experiment_semi_results.json`，日志 `experiment_semi_full.log`。完成后把 mean±std 表更新进 docs/算法层交接.md 与申报书素材。
2. **增量匹配**（下一个算法任务，方案已定）：现状是 `routes/gangs.py::api_detect_gangs_gnn` 每次 `query(Case).all()` 全库重聚类。改法：新增团伙画像聚合（账户池+话术质心，GangCaseRelation 已落库）→ 新案先与已知画像匹配（资金共享 + BGE 余弦，复用共识门控阈值哲学），挂不上的攒批才重聚类。目标 2-3 天，做完在 200 案合成数据上验证"增量模式下效果不掉"。
3. 申报书正文（用户判断：打磨很快，素材齐后半天可出）。
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
