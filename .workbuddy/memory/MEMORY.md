# FraudLens 项目长期记忆

## 一、项目定义与真实架构（代码可指认）
多智能体编排 + 图神经网络的反诈团伙智能研判系统；面向公安反诈中心/基层派出所，单机/内网部署。
- 交互层：Vue3 + Element Plus + ECharts + vis-network（`frontend/`）
- 决策层：FastAPI + **LangGraph StateGraph 真反思闭环**（规划→预处理→分析→聚类→反思，条件边回连，`backend/agents/orchestrator.py`）
- 数据层：MySQL + Redis + BGE-large 本地推理 + 云端 LLM（OpenAI 兼容）+ GNN（`backend/gnn/`）
- 运行环境：后端 `backend/`（端口 5003），MySQL 库 `fraudlens`，Redis 6379；`.env`（docker-compose 注入）+ `backend/key.env`（`main.py`/`tasks.py` dotenv 直接加载）**双份配置**

## 二、诚实口径金律（最高优先级，任何产出不得违反）
- **合成 ≠ 真实验证**；增量边界须量化；GNN 非全设定占优。
- 合成 HAN hard F1=0.947 / clean=1.0；dual-channel gain hard=+0.202；独立 Semantic 基线 clean 1.0 / hard 1.0。
- 真实 AMLSim（43,614 账户 / 1,305 环）全图 F1≈0.002–0.010，**所有方法含 GNN 均失效**；Elliptic 盲扫全败。这是「增量边界量化」发现，**非「验证通过」**。
- ⚠️ 旧记「GNN 0.784 / Louvain 0.822」在任何结果文件都不存在，**已作废禁用**。
- **「数据不出域」不能说满**，统一口径＝**「本地优先 + 出向脱敏」**：① 代码默认 `DISABLE_CLOUD_LLM=1`，但 `.env` / `backend/key.env` / `docker-compose.yml` 的 `${DISABLE_CLOUD_LLM:-0}` 覆盖为 **0（云端开）**，演示实际连阿里云百炼；② 文本出向有脱敏（`CLOUD_LLM_MASK=1`，掩身份证/银行卡/手机号/邮箱，**姓名不掩**）；③ 图片路径已于 2026-09-18 补门禁（`tools/vision.py` 先查 `cloud_llm_enabled()`，关闭则降级本地 OCR）。→ 对外统一表述：**「核心算法全本地；云端大模型可一键切断、切断后自动降级本地 OCR/规则；上云文本强制脱敏」**。PPT/申报书/论文/专利四处口径必须一致。

## 三、GNN 优化路线（核心贡献）
- Track A 资金链 GraphSAGE（#C44 加权邻接 log1p）：环子图 F1 未训练 0.084 → 训练后 **0.866（×4.7）**；baseline 二值 0.183。
- Track B 案情异构图 HAN 双通道（合成）。
- 扩线(refinement)：AMLSim 锚点 k 跳下拓扑基线 Louvain F1 由盲扫 0.002 → 约 0.11（约一个数量级）；**训练后 GNN 未见显著增益**（0.0025）。

## 四、云端 LLM 配置要点
- **双文件陷阱**：key/endpoint/model 必须**同时改 `.env` 与 `backend/key.env`**，只改一处会被另一处覆盖。
- 变量名沿用 `DEEPSEEK_API_KEY` / `DEEPSEEK_BASE_URL` / `DEEPSEEK_MODEL`（代码只认这几个名），endpoint=`https://dashscope.aliyuncs.com/compatible-mode/v1`，模型=`qwen3.8-flash`（多模态 MoE，1M 上下文；最强档改 `qwen3.8-max`）。
- `DISABLE_CLOUD_LLM=0` 启用云端（代码默认 `1`）；`CLOUD_LLM_MASK=1` 出向脱敏（已注入 docker-compose backend+celery）。

## 五、Redis 配置陷阱（2026-09-19 实测修复）
- `REDIS_PASSWORD` 若已配置但本机 Redis **未启用鉴权**，客户端 AUTH 失败 → `get_redis_pool()` 返回 None → **静默降级内存**，会话历史持久化 / JWT 黑名单全部失效。
- 已修两处：`core/redis_pool.py` 的 `RedisPool._connect()`（自动去密码重连）与 `get_redis_client()`（LongTermMemory 等统一入口）。仅当服务端明确回 `no password is set` 才回退，密码错不降级。
- `REDIS_AUTOSTART=1` 才会拉起内置 Redis（`backend/vendor/redis/`）。**脚本必须先 `load_dotenv` 再调 `wait_for_redis()`**，否则 `REDIS_AUTOSTART` 未生效 → 测试"依赖环境里碰巧有 Redis"，结果不可信。
- `LongTermMemory` 曾因 `key.decode()`（而 `decode_responses=True` 返回 str）静默吞异常返回空列表；已修为 `_as_str()` + `scan_iter` 替代 `KEYS` + 按时间戳排序。

