## 系统架构设计文档


```
# AI反诈研判官系统 v2.0 架构设计文档

## 1. 架构概述：为何采用Agent架构

### 1.1 现状与挑战
当前系统（`核心代码.txt`）虽已模块化，但存在隐性的“过程式”耦合。`AntiFraudChiefAgent.run` 方法实质上是一个**巨型工作流编排器**（Monolithic Workflow Orchestrator），其通过顺序调用工具函数完成特定任务。这种架构在逻辑变化时（如新增预警环节、变更分案策略）需修改主控流程，维护成本较高，且难以灵活应对复杂研判场景（如多轮交互核查）。

### 1.2 重构目标：从“工作流”向“认知协同”演进
本次重构旨在构建一个**多智能体协同系统（Multi-Agent Collaboration System）**。架构升级带来以下核心优势：
- **单一职责（Single Responsibility）**：将“分案”、“画像”、“串并”等认知能力封装为独立Agent，各司其职。
- **韧性增强（Resilience）**：单个Agent故障（如LLM超时）不影响其他Agent的状态，支持降级与重试。
- **可扩展性（Scalability）**：新增“跨境洗钱追踪Agent”仅需注册并订阅事件，无需修改现有Agent代码。
- **人机协同（Human-in-the-Loop）**：Agent可主动暂停请求人工介入（如关键证据确认），符合申报书中“增强智能”的愿景。

## 2. 核心Agent清单

基于现有代码（`IntelligentGangDiscoverer`, `process_single_case`）及申报书规划，定义以下核心Agent：

| Agent名称 | 代号 | 单一职责 | 对应原代码模块 |
| :--- | :--- | :--- | :--- |
| **数据预处理智能体** | `PreprocessAgent` | 清洗多源异构数据，脱敏PII，提取平台关键线索。 | `DataPreprocessor` |
| **分案策略智能体** | `TriageAgent` | 识别对话边界，将混杂数据流切割为独立案件单元。 | `ai_triage_cases` |
| **案件分析智能体** | `AnalystAgent` | 深度分析单案件，提取诈骗类型、风险等级、证据链。 | `process_single_case` |
| **画像生成智能体** | `ProfilerAgent` | 聚合个案分析结果，生成团伙全息画像（雷达图、特征指纹）。 | 需重构自 `_generate_gang_profile_via_llm` |
| **团伙发现智能体** | `ClusterAgent` | 基于语义向量执行无监督聚类，发现隐性犯罪团伙。 | `IntelligentGangDiscoverer` (核心算法保留) |
| **研判协同智能体** | `ChiefAgent` | **系统的中枢**。负责任务分发、冲突仲裁、全局状态管理与用户意图解析。 | `AntiFraudChiefAgent` (逻辑精简) |

## 3. 协作流程图 (Mermaid)

```mermaid
graph TD
    User[民警/前端] -->|上传数据| Chief[研判协同Agent (ChiefAgent)]
    
    subgraph “感知与执行层 (Agent Swarm)”
        Preprocess[预处理Agent]
        Triage[分案Agent]
        Analyst[分析Agent]
        Profiler[画像Agent]
        Cluster[团伙发现Agent]
    end

    Chief -- 1. 任务委派 --> Preprocess
    Preprocess -- 标准化消息流 --> Chief
    
    Chief -- 2. 边界识别请求 --> Triage
    Triage -- 案件切分列表 --> Chief
    
    Chief -- 3. 并发分析指令 --> Analyst
    Analyst -- 个案研判报告 --> Chief
    
    Chief -- 4. 聚合与聚类指令 --> Cluster
    Cluster -- 语义向量与团伙簇 --> Chief
    
    Chief -- 5. 画像生成指令 --> Profiler
    Profiler -- 团伙全息画像 --> Chief
    
    Chief -- 6. 最终响应组装 --> User
```

## 关键数据结构 (Agent间消息规范)

为确保Agent解耦，定义统一的**事件信封（Event Envelope）**格式：

```json
{
  "event_id": "uuid-1234-5678",
  "event_type": "CASE_ANALYSIS_COMPLETED",
  "timestamp": "2024-05-20T10:30:00Z",
  "source_agent": "AnalystAgent",
  "target_agent": "ChiefAgent",
  "correlation_id": "session-xxxx",
  "payload": {
    "case_id": "CASE_001",
    "risk_level": "HIGH",
    "structured_data": { ... }
  },
  "metadata": {
    "trace_id": "trace-xxxx",
    "priority": "high"
  }
}
```

**核心事件类型枚举**:

- `DATA_PREPROCESSED`: 数据清洗完成。
- `CASES_SPLITTED`: 分案边界确认。
- `SINGLE_CASE_ANALYZED`: 单案件分析完成（用于并行汇聚）。
- `CLUSTER_COMPLETED`: 团伙聚类计算完成。
- `PROFILE_GENERATED`: 画像生成完毕。
- `HUMAN_INTERVENTION_REQUIRED`: 请求人工介入（新增预留）。

```
***

### 文档二：Agent编程规范文档

**文件名**: `agent.md`

```markdown
# Agent 编程规范 v1.0

本规范适用于 `AI反诈研判官` 系统内的所有智能体开发。

## 1. Agent 编程模型 (Agent Programming Model)

每个Agent必须遵循**BaseAgent**抽象基类定义的生命周期。

### 1.1 标准接口 (Python 伪代码定义)

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pydantic import BaseModel

class AgentConfig(BaseModel):
    agent_id: str
    max_retries: int = 3
    timeout: int = 30

class AgentContext(BaseModel):
    session_id: str
    trace_id: str
    user_id: Optional[str] = None

class BaseAgent(ABC):
    def __init__(self, config: AgentConfig):
        self.config = config
        self.state = {} # 轻量级状态存储

    @abstractmethod
    async def process(self, payload: Dict[str, Any], context: AgentContext) -> Dict[str, Any]:
        """
        核心处理逻辑（必须实现）。
        - 输入：业务数据 payload，上下文 context。
        - 输出：处理后的业务数据字典。
        - 异常：抛出标准 AgentException 子类。
        """
        pass

    async def on_error(self, error: Exception, context: AgentContext) -> None:
        """错误回调（可选实现），用于上报监控或清理资源"""
        pass
```

## 可观测性规范 (Observability)

### 日志 (Logging) - **结构化 JSON 必须字段**

```json
{
  "level": "INFO",
  "agent_id": "AnalystAgent",
  "trace_id": "abc-123",
  "correlation_id": "session-xyz",
  "event": "LLM_REQUEST_START",
  "latency_ms": 0,
  "message": "Invoking Qwen-Max for case analysis",
  "timestamp": "..."
}
```

### 指标 (Metrics)

每个Agent必须暴露 Prometheus 格式指标：

- `agent_task_total`: Counter (按 status: success/failure 分类)
- `agent_task_duration_seconds`: Histogram

## 错误与重试规范

### 错误分类

| 错误类型           | 错误码前缀   | 处理策略               | 重试策略                              |
| :----------------- | :----------- | :--------------------- | :------------------------------------ |
| **客户端错误**     | `CLIENT_4XX` | 记录日志，直接返回失败 | **禁止重试** (如：输入数据格式错误)   |
| **临时性服务错误** | `SERVER_5XX` | 记录告警，返回失败     | **指数退避重试** (如：LLM Rate Limit) |
| **超时错误**       | `TIMEOUT`    | 记录告警，降级处理     | **有限重试 1 次**                     |
| **逻辑错误**       | `LOGIC_ERR`  | 终止当前链路           | **禁止重试** (如：聚类样本不足)       |
