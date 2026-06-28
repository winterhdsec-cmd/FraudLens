"""
Agent评估指标系统 - 量化Agent性能
参考：Agent评测最佳实践
"""
import time
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, field
from core.logger import logger


@dataclass
class AgentMetrics:
    """Agent性能指标"""
    
    # 任务完成指标
    task_success_count: int = 0
    task_failure_count: int = 0
    task_total_count: int = 0
    
    # 工具调用指标
    tool_call_count: int = 0
    tool_success_count: int = 0
    tool_failure_count: int = 0
    tool_avg_latency: float = 0.0
    
    # LLM调用指标
    llm_call_count: int = 0
    llm_total_tokens: int = 0
    llm_avg_latency: float = 0.0
    
    # 时间指标
    total_execution_time: float = 0.0
    avg_response_time: float = 0.0
    
    # 质量指标
    avg_confidence: float = 0.0
    user_satisfaction: float = 0.0
    
    # 错误指标
    error_count: int = 0
    error_types: Dict[str, int] = field(default_factory=dict)
    
    # ReAct循环指标
    thought_count: int = 0
    action_count: int = 0
    observation_count: int = 0
    reflection_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "task_success_rate": self.task_success_rate,
            "tool_success_rate": self.tool_success_rate,
            "avg_response_time": self.avg_response_time,
            "total_execution_time": self.total_execution_time,
            "llm_total_tokens": self.llm_total_tokens,
            "error_count": self.error_count,
            "avg_confidence": self.avg_confidence
        }
    
    @property
    def task_success_rate(self) -> float:
        """任务成功率"""
        if self.task_total_count == 0:
            return 0.0
        return self.task_success_count / self.task_total_count
    
    @property
    def tool_success_rate(self) -> float:
        """工具调用成功率"""
        if self.tool_call_count == 0:
            return 0.0
        return self.tool_success_count / self.tool_call_count


