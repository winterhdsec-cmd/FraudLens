"""
Agent Planning 模块 - 任务分解与执行路径优化
支持复杂任务的自动分解、优先级排序、依赖分析和执行路径优化
"""
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import json

from core.logger import logger


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class TaskPriority(Enum):
    """任务优先级"""
    CRITICAL = 0
    HIGH = 1
    MEDIUM = 2
    LOW = 3


@dataclass
class SubTask:
    """子任务"""
    task_id: str
    description: str
    tool_name: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    priority: TaskPriority = TaskPriority.MEDIUM
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None
    estimated_steps: int = 1
    actual_steps: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "description": self.description,
            "tool_name": self.tool_name,
            "dependencies": self.dependencies,
            "priority": self.priority.name,
            "status": self.status.name,
            "result": str(self.result)[:200] if self.result else None,
            "error": self.error,
            "estimated_steps": self.estimated_steps,
            "actual_steps": self.actual_steps
        }


@dataclass
class Plan:
    """执行计划"""
    plan_id: str
    goal: str
    subtasks: List[SubTask] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    total_steps: int = 0
    completed_steps: int = 0
    status: TaskStatus = TaskStatus.PENDING
    reflection_notes: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "goal": self.goal,
            "subtasks": [t.to_dict() for t in self.subtasks],
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "total_steps": self.total_steps,
            "completed_steps": self.completed_steps,
            "status": self.status.name,
            "progress": self.completed_steps / max(self.total_steps, 1),
            "reflection_notes": self.reflection_notes
        }


