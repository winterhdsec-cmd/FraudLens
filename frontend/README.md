# FraudLens — 多智能体协同反欺诈智能研判系统

> 基于多 Agent 协同 + 大语言模型的电信网络诈骗智能研判与预警平台

## 项目定位

FraudLens 是一款面向公安反诈实战场景的智能分析系统。系统以案件文本、通话录音、银行流水、聊天记录等多源异构数据为输入，通过 **Preprocess → Chief → Profiler / Cluster / Analyst** 多智能体协同架构，自动完成诈骗案件定性分析、诈骗团伙聚类挖掘、关联网络可视化、资金流向追踪、预警派单生成等全流程研判任务，为一线反诈民警提供"AI 研判副驾驶"。

---

## 系统架构

```
┌──────────────────────────────────────────────────────────────────┐
│                        Frontend (Vue 3)                           │
│   Showcase → 文本录入 → 深度分析 → 案件总览 → 关联网络 → 预警处置  │
└──────────────────────────────┬───────────────────────────────────┘
                               │ HTTP / WebSocket
┌──────────────────────────────▼───────────────────────────────────┐
│                      Backend (FastAPI)                            │
│  ┌─────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐             │
│  │ Auth    │ │ Cases    │ │ Gangs    │ │ Alerts   │ ...         │
│  └─────────┘ └──────────┘ └──────────┘ └──────────┘             │
│  ┌──────────────────────────────────────────────────┐            │
│  │              Multi-Agent Pipeline                 │            │
│  │  Preprocess → Chief → Profiler/Cluster/Analyst    │            │
│  └──────────────────────────────────────────────────┘            │
│  ┌─────────┐ ┌──────────┐ ┌──────────┐                          │
│  │ OCR     │ │ Redis    │ │ WebSocket│                          │
│  └─────────┘ └──────────┘ └──────────┘                          │
└──────────────────────────────┬───────────────────────────────────┘
                               │
┌──────────────────────────────▼───────────────────────────────────┐
│                      Data Layer                                   │
│   MySQL (案件/团伙/预警)  │  Redis (JWT黑名单/进度追踪)           │
│   LangChain + LLM (研判推理)  │  ChromaDB (向量检索)              │
└──────────────────────────────────────────────────────────────────┘
```

---

## 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| **前端框架** | Vue 3 + Vite | Composition API + SFC |
| **UI 组件库** | Element Plus | 企业级 UI 组件 |
| **数据可视化** | ECharts 5 + echarts-wordcloud | 统计图表 & 词云 |
| **关系图谱** | vis-network | 团伙关联网络可视化 |
| **后端框架** | FastAPI + Uvicorn | 异步高性能 API |
| **ORM** | SQLAlchemy 2.0 | 数据库 ORM |
| **数据库** | MySQL + Redis | 业务数据 + 缓存/黑名单 |
| **AI 引擎** | LangChain + LLM | 多智能体协同研判 |
| **向量检索** | ChromaDB + Sentence-Transformers | 语义相似度检索 |
| **OCR** | PaddleOCR / EasyOCR | 图片文字识别 |
| **实时通信** | Socket.IO (WebSocket) | 分析进度实时推送 |
| **认证** | JWT + Refresh Token | 无状态身份认证 |

---

## 功能模块

| 模块 | 路由 | 功能描述 |
|------|------|----------|
| 🏠 **Showcase** | `/` | 项目展示首页，技术能力介绍，一键演示 AI 流程 |
| 📝 **文本录入** | `/input` | 案件文本输入、关键词提取、AI 研判启动 |
| 📤 **图片上传** | `/upload` | 上传聊天截图/银行流水照片，OCR 识别后自动研判 |
| 📊 **Dashboard** | `/dashboard` | 数据大屏：案件趋势、风险分布、诈骗类型排行 |
| 📋 **案件总览** | `/overview` | 全部案件卡片/表格视图，筛选与搜索 |
| 🔍 **案件详情** | `/case-detail` | 单案深度分析：受害者画像、证据链、研判结论 |
| 👥 **诈骗团伙** | `/groups` | 团伙列表、风险评估、技战法标签 |
| 🔗 **团伙详情** | `/details` | 团伙成员结构、关联案件、AI 画像 |
| 🕸️ **关联网络** | `/network` | vis-network 关系图谱：人-案-团伙关联 |
| 💰 **资金流向** | `/capital-flow` | 多级资金链路追踪、流向图谱 |
| 🚨 **预警中心** | `/alerts` | 预警记录管理、签收/处置 |
| 📬 **派单管理** | `/dispatch` | 预警派单、处置反馈 |
| 👤 **重点人员** | `/key-persons` | 高危人员库：前科/在逃/关联人员 |
| 🔌 **API 接入** | `/api` | 模拟对接银行/警务/反诈平台数据源 |
| 📄 **报告导出** | `/report` | 研判报告生成、PDF/打印导出 |
| ⚙️ **系统管理** | `/admin` | 用户管理、系统配置 |
| 📡 **系统状态** | `/status` | 服务健康检查、Agent 状态监控 |