class MetricsCollector:
    """
    指标收集器
    
    收集和统计Agent运行指标
    """
    
    def __init__(self, agent_id: str):
        """
        初始化指标收集器
        
        Args:
            agent_id: Agent ID
        """
        self.agent_id = agent_id
        self.metrics = AgentMetrics()
        self.start_time = datetime.utcnow()
        
        # 历史记录
        self.task_history: List[Dict[str, Any]] = []
        self.tool_history: List[Dict[str, Any]] = []
        
        logger.info("MetricsCollector initialized", agent_id=agent_id)
    
    def record_task(self, task_id: str, success: bool, duration: float, metadata: Optional[Dict[str, Any]] = None):
        """
        记录任务执行
        
        Args:
            task_id: 任务ID
            success: 是否成功
            duration: 执行时间
            metadata: 额外元数据
        """
        self.metrics.task_total_count += 1
        if success:
            self.metrics.task_success_count += 1
        else:
            self.metrics.task_failure_count += 1
        
        self.metrics.total_execution_time += duration
        
        # 更新平均响应时间
        if self.metrics.task_total_count > 0:
            self.metrics.avg_response_time = (
                self.metrics.total_execution_time / self.metrics.task_total_count
            )
        
        # 记录历史
        self.task_history.append({
            "task_id": task_id,
            "success": success,
            "duration": duration,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {}
        })
        
        logger.info(
            "Task recorded",
            agent_id=self.agent_id,
            task_id=task_id,
            success=success,
            duration=duration
        )
    
    def record_tool_call(
        self,
        tool_name: str,
        success: bool,
        latency: float,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        记录工具调用
        
        Args:
            tool_name: 工具名称
            success: 是否成功
            latency: 延迟时间
            metadata: 额外元数据
        """
        self.metrics.tool_call_count += 1
        if success:
            self.metrics.tool_success_count += 1
        else:
            self.metrics.tool_failure_count += 1
        
        # 更新平均延迟
        total_latency = self.metrics.tool_avg_latency * (self.metrics.tool_call_count - 1)
        self.metrics.tool_avg_latency = (total_latency + latency) / self.metrics.tool_call_count
        
        # 记录历史
        self.tool_history.append({
            "tool_name": tool_name,
            "success": success,
            "latency": latency,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {}
        })
    
    def record_llm_call(self, tokens: int, latency: float):
        """
        记录LLM调用
        
        Args:
            tokens: token数量
            latency: 延迟时间
        """
        self.metrics.llm_call_count += 1
        self.metrics.llm_total_tokens += tokens
        
        # 更新平均延迟
        total_latency = self.metrics.llm_avg_latency * (self.metrics.llm_call_count - 1)
        self.metrics.llm_avg_latency = (total_latency + latency) / self.metrics.llm_call_count
    
    def record_error(self, error_type: str, error_message: str):
        """
        记录错误
        
        Args:
            error_type: 错误类型
            error_message: 错误消息
        """
        self.metrics.error_count += 1
        self.metrics.error_types[error_type] = self.metrics.error_types.get(error_type, 0) + 1
        
        logger.error(
            "Error recorded",
            agent_id=self.agent_id,
            error_type=error_type,
            error_message=error_message
        )
    
    def record_react_step(self, step_type: str):
        """
        记录ReAct循环步骤
        
        Args:
            step_type: 步骤类型（thought/action/observation/reflection）
        """
        if step_type == "thought":
            self.metrics.thought_count += 1
        elif step_type == "action":
            self.metrics.action_count += 1
        elif step_type == "observation":
            self.metrics.observation_count += 1
        elif step_type == "reflection":
            self.metrics.reflection_count += 1
    
    def update_confidence(self, confidence: float):
        """
        更新平均置信度
        
        Args:
            confidence: 置信度值
        """
        total_count = self.metrics.task_total_count
        if total_count == 0:
            self.metrics.avg_confidence = confidence
        else:
            old_total = self.metrics.avg_confidence * (total_count - 1)
            self.metrics.avg_confidence = (old_total + confidence) / total_count
    
    def get_summary(self) -> Dict[str, Any]:
        """
        获取指标摘要
        
        Returns:
            指标摘要字典
        """
        uptime = (datetime.utcnow() - self.start_time).total_seconds()
        
        return {
            "agent_id": self.agent_id,
            "uptime_seconds": uptime,
            "metrics": self.metrics.to_dict(),
            "recent_tasks": self.task_history[-10:],  # 最近10个任务
            "recent_tools": self.tool_history[-10:]   # 最近10个工具调用
        }
    
    def reset(self):
        """重置指标"""
        self.metrics = AgentMetrics()
        self.task_history.clear()
        self.tool_history.clear()
        self.start_time = datetime.utcnow()
        
        logger.info("Metrics reset", agent_id=self.agent_id)


class PerformanceEvaluator:
    """
    性能评估器
    
    基于指标评估Agent性能
    """
    
    @staticmethod
    def evaluate(metrics: AgentMetrics) -> Dict[str, Any]:
        """
        评估Agent性能
        
        Args:
            metrics: Agent指标
        
        Returns:
            评估结果
        """
        scores = {}
        
        # 任务成功率评分（0-100）
        scores["task_success_score"] = metrics.task_success_rate * 100
        
        # 工具成功率评分（0-100）
        scores["tool_success_score"] = metrics.tool_success_rate * 100
        
        # 响应时间评分（基于平均响应时间）
        # 假设理想响应时间为2秒，超过10秒得分为0
        if metrics.avg_response_time <= 2:
            scores["response_time_score"] = 100
        elif metrics.avg_response_time >= 10:
            scores["response_time_score"] = 0
        else:
            scores["response_time_score"] = 100 - (metrics.avg_response_time - 2) * 12.5
        
        # 错误率评分（0-100）
        if metrics.task_total_count > 0:
            error_rate = metrics.error_count / metrics.task_total_count
            scores["error_rate_score"] = (1 - error_rate) * 100
        else:
            scores["error_rate_score"] = 100
        
        # 综合评分
        scores["overall_score"] = (
            scores["task_success_score"] * 0.4 +
            scores["tool_success_score"] * 0.3 +
            scores["response_time_score"] * 0.2 +
            scores["error_rate_score"] * 0.1
        )
        
        # 评级
        overall = scores["overall_score"]
        if overall >= 90:
            grade = "A"
        elif overall >= 80:
            grade = "B"
        elif overall >= 70:
            grade = "C"
        elif overall >= 60:
            grade = "D"
        else:
            grade = "F"
        
        scores["grade"] = grade
        
        logger.info(
            "Performance evaluation completed",
            overall_score=overall,
            grade=grade
        )
        
        return scores


# 全局指标收集器注册表
_metrics_collectors: Dict[str, MetricsCollector] = {}


def get_metrics_collector(agent_id: str) -> MetricsCollector:
    """获取或创建指标收集器"""
    if agent_id not in _metrics_collectors:
        _metrics_collectors[agent_id] = MetricsCollector(agent_id)
    return _metrics_collectors[agent_id]


def list_all_metrics() -> Dict[str, Dict[str, Any]]:
    """列出所有Agent的指标"""
    return {
        agent_id: collector.get_summary()
        for agent_id, collector in _metrics_collectors.items()
    }