class TaskDecomposer:
    """
    任务分解器
    
    将复杂任务分解为可执行的子任务序列
    支持规则分解和 LLM 分解两种模式
    """
    
    # 预定义的任务分解规则
    DECOMPOSITION_RULES = {
        "案件分析": {
            "keywords": ["分析", "案件", "分析案件", "详细分析"],
            "subtasks": [
                {"desc": "获取案件基本信息", "tool": "get_case_detail", "priority": TaskPriority.HIGH},
                {"desc": "搜索相似案件", "tool": "search_similar_cases", "priority": TaskPriority.MEDIUM},
                {"desc": "获取案件统计数据", "tool": "get_statistics", "priority": TaskPriority.LOW},
                {"desc": "综合分析并生成报告", "tool": None, "priority": TaskPriority.HIGH}
            ]
        },
        "诈骗模式识别": {
            "keywords": ["诈骗模式", "识别", "特征", "模式识别"],
            "subtasks": [
                {"desc": "搜索知识库获取诈骗特征", "tool": "search_knowledge", "priority": TaskPriority.HIGH},
                {"desc": "查询相关案件", "tool": "query_cases", "priority": TaskPriority.MEDIUM},
                {"desc": "分析诈骗模式并总结", "tool": None, "priority": TaskPriority.HIGH}
            ]
        },
        "团伙分析": {
            "keywords": ["团伙", "犯罪网络", "组织"],
            "subtasks": [
                {"desc": "查询团伙相关信息", "tool": "query_cases", "priority": TaskPriority.HIGH},
                {"desc": "分析团伙成员关系", "tool": None, "priority": TaskPriority.HIGH},
                {"desc": "评估团伙风险等级", "tool": "get_statistics", "priority": TaskPriority.MEDIUM},
                {"desc": "生成团伙分析报告", "tool": None, "priority": TaskPriority.HIGH}
            ]
        },
        "统计报告": {
            "keywords": ["统计", "报告", "汇总", "总结"],
            "subtasks": [
                {"desc": "获取统计数据", "tool": "get_statistics", "priority": TaskPriority.HIGH},
                {"desc": "查询案件列表", "tool": "query_cases", "priority": TaskPriority.MEDIUM},
                {"desc": "生成统计报告", "tool": None, "priority": TaskPriority.HIGH}
            ]
        }
    }
    
    def __init__(self, llm_client=None):
        self.llm_client = llm_client
        logger.info("TaskDecomposer initialized", has_llm=llm_client is not None)
    
    async def decompose(self, goal: str, context: Optional[Dict] = None) -> List[SubTask]:
        """
        分解任务
        
        Args:
            goal: 任务目标
            context: 额外上下文
        
        Returns:
            子任务列表
        """
        # 1. 尝试规则匹配
        rule_result = self._match_rule(goal)
        if rule_result:
            logger.info("Task decomposed by rule", goal=goal[:50], subtasks=len(rule_result))
            return rule_result
        
        # 2. 尝试 LLM 分解
        if self.llm_client:
            try:
                llm_result = await self._decompose_with_llm(goal, context)
                if llm_result:
                    logger.info("Task decomposed by LLM", goal=goal[:50], subtasks=len(llm_result))
                    return llm_result
            except Exception as e:
                logger.warning("LLM decomposition failed, falling back to simple", error=str(e))
        
        # 3. 降级为简单任务
        return self._create_simple_task(goal)
    
    def _match_rule(self, goal: str) -> Optional[List[SubTask]]:
        """规则匹配分解"""
        for rule_name, rule_config in self.DECOMPOSITION_RULES.items():
            if any(kw in goal for kw in rule_config["keywords"]):
                subtasks = []
                for i, st in enumerate(rule_config["subtasks"]):
                    task = SubTask(
                        task_id=f"sub_{rule_name}_{i}",
                        description=st["desc"],
                        tool_name=st["tool"],
                        priority=st["priority"],
                        dependencies=[f"sub_{rule_name}_{i-1}"] if i > 0 and st["tool"] else []
                    )
                    subtasks.append(task)
                return subtasks
        return None
    
    async def _decompose_with_llm(self, goal: str, context: Optional[Dict] = None) -> Optional[List[SubTask]]:
        """使用 LLM 进行任务分解"""
        available_tools = [
            "query_cases", "search_similar_cases", "get_case_detail",
            "get_statistics", "search_knowledge", "retrieve_context"
        ]
        
        prompt = f"""你是一个任务规划专家。请将以下任务分解为可执行的子任务。

任务目标: {goal}

可用工具: {', '.join(available_tools)}

请以JSON格式输出子任务列表，每个子任务包含:
- description: 子任务描述
- tool_name: 需要调用的工具（可选）
- priority: 优先级 (high/medium/low)
- dependencies: 依赖的子任务索引

只输出JSON，不要其他内容。
"""
        
        try:
            from core.llm_client import wrap_messages
            response = await self.llm_client.chat.completions.create(
                model="deepseek-chat",
                messages=wrap_messages([{"role": "user", "content": prompt}]),
                temperature=0.3,
                max_tokens=1000
            )
            
            content = response.choices[0].message.content.strip()
            # 提取 JSON
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            tasks_data = json.loads(content)
            
            subtasks = []
            for i, task_data in enumerate(tasks_data if isinstance(tasks_data, list) else tasks_data.get("subtasks", [])):
                priority_map = {"high": TaskPriority.HIGH, "medium": TaskPriority.MEDIUM, "low": TaskPriority.LOW}
                task = SubTask(
                    task_id=f"sub_llm_{i}",
                    description=task_data.get("description", ""),
                    tool_name=task_data.get("tool_name"),
                    priority=priority_map.get(task_data.get("priority", "medium"), TaskPriority.MEDIUM),
                    dependencies=[f"sub_llm_{d}" for d in task_data.get("dependencies", [])]
                )
                subtasks.append(task)
            
            return subtasks if subtasks else None
            
        except Exception as e:
            logger.error("LLM decomposition parse failed", error=str(e))
            return None
    
    def _create_simple_task(self, goal: str) -> List[SubTask]:
        """创建简单任务（不分解）"""
        return [SubTask(
            task_id="sub_simple_0",
            description=goal,
            tool_name=None,
            priority=TaskPriority.MEDIUM
        )]


