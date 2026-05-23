<p align="center">
  <h1 align="center">🔍 FraudLens — 多智能体协同反欺诈智能研判系统</h1>
  <p align="center">
    <em>基于 FastAPI + LangChain + DeepSeek + Vue 3 构建的 AI 反诈智能研判平台</em>
  </p>
</p>

---

## 📖 项目简介

FraudLens 是面向公安机关反诈中心的智能研判系统，实现了从数据采集、智能研判、团伙聚类到可视化输出的完整研判链条。系统采用**三层智能体架构**（中枢编排 + 专业分析 + 知识增强），支持文本/图片/文档多模态输入，提供案件管理、团伙发现、资金追踪、预警监测、报告导出等全流程功能。

### ✨ 核心亮点

- 🤖 **6阶段 Agent 研判流水线**：清洗 → 分案 → 分析 → 聚类 → 画像 → 报告
- 🕸️ **交互式关系图谱**：vis-network 力导向布局，支持拖拽/缩放/筛选
- 💰 **资金流向追踪**：多层资金链路可视化，自动标注洗钱路径
- 🔗 **串并案智能推荐**：基于实体重叠的 Jaccard 相似度匹配
- 🚨 **实时预警监测**：新案件自动比对历史数据，命中即预警
- 📊 **数据看板**：ECharts 统计图表 + 关键指标卡片
- 📝 **报告导出**：PDF/Word 格式案件报告与团伙画像
- 🐳 **一键 Docker 部署**：5 服务容器化编排，开箱即用

---

## 🏗️ 系统架构

```
                    ┌─────────────────────────────────────┐
                    │          Nginx (:80)                │
                    │   静态文件 + API反向代理 + WebSocket  │
                    └──────────┬──────────────────────────┘
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
     ┌────────────┐   ┌────────────┐   ┌────────────┐
     │  Frontend  │   │  Backend   │   │   MySQL    │
     │  Vue 3 SPA │   │  FastAPI   │   │   8.0      │
     │  :80/静态   │   │  :5003     │   │  :3306     │
     └────────────┘   └─────┬──────┘   └────────────┘
                            │
                    ┌───────┼───────┐
                    ▼               ▼
             ┌────────────┐  ┌────────────┐
             │   Redis    │  │ DeepSeek   │
             │  7-alpine  │  │   API      │
             │  :6379     │  │ (云端LLM)  │
             └────────────┘  └────────────┘
```

### 项目结构

