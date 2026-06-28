"""
AI对话助手 - 支持多轮对话、工具调用、RAG检索
基于 LangGraph 和 mem0 的最佳实践
"""
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
import asyncio

from openai import AsyncOpenAI
from core.state import AgentState, AgentStatus
from core.logger import logger, tracer
from core.config import settings
from core.security import get_prompt_injection_detector, get_input_validator
from core.circuit_breaker import get_circuit_breaker, CircuitBreakerOpenError
from core.metrics import get_metrics_collector
from core.checkpoint import get_checkpoint_manager
from tools.base import ToolRegistry
from tools.database_tools import QueryCasesTool, SearchSimilarCasesTool, GetCaseDetailTool
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
        self.tools.register(GetStatisticsTool())
        self.tools.register(SearchKnowledgeTool())
        self.tools.register(RetrieveAndCompressContextTool())
        
        # 记忆系统
        self.short_term_memory = ShortTermMemory(max_messages=20)
        self.long_term_memory = LongTermMemory()
        self.vector_memory = VectorMemory(embedding_model=embedding_model)
        
        # 会话状态
        self.session_id = None
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
        
        logger.info("ChatAgent initialized", tools=list(self.tools.list_tools().keys()))
    
    @property
    def llm(self) -> Optional[AsyncOpenAI]:
        """延迟初始化LLM客户端"""
        if self._llm is None:
            if not settings.DEEPSEEK_API_KEY:
                logger.warning("DEEPSEEK_API_KEY not configured, LLM features disabled")
                return None
            self._llm = AsyncOpenAI(
                api_key=settings.DEEPSEEK_API_KEY,
                base_url=settings.DEEPSEEK_BASE_URL,
                timeout=60
            )
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
                # 2. 意图识别和工具选择
                intent = await self._identify_intent(user_message)
                
                # 3. 执行工具调用（如果需要）
                tool_result = None
                if intent.get("should_use_tool"):
                    tool_result = await self._execute_tool(intent)
                
                # 4. 生成回复
                response = await self._generate_response(
                    user_message=user_message,
                    intent=intent,
                    tool_result=tool_result,
                    context=context
                )
                
                # 5. 添加到记忆
                self.short_term_memory.add_message("assistant", response)
                self.state.add_message("assistant", response)
                
                # 6. 保存到向量记忆（用于长期检索）
                self.vector_memory.add_memory(
                    content=f"用户: {user_message}\n助手: {response}",
                    metadata={
                        "session_id": self.session_id,
                        "timestamp": datetime.utcnow().isoformat(),
                        "intent": intent.get("intent")
                    }
                )
                
                # 7. 检查是否需要压缩到长期记忆（当短期记忆超过阈值时）
                if len(self.short_term_memory.messages) >= 10:
                    self._compress_to_long_term_memory()
                
                duration = (datetime.utcnow() - start_time).total_seconds()
                
                # 记录成功指标
                self.metrics_collector.record_task(task_id, True, duration, {
                    "intent": intent.get("intent"),
                    "tool_used": intent.get("should_use_tool")
                })
                self.metrics_collector.update_confidence(intent.get("confidence", 0.5))
                
                logger.info(
                    "Chat response generated",
                    session_id=self.session_id,
                    intent=intent.get("intent"),
                    tool_used=intent.get("should_use_tool"),
                    duration_seconds=duration
                )
                
                return {
                    "session_id": self.session_id,
                    "response": response,
                    "intent": intent.get("intent"),
                    "tool_used": intent.get("tool_name"),
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
4. get_statistics - 获取统计数据
5. search_knowledge - 在知识库中搜索相关信息（反诈知识、案例分析等）
6. retrieve_context - 检索相关知识并压缩为上下文（用于深度分析）

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
                    model="deepseek-chat",
                    messages=[{"role": "user", "content": intent_prompt}],
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
                    model="deepseek-chat",
                    messages=[{"role": "user", "content": response_prompt}],
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
