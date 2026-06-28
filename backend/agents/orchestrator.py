"""
主编排 Agent - 基于 LangGraph 的工作流编排
"""
import json
import time
from typing import Dict, Any, List, Optional
from datetime import datetime

from core.state import WorkflowState, WorkflowStatus, AgentState
from core.metrics import get_metrics_collector
from core.circuit_breaker import get_circuit_breaker
from core.checkpoint import get_checkpoint_manager
from agents.analyst_agent import AnalystAgent
from agents.cluster_agent import ClusterAgent


class OrchestratorAgent:
    """
    主编排智能体
    
    使用 LangGraph 风格的编排来协调多个子 Agent:
    1. 规划阶段: 分析任务，制定执行计划
    2. 预处理阶段: 数据清洗和准备
    3. 分析阶段: 案件分析（可并行）
    4. 聚类阶段: 团伙发现
    5. 反思阶段: 质量评估和改进
    
    支持条件分支、循环和人类介入
    """
    
    def __init__(self, llm_client=None, embedding_model=None):
        self.llm = llm_client
        self.embedding_model = embedding_model
        
        # 初始化子 Agent
        self.analyst = AnalystAgent(llm_client=llm_client)
        self.cluster = ClusterAgent(llm_client=llm_client, embedding_model=embedding_model)
        
        # 工作流状态
        self.state = WorkflowState(workflow_id="orchestrator")
        
        # 检查点管理器
        self.checkpoint_manager = get_checkpoint_manager()
        self.checkpoint_enabled = True
        
        # 指标收集器
        self.metrics = get_metrics_collector("orchestrator")
    
    def process(self, cases: List[Dict[str, Any]], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        处理案件列表
        
        Args:
            cases: 案件列表
            context: 额外上下文
        
        Returns:
            处理结果
        """
        start_time = time.time()
        self.state.status = WorkflowStatus.RUNNING
        self.state.input_data = {"cases": cases, "context": context or {}}
        
        try:
            # 1. 规划阶段
            plan = self._plan(cases, context)
            self.state.record_execution("plan", {"plan": plan})
            
            # 保存检查点
            if self.checkpoint_enabled:
                self.checkpoint_manager.save_checkpoint(
                    agent_id="orchestrator",
                    state={
                        "stage": "plan_completed",
                        "plan": plan,
                        "cases_count": len(cases)
                    }
                )
            
            # 2. 预处理阶段
            preprocessed = self._preprocess(cases)
            self.state.record_execution("preprocess", {"count": len(preprocessed)})
            
            # 保存检查点
            if self.checkpoint_enabled:
                self.checkpoint_manager.save_checkpoint(
                    agent_id="orchestrator",
                    state={
                        "stage": "preprocess_completed",
                        "preprocessed_count": len(preprocessed)
                    }
                )
            
            # 3. 分析阶段（并行处理每个案件）
            analyzed_cases = []
            for case in preprocessed:
                result = self.analyst.analyze(case)
                analyzed_cases.append(result)
            self.state.record_execution("analyze", {"count": len(analyzed_cases)})
            
            # 保存检查点
            if self.checkpoint_enabled:
                self.checkpoint_manager.save_checkpoint(
                    agent_id="orchestrator",
                    state={
                        "stage": "analyze_completed",
                        "analyzed_count": len(analyzed_cases)
                    }
                )
            
            # 4. 聚类阶段
            gang_result = self.cluster.discover_gangs(analyzed_cases)
            self.state.record_execution("cluster", {"total_gangs": gang_result["total_gangs"]})
            
            # 保存检查点
            if self.checkpoint_enabled:
                self.checkpoint_manager.save_checkpoint(
                    agent_id="orchestrator",
                    state={
                        "stage": "cluster_completed",
                        "total_gangs": gang_result["total_gangs"]
                    }
                )
            
            # 5. 反思阶段
            reflection = self._reflect(analyzed_cases, gang_result)
            self.state.record_execution("reflect", reflection)
            
            # 如果质量不佳，重新分析
            if reflection.get("should_retry") and reflection.get("retry_count", 0) < 2:
                # 调整策略后重新分析
                adjusted_cases = self._adjust_strategy(analyzed_cases, reflection)
                for i, case in enumerate(adjusted_cases):
                    analyzed_cases[i] = self.analyst.analyze(case)
                
                # 重新聚类
                gang_result = self.cluster.discover_gangs(analyzed_cases)
            
            # 6. 生成最终结果
            processing_time = time.time() - start_time
            result = {
                "session_id": f"session_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                "cases": analyzed_cases,
                "gangs": gang_result["gangs"],
                "statistics": {
                    "total_cases": len(analyzed_cases),
                    "total_gangs": gang_result["total_gangs"],
                    "quality_score": gang_result.get("quality_score", 0),
                    "processing_time": processing_time
                },
                "reflection": reflection,
                "status": "completed"
            }
            
            self.state.status = WorkflowStatus.COMPLETED
            self.state.output_data = result
            
            # 保存最终检查点
            if self.checkpoint_enabled:
                self.checkpoint_manager.save_checkpoint(
                    agent_id="orchestrator",
                    state={
                        "stage": "completed",
                        "session_id": result["session_id"],
                        "total_cases": len(analyzed_cases),
                        "total_gangs": gang_result["total_gangs"]
                    }
                )
            
            # 记录成功指标
            self.metrics.record_task(
                task_id=result["session_id"],
                success=True,
                duration=processing_time,
                metadata={
                    "total_cases": len(analyzed_cases),
                    "total_gangs": gang_result["total_gangs"],
                    "quality_score": gang_result.get("quality_score", 0)
                }
            )
            
            return result
        
        except Exception as e:
            self.state.status = WorkflowStatus.FAILED
            
            # 记录失败指标
            self.metrics.record_task_failure(
                task_id="orchestrator_failed",
                error_type=type(e).__name__,
                error_message=str(e)
            )
            
            return {
                "session_id": None,
                "cases": [],
                "gangs": [],
                "statistics": {
                    "total_cases": 0,
                    "total_gangs": 0,
                    "quality_score": 0.0,
                    "processing_time": 0
                },
                "reflection": {},
                "error": str(e),
                "status": "failed"
            }
    
    def _plan(self, cases: List[Dict[str, Any]], context: Dict[str, Any]) -> Dict[str, Any]:
        """规划阶段：分析任务，制定执行计划"""
        
        n_cases = len(cases)
        
        # 简单的规则规划
        plan = {
            "strategy": "parallel_analysis",
            "batch_size": min(10, n_cases),
            "enable_clustering": n_cases >= 3,
            "enable_reflection": True
        }
        
        # 如果案件数量很大，使用批处理
        if n_cases > 50:
            plan["strategy"] = "batch_processing"
            plan["batch_size"] = 20
        
        return plan
    
    def _preprocess(self, cases: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """预处理阶段：数据清洗和准备"""
        
        preprocessed = []
        
        for case in cases:
            # 清洗数据
            cleaned_case = {
                "case_id": case.get("case_id", ""),
                "title": case.get("title", ""),
                "description": case.get("description", "").strip(),
                "scam_type": case.get("scam_type", "未知"),
                "amount": float(case.get("amount", 0)),
                "victim_name": case.get("victim_name", "未知"),
                "victim_age": case.get("victim_age"),
                "risk_score": case.get("risk_score", 0),
                "text_messages": case.get("text_messages", [])
            }
            
            # 跳过无效案件
            if not cleaned_case["description"] and not cleaned_case["text_messages"]:
                continue
            
            preprocessed.append(cleaned_case)
        
        return preprocessed
    
    def _reflect(
        self,
        analyzed_cases: List[Dict[str, Any]],
        gang_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """反思阶段：评估结果质量"""
        
        # 计算质量指标
        n_cases = len(analyzed_cases)
        n_gangs = gang_result["total_gangs"]
        quality_score = gang_result.get("quality_score", 0)
        
        # 检查是否有足够的团伙
        has_enough_gangs = n_gangs >= 1
        
        # 检查案件分析质量
        avg_risk_score = sum(c.get("risk_score", 0) for c in analyzed_cases) / n_cases if n_cases > 0 else 0
        has_good_analysis = avg_risk_score > 50
        
        # 综合评估
        overall_quality = (quality_score + (1 if has_enough_gangs else 0) + (1 if has_good_analysis else 0)) / 3
        
        reflection = {
            "quality_score": overall_quality,
            "has_enough_gangs": has_enough_gangs,
            "has_good_analysis": has_good_analysis,
            "should_retry": overall_quality < 0.6,
            "retry_count": 0,
            "improvements": []
        }
        
        # 生成改进建议
        if not has_enough_gangs:
            reflection["improvements"].append("团伙数量不足，建议调整聚类参数")
        
        if not has_good_analysis:
            reflection["improvements"].append("案件分析质量不佳，建议使用 LLM 深度分析")
        
        return reflection
    
    def _adjust_strategy(
        self,
        analyzed_cases: List[Dict[str, Any]],
        reflection: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """根据反思结果调整策略"""
        
        # 这里可以添加更复杂的策略调整逻辑
        # 例如：增加 LLM 分析的深度，调整聚类参数等
        
        return analyzed_cases
    
    def get_state(self) -> WorkflowState:
        """获取当前工作流状态"""
        return self.state
    
    def reset(self):
        """重置工作流状态"""
        self.state = WorkflowState(workflow_id="orchestrator")
