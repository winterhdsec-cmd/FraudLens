# FraudLens 前端 / UI 层交接文档

_交接自 WorkBuddy 会话（2026-08-29）。接手方（TRAE）请先读项目根目录 `AGENTS.md`，再读本文。算法层成果见 `docs/算法层交接.md`，两条线互不重叠。_

## 一、这条线做了什么（本轮范围）

用户带截图人工浏览提出 **10 个前端可视性/演示可靠性问题**，本轮已全部处理并推送（commit `39b4ad9`，main）：

| # | 问题 | 根因 | 修法 | 状态 |
|---|---|---|---|---|
| 1 | 资金流向图谱丑 | vis-network 力导向布局把分层 DAG 甩成一团随机漂浮 | 换 ECharts **桑基图**：受害人(青根节点)→一级卡→二级卡→归集/境外，流宽∝金额；`useEcharts.js` 注册了 `charts.SankeyChart` | ✅ 截图验证 |
| 2 | 预警中心无数据 | `get_active_alerts` 只读 Redis，而 `alert:*` 键带 7 天 TTL，过期后把 DB 里的预警"读丢" | DB 为主 + 回写 Redis 缓存，DB 故障才降级；旧种子的假案件号/百分制 confidence/自关联三类脏数据在 `seed.py::_do_alert_data` 自愈重建（基于 gang_case_relations 真实案件对） | ✅ 实测 87 条 |
| 3 | 看板悬浮每格长蓝条 | `tr:hover > td::after` | 收敛为 `td:first-child::after` | ✅ |
| 4 | AI 对话打不开 | ChatView 误读 `localStorage['token']`，真实 token 在 `sessionStorage['fraudlens_token']` | 改用 `store.token` | ✅ |
| 5 | 报告 PDF 太丑 | **reportlab 默认 Helvetica 无中文字形，中文全豆腐块** | 后端注册 `UnicodeCIDFont('STSong-Light')`（内置免字体文件）+ 红头公文版式（机关名/文号/密级/红线/落款/严禁外传页脚）；前端预览、打印、下载统一纸面红头组件 `ReportDocView.vue`（单一数据源 `buildReportDoc()`）；打印走 `window.open` + `w.print()`（可另存 PDF）；下载 PDF/docx 优先调后端 `/api/reports/gang|case`，失败降级本地 HTML | ✅ pymupdf 渲染核对 |
| 6 | 用户管理有问题 | 点"添加用户"无对话框；updateUser/deleteUser 路径少前缀必 404（实际挂 `/api/auth/admin/users/`）；表里 100 个压测垃圾用户无分页刷爆 | 补 Add/Edit 对话框 + 搜索 + 分页 20/页 + admin 保护；路径已修。**注意：100 个 stress_user 还在 DB 里没删**（见待办） | ✅ |
| 7 | 关联图谱"没有了" | 页面一直在，菜单没入口 | `MainLayout.vue` 案件研判组补 `network` 入口 | ✅ |
| 8 | 功能点多不知点哪 | 6 组 13 页，办案工作台与案件/团伙页重复 | **只出了建议没有动代码**（见"四、#8 建议"） | ⚠️ 建议已交付 |
| 9 | 案件总览加载慢 | 实测接口 31-88ms、列表 ~450ms，链路不慢；真凶是缓存 TTL 10s 切页必重拉 391KB + `getCaseGang` 每卡片对 48 团伙 find+includes 的 O(n²) | TTL 提至 30s；getCaseGang 改 computed Map 索引；seed 后 `reloadCasesAndGangs(true)` 绕空缓存 | ✅ 24/24 卡片冒烟 |
| 10 | 团伙画像简陋 | 卡片用了不存在的 `abilities` 字段永远显示假值 | 改真实 `radar_data` 六维雷达 + 作案流程链（steps）+ 关联案件列表（可跳详情） | ✅ |

## 二、关键陷阱（改前端/报表前必读，都踩过）

