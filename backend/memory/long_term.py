"""
长期记忆 - 压缩存储的历史对话摘要
支持 Redis 持久化，无 Redis 时优雅降级为内存存储
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import json

from core.logger import logger


def _as_str(key) -> str:
    """Redis key 归一化为 str。

    `get_redis_client()` 默认 `decode_responses=True`，返回的 key 已经是 str；
    但若调用方传入自定义 client（decode_responses=False）则为 bytes。
    历史实现直接 `key.decode()`，在默认配置下必然抛 AttributeError，
    且被外层兜底 except 吞掉 → 静默返回空列表，极难定位。
    """
    return key if isinstance(key, str) else key.decode()


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
                from core.redis_pool import get_redis_client
                self.redis = get_redis_client()
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
        """列出最近的摘要（按存储时间倒序）。

        两处历史缺陷在此修正：
          1. `key.decode()` 在 decode_responses=True（本项目默认）下必然抛
             AttributeError，被兜底 except 吞掉后静默返回空列表 → 改用 _as_str。
          2. `redis.keys()[-limit:]` 依赖 key 无序结果，无法兑现"最近"语义；
             且 KEYS 在大 keyspace 下会阻塞 Redis 单线程 → 改用 scan_iter 并
             按写入时间戳排序。
        """
        if self.redis:
            try:
                found: List[Dict[str, Any]] = []
                pattern = f"{self.namespace}:*"
                for key in self.redis.scan_iter(match=pattern, count=200):
                    data = self.redis.get(key)
                    if not data:
                        continue
                    summary_data = json.loads(data)
                    summary_data["session_id"] = _as_str(key).split(":")[-1]
                    found.append(summary_data)
                found.sort(key=lambda s: s.get("timestamp") or "", reverse=True)
                return found[:limit]
            except Exception as e:
                logger.warning("LongTermMemory: Redis list failed, using memory fallback", error=str(e))

        # 内存降级
        summaries: List[Dict[str, Any]] = []
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
                # scan_iter 替代 KEYS：后者在大 keyspace 下阻塞 Redis 单线程。
                # 分批 delete，避免一次性构造超大参数列表。
                batch: List[str] = []
                for key in self.redis.scan_iter(match=pattern, count=200):
                    batch.append(key)
                    if len(batch) >= 200:
                        self.redis.delete(*batch)
                        batch = []
                if batch:
                    self.redis.delete(*batch)
                return
            except Exception as e:
                logger.warning("LongTermMemory: Redis clear failed", error=str(e))

        self._memory_store.clear()
