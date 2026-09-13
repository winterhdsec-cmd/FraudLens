# FraudLens — 反诈智能研判系统

<div align="center">

面向反诈中心的智能辅助研判平台：上传诈骗线索，经多智能体流水线分析，实现案件串并、团伙发现与风险预警。

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104%2B-green.svg)](https://fastapi.tiangolo.com/)
[![Vue](https://img.shields.io/badge/Vue-3.5-brightgreen.svg)](https://vuejs.org/)

</div>

## 本仓库公开范围

本仓库公开系统的**工程性代码与文档**，作为系统开发完成度的可查证依据：

- 前端界面组件（Vue 3 + Element Plus）
- 后端接口服务骨架（FastAPI、数据库设计、工具链、安全与可观测性组件）
- 软件工程文档（需求、设计、测试、部署、用户手册）
- 部署配置（Docker Compose、Kubernetes、Nginx、监控）

**核心算法模块**（图神经网络与多智能体编排的具体实现）与模型权重、演示数据不在公开范围，请勿就该部分提出问题。

## 系统简介

FraudLens 面向公安反诈一线，采用多智能体流水线对案件线索进行研判：案件经要素抽取、聚类分析、团伙识别等环节，输出团伙画像与研判报告。系统强调本地化部署与数据不出域：纯 CPU 环境即可运行，云端大模型可关闭。

### 主要特性

- **多智能体研判流水线**：线索录入到报告生成的全流程自动化，支持人工复核与审批
- **团伙发现**：基于案件资金关系与话术文本的聚类与团伙识别
- **AI 研判助手**：多轮对话、工具调用、记忆系统
- **安全防护**：输入校验、提示注入检测、工具沙箱、脱敏处理、JWT 鉴权
- **工程化能力**：性能指标、检查点、分布式追踪、熔断与幂等

## 技术栈

| 层 | 技术 |
|----|------|
| 前端 | Vue 3、Element Plus、ECharts、Vite |
| 后端 | Python 3.10、FastAPI、LangGraph、PyTorch |
| 存储 | MySQL、Redis |
| 部署 | Docker Compose、Kubernetes、Nginx、Grafana |

## 工程文档

- [需求与规划](docs/软件工程文档/需求与规划)：软件系统需求规格说明书、项目开发计划
- [设计与技术](docs/软件工程文档/设计与技术)：概要设计、详细设计、数据库设计、接口设计说明书
- [测试](docs/软件工程文档/测试)：测试计划、测试报告
- [交付与用户](docs/软件工程文档/交付与用户)：部署手册、用户手册

## 本地部署

后端与中间件使用 Docker Compose：

```bash
cp .env.docker .env   # 按需填写环境变量（留空即走本地规则，不触达公网）
docker compose up -d
```

前端开发模式：

```bash
cd frontend
npm install
npm run dev
```

## 目录结构

```
frontend/          前端（Vue 3）
backend/           后端服务（FastAPI）
  ├── core/        运行时组件（配置、安全、可观测性、工具沙箱等）
  ├── database/    数据访问层与数据库设计
  ├── routes/      REST API 路由
  ├── rag/         知识库检索
  ├── memory/      记忆系统
  ├── schemas/     数据契约
  └── tools/       工具链（取证、OCR、脱敏、文档生成等）
docker/  k8s/  nginx/  monitoring/  部署与运维配置
docs/              软件工程文档
diagrams/          架构图（draw.io）
```
