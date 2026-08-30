"""
AI对话助手 - 支持多轮对话、工具调用、RAG检索
基于 LangGraph 和 mem0 的最佳实践
"""
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
import asyncio

from openai import AsyncOpenAI
from core.llm_client import wrap_messages, get_llm_model  # G2 脱敏网关 / 统一模型名出口
from core.state import AgentState, AgentStatus
from core.logger import logger, tracer
from core.config import settings
from core.security import get_prompt_injection_detector, get_input_validator
from core.circuit_breaker import get_circuit_breaker, CircuitBreakerOpenError
from core.metrics import get_metrics_collector
from core.checkpoint import get_checkpoint_manager
from core.planning import PlanningModule
from tools.base import ToolRegistry
from tools.database_tools import (
    QueryCasesTool, SearchSimilarCasesTool, GetCaseDetailTool, GetGangsTool,
)
from tools.statistics_tools import GetStatisticsTool
from tools.rag_tools import SearchKnowledgeTool, RetrieveAndCompressContextTool
from memory.short_term import ShortTermMemory
from memory.long_term import LongTermMemory
from memory.vector_memory import VectorMemory


class ChatAgent:
    """
    AI对话智能体
    
    核心特性：
    1. 多轮对话支持（短期记忆）
    2. 工具调用（查询案件、统计数据等）
    3. RAG检索（相似案件搜索）
    4. 上下文压缩（长期记忆）
    5. 意图识别（自动选择工具）
    """
    
    def __init__(self, llm_client=None, embedding_model=None):
        self._llm = llm_client
        self.embedding_model = embedding_model
        
        # 初始化工具
        self.tools = ToolRegistry()
        self.tools.register(QueryCasesTool())
        self.tools.register(SearchSimilarCasesTool())
        self.tools.register(GetCaseDetailTool())
        self.tools.register(GetGangsTool())
        self.tools.register(GetStatisticsTool())
        self.tools.register(SearchKnowledgeTool())
        self.tools.register(RetrieveAndCompressContextTool())
        
        # 记忆系统
        self.short_term_memory = ShortTermMemory(max_messages=20)
        self.long_term_memory = LongTermMemory()
        self.vector_memory = VectorMemory(embedding_model=embedding_model)
        
        # 会话状态
        self.session_id = None
        # 当前登录用户（由路由层注入，供工具做部门级数据隔离；工具不信任 LLM 传入的身份）
        self.user: Optional[Dict[str, Any]] = None
        self.state = AgentState(
            agent_id="chat_agent",
            agent_type="chat",
            max_iterations=5
        )
        
        # 安全组件
        self.prompt_injection_detector = get_prompt_injection_detector()
        self.input_validator = get_input_validator()
        
        # 熔断器（用于 LLM 调用）
        self.llm_circuit_breaker = get_circuit_breaker(
            "chat_agent_llm",
            failure_threshold=5,
            recovery_timeout=60
        )
        
        # 指标收集
        self.metrics_collector = get_metrics_collector("chat_agent")
        
        # 检查点管理（用于状态持久化）
        self.checkpoint_manager = get_checkpoint_manager()
        
        # 规划模块（用于复杂任务分解和执行）
        self.planning_module = PlanningModule(llm_client=self.llm, chat_agent=self)
        
        logger.info("ChatAgent initialized", tools=list(self.tools.list_tools().keys()))
    
    @property
    def llm(self) -> Optional[AsyncOpenAI]:
        """延迟初始化LLM客户端（经 G2 统一网关：默认关闭、启用脱敏）"""
        if self._llm is None:
            from core.llm_client import get_llm_client
            client = get_llm_client()
            if client is None:
                logger.warning(
                    "云端 LLM 已关闭或未配置（DISABLE_CLOUD_LLM=1 或缺少密钥），"
                    "ChatAgent 智能回复将降级为本地规则"
                )
            self._llm = client
        return self._llm
    
    def start_session(self, session_id: str = None):
        """开始新会话"""
        import uuid
        self.session_id = session_id or f"chat_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        self.short_term_memory.clear()
        self.state = AgentState(
            agent_id="chat_agent",
            agent_type="chat",
            max_iterations=5
        )
        
        logger.info("Chat session started", session_id=self.session_id)
        
        # 保存初始检查点
        self._save_checkpoint("session_started")
        
        return self.session_id
    
    async def chat_stream(self, user_message: str, context: Dict[str, Any] = None):
        """
        流式处理用户消息（生成器）
        
        Args:
            user_message: 用户输入
            context: 额外上下文
        
        Yields:
            流式响应片段
        """
        with tracer.span("chat_agent.chat_stream", session_id=self.session_id, user_msg=user_message[:100]):
            if not self.session_id:
                self.start_session()
            
            start_time = datetime.utcnow()
            
            # 安全检查
            validation_result = self.input_validator.validate_text_input(user_message, max_length=5000)
            if not validation_result["is_valid"]:
                yield {"type": "error", "content": "您的输入包含不合法内容，请检查后重试。"}
                return
            
            injection_check = self.prompt_injection_detector.detect(user_message)
            if not injection_check["is_safe"]:
                user_message = self.prompt_injection_detector.sanitize(user_message)
            
            # 添加到短期记忆
            self.short_term_memory.add_message("user", user_message)
            self.state.add_message("user", user_message)
            
            # 意图识别
            intent = await self._identify_intent(user_message)
            yield {"type": "intent", "content": intent.get("intent", "")}
            
            # 判断是否需要规划（复杂任务）
            needs_planning = self._needs_planning(user_message, intent)
            
            if needs_planning:
                yield {"type": "planning_start", "content": "正在制定执行计划..."}
                
                # 创建并执行计划
                plan = await self.planning_module.create_and_execute_plan(
                    goal=user_message,
                    context=context
                )
                
                yield {
                    "type": "planning_end", 
                    "content": f"计划执行完成: {plan.completed_steps}/{plan.total_steps} 步骤",
                    "metadata": {
                        "plan_id": plan.plan_id,
                        "subtasks_count": len(plan.subtasks),
                        "completed": plan.completed_steps,
                        "total": plan.total_steps
                    }
                }
                
                # 基于计划结果生成回复
                tool_result = {
                    "plan_completed": True,
                    "subtask_results": [
                        {"task": t.description, "status": t.status.name, "result": str(t.result)[:200] if t.result else None}
                        for t in plan.subtasks
                    ]
                }
            else:
                # 简单任务，直接执行工具
                tool_result = None
                if intent.get("should_use_tool"):
                    yield {"type": "tool_start", "content": intent.get("tool_name", "")}
                    tool_result = await self._execute_tool(intent)
                    yield {"type": "tool_end", "content": "工具执行完成"}
            
            # 流式生成回复
            full_response = ""
            async for chunk in self._generate_response_stream(
                user_message=user_message,
                intent=intent,
                tool_result=tool_result,
                context=context
            ):
                full_response += chunk
                yield {"type": "token", "content": chunk}
            
            # 完成
            self.short_term_memory.add_message("assistant", full_response)
            self.state.add_message("assistant", full_response)
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            yield {
                "type": "done",
                "content": "",
                "metadata": {
                    "session_id": self.session_id,
                    "intent": intent.get("intent"),
                    "tool_used": intent.get("tool_name"),
                    "duration_seconds": duration
                }
            }
    
    async def _generate_response_stream(
        self,
        user_message: str,
        intent: Dict[str, Any],
        tool_result: Optional[Dict[str, Any]],
        context: Optional[Dict[str, Any]]
    ):
        """流式生成回复"""
        # 准备上下文
        conversation_context = self.short_term_memory.get_context(max_tokens=2000)
        
        tool_context = ""
        if tool_result and tool_result.get("success"):
            tool_context = f"\n\n工具执行结果:\n{json.dumps(tool_result.get('data'), ensure_ascii=False, indent=2)}"
        
        if not self.llm:
            # 无 LLM 时返回简单响应
            response = self._generate_simple_response(intent, tool_result)
            for char in response:
                yield char
                await asyncio.sleep(0.01)
            return
        
        response_prompt = f"""你是一个反诈中心的AI助手，负责回答关于诈骗案件的问题。

对话历史:
{conversation_context}

用户最新消息: {user_message}
{tool_context}

请根据以上信息，用友好、专业的语气回复用户。
如果工具返回了数据，请用清晰的方式总结关键信息。
如果是闲聊，请友好回应并引导到反诈相关话题。
"""
        
        try:
            # 使用流式 API
            stream = await self.llm.chat.completions.create(
                model=get_llm_model(),
                messages=wrap_messages([{"role": "user", "content": response_prompt}]),
                temperature=0.7,
                max_tokens=1000,
                stream=True
            )
            
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            logger.error("LLM stream generation failed", error=str(e))
            response = self._generate_simple_response(intent, tool_result)
            for char in response:
                yield char
    
    async def chat(self, user_message: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        处理用户消息
        
        Args:
            user_message: 用户输入
            context: 额外上下文
        
        Returns:
            回复消息和元数据
        """
        with tracer.span("chat_agent.chat", session_id=self.session_id, user_msg=user_message[:100]):
            if not self.session_id:
                self.start_session()
            
            start_time = datetime.utcnow()
            task_id = f"chat_{int(start_time.timestamp() * 1000)}"
            
            # 安全检查：输入验证
            validation_result = self.input_validator.validate_text_input(user_message, max_length=5000)
            if not validation_result["is_valid"]:
                error_msg = f"输入验证失败: {validation_result['errors']}"
                logger.warning("Input validation failed", errors=validation_result["errors"])
                self.metrics_collector.record_error("InputValidation", error_msg)
                return {
                    "session_id": self.session_id,
                    "response": "您的输入包含不合法内容，请检查后重试。",
                    "error": error_msg,
                    "metadata": {}
                }
            
            # 安全检查：Prompt 注入检测
            injection_check = self.prompt_injection_detector.detect(user_message)
            if not injection_check["is_safe"]:
                logger.warning(
                    "Prompt injection detected",
                    threats_count=len(injection_check["threats"]),
                    session_id=self.session_id
                )
                self.metrics_collector.record_error("PromptInjection", str(injection_check["threats"]))
                # 清理输入
                user_message = self.prompt_injection_detector.sanitize(user_message)
            
            # 1. 添加到短期记忆
            self.short_term_memory.add_message("user", user_message)
            self.state.add_message("user", user_message)
            
            logger.info(
                "User message received",
                session_id=self.session_id,
                message_length=len(user_message)
            )
            
            try:
                # 优先使用真正的 ReAct 循环（原生 Function Calling）
                # 失败时回退到原意图识别流水线
                use_react = self.llm is not None
                if use_react:
                    response, intent, tool_used = await self._react_chat(
                        user_message=user_message,
                        context=context
                    )
                else:
                    # 无 LLM 时走原降级路径
                    intent = await self._identify_intent(user_message)
                    tool_result = None
                    if intent.get("should_use_tool"):
                        tool_result = await self._execute_tool(intent)
                    response = await self._generate_response(
                        user_message=user_message,
                        intent=intent,
                        tool_result=tool_result,
                        context=context
                    )
                    tool_used = intent.get("tool_name") if tool_result else None

                # 5. 添加到记忆
                self.short_term_memory.add_message("assistant", response)
                self.state.add_message("assistant", response)

                # 6. 保存到向量记忆（用于长期检索）
                self.vector_memory.add_memory(
                    content=f"用户: {user_message}\n助手: {response}",
                    metadata={
                        "session_id": self.session_id,
                        "timestamp": datetime.utcnow().isoformat(),
                        "intent": intent.get("intent") if isinstance(intent, dict) else None
                    }
                )

                # 7. 检查是否需要压缩到长期记忆（当短期记忆超过阈值时）
                if len(self.short_term_memory.messages) >= 10:
                    self._compress_to_long_term_memory()

                duration = (datetime.utcnow() - start_time).total_seconds()

                # 记录成功指标
                self.metrics_collector.record_task(task_id, True, duration, {
                    "intent": intent.get("intent") if isinstance(intent, dict) else None,
                    "tool_used": bool(tool_used)
                })
                self.metrics_collector.update_confidence(
                    intent.get("confidence", 0.5) if isinstance(intent, dict) else 0.5
                )

                logger.info(
                    "Chat response generated",
                    session_id=self.session_id,
                    intent=intent.get("intent") if isinstance(intent, dict) else None,
                    tool_used=tool_used,
                    duration_seconds=duration
                )

                return {
                    "session_id": self.session_id,
                    "response": response,
                    "intent": intent.get("intent") if isinstance(intent, dict) else None,
                    "tool_used": tool_used,
                    "metadata": {
                        "duration_seconds": duration,
                        "message_count": len(self.short_term_memory.messages)
                    }
                }
                
            except CircuitBreakerOpenError as e:
                logger.error("LLM circuit breaker open", error=str(e))
                self.metrics_collector.record_error("CircuitBreakerOpen", str(e))
                error_response = "系统暂时过载，请稍后再试。"
                self.short_term_memory.add_message("assistant", error_response)
                
                return {
                    "session_id": self.session_id,
                    "response": error_response,
                    "error": str(e),
                    "metadata": {}
                }
                
            except Exception as e:
                duration = (datetime.utcnow() - start_time).total_seconds()
                
                # 记录失败指标
                self.metrics_collector.record_task(task_id, False, duration, {
                    "error": str(e),
                    "error_type": type(e).__name__
                })
                self.metrics_collector.record_error(type(e).__name__, str(e))
                
                logger.error(
                    "Chat failed",
                    session_id=self.session_id,
                    error=str(e),
                    error_type=type(e).__name__
                )
                
                error_response = f"抱歉，处理您的消息时出现了问题：{str(e)}"
                self.short_term_memory.add_message("assistant", error_response)
                
                return {
                    "session_id": self.session_id,
                    "response": error_response,
                    "error": str(e),
                    "metadata": {}
                }
    
    async def _identify_intent(self, message: str) -> Dict[str, Any]:
        """识别用户意图"""
        with tracer.span("chat_agent.identify_intent"):
            # 如果没有LLM，使用规则匹配
            if not self.llm:
                return self._rule_based_intent(message)
            
            # 使用LLM识别意图
            intent_prompt = f"""分析用户的消息，识别意图并选择合适的工具。

用户消息: {message}

可用工具:
1. query_cases - 查询案件列表（按条件筛选）
2. search_similar_cases - 搜索相似案件（语义检索）
3. get_case_detail - 获取案件详情
4. get_gangs - 查询已识别的诈骗团伙及其成员案件（GNN聚类结果），回答"哪个案件属于哪个团伙"的串并归属
5. get_statistics - 获取统计数据
6. search_knowledge - 在知识库中搜索相关信息（反诈知识、案例分析等）
7. retrieve_context - 检索相关知识并压缩为上下文（用于深度分析）

请输出JSON格式:
{{
    "intent": "用户意图的简短描述",
    "should_use_tool": true/false,
    "tool_name": "工具名称（如果需要使用）",
    "tool_input": {{
        "参数1": "值1",
        "参数2": "值2"
    }},
    "confidence": 0.0-1.0
}}

如果不需要使用工具（如闲聊、一般性问题），设置 should_use_tool 为 false。
"""
            
            try:
                response = await self.llm.chat.completions.create(
                    model=get_llm_model(),
                    messages=wrap_messages([{"role": "user", "content": intent_prompt}]),
                    temperature=0.3,
                    max_tokens=500
                )
                
                content = response.choices[0].message.content
                
                # 解析JSON
                try:
                    intent_data = json.loads(content)
                    logger.info("Intent identified", intent=intent_data.get("intent"))
                    return intent_data
                except json.JSONDecodeError:
                    logger.warning("Failed to parse intent JSON", content=content[:200])
                    return self._rule_based_intent(message)
                    
            except Exception as e:
                logger.error("LLM intent identification failed", error=str(e))
                return self._rule_based_intent(message)
    
    def _rule_based_intent(self, message: str) -> Dict[str, Any]:
        """基于规则的意图识别（fallback）"""
        message_lower = message.lower()
        
        # 查询案件
        if any(kw in message for kw in ["查询案件", "案件列表", "所有案件", "最近案件"]):
            return {
                "intent": "查询案件列表",
                "should_use_tool": True,
                "tool_name": "query_cases",
                "tool_input": {"limit": 10},
                "confidence": 0.8
            }
        
        # 搜索相似案件
        if any(kw in message for kw in ["相似案件", "类似案件", "相关案件"]):
            # 提取描述
            description = message.replace("搜索相似案件", "").replace("类似案件", "").strip()
            if description:
                return {
                    "intent": "搜索相似案件",
                    "should_use_tool": True,
                    "tool_name": "search_similar_cases",
                    "tool_input": {"description": description, "top_k": 5},
                    "confidence": 0.8
                }
        
        # 获取案件详情
        if "案件详情" in message or "CASE_" in message:
            # 提取案件ID
            import re
            case_id_match = re.search(r'CASE_\w+', message)
            if case_id_match:
                case_id = case_id_match.group(0)
                return {
                    "intent": "获取案件详情",
                    "should_use_tool": True,
                    "tool_name": "get_case_detail",
                    "tool_input": {"case_id": case_id},
                    "confidence": 0.9
                }
        
        # 统计数据
        if any(kw in message for kw in ["统计", "报表", "数据汇总", "案件数量"]):
            return {
                "intent": "获取统计数据",
                "should_use_tool": True,
                "tool_name": "get_statistics",
                "tool_input": {"period": "month"},
                "confidence": 0.8
            }
        
        # 知识库搜索
        if any(kw in message for kw in ["知识库", "反诈知识", "诈骗手法", "防范方法", "案例分析"]):
            return {
                "intent": "搜索知识库",
                "should_use_tool": True,
                "tool_name": "search_knowledge",
                "tool_input": {"query": message, "top_k": 5, "strategy": "hybrid"},
                "confidence": 0.8
            }
        
        # 默认：不需要工具
        return {
            "intent": "一般对话",
            "should_use_tool": False,
            "confidence": 0.5
        }
    
    def _needs_planning(self, message: str, intent: Dict[str, Any]) -> bool:
        """
        判断是否需要复杂任务规划
        
        Args:
            message: 用户消息
            intent: 识别的意图
        
        Returns:
            是否需要规划
        """
        # 复杂任务关键词
        complex_keywords = [
            "分析", "详细分析", "全面分析", "综合分析",
            "报告", "生成报告", "写报告",
            "对比", "比较", "分析对比",
            "团伙", "犯罪网络", "组织",
            "模式", "规律", "趋势"
        ]
        
        # 检查是否包含复杂任务关键词
        if any(kw in message for kw in complex_keywords):
            # 检查意图置信度（低置信度可能需要多步骤）
            confidence = intent.get("confidence", 0.5)
            if confidence < 0.7:
                return True
            
            # 检查是否涉及多个工具
            tool_name = intent.get("tool_name")
            if not tool_name:
                # 没有明确工具，可能需要规划
                return True
        
        return False
    
    async def _execute_tool(self, intent: Dict[str, Any]) -> Dict[str, Any]:
        """执行工具调用（使用ToolSandbox安全执行）"""
        from core.tool_sandbox import ToolSandbox
        
        with tracer.span("chat_agent.execute_tool", tool=intent.get("tool_name")):
            tool_name = intent.get("tool_name")
            tool_input = intent.get("tool_input", {})
            
            logger.info("Executing tool", tool=tool_name, input=tool_input)
            
            tool = self.tools.get(tool_name)
            if not tool:
                logger.error("Tool not found", tool=tool_name)
                return {"error": f"工具 {tool_name} 不存在"}
            
            try:
                # 注入执行上下文：登录用户（部门隔离用）+ 会话ID。
                # 工具入参是 LLM 生成的，身份信息绝不能走 tool_input。
                tool.set_context({"user": self.user, "session_id": self.session_id})

                # 使用ToolSandbox安全执行工具
                sandbox = ToolSandbox(timeout=30.0, max_memory_mb=512, max_retries=2)
                
                result = await sandbox.execute(
                    tool_func=tool,
                    tool_input=tool_input,
                    context={"session_id": self.session_id}
                )
                
                if result["success"]:
                    logger.info(
                        "Tool executed successfully via sandbox",
                        tool=tool_name,
                        execution_time=result.get("execution_time"),
                        attempts=result.get("attempts")
                    )
                    
                    # 记录工具调用指标
                    self.metrics_collector.record_tool_call(
                        tool_name=tool_name,
                        success=True,
                        latency=result.get("execution_time", 0)
                    )
                    
                    # 解析工具返回的结果
                    tool_result = result["result"]
                    return {
                        "tool_name": tool_name,
                        "success": tool_result.success if hasattr(tool_result, 'success') else True,
                        "data": tool_result.data if hasattr(tool_result, 'data') else tool_result,
                        "error": tool_result.error if hasattr(tool_result, 'error') else None
                    }
                else:
                    logger.error(
                        "Tool execution failed in sandbox",
                        tool=tool_name,
                        error=result.get("error")
                    )
                    
                    # 记录失败指标
                    self.metrics_collector.record_tool_call(
                        tool_name=tool_name,
                        success=False,
                        latency=result.get("execution_time", 0)
                    )
                    
                    return {
                        "tool_name": tool_name,
                        "success": False,
                        "error": result.get("error", "Unknown error")
                    }
                
            except Exception as e:
                logger.error(
                    "Tool execution exception",
                    tool=tool_name,
                    error=str(e)
                )
                
                # 记录异常指标
                self.metrics_collector.record_tool_call(
                    tool_name=tool_name,
                    success=False,
                    latency=0
                )
                
                return {
                    "tool_name": tool_name,
                    "success": False,
                    "error": str(e)
                }
    
    async def _generate_response(
        self,
        user_message: str,
        intent: Dict[str, Any],
        tool_result: Optional[Dict[str, Any]],
        context: Optional[Dict[str, Any]]
    ) -> str:
        """生成回复"""
        with tracer.span("chat_agent.generate_response"):
            # 1. 短期记忆上下文
            conversation_context = self.short_term_memory.get_context(max_tokens=2000)
            
            # 2. 向量记忆检索（相关历史对话）
            vector_context = ""
            try:
                relevant_memories = self.vector_memory.search(user_message, top_k=3)
                if relevant_memories:
                    memory_parts = []
                    for mem in relevant_memories:
                        if mem.get("similarity", 0) > 0.5:
                            memory_parts.append(mem["content"][:200])
                    if memory_parts:
                        vector_context = "\n\n相关历史对话:\n" + "\n---\n".join(memory_parts)
                        logger.info("Vector memory retrieved", count=len(memory_parts))
            except Exception as e:
                logger.warning("Vector memory search failed", error=str(e))
            
            # 3. 长期记忆摘要（历史会话概要）
            long_term_context = ""
            try:
                if self.session_id:
                    summary_data = self.long_term_memory.get_summary(self.session_id)
                    if summary_data:
                        long_term_context = f"\n\n本次会话概要: {summary_data.get('summary', '')}"
            except Exception as e:
                logger.warning("Long-term memory retrieval failed", error=str(e))
            
            # 4. 工具结果
            tool_context = ""
            if tool_result and tool_result.get("success"):
                tool_context = f"\n\n工具执行结果:\n{json.dumps(tool_result.get('data'), ensure_ascii=False, indent=2)}"
            
            # 生成回复
            if not self.llm:
                return self._generate_simple_response(intent, tool_result)
            
            response_prompt = f"""你是一个反诈中心的AI助手，负责回答关于诈骗案件的问题。

对话历史:
{conversation_context}
{long_term_context}
{vector_context}

用户最新消息: {user_message}
{tool_context}

请根据以上信息，用友好、专业的语气回复用户。
如果工具返回了数据，请用清晰的方式总结关键信息。
如果是闲聊，请友好回应并引导到反诈相关话题。
"""
            
            try:
                response = await self.llm.chat.completions.create(
                    model=get_llm_model(),
                    messages=wrap_messages([{"role": "user", "content": response_prompt}]),
                    temperature=0.7,
                    max_tokens=1000
                )
                
                return response.choices[0].message.content
                
            except Exception as e:
                logger.error("LLM response generation failed", error=str(e))
                return self._generate_simple_response(intent, tool_result)
    
    def _generate_simple_response(
        self,
        intent: Dict[str, Any],
        tool_result: Optional[Dict[str, Any]]
    ) -> str:
        """生成简单回复（无LLM）"""
        if not tool_result or not tool_result.get("success"):
            return "抱歉，我暂时无法处理您的请求。请稍后再试。"
        
        tool_name = tool_result.get("tool_name")
        data = tool_result.get("data", {})
        
        if tool_name == "query_cases":
            cases = data.get("cases", [])
            total = data.get("total", 0)
            return f"查询到 {total} 个案件。" + (f"最近的是：{cases[0]['title']}" if cases else "")
        
        elif tool_name == "search_similar_cases":
            similar = data.get("similar_cases", [])
            count = data.get("count", 0)
            return f"找到 {count} 个相似案件。" + (f"最相似的是：{similar[0]['title']}" if similar else "")
        
        elif tool_name == "get_case_detail":
            case = data
            return f"案件 {case.get('case_id')}：{case.get('title')}，诈骗类型：{case.get('fraud_type')}，风险等级：{case.get('risk_level')}"
        
        elif tool_name == "get_statistics":
            summary = data.get("summary", {})
            return f"统计信息：总案件数 {summary.get('total_cases')}，总金额 {summary.get('total_amount'):,.0f} 元"
        
        return "已为您处理请求。"
    
    def _save_checkpoint(self, stage: str, metadata: Dict[str, Any] = None):
        """保存检查点"""
        if not self.session_id:
            return
        
        state = {
            "session_id": self.session_id,
            "messages": self.short_term_memory.get_messages(),
            "state": self.state.to_dict() if hasattr(self.state, 'to_dict') else {}
        }
        
        meta = metadata or {}
        meta["stage"] = stage
        meta["message_count"] = len(self.short_term_memory.messages)
        
        try:
            checkpoint_id = self.checkpoint_manager.save_checkpoint(
                agent_id=f"chat_agent_{self.session_id}",
                state=state,
                metadata=meta
            )
            logger.info("Checkpoint saved", stage=stage, checkpoint_id=checkpoint_id)
        except Exception as e:
            logger.error("Failed to save checkpoint", error=str(e), stage=stage)
    
    def restore_session(self, session_id: str) -> bool:
        """恢复会话"""
        try:
            checkpoint = self.checkpoint_manager.get_latest_checkpoint(
                agent_id=f"chat_agent_{session_id}"
            )
            
            if not checkpoint:
                logger.warning("No checkpoint found for session", session_id=session_id)
                return False
            
            state = checkpoint.get("state", {})
            self.session_id = session_id
            self.short_term_memory.clear()
            
            # 恢复消息历史
            for msg in state.get("messages", []):
                self.short_term_memory.add_message(msg["role"], msg["content"])
            
            logger.info("Session restored", session_id=session_id, message_count=len(state.get("messages", [])))
            return True
            
        except Exception as e:
            logger.error("Failed to restore session", error=str(e), session_id=session_id)
            return False
    
    def get_history(self) -> List[Dict[str, Any]]:
        """获取对话历史"""
        return self.short_term_memory.get_messages()
    
    def clear_history(self):
        """清空对话历史"""
        self.short_term_memory.clear()
        logger.info("Chat history cleared", session_id=self.session_id)
    
    async def _react_chat(
        self,
        user_message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> tuple:
        """
        真正的 ReAct 循环（原生 Function Calling）

        流程：Thought → Action(tool_call) → Observation(tool_result) → Reflection
        最多迭代 max_iterations 轮，避免无限循环。

        Returns:
            (response_text, intent_dict, tool_used_name)
        """
        max_iterations = self.state.max_iterations if hasattr(self.state, "max_iterations") else 5
        tool_schemas = self.tools.to_openai_schemas()

        # 构造系统提示词
        system_prompt = (
            "你是反诈中心的 AI 助手 FraudLens。你可以调用工具查询案件、统计、知识库等。\n"
            "请按以下原则工作：\n"
            "1. 先判断用户问题是否需要调用工具；不需要时直接回答。\n"
            "2. 调用工具时给出明确的参数；同一工具避免重复调用相同参数。\n"
            "3. 拿到工具结果后，用清晰、专业的语言总结关键信息，不要原样堆砌 JSON。\n"
            "4. 涉及金额、身份证、银行卡等敏感信息时，注意脱敏呈现。\n"
            "5. 回答控制在 500 字以内，分点说明更佳。"
        )

        # 组装初始消息
        messages = [{"role": "system", "content": system_prompt}]

        # 注入短期记忆上下文（保留多轮语义）
        try:
            history_ctx = self.short_term_memory.get_context(max_tokens=1500)
            if history_ctx:
                messages.append({
                    "role": "system",
                    "content": f"对话历史（最近若干轮）:\n{history_ctx}"
                })
        except Exception as e:
            logger.warning("Short-term memory context build failed", error=str(e))

        # 注入 RAG 检索上下文（如果用户问题与反诈知识相关）
        try:
            rag_context = await self._maybe_rag_retrieve(user_message)
            if rag_context:
                messages.append({
                    "role": "system",
                    "content": f"相关知识参考:\n{rag_context}"
                })
        except Exception as e:
            logger.warning("RAG context injection failed", error=str(e))

        # 用户消息
        messages.append({"role": "user", "content": user_message})

        intent: Dict[str, Any] = {"intent": "react_chat", "confidence": 0.9}
        tool_used_name: Optional[str] = None
        final_response = ""

        for iteration in range(max_iterations):
            logger.info(
                "ReAct iteration",
                session_id=self.session_id,
                iteration=iteration + 1
            )

            try:
                # 调用 LLM（带 tools 参数，启用 Function Calling）
                # 注意：DeepSeek 兼容 OpenAI tools 接口
                llm_resp = await self.llm.chat.completions.create(
                    model=get_llm_model(),
                    messages=wrap_messages(messages),
                    tools=tool_schemas if tool_schemas else None,
                    tool_choice="auto" if tool_schemas else None,
                    temperature=0.5,
                    max_tokens=1000
                )
            except Exception as e:
                logger.error("ReAct LLM call failed", iteration=iteration + 1, error=str(e))
                # 降级到规则路径
                fallback_intent = await self._identify_intent(user_message)
                fallback_tool_result = None
                if fallback_intent.get("should_use_tool"):
                    fallback_tool_result = await self._execute_tool(fallback_intent)
                final_response = await self._generate_response(
                    user_message, fallback_intent, fallback_tool_result, context
                )
                return final_response, fallback_intent, fallback_intent.get("tool_name")

            choice = llm_resp.choices[0]
            message = choice.message

            # 把 assistant 消息追加到历史（包含可能的 tool_calls）
            assistant_msg: Dict[str, Any] = {"role": "assistant", "content": message.content or ""}
            if message.tool_calls:
                assistant_msg["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    }
                    for tc in message.tool_calls
                ]
            messages.append(assistant_msg)

            # 情况 A：没有工具调用 → 终止循环，content 即为最终回复
            if not message.tool_calls:
                final_response = message.content or ""
                # 如果迭代 0 就没工具调用，仍尝试标注意图
                if iteration == 0:
                    intent = {
                        "intent": "直接回答",
                        "should_use_tool": False,
                        "confidence": 0.9
                    }
                break

            # 情况 B：有工具调用 → 依次执行并回填 tool 消息
            for tc in message.tool_calls:
                tool_name = tc.function.name
                try:
                    tool_args = json.loads(tc.function.arguments) if tc.function.arguments else {}
                except json.JSONDecodeError as e:
                    logger.warning("Tool args JSON parse failed", tool=tool_name, error=str(e))
                    tool_args = {}

                # 记录首个工具到 intent 元数据
                if tool_used_name is None:
                    tool_used_name = tool_name
                    intent = {
                        "intent": "工具调用",
                        "should_use_tool": True,
                        "tool_name": tool_name,
                        "tool_input": tool_args,
                        "confidence": 0.9
                    }

                logger.info(
                    "ReAct tool call",
                    tool=tool_name,
                    args=tool_args,
                    iteration=iteration + 1
                )

                # 执行工具（沙箱）
                tool_output = await self._execute_tool({
                    "tool_name": tool_name,
                    "tool_input": tool_args
                })

                # 记录工具调用指标
                self.metrics_collector.record_tool_call(
                    tool_name=tool_name,
                    success=tool_output.get("success", False),
                    latency=0
                )

                # 序列化工具结果
                try:
                    obs_content = json.dumps(
                        tool_output.get("data", tool_output),
                        ensure_ascii=False,
                        default=str
                    )
                except Exception:
                    obs_content = str(tool_output)

                # 限制观测内容长度，避免上下文爆炸
                if len(obs_content) > 4000:
                    obs_content = obs_content[:4000] + "...(已截断)"

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": obs_content
                })

            # 进入下一轮，让 LLM 基于观测结果继续推理或给出最终答复

        else:
            # 达到最大迭代仍有工具调用，强制让 LLM 给出收尾回复
            logger.warning(
                "ReAct reached max iterations, forcing final response",
                max_iterations=max_iterations
            )
            try:
                llm_resp = await self.llm.chat.completions.create(
                    model=get_llm_model(),
                    messages=wrap_messages(messages + [{
                        "role": "system",
                        "content": "已达最大推理轮数，请基于已有信息直接给出最终答复（不再调用工具）。"
                    }]),
                    temperature=0.5,
                    max_tokens=800
                )
                final_response = llm_resp.choices[0].message.content or ""
            except Exception as e:
                logger.error("ReAct final response failed", error=str(e))
                final_response = "已调用工具获取信息，但生成最终回复时出错。请稍后重试。"

        # 保底：如果 LLM 未给出任何内容
        if not final_response.strip():
            final_response = "已为您处理请求。"

        return final_response, intent, tool_used_name

    async def _maybe_rag_retrieve(self, user_message: str) -> Optional[str]:
        """
        判断用户消息是否需要 RAG 检索，若是则返回压缩后的知识上下文。
        仅当消息长度 >= 6 且包含反诈相关关键词时触发，避免闲聊也走 RAG。
        """
        if len(user_message) < 6:
            return None

        rag_keywords = [
            "诈骗", "欺诈", "反诈", "套路", "话术", "洗钱", "引流", "跑分",
            "刷单", "杀猪盘", "冒充", "冒充公检法", "短信", "钓鱼", "网赌",
            "知识库", "案例", "防范", "识别", "手法"
        ]
        if not any(kw in user_message for kw in rag_keywords):
            return None

        try:
            search_tool = self.tools.get("search_knowledge")
            if not search_tool:
                return None
            result = search_tool(query=user_message, top_k=3, strategy="hybrid")
            if not result.success or not result.data:
                return None

            docs = result.data.get("documents") or result.data.get("results") or []
            if not docs:
                return None

            parts = []
            for d in docs[:3]:
                content = d.get("content") or d.get("text") or ""
                title = d.get("title", "知识片段")
                if content:
                    parts.append(f"- [{title}] {content[:300]}")

            return "\n".join(parts) if parts else None
        except Exception as e:
            logger.warning("RAG retrieve in ReAct failed", error=str(e))
            return None

    def _compress_to_long_term_memory(self):
        """将短期记忆压缩到长期记忆"""
        if not self.session_id:
            return
        
        try:
            # 获取当前短期记忆
            messages = self.short_term_memory.get_messages()
            if not messages:
                return
            
            # 压缩对话为摘要
            summary = self.long_term_memory.compress_conversation(messages)
            
            # 存储到长期记忆
            self.long_term_memory.store_summary(
                session_id=self.session_id,
                summary=summary,
                metadata={
                    "message_count": len(messages),
                    "compressed_at": datetime.utcnow().isoformat()
                }
            )
            
            logger.info(
                "Long-term memory compressed",
                session_id=self.session_id,
                message_count=len(messages)
            )
            
        except Exception as e:
            logger.error("Failed to compress to long-term memory", error=str(e))
