"""
FastAPI application for FraudLens.
Replaces the original Flask app.py with a modern ASGI architecture.
"""
import os
import asyncio
import traceback
import threading
import time
import re
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from dotenv import load_dotenv

dotenv_path = os.path.join(os.path.dirname(__file__), 'key.env')
load_dotenv(dotenv_path)

from core.config import settings

# ── 内置 Redis：在任何中间件/连接池初始化之前，确保本机 Redis 可用 ──
# REDIS_AUTOSTART=1 时：端口已有 Redis → 复用；空闲且有 vendor 二进制 → 自动拉起；
# 其余情况安静跳过（redis_pool 的内存兜底链保持不变）。
try:
    from core.redis_embedded import ensure_embedded_redis
    ensure_embedded_redis()
except Exception as _redis_boot_err:  # 绝不允许 Redis 引导失败阻断启动
    print(f"[main] 内置 Redis 引导跳过: {_redis_boot_err}")

# ── G4 / G5：安全中间件（Wave 1 合规刚需，docs/13） ──
import base64

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """注入基础安全响应头（G5）。HSTS 仅在 TLS 启用时下发。"""
    def __init__(self, app):
        super().__init__(app)
        self._hsts = settings.TLS_ENABLED == "1"

    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        if self._hsts:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
        return response


def _extract_sub_from_auth(authorization: str):
    """从 Bearer JWT 中无验证地抽取 sub（仅用于限流标识，非鉴权）。"""
    try:
        if not authorization or not authorization.startswith("Bearer "):
            return None
        token = authorization[7:]
        payload_b64 = token.split(".")[1]
        payload_b64 += "=" * (-len(payload_b64) % 4)
        payload = base64.urlsafe_b64decode(payload_b64)
        import json as _json
        return _json.loads(payload).get("sub")
    except Exception:
        return None


class RateLimitMiddleware(BaseHTTPMiddleware):
    """全局令牌桶限流（G6）：按 user+IP，Redis 实现；Redis 不可用时回退进程内（不阻断）。

    配置：RATE_LIMIT_REQUESTS（默认 60）/ RATE_LIMIT_WINDOW（默认 60 秒）。
    白名单：/health /ready /docs /openapi.json /ws。
    """
    WHITELIST_PREFIXES = ("/health", "/ready", "/docs", "/openapi.json", "/ws", "/api/metrics/prometheus")

    def __init__(self, app):
        super().__init__(app)
        try:
            self.cap = int(settings.RATE_LIMIT_REQUESTS)
        except (ValueError, TypeError):
            self.cap = 60
        try:
            self.window = int(settings.RATE_LIMIT_WINDOW)
        except (ValueError, TypeError):
            self.window = 60
        self._redis = None
        try:
            from core.redis_pool import get_redis_client
            self._redis = get_redis_client(socket_timeout=1.0)
            self._redis.ping()
        except Exception:
            self._redis = None
        self._mem = {}  # 回退：进程内令牌桶

    async def dispatch(self, request, call_next):
        path = request.url.path
        if any(path.startswith(p) for p in self.WHITELIST_PREFIXES):
            return await call_next(request)
        ident = self._ident(request)
        key = f"ratelimit:{ident}"
        allowed, retry_after = self._acquire(key)
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={"success": False, "error": "请求过于频繁，请稍后再试"},
                headers={"Retry-After": str(retry_after)},
            )
        return await call_next(request)

    def _ident(self, request):
        auth = request.headers.get("authorization", "")
        sub = _extract_sub_from_auth(auth)
        client = (request.client or ("unknown", 0))[0]
        return f"u{sub}" if sub else f"ip{client}"

    def _acquire(self, key: str):
        now = time.time()
        # 0 或负数 = 不限流（开发环境便利；生产应显式配置上限）
        if self.cap <= 0:
            return True, 0
        if self._redis is not None:
            try:
                data = self._redis.hgetall(key)
                tokens = float(data.get(b"tokens", str(self.cap)))
                ts = float(data.get(b"ts", str(now)))
                elapsed = now - ts
                tokens = min(self.cap, tokens + elapsed * (self.cap / self.window))
                if tokens >= 1:
                    tokens -= 1
                    self._redis.hset(key, "tokens", tokens)
                    self._redis.hset(key, "ts", now)
                    self._redis.expire(key, self.window * 2)
                    return True, 0
                retry = int((1 - tokens) / (self.cap / self.window)) + 1
                return False, max(retry, 1)
            except Exception:
                pass  # 回退进程内
        # 进程内回退
        bucket = self._mem.get(key)
        if bucket is None:
            bucket = {"tokens": self.cap, "ts": now}
            self._mem[key] = bucket
        elapsed = now - bucket["ts"]
        bucket["tokens"] = min(
            self.cap, bucket["tokens"] + elapsed * (self.cap / self.window)
        )
        bucket["ts"] = now
        if bucket["tokens"] >= 1:
            bucket["tokens"] -= 1
            return True, 0
        retry = int((1 - bucket["tokens"]) / (self.cap / self.window)) + 1
        return False, max(retry, 1)


