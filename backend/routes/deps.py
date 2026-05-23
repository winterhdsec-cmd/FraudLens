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
from pydantic import BaseModel

import jwt as pyjwt

from database import db
from tools.response import logger
from tools.redis_utils import blacklist_add, blacklist_exists, redis_available

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "fraudlens-jwt-secret-key-2024")
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
        import redis as _redis_check
        r = _redis_check.Redis(host=os.getenv('REDIS_HOST', 'localhost'), port=int(os.getenv('REDIS_PORT', '6379')), password=os.getenv('REDIS_PASSWORD', None) or None, socket_connect_timeout=1)
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


class LoginRequest(BaseModel):
    username: str
    password: str

class RegisterRequest(BaseModel):
    username: str
    password: str
    display_name: str = ''
    role: str = 'police'
    department: str = ''
    phone: str = ''

class RefreshRequest(BaseModel):
    refresh_token: str

class MergeConfirmRequest(BaseModel):
    case_id_a: str
    case_id_b: str
    gang_id: str

class AnalyzeRequest(BaseModel):
    messages: list = []
    platform_data: dict = {}
    session_id: Optional[str] = None


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
    user = User.query.get(int(payload['sub']))
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
                import redis as _redis
                r = _redis.Redis(host=os.getenv('REDIS_HOST', 'localhost'), port=int(os.getenv('REDIS_PORT', '6379')), password=os.getenv('REDIS_PASSWORD', None) or None, db=int(os.getenv('REDIS_DB', '0')))
                r.publish(f'progress:{self.session_id}', json.dumps(entry, default=str))
                r.close()
            except Exception:
                pass