class ExecutionOptimizer:
    """
    执行路径优化器
    
    分析子任务依赖关系，优化执行顺序
    支持并行执行无依赖任务
    """
    
    def optimize(self, subtasks: List[SubTask]) -> List[List[SubTask]]:
        """
        优化执行顺序，返回分层执行计划
        
        Returns:
            分层任务列表，每层可并行执行
        """
        if not subtasks:
            return []
        
        # 构建依赖图
        task_map = {t.task_id: t for t in subtasks}
        in_degree = {t.task_id: 0 for t in subtasks}
        
        for task in subtasks:
            for dep in task.dependencies:
                if dep in task_map:
                    in_degree[task.task_id] += 1
        
        # 拓扑排序分层
        layers = []
        remaining = set(task_map.keys())
        
        while remaining:
            # 找到所有入度为0的任务
            current_layer = [
                tid for tid in remaining 
                if in_degree.get(tid, 0) == 0
            ]
            
            if not current_layer:
                # 存在循环依赖，强制打破
                current_layer = [min(remaining, key=lambda x: task_map[x].priority.value)]
                logger.warning("Circular dependency detected, breaking cycle", task=current_layer[0])
            
            # 按优先级排序
            current_layer.sort(key=lambda x: task_map[x].priority.value)
            layers.append([task_map[tid] for tid in current_layer])
            
            # 更新入度
            for tid in current_layer:
                remaining.remove(tid)
                for task in subtasks:
                    if tid in task.dependencies:
                        in_degree[task.task_id] -= 1
        
        logger.info(
            "Execution plan optimized",
            total_tasks=len(subtasks),
            layers=len(layers),
            parallelizable=sum(1 for l in layers if len(l) > 1)
        )
        
        return layers


class PlanExecutor:
    """
    计划执行器
    
    按照优化后的执行计划逐步执行子任务
    支持进度跟踪和错误恢复
    """
    
    def __init__(self, chat_agent=None):
        self.chat_agent = chat_agent
        self.optimizer = ExecutionOptimizer()
        logger.info("PlanExecutor initialized")
    
    async def execute_plan(self, plan: Plan) -> Plan:
        """
        执行计划
        
        Args:
            plan: 执行计划
        
        Returns:
            更新后的计划
        """
        plan.status = TaskStatus.IN_PROGRESS
        
        # 优化执行顺序
        layers = self.optimizer.optimize(plan.subtasks)
        
        task_map = {t.task_id: t for t in plan.subtasks}
        plan.total_steps = sum(t.estimated_steps for t in plan.subtasks)
        
        for layer_idx, layer in enumerate(layers):
            logger.info(
                "Executing layer",
                layer=layer_idx + 1,
                total_layers=len(layers),
                tasks=len(layer)
            )
            
            # 并行执行当前层的所有任务
            tasks_to_run = []
            for task in layer:
                if task.status == TaskStatus.PENDING:
                    task.status = TaskStatus.IN_PROGRESS
                    tasks_to_run.append(task)
            
            # 执行任务
            for task in tasks_to_run:
                try:
                    await self._execute_subtask(task, plan)
                    task.status = TaskStatus.COMPLETED
                    plan.completed_steps += task.actual_steps
                except Exception as e:
                    task.status = TaskStatus.FAILED
                    task.error = str(e)
                    logger.error("SubTask failed", task_id=task.task_id, error=str(e))
                    
                    # 标记依赖此任务的后续任务为跳过
                    self._skip_dependent_tasks(task.task_id, plan.subtasks)
            
            plan.reflection_notes.append(
                f"Layer {layer_idx + 1}: {sum(1 for t in layer if t.status == TaskStatus.COMPLETED)}/{len(layer)} tasks completed"
            )
        
        # 更新计划状态
        if all(t.status == TaskStatus.COMPLETED for t in plan.subtasks):
            plan.status = TaskStatus.COMPLETED
        elif any(t.status == TaskStatus.COMPLETED for t in plan.subtasks):
            plan.status = TaskStatus.COMPLETED  # 部分完成也算完成
        else:
            plan.status = TaskStatus.FAILED
        
        plan.completed_at = datetime.utcnow()
        
        return plan
    
    async def _execute_subtask(self, task: SubTask, plan: Plan):
        """执行单个子任务"""
        logger.info("Executing subtask", task_id=task.task_id, description=task.description[:50])
        
        if task.tool_name and self.chat_agent:
            # 调用工具
            tool = self.chat_agent.tools.get_tool(task.tool_name)
            if tool:
                result = await self.chat_agent._execute_tool({
                    "tool_name": task.tool_name,
                    "confidence": 1.0,
                    "should_use_tool": True,
                    "tool_params": {}
                })
                task.result = result
                task.actual_steps = 1
            else:
                task.result = {"warning": f"Tool {task.tool_name} not found"}
                task.actual_steps = 0
        else:
            # 非工具任务（总结、分析等）
            task.result = {"status": "completed", "note": task.description}
            task.actual_steps = 1
    
    def _skip_dependent_tasks(self, failed_task_id: str, subtasks: List[SubTask]):
        """跳过依赖失败任务的后续任务"""
        for task in subtasks:
            if failed_task_id in task.dependencies and task.status == TaskStatus.PENDING:
                task.status = TaskStatus.SKIPPED
                task.error = f"Skipped due to dependency failure: {failed_task_id}"


