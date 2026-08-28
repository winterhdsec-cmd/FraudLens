"""
FraudLens — 统一响应工具 & 日志系统
G9（docs/13）：日志改为结构化 JSON + trace_id 透传，便于 Loki/ELK 集中收集与跨服务串联。
"""
import logging
import sys
import json
import uuid
import contextvars
import datetime
from fastapi.responses import JSONResponse
from typing import Any, Optional

# ── trace_id：贯穿一次请求的链路标识（G9 / G10 基础） ──
TRACE_ID = contextvars.ContextVar("trace_id", default="-")


def gen_trace_id() -> str:
    return uuid.uuid4().hex[:16]


def set_trace_id(tid: Optional[str] = None) -> str:
    tid = tid or gen_trace_id()
    TRACE_ID.set(tid)
    return tid


def get_trace_id() -> str:
    return TRACE_ID.get()


class JsonFormatter(logging.Formatter):
    """输出单行 JSON：ts/level/logger/trace_id/msg（+ extra 透传字段）。

    不用 strftime("%f")（不被支持），改用 record.created/record.msecs 手工拼毫秒。
    """

    def format(self, record: logging.LogRecord) -> str:
        ts = datetime.datetime.utcfromtimestamp(record.created).strftime(
            "%Y-%m-%dT%H:%M:%S."
        ) + f"{int(record.msecs):03d}Z"
        payload = {
            "ts": ts,
            "level": record.levelname,
            "logger": record.name,
            "trace_id": get_trace_id(),
            "msg": record.getMessage(),
        }
        # 透传调用方通过 extra={...} 传入的结构化字段
        extra = getattr(record, "extra_fields", None)
        if isinstance(extra, dict):
            payload.update(extra)
        return json.dumps(payload, ensure_ascii=False)


logger = logging.getLogger("fraudlens")
logger.setLevel(logging.INFO)
_handler = logging.StreamHandler(sys.stdout)
_handler.setFormatter(JsonFormatter())
logger.addHandler(_handler)
logger.propagate = False


def ok(data: Any = None, message: str = "success") -> dict:
    return {"success": True, "data": data, "message": message}


def fail(error: str = "", code: int = 400) -> JSONResponse:
    return JSONResponse(
        status_code=code,
        content={"success": False, "error": error}
    )
