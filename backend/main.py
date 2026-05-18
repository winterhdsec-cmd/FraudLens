"""
FastAPI application for FraudLens.
Replaces the original Flask app.py with a modern ASGI architecture.
"""
import os
import sys
import json
import time
import uuid
import asyncio
import traceback
import threading
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional, List

from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect, UploadFile, File, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel

import jwt as pyjwt

from flask import Flask as _Flask
from dotenv import load_dotenv

# 加载 key.env
dotenv_path = os.path.join(os.path.dirname(__file__), 'key.env')
load_dotenv(dotenv_path)

from database import db, init_db
from database.crud import (
    get_all_cases, get_case_by_id,
    get_all_gangs, get_gang_by_id,
    get_sessions, get_session_detail,
    search_cases, delete_session,
    get_case_stats, update_case_status, _case_to_dict
)
from database.auth import log_operation as _flask_log_operation

DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "20051223")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME", "fraudlens")
DB_URI = f'mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4'

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "fraudlens-jwt-secret-key-2024")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 8
_TOKEN_BLACKLIST: set = set()

USE_CELERY = os.getenv("USE_CELERY", "auto").lower()
if USE_CELERY == "auto":
    try:
        import redis as _redis_check
        r = _redis_check.Redis(host='localhost', port=6379, socket_connect_timeout=1)
        r.ping()
        USE_CELERY = True
        r.close()
        print("✅ Redis 已检测到，自动启用 Celery 异步模式")
    except Exception:
        USE_CELERY = False
        print("ℹ️ Redis 未检测到，使用同步模式 (安装 Redis 后自动切换)")
elif USE_CELERY == "true":
    USE_CELERY = True
else:
    USE_CELERY = False

_flask_app: Optional[_Flask] = None

def get_flask_app() -> _Flask:
    global _flask_app
    if _flask_app is None:
        _flask_app = _Flask(__name__)
        _flask_app.config['SQLALCHEMY_DATABASE_URI'] = DB_URI
        _flask_app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        init_db(_flask_app)
    return _flask_app

# ---------- JWT Helpers ----------
def create_token(user_id: Any, extra_claims: Optional[Dict[str, Any]] = None, expires_delta: Optional[timedelta] = None) -> str:
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
        if jti in _TOKEN_BLACKLIST:
            return None
        return payload
    except pyjwt.ExpiredSignatureError:
        return None
    except pyjwt.InvalidTokenError:
        return None

# ---------- Auth Dependencies ----------
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
    app = get_flask_app()
    with app.app_context():
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

# ---------- Operation Log helper ----------
def log_operation(user_id: int, username: str, action: str, target_type: str = '', target_id: str = '', detail: Any = None, ip_address: str = ''):
    app = get_flask_app()
    with app.app_context():
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

# ---------- Progress Tracking ----------
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
                r = _redis.Redis(host='localhost', port=6379, db=0)
                r.publish(f'progress:{self.session_id}', json.dumps(entry, default=str))
                r.close()
            except Exception:
                pass

# ---------- Pydantic Models ----------
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

# ---------- Lifespan ----------
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("=" * 60)
    print("AI 反诈研判官系统 v3.0 (FastAPI) 启动")
    print("=" * 60)
    flask_app = get_flask_app()
    with flask_app.app_context():
        from database.models import User
        # 注册P1模型
        from database.p1_models import CapitalFlow, DispatchOrder, KeyPerson
        db.create_all()
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin', display_name='系统管理员', role='admin', department='反诈中心')
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print("默认管理员账号已创建 (admin/admin123)")
    try:
        from tools.engine import engine as _engine
        global fraud_engine
        fraud_engine = _engine
        print("反诈引擎初始化成功")
    except Exception as e:
        print(f"反诈引擎初始化失败: {e}")
        fraud_engine = None
    print(f"USE_CELERY={USE_CELERY}")
    print(f"数据库: {DB_HOST}:{DB_PORT}/{DB_NAME}")
    print("=" * 60)
    yield
    print("服务关闭")

