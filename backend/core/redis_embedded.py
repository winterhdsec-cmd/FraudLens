"""
FraudLens — 内置 Redis 服务管理器（零依赖启动 / 分级自适应降级）

定位：把 Redis 作为「项目自带能力」而不是外部环境依赖。
- 本机已有 Redis（Docker / Windows 服务 / 手工进程）在监听 → 直接复用，绝不重复拉起；
- 端口空闲且仓库内置了 vendor/redis/redis-server.exe（Windows 便携版，BSD-3）→ 以后端子进程
  方式自动拉起，退出时 SHUTDOWN SAVE 落盘，缓存跨后端重启常驻（消除 dashboard 冷算）；
- 非 Windows / 未随仓分发二进制 / 端口被非 Redis 占用 → 安静跳过，调用链走既有的
  core.redis_pool 内存兜底，主流程零影响。

设计约束（与 redis_pool.py 一致的降级哲学）：
- 绝不因 Redis 缺失阻断启动；本模块任何异常只记 WARNING。
- 开关：环境变量 REDIS_AUTOSTART=1 显式启用（默认 0，保持现状）；
  哨兵模式（REDIS_SENTINEL_HOSTS 非空）或远程 REDIS_HOST 下自动禁用，避免误拉本地进程。
"""
import atexit
import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

_VENDOR_DIR = Path(__file__).resolve().parent.parent / "vendor" / "redis"
_SERVER_EXE = _VENDOR_DIR / "redis-server.exe"
_CLI_EXE = _VENDOR_DIR / "redis-cli.exe"
_RUNTIME_DIR = _VENDOR_DIR / "runtime"

_embedded_proc: Optional[subprocess.Popen] = None
_embedded_active = False   # 本进程是否成功拉起了嵌入 Redis（供 redis_pool 例外判断）


def embedded_redis_active() -> bool:
    """当前进程是否拉起了内置 Redis。"""
    return _embedded_active


def _log(msg: str, level: str = "info") -> None:
    try:
        from core.logger import logger
        getattr(logger, level)(msg)
    except Exception:
        print(f"[redis_embedded][{level.upper()}] {msg}")


def port_probe(host: str, port: int, timeout: float = 0.4) -> str:
    """返回 'redis'（PING→PONG）/ 'open'（占用但非 Redis）/ 'free'。"""
    try:
        with socket.create_connection((host, port), timeout=timeout) as s:
            s.settimeout(timeout)
            try:
                s.sendall(b"PING\r\n")
                data = s.recv(64)
                return "redis" if b"PONG" in data else "open"
            except (socket.timeout, OSError):
                return "open"
    except OSError:
        return "free"


def ping_ok(host: str, port: int, timeout: float = 0.6) -> bool:
    return port_probe(host, port, timeout) == "redis"


def _wait_ready(host: str, port: int, deadline_s: float = 8.0) -> bool:
    end = time.time() + deadline_s
    while time.time() < end:
        if ping_ok(host, port):
            return True
        # 进程若已退出则提前失败
        if _embedded_proc is not None and _embedded_proc.poll() is not None:
            return False
        time.sleep(0.25)
    return False


def _shutdown_embedded() -> None:
    """尽力优雅退出：先发 SHUTDOWN SAVE（保留缓存跨重启，纯 redis-py，不依赖 redis-cli.exe），
    失败再 terminate 兜底。"""
    global _embedded_proc
    proc = _embedded_proc
    if proc is None or proc.poll() is not None:
        return
    # 优雅 SHUTDOWN：走已安装的 redis-py 客户端（比 redis-cli.exe 更可靠）
    try:
        port = int(os.getenv("REDIS_PORT", "6379"))
        import redis as _redis
        _redis.Redis(host="127.0.0.1", port=port, protocol=2, socket_timeout=1.0).shutdown(save=True)
    except Exception:
        # shutdown 会主动断连，client 侧常抛 ConnectionError，属正常
        pass
    try:
        proc.wait(timeout=3)
        return
    except Exception:
        pass
    try:
        proc.terminate()
        proc.wait(timeout=2)
    except Exception:
        pass


def ensure_embedded_redis() -> bool:
    """幂等入口：确保本机 Redis 可用（复用外部 / 拉起内置）。返回当前是否有 Redis 可用。

    只应由进程启动路径（main.py）调用一次；内部注册 atexit 负责子进程清理。
    """
    global _embedded_proc, _embedded_active

    if os.getenv("REDIS_AUTOSTART", "0") != "1":
        return ping_ok(os.getenv("REDIS_HOST", "localhost"), int(os.getenv("REDIS_PORT", "6379")))

    # 哨兵/集群/远程场景：绝不拉起本地嵌入进程
    if os.getenv("REDIS_SENTINEL_HOSTS", "").strip():
        return False
    if sys.platform != "win32":
        # Linux/容器环境交给 docker-compose 与系统服务，二进制亦不可用
        return False
    host = os.getenv("REDIS_HOST", "localhost")
    if host not in ("localhost", "127.0.0.1", "0.0.0.0"):
        return False
    try:
        port = int(os.getenv("REDIS_PORT", "6379"))
    except ValueError:
        port = 6379

    probe = port_probe(host if host != "0.0.0.0" else "127.0.0.1", port)
    if probe == "redis":
        _log("内置 Redis：检测到本机已有 Redis 在监听，直接复用外部实例")
        return True
    if probe == "open":
        _log(f"内置 Redis：端口 {port} 被非 Redis 进程占用，跳过自动拉起（走内存兜底）", "warning")
        return False

    if not _SERVER_EXE.exists():
        _log(f"内置 Redis：未随仓分发二进制（{_SERVER_EXE} 缺失），跳过", "warning")
        return False

    # 准备运行时目录（dump.rdb 落盘处）
    try:
        _RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        _log(f"内置 Redis：运行目录创建失败 {e}，跳过", "warning")
        return False

    args = [
        str(_SERVER_EXE),
        "--port", str(port),
        "--bind", "127.0.0.1",
        "--dir", str(_RUNTIME_DIR),
        "--maxmemory", os.getenv("REDIS_EMBEDDED_MAXMEM", "256mb"),
        "--maxmemory-policy", "allkeys-lru",
        "--logfile", str(_RUNTIME_DIR / "redis-embedded.log"),
        "--appendonly", "no",
    ]
    try:
        flags = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NO_WINDOW", 0)
        _embedded_proc = subprocess.Popen(
            args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            creationflags=flags,
            cwd=str(_VENDOR_DIR),
        )
    except OSError as e:
        _log(f"内置 Redis：进程拉起失败 {e}（走内存兜底）", "warning")
        _embedded_proc = None
        return False

    if _wait_ready("127.0.0.1", port):
        _embedded_active = True
        atexit.register(_shutdown_embedded)
        _log(
            f"内置 Redis 已自动拉起：pid={_embedded_proc.pid} port={port} "
            f"数据目录={_RUNTIME_DIR}（退出时 SHUTDOWN SAVE，缓存跨重启常驻）"
        )
        return True

    # 启动失败：清理残进程，安静降级
    _shutdown_embedded()
    _embedded_proc = None
    logf = _RUNTIME_DIR / "redis-embedded.log"
    tail = ""
    try:
        if logf.exists():
            tail = logf.read_text(encoding="utf-8", errors="replace")[-200:]
    except Exception:
        pass
    _log(f"内置 Redis：启动后 ping 超时，已回收进程（走内存兜底）。日志尾：{tail}", "warning")
    return False
