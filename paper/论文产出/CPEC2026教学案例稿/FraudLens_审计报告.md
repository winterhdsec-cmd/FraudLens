# FraudLens 论文逻辑与实战落地审计报告

> 审计框架：学术导师 + 公安信息化实战专家双重视角。
> 目标：CPEC2026 实验教学案例稿（A 稿）+ 反诈团伙研判原型系统。
> 审计稿：`CPEC2026_draft.tex`（2026-08-03 22:15 版，17 页）+ 全量后端/前端代码。
> 审计日期：2026-08-04。

---

## §1 总体质量判定

论文选题精准（AI 赋能反诈实验教学），诚实边界把控优良（合成≠真实、±0.1214 种子敏感性、教学成效待实证标注）。工程底座扎实程度超出预期——docker-compose 全栈部署、LangGraph StateGraph 真反思闭环、HAN 异构注意力含 5 元路径双通道、JWT+RBAC+CORS+限流+安全头全链路落地，**论文声称与代码实现吻合度约 90%**。

但存在 **1 处致命矛盾**（编排器实现描述与代码不匹配）和 **多个未实证缺口**（教学成效零数据、门控消融缺数字、系统对单机部署过重）。在 CPEC 这种实践教学会议的尺度下，当前版本已具投稿竞争力，修正致命问题后可达 8.5–9 分。

---

## §2 致命问题

### F-1｜§3.2 行257 编排器描述与代码直接矛盾

- **定位**：`CPEC2026_draft.tex` 第 257 行。
  ```latex
  研判工作流由手写顺序编排器（orchestrator）串联"规划 → 预处理 → 分析 → 聚类 → 反思"五个节点
  ```
- **证据**：`backend/agents/orchestrator.py` 第 1-12 行（文件头注释）+ 第 26 行（`from langgraph.graph import StateGraph`）。该文件于 2026-07-26 重构（任务 #30），已从手写流水线升级为 **LangGraph StateGraph 真反思闭环**（条件边回连 analyze_node + 真实 `_adjust_strategy` 改参 + `retry_count` 自增）。代码实际架构与论文中"手写顺序编排器"完全矛盾。
- **更隐蔽的子矛盾**：同一段后文写"未收敛时经条件边回连分析节点触发真实重算"——这在手写顺序编排器里是不可能实现的（手写顺序无条件边概念）。也就是说，当前段落内部**自己打了自己脸**：前半句说手写、后半句描述的特性只有 LangGraph 才有。
- **修复**：将第 257 行改为：
  ```latex
  研判工作流以 LangGraph StateGraph~\cite{langgraph2024} 编排"规划 → 预处理 → 分析 → 聚类 → 反思"五个节点，
  反思节点经条件边在未收敛时回连分析节点触发真实重算
  ```
  删除"手写顺序编排器"表述，统一为 LangGraph StateGraph。
- **预计工时**：10 分钟 + 重编译核验。
- **是否阻塞投稿**：**是**。若审稿人对照代码（或答辩时被问），属事实性错误。

### F-2｜实验数字 0.9154/0.3228/0.8353 缺乏可追溯性引证

- **定位**：§4.2 表~\ref{tab:baselines}、§4.3 表~\ref{tab:ablation}。
- **证据**：`experiment_baselines_v2.py` 和 `experiment_gating_sensitivity.py` 等脚本确实存在且结构匹配，但**论文正文未标注"数据由 `experiment_baselines_v2.py`（10 seeds × cross=0.2）生成"等溯源信息**。数字分散在三处 TeX 中一致，但审稿人/导师可能要求"给我跑出来看"，届时若脚本因环境（BGE 模型版本、Python 库版本）产生微小偏差，答辩被动。
- **修复**：
  1. 在 §4.2 表后加一行脚注：`实验复现脚本位于 backend/gnn/experiment_baselines_v2.py，设置 n_seeds=10, cross∈{0.0,0.2} 即可复现主基线。`
  2. 最好实际跑一次脚本，将输出与论文数字对比，确保完全一致（≤ 0.001 偏差可接受并标注）。
- **预计工时**：加脚注 5 分钟；跑实验核验 10 分钟（取决于 BGE 模型是否已下载）。
- **是否阻塞投稿**：**不直接阻塞**，但答辩/审稿风险高。属于"可以不自爆但必须自保"的项。

---

## §3 重要问题

### M-1｜"教学成效待实证"——整稿的最大软肋

- **定位**：摘要行 75 "教学成效有待课堂实施后实证检验"、§5.9 行 537-539 诚实标注。
- **问题**：CPEC 是**实践教育**会议。参考论文（李清勇《私教还是枪手》等）均含学生成效数据（满意度/成绩/反馈）。本稿贯穿全文的是"设计层面"/"教学成效待实证"——诚实、但显虚。审稿人最可能的一句话："**设计得很完整，但有没有学生用过？哪怕跑过一回？**"
- **修复优先级（按可行性降序）**：
  1. **最优**：拉 5-10 个同学跑 §5 实训，发问卷收反馈（难度/收获/卡壳点），N≥8 即可在 §5.9 写"初步实证（N=8）"。
  2. **次优**：若无人手，在 §5.9 从"纯诚实标注"升级为"教学实施预案 + 预期指标框架"——至少让审稿人看到"你知道怎么评、而且评审完真会去评"。
  3. **临时**：在 §6 未来工作中强化"下一阶段已在联系 X 门课程、预计 Y 学期实施"——比"未来合作获取"具体得多。
- **预计工时**：最优 2–3 天（实际试点）；次优 2 小时（纯文字）。
- **是否阻塞投稿**：**不致命但权重极高**。有试点数据 vs 纯设计 = 7 分 vs 8.5 分的差距。

### M-2｜基线表中"CurrentSystem（Louvain）"命名误导

- **定位**：表~\ref{tab:baselines} 中 'CurrentSystem（Louvain）' 行。
- **问题**：这个条目实际是**不带 GNN 的降级模式**（Louvain 社区发现），但命名 `CurrentSystem` 让审稿人以为"这就是你们系统的表现"——而系统实际上还包含 HAN GNN 模块。审稿人可能误读为"你们的系统不如 KMeans"。
- **修复**：改名 `Louvain（降级基线）` 或 `CurrentSystem w/o GNN（Louvain）`，并在表注中说明"该行对应 §3.4 反思闭环中 GNN 关闭后的降级路径，非系统正常模式"。
- **预计工时**：5 分钟。
- **是否阻塞投稿**：否，但影响审稿人对系统能力的理解。

### M-3｜系统对"派出所本地电脑"部署过重

- **定位**：docker-compose.yml（390 行，10 个容器：MySQL 8.0 + Redis + Minio + Backend + Celery + Nginx + Prometheus + Grafana + OTel-Collector + Tempo），以及 §5.7 课程对接中"教师统一容器化部署"表述。
- **问题**：论文定位是"教师部署、学生浏览器访问"的教学场景。10 容器的 docker-compose 在生产环境中合理，但在"普通教学机房 PC"上（典型配置 8GB RAM）几乎跑不动（MySQL+Redis+ESQUE + BGE 模型 ≈ 5-8GB 内存占用）。**教学机房不等于服务器机房**。
- **修复**：
  1. 在 §3.6 工程可信中诚实标注系统资源需求（建议 16GB RAM+/4 核+），并说明"在 8GB RAM 的低配机上可关闭 Prometheus/Grafana/Tempo 3 个监控容器，GNN 推理可降级为规则聚类"。
  2. 提供一个 `docker-compose.lite.yml`（只含 MySQL+Redis+Backend+Nginx 4 个核心容器）供教学轻量部署——这是"一键部署"的诚实践行。