# ---------- App ----------
app = FastAPI(title="FraudLens AI 反诈研判官系统", version="3.0", lifespan=lifespan)

# 挂载P1路由

# 挂载 P1 路由 (资金流向/派单/重点人员)
from database.p1_routes import router as p1_router
app.include_router(p1_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['http://localhost:5173', 'http://127.0.0.1:5173'],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- DB Context Middleware ----------
@app.middleware("http")
async def db_context_middleware(request: Request, call_next):
    flask_app = get_flask_app()
    with flask_app.app_context():
        response = await call_next(request)
    return response

# ========== Auth Routes ==========

@app.post('/api/auth/login')
async def api_login(data: LoginRequest, request: Request):
    try:
        flask_app = get_flask_app()
        with flask_app.app_context():
            from database.models import User
            user = User.query.filter_by(username=data.username).first()
            if not user or not user.check_password(data.password):
                raise HTTPException(status_code=401, detail="用户名或密码错误")
            if not user.is_active:
                raise HTTPException(status_code=403, detail="账号已被禁用")
            user.last_login = datetime.utcnow()
            db.session.commit()
            access_token = create_token(
                user.id,
                extra_claims={
                    'username': user.username,
                    'role': user.role,
                    'display_name': user.display_name
                }
            )
            refresh_token = create_refresh_token(user.id)
            ip = request.client.host if request.client else ''
            log_operation(user.id, user.username, 'login', ip_address=ip)
            return {
                "success": True,
                "access_token": access_token,
                "refresh_token": refresh_token,
                "user": user.to_dict()
            }
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})

@app.post('/api/auth/register')
async def api_register(data: RegisterRequest, request: Request):
    try:
        if not data.username or not data.password:
            raise HTTPException(status_code=400, detail="用户名和密码不能为空")
        if len(data.password) < 6:
            raise HTTPException(status_code=400, detail="密码长度至少6位")
        flask_app = get_flask_app()
        with flask_app.app_context():
            from database.models import User
            if User.query.filter_by(username=data.username).first():
                raise HTTPException(status_code=409, detail="用户名已存在")
            user = User(
                username=data.username,
                display_name=data.display_name or data.username,
                role=data.role,
                department=data.department,
                phone=data.phone
            )
            user.set_password(data.password)
            db.session.add(user)
            db.session.commit()
            ip = request.client.host if request.client else ''
            log_operation(user.id, user.username, 'register', ip_address=ip)
            return JSONResponse(status_code=201, content={
                "success": True, "message": "注册成功", "user": user.to_dict()
            })
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})

@app.get('/api/auth/me')
async def api_get_me(current_user: dict = Depends(get_current_user)):
    flask_app = get_flask_app()
    with flask_app.app_context():
        from database.models import User
        user = User.query.get(current_user['id'])
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        return {"success": True, "user": user.to_dict()}

@app.post('/api/auth/logout')
async def api_logout(request: Request):
    token = get_token_from_header(request)
    if token:
        payload = decode_token(token)
        if payload:
            jti = payload.get('jti', token[-16:])
            _TOKEN_BLACKLIST.add(jti)
    return {"success": True, "message": "已退出登录"}

@app.get('/api/auth/users')
async def api_list_users(current_user: dict = Depends(get_current_user)):
    flask_app = get_flask_app()
    with flask_app.app_context():
        from database.models import User
        users = User.query.order_by(User.created_at.desc()).all()
        return {"success": True, "users": [u.to_dict() for u in users]}

@app.get('/api/auth/logs')
async def api_get_auth_logs(current_user: dict = Depends(get_current_user)):
    flask_app = get_flask_app()
    with flask_app.app_context():
        from database.models import OperationLog
        logs = OperationLog.query.order_by(OperationLog.created_at.desc()).limit(100).all()
        return {
            "success": True,
            "logs": [{
                'id': l.id,
                'username': l.username,
                'action': l.action,
                'target': f"{l.target_type}/{l.target_id}",
                'detail': l.detail,
                'ip_address': l.ip_address,
                'created_at': l.created_at.isoformat() if l.created_at else None
            } for l in logs]
        }

