# FraudLens 项目长期记忆

## 一、项目与真实架构（代码可指认）
多智能体编排 + GNN 的反诈团伙智能研判系统；面向公安反诈中心/基层派出所，单机/内网部署。
- 交互：Vue3 + Element Plus + ECharts + vis-network（`frontend/`）
- 决策：FastAPI + **LangGraph StateGraph 真反思闭环**（规划→预处理→分析→聚类→反思，条件边回连，`backend/agents/orchestrator.py`）
- 数据：MySQL + Redis + BGE-large 本地推理 + 云端 LLM（OpenAI 兼容）+ GNN（`backend/gnn/`）
- 端口：后端 **5003**、前端 **5173**、MySQL `fraudlens`、Redis 6379（后端自动拉起）。登录 `admin/admin123`。
- 配置**双份**：`.env`（compose 注入）+ `backend/key.env`。**`main.py` 只读 `key.env`，从不读根目录 `.env`**。

## 二、诚实口径金律（最高优先级，任何产出不得违反）
- **合成 ≠ 真实验证**；增量边界须量化；GNN 非全设定占优。
- 合成 HAN hard F1=0.947 / clean=1.0；dual-channel gain hard=+0.202；Semantic 基线 clean/hard 均 1.0。
- 真实 AMLSim（43,614 账户/1,305 环）全图 F1≈0.002–0.010，**所有方法含 GNN 均失效**；Elliptic 盲扫全败。这是「增量边界量化」，**非「验证通过」**。
- ⚠️ 旧记「GNN 0.784 / Louvain 0.822」在任何结果文件都不存在，**已作废禁用**。
- **「数据不出域」不能说满**，统一口径＝**「本地优先 + 出向脱敏」**：代码默认 `DISABLE_CLOUD_LLM=1`，但 `.env`/`key.env`/compose 的 `${DISABLE_CLOUD_LLM:-0}` 覆盖为 **0（云端开）**，演示实际连阿里云百炼；文本出向脱敏（`CLOUD_LLM_MASK=1`，掩身份证/银行卡/手机号/邮箱，**姓名不掩**）；图片 2026-09-18 补门禁（`tools/vision.py` 先查 `cloud_llm_enabled()`，关闭则降级本地 OCR）。→ 对外统一：**「核心算法全本地；云端大模型可一键切断、切断后自动降级本地 OCR/规则；上云文本强制脱敏」**。PPT/申报书/论文/专利四处口径必须一致。

## 三、GNN 路线（核心贡献）
- Track A 资金链 GraphSAGE（#C44 加权邻接 log1p）：环子图 F1 未训练 0.084 → 训练后 **0.866（×4.7）**；baseline 二值 0.183。
- Track B 案情异构图 HAN 双通道（合成，双通道增益 hard +0.202）。
- 扩线 refinement：AMLSim 锚点 k 跳下 Louvain F1 盲扫 0.002 → 约 0.11（约一个数量级）；**训练后 GNN 未见显著增益**（0.0025）。

