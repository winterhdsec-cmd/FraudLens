# FraudLens ArXiv 研究日志

> 追踪方向：多智能体编排 + 异构图神经网络（HAN/GraphSAGE）反诈团伙发现 / 资金链（AML、fund_flow、回流闭环）。
> 维护规则：每次讨论的论文追加到此文件，格式见 ArXiv Watcher 规范。

### [2026-07-26] Heterogeneous Graph Attention Network (HAN)
- **Authors**: Xiao Wang, Houye Ji, Chuan Shi, Bai Wang, Peng Cui et al.
- **Link**: http://arxiv.org/abs/1903.07293
- **Summary**: 提出层级注意力（节点级+语义级）的异构图神经网络，按元路径聚合邻居并学习不同元路径重要性。本项目 HAN 模块的基石；Stage2(#6) 已把 4 条元路径从"复用同一邻接矩阵"真修为各自独立子图（case-account-case / case-perpetrator-case / case-type-case / case-city-case）。

### [2026-07-26] Enhancing GNN-based Fraud Detectors against Camouflaged Fraudsters (CARE-GNN)
- **Authors**: Yingtong Dou, Zhiwei Liu, Li Sun, Yutong Deng, Hao Peng et al.
- **Link**: http://arxiv.org/abs/2008.08692
- **Summary**: 指出欺诈者"特征伪装+关系伪装"会破坏 GNN 聚合，提出标签感知相似度+强化学习选邻居的 CARE-GNN。直接对标本项目 cross_gang_account_share（跨团伙共享收款账户即"关系伪装"）；当前 HAN 未做伪装鲁棒，是明确短板。

### [2026-07-26] Alleviating the Inconsistency Problem of Applying GNN to Fraud Detection (GraphConsis)
- **Authors**: Zhiwei Liu, Yingtong Dou, Philip S. Yu, Yutong Deng, Hao Peng
- **Link**: http://arxiv.org/abs/2005.00625
- **Summary**: 系统提出欺诈检测中的"上下文/特征/关系"三类不一致，用一致性打分过滤邻居。本项目节点特征多为 hash 类 one-hot（victim/phone/type/city），信息量近随机，正是"特征不一致"问题；Stage1 已对 account/perpetrator 去 hash，但其余节点仍待补。

### [2026-07-26] Finding Money Launderers Using Heterogeneous Graph Neural Networks
- **Authors**: Fredrik Johannessen, Martin Jullum
- **Link**: http://arxiv.org/abs/2307.13499
- **Summary**: 首个在大型真实异构网络（DNB 银行交易+企业角色）上用 GNN 做反洗钱的工作，把 MPNN 扩展到异构图并提出跨边聚合方法。与本项目"资金链"方向最直接对标——account/perpetrator/fund_flow 节点边设计与之同源；区别在于本项目用合成数据且无真实银行授权数据。

### [2026-07-26] LineMVGNN: Anti-Money Laundering with Line-Graph-Assisted Multi-View GNN
- **Authors**: Chung-Hoo Poon, James Kwok, Calvin Chow, Jang-Hyeon Choi
- **Link**: http://arxiv.org/abs/2603.23584
- **Summary**: 用有向交易图（digraph）+ 收/付款双向消息传递 + line-graph 视图增强资金流传播，做 AML。关键启示：本项目主图刻意保持"无向"以零改 HAN/社区接口，但方向性（fund_flow 有向边）未被 GNN 充分利用——加有向/line-graph 视图是强差异化卖点。

### [2026-07-26] Detecting Credit Card Fraud via Heterogeneous GNN with Graph Attention
- **Authors**: Qiuwu Sha, Tengda Tang, Xinyu Du, Jie Liu, Yixian Wang et al.
- **Link**: http://arxiv.org/abs/2504.08183
- **Summary**: 异构交易图（用户/商户/交易多节点）+ 图注意力动态加权 + 时间衰减机制 + SMOTE/代价敏感应对样本不平衡。时间衰减机制可直接迁移到本项目 fund_flow（含时间属性）的边权重/聚合中。

### [2026-07-26] Crowdsourcing Fraud Detection over Heterogeneous Temporal MMMA Graph (CMT)
- **Authors**: Zequan Xu, Qihang Sun, Shaofeng Hu, Jieming Shi, Hui Li
- **Link**: http://arxiv.org/abs/2308.02793
- **Summary**: 在异构时序图(HTG)上用自监督对比学习同时捕捉异质性与动态性。启示：本项目图目前是静态快照，若民警提供时间序列案件，可加动态/时序视图提升近期团伙活动捕获。

### [2026-07-26] Detection, Attribution, Narration: An End-to-End Pipeline for Explainable Money Mule Identification
- **Authors**: Yuge Zhang, Yuanxing Zhang, Yichao Jin et al.
- **Link**: http://arxiv.org/abs/2607.17586
- **Summary**: 三阶段可解释流水线：LightGBM(280 特征) → TreeSHAP 归因 → LLM 生成分析师可读叙述。与本项目多智能体(analyst→cluster→chat)+客观置信度门控高度同源；其 SHAP 归因思路可借鉴来让"客观置信度"更可解释、更抗争议。

### [2026-07-26] Forensic Schema for Psychological Manipulation in Cyber Fraud: LLM-Driven Victim Reports Analysis
- **Authors**: Zikai Alex Wen, Corrazon Ogot, Juan Li, Yan Bai
- **Link**: http://arxiv.org/abs/2607.07751
- **Summary**: 用 LLM 从受害者报告抽取心理操纵指标（κ=0.69 对齐人类标注），做取证式话术分析。这正是本项目 analyst 智能体分析诈骗话术的角色；但与公安大学"LLM+语义聚类分析话术"论文重叠，须明确差异化：本项目 LLM 提取的语义/BGE 嵌入仅作"分析层特征"，真正团伙发现靠资金链拓扑+GNN。

### [2026-07-26] Graph Neural Networks for Financial Fraud Detection: A Review
- **Authors**: Dawei Cheng, Yao Zou, Sheng Xiang, Changjun Jiang
- **Link**: http://arxiv.org/abs/2411.05815
- **Summary**: 统一框架综述 100+ 篇 GNN 金融欺诈检测研究，分图构建/模型/部署/设计考量。论文 Related Work 必引；可据此把工作定位在"异构图构建 + 无/半监督 GNN + 有向 AML + LLM 话术分析"四支的交叉整合点。
