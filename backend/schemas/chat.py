"""AI 对话共享契约（原 routes/chat.py 内联定义迁移而来）。"""
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


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
