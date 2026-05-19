"""
FraudLens — 统一响应工具 & 日志系统
"""
import logging
import sys
from fastapi.responses import JSONResponse
from typing import Any, Optional

# ── 日志系统 ──
logger = logging.getLogger("fraudlens")
logger.setLevel(logging.INFO)
_handler = logging.StreamHandler(sys.stdout)
_handler.setFormatter(logging.Formatter(
    "[%(asctime)s] %(levelname)s %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
))
logger.addHandler(_handler)
logger.propagate = False


def ok(data: Any = None, message: str = "success") -> dict:
    return {"success": True, "data": data, "message": message}


def fail(error: str = "", code: int = 400) -> JSONResponse:
    return JSONResponse(
        status_code=code,
        content={"success": False, "error": error}
    )