@app.post('/api/auth/refresh')
async def api_refresh(data: RefreshRequest):
    token = data.refresh_token
    payload = decode_token(token)
    if not payload or payload.get('type') != 'refresh':
        raise HTTPException(status_code=401, detail="无效的刷新令牌")
    user_id = int(payload['sub'])
    flask_app = get_flask_app()
    with flask_app.app_context():
        from database.models import User
        user = User.query.get(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        access_token = create_token(
            user.id,
            extra_claims={
                'username': user.username,
                'role': user.role,
                'display_name': user.display_name
            }
        )
        return {"success": True, "access_token": access_token}

# ========== Agent Analysis ==========

@app.post('/agent-analyze')
async def api_agent_analyze(data: AnalyzeRequest, request: Request):
    try:
        raw_messages = data.messages
        platform_data = data.platform_data
        session_id = data.session_id or str(uuid.uuid4())
        if not raw_messages and not platform_data:
            raise HTTPException(status_code=400, detail="没有收到消息内容或平台数据")
        if USE_CELERY:
            from tasks import run_analysis_task
            task = run_analysis_task.delay(raw_messages, session_id)
            return {
                "success": True,
                "task_id": task.id,
                "session_id": session_id,
                "message": "分析任务已提交到队列"
            }
        print("=" * 60)
        print("反诈研判官Agent启动智能研判流程 (同步模式)...")
        print(f"会话ID: {session_id}")
        print("=" * 60)
        from agents.chief_agent import ChiefAgent
        from agents.base import AgentConfig, AgentContext
        LLM_REQUEST_TIMEOUT = 30
        llm_analyze = None
        llm_triage = None
        try:
            from langchain_community.llms import Tongyi
            llm_analyze = Tongyi(model_name="qwen-max", temperature=0.1, request_timeout=LLM_REQUEST_TIMEOUT)
            llm_triage = Tongyi(model_name="qwen-turbo", temperature=0.1, request_timeout=LLM_REQUEST_TIMEOUT)
        except ImportError:
            print("使用模拟模式 (langchain不可用)")
        progress_adapter = ProgressAdapter(session_id)
        progress_adapter.emit('analysis_progress', {
            'stage': 'init', 'stage_name': '初始化', 'status': 'running',
            'progress': 0, 'progress_percent': 0, 'message': '初始化分析引擎'
        })
        chief_agent = ChiefAgent(
            AgentConfig(agent_id="ChiefAgent"),
            llm_analyze,
            llm_triage,
            socketio=progress_adapter,
            session_id=session_id,
            persist=True
        )
        context = AgentContext(session_id=session_id, trace_id=str(uuid.uuid4()))
        result = chief_agent.process({
            'messages': raw_messages,
            'platform_data': platform_data
        }, context)
        progress_adapter.emit('analysis_complete', {
            'success': result.get('success'),
            'total_cases': result.get('total_cases', 0),
            'total_gangs': len(result.get('gangs', [])),
            'trace_id': context.trace_id
        })
        print("=" * 60)
        print("智能研判完成！")
        print("=" * 60)
        return result
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})

@app.get('/api/tasks/{task_id}')
async def api_get_task(task_id: str):
    try:
        if not USE_CELERY:
            return JSONResponse(status_code=400, content={
                "success": False, "error": "Celery模式未启用"
            })
        from celery.result import AsyncResult
        from celery_app import celery_app
        task_result = AsyncResult(task_id, app=celery_app)
        if task_result.failed():
            return {"success": False, "task_id": task_id, "status": "FAILURE", "error": str(task_result.result)}
        elif task_result.successful():
            return {"success": True, "task_id": task_id, "status": "SUCCESS", "result": task_result.result}
        else:
            meta = task_result.info or {}
            return {"success": True, "task_id": task_id, "status": task_result.state, "meta": meta}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})

# ========== WebSocket Progress ==========

