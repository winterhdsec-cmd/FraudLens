"""
AI对话API路由
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from datetime import datetime

from agents.chat_agent import ChatAgent
from core.logger import logger
from core.security import PromptInjectionDetector, InputValidator
from .deps import get_current_user

router = APIRouter(prefix="/api/chat", tags=["chat"])


# 请求/响应模型
class ChatRequest(BaseModel):
    """对话请求"""
    message: str = Field(..., description="用户消息", min_length=1, max_length=5000)
    session_id: Optional[str] = Field(None, description="会话ID（可选，不传则创建新会话）")
    context: Optional[Dict[str, Any]] = Field(None, description="额外上下文")


class ChatResponse(BaseModel):
    """对话响应"""
    session_id: str
    response: str
    intent: Optional[str] = None
    tool_used: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SessionInfo(BaseModel):
    """会话信息"""
    session_id: str
    message_count: int
    created_at: str
    last_active: str


# 全局ChatAgent实例（实际生产环境应该用依赖注入）
_chat_agent: Optional[ChatAgent] = None


def get_chat_agent() -> ChatAgent:
    """获取ChatAgent实例"""
    global _chat_agent
    if _chat_agent is None:
        _chat_agent = ChatAgent()
    return _chat_agent


@router.post("/message", response_model=ChatResponse)
async def send_message(
    request: ChatRequest,
    chat_agent: ChatAgent = Depends(get_chat_agent),
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
        
        # 设置会话
        if request.session_id:
            chat_agent.session_id = request.session_id
        else:
            chat_agent.start_session()
        
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


@router.get("/sessions/{session_id}/history")
async def get_chat_history(
    session_id: str,
    chat_agent: ChatAgent = Depends(get_chat_agent),
    current_user: dict = Depends(get_current_user)
):
    """获取对话历史"""
    try:
        chat_agent.session_id = session_id
        history = chat_agent.get_history()
        
        return {
            "session_id": session_id,
            "messages": history,
            "count": len(history)
        }
    except Exception as e:
        logger.error("Get history error", error=str(e))
        raise HTTPException(status_code=500, detail=f"获取历史失败: {str(e)}")


@router.delete("/sessions/{session_id}")
async def clear_session(
    session_id: str,
    chat_agent: ChatAgent = Depends(get_chat_agent),
    current_user: dict = Depends(get_current_user)
):
    """清空会话历史"""
    try:
        chat_agent.session_id = session_id
        chat_agent.clear_history()
        
        return {
            "message": "会话已清空",
            "session_id": session_id
        }
    except Exception as e:
        logger.error("Clear session error", error=str(e))
        raise HTTPException(status_code=500, detail=f"清空会话失败: {str(e)}")


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
                "name": "统计数据",
                "description": "获取案件统计数据",
                "example": "这个月的案件统计",
                "tool": "get_statistics"
            }
        ]
    }