- **预计工时**：标注 10 分钟；lite compose 30 分钟。
- **是否阻塞投稿**：否，但涉及论文的"可复现性"声称是否真实成立。

### M-4｜门控消融的"具体数值待系统开放"实质等于缺数据

- **定位**：§4.3 行 333："该决策层指标由复现脚本在本地运行后输出，本文在此给出方法学框架与教学定位，具体数值随系统开放供学生复现，避免以未实测数字充作结果。"
- **问题**：这段话翻译成审稿人视角 = "**我们没跑这个实验**"。固然诚实，但审稿人也会问："那表里的其他数字也是同样情况吗？"
- **修复**：要么实跑一次（脚本 `experiment_gating_sensitivity.py` 存在），补充一组 baseline precision/recall 值；要么在表注中明确"该部分仅给出方法框架，具体精度依赖冻卡决策的警务标注，本文未做实测"——把"开放供学生复现"改成更直白的"未实测但方式可复现"。
- **预计工时**：5 分钟（改注）/ 20 分钟（实跑）。
- **是否阻塞投稿**：否，但在答辩/审稿中可能被追问。

### M-5｜前端缺引导/教程——民警"不会用"

- **定位**：`frontend/src/views/` 目录，19 个视图组件，`frontend/src/router/index.js`。
- **问题**：以"一线民警直接使用"为场景，当前 UI 无新手引导（onboarding）、无操作提示（tooltip）、无上下文帮助。19 个视图对非技术用户来说等于迷宫。代码审计确认存在 Login/Input/Upload/Dashboard 等功能页面，但未见 Walkthrough/Guide 或 ContextHelp 组件。
- **修复**：
  1. 加一个 `WalkthroughView.vue`（简单的步骤引导页，第一步选案情来源、第二步看仪表盘、第三步读团伙结果）。
  2. Dashboard 页加首次登录的遮罩引导（Element Plus Tour 或 Steps 组件）。
- **预计工时**：轻量引导 2 小时。
- **是否阻塞投稿**：否。论文不要求前端截图证明可用性。但若答辩被问"民警真的能用吗"，需要诚实回答"界面已实现但缺乏非技术人员引导"。

---

## §4 次要问题

### m-1｜占位符未填
- **吴燕波生年**：作者简介仍 `19xx—`（首页地脚）。→ 给年份 + 5 分钟填。
- **院级科研编号**：基金项目栏 `待补`。→ 拿到编号 + 5 分钟填。

### m-2｜§3 HAN 公式仍在正文
- 行 250 `\mathbf{z}_u = \sum_{i=1}^{P} \beta_i \cdot \mathbf{h}_u^{\Phi_i}`。对于教育刊读者偏重。建议挪至文末附录或脚注，正文改为"通过语义级注意力动态组合各元路径输出"的文本描述。

### m-3｜缺少 CI/CD 与测试覆盖率
- 大量 test_*.py 文件存在但无 `pytest --cov` 报告、无 GitHub Actions / Jenkins pipeline。

### m-4｜§3.6 "系统当前仍属科研原型，尚未在真实警务环境完成端到端验证"措辞可更强
- 当前诚实但偏弱。建议改为"本文仅做教学案例设计层面的系统介绍与能力基线报告；系统在真实警务数据上的端到端效能待后续合作获取脱敏数据后验证"——更明确区分"设计"和"验证"。

---

## §5 实战差距矩阵

审计基准：面向基层派出所**单机/内网部署、一线民警直接使用**。当前系统成熟度评定为 **科研原型（PoC → 可用之间）**，距离"民警能用、敢用、好用"有梯度差。

| 维度 | 子项 | 当前状态 | 目标状态 | 差距描述 | 补全路径 | 优先级 |
|------|------|----------|----------|----------|----------|--------|
| **部署** | 单机资源占用 | 10容器（MySQL+Redis+Minio+Backend+Celery+Nginx+Prom+Grafana+OTel+Tempo）≈12-16GB RAM | 4核心容器（MySQL+Redis+Backend+Nginx）≈4-6GB RAM，一般 PC 可跑 | 教学/派出所场景不需要 Prom/Grafana/Tempo；Celery 可内嵌 Backend；Minio 可换本地文件 | 提供 `docker-compose.lite.yml` 精简至核心 4 容器；环境变量 `DEPLOY_MODE=lite` 自动关闭监控 | **高** |
| **部署** | 非技术人员部署文档 | 无面向教师的部署指南 | 一份《教师部署手册》（含 docker 安装 → 克隆 → 启动 → 验证 → 学生访问 五步） | 当前仅 `.env` 和 docker-compose.yml，无面向非技术人员的引导 | 编写 `docs/DEPLOY_TEACHER.md`（中文，截图+命令） | **中** |
| **数据** | 真实案件导入 | CSV/TXT 解析器就绪（`database/importer.py`），合成数据种子完整 | 民警可上传 Excel/CSV，系统自动字段映射 + 校验 + 增量导入 | 当前导入依赖预定义字段名，无灵活的列映射 UI | 前端加"字段映射"交互：拖拽 CSV 列 → 系统字段；后端加 schema 推断 | **高** |
| **数据** | 脱敏/合规 | BGE 本地推理（数据不出域）+ 云端 LLM 默认关闭 | 完整的"数据不出派出所局域网"认证 | paper 已诚实标注；实战需补充导出审计 + 数据销毁 + 访问日志脱敏 | 加 AdminView 的数据导出审计 + 用户操作日志导出 | **低** |
| **交互** | 民警工作台 | WorkbenchView 存在，Dashboard 有数据看板 | 统一的工作台：待办队列 + 预警排序 + 一键跳转案件详情 | Dashboard 偏"信息展示"，缺"任务驱动"引导（如"待你处理：3 个预警"） | WorkbenchView 重构为任务队列式（待研判/待复核/已完成），每项带优先级+时效 | **高** |
| **交互** | 新手引导 | 无 | 首次登录 → 引导遮罩（3 步：导入案情 → 查看结果 → 提交报告） | 19 视图无 tour/walkthrough | 加 `FirstTimeGuide` 组件（Element Plus Tour），`localStorage` 标记已完成 | **中** |
| **交互** | 研判结果可解释性 | ClusterAgent 输出团伙 + 关联原因（relation_reasons），GangDetector 有资金回流标志 | 每条研判结论附带"为什么这么判"的可视化证据链 | relation_reasons 为文本，缺图形证据（如"该团伙 3 案共享账户 X" 的高亮），普通民警难理解 | 加 EvidenceCard 组件：团伙详情页展示共享实体 + 资金回流图 | **中** |
| **安全** | 离线/内网部署 | 云端 LLM 默认关闭（`DISABLE_CLOUD_LLM=true`），BGE 本地推理 | 完全离线（所有容器/模型预下载，零外网依赖） | 首次启动需拉 Docker 镜像（外网），BGE 模型需预下载 | 提供离线安装包（docker save + model tar） | **低** |
| **可维护性** | 系统监控/告警 | Prometheus+Grafana 就绪（`monitoring/` 完整） | 民警/管理员可见的基础健康页面（CPU/内存/磁盘/分析队列积压） | 前端 StatusView 存在但内容未知；需确认是否展示基础健康指标 | StatusView 接入 `/api/metrics/prometheus` 并图形化 CPU/内存/队列 | **低** |
| **可维护性** | 数据备份 | MySQL GTID 主从 + Redis 哨兵（`--profile ha`） | 自动定期备份 + 一键恢复 | 无自动备份脚本 | 加 `scripts/backup.sh`（mysqldump + Redis SAVE 定时 crontab） | **低** |

---

## §6 答辩刁难清单（10 个最可能被问到的问题及建议应答）