1. **reportlab**：`TableStyle` 的 `FONTNAME` 必须全表 `(0,0)-(-1,-1)`——只设第一列的话值列仍是 Helvetica，中文又是豆腐块。且 reportlab **不认 `&nbsp;`**，公文元信息分隔用全角空格 `　`。
2. **样式类名污染**：全局深色主题有裸 `.section-title`/`.section-header`，纸面文书组件里凡与全局重名的类都会被盖掉——所以 `ReportDocView` 与 `REPORT_DOC_CSS` 的类统一 `rd-` 前缀（`doc-table`/`doc-para`/`doc-ol` 经查全局无冲突才保留）。新加纸面样式沿用 rd-* 约定。
3. **路由名**：资金流向是 `capital-flow` 不是 `capital`（CaseDetailView 曾错，已修）。新增跳转前先查 `router/index.js`。
4. **auth 路由前缀**：admin/users 实际在 `/api/auth/admin/users/` 下，不是 `/api/admin/users/`。
5. **token 存储**：统一走 `store.js`（sessionStorage `fraudlens_token`），永远不要直接读 localStorage。
6. **后端 `--reload`**：uvicorn 会自动热载 `database/report.py` 等；但 `alert.py`/`seed.py`/`main.py` 若改动未见生效需重启后端（当前 5003 端口进程）。
7. **中文 gang_id**：形如 `GANG_冒充熟人_032`，走 URL 必须 encode，否则 curl/axios 报 Invalid HTTP request。
8. **Vite proxy 前缀匹配**：`/api` 会截走所有 `/api*` 开头路由，新增非 /api 前缀的本地路由要避开。
9. **数据字段真相以 crud.py 为准**：团伙对象**没有** `timeline` 字段（有 `steps`）；早期文档说"没用 LangGraph"已过时（AGENTS.md 有修正说明）。

## 三、环境速查

- 前端 dev：`E:\FraudLens\frontend`，Vite 在 **5173**；后端 uvicorn 在 **5003**（`backend/venv-full/Scripts/python.exe -m uvicorn main:app --reload --port 5003`，由 run-local.bat 拉起）。
- 测试账号：`admin / admin123`。
- 报告 PDF 直读需要后端 venv 里有 `pymupdf`（本轮新装的，仅用于渲染核对，不在 requirements.txt——要不要加由接手方决定）。

## 四、#8 功能收敛建议（已口头交付，未实施）

以一线办案民警视角，收敛路线：

1. **首页改"今日工作台"**：Dashboard 顶部加待办队列区（未处置预警/待研判团伙/待批报告），点条目直达，图表下移。工程量小、演示叙事提升最大，**优先做**。
2. **办案工作台砍掉或合并**：其 5 个 Tab 与案件管理/团伙画像高度重复。推荐砍掉，把独有的"四单流转"并进预警中心。
3. **文本录入 + 文件上传**合并为一个"线索录入"页（两个 Tab）。
4. **AI 对话助手**收进右下角悬浮球，不占一级菜单。
5. 收敛后导航 6 组 13 页 → 4 组 8 页，演示讲"录入线索→看串并→出文书"三步闭环。

## 五、待办（按优先级）

1. **用户表 100 个 stress_user 压测垃圾仍在 DB**（`backend/data/` 的 sqlite）。前端已靠搜索+分页遮住，但参赛演示时用户管理页首屏还是会被懂行的人看出异常。清理 SQL：`DELETE FROM users WHERE username LIKE 'stress_user%';`——**先备份再删，动 DB 前跟用户确认**。
2. **团伙报告 docx**：后端只有 `export_case_docx`，没有 gang docx；前端选"Word + 团伙"会静默降级本地 HTML。要么补后端接口，要么前端把选项置灰说明。
3. #8 的收敛改造（等用户拍板第 2 条砍工作台还是合并）。
4. `.ui-test/`（被 gitignore，本地保留）里有可复用探针：`shot_report.js`（报告页截图）、`probe_perf.js`（overview 首屏耗时 + API timing）、`probe_gangmap.js`（卡片团伙标签冒烟）。改完 UI 用它们回归，登录→overview→report 的 puppeteer 套路是现成的。
5. ReportView 的"关联网络"复选框（includeNetwork）目前没有实际渲染内容（只有 buildReportDoc 不消费它）——要么在报告里补一句网络统计，要么去掉该选项。
6. 后端 reports 里 7 月的旧豆腐块 PDF 还堆在 `backend/reports/`，可清。

## 六、本线提交记录

- `39b4ad9` fix(ui): 修复用户反馈的10个前端可视性问题(#1-#10) —— 已推送 origin/main
- 更早的相关提交：`161c02e`（团伙名裁切）、`33da9c1`/`15554b0`/`f87331b`（骨架屏/分页/echarts 懒加载批次）
- **工作区遗留的 `backend/gnn/*` 未提交改动属于算法会话线**（见 docs/算法层交接.md），不属于本线，勿混提交。
