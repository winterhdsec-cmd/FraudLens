from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pydantic import BaseModel
import json
import time
import uuid


class AgentConfig(BaseModel):
    agent_id: str
    max_retries: int = 3
    timeout: int = 30


class AgentContext(BaseModel):
    session_id: str
    trace_id: str
    user_id: Optional[str] = None


class AgentException(Exception):
    """Agent基础异常类"""
    pass


class ClientError(AgentException):
    """客户端错误"""
    pass


class ServerError(AgentException):
    """服务端错误"""
    pass


class TimeoutError(AgentException):
    """超时错误"""
    pass


class LogicError(AgentException):
    """逻辑错误"""
    pass


class BaseAgent(ABC):
    def __init__(self, config: AgentConfig):
        self.config = config
        self.state = {}  # 轻量级状态存储

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
        self._log("ERROR", f"Agent error: {str(error)}", context)

    def _log(self, level: str, message: str, context: AgentContext) -> None:
        """结构化日志记录"""
        log_entry = {
            "level": level,
            "agent_id": self.config.agent_id,
            "trace_id": context.trace_id,
            "correlation_id": context.session_id,
            "event": f"{self.config.agent_id}_PROCESS",
            "latency_ms": 0,
            "message": message,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        }
        print(json.dumps(log_entry))

    def _generate_event(self, event_type: str, payload: Dict[str, Any], context: AgentContext) -> Dict[str, Any]:
        """生成事件信封"""
        return {
            "event_id": str(uuid.uuid4()),
            "event_type": event_type,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "source_agent": self.config.agent_id,
            "target_agent": "ChiefAgent",
            "correlation_id": context.session_id,
            "payload": payload,
            "metadata": {
                "trace_id": context.trace_id,
                "priority": "high"
            }
        }