# ── G9 / G10：trace_id 透传（最外层，贯穿整条请求链） ──
class TraceIDMiddleware(BaseHTTPMiddleware):
    """为每次请求分配/透传 trace_id（nginx 可经 X-Trace-Id 传入），写入响应头，
    并注入 contextvars，使本次请求内的所有日志带同一链路 ID（便于 Loki/ELK 串联）。"""
    async def dispatch(self, request, call_next):
        from tools.response import set_trace_id, get_trace_id
        incoming = request.headers.get("x-trace-id")
        set_trace_id(incoming if incoming else None)
        response = await call_next(request)
        response.headers["X-Trace-Id"] = get_trace_id()
        return response


# ── G8：指标采集中间件（位于限流/CORS 之外，能捕获 429 与全链路耗时） ──
_METRICS_SKIP = ("/ready", "/health", "/docs", "/openapi.json", "/ws",
                "/api/metrics/prometheus", "/metrics", "/static")


def _normalize_path(path: str) -> str:
    """把数值路径段折叠为 {id}，避免 Prometheus label 基数爆炸。"""
    return re.sub(r"/\d+(?=/|$)", "/{id}", path)


class MetricsMiddleware(BaseHTTPMiddleware):
    """记录每个 HTTP 请求的 方法/路径/状态/耗时 到 Prometheus 指标（core.metrics_exporter）。"""
    async def dispatch(self, request, call_next):
        path = request.url.path
        if any(path.startswith(p) for p in _METRICS_SKIP):
            return await call_next(request)
        start = time.time()
        response = await call_next(request)
        dur = time.time() - start
        try:
            from core.metrics_exporter import record_request
            record_request(request.method, _normalize_path(path), response.status_code, dur)
        except Exception:
            pass  # 指标失败绝不阻断业务
        return response


from database import db, init_db
from tools.response import logger

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME", "fraudlens")

# 初始化 SQLAlchemy 2.0 引擎与会话（去除 Flask 依赖，消除 P0 架构异味）
init_db()
try:
    with db.engine.connect() as _conn:
        _conn.execute(db.text("SET NAMES utf8mb4"))
except Exception as e:
    logger.warning(f"SET NAMES utf8mb4 跳过（数据库可能未就绪）: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 60)
    logger.info("AI 反诈研判官系统 v3.0 (FastAPI) 启动")
    logger.info("=" * 60)

    # G10：OpenTelemetry 分布式追踪接入（docs/09 #C46）。
    # 启用(OTEL_ENABLED=1 且依赖就绪)时为每条路由自动开 server span；
    # 未安装依赖 / 未启用时静默 no-op，不影响主流程（科研原型零依赖可跑）。
    try:
        from core.otel import init_otel
        if init_otel(app):
            logger.info("OpenTelemetry 追踪已启用，span 经 OTLP 导出")
        else:
            logger.info("OpenTelemetry 追踪未启用（默认/依赖缺失，属正常降级）")
    except Exception as _otel_err:
        logger.warning(f"OTel 初始化跳过（未启用或依赖缺失，属正常降级）: {_otel_err}")
    from database.models import User
    from database.p1_models import CapitalFlow, DispatchOrder, KeyPerson
    try:
        db.create_all()
        if not db.session.query(User).filter_by(username='admin').first():
            admin = User(username='admin', display_name='系统管理员', role='admin', department='反诈中心')
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            logger.info("默认管理员账号已创建 (admin/admin123)")
    except Exception as _db_err:
        logger.warning(f"数据库初始化跳过（数据库可能未就绪，服务以降级模式启动）: {_db_err}")
        try:
            db.session.rollback()
        except Exception:
            pass
    try:
        from tools.engine import engine as _engine
        global fraud_engine
        fraud_engine = _engine
        logger.info("反诈引擎初始化成功")
    except Exception as e:
        logger.error(f"反诈引擎初始化失败: {e}")
        fraud_engine = None
    try:
        import threading
        def _warmup_ocr():
            try:
                from tools.ocr import get_reader as _get_ocr_reader
                _get_ocr_reader()
                logger.info("EasyOCR 模型预热完成")
            except Exception as e:
                logger.warning(f"EasyOCR 预热跳过: {e}")
        threading.Thread(target=_warmup_ocr, daemon=True).start()
        logger.info("EasyOCR 预热已在后台启动")
    except Exception as e:
        logger.warning(f"EasyOCR 预热跳过: {e}")
    try:
        from tools.engine import engine as _engine_check
        logger.info("BGE 嵌入模型已通过反诈引擎加载")
    except Exception as e:
        logger.warning(f"BGE 模型预热跳过: {e}")
    
    # 初始化RAG知识库
    try:
        from seed_knowledge import seed_knowledge_base
        seed_knowledge_base()
        logger.info("RAG 知识库初始化完成")
    except Exception as e:
        logger.warning(f"RAG 知识库初始化跳过: {e}")
    
    logger.info(f"数据库: {DB_HOST}:{DB_PORT}/{DB_NAME}")
    logger.info("=" * 60)

    # 将所有重数据初始化操作移到后台线程，避免阻塞事件循环
    def _background_init():
        from database.seed import (
            _do_seed_data, _do_p1_data, _do_gang_data, _do_radar_background,
            _do_alert_data
        )
        _do_seed_data()
        _do_p1_data()
        _do_gang_data()
        _do_alert_data()
        _do_radar_background()

    threading.Thread(target=_background_init, daemon=True).start()
    logger.info("数据初始化已在后台启动")

    yield
    logger.info("服务关闭")


app = FastAPI(title="FraudLens AI 反诈研判官系统", version="3.0", lifespan=lifespan)

from database.p1_routes import router as p1_router
app.include_router(p1_router)

# G4：CORS 源白名单（去掉通配 *，默认回退本地安全源，由 CORS_ALLOWED_ORIGINS 覆盖）
_cors_env = settings.CORS_ALLOWED_ORIGINS
_cors_origins = (
    [o.strip() for o in _cors_env.split(",") if o.strip()]
    or ["http://localhost", "http://127.0.0.1"]
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)
# G6：全局限流（最外层之下、CORS 之上）
app.add_middleware(RateLimitMiddleware)
# G5：安全响应头（最外层，确保 429 等也带头）
app.add_middleware(SecurityHeadersMiddleware)
# G8：指标采集中间件（位于限流/CORS 之外，能捕获 429 与全链路耗时）
app.add_middleware(MetricsMiddleware)
# G9/G10：trace_id 透传（最外层，贯穿整条请求链）
app.add_middleware(TraceIDMiddleware)


_db_lock = asyncio.Lock()


@app.middleware("http")
async def db_session_middleware(request: Request, call_next):
    path = request.url.path
    if path.startswith('/api/') or path in ('/agent-analyze', '/health'):
        async with _db_lock:
            response = await call_next(request)
        return response
    return await call_next(request)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    try:
        db.session.remove()
    except Exception:
        pass
    try:
        db.session.rollback()
    except Exception:
        pass
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={"success": False, "error": str(exc), "type": type(exc).__name__}
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "error": exc.detail}
    )