## 四、配置与 Redis（三处已修，含两条铁律）
- 云端 LLM：变量名沿用 `DEEPSEEK_API_KEY`/`DEEPSEEK_BASE_URL`/`DEEPSEEK_MODEL`（代码只认这几个名）；endpoint=`https://dashscope.aliyuncs.com/compatible-mode/v1`，模型 `qwen3.8-flash`（多模态 MoE，1M 上下文；最强档 `qwen3.8-max`）。
- **双文件陷阱**：key/endpoint/model 必须**同时改 `.env` 与 `key.env`**，只改一处会被另一处覆盖。
- `REDIS_PASSWORD` 配了但服务端未鉴权 → AUTH 失败 → `get_redis_pool()` 返回 None → **静默降级内存**。已修 `core/redis_pool.py`：仅当服务端明确回 `no password is set` 才去密码重连，密码错不降级。`LongTermMemory` 曾因 `key.decode()`（而 `decode_responses=True` 返回 str）静默吞异常，已修 `_as_str()` + `scan_iter`。
- ⚠️ **【已推翻，勿再当缺陷】** 我曾把「Redis 密码不一致 → 单次调用 2–25 秒」列为 P0。真实运行实测 **2ms，不存在**。假象来源＝脚本写了 `load_dotenv(.env)` → `load_dotenv(key.env)`，而 python-dotenv 默认 **`override=False`（先加载者胜出）**，`.env` 的值盖过 `key.env`，造出只存在于脚本里的组合。另：`core/config.py` 的 pydantic `env_file=".env"` **按 cwd 解析**，从 `backend/` 启动读不到。保留的加固只是**防御性**的。
- **铁律 A：验证脚本的配置加载方式必须与被测程序逐字一致。** 12 个验证/维护脚本已统一为「只加载 key.env」。否则测的是脚本环境，不是产品。
- **铁律 B：见到 redis-py 客户端就问 —— 这里失败会不会被当「可重试」而退避重试？** 同模式栽过两次：`core/redis_embedded.py::_shutdown_embedded()` 的 `shutdown(save=True)` 让服务端主动断连 → 指数退避 → **阻塞 44.6 秒**；加 `Retry(NoBackoff(), 0)` 后 **0.2s**，回归 9分01秒 → 3分04秒。`RedisPool._connect()` 的 ping **保留**重试（哨兵场景刻意设计）。
- **待用户决定**：`JWT_SECRET_KEY` 两份取值不同 → 换部署方式会让**所有已签发 token 失效**。密钥类操作未动。`python backend/check_config.py` 报 ERROR，统一后变绿。

## 五、工程状态（B+ 科研原型级，**绝不可称生产部署**）
- 已落地：JWT+RBAC、审计双表、LangGraph 真闭环、HAN 真异构、多环境配置、compose 全栈。9 张表已填脱敏演示数据（`seed_empty_tables.py`，幂等，`SEED=20260918`）。
- 缺口：TLS 待证书、真实警务数据端到端验证缺、案卷 OCR→结构化待接、**止付冻结仅 Mock**（`tools/freeze_executor.py`）。
- 止付冻结链路 2026-09-19 才**首次真正跑通**：执行器取 `t.get("account")` 而前端写的是 `account_number` → 静默跳过全部账户 → 0 回执、工单恒 `failed`。已加 `_pick()` 兼容三套字段名 + `_derive_freeze_status()` + 收紧门控（**admin 也不得执行未审批工单**）。
- 脱敏规范：手机 `138****8888`、卡 `6222 **** **** 8888`、身份证 `4201**********1234`、人名 `张*明`。
- `gnn/pathb_*`、`experiment_*`、`probe_*`、`backend/test_*.py` 为实验残留，非主线。

## 六、用户与产出线
- 用户＝**韩冬**（对外称 hd），湖北警官学院信息技术系**大三**，武汉。
- **B 线·竞赛（唯一活跃线）**：中国国际大学生创新大赛(2026)，高教主赛道·创意组·「人工智能+」。**初赛已过**，当前＝复赛准备。
- **A 线·CPEC 教学案例稿已停做**（用户明确「不打算做教育类的了」），相关叙事/制图约定降级为背景参考，不再投入。
- 署名（锁定）：韩冬(一作)/吴燕波(二作+通信)/徐伟(共二)。基金：大创 S202611332001。**竞赛指导教师限 1 名＝吴燕波**。占位待补：吴燕波生年、院级科研编号。

## 七、用户规矩
- 改动前先讲**改动点 + 回归风险**；代码改动记入 `docs/09`（#C 编号）。
- 报完成前须**端到端自检**（单元 + E2E + 日志）。
- **教方法 ≠ 代劳产出**：用户说"教你读"时，交付**可迁移的方法/关注点清单/自检技巧**。
- 参考文献只留正文 `\cite` 实引；降 AI 检测率但**诚实边界原样保留**。