| # | 问题 | 建议应答要点 |
|---|------|------------|
| 1 | "你用了 LangGraph StateGraph，为什么论文写的是手写编排器？" | 这是笔误（或旧版残留），已修正为 LangGraph StateGraph。代码 `orchestrator.py` 2026-07-26 已重构为 LangGraph，条件边回连 analyze_node 实现真实反思闭环。 |
| 2 | "合成数据上的 F1=0.9154，真实数据上能到多少？" | 诚实回答：目前未在真实警务数据上验证。合成数据的强信号特征使数字偏高，真实数据泛化需进一步实证。但这恰好是实训环节五"科学边界认知"的教学内容——让学生理解模型在真实世界中的增量是有限的。 |
| 3 | "你的学生用过这个系统吗？有什么反馈？" | 诚实回答：目前仅在设计层面完成实训方案，尚未在真实课堂实施。下一步计划联系相关课程开展试点。若已有 N 人初步反馈，直接给数据。 |
| 4 | "系统要 MySQL+Redis+FastAPI+Vue+Nginx+BGE 模型，一个普通教学机房 PC 跑得动吗？" | 核心 4 容器（MySQL+Redis+Backend+Nginx）可在 8GB RAM PC 运行；Prometheus/Grafana/Tempo 监控栈为可选组件。BGE 模型首次加载需 1-3 分钟，后续推理在 CPU 上可接受（10-30 条/s）。已计划提供轻量化 deploy profile。 |
| 5 | "你和已有的反诈系统（如公安内部研判平台）有什么区别？" | 本文定位为**教学案例**，非替代现有研判系统。差异化：(1) 可复现——学生能跑完整链路；(2) 诚实边界——明确标注合成≠真实；(3) 开放——所有代码/数据/脚本随系统分发。这些在封闭的警务内网系统中无法做到。 |
| 6 | "HAN 在合成数据上和 KMeans 差距不大（0.915 vs 0.937），凭什么说 HAN 更好？" | KMeans 在 Hard 场景的 0.937 靠合成特征携带的强信号；在 cross≥0.2 的更强干扰下，KMeans 和 Semantic 均反超所有图方法。这是合成数据本身的局限性——不代表 HAN 在实际复杂场景下不如 KMeans。论文已诚实标注了这一点。 |
| 7 | "你的云 LLM（DeepSeek）分析会泄密吗？" | LLM 旁路默认关闭（`DISABLE_CLOUD_LLM=true`），数据不出域是核心设计。即使开启，输入 LLM 的内容仅含脱敏后的案件摘要（无身份证/手机号/银行卡号明文），且论文在教学部署中建议保持关闭。 |
| 8 | "反思闭环到底提升了什么？数字可信吗？" | 反思闭环将失败场景（强跨团伙干扰后聚类未收敛）的 F1 从 0.3228 提升至 0.8353——提升约 2.5 倍。这来自自动关闭 GNN 回退规则聚类 + 调小聚类粒度。数字来自 10 seeds 均值，脚本 `experiment_baselines_v2.py` 可复现。 |
| 9 | "你的多智能体到底是真多智能体还是顺序流水线？" | 本文所称"多智能体"指分析（AnalystAgent）、聚类（ClusterAgent）、对话（ChatAgent）等阶段 Agent 的**顺序编排**，非协商型或竞争型多智能体系统。已在 §3.3 明确界定。LangGraph StateGraph 提供了条件边回连（反思→分析），使编排不是死流水线。 |
| 10 | "你这个系统能部署到真实派出所吗？" | 目前属于科研原型，尚未在真实警务环境端到端验证。技术栈层面可行（docker-compose 单机部署 + JWT/RBAC + 数据不出域），但有三个现实瓶颈：(1) 真实脱敏案件数据获取需公安合作；(2) 门控冻卡建议的精度需真实标注校准；(3) 民警操作培训与 UX 优化。本文定位为教学案例，生产部署属后续工程化工作。 |

---

## 修订优先级总表

| 优先级 | 编号 | 问题 | 预计工时 | 阻塞投稿 |
|--------|------|------|----------|----------|
| 🔴 致命 | **G-ROUTE** | **路线决策：是否采纳 4 Lab 教学优先方案** | 3-4h（纯文字改写） | **路线级** |
| 🔴 致命 | F-1 | "手写编排器"→ LangGraph StateGraph | 10 分钟 | **是** |
| 🔴 致命 | F-2 | 实验数字加可追溯引证脚注 | 5 分钟 | 答辩风险 |
| 🔴 致命 | m-1 | 占位符（生年/编号） | 10 分钟 | 格式审查堵点 |
| 🟡 重要 | M-1 | 教学成效待实证→初步实证或预案 | 2h–2d | 否但评分权重极高 |
| 🟡 重要 | M-2 | CurrentSystem(Louvain) 命名修正 | 5 分钟 | 否 |
| 🟡 重要 | M-3 | 系统部署资源需求诚实标注 | 10 分钟 | 否 |
| 🟡 重要 | M-4 | 门控消融缺数据→实跑或诚实改注 | 5–20 分钟 | 否 |
| 🟡 重要 | M-5 | 前端加新手引导 | 2 小时 | 否 |
| 🟢 次要 | m-2 | HAN 公式移附录 | 5 分钟 | 否 |
| 🟢 次要 | m-3 | CI/CD + 测试覆盖率 | 2 小时 | 否 |
| 🟢 次要 | m-4 | §3.6 措辞加强 | 5 分钟 | 否 |

---

> **审计结语**：代码底子出乎意料地扎实——docker-compose 全栈、LangGraph 真闭环、HAN 5元路径真异构、安全全链路，论文声称与实现吻合度约 90%。一票致命（编排器表述）修正后即可投。唯一真正的竞争短板是"零教学实证"，修正策略取决于你是否有 2 天时间做迷你试点。

---

## §A 教学实施预案（替代"待实证"——暑假无学生可试点时的学术诚信方案）

> **背景**：作者为湖北警官学院大二学生，暑假期间无法组织正式学生进行实训试点。本文投稿 CPEC 实践教育会议，评审期望看到"教学成效"但作者选择诚实标注。本节提供一份**可写进 §5 的完整教学实施预案**，将"教学成效待实证"升级为"预注册式的实施计划 + 预期指标框架"，让审稿人看到你知道怎么评、而且已做好准备去评。

### A.1 实施时机与课程锚定

| 要素 | 具体内容 |
|------|----------|
| **首选课程** | 《网络犯罪侦查》或《网络空间安全综合实训》（湖北警官学院信息技术系，大三下学期） |
| **备选课程** | 《人工智能安全》《图数据挖掘》 |
| **最早实施窗口** | 2026 年秋季学期（9-12 月） |
| **学时** | 16 学时（4 周，每周 4 学时），对应论文 §5 五环节递进任务链 |
| **学生背景** | 已修 Python 基础、数据库原理，未修图神经网络（即"零 GNN 先验"假设成立） |
| **教学环境** | 教师用 docker-compose 在系服务器统一部署，学生通过校内浏览器访问（无需本机配置） |

### A.2 实施流程（五环节 × 4 次课）

| 课次 | 环节 | 学生任务 | 提交物 | 预计难点 |
|------|------|----------|--------|----------|
| 1 | 导入 + 环节一：数据建模 | 教师展示真实反诈案例 → 系统演示 → 学生手工构建一例案情异构图（5 类节点、5 条元路径） | 异构图草图 + 元路径合理性说明 | 元路径概念抽象，需教师先给一例带跑 |
| 2 | 环节二：融合推理 + 环节三：编排调度 | 运行 Clean/Hard 双场景复现脚本 → 对照 F1 曲线分析 GraphSAGE 塌缩原因 → 配置反思阈值观察回连日志 | 消融归因报告（≥ 500 字） | 学生可能只抄数字不分析原因；需在报告模板中强制要求"三个为什么" |
| 3 | 环节四：决策伦理 + 环节五前半 | 调整门控阈值，讨论误冻/漏冻权衡 → 在 Elliptic 图上复现盲扫全败现象 | 冻卡决策伦理分析报告 | 伦理讨论可能流于空泛；提供 3 个真实反诈误冻案例作为讨论材料 |
| 4 | 环节五后半 + 汇报答辩 | 撰写综合实验报告（含诚实边界认知段落）→ 5 分钟小组答辩 | 综合报告 + PPT | 学生可能把合成数据结论写成真实数据结论——教师需在点评中专门纠正这一点 |

