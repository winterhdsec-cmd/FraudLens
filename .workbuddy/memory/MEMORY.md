# FraudLens 项目长期记忆（精简版）

## 官方定义与真实架构（代码可指认）
- 多智能体编排 + 图神经网络的反诈团伙智能研判系统；面向公安反诈中心/基层派出所，单机/内网部署，不追求云端商业化。
- 交互层 Vue3+Element Plus+ECharts+vis-network；决策协同层 FastAPI + **LangGraph StateGraph 真反思闭环**（规划→预处理→分析→聚类→反思，条件边回连）；数据层 MySQL+Redis + BGE-large 本地推理 + 云端 LLM（**当前=阿里云百炼 DashScope 千问 qwen3.8-flash（2026-08-26 新发多模态 MoE，1M上下文）**，OpenAI 兼容）+ GNN。

## 云端 LLM 配置要点（2026-08-29 切换）
- **双文件陷阱**：云端 LLM 的 key/endpoint/model 必须同时改两处才生效——根目录 `.env`（docker-compose 注入）与 `backend/key.env`（`main.py`/`tasks.py` 用 dotenv 直接加载）。只改一处会被另一处覆盖。
- 变量名仍沿用 `DEEPSEEK_API_KEY` / `DEEPSEEK_BASE_URL` / `DEEPSEEK_MODEL`（代码只认这几个名），endpoint=`https://dashscope.aliyuncs.com/compatible-mode/v1`，模型=`qwen3.8-flash`（**2026-08-26 新发多模态 MoE，1M 上下文，OpenAI 兼容，文本/图像/视频全能**；要切最强档改 `qwen3.8-max`）。
- 切换前为 DeepSeek（`deepseek-chat` + `https://api.deepseek.com/v1`），已整体迁移至阿里云。
- `DISABLE_CLOUD_LLM=0` 启用云端（默认 `1` 关闭、数据不出域）；`CLOUD_LLM_MASK=1` 出向 prompt 脱敏（身份证/银行卡/手机号/邮箱）。
- 图片识别（tools/vision.py）自动复用同一模型，qwen3.8-flash 本身多模态可看图；VISION_MODELS 列表虽不含 qwen，但 analyze() 仍会先用 self.model 发图，不受影响。

## 诚实口径金律（最高优先级，任何产出不得违反）
- 合成 ≠ 真实验证；增量边界须量化；GNN 非全设定占优。
- 合成 HAN hard F1=0.947/clean=1.0；dual-channel gain hard=+0.202；独立 Semantic 基线 clean 1.0/hard 1.0。
- 真实 AMLSim（43,614账户/1,305环）全图 F1≈0.002–0.010，所有法含 GNN 失效；Elliptic 盲扫全败。这是「增量边界量化」发现，非「验证通过」。

## GNN 优化路线（核心贡献）
- Track A 资金链 GraphSAGE（#C44 加权邻接 log1p）：环子图 F1 未训练 0.084→训练后 **0.866（×4.7）**；baseline 二值 0.183。
- Track B 案情异构图 HAN 双通道（合成）。
- 扩线(refinement)设定：AMLSim 锚点 k跳下**拓扑基线 Louvain F1 由盲扫 0.002 提至约 0.11（约一个数量级）**；**训练后 GNN 未见显著增益**（0.0025）。⚠️ 2026-08-04 核验：旧记的"GNN 0.784/Louvain 0.822"在任何结果文件都不存在，**已作废禁用**；论文已统一改为诚实表述（摘要/贡献/结论/Lab4）。

## 工程状态（B+ 科研原型级，绝不可称生产部署）
- 已落地：JWT+RBAC、审计双表、LangGraph 真闭环、HAN 真异构、多环境配置、docker-compose 全栈。
- 缺口：TLS 待证书、真实警务数据端到端验证缺、案卷 OCR→结构化待接、止付冻结仅 Mock（backend/tools/freeze_executor.py，真实对接待警务协调）。

## 用户身份与两条产出线
- 用户=韩冬，湖北警官学院信息技术系大二。
- **A 线·论文**：CPEC2026 教学案例稿，`paper/CPEC2026_draft.tex`（22 页，XeLaTeX+BibTeX）。截 2026-08-15。教学叙事仅服务论文投递。
- **B 线·竞赛**：中国国际大学生创新大赛(2026) 校赛，赛道=**高教主赛道·创意组·"人工智能+"**；报名 8/10 开放、9/15 17:00 截止（后不可改）、9/17 答辩。
- **文献按产出线归位（2026-08-29 定）**：每篇参考文献先分类再决定精力——① 技术方法类（GNN/多智能体/渗透测试）→ 服务 **B 线**系统实现，深读方法；② 教育教学类（AI 赋能教学/实验案例）→ 服务 **A 线**四 Lab 设计，重点读教学设计与结论；③ 政策治理·行为类（如江海洋2025 公众防范行为问卷研究）→ 只服务绪论意义与社会价值叙事，读摘要+结论即可，**不可当技术支撑引用**。韩冬曾疑惑"行为类论文跟我系统有啥关系"，根因是未区分 A/B 线：CPEC 稿是教学案例论文（非技术论文），其论证链"教学干预→能力提升"恰需教育类证据。

