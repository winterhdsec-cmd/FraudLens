"""
Agent 运行时 - 专业级 ReAct 循环实现
基于 LangGraph 和 AutoGen 的最佳实践
"""
import asyncio
import json
import re
from typing import Dict, List, Any, Optional, Callable, Union
from datetime import datetime
import time

from openai import AsyncOpenAI
from .config import settings
from .state import AgentState, AgentStatus, Message, Thought, Action, Observation, Reflection
from .logger import logger, tracer
from .circuit_breaker import get_circuit_breaker, CircuitBreakerOpenError
from .security import get_prompt_injection_detector, get_tool_call_validator
from .checkpoint import get_checkpoint_manager
from .metrics import get_metrics_collector
from .tool_sandbox import get_tool_registry
from tools.base import Tool, ToolRegistry


class AgentRuntime:
    """
    专业级 Agent 运行时
    
    核心特性：
    1. ReAct 循环（Thought → Action → Observation → Reflection）
    2. 重试机制（指数退避）
    3. 超时控制
    4. 结构化日志和追踪
    5. 检查点支持
    6. 工具注册表
    """
    
    def __init__(
        self,
        agent_id: str,
        agent_type: str,
        tools: Optional[ToolRegistry] = None,
        max_iterations: int = None,
        enable_reflection: bool = None,
        timeout: int = None,
        max_retries: int = 3
    ):
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.tools = tools or ToolRegistry()
        self.max_iterations = max_iterations or settings.AGENT_MAX_ITERATIONS
        self.enable_reflection = enable_reflection if enable_reflection is not None else settings.REFLECTION_ENABLED
        self.timeout = timeout or settings.AGENT_TIMEOUT
        self.max_retries = max_retries
        
        # 延迟初始化 LLM 客户端
        self._llm = None
        
        # 状态
        self.state = AgentState(
            agent_id=agent_id,
            agent_type=agent_type,
            max_iterations=self.max_iterations
        )
        
        # 检查点（使用持久化检查点管理器）
        self.checkpoint_manager = get_checkpoint_manager()
        self.checkpoints: List[Dict[str, Any]] = []
        
        # 熔断器（用于 LLM 调用）
        self.llm_circuit_breaker = get_circuit_breaker(
            f"{agent_id}_llm",
            failure_threshold=5,
            recovery_timeout=60
        )
        
        # 指标收集器
        self.metrics_collector = get_metrics_collector(agent_id)
        
        # 安全检查器
        self.prompt_injection_detector = get_prompt_injection_detector()
        self.tool_call_validator = get_tool_call_validator()
        
        # 回调
        self.on_thought: Optional[Callable] = None
        self.on_action: Optional[Callable] = None
        self.on_observation: Optional[Callable] = None
        self.on_reflection: Optional[Callable] = None
    
    @property
    def llm(self) -> Optional[AsyncOpenAI]:
        """延迟初始化LLM客户端（经 G2 统一网关；关闭/缺密钥时返回 None）"""
        if self._llm is None:
            from .llm_client import get_llm_client
            self._llm = get_llm_client()
            # G8：云端 LLM 不可用 → 降级到本地规则兜底，记一次降级事件
            if self._llm is None and not getattr(self, "_degrade_counted", False):
                self._degrade_counted = True
                try:
                    from core.metrics_exporter import inc_degrade
                    inc_degrade()
                except Exception:
                    pass
        return self._llm
    
    def register_tool(self, tool: Tool):
        """注册工具"""
        self.tools.register(tool)
        logger.info(f"Tool registered: {tool.name}", agent_id=self.agent_id)
    
    def _build_system_prompt(self, task: str, context: Dict[str, Any] = None) -> str:
        """构建系统提示"""
        tools_desc = "\n".join([
            f"- {tool.name}: {tool.description}"
            for tool in self.tools.list_tools().values()
        ])
        
        system_prompt = f"""你是一个智能 Agent，负责执行以下任务:
{task}

你可以使用以下工具:
{tools_desc}

请按照 ReAct 模式工作:
1. Thought: 思考当前情况，决定下一步行动
2. Action: 调用工具执行操作（必须使用 JSON 格式）
3. Observation: 观察执行结果
4. Reflection: 反思结果质量

工具调用格式:
```json
{{
    "tool_name": "工具名称",
    "tool_input": {{
        "参数1": "值1",
        "参数2": "值2"
    }}
}}
```

如果任务完成，请输出最终答案。
如果遇到问题，请反思并调整策略。

当前上下文:
{json.dumps(context or {}, ensure_ascii=False, indent=2)}
"""
        return system_prompt
    
    async def think(self, task: str, context: Dict[str, Any] = None) -> Thought:
        """思考阶段 - 决定下一步行动"""
        with tracer.span("agent.think", agent_id=self.agent_id, iteration=self.state.current_iteration):
            self.state.status = AgentStatus.THINKING
            self.metrics_collector.record_react_step("thought")
            
            # 安全检查：检测任务中的注入攻击
            safety_check = self.prompt_injection_detector.detect(task)
            if not safety_check["is_safe"]:
                logger.warning(
                    "Potential prompt injection detected in task",
                    agent_id=self.agent_id,
                    threats_count=len(safety_check["threats"])
                )
                # 清理任务文本
                task = self.prompt_injection_detector.sanitize(task)
            
            system_prompt = self._build_system_prompt(task, context)
            
            # 构建消息历史
            messages = [{"role": "system", "content": system_prompt}]
            for msg in self.state.messages[-10:]:
                messages.append({"role": msg.role, "content": msg.content})
            
            # 调用 LLM（带重试和熔断器）
            start_time = time.time()
            try:
                response = await self.llm_circuit_breaker.async_call(
                    self._call_llm_with_retry,
                    messages
                )
                
                thought_content = response.choices[0].message.content
                llm_latency = time.time() - start_time
                
                # 记录 LLM 调用指标
                tokens = response.usage.total_tokens if hasattr(response, 'usage') else 0
                self.metrics_collector.record_llm_call(tokens, llm_latency)
                
            except CircuitBreakerOpenError as e:
                logger.error(
                    "LLM circuit breaker is open",
                    agent_id=self.agent_id,
                    error=str(e)
                )
                self.metrics_collector.record_error("CircuitBreakerOpen", str(e))
                raise
            
            thought = Thought(
                content=thought_content,
                reasoning="ReAct 思考过程"
            )
            
            self.state.add_thought(thought_content)
            self.state.add_message("assistant", thought_content)
            
            logger.info(
                "Thought generated",
                agent_id=self.agent_id,
                iteration=self.state.current_iteration,
                thought_length=len(thought_content)
            )
            
            if self.on_thought:
                await self.on_thought(thought)
            
            return thought
    
    async def act(self, thought: Thought) -> Action:
        """行动阶段 - 执行工具调用"""
        with tracer.span("agent.act", agent_id=self.agent_id):
            self.state.status = AgentStatus.ACTING
            self.metrics_collector.record_react_step("action")
            
            # 解析工具调用
            tool_call = self._parse_tool_call(thought.content)
            
            if not tool_call:
                logger.info("No tool call detected", agent_id=self.agent_id)
                return Action(
                    tool_name="none",
                    tool_input={},
                    result=thought.content,
                    success=True
                )
            
            tool_name = tool_call.get("tool_name")
            tool_input = tool_call.get("tool_input", {})
            
            # 安全验证：工具调用检查
            tool_safety = self.tool_call_validator.validate_tool_call(tool_name, tool_input)
            if not tool_safety["is_safe"]:
                logger.warning(
                    "Unsafe tool call blocked",
                    agent_id=self.agent_id,
                    tool_name=tool_name,
                    errors=tool_safety["errors"]
                )
                self.metrics_collector.record_error("UnsafeToolCall", str(tool_safety["errors"]))
                return Action(
                    tool_name=tool_name,
                    tool_input=tool_input,
                    success=False,
                    error=f"工具调用被安全策略拦截: {tool_safety['errors']}"
                )
            
            logger.info(
                f"Executing tool: {tool_name}",
                agent_id=self.agent_id,
                tool_input=tool_input
            )
            
            # 执行工具
            tool = self.tools.get(tool_name)
            if not tool:
                logger.error(f"Tool not found: {tool_name}", agent_id=self.agent_id)
                return Action(
                    tool_name=tool_name,
                    tool_input=tool_input,
                    success=False,
                    error=f"工具 {tool_name} 不存在"
                )
            
            tool_start = time.time()
            try:
                # 执行工具（带超时）
                result = await asyncio.wait_for(
                    asyncio.to_thread(tool, **tool_input),
                    timeout=self.timeout
                )
                
                tool_latency = time.time() - tool_start
                self.metrics_collector.record_tool_call(tool_name, True, tool_latency)
                
                action = Action(
                    tool_name=tool_name,
                    tool_input=tool_input,
                    result=result,
                    success=True
                )
                
                logger.info(
                    f"Tool executed successfully: {tool_name}",
                    agent_id=self.agent_id
                )
                
            except asyncio.TimeoutError:
                tool_latency = time.time() - tool_start
                self.metrics_collector.record_tool_call(tool_name, False, tool_latency)
                self.metrics_collector.record_error("ToolTimeout", f"{tool_name} timeout")
                
                logger.error(
                    f"Tool execution timeout: {tool_name}",
                    agent_id=self.agent_id,
                    timeout=self.timeout
                )
                action = Action(
                    tool_name=tool_name,
                    tool_input=tool_input,
                    success=False,
                    error=f"工具执行超时（{self.timeout}秒）"
                )
            except Exception as e:
                tool_latency = time.time() - tool_start
                self.metrics_collector.record_tool_call(tool_name, False, tool_latency)
                self.metrics_collector.record_error(type(e).__name__, str(e))
                
                logger.error(
                    f"Tool execution failed: {tool_name}",
                    agent_id=self.agent_id,
                    error=str(e),
                    error_type=type(e).__name__
                )
                action = Action(
                    tool_name=tool_name,
                    tool_input=tool_input,
                    success=False,
                    error=str(e)
                )
            
            self.state.actions.append(action)
            
            if self.on_action:
                await self.on_action(action)
            
            return action
    
    async def observe(self, action: Action) -> Observation:
        """观察阶段 - 记录执行结果"""
        with tracer.span("agent.observe", agent_id=self.agent_id):
            self.state.status = AgentStatus.OBSERVING
            
            if action.success:
                observation_content = f"工具 {action.tool_name} 执行成功:\n{json.dumps(action.result, ensure_ascii=False, indent=2)}"
            else:
                observation_content = f"工具 {action.tool_name} 执行失败: {action.error}"
            
            observation = Observation(content=observation_content)
            self.state.observations.append(observation)
            self.state.add_message("tool", observation_content)
            
            logger.info(
                f"Observation recorded",
                agent_id=self.agent_id,
                tool=action.tool_name,
                success=action.success
            )
            
            if self.on_observation:
                await self.on_observation(observation)
            
            return observation
    
    async def reflect(self, task: str) -> Reflection:
        """反思阶段 - 评估结果质量"""
        if not self.enable_reflection:
            return Reflection(
                content="反思已禁用",
                quality_score=1.0,
                should_retry=False
            )
        
        with tracer.span("agent.reflect", agent_id=self.agent_id):
            self.state.status = AgentStatus.REFLECTING
            
            context_summary = self.state.get_context_summary()
            reflection_prompt = f"""请反思当前的执行过程:

任务: {task}

执行历史:
{context_summary}

请评估:
1. 任务是否完成？
2. 结果质量如何（0-1分）？
3. 是否需要调整策略？

请输出 JSON 格式:
{{
    "completed": true/false,
    "quality_score": 0.0-1.0,
    "improvements": ["改进建议1", "改进建议2"],
    "should_retry": true/false
}}
"""
            
            response = await self._call_llm_with_retry(
                [{"role": "user", "content": reflection_prompt}],
                temperature=0.3,
                max_tokens=500
            )
            
            reflection_content = response.choices[0].message.content
            
            try:
                reflection_data = json.loads(reflection_content)
                reflection = Reflection(
                    content=reflection_content,
                    quality_score=reflection_data.get("quality_score", 0.5),
                    improvements=reflection_data.get("improvements", []),
                    should_retry=reflection_data.get("should_retry", False)
                )
            except json.JSONDecodeError:
                logger.warning(
                    "Failed to parse reflection JSON",
                    agent_id=self.agent_id,
                    content=reflection_content[:200]
                )
                reflection = Reflection(
                    content=reflection_content,
                    quality_score=0.5,
                    should_retry=False
                )
            
            self.state.reflections.append(reflection)
            
            logger.info(
                "Reflection completed",
                agent_id=self.agent_id,
                quality_score=reflection.quality_score,
                should_retry=reflection.should_retry
            )
            
            if self.on_reflection:
                await self.on_reflection(reflection)
            
            return reflection
    
    def _parse_tool_call(self, content: str) -> Optional[Dict[str, Any]]:
        """解析工具调用 - 支持多种格式"""
        # 尝试解析 markdown 代码块中的 JSON
        code_block_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
        matches = re.findall(code_block_pattern, content, re.DOTALL)
        
        for match in matches:
            try:
                tool_call = json.loads(match)
                if "tool_name" in tool_call:
                    return tool_call
            except json.JSONDecodeError:
                continue
        
        # 尝试直接解析 JSON
        json_pattern = r'\{[^{}]*"tool_name"[^{}]*\}'
        matches = re.findall(json_pattern, content, re.DOTALL)
        
        for match in matches:
            try:
                tool_call = json.loads(match)
                if "tool_name" in tool_call:
                    return tool_call
            except json.JSONDecodeError:
                continue
        
        return None
    
    async def _call_llm_with_retry(
        self,
        messages: List[Dict[str, str]],
        temperature: float = None,
        max_tokens: int = None
    ):
        """调用 LLM（带重试和指数退避）"""
        temperature = temperature or settings.LLM_TEMPERATURE
        max_tokens = max_tokens or settings.LLM_MAX_TOKENS

        if self.llm is None:
            raise RuntimeError(
                "云端 LLM 未启用（DISABLE_CLOUD_LLM=1 或缺少密钥），无法完成该智能调用"
            )

        for attempt in range(self.max_retries):
            try:
                response = await self.llm.chat.completions.create(
                    model=settings.DEEPSEEK_MODEL,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                return response
            except Exception as e:
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt  # 指数退避
                    logger.warning(
                        f"LLM call failed, retrying in {wait_time}s",
                        agent_id=self.agent_id,
                        attempt=attempt + 1,
                        error=str(e)
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(
                        "LLM call failed after all retries",
                        agent_id=self.agent_id,
                        max_retries=self.max_retries,
                        error=str(e)
                    )
                    raise
    
    async def run(self, task: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """运行 ReAct 循环"""
        with tracer.span("agent.run", agent_id=self.agent_id, task=task[:100]):
            start_time = time.time()
            task_id = f"task_{int(start_time * 1000)}"
            self.state.status = AgentStatus.RUNNING
            self.state.input_data = {"task": task, "context": context or {}}
            
            logger.info(
                "Agent run started",
                agent_id=self.agent_id,
                task=task[:100],
                max_iterations=self.max_iterations
            )
            
            try:
                while self.state.current_iteration < self.max_iterations:
                    self.state.current_iteration += 1
                    
                    # 1. 思考
                    thought = await self.think(task, context)
                    
                    # 2. 行动
                    action = await self.act(thought)
                    
                    # 3. 观察
                    observation = await self.observe(action)
                    
                    # 4. 反思
                    reflection = await self.reflect(task)
                    self.metrics_collector.record_react_step("reflection")
                    
                    # 保存检查点（持久化）
                    self._save_checkpoint()
                    
                    # 检查是否完成
                    if reflection.quality_score >= 0.8 and not reflection.should_retry:
                        self.state.status = AgentStatus.COMPLETED
                        duration = time.time() - start_time
                        
                        # 记录任务成功
                        self.metrics_collector.record_task(task_id, True, duration, {
                            "iterations": self.state.current_iteration,
                            "quality_score": reflection.quality_score
                        })
                        self.metrics_collector.update_confidence(reflection.quality_score)
                        
                        self.state.output_data = {
                            "result": action.result if action.success else None,
                            "thought": thought.content,
                            "iterations": self.state.current_iteration,
                            "duration_seconds": duration
                        }
                        
                        logger.info(
                            "Agent run completed successfully",
                            agent_id=self.agent_id,
                            iterations=self.state.current_iteration,
                            duration_seconds=duration
                        )
                        
                        return self.state.output_data
                    
                    # 更新上下文
                    context = {
                        "last_thought": thought.content,
                        "last_action": action.tool_name,
                        "last_observation": observation.content,
                        "reflection": reflection.content
                    }
                
                # 超过最大迭代次数
                self.state.status = AgentStatus.FAILED
                duration = time.time() - start_time
                
                # 记录任务失败
                self.metrics_collector.record_task(task_id, False, duration, {
                    "iterations": self.state.current_iteration,
                    "reason": "max_iterations_exceeded"
                })
                
                self.state.output_data = {
                    "error": "超过最大迭代次数",
                    "iterations": self.state.current_iteration,
                    "duration_seconds": duration
                }
                
                logger.warning(
                    "Agent run exceeded max iterations",
                    agent_id=self.agent_id,
                    max_iterations=self.max_iterations,
                    duration_seconds=duration
                )
                
                return self.state.output_data
                
            except Exception as e:
                self.state.status = AgentStatus.FAILED
                self.state.error_count += 1
                duration = time.time() - start_time
                
                # 记录任务失败和错误
                self.metrics_collector.record_task(task_id, False, duration, {
                    "iterations": self.state.current_iteration,
                    "reason": "exception"
                })
                self.metrics_collector.record_error(type(e).__name__, str(e))
                
                self.state.output_data = {
                    "error": str(e),
                    "iterations": self.state.current_iteration,
                    "duration_seconds": duration
                }
                
                logger.error(
                    "Agent run failed",
                    agent_id=self.agent_id,
                    error=str(e),
                    error_type=type(e).__name__,
                    duration_seconds=duration
                )
                
                raise
    
    def _save_checkpoint(self):
        """保存检查点（持久化到磁盘）"""
        checkpoint = {
            "iteration": self.state.current_iteration,
            "timestamp": datetime.utcnow().isoformat(),
            "status": self.state.status.value,
            "thoughts_count": len(self.state.thoughts),
            "actions_count": len(self.state.actions)
        }
        self.checkpoints.append(checkpoint)
        
        # 持久化到磁盘
        try:
            self.checkpoint_manager.save_checkpoint(
                agent_id=self.agent_id,
                state={
                    "iteration": self.state.current_iteration,
                    "status": self.state.status.value,
                    "messages_count": len(self.state.messages),
                    "thoughts_count": len(self.state.thoughts),
                    "actions_count": len(self.state.actions)
                },
                metadata={"checkpoint": checkpoint}
            )
        except Exception as e:
            logger.warning(
                "Failed to persist checkpoint",
                agent_id=self.agent_id,
                error=str(e)
            )
        
        logger.debug(
            "Checkpoint saved",
            agent_id=self.agent_id,
            iteration=self.state.current_iteration
        )
    
    def get_state(self) -> AgentState:
        """获取当前状态"""
        return self.state
    
    def get_checkpoints(self) -> List[Dict[str, Any]]:
        """获取检查点列表"""
        return self.checkpoints
    
    def reset(self):
        """重置状态"""
        self.state = AgentState(
            agent_id=self.agent_id,
            agent_type=self.agent_type,
            max_iterations=self.max_iterations
        )
        self.checkpoints.clear()
        
        logger.info("Agent reset", agent_id=self.agent_id)