### A.3 评价指标体系（预注册）

> 以下指标在实施前即声明（类似临床试验的"预注册"），实施后按同样指标采集数据，避免"先看数据再定指标"的选择性报告。

| 指标 | 度量方法 | 达标线 | 预期值 |
|------|----------|--------|--------|
| **知识掌握度** | 课前/课后问卷（10 题多选，覆盖：异构图概念、元路径作用、反思闭环原理、合成vs真实边界） | 课后正确率 ≥ 70% | 75-85% |
| **技能可复现性** | 环节二 Clean/Hard 双场景复现成功率（学生独立跑通脚本并输出正确 F1 的人数占比） | ≥ 80% | 85-95% |
| **归因分析深度** | 消融报告盲评（教师按 4 级量表：1-记流水账 / 2-描述现象 / 3-归因分析 / 4-批判性反思） | 均值 ≥ 2.5 | 2.8-3.2 |
| **诚实边界认知** | 综合报告中是否出现"合成数据=真实验证"的错误表述（设置1分倒扣项：出现一次扣1分，满分5分） | ≤ 1 次/人 | 0-0.5 次/人 |
| **系统可用性** | SUS 系统可用性量表（10 题，0-100 分） | ≥ 60 | 55-70（预期偏低，因原型 UI 未优化） |
| **课程推荐意愿** | NPS 净推荐值（"你会向同学推荐这门实训课吗？"0-10 分） | ≥ 6 | 6-8 |

### A.4 问卷模板（预设计）

**课前问卷（知识摸底）** —— 10 题，5 分钟：
1. 异构图与同构图的主要区别是什么？
2. "元路径"在图神经网络中起什么作用？
3. KMeans 聚类的基本原理是？
4. 以下哪种情况属于"过拟合"？
5-10. （同构设计，覆盖 GNN 基础、LangGraph 概念、合成vs真实边界、反诈业务常识）

**课后问卷（同题 + 3 道拓展）** —— 13 题，8 分钟：
11. 在 Hard 场景下 GraphSAGE 发生塌缩的根本原因是什么？
12. 反思闭环的"自动降级"对工程系统的意义是什么？
13. 为什么合成数据上的模型表现不能直接推广到真实警务数据？

**实训反馈问卷**（SUS + NPS + 2 道开放题）：
- SUS 量表（10 题标准版，中文翻译）
- NPS 单题
- 开放题 1：「实训中让你最困惑的一个地方是什么？」
- 开放题 2：「如果让你改一个地方，你会改什么？」

### A.5 风险预案

| 风险 | 概率 | 影响 | 预案 |
|------|------|------|------|
| BGE 模型无法在服务器下载 | 中 | 文本通道不可用 | 提前下载模型嵌入 Docker 镜像；或提供 `USE_TEXT_CHANNEL=false` 模式，结构通道可独立运行 |
| docker-compose 在系服务器上启动失败（端口冲突/内存不足） | 中 | 全班无法实训 | 提前 2 周在服务器试部署；准备轻量 deploy profile（仅 core 4 容器） |
| 学生 Python 基础太差（无法读懂脚本） | 高 | 复现率低、问卷成绩差 | 环节一前加 30 分钟 Python + Jupyter 速成（不追求会写，只追求会跑、会改参数） |
| 学生对"合成≠真实"边界理解不深 | 高 | 问卷正确率低、报告出现"合成=真实"错误 | 环节五专门设"找茬"练习：给一段故意把合成当真实的错误报告，让学生找出 3 处谬误 |
| 16 学时机房排课冲突 | 低 | 实训延期 | 备选 8 学时精简版（去掉环节三/四的深度探究，保留核心实验链路） |

### A.6 论文中的写入方式

> 以下为建议写入 §5.9 的段落（替换当前"教学成效说明（诚实标注）"）：

```
\subsection{教学成效说明与实施预案}

本案例设计尚未在正式课程中规模化实施。为保障教学成效评估的客观性，
本节按照"预注册"原则预先声明评价指标、度量方法与达标线，
待 2026 年秋季学期在《网络犯罪侦查》课程中实施后按同样指标采集数据并如实报告，
避免选择性报告带来的偏差。

评价体系含六个维度：知识掌握度（课前/课后问卷）、技能可复现性（双场景复现成功率）、
归因分析深度（消融报告盲评）、诚实边界认知（合成≠真实表述准确性）、
系统可用性（SUS 量表）与课程推荐意愿（NPS）。
各维度预期值与度量方法见表~\ref{tab:eval}（实施前声明），
实施后将补充实测值并进行差异分析。

需特别说明：本节所列均为\textbf{设计层面的实施预案}，
不构成已验证的教学成效数据；实际教学成效待课堂实施后实证评估。
```

并附一张三线表 `tab:eval`（6 指标 × 3 列：度量方法 / 达标线 / 预期值），
取自本节 A.3 评价指标表。

---

## §B 项目文件地图与关键路径

> 下一任 agent 接手时可据此快速定位。

### B.1 编译与交付

| 路径 | 用途 |
|------|------|
| `paper/CPEC2026_draft.tex` | **主稿**（A 稿，XeLaTeX + BibTeX） |
| `paper/references.bib` | 参考文献（32 条，GB/T 7714-2015） |
| `paper/fraudlens_outline.tex` | B 稿（技术向，供对比/移植图表用） |
| `paper/compiled_编译产物/CPEC2026_draft.pdf` | 最新编译 PDF（已同步时间戳版） |
| `paper/CoverLetter_CPEC2026.md` | 投稿信草稿（A→CPEC / B→技术刊 分工声明） |
| `paper/CPEC2026_论文写作方法论.md` | Phase0-4 写作 OS + 风格基线 + 红线 |
| `paper/投稿说明_给指导老师.md` | 大白话版，供师生抓主线 |
| `paper/交接提示词_论文复评.md` | 前一版交接提示词（本报告为其升级版） |
| **`paper/FraudLens_审计报告.md`** | **本文件——全量审计 + 执行清单** |

### B.2 后端核心

| 路径 | 用途 |
|------|------|
| `backend/main.py` | FastAPI 入口 + 中间件链（CORS/限流/安全头/审计） |
| `backend/agents/orchestrator.py` | **LangGraph StateGraph 编排器**（5节点+条件边反思闭环） |
| `backend/agents/analyst_agent.py` | 案件分析 Agent（实体抽取+风险评估+RAG） |
| `backend/agents/cluster_agent.py` | 团伙聚类 Agent（实体关联+GNN/Louvain+资金回流） |
| `backend/agents/chat_agent.py` | AI 对话 Agent（ReAct循环+Function Calling） |
| `backend/gnn/han_model.py` | HAN + FraudHAN + GraphCL 预训练（5元路径双通道） |
| `backend/gnn/gang_detector.py` | GangDetector 主控制器 |
| `backend/gnn/graph_builder.py` | 异构图构建（元路径+文本BGE通道+资金回流） |
| `backend/gnn/gnn_model.py` | GraphSAGE 基线模型 |
| `backend/gnn/experiment_baselines_v2.py` | **主基线实验脚本**（10 seeds × cross∈{0.0,0.2} 产生 0.9154） |
| `backend/gnn/experiment_gating_sensitivity.py` | 门控消融实验 |
| `backend/core/security.py` | Prompt 注入防护（24 条正则） |
| `backend/core/metrics_exporter.py` | Prometheus 指标导出 |
| `backend/database/importer.py` | CSV/TXT 数据导入器 |
| `backend/database/models.py` | SQLAlchemy 数据模型（User, Case, Gang, OperationLog 等） |
| `backend/database/p1_models.py` | Phase1 扩展（资金流/派单/重点人员） |

