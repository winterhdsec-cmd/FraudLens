"""
对象存储封装（A4.1，#C13）。

将 OCR 原始件 / 导出报告存入本地 minio 对象存储，不进 MySQL / 裸盘，
满足"数据不出域" + 大文件独立存储 + 可审计留痕。

优雅降级：minio 不可用（未安装 SDK / 服务未起 / 网络异常）时，
``put_object`` 返回 ``False``，调用方自行退回本地磁盘，**绝不导致主接口 500**。

下载方式：
    - ``presigned_get_url`` 生成 minio 原生 URL（host 即 MINIO_ENDPOINT，
      同网络 / 容器内可直接下载；不可直接替换 host，否则签名失效）。
    - 前端经后端代理端点 ``/api/object/{key}`` 取对象（数据不出域，minio 不暴露公网）。

环境变量（docker-compose.yml 注入）：
    MINIO_ENDPOINT      默认 minio:9000（容器内服务名）
    MINIO_ROOT_USER     默认 fraudlens
    MINIO_ROOT_PASSWORD 默认 fraudlens123
    MINIO_BUCKET        默认 fraudlens
"""
import io
import os
from datetime import timedelta
from typing import Optional

from tools.response import logger

try:
    from minio import Minio
    from minio.error import S3Error
    _HAVE_MINIO = True
except Exception as e:  # pragma: no cover - SDK 缺失属部署选择
    _HAVE_MINIO = False
    Minio = None
    S3Error = Exception
    logger.warning(f"[ObjectStore] minio SDK 未安装，对象存储降级为本地: {e}")


DEFAULT_BUCKET = os.getenv("MINIO_BUCKET", "fraudlens")
_ENDPOINT = os.getenv("MINIO_ENDPOINT", "minio:9000")
_ACCESS_KEY = os.getenv("MINIO_ROOT_USER", "fraudlens")
_SECRET_KEY = os.getenv("MINIO_ROOT_PASSWORD", "fraudlens123")

_client = None
_enabled = False


def is_enabled() -> bool:
    """minio 是否真正可用（SDK 已装且连接成功）。首次调用触发懒连接。"""
    if not _HAVE_MINIO:
        return False
    _get_client()
    return _enabled


def _get_client() -> Optional["Minio"]:
    """懒初始化 client；首次调用时自动建桶，失败则标记降级。"""
    global _client, _enabled
    if _client is not None:
        return _client
    if not _HAVE_MINIO:
        _enabled = False
        return None
    try:
        _client = Minio(
            _ENDPOINT,
            access_key=_ACCESS_KEY,
            secret_key=_SECRET_KEY,
            secure=False,
        )
        # 自动建桶（若不存在），幂等
        if not _client.bucket_exists(DEFAULT_BUCKET):
            _client.make_bucket(DEFAULT_BUCKET)
        _enabled = True
        logger.info(f"[ObjectStore] 已连接 minio {_ENDPOINT} 桶={DEFAULT_BUCKET}")
    except Exception as e:
        logger.warning(f"[ObjectStore] minio 不可用，退回本地存储: {e}")
        _enabled = False
        _client = None
    return _client


def put_object(key: str, data: bytes,
               content_type: str = "application/octet-stream") -> bool:
    """存对象。成功 True；minio 不可用 / 失败 False（调用方自行退回本地）。"""
    client = _get_client()
    if client is None:
        return False
    try:
        client.put_object(
            DEFAULT_BUCKET, key, io.BytesIO(data),
            length=len(data), content_type=content_type,
        )
        return True
    except Exception as e:
        logger.warning(f"[ObjectStore] put {key} 失败，退回本地: {e}")
        return False


def get_object(key: str) -> Optional[bytes]:
    client = _get_client()
    if client is None:
        return None
    try:
        resp = client.get_object(DEFAULT_BUCKET, key)
        data = resp.read()
        resp.close()
        resp.release_conn()
        return data
    except Exception as e:
        logger.warning(f"[ObjectStore] get {key} 失败: {e}")
        return None


def presigned_get_url(key: str, expires_sec: int = 3600) -> Optional[str]:
    """生成 minio 原生 presigned URL（host 即 MINIO_ENDPOINT，替换 host 会致签名失效）。

    外部下载请走后端代理端点 ``/api/object/{key}``（见 routes/files.py）。
    """
    client = _get_client()
    if client is None:
        return None
    try:
        return client.presigned_get_object(
            DEFAULT_BUCKET, key, expires=timedelta(seconds=expires_sec))
    except Exception as e:
        logger.warning(f"[ObjectStore] presigned {key} 失败: {e}")
        return None


def delete_object(key: str) -> bool:
    client = _get_client()
    if client is None:
        return False
    try:
        client.remove_object(DEFAULT_BUCKET, key)
        return True
    except Exception as e:
        logger.warning(f"[ObjectStore] delete {key} 失败: {e}")
        return False
