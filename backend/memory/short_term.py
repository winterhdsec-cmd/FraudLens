"""
短期记忆 - 当前会话的对话历史

持久化策略（G3 会话记忆持久化）：
- 内存 deque 作为热路径缓存，始终生效（Redis 不可用时行为与历史版本一致）。
- 当绑定 session_id 且 Redis 可用时，每条消息增量写入 Redis List
  （key = fraudlens:chat:history:{session_id}），并设置 TTL。
- 恢复会话时从 Redis 读回最近 max_messages 条，实现「切换页面/重启进程不丢对话」。
- 写入 Redis 的消息**必须**已过 G2 脱敏网关（调用方保证），历史列表内不再二次脱敏，
  避免重复脱敏把 138****8888 再打成 138****0*88。
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from collections import deque
import json

from core.logger import logger

# Redis 键前缀与保留时长
HISTORY_KEY_PREFIX = "fraudlens:chat:history:"
HISTORY_TTL_SECONDS = 7 * 24 * 3600  # 会话历史保留 7 天
# 落盘上限：比内存窗口大，保证长会话「翻历史」时仍有余量
HISTORY_MAX_STORED = 200


class ShortTermMemory:
    """
    短期记忆
    
    存储当前会话的对话历史，支持：
    - 固定窗口大小
    - Token 限制
    - 自动滚动
    - Redis 持久化（可选，无 Redis 时自动降级为纯内存）
    """
    
    def __init__(self, max_messages: int = 20, max_tokens: int = 4000,
                 session_id: str = None, persist: bool = True):
        self.max_messages = max_messages
        self.max_tokens = max_tokens
        self.messages: deque = deque(maxlen=max_messages)
        self.session_id: Optional[str] = session_id
        self.created_at = datetime.utcnow()
        # persist=False 用于纯内存场景（如无会话的一次性查询），避免污染 Redis
        self.persist = persist
        self._redis_pool = None
        self._redis_checked = False

    # ------------------------------------------------------------------
    # Redis 接入（惰性 + 失败即降级，绝不让缓存故障影响对话主流程）
    # ------------------------------------------------------------------
    def _get_redis(self):
        """惰性获取 Redis 连接池；不可用时返回 None 并永久降级本次实例。"""
        if not self.persist:
            return None
        if self._redis_checked:
            return self._redis_pool
        self._redis_checked = True
        try:
            from core.redis_pool import get_redis_pool
            self._redis_pool = get_redis_pool()
        except Exception as e:
            logger.warning("ShortTermMemory: Redis 不可用，降级纯内存", error=str(e))
            self._redis_pool = None
        return self._redis_pool

    def _history_key(self) -> Optional[str]:
        if not self.session_id:
            return None
        return f"{HISTORY_KEY_PREFIX}{self.session_id}"

    def bind_session(self, session_id: str, load: bool = True) -> bool:
        """绑定会话 ID；load=True 时从 Redis 恢复历史。

        Returns: 是否成功从 Redis 恢复出历史（无历史或 Redis 不可用均返回 False）
        """
        self.session_id = session_id
        if load:
            return self.load()
        return False

    def _persist_append(self, message: Dict[str, Any]) -> None:
        """增量写入一条消息到 Redis List（含裁剪与 TTL 续期）。"""
        pool = self._get_redis()
        key = self._history_key()
        if pool is None or key is None:
            return
        try:
            with pool.get_client() as client:
                client.rpush(key, json.dumps(message, ensure_ascii=False))
                # 只保留最近 HISTORY_MAX_STORED 条，防止无限增长
                client.ltrim(key, -HISTORY_MAX_STORED, -1)
                client.expire(key, HISTORY_TTL_SECONDS)
        except Exception as e:
            logger.warning("ShortTermMemory: 写入 Redis 失败，仅保留内存",
                           session_id=self.session_id, error=str(e))

    def load(self) -> bool:
        """从 Redis 载入最近 max_messages 条历史到内存。"""
        pool = self._get_redis()
        key = self._history_key()
        if pool is None or key is None:
            return False
        try:
            with pool.get_client() as client:
                raw_items = client.lrange(key, -self.max_messages, -1)
            if not raw_items:
                return False
            restored: List[Dict[str, Any]] = []
            for raw in raw_items:
                try:
                    restored.append(json.loads(raw))
                except (ValueError, TypeError):
                    continue  # 跳过损坏条目，不影响其余历史
            if not restored:
                return False
            self.messages = deque(restored, maxlen=self.max_messages)
            logger.info("ShortTermMemory: 已从 Redis 恢复历史",
                        session_id=self.session_id, count=len(restored))
            return True
        except Exception as e:
            logger.warning("ShortTermMemory: 读取 Redis 失败",
                           session_id=self.session_id, error=str(e))
            return False

    def _persist_clear(self) -> None:
        pool = self._get_redis()
        key = self._history_key()
        if pool is None or key is None:
            return
        try:
            with pool.get_client() as client:
                client.delete(key)
        except Exception as e:
            logger.warning("ShortTermMemory: 删除 Redis 历史失败",
                           session_id=self.session_id, error=str(e))

    def detach(self) -> None:
        """解绑会话（只清内存，**不动 Redis**）。

        会话切换时使用：避免用旧 session_id 的 clear() 误删上一个会话的持久化历史。
        """
        self.messages.clear()
        self.session_id = None
    
    def add_message(self, role: str, content: str, metadata: Dict[str, Any] = None):
        """添加消息（同时增量持久化到 Redis）"""
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {}
        }
        self.messages.append(message)
        self._persist_append(message)
    
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
        """清空记忆（同时删除 Redis 中的历史）"""
        self.messages.clear()
        self._persist_clear()
    
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
        memory = cls(
            session_id=data.get("session_id"),
            # 反序列化场景不再二次回写 Redis（数据源本身可能就来自 Redis）
            persist=False,
        )
        memory.messages = deque(data.get("messages", []), maxlen=memory.max_messages)
        try:
            memory.created_at = datetime.fromisoformat(data["created_at"])
        except (KeyError, ValueError, TypeError):
            pass  # 缺失/格式异常时保留默认创建时间
        return memory
