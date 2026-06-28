"""
长期记忆 - 压缩存储的历史对话摘要
支持 Redis 持久化，无 Redis 时优雅降级为内存存储
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import json

from core.logger import logger


class LongTermMemory:
    """
    长期记忆

    存储历史对话的压缩摘要，支持：
    - Redis 持久化（优先）
    - 内存降级（无 Redis 时）
    - 自动摘要压缩
    - 按时间检索
    """

    def __init__(self, redis_client=None):
        self.redis = None
        self.namespace = "fraudlens:long_term_memory"
        # 内存降级存储
        self._memory_store: Dict[str, str] = {}

        # 尝试连接 Redis
        try:
            if redis_client is not None:
                self.redis = redis_client
            else:
                from core.config import settings
                import redis
                self.redis = redis.from_url(settings.REDIS_URI)
                # 验证连接
                self.redis.ping()
            logger.info("LongTermMemory: Redis connected")
        except Exception as e:
            logger.warning(
                "LongTermMemory: Redis unavailable, falling back to in-memory storage",
                error=str(e)
            )
            self.redis = None

    def store_summary(self, session_id: str, summary: str, metadata: Dict[str, Any] = None):
        """存储对话摘要"""
        key = f"{self.namespace}:{session_id}"
        data = json.dumps({
            "summary": summary,
            "metadata": metadata or {},
            "timestamp": datetime.utcnow().isoformat()
        }, ensure_ascii=False)

        if self.redis:
            try:
                self.redis.set(key, data)
                self.redis.expire(key, 30 * 24 * 3600)
                return
            except Exception as e:
                logger.warning("LongTermMemory: Redis store failed, using memory fallback", error=str(e))

        self._memory_store[key] = data

    def get_summary(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取对话摘要"""
        key = f"{self.namespace}:{session_id}"

        if self.redis:
            try:
                data = self.redis.get(key)
                if data:
                    return json.loads(data)
                return None
            except Exception as e:
                logger.warning("LongTermMemory: Redis get failed, using memory fallback", error=str(e))

        data = self._memory_store.get(key)
        return json.loads(data) if data else None

    def list_summaries(self, limit: int = 10) -> List[Dict[str, Any]]:
        """列出最近的摘要"""
        summaries = []

        if self.redis:
            try:
                pattern = f"{self.namespace}:*"
                keys = self.redis.keys(pattern)
                for key in keys[-limit:]:
                    data = self.redis.get(key)
                    if data:
                        summary_data = json.loads(data)
                        summary_data["session_id"] = key.decode().split(":")[-1]
                        summaries.append(summary_data)
                return summaries
            except Exception as e:
                logger.warning("LongTermMemory: Redis list failed, using memory fallback", error=str(e))

        # 内存降级
        for key, data in list(self._memory_store.items())[-limit:]:
            summary_data = json.loads(data)
            summary_data["session_id"] = key.split(":")[-1]
            summaries.append(summary_data)

        return summaries

    def compress_conversation(self, messages: List[Dict[str, Any]]) -> str:
        """
        压缩对话为摘要
        使用规则压缩，生产环境可替换为 LLM 摘要生成
        """
        if not messages:
            return ""

        user_messages = [m for m in messages if m["role"] == "user"]
        assistant_messages = [m for m in messages if m["role"] == "assistant"]

        summary_parts = []

        if user_messages:
            summary_parts.append(f"用户提出了 {len(user_messages)} 个问题")
            last_user_msg = user_messages[-1]["content"][:100]
            summary_parts.append(f"最后的问题: {last_user_msg}")

        if assistant_messages:
            summary_parts.append(f"助手给出了 {len(assistant_messages)} 个回答")

        return " | ".join(summary_parts)

    def delete_summary(self, session_id: str):
        """删除摘要"""
        key = f"{self.namespace}:{session_id}"

        if self.redis:
            try:
                self.redis.delete(key)
                return
            except Exception as e:
                logger.warning("LongTermMemory: Redis delete failed", error=str(e))

        self._memory_store.pop(key, None)

    def clear_all(self):
        """清空所有摘要"""
        if self.redis:
            try:
                pattern = f"{self.namespace}:*"
                keys = self.redis.keys(pattern)
                if keys:
                    self.redis.delete(*keys)
                return
            except Exception as e:
                logger.warning("LongTermMemory: Redis clear failed", error=str(e))

        self._memory_store.clear()