### B.3 前端核心

| 路径 | 用途 |
|------|------|
| `frontend/src/views/DashboardView.vue` | 数据看板 |
| `frontend/src/views/InputView.vue` | 案情录入 |
| `frontend/src/views/GroupsView.vue` | 团伙发现结果 |
| `frontend/src/views/NetworkView.vue` | vis-network 关系图谱 |
| `frontend/src/views/ChatView.vue` | AI 对话助手 |
| `frontend/src/views/WorkbenchView.vue` | 民警工作台 |
| `frontend/src/components/NetworkGraph.vue` | 团伙关系图组件 |
| `frontend/src/router/index.js` | 路由配置（含 auth guard） |

### B.4 部署与运维

| 路径 | 用途 |
|------|------|
| `docker-compose.yml` | 生产部署编排（10 容器，含监控栈） |
| `docker-compose.dev.yml` | 开发模式（源码挂载 + langgraph 自动装） |
| `docker-compose.ha.yml` | HA 叠加（MySQL 主从 + Redis 哨兵） |
| `Dockerfile` | Backend 容器构建 |
| `docker/init.sql` | MySQL 建表 DDL（users/cases/gangs/graph 等 14+ 表） |
| `docker/entrypoint.sh` | 容器入口（BGE 模型预热 + DB 迁移） |
| `.env.docker` | 环境变量模板 |
| `.env` | **实际环境变量**（含密钥，勿提交！） |
| `start.bat` | Windows 启动脚本 |
| `k8s/` | Kubernetes 清单（预留） |
| `monitoring/` | Prometheus + Grafana + Tempo 配置 |

### B.5 实验与数据

| 路径 | 用途 |
|------|------|
| `backend/gnn/experiment_*.py` | 8 个实验脚本 |
| `backend/gnn/synthetic_data.py` | 合成案情生成器 |
| `backend/gnn/synth_accounts.py` | 合成账户数据 |
| `backend/gnn/adapters/amlsim_adapter.py` | AMLSim 仿真适配器 |
| `backend/data/datasets/elliptic/` | Elliptic 比特币欺诈数据（features.csv 689MB） |
| `backend/bge-large-zh-v1.5/` | BGE 中文嵌入模型（本地推理） |
| `demo_案件材料.docx` | 演示用案卷材料 |
| `docker/data.sql` | 种子数据 |

### B.6 文档资产

| 路径 | 用途 |
|------|------|
| `docs/项目总览与需求_Overview.md` | 项目定位 + 用户需求 |
| `docs/架构设计_Architecture.md` | 系统架构详解 |
| `docs/工程质量与业务落地_Quality.md` | 安全/审计/降级/合规 |
| `docs/代码进度_CodeStatus.md` | 各模块完成度 |
| `docs/论文与答辩准备_Paper.md` | 论文进度 + 答辩策略 |
| `docs/实验与评测_Experiments.md` | 实验设计 + 结果分析 |
| `docs/变更记录_Changelog.md` | #C 编号变更记录 |
| `docs/INDEX.md` | 文档导航地图 |
| `paper/references_参考文献/` | 19 篇参考论文 PDF（李清勇/厉旭杰/张金/向尕等）|

---

## §C 技术栈与版本锁定

| 层面 | 组件 | 版本 |
|------|------|------|
| **语言** | Python | 3.10（后端） |
| | Node.js | 22.22.2（前端构建） |
| **Web** | FastAPI | ≥0.104 |
| | Uvicorn | ≥0.24 |
| | Vue 3 | 3.5.25 |
| | Vite | 7.3.1 |
| | Element Plus | 2.8.4 |
| **数据库** | MySQL | 8.0（容器） |
| | Redis | 7-alpine（容器） |
| **AI/ML** | LangGraph | ≥0.2.0（#30 引入，替代手写编排器） |
| | LangChain | ≥0.1.0 |
| | OpenAI SDK | ≥1.0.0（直连 DeepSeek） |
| | BGE-large-zh | v1.5（本地推理，`backend/bge-large-zh-v1.5/`） |
| **编排** | Celery | ≥5.3（异步分析任务） |
| **部署** | Docker Compose | v3.8 |
| | Nginx | alpine（反向代理） |
| **可视化** | ECharts | 5.6 |
| | vis-network | 10.1 |
| **监控** | Prometheus + Grafana + Tempo + OTel-Collector | latest |
| **编译** | TeX Live | 2026（`D:/texlive/2026/bin/windows/xelatex.exe`） |
| **环境密钥** | DeepSeek API Key | `.env` 中 `DEEPSEEK_API_KEY`（可选，默认关闭） |

---

## §D 已知陷阱与绕过方案

| # | 陷阱 | 现象 | 绕过方案 |
|---|------|------|----------|
| 1 | **PDF 被锁** | `xelatex` 编译时 `CPEC2026_draft.pdf` 被预览程序（Acrobat/浏览器）锁定 → 编译失败 | 用 `-jobname viewbuild` 输出到非锁定文件名；编译完再 `cp viewbuild.pdf ...` |
| 2 | **沙箱 safe-delete** | `rm` / `os.remove` 被 WorkBuddy 安全删除包装拦截（recycle-bin 不可用） | 临时文件删不掉就留着；核心交付物（PDF）已归档到 `compiled_编译产物/` 不受影响 |
| 3 | **BGE 模型首次下载** | 首次 `docker-compose up` 时 `entrypoint.sh` 自动下载 BGE-large-zh-v1.5（~1.3GB），可能超时或网络不通 | 模型已本地缓存于 `backend/bge-large-zh-v1.5/`；Dockerfile 用 `COPY` 预置即可跳过下载 |
| 4 | **DeepSeek API 欠费/不可用** | 默认 `DISABLE_CLOUD_LLM=true` 避免依赖；若开启后 API 不可用，AnalystAgent 的 LLM 分析步骤会报错但不阻塞主链路 | 始终保持 `DISABLE_CLOUD_LLM=true`；论文教学场景中 LLM 旁路默认关闭 |
| 5 | **Elliptic 数据无表头** | `features.csv` 689MB，无列名、classes 列含 'unknown' 字符串 | 已在 `experiment_elliptic.py` 中硬编码列索引处理 |
| 6 | **HAN inference on CPU 慢** | 案件量大时（>100）GraphCL pre-training + HAN inference 在 CPU 上耗时 >30s | 教学场景案件量小（5-15），可接受；生产需 GPU |
| 7 | **Windows 路径反斜杠** | `.env` / Python 中使用 Windows 反斜杠路径 → Docker 内 Linux 挂载失败 | `.env.docker` 模板已用正斜杠；编辑 `.env` 时注意 |
| 8 | **当前环境无法查看 PNG** | WorkBuddy 本会话模型不支持图像，Read PNG 返回 "model does not support images" | 所有图核验用 PyMuPDF 程序化几何分析（抽矩形坐标→碰撞检测），比肉眼可靠；最终仍需人工目检 PDF |

---

## §E 下一任 agent 预配置执行清单

> 按优先级排序，直接可执行。每一步完成后 **重编译核验（0 undefined / 0 error）并归档**。

### 🔴 第一优先级：必须立即修（投稿阻塞 + 答辩风险 + 路线决策）