## 署名与导师（已锁定）
- 作者序：韩冬(一作)/吴燕波(二作+通信)/徐伟(共二)。基金：大创 S202611332001（徐伟、吴燕波共导）；院级科研（胡老师名义指导，不署作者，致谢提立项，编号待补）。
- **竞赛指导教师限 1 名=吴燕波**；徐伟在致谢如实提，不填官方字段。

## paper 文件夹结构（2026-08-04 重整）
- 用户要求删除全部 5 个 skill（fraudlens-product/paper/competition/tech/ppt），已用 Python rmtree 永久删除；多会话 skill 体系废弃，不再引用。
- paper 只保留 3 个文件夹：
  - `参考文献/`（参考 PDF + references.bib）
  - `会议模板/`（CPEC 各类模板）
  - `论文产出/`（CPEC2026教学案例稿/ 含 .tex/.pdf/审计报告/写作规划/投稿文档；技术稿fraudlens_outline/；项目管理/ 含 项目事实源/需求与完成度追踪/团队组建方案）
- 两篇论文内容已彻底分开（教学案例稿 vs 技术稿）。
- references.bib 已复制到两论文旁以保证独立编译。
- 构建残留（_pandoc_figs、compiled_编译产物）因安全钩子批量删除确认阈值被拦，移出 paper 至 `E:\FraudLens\_build_trash_20260804\` 隔离，待用户确认后永久删除。
- 项目事实源.md 已更新 §0/§8，去掉 skill 引用、路径对齐新结构。

## 论文状态
- 已完成审计修正：F-1(手写→LangGraph StateGraph 全文统一)、F-2(实验溯源脚注)、M-1~M-4、m-2、m-4。
- 教学设计两次重构→**四 Lab 最终版**：Lab1 案情分析与研判流程 / Lab2 工具辅助串并案 / Lab3 冻卡决策与伦理权衡 / Lab4 边界认知与诚实反思。
- 占位待补：吴燕波生年、院级科研编号（问吴老师）。

## 当前状态（2026-08-29 用户表态）
- **A 线 CPEC 教学案例稿停做**：用户明确「不打算做教育类的了」「CPEC 教学案例稿不做了」。四 Lab 教学叙事、教学案例稿、相关 draw.io 图（图2 已落地、图3 规划中）搁置；A 线文献（教学/行为类）降级为「仅背景参考」，不再作为技术支撑引用。
- **B 线·竞赛（技术方向）仍 active**：中国国际大学生创新大赛(2026)，赛道=高教主赛道·创意组·"人工智能+"，9/15 17:00 截止、9/17 答辩。
- **用户当前优先事项**：先真正理解 FraudLens 项目本身（大量代码由 AI 生成、本人不够熟），再谈论文怎么写。已生成项目梳理地图 `E:\FraudLens\FraudLens_项目梳理.html`。
- **代码真实状态（2026-08-29 Explore 核实）**：核心 AI 能力（LangGraph 真反思闭环 backend/agents/orchestrator.py、双 GNN backend/gnn/、9 专项 Agent、ECharts/vis-network 前端、docker 全栈）均为真实现；唯一明确虚实现是**止付冻结** backend/tools/freeze_executor.py（Mock，待警务对接）；gnn/pathb_*、experiment_*、probe_* 为实验残留，非主线，初学者应忽略。

## 用户规矩
- 改动前先讲改动点+回归风险；代码改动记入 docs/09（#C 编号）。
- 参考文献只留正文 `\cite` 实引；降 AI 检测率但诚实边界原样保留。
- **教方法 ≠ 代劳产出（2026-08-29 用户明确纠正）**：用户说"教你读"时，要交付的是**可迁移的方法/关注点清单/自检技巧**，不是把论文内容嚼碎喂给他。已产生的成品（如文献笔记）定位为"模板 + 读后对照检验"，让用户先自己读、再对比找漏，不要让他直接抄。

## 论文制图约定（2026-08-10 起：draw.io 路线，MCP 已放弃）
- **用户拍板（2026-08-10，推翻 08-09 TikZ）**：论文科研图**统一迁到 draw.io (diagrams.net) 所见即所得**。理由：手摆坐标 + 无实时反馈 = 反复改来改去；draw.io 拖拽当场可见布局。
- **MCP 路线已放弃（2026-08-10 深夜）**：WorkBuddy 自带的 `connector-proxy`（HTTP 聚合器，端口每次重启都变 54468/55674/…）在用户机器上 `ECONNREFUSED` 起不来，重开多次无效；无法从外部修复。故放弃 `@drawio/mcp` / `@next-ai-drawio/mcp-server` 任何 MCP 连接。
- **现行路线（2026-08-10 凌晨定，大脑-执行器分离）**：因 Next AI Drawio 把「AI 对话生成」与「SVG 渲染」耦合同一 Electron 进程，一次生成超密图极易 UI 假死/后台长跑。用户要求分离——**Agent（大脑）用 Python 直接算坐标写出 `.drawio` XML 文件**（`gen_drawio_figs.py`），**用户在桌面版 draw.io 打开微调 + 导出 PDF**，发回 Agent 用 `\includegraphics` 嵌主稿 + XeLaTeX 重编译。彻底避开软件内 AI 生成卡顿。mcp.json 仍只留纯 stdio `drawio` 条目（不再经坏代理）。
- **迁移范围**：`fig_arch.tex / fig_workflow.tex / fig_stages.tex / fig_mode.tex` 4 张 TikZ 图全部迁 draw.io；旧 Python 生成器 `build_fig_workflow.py`/`_verify_fig.py` 保留参考但非主路径。
- **诚实代价**：图内字体不与 LaTeX 正文 100% 一致；缓解：draw.io 字体设论文同款（Times/思源宋体）+ 原生 LaTeX 公式(MathJax)；对 CPEC 教学案例稿可接受。
- **调研结论（2026-08-10 联网）**：科研固定分区/工作流图，WYSIWYG 拖拽（draw.io/Inkscape/Visio）最稳；自动布局（Mermaid/D2/Graphviz）会把「固定三列+panel」摊平，不适合本类图。
- **图2 workflow 已落地（2026-08-11 凌晨）**：用户用 Next AI Drawio 生成并导出 `about_blank.pdf`（A4 整页、未裁剪），AI 用 PyMuPDF 自动检测真实内容 bbox、裁掉 PDF 内置标题后保存为 `paper/论文产出/CPEC2026教学案例稿/fig_workflow.pdf`；主稿原 TikZ 代码块替换为 `\includegraphics[width=\textwidth]{fig_workflow.pdf}`，保留 LaTeX `\caption` 统一管理题注；XeLaTeX+BibTeX×3 编译通过，图2 正常显示在第 5 页。

## 图3 设计决策（2026-08-11 读参考文献后定稿）
- **用户诉求**：图要「一目了然」或「结构性非常好」；补「AI 赋能反诈教学 / AI 如何培养学生」的教育叙事。
- **参考学习（已读 18 篇 PDF 并截图分析）**：
  - 刘莞玲《人工智能技术赋能计算机实践教学创新》：中央椭圆「教学过程」+ 四角「多形式/多主体/多维度/全过程」，扁平环绕式；
  - 谢鑫《基于智能体编程的智创编程教学模式探索》：「学生—智能体—教师」三角协同 + 底部「平台/评价」；Fig.5 更延伸为「学生/教师在顶，左右两侧 LMS/AI 平台 Agent，中央竖向流程」；
  - 张金《基于通用大语言模型的计算机系统创新实验设计》：三栏「教师流程 / 能力目标 / 大语言模型智能体（含能力边界）」，明确写出 AI「难以达成」与「可具备辅助」；
  - 向尕《信息安全专业综合实习》：垂直分层「实施层/资源层/平台层」实践教学框架；
  - 李剑《网安课程思政教育》：带菱形判断门的垂直流程；
  - 厉旭杰《集成 AI LLM 的在线编程实验平台》：横向 5 步流水线。
- **综合定稿**：新图 3 采用 **「学生—AI 智能助教—教师」三角协同 + 中央 4-Lab 反诈实训闭环 + 底部育人目标** 的混合布局。既引用谢鑫的三角协同证明这是成熟教育框架，又用刘莞玲的中央闭环体现「AI 赋能」，再用张金的「AI 能力边界」 honesty 框点出我们的核心叙事。该图将替换旧的扁平 `fig_stages.tex`。
- **提示词文件**：`paper/论文产出/CPEC2026教学案例稿/提示词_图3_AI赋能反诈教学实践闭环.md`。
- **防卡顿拆分（2026-08-10 深夜定，已降级）**：原图1/图3 提示词各拆为「第1步骨架→第2步填充→第3步连线」三段（文件 `提示词_图1_架构图_拆分三步.md`、`提示词_图3_AI赋能反诈教学实践闭环_拆分三步.md`），因 Next AI Drawio 同名软件内 AI 生成易卡顿。→ **2026-08-10 凌晨已演进为「Agent 用 Python 直接生成 .drawio XML」路线**，提示词拆分文件保留作参考。

