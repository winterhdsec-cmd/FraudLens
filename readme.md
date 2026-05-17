# FraudLens - AI 反诈智能研判系统

基于 **FastAPI + Celery + Vue 3** 构建的 AI 反诈智能研判系统，面向公安机关反诈中心民警使用。系统实现了从数据采集、智能研判、团伙聚类到可视化输出的完整研判链条。

---

## 系统架构

```
FraudLens/
├── backend/                    # 🖥️ 后端 (FastAPI + Celery)
│   ├── main.py                 # ★ 应用入口 (30+ API 路由)
│   ├── celery_app.py           # Celery 异步任务配置
│   ├── tasks.py                # Celery 任务定义
│   ├── agents/                 # 🤖 三层智能体架构
│   │   ├── chief_agent.py      # 中枢编排 (6阶段研判流程)
│   │   ├── preprocess_agent.py # 数据清洗/脱敏
│   │   ├── triage_agent.py     # 智能分案
│   │   ├── analyst_agent.py    # 案件深度分析
│   │   ├── cluster_agent.py    # 团伙发现 (BGE→UMAP→HDBSCAN)
│   │   └── profiler_agent.py   # 团伙画像增强
│   ├── database/               # 数据库模块
│   │   ├── models.py           # 11张数据表
│   │   ├── crud.py             # CRUD操作
│   │   ├── auth.py             # JWT认证 + 审计
│   │   ├── alert.py            # 预警监测
│   │   ├── merge.py            # 串并案推荐
│   │   ├── report.py           # PDF/Word报告
│   │   ├── dashboard.py        # 数据看板统计
│   │   └── importer.py         # CSV/Excel批量导入
│   ├── tools/engine.py         # BGE语义编码引擎
│   └   └── key.env                 # API密钥配置
│
└── frontend/                   # 🌐 前端 (Vue 3 + Element Plus)
    └── src/
        ├── App.vue             # 主页面 (7个视图)
        ├── api.js              # API客户端
        ├── store.js            # 认证状态管理
        └── style.css           # 深色科技风主题
```

## 核心功能

| 功能模块 | 说明 |
|---------|------|
| **智能研判** | 5阶段 Agent 流水线：清洗→分案→分析→聚类→画像 |
| **案件管理** | 完整 CRUD + 状态流转 (待分析→已分析→已立案→侦办中→已结案) |
| **串并案推荐** | 基于手机号/银行卡/IP 实体重叠的 Jaccard 相似度自动推荐 |
| **团伙聚类** | BGE 语义编码 → UMAP 降维 → HDBSCAN 聚类 + 质量评估 |
| **预警监测** | 新案件自动比对历史数据，命中实体触发预警 |
| **报告导出** | PDF/Word 案件报告 + 团伙画像报告 |
| **批量导入** | CSV/Excel 批量导入案件数据批量导入 |
| **数据看板** | 4张 ECharts 图表 + 统计卡片 + 最新案件列表 |
| **关系图谱** | SVG 团伙关联网络可视化 |

## 技术栈

| 层级 | 技术 |
|------|------|
| **Web框架** | FastAPI + uvicorn |
| **任务队列** | Celery + Redis (可选) |
| **数据库** | MySQL + SQLAlchemy |
| **认证** | PyJWT (令牌黑名单) |
| **语义编码** | BAAI BGE-large-zh-v1.5 |
| **LLM** | 阿里云百炼 (DeepSeek-v4-flash) |
| **前端** | Vue 3 + Element Plus + ECharts |
| **实时通讯** | WebSocket |

## 快速启动

### 前置条件

- Python 3.10+
- Node.js 18+
- MySQL 8.0+
- BGE 模型文件放在 `backend/bge-large-zh-v1.5/`

### 1. 配置API密钥

```bash
# 创建 key.env
DASHSCOPE_API_KEY=你的阿里云百炼API Key
```

### 2. 启动后端

```bash
cd backend
pip install -r requirements.txt
python main.py
```

服务启动在 `http://localhost:5000`

### 3. 启动前端

```bash
cd frontend
npm install
npm run dev
```

访问 `http://localhost:5173`

### 4. 登录

默认管理员账号: **admin** / **admin123**

## 可用API

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/auth/login | 登录 |
| POST | /api/auth/register | 注册 |
| POST | /agent-analyze | 智能研判 |
| GET | /api/cases | 案件列表 |
| PUT | /api/cases/{id}/status | 案件状态流转 |
| GET | /api/gangs | 团伙列表 |
| GET | /api/dashboard | 数据看板 |
| GET | /api/alerts | 活跃预警 |
| POST | /api/merges/suggest | 串并案推荐 |
| GET | /api/reports/case/{id} | 案件报告 (PDF/Word) |
| POST | /api/import/csv | CSV批量导入 |
| WS | /ws/{session_id} | 实时进度推送 |

## 数据库表

- `users` — 用户/权限
- `cases` — 案件
- `gangs` — 团伙
- `gang_case_relations` — 团伙-案件关联
- `persons` — 人员信息
- `accounts` — 银行账户
- `phones` — 电话号码
- `evidence_items` — 证据材料
- `analysis_sessions` — 分析会话
- `operation_logs` — 审计日志
- `merge_suggestions` — 串并案建议

## 项目版本

| 版本 | 说明 |
|------|------|
| v1.0 | 基础框架: Flask + Vue + BGE 聚类 |
| v2.0 | 公安实战: JWT认证 + 案件管理 + 串并案 + 串并案 + 报告导出 |
| v3.0 | 架构升级: FastAPI + Celery + 真实LLM + WebSocket |