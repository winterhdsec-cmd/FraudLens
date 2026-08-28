# FraudLens - 反诈智能研判系统

<div align="center">

**基于 Multi-Agent 架构的智能反诈分析平台**

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104%2B-green.svg)](https://fastapi.tiangolo.com/)
[![Vue](https://img.shields.io/badge/Vue-3.5-brightgreen.svg)](https://vuejs.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

</div>

> 📚 **项目文档中心**：进度与规范统一收录在 [`docs/INDEX.md`](./docs/INDEX.md) —— 代码进度看 [`docs/代码进度_CodeStatus.md`](./docs/代码进度_CodeStatus.md)，论文/专利进度看 [`docs/论文与答辩准备_Paper.md`](./docs/论文与答辩准备_Paper.md)。

## 📋 项目简介

FraudLens 是一个面向反诈中心的智能研判系统，采用先进的 Multi-Agent 架构，集成了图神经网络（GNN）、检索增强生成（RAG）、大语言模型（LLM）等技术，实现诈骗案件的智能分析、团伙发现和风险预警。

### 核心特性

- 🤖 **Multi-Agent 智能架构**：基于 LangGraph `StateGraph` 的多智能体反思闭环编排（规划→预处理→分析→聚类→反思，反思节点条件边回连），支持 Agent 协作
- 🧠 **GNN 团伙发现**：使用 HAN（异构图注意力网络）进行案件级团伙聚类，含 5 条元路径双通道融合（结构通道 + BGE 文本通道），GraphCL 无监督预训练；Louvain 社区检测作为降级基线
- 📚 **RAG 知识库**：文档处理、向量化存储、多路召回（向量/关键词/混合检索）
- 💬 **AI 对话助手**：支持多轮对话、工具调用、记忆系统、意图识别
- 🔒 **安全防护**：Prompt 注入检测、输入验证、工具沙箱、熔断器保护
- 📊 **实时监控**：性能指标收集、检查点持久化、分布式追踪
- 🎨 **现代化前端**：Vue 3 + Element Plus，深色科技风 UI，丰富的可视化组件

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend (Vue 3)                        │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │ 案件研判  │ │ 团伙发现  │ │ AI 对话  │ │ 数据看板  │       │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                   Backend (FastAPI + Flask)                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Orchestrator Agent (编排层)               │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐             │  │
│  │  │AnalystAgent│ │ClusterAgent│ │ChatAgent │             │  │
│  │  └──────────┘ └──────────┘ └──────────┘             │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │  Core    │ │  Memory  │ │   RAG    │ │  Tools   │       │
│  │ Security │ │ Short/   │ │Knowledge │ │ Database │       │
│  │ Circuit  │ │ Long/    │ │  Base    │ │ Evidence │       │
│  │ Breaker  │ │ Vector   │ │ Vector   │ │ Risk     │       │
│  │ Checkpoint│ │          │ │ Search   │ │ Statistics│      │
│  │ Metrics  │ │          │ │          │ │          │       │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    Infrastructure                            │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │  MySQL   │ │  Redis   │ │  Celery  │ │  Nginx   │       │
│  │  8.0     │ │  7.0     │ │  Worker  │ │  Proxy   │       │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
└─────────────────────────────────────────────────────────────┘
```

## 🛠️ 技术栈

### 后端
- **Web 框架**: FastAPI + Flask (混合架构，正在迁移到纯 FastAPI)
- **数据库**: MySQL 8.0 + SQLAlchemy 2.0
- **缓存**: Redis 7.0
- **任务队列**: Celery 5.3
- **LLM**: OpenAI API (DeepSeek) + LangChain
- **图神经网络**: PyTorch + PyTorch Geometric（GraphSAGE / **真异构 HAN（资金链感知元路径）**）；含**资金回流闭环检测**与**客观置信度门控**（高置信建议冻结，低置信待人工复核）；OCR 原件与导出报告存**本地 minio 对象存储**（数据不出域）
- **NLP**: Transformers + Sentence-BERT (BGE)
- **OCR**: EasyOCR
- **安全**: JWT 认证 + 输入验证 + Prompt 注入检测

### 前端
- **框架**: Vue 3.5 + Vite
- **UI 组件**: Element Plus
- **可视化**: ECharts 5.6 + Vis-Network
- **HTTP 客户端**: Axios
- **实时通信**: Socket.IO

### 部署
- **容器化**: Docker + Docker Compose
- **反向代理**: Nginx
- **进程管理**: Uvicorn (ASGI)

## 🚀 快速开始

### 环境要求
- Python 3.9+
- Node.js 18+
- MySQL 8.0
- Redis 7.0

### 方式一：Docker 部署（推荐）

```bash
# 1. 克隆项目
git clone https://github.com/yourusername/FraudLens.git
cd FraudLens

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，配置数据库密码、API Key 等

# 3. 启动服务
docker-compose up -d

# 4. 访问系统
# 前端: http://localhost
# 后端 API: http://localhost:5003
```

### 方式二：本地开发部署

#### 后端

```bash
cd backend

# 1. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置环境变量
cp key.env.example key.env
# 编辑 key.env 文件

# 4. 初始化数据库
mysql -u root -p < docker/init.sql
mysql -u root -p < docker/data.sql

# 5. 启动服务
python main.py
```

#### 前端

```bash
cd frontend

# 1. 安装依赖
npm install

# 2. 启动开发服务器
npm run dev

# 3. 构建生产版本
npm run build
```

## 📁 项目结构

```
FraudLens/
├── backend/                    # 后端服务
│   ├── agents/                 # Agent 模块
│   │   ├── orchestrator.py     # 编排 Agent
│   │   ├── analyst_agent.py    # 案件分析 Agent
│   │   ├── cluster_agent.py    # 团伙发现 Agent
│   │   └── chat_agent.py       # 对话 Agent
│   ├── core/                   # 核心模块
│   │   ├── security.py         # 安全模块（输入验证、注入检测）
│   │   ├── circuit_breaker.py  # 熔断器
│   │   ├── checkpoint.py       # 检查点管理
│   │   ├── metrics.py          # 指标收集
│   │   ├── tool_sandbox.py     # 工具沙箱
│   │   └── agent_runtime.py    # Agent 运行时
│   ├── memory/                 # 记忆系统
│   │   ├── short_term.py       # 短期记忆
│   │   ├── long_term.py        # 长期记忆
│   │   └── vector_memory.py    # 向量记忆
│   ├── rag/                    # RAG 模块
│   │   └── knowledge_base.py   # 知识库
│   ├── gnn/                    # 图神经网络模块
│   │   ├── graph_builder.py    # 异构图构建
│   │   ├── gnn_model.py        # GraphSAGE 模型
│   │   ├── community.py        # 社区检测
│   │   └── gang_detector.py    # 团伙检测器
│   ├── tools/                  # 工具集
│   │   ├── database_tools.py   # 数据库查询工具
│   │   ├── evidence_tools.py   # 证据提取工具
│   │   ├── risk_tools.py       # 风险评估工具
│   │   └── rag_tools.py        # RAG 检索工具
│   ├── routes/                 # API 路由
│   │   ├── system.py           # 系统路由
│   │   ├── chat.py             # 对话路由
│   │   ├── cases.py            # 案件路由
│   │   └── gangs.py            # 团伙路由
│   ├── database/               # 数据库模型
│   │   ├── models.py           # ORM 模型
│   │   └── crud.py             # CRUD 操作
│   ├── main.py                 # FastAPI 入口
│   └── requirements.txt        # Python 依赖
│
├── frontend/                   # 前端应用
│   ├── src/
│   │   ├── views/              # 页面视图
│   │   │   ├── DashboardView.vue    # 数据看板
│   │   │   ├── CaseDetailView.vue   # 案件详情
│   │   │   ├── GroupsView.vue       # 团伙发现
│   │   │   ├── ChatView.vue         # AI 对话
│   │   │   └── ...
│   │   ├── components/         # 通用组件
│   │   │   ├── NetworkGraph.vue     # 关系图谱
│   │   │   └── ...
│   │   ├── App.vue             # 根组件
│   │   └── main.js             # 入口文件
│   ├── package.json            # Node 依赖
│   └── vite.config.js          # Vite 配置
│
├── docker/                     # Docker 配置
│   ├── init.sql                # 数据库初始化脚本
│   └── data.sql                # 示例数据
├── docker-compose.yml          # Docker Compose 配置
├── nginx.conf                  # Nginx 配置
└── README.md                   # 项目说明
```

## 🔌 API 文档

### 核心接口

#### 1. 智能研判

```http
POST /api/system/agent-analyze
Content-Type: application/json
Authorization: Bearer <token>

{
  "messages": [
    {
      "case_id": "CASE_001",
      "description": "案件描述",
      "text_messages": ["聊天记录1", "聊天记录2"]
    }
  ],
  "session_id": "optional-session-id"
}
```

#### 2. AI 对话

```http
POST /api/chat/message
Content-Type: application/json
Authorization: Bearer <token>

{
  "message": "查询最近的诈骗案件",
  "session_id": "chat-session-id"
}
```

#### 3. 团伙发现

```http
GET /api/gangs/graph/stats
Authorization: Bearer <token>
```

#### 4. 知识库搜索

```http
POST /api/rag/search
Content-Type: application/json
Authorization: Bearer <token>

{
  "query": "诈骗手法",
  "top_k": 5,
  "strategy": "hybrid"
}
```

### 认证方式

所有 API 接口需要 JWT 认证：

```http
POST /api/auth/login
Content-Type: application/json

{
  "username": "admin",
  "password": "password"
}
```

响应：

```json
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer"
}
```

## 🧪 测试

```bash
# 运行集成测试
cd backend
python test_integration_final.py

# 运行 GNN 模块测试
python test_gnn.py

# 运行端到端测试
python test_e2e_modules.py
```

## 📊 性能指标

系统集成了完整的性能监控：

- **任务成功率**: 实时统计任务执行成功/失败比例
- **工具调用指标**: 记录工具调用次数、成功率、平均延迟
- **LLM 调用指标**: Token 消耗、调用延迟
- **错误追踪**: 错误类型分类、错误消息记录
- **检查点**: 状态持久化、故障恢复

查看指标：

```http
GET /api/system/metrics
Authorization: Bearer <token>
```

## 🔐 安全特性

- ✅ **输入验证**: SQL 注入检测、XSS 防护、命令注入防护
- ✅ **Prompt 注入检测**: 识别指令覆盖、角色扮演攻击、系统提示泄露
- ✅ **工具沙箱**: 超时控制、资源限制、异常隔离
- ✅ **熔断器**: 防止级联故障，支持自动恢复
- ✅ **JWT 认证**: 安全的身份认证和授权
- ✅ **敏感信息保护**: API Key 环境变量管理

## 🗺️ 路线图

- [x] Multi-Agent 架构重构
- [x] GNN 团伙发现模块
- [x] RAG 知识库集成
- [x] 记忆系统（短期/长期/向量）
- [x] 安全防护模块
- [x] 性能监控和指标收集
- [ ] 分布式部署优化
- [ ] 模型微调支持
- [ ] 更多可视化工具
- [ ] 移动端适配

## 🤝 贡献指南

欢迎贡献！请遵循以下步骤：

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## 📧 联系方式

- 项目作者: [Your Name]
- Email: [your-email@example.com]

## 🙏 致谢

- [DeepSeek](https://www.deepseek.com/) - 提供 LLM API 支持
- [LangChain](https://langchain.com/) - Agent 框架参考
- [Vue.js](https://vuejs.org/) - 前端框架
- [FastAPI](https://fastapi.tiangolo.com/) - 后端框架

---

<div align="center">

**如果这个项目对你有帮助，请给一个 ⭐️ Star 支持！**

</div>
