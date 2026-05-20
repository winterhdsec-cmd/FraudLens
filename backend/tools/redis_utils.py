"""
FraudLens — Redis 连接工具
提供统一的 Redis 连接管理与常用操作封装
"""
import os
import json
import logging
from typing import Optional, Any

logger = logging.getLogger("fraudlens")

_redis_client = None


def get_redis():
    global _redis_client
    if _redis_client is not None:
        try:
            _redis_client.ping()
            return _redis_client
        except Exception:
            _redis_client = None
    try:
        import redis as _redis
        host = os.getenv("REDIS_HOST", "localhost")
        port = int(os.getenv("REDIS_PORT", "6379"))
        db = int(os.getenv("REDIS_DB", "0"))
        password = os.getenv("REDIS_PASSWORD", None)
        _redis_client = _redis.Redis(
            host=host, port=port, db=db,
            password=password or None,
            socket_connect_timeout=2,
            decode_responses=True
        )
        _redis_client.ping()
        logger.info(f"Redis 连接成功 ({host}:{port}/{db})")
        return _redis_client
    except Exception as e:
        logger.warning(f"Redis 不可用，将使用内存存储: {e}")
        return None


def redis_available():
    client = get_redis()
    return client is not None


def blacklist_add(jti: str, ttl_seconds: int = 86400) -> bool:
    client = get_redis()
    if client is None:
        return False
    try:
        client.setex(f"blacklist:{jti}", ttl_seconds, "1")
        return True
    except Exception as e:
        logger.error(f"Redis blacklist_add 失败: {e}")
        return False


def blacklist_exists(jti: str) -> bool:
    client = get_redis()
    if client is None:
        return False
    try:
        return client.exists(f"blacklist:{jti}") > 0
    except Exception as e:
        logger.error(f"Redis blacklist_exists 失败: {e}")
        return False


def alert_store_set(alert_id: int, data: dict, ttl_seconds: int = 604800) -> bool:
    client = get_redis()
    if client is None:
        return False
    try:
        client.setex(f"alert:{alert_id}", ttl_seconds, json.dumps(data, default=str))
        return True
    except Exception as e:
        logger.error(f"Redis alert_store_set 失败: {e}")
        return False


def alert_store_get(alert_id: int) -> Optional[dict]:
    client = get_redis()
    if client is None:
        return None
    try:
        raw = client.get(f"alert:{alert_id}")
        if raw:
            return json.loads(raw)
        return None
    except Exception as e:
        logger.error(f"Redis alert_store_get 失败: {e}")
        return None


def alert_store_delete(alert_id: int) -> bool:
    client = get_redis()
    if client is None:
        return False
    try:
        client.delete(f"alert:{alert_id}")
        return True
    except Exception as e:
        logger.error(f"Redis alert_store_delete 失败: {e}")
        return False


def alert_list_all() -> list:
    alerts = []
    client = get_redis()
    if client is None:
        return alerts
    try:
        keys = client.keys("alert:*")
        for key in sorted(keys):
            raw = client.get(key)
            if raw:
                alerts.append(json.loads(raw))
        return alerts
    except Exception as e:
        logger.error(f"Redis alert_list_all 失败: {e}")
        return []