@app.websocket('/ws/{session_id}')
async def websocket_progress(websocket: WebSocket, session_id: str):
    await websocket.accept()
    await websocket.send_json({"type": "connected", "session_id": session_id})
    last_index = 0
    try:
        if USE_CELERY:
            try:
                import redis as _redis
                r = _redis.Redis(host='localhost', port=6379, db=0)
                pubsub = r.pubsub()
                pubsub.subscribe(f'progress:{session_id}')
                while True:
                    message = pubsub.get_message(timeout=1.0)
                    if message and message['type'] == 'message':
                        data = json.loads(message['data'])
                        await websocket.send_json(data)
                    await asyncio.sleep(0.1)
            except Exception:
                pass
        else:
            while True:
                lock = progress_locks.get(session_id)
                store = progress_store.get(session_id, [])
                new_items = []
                if lock:
                    with lock:
                        if last_index < len(store):
                            new_items = store[last_index:]
                            last_index = len(store)
                else:
                    if last_index < len(store):
                        new_items = store[last_index:]
                        last_index = len(store)
                for item in new_items:
                    try:
                        await websocket.send_json(item)
                    except Exception:
                        pass
                await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"WebSocket错误 ({session_id}): {e}")
    finally:
        progress_store.pop(session_id, None)
        progress_locks.pop(session_id, None)

# ========== Health ==========

@app.get('/health')
async def health_check():
    db_ok = False
    try:
        flask_app = get_flask_app()
        with flask_app.app_context():
            from database.models import Case
            Case.query.first()
            db_ok = True
    except Exception:
        pass
    return {
        "status": "healthy",
        "service": "AI反诈研判官系统",
        "version": "3.0",
        "database": "connected" if db_ok else "disconnected",
        "agent_status": "active",
        "websocket_enabled": True
    }

# ========== CRUD: Cases ==========

@app.get('/api/cases')
async def api_get_cases():
    try:
        cases = get_all_cases()
        return {"success": True, "cases": cases, "total": len(cases)}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})

@app.get('/api/cases/stats')
async def api_case_stats():
    try:
        stats = get_case_stats()
        return {"success": True, "stats": stats}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})

@app.get('/api/cases/{case_id}')
async def api_get_case(case_id: str):
    try:
        case = get_case_by_id(case_id)
        if case:
            return {"success": True, "case": case}
        return JSONResponse(status_code=404, content={"success": False, "error": "案件不存在"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})

@app.put('/api/cases/{case_id}/status')
async def api_update_case_status(case_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    try:
        body = await request.json()
        new_status = body.get('status', '')
        if not new_status:
            raise HTTPException(status_code=400, detail="缺少状态参数")
        result = update_case_status(case_id, new_status)
        ip = request.client.host if request.client else ''
        log_operation(current_user['id'], current_user.get('username', ''),
                      'update_status', 'case', case_id, {'new_status': new_status}, ip_address=ip)
        return {"success": True, "case": result}
    except HTTPException:
        raise
    except ValueError as e:
        return JSONResponse(status_code=400, content={"success": False, "error": str(e)})
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})

# ========== CRUD: Gangs ==========

@app.get('/api/gangs')
async def api_get_gangs():
    try:
        gangs = get_all_gangs()
        return {"success": True, "gangs": gangs, "total": len(gangs)}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})

@app.get('/api/gangs/{gang_id}')
async def api_get_gang(gang_id: str):
    try:
        gang = get_gang_by_id(gang_id)
        if gang:
            return {"success": True, "gang": gang}
        return JSONResponse(status_code=404, content={"success": False, "error": "团伙不存在"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})

# ========== Sessions ==========

@app.get('/api/sessions')
async def api_get_sessions():
    try:
        sessions = get_sessions()
        return {"success": True, "sessions": sessions}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})

@app.get('/api/sessions/{session_id}')
async def api_get_session_detail(session_id: str):
    try:
        detail = get_session_detail(session_id)
        if detail:
            return {"success": True, **detail}
        return JSONResponse(status_code=404, content={"success": False, "error": "会话不存在"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})