## 八、回归验证入口（**12 脚本，全绿，约 60s**）
`python backend/run_verifications.py`（退出码 0/1），可传关键词只跑部分：
`_verify_seed_consistency`(20) · `_verify_db_isolation`(4) · `_smoke_frontend_api` · `_verify_persons_collision`(19) · `_verify_freeze_executor` · `_verify_review_flow`(27) · `_verify_alert_flow`(13) · `_verify_demo_reset`(18) · `_verify_merge_panel` · `_verify_seed_api`(18) · `_verify_chat_memory`(24) · `_e2e_chat_memory`(26)。
- 数据一致性缺陷 → 先 `python backend/fix_seed_consistency.py --dry-run` 审计，再去掉 `--dry-run` 修复。
- 脚本必须 `load_dotenv` + `wait_for_redis()` 自举依赖，否则"依赖环境碰巧有 Redis"而假通过。
- **断言落库结果必须用独立连接读**（`with db.engine.connect()`）：`db.session` 是 thread-local，TestClient 在另一线程提交，主线程 session 读到**旧快照** → "接口 200 但断言读不到"的**假失败**。先怀疑读法。
- 探针读跨连接写入前须 `db.session.rollback()`；清理测试数据注意外键顺序（先 `approval_nodes` 再 `approval_flows`）。
- **新增 400 校验前先确认 handler 有 `except HTTPException: raise`** —— 只有 `except Exception` 时会被兜成 **500**。
- **终态不可逆**：所有状态机（冻结工单/HITL 复核/审批流/预警处置/派单）终态不得再流转或改写结论。修一处顺手查同类。

## 九、数据库事务卫生（2026-09-22，两个同源缺陷已修）
**根源一句话**：`db.session` **thread-local 且从不被中间件清理** → 工作线程被复用，事务一直延续。后果：①未提交的写**永久持锁**；②REPEATABLE READ 下**读旧快照**。
- **铁律 1：daemon 后台线程写库必须显式收尾。** `main.py::_background_init` 每次启动在 daemon 线程跑初始化；`seed.py::_do_alert_data()` 的 `.delete()` **0 行命中也留表级意向锁**，紧接 `if count>0: return` 不结束事务 → `alert_records` **永久锁死**，之后写该表 Lock wait timeout(50s)→500（**每次启动埋一颗雷**）。已修：seed 补 rollback + `_background_init` 加 **try/finally 兜底**（commit→rollback→remove）。
- **铁律 2：`.delete()`/`.update()` 即使 0 行命中也可能加锁**，不能因"没删到东西"就不结束事务。
- **铁律 3：MySQL 引擎已设 `isolation_level='READ COMMITTED'`**（`database/__init__.py`，仅 mysql）。此前 REPEATABLE READ + session 复用 → 别的请求刚提交的数据读不到（实测 `GET /api/alerts` 写后仍返回旧 87 条）。改后**立即可见**、不加间隙锁。
- **诊断锁顺序**：`information_schema.innodb_trx`（谁挂着）→ `performance_schema.data_locks`（持了什么锁）→ `SHOW PROCESSLIST` → **停服对照**（确认归属）。
- **判据盯「有害性」而非「存在性」**：护栏曾断言"无 >30s 挂起事务"→ 恒失败；实则那些是 `trx_rows_locked=0` 的**空闲只读事务**（READ COMMITTED 下无害）。改判为"无 >30s 的**持锁**事务"。