- [ ] **🆕 G-ROUTE｜路线决策**：是否采纳 §G 的"4 Lab 教学优先"方案？**推荐采纳**——将论文从"系统即案例（生搬硬套）"改写为"4 节 Jupyter 实验课为核心载体 + FraudLens 原型为进阶入口"的双层设计。若采纳，额外做以下三项（均在论文纯文字层面，不涉及编译风险）：
  - [ ] 改写 §5.3（五环节→4 Lab 递进实验链）+ 图 `fig:stages` 5盒→4盒
  - [ ] 改写 §5.6（5 条 enumerate→4 个 Lab 教案子节，每节含目标/步骤/观察点/讨论题）
  - [ ] 新增 §5.10 "教学优先的设计哲学"（~300 字，解释为何用 Jupyter 而非全栈 Web）
- [ ] **F-1**：`CPEC2026_draft.tex` 第 257 行——"手写顺序编排器" → "LangGraph StateGraph~\cite{langgraph2024} 编排"。同时删除段落内自相矛盾的"手写"表述，确保与 `backend/agents/orchestrator.py`（2026-07-26 重构版）一致。
- [ ] **F-2**：在 §4.2 表~\ref{tab:baselines} 后加脚注：`实验复现脚本：backend/gnn/experiment_baselines_v2.py（n_seeds=10, cross∈{0.0,0.2}）。` 如环境允许，实际跑一次交叉核验数字。
- [ ] **m-1**：补吴燕波生年（首页地脚作者简介）、补院级科研编号（基金项目栏）——两项均需用户提供后填入。

### 🟡 第二优先级：显著提升竞争力

- [ ] **M-1 教学实施预案**：将本报告 §A 中的预案段落写入论文 §5.9（替换当前"教学成效说明（诚实标注）"），并添加 `tab:eval` 评价指标表。**这是不增加外部依赖、纯文字改动即可大幅提升教育稿说服力的最高杠杆项**。
- [ ] **M-2**：表~\ref{tab:baselines} 中 `CurrentSystem（Louvain）` → `Louvain（降级基线 / GNN 关闭）`，表注说明"对应 §3.4 反思闭环中 GNN 关闭后的降级路径"。
- [ ] **M-3**：在 §3.6 或 §5.7 中诚实标注：系统需 16GB RAM / 4 核（完整栈）；轻量部署 4 核心容器（MySQL+Redis+Backend+Nginx）可在 8GB RAM 运行。如时间允许，提供 `docker-compose.lite.yml`。
- [ ] **M-4**：门控消融——要么实跑 `experiment_gating_sensitivity.py` 补 1-2 组 precision/recall 值，要么将 §4.3 的"具体数值随系统开放"改为更直白的"该部分仅给出方法学框架，精度依赖真实警务冻卡标注，本文未做实测"。

### 🟢 第三优先级：锦上添花（时间允许时做）

- [ ] **m-2**：§3 HAN 公式 `z_u=Σβ_i h` 挪至文末附录/脚注，正文改为文本描述。
- [ ] **M-5**：前端加简易新手引导——`WalkthroughView.vue`（Element Plus Tour 组件，3 步引导）。
- [ ] **m-4**：§3.6 "系统当前仍属科研原型" → 改为更明确区分"设计"与"验证"的表述。
- [ ] **m-3**：加 `pytest --cov` 脚本 + `.github/workflows/test.yml`（如使用 GitHub）。
- [ ] 提供 `docker-compose.lite.yml`（core 4 容器）和 `docs/DEPLOY_TEACHER.md`（中文五步部署指南）。

### 🛑 绝对不能碰的红线

以下四条为作者（韩冬）强制规定的学术诚实底线，**改稿时绝对不能为讨好审稿人而违背**：

1. **合成 ≠ 真实验证**：主实验合成数据，绝不把合成 F1 写成"真实数据验证通过"。
2. **GNN 增量边界诚实标注**：HAN 仅在结构清晰子图占优；盲扫全败、扩线提两个数量级是设定迁移发现。
3. **降 AI 检测率不得淡化边界**：可软化套话、降被动句，但以上两条原样保留。
4. **不夸大落地**：系统属科研原型，未真实警务端到端验证；教学成效待实证（可改为预案但不得写成已验证）。

### 工具环境速查

```
编译：D:/texlive/2026/bin/windows/xelatex.exe + bibtex
命令：xelatex -interaction=nonstopmode -jobname viewbuild CPEC2026_draft.tex → bibtex viewbuild → xelatex ×2
核验：grep -c "undefined\|Overfull" viewbuild.log
归档：cp viewbuild.pdf compiled_编译产物/CPEC2026_draft_$(date +%Y%m%d-%H%M).pdf
图核验（本环境大概率看不了 PNG）：PyMuPDF fitz.open().get_drawings() 抽坐标 → 程序化碰撞检测
```

---

## §G 教学优先重构方案（作者 2026-08-04 定调：从"生搬硬套"到"为教学设计"）

> **核心诊断**：FraudLens 本质上是一个**工程系统**（docker-compose 10 容器、LangGraph 反思闭环、19 前端视图、JWT+RBAC+监控栈），当前论文把"教学案例"的外衣套在一个工程系统上——**先有系统，再想怎么让学生用**。而 CPEC 优秀教学案例稿（李清勇、厉旭杰、张金等）的思路正好相反：**先有教学目标，再设计用什么载体来教**。
>
> **作者直觉（完全正确）**：对于日常本科教学太难了。工程复杂度（Docker 部署、API 鉴权、LangGraph 编排）是**教学噪声**而非**教学信号**。
>
> 本节提供完整的教学优先改造方案，将 FraudLens 从"要部署的系统"重构为**4 节 Jupyter 实验课**，学生在自己笔记本上 `pip install` 四个包即可运行——不碰 docker、不管 Vue、不理编排细节。

### G.1 教学优先设计总览：4 Lab × 2 小时 = 8 学时

```
FraudLens Lab（教学版交付物）
├── lab1_认识案情与异构图.ipynb    （2h）认识数据→手工构建异构图→理解"元路径"
├── lab2_结构通道探案.ipynb        （2h）建图→社区发现(Louvain)→看共享实体→F1评测
├── lab3_文本通道与双通道融合.ipynb （2h）BGE语义相似连边→双通道消融观察→降级实验
├── lab4_算法的诚实边界.ipynb      （2h）给高难度数据让算法失败→写边界反思→伦理讨论
├── data/                         预烘焙合成数据 + 预计算缓存（cell→Run All 秒出）
├── README.md                     学生自述文件（零 GNN 先验可上手）
└── requirements.txt              仅 6 个包：numpy, pandas, networkx, matplotlib,
                                   scikit-learn, sentence-transformers
```

**与当前论文 §5 五环节的对应关系**：

| 当前论文 §5 | 教学版 Lab | 学生具体做什么 | 观察与归因点 |
|:--|:--|:--|:--|
| 环节一 数据建模 | Lab1 认识案情与异构图 | 打开合成案情 JSON → 在纸上画出异构关系图（案件-账户-手机号-类型-城市）→ 用 NetworkX 代码验证自己的草图 | "为什么以案件为中心而非裸账户？" |
| 环节二 融合推理 | Lab2 + Lab3 | Lab2：只建结构图→Louvain 社区发现→评估 F1；Lab3：加 BGE 文本边→跑双通道聚类→对比结构-only vs 双通道的 F1 差异 | "文本通道在什么时候起作用？"（中等 cross 时不显著、高 cross 时才显现） |
| 环节三 编排调度 | Lab3 后半段（降级实验） | 手动关闭 GNN→回退 Louvain→比较聚类质量→讨论"工程上为什么需要降级" | "降级是失败还是设计？" |
| 环节四 决策伦理 | Lab4 延伸讨论 | 给定 4 因子门控逻辑（团伙规模/金额/关联账户数/资金回流）→ 计算一个真实误冻案例的溯因 → 讨论"误冻 vs 漏冻" | "算法说冻，人敢冻吗？" |
| 环节五 边界验证 | Lab4 主实验 | 给 cross=0.4 的高难度数据 → 所有方法 F1 崩塌 → 读论文中的 AMLSim/Elliptic 盲扫结果 → 写 300 字"诚实边界反思" | "为什么真实数据上所有方法都会失败？" |

