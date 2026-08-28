"""
结构化日志和追踪系统
"""
import logging
import json
from typing import Dict, Any, Optional
from datetime import datetime
from contextlib import contextmanager
import threading


class StructuredLogger:
    """结构化日志器"""
    
    def __init__(self, name: str, level: int = logging.INFO):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        self.logger.propagate = False
        
        # 添加处理器
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s | %(levelname)s | %(name)s | %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    def info(self, message: str, **kwargs):
        """信息日志"""
        self._log(logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """警告日志"""
        self._log(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """错误日志"""
        self._log(logging.ERROR, message, **kwargs)
    
    def debug(self, message: str, **kwargs):
        """调试日志"""
        self._log(logging.DEBUG, message, **kwargs)
    
    def _log(self, level: int, message: str, **kwargs):
        """内部日志方法"""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": logging.getLevelName(level),
            "message": message,
            **kwargs
        }
        self.logger.log(level, json.dumps(log_data, ensure_ascii=False))


class TraceContext:
    """追踪上下文"""
    
    _local = threading.local()
    
    def __init__(self, trace_id: str, span_id: str, parent_span_id: Optional[str] = None):
        self.trace_id = trace_id
        self.span_id = span_id
        self.parent_span_id = parent_span_id
        self.start_time = datetime.utcnow()
        self.attributes: Dict[str, Any] = {}
    
    def set_attribute(self, key: str, value: Any):
        """设置属性"""
        self.attributes[key] = value
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "start_time": self.start_time.isoformat(),
            "attributes": self.attributes
        }


class Tracer:
    """追踪器"""
    
    def __init__(self, service_name: str = "fraudlens"):
        self.service_name = service_name
        self.logger = StructuredLogger(f"{service_name}.tracer")
        self._local = threading.local()
    
    @contextmanager
    def span(self, name: str, **attributes):
        """创建追踪span"""
        trace_id = getattr(self._local, 'trace_id', None) or self._generate_id()
        parent_span_id = getattr(self._local, 'span_id', None)
        span_id = self._generate_id()
        
        context = TraceContext(trace_id, span_id, parent_span_id)
        context.set_attribute("name", name)
        context.set_attribute("service", self.service_name)
        for k, v in attributes.items():
            context.set_attribute(k, v)
        
        # 保存当前上下文
        old_trace_id = getattr(self._local, 'trace_id', None)
        old_span_id = getattr(self._local, 'span_id', None)
        
        # 设置新上下文
        self._local.trace_id = trace_id
        self._local.span_id = span_id
        
        self.logger.info(
            f"Span started: {name}",
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id,
            **attributes
        )
        
        try:
            yield context
            self.logger.info(
                f"Span completed: {name}",
                trace_id=trace_id,
                span_id=span_id,
                duration_ms=(datetime.utcnow() - context.start_time).total_seconds() * 1000
            )
        except Exception as e:
            self.logger.error(
                f"Span failed: {name}",
                trace_id=trace_id,
                span_id=span_id,
                error=str(e),
                error_type=type(e).__name__
            )
            raise
        finally:
            # 恢复旧上下文
            if old_trace_id is not None:
                self._local.trace_id = old_trace_id
            if old_span_id is not None:
                self._local.span_id = old_span_id
    
    def _generate_id(self) -> str:
        """生成唯一ID"""
        import uuid
        return str(uuid.uuid4())[:16]


# 全局实例
try:
    from core.config import settings
    _log_level = getattr(logging, str(getattr(settings, "LOG_LEVEL", "INFO")).upper(), logging.INFO)
except Exception:
    _log_level = logging.INFO
logger = StructuredLogger("fraudlens", level=_log_level)
tracer = Tracer("fraudlens")