@app.delete('/api/sessions/{session_id}')
async def api_delete_session(session_id: str):
    try:
        delete_session(session_id)
        return {"success": True, "message": "删除成功"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})

# ========== Search ==========

@app.get('/api/search')
async def api_search(q: str = Query('', alias='q')):
    try:
        if not q:
            return {"success": True, "cases": []}
        cases = search_cases(q)
        return {"success": True, "cases": cases, "total": len(cases)}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})

@app.get('/api/search/advanced')
async def api_advanced_search(type: str = Query('', alias='type'), value: str = Query('', alias='value')):
    try:
        if not type or not value:
            raise HTTPException(status_code=400, detail="请指定搜索类型和关键词")
        flask_app = get_flask_app()
        with flask_app.app_context():
            from database.models import Case
            cases = Case.query.order_by(Case.created_at.desc()).all()
            results = []
            for c in cases:
                entities = c.extracted_entities or {}
                if type == 'phone' and value in str(entities.get('phone_numbers', [])):
                    results.append(c)
                elif type == 'bank' and value in str(entities.get('bank_accounts', [])):
                    results.append(c)
                elif type == 'ip' and value in str(entities.get('ips', entities.get('ip_addresses', []))):
                    results.append(c)
                elif type == 'app' and value in str(entities.get('app_names', [])):
                    results.append(c)
            return {"success": True, "cases": [_case_to_dict(c) for c in results], "total": len(results)}
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})

# ========== Dashboard ==========

@app.get('/api/dashboard')
async def api_dashboard():
    try:
        from database.dashboard import get_dashboard_data
        data = get_dashboard_data()
        return {"success": True, "data": data}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})

@app.get('/api/dashboard/trend')
async def api_dashboard_trend():
    try:
        from database.dashboard import get_dashboard_data
        data = get_dashboard_data()
        return {"success": True, "trend": data['trend_data']}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})

@app.get('/api/dashboard/latest-session')
async def api_latest_session():
    try:
        sessions = get_sessions()
        if sessions:
            sid = sessions[0]['session_id']
            detail = get_session_detail(sid)
            if detail:
                return {"success": True, **detail}
        return {"success": True, "session": None, "cases": [], "gangs": []}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})

# ========= = Alerts ==========

@app.get('/api/alerts')
async def api_get_alerts():
    try:
        from database.alert import alert_engine
        alerts = alert_engine.get_active_alerts()
        return {"success": True, "alerts": alerts, "total": len(alerts)}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})

@app.post('/api/alerts/{alert_id}/resolve')
async def api_resolve_alert(alert_id: int):
    try:
        from database.alert import alert_engine
        result = alert_engine.resolve_alert(alert_id)
        if result:
            return {"success": True, "message": "警报已解决"}
        return JSONResponse(status_code=404, content={"success": False, "error": "警报不存在"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})

@app.post('/api/alerts/check')
async def api_check_alerts():
    try:
        from database.alert import alert_engine
        cases = get_all_cases()
        if not cases:
            return {"success": True, "alerts": []}
        latest = cases[0]
        alerts = alert_engine.check_new_case(latest)
        return {"success": True, "alerts": alerts}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})

# ========== Merges ==========

@app.post('/api/merges/suggest')
async def api_suggest_merges(current_user: dict = Depends(get_current_user)):
    try:
        from database.merge import suggest_merges
        cases = get_all_cases()
        suggestions = suggest_merges(cases)
        return {
            "success": True,
            "suggestions": [{
                'id': s.id,
                'case_id_a': s.case_id_a,
                'case_id_b': s.case_id_b,
                'similarity': s.similarity,
                'reason': s.reason
            } for s in suggestions],
            "total": len(suggestions)
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})

@app.post('/api/merges/confirm')
async def api_confirm_merge(data: MergeConfirmRequest, request: Request, current_user: dict = Depends(get_current_user)):
    try:
        from database.merge import confirm_merge
        confirm_merge(data.case_id_a, data.case_id_b, data.gang_id, current_user['id'])
        ip = request.client.host if request.client else ''
        log_operation(current_user['id'], current_user.get('username', ''),
                      'confirm_merge', 'merge', f"{data.case_id_a}+{data.case_id_b}", ip_address=ip)
        return {"success": True, "message": "合并成功"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})