## 六、工程状态（B+ 科研原型级，**绝不可称生产部署**）
- 已落地：JWT+RBAC、审计双表、LangGraph 真闭环、HAN 真异构、多环境配置、docker-compose 全栈。
- 缺口：TLS 待证书、真实警务数据端到端验证缺、案卷 OCR→结构化待接、**止付冻结仅 Mock**（`backend/tools/freeze_executor.py`，真实对接需警务协调）。
- **止付冻结链路已于 2026-09-19 修好**（此前**从未成功过**）：`MockFreezeExecutor` 按 `t.get("account")`/`t.get("bank")` 取值，而前端与创建接口写的是 `account_number`/`bank_name` → 静默跳过全部账户 → **0 条回执、工单恒为 `failed`**（3 张线上工单全中）。已加 `_pick()` 兼容三套字段名；状态推导抽成 `_derive_freeze_status()`（`pending` 不再算失败）；并收紧执行门控（**admin 也不得执行未审批工单**，原先可绕过审批链直接冻结）。
- 9 张空表**已于 2026-09-19 填充脱敏演示数据**（`backend/seed_empty_tables.py`，幂等可复现，`SEED=20260918`）：persons 364 / accounts 545 / phones 364 / evidence_items 424 / merge_suggestions 14 / imported_fund_flows 29 / freeze_approvals 4 / freeze_receipts 3 / review_opinions 4。脱敏规范：手机 `138****8888`、卡 `6222 **** **** 8888`、身份证 `4201**********1234`、人名 `张*明`。
- `gnn/pathb_*`、`experiment_*`、`probe_*`、`backend/test_*.py` 为实验残留，非主线。

## 七、用户与产出线
- 用户＝**韩冬**（对外称 hd），湖北警官学院信息技术系**大三**，武汉。
- **B 线·竞赛（唯一活跃线）**：中国国际大学生创新大赛(2026)，赛道＝高教主赛道·创意组·「人工智能+」。**初赛已过（老师评价"非常好"），当前阶段＝复赛准备。**
- **A 线·CPEC 教学案例稿已停做**（用户明确「不打算做教育类的了」）：四 Lab 教学叙事、draw.io 制图约定、图3 设计决策、教学/行为类文献均**降级为背景参考，不再投入**。
- 署名（已锁定）：韩冬(一作) / 吴燕波(二作+通信) / 徐伟(共二)。基金：大创 S202611332001。**竞赛指导教师限 1 名＝吴燕波**；徐伟在致谢如实提，不填官方字段。占位待补：吴燕波生年、院级科研编号。

## 八、用户规矩
- 改动前先讲**改动点 + 回归风险**；代码改动记入 `docs/09`（#C 编号）。
- 报完成前须**端到端自检**（单元 + E2E + 日志），不接受只改代码不验证。
- **教方法 ≠ 代劳产出**：用户说"教你读"时，交付的是**可迁移的方法/关注点清单/自检技巧**，不是把内容嚼碎喂给他。
- 参考文献只留正文 `\cite` 实引；降 AI 检测率但**诚实边界原样保留**。

## 九、回归验证入口（2026-09-19 建，8 脚本 / 217 项）
`python backend/run_verifications.py` 一键跑全部并汇总（退出码 0/1），也可传关键词只跑部分：
`_verify_seed_consistency.py`（数据不变量 17）· `_smoke_frontend_api.py`（前端 GET 全量巡检 40）· `_verify_persons_collision.py`（重点人员碰撞比对 19）· `_verify_freeze_executor.py`（冻结执行器字段兼容+门控+**详情接口字段契约**+端到端 39）· `_verify_merge_panel.py`（并案建议面板 37）· `_verify_seed_api.py`（脱敏数据可见性 18）· `_verify_chat_memory.py`（会话持久化 24）· `_e2e_chat_memory.py`（路由层 E2E + 侧边栏契约 26）。**当前全绿。**
- 新增数据一致性缺陷 → 先 `python backend/fix_seed_consistency.py --dry-run` 审计，去掉 `--dry-run` 修复（覆盖 merge_suggestions / freeze_approvals / freeze_orders 三类）。
- 验证脚本必须 `load_dotenv` 并 `wait_for_redis()` 自举依赖，否则会"依赖环境碰巧有 Redis"而假通过。
- 探针读跨连接写入前须 `db.session.rollback()`（MySQL REPEATABLE READ 会一直用旧快照）；清理测试数据注意外键顺序（先删 `approval_nodes` 再删 `approval_flows`）。
- **写前端前先实拉接口 dump 真实字段名，再用断言锁住**（本项目多次栽在"前端读的字段后端不给"上；冻结执行器 `account` vs `account_number` 即此类）。

## 十、申报书排版规范（改申报书前必读）
`docs/申报书排版原则.md`（2026-09-19 从隔离区抢救）：正文行距固定值 **22 磅**（表格内部与封面个人信息表除外）；每页尽量填满不留大片空白；图题在下、表题在上、解释段紧跟；禁止 1×1 表格嵌套二级标题；编号体系 一、/（一）/1./（1）全文统一；正文含图题统一**小四 12pt**，不得混用五号；**申报书不得含专利相关内容**（尚未申请专利）、不得含论文全文（论文作独立附件）；附录仅放佐证材料清单；避免"供评委参考"等解释性语言；全文用大白话解释术语，避免过度技术化与参数堆叠。

## 十一、已知易复发陷阱
- **静默降级**最危险：「接口 200」≠「功能在工作」。见 `repo-health-audit` 技能阶段 2.5。
- **取样陷阱**：用 `.query().first()` 取样做验证会赌运气（本次曾取到唯一那条 `is_active=False` 记录，一度误判碰撞功能有 bug）。取样要带明确条件。
- **N+1**：列表接口逐条查关联表会放大耗时（`merge.py` 曾 14 条建议打 28 次库 → 101ms；改一次 `IN` 批量取回后 20ms）。
