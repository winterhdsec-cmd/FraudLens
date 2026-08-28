"""
FraudLens — Celery 任务幂等（G11, docs/13）。

核心思路：为 (会话 + 参数) 生成确定性 task_id，并用 Redis SETNX 在窗口期内去重，
保证同一研判请求在窗口内至多只真正入队一次（at-most-once）。云端 LLM 默认关闭时
也完全不影响业务（Redis 不可用时 is_new=True 放行）。
"""
import hashlib
import json
import os

_TTL = int(os.getenv("CELERY_DEDUP_TTL", "3600"))


def _client():
    try:
        from core.redis_pool import get_redis_client
        return get_redis_client(socket_timeout=1.0)
    except Exception:
        return None


def claim_analysis_task(session_id, raw_messages, platform_data):
    """返回 (task_id, is_new)。

    is_new=False 表示窗口内已提交过，调用方应跳过 apply_async（不重复跑）。
    Redis 不可用时 is_new=True（放行，不阻断业务）。
    """
    payload = json.dumps(
        {"m": raw_messages, "p": platform_data},
        ensure_ascii=False,
        sort_keys=True,
    )
    tid = "analyze:" + hashlib.sha1(
        f"{session_id}:{payload}".encode("utf-8")
    ).hexdigest()
    r = _client()
    if r is None:
        return tid, True
    try:
        claimed = r.set(f"celery:dedup:{tid}", "1", nx=True, ex=_TTL)
        return tid, bool(claimed)
    except Exception:
        return tid, True


# 同步模式（USE_CELERY=false）幂等窗口，秒级即可覆盖"双击/重复提交"
_SYNC_TTL = int(os.getenv("SYNC_DEDUP_TTL", "120"))


def _claim_sync_analysis(raw_messages, platform_data):
    """同步研判内容级去重：返回 (是否拿到执行权, dedup_key)。

    键仅由消息内容哈希决定（不含 session_id——前端每次点击生成新 session，
    若含 session 则幂等被击穿）。窗口内第二笔相同内容提交返回 False。
    Redis 不可用时放行（不阻断业务）。
    """
    payload = json.dumps(
        {"m": raw_messages, "p": platform_data},
        ensure_ascii=False,
        sort_keys=True,
    )
    key = "sync:analyze:" + hashlib.sha1(payload.encode("utf-8")).hexdigest()
    r = _client()
    if r is None:
        return True, key
    try:
        claimed = r.set(f"celery:dedup:{key}", "1", nx=True, ex=_SYNC_TTL)
        return bool(claimed), key
    except Exception:
        return True, key