class PlanningModule:
    """
    规划模块 - Agent 的核心决策组件
    
    整合任务分解、执行优化和计划执行
    支持自我反思和动态调整
    """
    
    def __init__(self, llm_client=None, chat_agent=None):
        self.decomposer = TaskDecomposer(llm_client)
        self.executor = PlanExecutor(chat_agent)
        self.plans_history: List[Plan] = []
        logger.info("PlanningModule initialized")
    
    async def create_and_execute_plan(self, goal: str, context: Optional[Dict] = None) -> Plan:
        """
        创建并执行计划
        
        Args:
            goal: 任务目标
            context: 额外上下文
        
        Returns:
            执行完成的计划
        """
        import uuid
        
        # 1. 分解任务
        subtasks = await self.decomposer.decompose(goal, context)
        
        # 2. 创建计划
        plan = Plan(
            plan_id=f"plan_{uuid.uuid4().hex[:8]}",
            goal=goal,
            subtasks=subtasks
        )
        
        logger.info(
            "Plan created",
            plan_id=plan.plan_id,
            goal=goal[:50],
            subtasks=len(subtasks)
        )
        
        # 3. 执行计划
        plan = await self.executor.execute_plan(plan)
        
        # 4. 保存历史
        self.plans_history.append(plan)
        
        # 5. 自我反思
        reflection = self._reflect(plan)
        plan.reflection_notes.append(reflection)
        
        logger.info(
            "Plan completed",
            plan_id=plan.plan_id,
            status=plan.status.name,
            progress=f"{plan.completed_steps}/{plan.total_steps}"
        )
        
        return plan
    
    def _reflect(self, plan: Plan) -> str:
        """自我反思"""
        completed = sum(1 for t in plan.subtasks if t.status == TaskStatus.COMPLETED)
        failed = sum(1 for t in plan.subtasks if t.status == TaskStatus.FAILED)
        total = len(plan.subtasks)
        
        if failed == 0:
            return f"计划执行成功: {completed}/{total} 子任务完成"
        else:
            return f"计划部分完成: {completed}/{total} 成功, {failed} 失败。建议: 检查失败任务的工具配置和参数。"
    
    def get_stats(self) -> Dict[str, Any]:
        """获取规划统计信息"""
        total_plans = len(self.plans_history)
        completed_plans = sum(1 for p in self.plans_history if p.status == TaskStatus.COMPLETED)
        
        return {
            "total_plans": total_plans,
            "completed_plans": completed_plans,
            "success_rate": completed_plans / max(total_plans, 1),
            "recent_plans": [p.to_dict() for p in self.plans_history[-5:]]
        }