---

## 快速启动

### 环境要求

- **Python** >= 3.10
- **Node.js** >= 18
- **MySQL** >= 8.0
- **Redis** >= 6.0

### 1. 后端启动

```bash
cd backend

# 创建虚拟环境 & 安装依赖
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Linux/Mac
pip install -r requirements.txt

# 配置环境变量 (.env)
# DB_HOST=localhost
# DB_PORT=3306
# DB_USER=root
# DB_PASSWORD=your_password
# DB_NAME=fraudlens
# REDIS_URL=redis://localhost:6379

# 启动服务
python main.py
# 或: uvicorn main:app --host 0.0.0.0 --port 5003 --reload
```

### 2. 前端启动

```bash
cd frontend

npm install
npm run dev
# 访问 http://localhost:5173
```

### 3. 种子数据初始化

登录系统后，若数据库为空，系统会自动弹出提示询问是否加载示例数据。
也可手动调用 API：

```bash
curl -X POST http://localhost:5003/api/seed
```

---

## 项目结构

```
FraudLens/
├── backend/                  # FastAPI 后端
│   ├── agents/               # AI Agent 模块
│   │   ├── chief_agent.py    # 总指挥 Agent：任务编排
│   │   ├── preprocess_agent.py # 预处理 Agent：数据清洗
│   │   ├── profiler_agent.py   # 画像 Agent：个体分析
│   │   ├── cluster_agent.py    # 聚类 Agent：团伙挖掘
│   │   └── analyst_agent.py    # 分析 Agent：综合研判
│   ├── database/             # 数据库层
│   │   ├── models.py         # 核心数据模型 (Case, Gang, Alert)
│   │   ├── p1_models.py      # 扩展模型 (CapitalFlow, Dispatch, KeyPerson)
│   │   └── p1_routes.py      # 种子数据 & 资金/派单/重点人员 API
│   ├── routes/               # API 路由
│   │   ├── auth.py           # 认证 (JWT)
│   │   ├── cases.py          # 案件 CRUD
│   │   ├── gangs.py          # 团伙查询
│   │   ├── sessions.py       # 分析会话 (WebSocket)
│   │   ├── dashboard.py      # 数据大屏
│   │   ├── alerts.py         # 预警管理
│   │   ├── files.py          # 文件上传 & OCR
│   │   ├── reports.py        # 报告生成
│   │   └── searches.py       # 搜索
│   ├── tools/                # 工具模块
│   │   ├── engine.py         # Agent 编排引擎
│   │   ├── ocr.py            # OCR 识别
│   │   └── redis_utils.py    # Redis 工具
│   └── main.py               # 应用入口
│
├── frontend/                 # Vue 3 前端
│   ├── src/
│   │   ├── views/            # 页面组件 (16 个)
│   │   ├── components/       # 公共组件
│   │   │   ├── ShowcaseView.vue   # 首页展示
│   │   │   └── NetworkGraph.vue   # 关联网络图谱
│   │   ├── composables/      # 组合式函数
│   │   │   └── useFraudLens.js    # 核心业务逻辑 (~1400 行)
│   │   ├── router/           # 路由配置
│   │   ├── api.js            # API 封装
│   │   ├── store.js          # 全局状态
│   │   └── App.vue           # 根组件
│   └── package.json
└── README.md
```

---

## 开发团队

| 角色 | 成员 |
|------|------|
| 项目负责人 | — |
| 前端开发 | — |
| 后端开发 | — |
| AI 算法 | — |
| 产品设计 | — |

---

## License

本项目仅用于学术研究与竞赛展示，不涉及商业用途。