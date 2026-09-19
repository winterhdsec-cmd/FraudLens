"""
AI对话API路由
"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from typing import Dict, Any, List, Optional
from datetime import datetime
import json
import threading

from agents.chat_agent import ChatAgent
from core.logger import logger
from core.security import PromptInjectionDetector, InputValidator
from .deps import get_current_user
from schemas.chat import ChatRequest, ChatResponse, SessionInfo

router = APIRouter(prefix="/api/chat", tags=["chat"])


# 请求/响应模型已迁移至 schemas.chat（T3 / docs/13 G17）

# 会话池：按 session_id 隔离 ChatAgent 实例，避免多用户串台
# （修复原全局单例导致的 session_id/memory 互相覆盖问题）
_chat_agents: Dict[str, ChatAgent] = {}
_chat_agents_lock = threading.Lock()
# 共享的工具/模型引用（无状态，可安全复用）
_shared_tools_registry = None
_shared_embedding_model = None


def _get_shared_embedding_model():
    """获取共享的 embedding 模型（用于 VectorMemory），避免每个会话重复加载"""
    global _shared_embedding_model
    if _shared_embedding_model is None:
        try:
            from core.embedding import get_embedding_model
            _shared_embedding_model = get_embedding_model()
            logger.info("ChatAgent 共享 embedding 模型已初始化")
        except Exception as e:
            logger.warning(f"ChatAgent embedding 模型加载失败，VectorMemory 将走 hash 降级: {e}")
    return _shared_embedding_model


def _create_chat_agent() -> ChatAgent:
    """创建新的 ChatAgent 实例（注入真实 embedding 模型）"""
    return ChatAgent(embedding_model=_get_shared_embedding_model())


def get_chat_agent(session_id: Optional[str] = None) -> ChatAgent:
    """获取 ChatAgent 实例（按 session_id 隔离）"""
    if not session_id:
        # 无 session_id 时返回临时实例（用于无状态查询）
        return _create_chat_agent()
    with _chat_agents_lock:
        if session_id not in _chat_agents:
            _chat_agents[session_id] = _create_chat_agent()
            # 限制会话池大小，避免内存泄漏（保留最近 100 个）
            if len(_chat_agents) > 100:
                oldest = next(iter(_chat_agents))
                del _chat_agents[oldest]
        return _chat_agents[session_id]


def get_persisted_history(session_id: str, limit: int = 200) -> List[Dict[str, Any]]:
    """直接从 Redis 读取会话历史（不依赖 ChatAgent 实例是否存在）。

    前端刷新/切页面/服务重启后都能取回完整对话，是记忆持久化的读路径。
    Redis 不可用时返回空列表，由前端降级为「无历史」。
    """
    try:
        from memory.short_term import ShortTermMemory
        memory = ShortTermMemory(session_id=session_id)
        memory.load()
        return memory.get_messages(limit=limit)
    except Exception as e:
        logger.warning("读取持久化历史失败", session_id=session_id, error=str(e))
        return []


def list_persisted_sessions(limit: int = 50) -> List[Dict[str, Any]]:
    """枚举 Redis 中已有历史的会话，供前端重建会话列表。

    返回按最近活跃时间倒序的 [{id, title, messageCount, lastActive}]。
    """
    try:
        from core.redis_pool import get_redis_pool
        from memory.short_term import HISTORY_KEY_PREFIX

        pool = get_redis_pool()
        if pool is None:
            return []

        sessions: List[Dict[str, Any]] = []
        with pool.get_client() as client:
            for raw_key in client.scan_iter(match=f"{HISTORY_KEY_PREFIX}*", count=100):
                key = raw_key if isinstance(raw_key, str) else raw_key.decode()
                sid = key[len(HISTORY_KEY_PREFIX):]
                try:
                    count = int(client.llen(key))
                    tail = client.lrange(key, -1, -1)
                except Exception:
                    continue
                if not tail:
                    continue
                last = {}
                try:
                    last = json.loads(tail[0])
                except (ValueError, TypeError):
                    pass
                # 首条 user 消息作为标题
                title = ""
                try:
                    head = client.lrange(key, 0, 1)
                    for item in head:
                        msg = json.loads(item)
                        if msg.get("role") == "user":
                            title = (msg.get("content") or "")[:20]
                            break
                except Exception:
                    pass
                sessions.append({
                    "id": sid,
                    "title": title or "未命名对话",
                    "messageCount": count,
                    "lastActive": last.get("timestamp") or "",
                })

        sessions.sort(key=lambda s: s["lastActive"], reverse=True)
        return sessions[:limit]
    except Exception as e:
        logger.warning("枚举持久化会话失败", error=str(e))
        return []


@router.post("/message", response_model=ChatResponse)
async def send_message(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    发送消息到AI助手
    
    - 支持多轮对话
    - 自动识别意图
    - 可调用工具查询案件、统计数据等
    """
    try:
        # 输入验证
        if not request.message.strip():
            raise HTTPException(status_code=400, detail="消息不能为空")
        
        # 使用core.security进行输入验证和清理
        input_validator = InputValidator()
        validation_result = input_validator.validate_text_input(request.message)
        if not validation_result["is_valid"]:
            raise HTTPException(
                status_code=400, 
                detail=f"输入验证失败: {validation_result['errors']}"
            )
        
        # Prompt注入检测
        injection_detector = PromptInjectionDetector()
        injection_result = injection_detector.detect(request.message)
        if not injection_result["is_safe"]:
            logger.warning(
                "检测到Prompt注入尝试",
                threats=injection_result["threats"]
            )
            raise HTTPException(
                status_code=400,
                detail="检测到不安全的输入内容"
            )
        
        # 清理输入
        sanitized_message = input_validator.sanitize_input(request.message)

        # 按 session_id 获取隔离的 ChatAgent 实例
        chat_agent = get_chat_agent(request.session_id)
        
        # 注入当前登录用户（工具做部门级数据隔离用；身份来自鉴权层，不信任 LLM）
        chat_agent.user = current_user
        
        # 确保会话就绪并**载入历史**（G3：切页面/重启后对话不丢）
        chat_agent.ensure_session(request.session_id)
        
        # 处理消息
        result = await chat_agent.chat(
            user_message=sanitized_message,
            context=request.context
        )
        
        return ChatResponse(
            session_id=result["session_id"],
            response=result["response"],
            intent=result.get("intent"),
            tool_used=result.get("tool_used"),
            metadata=result.get("metadata", {})
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Chat API error", error=str(e), error_type=type(e).__name__)
        raise HTTPException(status_code=500, detail=f"处理消息时出错: {str(e)}")


@router.post("/message/stream")
async def send_message_stream(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    流式发送消息到AI助手（SSE）
    
    返回 Server-Sent Events 流，支持实时展示AI回复
    """
    try:
        # 输入验证
        if not request.message.strip():
            raise HTTPException(status_code=400, detail="消息不能为空")
        
        # 使用core.security进行输入验证和清理
        input_validator = InputValidator()
        validation_result = input_validator.validate_text_input(request.message)
        if not validation_result["is_valid"]:
            raise HTTPException(
                status_code=400, 
                detail=f"输入验证失败: {validation_result['errors']}"
            )
        
        # Prompt注入检测
        injection_detector = PromptInjectionDetector()
        injection_result = injection_detector.detect(request.message)
        if not injection_result["is_safe"]:
            logger.warning(
                "检测到Prompt注入尝试",
                threats=injection_result["threats"]
            )
            raise HTTPException(
                status_code=400,
                detail="检测到不安全的输入内容"
            )
        
        # 清理输入
        sanitized_message = input_validator.sanitize_input(request.message)
        
        # 按 session_id 获取隔离的 ChatAgent 实例
        chat_agent = get_chat_agent(request.session_id)
        
        # 注入当前登录用户（工具做部门级数据隔离用；身份来自鉴权层，不信任 LLM）
        chat_agent.user = current_user
        
        # 确保会话就绪并**载入历史**（G3：切页面/重启后对话不丢）
        chat_agent.ensure_session(request.session_id)
        
        # 流式生成响应
        async def event_generator():
            try:
                async for chunk in chat_agent.chat_stream(
                    user_message=sanitized_message,
                    context=request.context
                ):
                    # 发送SSE事件
                    yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
            except Exception as e:
                logger.error("Stream error", error=str(e))
                error_chunk = {
                    "type": "error",
                    "content": f"流式响应出错: {str(e)}"
                }
                yield f"data: {json.dumps(error_chunk, ensure_ascii=False)}\n\n"
        
        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"  # 禁用Nginx缓冲
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Chat stream API error", error=str(e), error_type=type(e).__name__)
        raise HTTPException(status_code=500, detail=f"处理消息时出错: {str(e)}")


@router.get("/sessions/{session_id}/history")
async def get_chat_history(
    session_id: str,
    current_user: dict = Depends(get_current_user)
):
    """获取对话历史

    直接从 Redis 读取（不经过 ChatAgent 实例），因此即使：
    - 服务刚重启、会话池为空
    - 该会话的 Agent 实例已被 LRU 淘汰
    依然能取回完整历史。这是前端刷新/切换页面后恢复对话的数据源。
    """
    try:
        messages = get_persisted_history(session_id)
        return {
            "session_id": session_id,
            "messages": messages,
            "count": len(messages)
        }
    except Exception as e:
        logger.error("Get history error", error=str(e))
        raise HTTPException(status_code=500, detail=f"获取历史失败: {str(e)}")


@router.delete("/sessions/{session_id}")
async def clear_session(
    session_id: str,
    current_user: dict = Depends(get_current_user)
):
    """清空会话历史（内存 + Redis 一并删除）"""
    try:
        # 1) 清 Runtime 实例内的内存副本
        agent = get_chat_agent(session_id)
        agent.ensure_session(session_id)
        agent.clear_history()

        # 2) 兜底清 Redis（避免实例不存在时残留）
        try:
            from memory.short_term import ShortTermMemory
            memory = ShortTermMemory(session_id=session_id)
            memory.clear()
        except Exception as e:
            logger.warning("Redis history purge skipped", session_id=session_id, error=str(e))

        # 3) 会话池中移除，下次访问重新建实例
        with _chat_agents_lock:
            _chat_agents.pop(session_id, None)

        return {
            "message": "会话已清空",
            "session_id": session_id
        }
    except Exception as e:
        logger.error("Clear session error", error=str(e))
        raise HTTPException(status_code=500, detail=f"清空会话失败: {str(e)}")


@router.get("/sessions")
async def list_sessions(
    current_user: dict = Depends(get_current_user)
):
    """列出当前服务端持有的活跃会话（含消息数、最近活跃时间）

    用于前端「历史会话」面板在刷新后重建列表（原先该列表只存在内存里）。
    """
    try:
        items = list_persisted_sessions()
        return {"sessions": items, "count": len(items)}
    except Exception as e:
        logger.error("List sessions error", error=str(e))
        raise HTTPException(status_code=500, detail=f"获取会话列表失败: {str(e)}")


@router.get("/intents")
async def list_intents():
    """列出支持的意图和工具"""
    return {
        "intents": [
            {
                "name": "查询案件",
                "description": "查询案件列表，支持按条件筛选",
                "example": "查询最近10个案件",
                "tool": "query_cases"
            },
            {
                "name": "搜索相似案件",
                "description": "根据描述搜索语义相似的案件",
                "example": "搜索与'冒充公检法诈骗'相似的案件",
                "tool": "search_similar_cases"
            },
            {
                "name": "获取案件详情",
                "description": "获取指定案件的详细信息",
                "example": "查看案件 CASE_20240101_12345678 的详情",
                "tool": "get_case_detail"
            },
            {
                "name": "查询团伙",
                "description": "查询已识别的诈骗团伙及其成员案件（GNN聚类结果），支持串并归属分析",
                "example": "哪些案件属于同一个团伙？某案件属于哪个团伙？",
                "tool": "get_gangs"
            },
            {
                "name": "统计数据",
                "description": "获取案件统计数据",
                "example": "这个月的案件统计",
                "tool": "get_statistics"
            }
        ]
    }
