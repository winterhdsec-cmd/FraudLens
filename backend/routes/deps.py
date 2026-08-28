"""
Shared dependencies extracted from main.py for all route modules.
"""
import os
import json
import time
import uuid
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

from fastapi import Depends, HTTPException, Request

from sqlalchemy.exc import OperationalError, InterfaceError as SAInterfaceError, InvalidRequestError, DisconnectionError
import pymysql.err

import jwt as pyjwt

from database import db
from tools.response import logger
from tools.redis_utils import blacklist_add, blacklist_exists, redis_available

# 安全配置 - 从环境变量读取,不提供默认值以避免硬编码密钥
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not JWT_SECRET_KEY:
    raise ValueError("JWT_SECRET_KEY environment variable is required for security")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

_redis_available = redis_available()
if _redis_available:
    logger.info("JWT 黑名单使用 Redis 持久化存储")
else:
    logger.warning("Redis 不可用，JWT 黑名单将使用内存存储（重启后失效）")
_TOKEN_BLACKLIST: set = set()

USE_CELERY = os.getenv("USE_CELERY", "auto").lower()
if USE_CELERY == "auto":
    try:
        from core.redis_pool import get_redis_client
        r = get_redis_client(socket_timeout=1.0)
        r.ping()
        r.close()
        from celery_app import celery_app as _celery_app_check
        insp = _celery_app_check.control.inspect()
        workers = insp.ping()
        if workers:
            USE_CELERY = True
            logger.info("Redis + Celery Worker 已检测到，启用异步模式")
        else:
            USE_CELERY = False
            logger.info("Redis 已检测到但无 Celery Worker 运行，使用同步模式")
    except Exception:
        USE_CELERY = False
        logger.info("Redis 未检测到，使用同步模式")
elif USE_CELERY == "true":
    USE_CELERY = True
else:
    USE_CELERY = False


# 以下请求模型已迁移至共享契约包 `schemas`（T3 / docs/13 G17），路由统一从 schemas 导入：
#   from schemas.auth import LoginRequest, RegisterRequest, RefreshRequest
#   from schemas.analysis import AnalyzeRequest
#   from schemas.merge import MergeConfirmRequest

def create_token(user_id: Any, extra_claims: Optional[Dict[str, Any]] = None,
                 expires_delta: Optional[timedelta] = None) -> str:
    if expires_delta is None:
        expires_delta = timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    payload = {
        'sub': str(user_id),
        'iat': datetime.utcnow(),
        'exp': datetime.utcnow() + expires_delta,
        'type': 'access'
    }
    if extra_claims:
        payload.update(extra_claims)
    return pyjwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def create_refresh_token(user_id: Any) -> str:
    payload = {
        'sub': str(user_id),
        'iat': datetime.utcnow(),
        'exp': datetime.utcnow() + timedelta(days=7),
        'type': 'refresh'
    }
    return pyjwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        payload = pyjwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        jti = payload.get('jti', token[-16:])
        if _redis_available:
            if blacklist_exists(jti):
                return None
        elif jti in _TOKEN_BLACKLIST:
            return None
        return payload
    except pyjwt.ExpiredSignatureError:
        return None
    except pyjwt.InvalidTokenError:
        return None


def get_token_from_header(request: Request) -> Optional[str]:
    auth = request.headers.get('Authorization', '')
    if auth.startswith('Bearer '):
        return auth[7:]
    return None


def get_current_user(request: Request) -> Dict[str, Any]:
    token = get_token_from_header(request)
    if not token:
        raise HTTPException(status_code=401, detail="未提供认证令牌")
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="令牌无效或已过期")
    from database.models import User
    for _attempt in range(3):
        try:
            user = db.session.get(User, int(payload['sub']))
            break
        except Exception as e:
            logger.warning(f"数据库查询失败(重试 {_attempt + 1}/3): {e}")
            try:
                db.session.rollback()
            except Exception as rollback_err:
                logger.warning(f"回滚失败: {rollback_err}")
            try:
                db.session.remove()
            except Exception as remove_err:
                logger.warning(f"清理会话失败: {remove_err}")
            import time
            time.sleep(0.3)
            user = None
    else:
        user = None
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="账号已被禁用")
    return user.to_dict()


def get_optional_user(request: Request) -> Optional[Dict[str, Any]]:
    token = get_token_from_header(request)
    if not token:
        return None
    payload = decode_token(token)
    if not payload:
        return None
    return payload


def log_operation(user_id: int, username: str, action: str,
                  target_type: str = '', target_id: str = '',
                  detail: Any = None, ip_address: str = ''):
    from database.models import OperationLog
    log = OperationLog(
        user_id=user_id,
        username=username,
        action=action,
        target_type=target_type,
        target_id=target_id,
        detail=detail or {},
        ip_address=ip_address
    )
    db.session.add(log)
    db.session.commit()


def db_retry(max_retries=3):
    def decorator(func):
        import functools
        import asyncio
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except (
                    OperationalError, SAInterfaceError, InvalidRequestError,
                    DisconnectionError, pymysql.err.InterfaceError, pymysql.err.OperationalError
                ) as e:
                    last_error = e
                    logger.warning(f"数据库连接错误(重试 {attempt + 1}/{max_retries}): {e}")
                    try:
                        db.session.rollback()
                    except Exception as rollback_err:
                        logger.warning(f"回滚失败: {rollback_err}")
                    try:
                        db.session.close()
                    except Exception as close_err:
                        logger.warning(f"关闭连接失败: {close_err}")
                    try:
                        db.session.remove()
                    except Exception as remove_err:
                        logger.warning(f"清理会话失败: {remove_err}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(1.0)
                except Exception as e:
                    if 'pymysql.err.InterfaceError' in type(e).__name__ or 'pymysql.err.OperationalError' in type(e).__name__:
                        last_error = e
                        logger.warning(f"PyMySQL错误(重试 {attempt + 1}/{max_retries}): {e}")
                        try:
                            db.session.rollback()
                        except Exception as rollback_err:
                            logger.warning(f"回滚失败: {rollback_err}")
                        try:
                            db.session.remove()
                        except Exception as remove_err:
                            logger.warning(f"清理会话失败: {remove_err}")
                        if attempt < max_retries - 1:
                            await asyncio.sleep(1.0)
                    else:
                        raise
            raise last_error
        return wrapper
    return decorator


progress_store: Dict[str, List[Dict[str, Any]]] = {}
progress_locks: Dict[str, threading.Lock] = {}


class ProgressAdapter:
    def __init__(self, session_id: str):
        self.session_id = session_id
        if session_id not in progress_store:
            progress_store[session_id] = []
        if session_id not in progress_locks:
            progress_locks[session_id] = threading.Lock()

    def emit(self, event: str, data: Dict[str, Any], room: Optional[str] = None):
        lock = progress_locks.get(self.session_id)
        entry = {'event': event, 'data': data, 'ts': time.time()}
        if lock:
            with lock:
                progress_store[self.session_id].append(entry)
        else:
            progress_store[self.session_id].append(entry)
        if USE_CELERY:
            try:
                from core.redis_pool import get_redis_client
                r = get_redis_client()
                r.publish(f'progress:{self.session_id}', json.dumps(entry, default=str))
                r.close()
            except Exception as e:
                logger.warning(f"Redis发布进度消息失败: {e}")