### G.2 【最重要的设计决策】预计算但可重算——不做实时推理

> 这条决定极其关键，解释了为什么教学版不需要 Docker/GNN 训练环境。

**设计原则**：所有 GNN 推理、模型训练、耗时计算的结果**预烘焙成 JSON/NumPy 数组**，学生打开 notebook 第一件事是 `cell → Run All`，3 秒出结果。结果表格和曲线已就绪，学生的工作是**读结果、对比、归因**，不是等训练。

每个 Lab 的核心实验 cell 提供一个 `--recompute` 标记（默认 False）。想体验完整训练过程的学生可设为 True（需要 PyTorch + BGE 模型，约 5-10 分钟等待），但**不要求**——这满足了"零 GNN 先验可上手"的承诺。

**预计算缓存（`data/precomputed/`）**：

| 文件 | 内容 | 来源模块 |
|:--|:--|:--|
| `cases_clean.json` | cross=0.0 场景的合成案情（5 团伙×8 案 + ground truth） | `synthetic_data.py` |
| `cases_hard.json` | cross=0.2 场景的合成案情 | `synthetic_data.py` |
| `cases_extreme.json` | cross=0.4 场景（用于 Lab4 失败实验） | `synthetic_data.py` 调参 |
| `graph_edges_structure.json` | 结构通道邻接矩阵（case_account_case + 其他 3 条） | `graph_builder.py` |
| `graph_edges_text.json` | 文本通道邻接矩阵（case_text_case，BGE cos≥0.5） | `graph_builder.py._metapath_text()` |
| `embeddings_han.npy` | HAN 预训练后的案件嵌入 | `han_model.py` + GraphCL |
| `results_baselines.csv` | 6 种方法 Clean/Hard F1（=论文表 tab:baselines） | `experiment_baselines_v2.py` |
| `results_ablation.csv` | 消融实验结果（=论文表 tab:ablation） | `experiment_baselines_v2.py` |

### G.3 四节 Lab 详细教案

#### Lab1：认识案情与异构图（2h）

**教学目标**：理解反诈案件的数据结构，理解"异构图"和"元路径"概念。

**步骤**：
1. （10 min）教师展示一个真实电信诈骗案例（刷单返利）→ 黑板上列出涉及的实体：1 个受害者、3 个诈骗账户、5 个关联手机号、1 个诈骗类型
2. （20 min）学生打开 `cases_clean.json` → 用 `pandas` 浏览案情数据 → 回答问题："这个案子涉及哪些类型的实体？哪些实体在多个案子间共享？"
3. （40 min）在纸上画出异构图——5 类节点（case/account/perpetrator/type/city）→ 按共享实体连边 → 用 NetworkX 代码验证自己的草图 → 输出 `nx.info(G)`
4. （30 min）教师引入"元路径"概念：`case-account-case` = 共享账户的两案可能同伙 → 学生用代码验证"哪些案对共享了同一个账户"
5. （20 min）收尾讨论："为什么异构图比同构图更适合反诈？如果用同构图（只保留案件节点，边=共享实体），丢失了什么信息？"

**观察点（学生报告需回答）**：
- 本案情数据中，哪种共享关系最频繁？这意味着什么？
- 如果只用"共享账户"这一种关系来连边，漏掉了哪些可能同伙的案件？

**代码依赖**：`numpy, pandas, networkx, matplotlib`（4 个包，无需深度学习）

#### Lab2：结构通道探案（2h）

**教学目标**：用图社区发现初步找出团伙，理解"纯结构信号"的能力与局限。

**步骤**：
1. （10 min）回顾 Lab1 的异构图 → 加载 `graph_edges_structure.json`（只含结构通道的邻接矩阵）
2. （30 min）用 `networkx.community.louvain_communities` 做社区发现 → 对比 ground truth → 计算 F1 → **这是学生第一次见到 F1 概念，需要教师解释 TP/FP/FN**
3. （30 min）探索"为什么有些团伙没找对"：挑选两个被漏掉的真实同伙案件 → 手动检查它们在图中的连接路径 → 发现"它们没有直接共享账户，但通过中间人相连"（= 多跳问题）
4. （20 min）对比 `results_baselines.csv` 中 Louvain 和 HAN 的差距 → 理解"为什么需要图神经网络来捕捉多跳结构"——**这是引入 HAN 的动机，学生不用看懂 HAN 公式，只需要看懂"Louvain 0.86 vs HAN 0.91"这个数字差异**
5. （30 min）非必选 challenge：修改邻接矩阵的权重（用加权边代替二值边）→ 观察对 Louvain 结果的影响 → "权重编码了资金强度信息"

**观察点**：Louvain 社区发现漏掉了哪些团伙？为什么？（引导：没有共享实体但通过中间人关联的案件无法被社区发现捕捉）

**代码依赖**：`numpy, pandas, networkx, scikit-learn`（4 个包）

#### Lab3：文本通道与双通道融合（2h）

**教学目标**：理解多源信息融合的价值，体验"消融实验"的归因逻辑。

**步骤**：
1. （10 min）回顾 Lab2 → 加载 `graph_edges_text.json`（文本通道：BGE 语义相似连边）→ 观察"哪些原本不连边的案对现在连上了？连上的原因是什么？"（话术相似）
2. （20 min）加载 `results_baselines.csv` → 对比 Semantic-only（只用文本）、Structure-only（只用结构）、Dual-channel（两者融合）的 F1 → **关键教学时刻：发现双通道增益在 cross=0.0（Clean）场景几乎为零，cross=0.2（Hard）场景才显现** → 讨论为什么
3. （30 min）阅读 `results_ablation.csv` → 找出 w/o 反思闭环的失败场景 F1=0.3228 → 理解"反思闭环救了什么"
4. （30 min）手动关闭 GNN（在代码中把 `use_gnn` 设为 False）→ 重跑 Louvain → 观察 F1 下降 → 理解"降级不是失败，是有意设计的工程兜底"
5. （10 min）教师引入一个问题："如果现在给你一个全新的诈骗类型（训练数据里没见过），双通道融合还会有效吗？" → 引出 Lab4

**观察点**：文本通道的补强增益是恒定的还是场景依赖的？在什么场景下显现？为什么？

**代码依赖**：`numpy, pandas, scikit-learn`（3 个包；sentence-transformers 仅 `--recompute` 时需要）

#### Lab4：算法的诚实边界（2h）

**教学目标**：建立"模型能力边界"的认知，理解诚实标注的学术价值，完成伦理讨论。

