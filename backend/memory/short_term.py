"""
短期记忆 - 当前会话的对话历史
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from collections import deque
import json


class ShortTermMemory:
    """
    短期记忆
    
    存储当前会话的对话历史，支持：
    - 固定窗口大小
    - Token 限制
    - 自动滚动
    """
    
    def __init__(self, max_messages: int = 20, max_tokens: int = 4000):
        self.max_messages = max_messages
        self.max_tokens = max_tokens
        self.messages: deque = deque(maxlen=max_messages)
        self.session_id: Optional[str] = None
        self.created_at = datetime.utcnow()
    
    def add_message(self, role: str, content: str, metadata: Dict[str, Any] = None):
        """添加消息"""
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {}
        }
        self.messages.append(message)
    
    def get_messages(self, limit: int = None) -> List[Dict[str, Any]]:
        """获取消息历史"""
        if limit:
            return list(self.messages)[-limit:]
        return list(self.messages)
    
    def get_context(self, max_tokens: int = None) -> str:
        """获取上下文（用于 LLM 输入）"""
        max_tokens = max_tokens or self.max_tokens
        
        context_parts = []
        total_tokens = 0
        
        for msg in reversed(self.messages):
            # 简单估算 token 数（中文约 1.5 字/token）
            msg_tokens = len(msg["content"]) // 1.5
            
            if total_tokens + msg_tokens > max_tokens:
                break
            
            context_parts.insert(0, f"{msg['role']}: {msg['content']}")
            total_tokens += msg_tokens
        
        return "\n".join(context_parts)
    
    def clear(self):
        """清空记忆"""
        self.messages.clear()
    
    def to_dict(self) -> Dict[str, Any]:
        """序列化"""
        return {
            "session_id": self.session_id,
            "messages": list(self.messages),
            "created_at": self.created_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ShortTermMemory':
        """反序列化"""
        memory = cls()
        memory.session_id = data.get("session_id")
        memory.messages = deque(data.get("messages", []), maxlen=memory.max_messages)
        memory.created_at = datetime.fromisoformat(data["created_at"])
        return memory