## 十、本机环境硬限制（会反复遇到，必须先讲清楚）
- **AI 起的服务无法常驻**：`nohup … &`（命令结束即回收整棵进程树）、工具托管后台任务（会话空闲后回收，**无任何报错日志**）、`Start-Process`（被安全策略拦/静默无效）、**`schtasks`（彻底封禁，不得绕过）**。→ 「保持服务运行」只能由**用户自己双击** `E:\FraudLens\启动演示.bat`（用 `start` 开独立窗口）。**说"服务已起"时必须同时说明这一点**。
- **本环境无法执行 `.bat`**：从 Bash 与另一个 shell 工具调 `cmd.exe` 均被安全策略拦截 → 只能做**静态校验**（行尾/BOM/标签与 goto 目标/括号平衡）+ 关键子逻辑等价实测。**不要把"静态检查通过"说成"运行验证通过"**。
- **写 `.bat` 必须 CRLF 且无 BOM**：cmd.exe 对 LF-only 批处理解析 `:label`/`goto`/`call` 不可靠，会「跑一半静默退出」。仓库已加 `.gitattributes` 固化（`*.bat/*.cmd/*.ps1`→`eol=crlf`，其余源码 `eol=lf`）。2026-09-22 修正 8 个 LF-only 批处理（`start.bat`/`start_police.bat` 含 5、3 个标签，风险最高）。

## 十一、前端与可视化铁律
- **写前端前先实拉接口 dump 真实字段名，再用断言锁住**（多次栽在"前端读的字段后端不给"；冻结执行器 `account` vs `account_number`）。见到 `ElMessageBox.alert(JSON.stringify(row))` 即视为"未完成的详情页"（已复发 4 次，现全消灭）。
- **dump 必须深入到数组元素的形状**：只 dump 顶层键会漏嵌套结构 —— 曾因此让表决记录表三列全空（用了 `role`/`status`/`decided_at`，实际 `approver_role`/`decision`/`created_at`），**构建通过、断言全绿，只有看图才发现**。
- **改组件库按钮颜色必须同时清 `background-image`**：全局主题给 `.el-button--primary` 加了蓝色渐变，只改 `background-color` 时**断言过、界面仍是蓝**。裁决用「裁剪截图 + 像素取色」，不靠肉眼。Element Plus 2.x 的 `confirmButtonClass` 不生效，用 `customClass`。
- **UI 改动必须真开页面看**（`frontend-visual-verify` 技能）；**构建通过 ≠ 界面能用**。
- **grep 只能给候选，判定要看实际实现**：曾用"有 el-table 但无 v-loading"断定 5 个视图缺加载态，核实后 OverviewView 已有骨架屏（假阳性）。**盘点结论要二次核实** —— 曾有 3 条 grep 判断，2 条是假阳性。

## 十二、其他易复发陷阱
- **静默降级**最危险：「接口 200」≠「功能在工作」。**「能启动」≠「能演示」**：09-22 两个缺陷都不影响启动、接口探测全 200，只在**真写一次数据**时暴露。
- **排查报错认第一个异常**：`el-tabs unregisterPane` 之类是**次生错误**；用「回退到上一提交再跑一次」的对照实验确认归属。
- **取样陷阱**：`.query().first()` 取样赌运气（曾取到唯一那条 `is_active=False` 记录，误判有 bug）。
- **JSON 列经 `text()` 查询返回字符串**：`isinstance(x, list)` 恒为假 → 静默漏检，需先 `json.loads`。
- **N+1**：`merge.py` 曾 14 条建议打 28 次库 → 101ms；改一次 `IN` 批量取回后 20ms。
- **演示文案**：测试脚本写入的「E2E 测试」「测试账户A」会出现在界面上；`fix_seed_consistency.py` 已纳入审计（V11–V13）。

## 十三、申报书排版规范（改申报书前必读）
`docs/申报书排版原则.md`：正文行距固定值 **22 磅**（表格内部与封面个人信息表除外）；每页填满不留大片空白；图题在下、表题在上、解释段紧跟；禁止 1×1 表格嵌套二级标题；编号 一、/（一）/1./（1）全文统一；正文含图题统一**小四 12pt**；**申报书不得含专利相关内容**、不得含论文全文；附录仅放佐证材料清单；避免"供评委参考"等解释性语言；用大白话解释术语。