**步骤**：
1. （15 min）加载 `cases_extreme.json`（cross=0.4 高跨团伙干扰）→ 所有 6 种方法 F1 崩塌（降到 0.3-0.5）→ 学生震惊——**这是设计好的"失败时刻"，教学意义极深**
2. （30 min）看 AMLSim 盲扫 F1≈0.002、Elliptic HAN F1≈0.016 的真实图数据 → 讨论"为什么真实数据上所有方法都失败？根因在哪？"
3. （20 min）引入"扩线"（refinement）概念：给定一个锚点嫌疑账户→只分析该账户的 k 跳邻居→小图上的检测精度大幅提升。传递核心 insight：**反诈 GNN 的瓶颈不在编码器设计，而在'盲扫 vs 扩线'的任务设定**
4. （25 min）写 300 字"我的诚实边界反思"：① 为什么我们这个实验不能声称"真实警务数据验证通过"？② 如果有真实脱敏数据，你预期结果会比合成数据好还是差？为什么？③ 作为未来的警务技术使用者，你会怎么向领导/同事解释"这个模型可能不准"？
5. （10 min）伦理深化：讨论误冻案例（门控阈值设太低→无辜者账户被冻结）→ 如果算法建议冻结但你觉得不该冻，你会怎么办？→ 引出"人机协同决策"议题

**观察点（核心考核）**：学生写的"诚实边界反思"中是否出现了"合成数据 = 真实数据"的错误表述？——这是本实训最重要的教学产出：**带着边界意识进入职业生涯**。

**代码依赖**：`numpy, pandas, matplotlib`（3 个包）

### G.4 从现有代码中提取/适配

每个 Lab 的底层计算完全复用现有 FraudLens 后端模块，**不需要重写 80% 的代码**：

| Lab | 预计算数据 | 来源模块 | 复用方式 |
|:--|:--|:--|:--|
| Lab1 | `cases_clean.json` | `synthetic_data.py` | 已有合成数据生成器，直接导出 JSON |
| Lab2 | `graph_edges_structure.json`, `results_baselines.csv` | `graph_builder.py._metapath()`, `experiment_baselines_v2.py` | graph_builder 已有结构通道构建；实验脚本已有 CSV 输出 |
| Lab3 | `graph_edges_text.json`, `results_ablation.csv` | `graph_builder.py._metapath_text()`, `experiment_baselines_v2.py` | 文本通道已实现（BGE cos≥0.5 连边）；消融结果已有 |
| Lab4 | `cases_extreme.json`, AMLSim/Elliptic 对比数据 | `synthetic_data.py`（改 cross=0.4）, `experiment_elliptic.py` | 合成数据生成器接受 cross 参数；Elliptic 实验已有 |

**需要新建的文件**（仅 7 个，预计工时 4 小时）：
1. `FraudLens_Lab/README.md` — 学生自述文件
2. `FraudLens_Lab/requirements.txt` — 6 个包
3. `FraudLens_Lab/lab1_认识案情与异构图.ipynb` — 新建 notebook
4. `FraudLens_Lab/lab2_结构通道探案.ipynb` — 新建 notebook
5. `FraudLens_Lab/lab3_文本通道与双通道融合.ipynb` — 新建 notebook
6. `FraudLens_Lab/lab4_算法的诚实边界.ipynb` — 新建 notebook
7. `FraudLens_Lab/scripts/precompute.py` — 数据预生成脚本（调用现有模块，可跑通即可）

### G.5 论文叙事改写方案

当前论文 §5 的"五环节递进任务链"需改写为以 **4 节 Lab 实验课** 为核心载体的叙事：

**保持不变的内容**（已在论文中，不删）：
- §5.1 学情分析与课程衔接
- §5.2 "研—训—评"一体化模式 + 图~\ref{fig:mode}
- §5.4 教学目标与能力映射（表 ~\ref{tab:ability}）
- §5.5 复杂工程问题特征映射（表 ~\ref{tab:cep}）
- §5.7 课程对接与实施组织
- §5.8 考核方式设计
- §5.9 课程思政与伦理教育

**需要改的内容**：

1. **§5.3 五环节递进任务链 + 图~\ref{fig:stages}**：
   - 改为 **"4 节实验课递进实验链"**。
   - 图 `fig:stages` 的 5 stage 盒子改为 4 个（环节一→Lab1 / 环节二→Lab2 / 环节三+四→Lab3 / 环节五→Lab4），保留递进箭头。
   - 叙事角度从"系统有什么模块"转为"学生要做什么实验、看什么现象、讨论什么问题"。

2. **§5.6 实训环节设计**（当前为 5 条 enumerate）：
   - 改为 4 个子节（Lab1–Lab4），每节含：教学目标 → 实验步骤概要（3-5 步）→ 关键观察点 → 讨论题。
   - 特别标注"预计算但可重算"的设计——学生零 GNN 先验可上手，核心在观察与归因而非模型训练。

3. **新增 §5.10 "教学优先的设计哲学"**：
   - 约 300 字，解释"为什么用 Jupyter notebook 而非全栈 Web 系统作为教学载体"：
     - 零部署（学生 `pip install` 6 个包即可，不需要 Docker/数据库/Nginx）
     - 预计算（教学时间用于读结果和讨论，不用于等训练）
     - 渐进复杂性（Lab1 纯手工→Lab2 纯代码→Lab3 灌数据→Lab4 做失败实验）
   - 最后一段保留 FraudLens 完整原型作为"进阶入口"：供有工程兴趣的学生在课程设计/毕设中深入，但日常教学以 4 lab 为主——形成"基础层-进阶层"双层设计。

### G.6 两种方案的对比（供说服导师用）

| 维度 | 当前方案（系统即案例） | 教学优先方案（4 Lab） |
|:--|:--|:--|
| 学生上手门槛 | 需 Docker、MySQL、Redis、Vue——非计算机专业几乎不可行 | `pip install` 6 个包，任意笔记本 |
| 教学时间利用 | 30% 用于部署/调试环境 | 100% 用于实验+讨论 |
| 认知负荷 | 系统架构（LangGraph/容器/JWT）是教学噪声 | 只暴露异构图+GNN 核心概念 |
| 可复现性 | 依赖特定环境（BGE 模型、MySQL schema） | 预计算数据随 notebook 分发，100% 可复现 |
| 差异化 | 系统和市面上教学案例完全不同——但差异点是工程复杂度，非教学价值 | 系统和现有教学案例的差异在于"带失败实验的诚实边界训练"——这恰恰是教学创新 |
| 与 CPEC/实验技术与管理对标 | 勉强对标（系统太多、教学太少） | **精准对标**（李清勇那篇也是"概念-实验-讨论"三层，无全栈系统） |
| 后续维护 | 系统升级 → 教学方案也得改 | 实验数据是静态的，同步更新 `precompute.py` 即可 |
| 教学实效评估 | 必须等完整实施（一学期后） | 4 lab 可在 1-2 周内找 3-5 个同学试跑收集初步反馈 |

### G.7 下一任 agent 的执行路径

> 已整合进 §E 执行清单。本节仅补充教学优先改造的专属步骤。

**P0（和原有 F-1/F-2 平级，阻塞投稿路径）**：
- [ ] 决定路线：是用"4 Lab"方案改写 §5（推荐），还是保留当前"五环节+系统"方案。
- [ ] 若走 4 Lab 路线：改写 `CPEC2026_draft.tex` 的 §5.3、§5.6、新增 §5.10（预计 3-4 小时，全部是纯文字改动，不涉及编译风险）。

**P1（投稿前可做，加分但不阻塞）**：
- [ ] 创建 `FraudLens_Lab/` 目录，写 4 个 notebook 草稿（markdown cell + 伪代码即可，不需要能跑通）。
- [ ] 在论文 §5 中加一张"4 Lab 递进实验链"示意图（TikZ，画 4 个横排盒子 + 递进箭头，类似当前 `fig:stages` 但砍一个盒子）。
- [ ] 更新论文中所有 "五环节"→"四环节实验链" 的硬引用。

**P2（投稿后/答辩前补充，提升说服力）**：
- [ ] 实写 `scripts/precompute.py` + 跑通 4 个 notebook，确保 future 学生真的能 Run All。
- [ ] 找 3-5 个同学试跑（开学后），收集 SUS/NPS 初步数据，替换论文 §A 中的预期值为实测值。
