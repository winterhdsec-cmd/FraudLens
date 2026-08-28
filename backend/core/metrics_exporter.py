"""
FraudLens — 零依赖 Prometheus 文本指标导出器（G8, docs/13）。

输出符合 Prometheus 文本格式（https://prometheus.io/docs/instrumenting/exposition_formats/），
可被 Prometheus 直接 scrape。刻意不引入 prometheus_client，避免给科研原型环境加第三方依赖。

用法：
    from core.metrics_exporter import (
        record_request, inc_analysis, inc_gangs,
        inc_freeze, inc_degrade, update_celery_pending, generate_latest,
    )

    record_request("GET", "/api/cases", 200, 0.123)   # HTTP 中间件
    inc_analysis(); inc_gangs(3); inc_freeze(2); inc_degrade()  # 业务事件
    update_celery_pending()                              # 刷新 Celery 待处理 gauge
    text = generate_latest()                             # 给 /api/metrics/prometheus 端点
"""
import threading
import time
from typing import Dict, List, Tuple

_LOCK = threading.Lock()

# 指标单位约定：计数用 _total 后缀；耗时用 _seconds 后缀。
_DEFAULT_BUCKETS = (0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0)


class _Base:
    def __init__(self, name: str, help_: str, labels: Tuple[str, ...] = ()):
        self.name = name
        self.help = help_
        self.labels = tuple(labels)

    def _label_str(self, kw: Dict[str, str]) -> str:
        if not self.labels:
            return ""
        parts = []
        for l in self.labels:
            v = str(kw.get(l, "")).replace("\\", "\\\\").replace('"', '\\"')
            parts.append(f'{l}="{v}"')
        return "{" + ",".join(parts) + "}"

    def emit(self) -> List[str]:
        raise NotImplementedError


class Counter(_Base):
    def __init__(self, name, help_, labels=()):
        super().__init__(name, help_, labels)
        self._v: Dict[Tuple, float] = {}

    def inc(self, amount: float = 1.0, **kw):
        key = tuple(kw.get(l, "") for l in self.labels)
        with _LOCK:
            self._v[key] = self._v.get(key, 0.0) + amount

    def emit(self):
        out = [f"# HELP {self.name} {self.help}", f"# TYPE {self.name} counter"]
        for key, val in self._v.items():
            kw = dict(zip(self.labels, key))
            out.append(f"{self.name}{self._label_str(kw)} {val}")
        return out


class Gauge(_Base):
    def __init__(self, name, help_, labels=()):
        super().__init__(name, help_, labels)
        self._v: Dict[Tuple, float] = {}

    def set(self, value: float, **kw):
        key = tuple(kw.get(l, "") for l in self.labels)
        with _LOCK:
            self._v[key] = float(value)

    def emit(self):
        out = [f"# HELP {self.name} {self.help}", f"# TYPE {self.name} gauge"]
        for key, val in self._v.items():
            kw = dict(zip(self.labels, key))
            out.append(f"{self.name}{self._label_str(kw)} {val}")
        return out


class Histogram(_Base):
    def __init__(self, name, help_, buckets=_DEFAULT_BUCKETS, labels=()):
        super().__init__(name, help_, labels)
        self.buckets = tuple(buckets)
        # _v[key] = {"count":n, "sum":s, "bucket": {b: c}}
        self._v: Dict[Tuple, Dict[str, object]] = {}

    def observe(self, value: float, **kw):
        key = tuple(kw.get(l, "") for l in self.labels)
        with _LOCK:
            d = self._v.get(key)
            if d is None:
                d = {"count": 0, "sum": 0.0, "bucket": {b: 0 for b in self.buckets}}
                self._v[key] = d
            d["count"] += 1
            d["sum"] += value
            for b in self.buckets:
                if value <= b:
                    d["bucket"][b] += 1

    def emit(self):
        out = [f"# HELP {self.name} {self.help}", f"# TYPE {self.name} histogram"]
        for key, d in self._v.items():
            kw = dict(zip(self.labels, key))
            base = self.name + self._label_str(kw)
            # observe() 已把每个 bucket 存成「<= b」的累计值（见 observe），
            # 此处直接输出即可；若再次累加会重复计数（G8 实测发现的 bug）。
            for b in self.buckets:
                out.append(f'{base}_bucket{{le="{b}"}} {d["bucket"][b]}')
            out.append(f'{base}_bucket{{le="+Inf"}} {d["count"]}')
            out.append(f"{base}_sum {d['sum']}")
            out.append(f"{base}_count {d['count']}")
        return out


# ── 全局指标实例 ──
ANALYSIS_TOTAL = Counter("analysis_total", "研判任务提交总数")
GANGS_TOTAL = Counter("gangs_detected_total", "GNN 检测出的团伙总数")
FREEZE_TOTAL = Counter("freeze_decisions_total", "冻卡决策建议总数")
DEGRADE_TOTAL = Counter(
    "llm_degradation_total", "云端 LLM 不可用(降级到本地规则兜底)累计次数"
)
HTTP_REQUESTS = Counter(
    "http_requests_total", "HTTP 请求总数", ("method", "path", "status")
)
HTTP_LATENCY = Histogram(
    "http_request_duration_seconds", "HTTP 请求耗时(秒)", labels=("method", "path")
)
CELERY_PENDING = Gauge("celery_pending_tasks", "Celery 队列待处理任务数")


def record_request(method: str, path: str, status: int, duration: float):
    HTTP_REQUESTS.inc(1, method=method, path=path, status=str(status))
    HTTP_LATENCY.observe(duration, method=method, path=path)


def inc_analysis():
    ANALYSIS_TOTAL.inc()


def inc_gangs(n: int = 1):
    GANGS_TOTAL.inc(max(int(n), 0))


def inc_freeze(n: int = 1):
    FREEZE_TOTAL.inc(max(int(n), 0))


def inc_degrade():
    DEGRADE_TOTAL.inc()


def set_celery_pending(n: int):
    CELERY_PENDING.set(max(int(n), 0))


def update_celery_pending():
    """从 Redis broker 查询 Celery 默认队列长度，刷新 gauge。失败静默。"""
    try:
        from core.redis_pool import get_redis_client

        r = get_redis_client(socket_timeout=1.0)
        n = r.llen("celery")
        if n is not None:
            set_celery_pending(int(n))
    except Exception:
        pass


def generate_latest() -> str:
    lines: List[str] = []
    for m in (
        HTTP_REQUESTS,
        HTTP_LATENCY,
        ANALYSIS_TOTAL,
        GANGS_TOTAL,
        FREEZE_TOTAL,
        DEGRADE_TOTAL,
        CELERY_PENDING,
    ):
        lines.extend(m.emit())
    return "\n".join(lines) + "\n"