```
FraudLens/
├── backend/                        # 🖥️ 后端 (FastAPI)
│   ├── main.py                     # 应用入口 + 30+ API 路由
│   ├── agents/                     # 🤖 三层智能体架构
│   │   ├── chief_agent.py          #   中枢编排 (6阶段研判)
│   │   ├── preprocess_agent.py     #   数据清洗/脱敏
│   │   ├── triage_agent.py         #   智能分案
│   │   ├── analyst_agent.py        #   案件深度分析
│   │   ├── cluster_agent.py        #   团伙发现 (BGE→UMAP→HDBSCAN)
│   │   └── profiler_agent.py       #   团伙画像增强
│   ├── database/                   # 数据库模块
│   │   ├── models.py               #   14张数据表 ORM
│   │   ├── p1_models.py            #   资金流向/派单/重点人员
│   │   ├── crud.py / dashboard.py  #   CRUD + 看板统计
│   │   └── importer.py             #   CSV/Excel 批量导入
│   ├── routes/                     # API 路由
│   │   ├── auth.py                 #   JWT 双令牌认证
│   │   ├── cases.py / gangs.py     #   案件/团伙 CRUD
│   │   ├── alerts.py / merges.py   #   预警/串并案
│   │   ├── system.py               #   研判/健康检查/AI配置
│   │   └── files.py                #   文件上传/OCR/视觉分析
│   ├── tools/                      # 工具模块
│   │   ├── engine.py               #   BGE 语义编码引擎
│   │   ├── ocr.py                  #   EasyOCR 文字识别
│   │   ├── vision.py               #   DeepSeek VL 视觉分析
│   │   └── redis_utils.py          #   Redis 缓存/黑名单
│   └── bge-large-zh-v1.5/          # BGE 嵌入模型 (需单独下载)
│
├── frontend/                       # 🌐 前端 (Vue 3 + Element Plus)
│   └── src/
│       ├── views/                  # 页面组件
│       │   ├── DashboardView.vue   #   数据看板
│       │   ├── UploadView.vue      #   智能上传
│       │   ├── OverviewView.vue    #   案件总览
│       │   ├── DetailsView.vue     #   深度分析
│       │   ├── NetworkView.vue     #   关联网络图谱
│       │   ├── CapitalFlowView.vue #   资金流向图谱
│       │   ├── AlertsView.vue      #   预警中心
│       │   ├── DispatchView.vue    #   派单管理
│       │   ├── KeyPersonsView.vue  #   重点人员
│       │   ├── ReportView.vue      #   报告中心
│       │   └── AdminView.vue       #   系统管理 + AI配置
│       ├── components/
│       │   ├── NetworkGraph.vue    #   vis-network 关联图谱
│       │   └── MiniNetworkGraph.vue#   轻量图谱组件
│       ├── composables/
│       │   └── useFraudLens.js     #   数据映射/转换
│       ├── api.js                  #   API 客户端
│       └── style.css               #   深色科技风主题
│
├── docker/                         # 🐳 Docker 配置
│   ├── init.sql                    #   MySQL 建表脚本 (14张表)
│   ├── data.sql                    #   演示数据 (75案件+11团伙)
│   ├── entrypoint.sh               #   后端启动脚本
│   ├── seed.sh                     #   种子数据注入
│   ├── export-data.bat             #   数据导出工具
│   └── import-data.bat             #   数据导入工具
│
├── Dockerfile                      # 多阶段构建
├── docker-compose.yml              # 5服务编排
├── nginx.conf                      # Nginx 反向代理
├── .env.docker                     # 环境变量模板
├── start.bat                       # 一键启动 (Windows)
└── stop.bat                        # 一键停止 (Windows)
```

---

## 🛠️ 技术栈

| 层级 | 技术 |
|------|------|
| **Web 框架** | FastAPI + uvicorn (ASGI) |
| **AI/LLM** | LangChain + DeepSeek Chat |
| **语义编码** | BAAI bge-large-zh-v1.5 |
| **聚类算法** | UMAP 降维 + HDBSCAN 密度聚类 |
| **OCR** | EasyOCR (中英文) |
| **视觉分析** | DeepSeek VL2 多模态 |
| **数据库** | MySQL 8.0 + SQLAlchemy 2.0 |
| **缓存** | Redis 7 (令牌黑名单/预警缓存/进度推送) |
| **认证** | PyJWT 双令牌 (Access + Refresh) |
| **前端** | Vue 3 + Element Plus + vis-network |
| **实时通讯** | WebSocket |
| **容器化** | Docker + docker-compose + Nginx |

---

## 🚀 快速开始

### 方式一：Docker 一键部署（推荐）

#### 前置条件