from routes.auth import router as auth_router
from routes.cases import router as cases_router
from routes.gangs import router as gangs_router
from routes.sessions import router as sessions_router
from routes.alerts import router as alerts_router
from routes.dashboard import router as dashboard_router
from routes.searches import router as searches_router
from routes.reports import router as reports_router
from routes.merges import router as merges_router
from routes.files import router as files_router
from routes.system import router as system_router
from routes.reviews import router as reviews_router
from routes.chat import router as chat_router
# Phase R1：办案工作流路由（案件生命周期/研判任务/止付冻结/复核/审批）
from routes.workflow import router as workflow_router

app.include_router(auth_router)
app.include_router(cases_router)
app.include_router(gangs_router)
app.include_router(sessions_router)
app.include_router(alerts_router)
app.include_router(dashboard_router)
app.include_router(searches_router)
app.include_router(reports_router)
app.include_router(merges_router)
app.include_router(files_router)
app.include_router(system_router)
app.include_router(reviews_router)
app.include_router(chat_router)
app.include_router(workflow_router)


@app.get("/ready")
async def ready_probe():
    """就绪探针:校验数据库与缓存可达,供容器编排(K8s/Docker readiness)使用。"""
    checks = {"db": "ok", "redis": "ok"}
    try:
        db.session.execute(db.text("SELECT 1"))
    except Exception as e:
        checks["db"] = f"error: {e}"
    try:
        from core.redis_pool import get_redis_client
        _r = get_redis_client(socket_timeout=2.0)
        _r.ping()
        _r.close()
    except Exception as e:
        checks["redis"] = f"error: {e}"
    if checks["db"] != "ok" or checks["redis"] != "ok":
        return JSONResponse(status_code=503, content={"status": "not_ready", **checks})
    return {"status": "ready", **checks}


# ── G8：Prometheus 文本指标端点（供 Prometheus scrape；内网抓取，无需鉴权） ──
@app.get("/api/metrics/prometheus")
async def prometheus_metrics():
    """导出 HTTP + 业务指标，符合 Prometheus 文本格式。"""
    try:
        from core.metrics_exporter import update_celery_pending, generate_latest
        update_celery_pending()
        return Response(generate_latest(), media_type="text/plain; version=0.0.4")
    except Exception as e:  # 指标失败绝不阻断
        logger.warning(f"/api/metrics/prometheus 导出失败: {e}")
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


_static_dir = os.path.join(os.path.dirname(__file__), 'static')
if os.path.isdir(_static_dir):
    app.mount("/", StaticFiles(directory=_static_dir, html=True), name="static")

if __name__ == '__main__':
    import uvicorn
    logger.info("=" * 60)
    logger.info("AI 反诈研判官系统 v3.0 (FastAPI)")
    logger.info("=" * 60)
    logger.info("   POST /agent-analyze   (智能研判分析)")
    logger.info("   GET  /health          (健康检查)")
    logger.info("   GET  /api/cases       (案件列表)")
    logger.info("   WS   /ws/{session_id} (实时进度)")
    logger.info("=" * 60)
    uvicorn.run(app, host='0.0.0.0', port=int(os.getenv("PORT", "5003")))
