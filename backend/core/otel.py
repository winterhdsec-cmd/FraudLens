"""
FraudLens — OpenTelemetry 分布式追踪接入（G10, docs/13 / docs/09 #C46）。

设计铁律（与 G8 零依赖 metrics_exporter 一致）：
  OTel 默认关闭、缺包时 no-op，绝不因未安装 opentelemetry 而使应用崩溃。
  科研原型镜像无需 otel 依赖即可照常运行；仅当显式 OTEL_ENABLED=1 且依赖就绪时才真正导出追踪。

启用（环境变量，docker-compose / key.env 均可）：
  OTEL_ENABLED=1
  OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317   # OTLP gRPC 端点（默认指向编排内 collector）
  OTEL_SERVICE_NAME=fraudlens-backend

降级矩阵：
  - OTEL_ENABLED != "1"                          → 全部 no-op（默认）
  - 装了开关但 opentelemetry 包缺失             → 导入失败被吞，全部 no-op
  - 装了但 OTLP 端点不可达                       → SDK 后台导出失败静默丢弃，不阻断业务

对外 API（任何环境都可安全调用，禁用时返回 None / no-op）：
  init_otel(app=None) -> bool     在 lifespan 调一次；启用时注册 TracerProvider + 自动埋点
  is_enabled() -> bool
  get_tracer()                    返回 tracer 或 None
  span(name, **attrs)             同步上下文管理器：启用时开子 span，禁用时透传 None
  aspan(name, **attrs)            异步上下文管理器
  current_trace_id() -> str      当前 span 的 trace_id(hex)，禁用时返回 ""（供 G9 关联用）
"""
import os
import contextlib

# 总开关：默认关闭。仅当显式开启时才尝试导入 opentelemetry（避免污染原型镜像）。
_ENABLED = os.getenv("OTEL_ENABLED", "0") == "1"

# 延迟导入：只有启用时才 import；失败则标记为不可用，后续全 no-op。
_OTEL_AVAILABLE = False
if _ENABLED:
    try:
        from opentelemetry import trace  # noqa: F401
        from opentelemetry.sdk.resources import Resource  # noqa: F401
        from opentelemetry.sdk.trace import TracerProvider  # noqa: F401
        from opentelemetry.sdk.trace.export import BatchSpanProcessor  # noqa: F401
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter  # noqa: F401
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor  # noqa: F401
        from opentelemetry.instrumentation.requests import RequestsInstrumentor  # noqa: F401
        from opentelemetry.instrumentation.redis import RedisInstrumentor  # noqa: F401
        _OTEL_AVAILABLE = True
    except Exception:
        _OTEL_AVAILABLE = False

# 最终是否真正启用 = 开关 AND 依赖可用
_ENABLED = _ENABLED and _OTEL_AVAILABLE

_TRACER = None


def is_enabled() -> bool:
    return _ENABLED


def init_otel(app=None) -> bool:
    """启用时配置全局 TracerProvider + OTLP 导出 + 自动埋点；返回是否成功。

    失败（端点不可达 / 依赖异常）时静默降级为 no-op，绝不抛给调用方。
    """
    global _TRACER, _ENABLED
    if not _ENABLED:
        return False
    try:
        endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector:4317")
        service_name = os.getenv("OTEL_SERVICE_NAME", "fraudlens-backend")

        from opentelemetry import trace
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.instrumentation.requests import RequestsInstrumentor
        from opentelemetry.instrumentation.redis import RedisInstrumentor

        resource = Resource.create({
            "service.name": service_name,
            "service.version": os.getenv("APP_VERSION", "4.0.0"),
        })
        provider = TracerProvider(resource=resource)
        exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
        _TRACER = trace.get_tracer(service_name)

        if app is not None:
            FastAPIInstrumentor.instrument_app(app)
            try:
                RequestsInstrumentor().instrument()
            except Exception:
                pass
            try:
                RedisInstrumentor().instrument()
            except Exception:
                pass
        return True
    except Exception:
        # 任何异常都降级，不影响主流程
        _ENABLED = False
        _TRACER = None
        return False


def get_tracer():
    return _TRACER


@contextlib.contextmanager
def span(name: str, **attrs):
    """同步 span 上下文管理器。禁用时透传 None，调用方无需判空即可 yield 后直接用。"""
    if not _ENABLED or _TRACER is None:
        yield None
        return
    # OTel 仅接受 str/int/float/bool/Sequence；这里做一层安全过滤
    clean = {k: v for k, v in attrs.items() if isinstance(v, (str, int, float, bool))}
    with _TRACER.start_as_current_span(name) as s:
        for k, v in clean.items():
            s.set_attribute(k, v)
        yield s


@contextlib.asynccontextmanager
async def aspan(name: str, **attrs):
    """异步 span 上下文管理器。"""
    if not _ENABLED or _TRACER is None:
        yield None
        return
    clean = {k: v for k, v in attrs.items() if isinstance(v, (str, int, float, bool))}
    with _TRACER.start_as_current_span(name) as s:
        for k, v in clean.items():
            s.set_attribute(k, v)
        yield s


def current_trace_id() -> str:
    """返回当前活跃 span 的 trace_id（16 位 hex）；无活跃 span / 禁用时返回空串。"""
    if not _ENABLED:
        return ""
    try:
        from opentelemetry import trace
        ctx = trace.get_current_span().get_span_context()
        if ctx and ctx.trace_id:
            return format(ctx.trace_id, "016x")
    except Exception:
        pass
    return ""