- [Docker Desktop](https://www.docker.com/products/docker-desktop) 已安装并运行

#### 部署步骤

**1. 克隆项目**

```bash
git clone https://github.com/你的用户名/FraudLens.git
cd FraudLens
```

**2. 配置环境变量**

```bash
# Windows
copy .env.docker .env

# macOS/Linux
cp .env.docker .env
```

编辑 `.env` 文件，填入你的 DeepSeek API Key：

```env
DEEPSEEK_API_KEY=sk-你的API密钥
```

> 💡 也可以启动后在系统管理页面的「AI 配置」中在线设置

**3. 一键启动**

```bash
# Windows: 双击 start.bat 或命令行执行
start.bat

# macOS/Linux
docker-compose up -d --build
```

**4. 下载 BGE 模型（可选）**

BGE 模型用于团伙聚类分析，如需此功能：

```bash
# 从 HuggingFace 下载 bge-large-zh-v1.5
# 放置到 backend/bge-large-zh-v1.5/ 目录

# 然后复制到容器中
docker cp backend/bge-large-zh-v1.5/. $(docker-compose ps -q backend):/app/bge-large-zh-v1.5/
docker-compose restart backend
```

> ⚠️ 不下载 BGE 模型不影响其他功能，仅团伙聚类分析不可用

**5. 访问系统**

- 🌐 系统地址：http://localhost
- 👤 默认账号：`admin` / `admin123`

#### 常用命令

```bash
docker-compose logs -f          # 查看实时日志
docker-compose restart backend  # 重启后端
docker-compose down             # 停止所有服务
docker-compose down -v          # 停止并清除数据
```

#### 数据管理

```bash
# 导出本地 MySQL 数据到 Docker
docker\export-data.bat

# 导入数据到已运行的 Docker MySQL
docker\import-data.bat

# 注入种子演示数据
docker-compose run --rm seed
```

---

### 方式二：本地开发

#### 前置条件

- Python 3.10+
- Node.js 18+
- MySQL 8.0+
- Redis（可选）

#### 1. 配置后端

```bash
cd backend

# 创建 key.env 配置文件
# 填入以下内容：
# DEEPSEEK_API_KEY=sk-你的API密钥
# DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
# DEEPSEEK_MODEL=deepseek-chat
# DB_HOST=localhost
# DB_PORT=3306
# DB_USER=root
# DB_PASSWORD=你的MySQL密码
# DB_NAME=fraudlens

# 安装依赖
pip install -r requirements.txt

# 下载 BGE 模型到 backend/bge-large-zh-v1.5/
# 从 https://huggingface.co/BAAI/bge-large-zh-v1.5 下载

# 启动后端
python main.py
```

#### 2. 配置前端

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

#### 3. 访问

- 前端：http://localhost:5173
- 后端 API：http://localhost:5003
- 默认账号：`admin` / `admin123`

---

## 📋 功能模块

| 功能模块 | 说明 |
|---------|------|
| **智能研判** | 6阶段 Agent 流水线：清洗→分案→分析→聚类→画像→报告 |
| **案件管理** | 完整 CRUD + 状态流转 (待分析→已分析→已立案→侦办中→已结案) |
| **团伙发现** | BGE 语义编码 → UMAP 降维 → HDBSCAN 聚类 |
| **串并案推荐** | 基于手机号/银行卡/IP 实体重叠的 Jaccard 相似度 |
| **资金追踪** | 多层资金链路可视化，自动标注洗钱路径 |
| **预警监测** | 新案件自动比对历史数据，命中实体触发预警 |
| **关联图谱** | vis-network 交互式力导向图谱 |
| **派单管理** | 案件派单→签收→处置→反馈全流程 |
| **重点人员** | 前科人员/高危人员/涉诈重点人/两卡人员管理 |
| **报告导出** | PDF/Word 案件报告 + 团伙画像报告 |
| **批量导入** | CSV/Excel 批量导入 + OCR 图片识别 + 视觉分析 |
| **数据看板** | ECharts 统计图表 + 关键指标卡片 |
| **AI 配置** | 前端在线设置 API Key，无需修改配置文件 |

---

## 📡 API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/auth/login` | 用户登录 |
| POST | `/api/auth/register` | 用户注册 |
| GET | `/api/auth/me` | 当前用户信息 |
| PUT | `/api/auth/change-password` | 修改密码 |
| POST | `/agent-analyze` | 智能研判分析 |
| GET | `/api/cases` | 案件列表 |
| GET | `/api/cases/{id}` | 案件详情 |
| PUT | `/api/cases/{id}/status` | 案件状态流转 |
| GET | `/api/gangs` | 团伙列表 |
| GET | `/api/gangs/{id}` | 团伙详情 |
| GET | `/api/dashboard` | 数据看板 |
| GET | `/api/alerts` | 活跃预警 |
| POST | `/api/merges/suggest` | 串并案推荐 |
| GET | `/api/reports/case/{id}` | 案件报告 |
| GET | `/api/reports/gang/{id}` | 团伙报告 |
| POST | `/api/import/csv` | CSV 批量导入 |
| POST | `/api/import/excel` | Excel 批量导入 |
| POST | `/api/ocr` | OCR 图片识别 |
| POST | `/api/analyze-file` | 文件智能分析 |
| POST | `/api/vision-analyze` | 视觉分析 |
| GET | `/api/settings/api-key` | 获取 AI 配置状态 |
| PUT | `/api/settings/api-key` | 更新 AI 配置 |
| GET | `/health` | 健康检查 |
| WS | `/ws/{session_id}` | 实时进度推送 |

---

## 🗄️ 数据库

系统共 14 张数据表：

| 表名 | 说明 |
|------|------|
| `users` | 用户/权限 |
| `operation_logs` | 操作审计日志 |
| `analysis_sessions` | 分析会话 |
| `cases` | 诈骗案件 |
| `gangs` | 犯罪团伙 |
| `gang_case_relations` | 团伙-案件关联 |
| `persons` | 人员信息 |
| `accounts` | 银行账户 |
| `phones` | 电话号码 |
| `evidence_items` | 证据材料 |
| `alert_records` | 预警记录 |
| `merge_suggestions` | 串并案建议 |
| `capital_flows` | 资金流向 |
| `dispatch_orders` | 派单记录 |
| `key_persons` | 重点人员 |

---

## 🐳 Docker 架构说明

```
docker-compose.yml 编排 5 个服务：

┌──────────────────────────────────────────────────┐
│  nginx:alpine (:80)                              │
│  - 反向代理 /api/* → backend:5003                │
│  - 静态文件 / → Vue SPA                          │
│  - WebSocket /ws/* → backend:5003                │
├──────────────────────────────────────────────────┤
│  backend (Python 3.11) (:5003)                   │
│  - FastAPI 应用                                   │
│  - BGE 模型通过 Volume 挂载                       │
│  - EasyOCR 模型通过 Volume 持久化                 │
├──────────────────────────────────────────────────┤
│  mysql:8.0 (:3306, 宿主机:3307)                  │
│  - 自动执行 init.sql 建表                         │
│  - 自动执行 data.sql 导入演示数据                  │
│  - 数据持久化到 mysql-data Volume                 │
├──────────────────────────────────────────────────┤
│  redis:7-alpine (:6379, 宿主机:6380)             │
│  - 密码认证                                       │
│  - 数据持久化到 redis-data Volume                 │
├──────────────────────────────────────────────────┤
│  seed (一次性容器)                                │
│  - 运行 seed_demo.py 注入 75 条演示案件           │
│  - 执行完毕自动退出                               │
└──────────────────────────────────────────────────┘
```

### 数据持久化

| 操作 | 数据是否保留 |
|------|-------------|
| `docker-compose restart` | ✅ 保留 |
| `docker-compose down` | ✅ 保留 |
| `docker-compose down -v` | ❌ 删除（`-v` 才清除 Volume） |

### BGE 模型说明

BGE 模型文件约 1.3GB，不打包进 Docker 镜像（避免镜像膨胀）。采用 Volume 挂载方式：

1. **首次部署**：从 [HuggingFace](https://huggingface.co/BAAI/bge-large-zh-v1.5) 下载模型到 `backend/bge-large-zh-v1.5/`
2. **复制到容器**：`start.bat` 会自动检测并复制，或手动执行 `docker cp`
3. **不安装 BGE**：系统仍可正常运行，仅团伙聚类分析功能不可用

---

## 📜 版本历史

| 版本 | 说明 |
|------|------|
| v1.0 | 基础框架：Flask + Vue + BGE 聚类 |
| v2.0 | 公安实战：JWT 认证 + 案件管理 + 串并案 + 报告导出 |
| v3.0 | 架构升级：FastAPI + Celery + DeepSeek LLM + WebSocket |
| v3.1 | Docker 部署 + vis-network 图谱 + AI 配置界面 + 资金追踪 |
