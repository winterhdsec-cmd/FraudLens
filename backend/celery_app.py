"""
Celery configuration for FraudLens.

Broker/backend 自动适配两种 Redis 拓扑：
- 直连模式（默认）：REDIS_SENTINEL_HOSTS 为空 → redis://host:port/db
- 哨兵模式（HA）：REDIS_SENTINEL_HOSTS 非空 → 走 kombu 的 SentinelTransport。
  注意 scheme 必须是 `sentinel://`（不是 `redis+sentinel://`，后者在 kombu 5.x 会被
  静默解析为普通 redis Transport，导致哨兵失效）。多个哨兵用 `;` 分隔，
  master_name 通过 broker_transport_options 下发，实现 master 故障转移后 Worker 自动
  跟随新主（补齐 #C35 未覆盖的尾巴，详见 docs/09 #C38）。
"""
import os
from celery import Celery

_redis_host = os.getenv("REDIS_HOST", "localhost")
_redis_port = os.getenv("REDIS_PORT", "6379")
_redis_db = os.getenv("REDIS_DB", "0")
_redis_password = os.getenv("REDIS_PASSWORD", "")
_sentinel_hosts = os.getenv("REDIS_SENTINEL_HOSTS", "")
_sentinel_service = os.getenv("REDIS_SENTINEL_SERVICE_NAME", "mymaster")
_redis_auth = f":{_redis_password}@" if _redis_password else ""

if _sentinel_hosts:
    # 接受逗号或分号分隔的哨兵列表："h1:26379,h2:26379" / "h1:26379;h2:26379"
    _seps = _sentinel_hosts.replace(";", ",").split(",")
    _hosts = [h.strip() for h in _seps if h.strip()]
    # 密码仅作用于被发现的 master/slave 连接（kombu 会把 URL userinfo 密码放入
    # connection_kwargs，哨兵连接本身走独立的 sentinel_kwargs=None，不会误认证）。
    _parts = []
    for _i, _h in enumerate(_hosts):
        if _i == 0 and _redis_auth:
            _parts.append(f"sentinel://{_redis_auth}{_h}")
        else:
            _parts.append(f"sentinel://{_h}")
    _broker = ";".join(_parts) + f"/{_sentinel_service}/{_redis_db}"
else:
    _broker = f"redis://{_redis_auth}{_redis_host}:{_redis_port}/{_redis_db}"

celery_app = Celery('fraudlens',
    broker=_broker,
    backend=_broker,
    include=['tasks']
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Shanghai',
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_default_queue='celery',
    worker_prefetch_multiplier=1,
)

# 哨兵模式：告知 Kombu 通过 Sentinel 发现 master（broker 与 result backend 共用）
if _sentinel_hosts:
    _sentinel_opts = {"master_name": _sentinel_service}
    celery_app.conf.broker_transport_options = _sentinel_opts
    celery_app.conf.result_backend_transport_options = _sentinel_opts