@app.get('/api/merges/pending')
async def api_pending_merges(current_user: dict = Depends(get_current_user)):
    try:
        from database.merge import get_pending_merges
        suggestions = get_pending_merges()
        return {"success": True, "suggestions": suggestions}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})

# ========== Reports ==========

@app.get('/api/reports/case/{case_id}')
async def api_case_report(case_id: str, format: str = Query('pdf', alias='format')):
    try:
        from database.report import generate_case_report, export_case_docx
        filepath = export_case_docx(case_id) if format == 'docx' else generate_case_report(case_id)
        filename = os.path.basename(filepath)
        return {"success": True, "file_path": f"/api/reports/download/{filename}"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})

@app.get('/api/reports/gang/{gang_id}')
async def api_gang_report(gang_id: str):
    try:
        from database.report import generate_gang_report
        filepath = generate_gang_report(gang_id)
        filename = os.path.basename(filepath)
        return {"success": True, "file_path": f"/api/reports/download/{filename}"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})

@app.get('/api/reports/download/{filename}')
async def api_download_report(filename: str):
    try:
        reports_dir = os.path.join(os.path.dirname(__file__), 'reports')
        filepath = os.path.join(reports_dir, filename)
        if not os.path.exists(filepath):
            return JSONResponse(status_code=404, content={"success": False, "error": "文件不存在"})
        return FileResponse(filepath, filename=filename)
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})

# ========== Import ==========

@app.post('/api/import/csv')
async def api_import_csv(file: UploadFile = File(...)):
    try:
        from database.importer import import_from_csv
        import tempfile
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.csv')
        content = await file.read()
        tmp.write(content)
        tmp.close()
        result = import_from_csv(tmp.name)
        os.unlink(tmp.name)
        return {"success": True, **result}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})

@app.post('/api/import/excel')
async def api_import_excel(file: UploadFile = File(...)):
    try:
        from database.importer import import_from_excel
        import tempfile
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx')
        content = await file.read()
        tmp.write(content)
        tmp.close()
        result = import_from_excel(tmp.name)
        os.unlink(tmp.name)
        return {"success": True, **result}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})

# ========== Logs ==========

@app.get('/api/logs')
async def api_public_logs():
    try:
        from database.models import OperationLog
        flask_app = get_flask_app()
        with flask_app.app_context():
            logs = OperationLog.query.order_by(OperationLog.created_at.desc()).limit(50).all()
            return {
                "success": True,
                "logs": [{
                    'id': l.id, 'username': l.username, 'action': l.action,
                    'target': f"{l.target_type}/{l.target_id}",
                    'created_at': l.created_at.isoformat() if l.created_at else None
                } for l in logs]
            }
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})

# ========== Network Data ==========

@app.get('/api/network-data')
async def api_network_data():
    return {
        "success": True,
        "message": "此接口需要基于会话或数据库实现完整功能",
        "sample_data": {
            "nodes": [
                {"id": "GANG_001", "name": "示例团伙", "type": "gang", "value": 50000},
                {"id": "CASE_001", "name": "示例案件", "type": "case", "value": 15000, "gang_id": "GANG_001"}
            ],
            "links": [
                {"source": "GANG_001", "target": "CASE_001", "value": 15000}
            ]
        }
    }

# ========== Entry Point ==========

if __name__ == '__main__':
    import uvicorn
    print("=" * 60)
    print("AI 反诈研判官系统 v3.0 (FastAPI)")
    print("=" * 60)
    print("可用接口:")
    print("   POST /agent-analyze   (智能研判分析)")
    print("   GET  /health          (健康检查)")
    print("   GET  /api/cases       (案件列表)")
    print("   WS   /ws/{session_id} (实时进度)")
    print("=" * 60)
    uvicorn.run(app, host='0.0.0.0', port=5003)