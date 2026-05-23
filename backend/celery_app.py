"""
Celery configuration for FraudLens.
"""
import os
from celery import Celery

_redis_host = os.getenv("REDIS_HOST", "localhost")
_redis_port = os.getenv("REDIS_PORT", "6379")
_redis_db = os.getenv("REDIS_DB", "0")
_redis_password = os.getenv("REDIS_PASSWORD", "")
_redis_auth = f":{_redis_password}@" if _redis_password else ""
_redis_url = f"redis://{_redis_auth}{_redis_host}:{_redis_port}/{_redis_db}"

celery_app = Celery('fraudlens',
    broker=_redis_url,
    backend=_redis_url,
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
    worker_prefetch_multiplier=1,
)