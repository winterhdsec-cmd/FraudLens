"""
Redis 连接池管理器
提供高性能 Redis 连接和缓存功能

支持两种拓扑：
  - 直连模式（默认）：连接单个 Redis 节点（REDIS_HOST:REDIS_PORT）。
  - 哨兵模式（HA）：当 REDIS_SENTINEL_HOSTS 非空时，通过 redis-py Sentinel
    自动发现当前 master 并连接，master 故障被哨兵提升后客户端透明重连
    （SentinelConnectionPool 在连接错误时重新发现 master），实现故障转移。
"""
import json
import pickle
from typing import Any, Optional, Dict, List, Tuple
from datetime import datetime, timedelta
from contextlib import contextmanager
from core.logger import logger
from core.config import settings


def _parse_sentinel_hosts(raw: str) -> List[Tuple[str, int]]:
    """把 'h1:26379,h2:26379' 解析成 [(h1,26379),(h2,26379)]。空串返回 []。"""
    hosts: List[Tuple[str, int]] = []
    for part in (raw or "").split(","):
        part = part.strip()
        if not part:
            continue
        if ":" in part:
            h, p = part.rsplit(":", 1)
            hosts.append((h, int(p)))
        else:
            hosts.append((part, 26379))
    return hosts


def _resp2_kw() -> Dict[str, Any]:
    """强制 RESP2 协议（redis-py>=6 默认发 HELLO 3 握手，Redis<6 服务端会直接报
    unknown command 'HELLO'，内置 vendor Redis 5.0.14 即此场景）。

    protocol 参数 redis-py>=5.0 支持；更旧版本忽略未知 kwargs 会报错，故探测一次后缓存。
    """
    global _RESP2_KW
    if _RESP2_KW is not None:
        return _RESP2_KW
    try:
        import inspect
        import redis as _redis
        sig = inspect.signature(_redis.Redis.__init__)
        _RESP2_KW = {"protocol": 2} if "protocol" in sig.parameters else {}
    except Exception:
        _RESP2_KW = {}
    return _RESP2_KW


_RESP2_KW: Optional[Dict[str, Any]] = None


def get_redis_client(
    decode_responses: bool = True,
    socket_timeout: float = 2.0,
    sentinel_hosts: Optional[List[Tuple[str, int]]] = None,
    service_name: Optional[str] = None,
) -> "redis.Redis":
    """返回哨兵感知（或直连）的 redis.Redis 客户端 —— 全栈统一入口。

    - 若传入 sentinel_hosts 或环境变量 REDIS_SENTINEL_HOSTS 非空 → 哨兵模式，
      通过 Sentinel.master_for() 拿到始终指向当前 master 的客户端（透明故障转移）。
    - 否则 → 直连 REDIS_HOST:REDIS_PORT。
    调用方负责 ping / 异常处理（哨兵不可达时由调用方决定降级策略）。
    """
    import redis  # 局部导入，避免对无 redis 的环境造成导入期硬依赖
    hosts = sentinel_hosts if sentinel_hosts is not None else _parse_sentinel_hosts(
        getattr(settings, "REDIS_SENTINEL_HOSTS", "")
    )
    if hosts:
        svc = service_name or getattr(settings, "REDIS_SENTINEL_SERVICE_NAME", "mymaster")
        sentinel = redis.sentinel.Sentinel(
            hosts,
            socket_timeout=socket_timeout,
            socket_connect_timeout=socket_timeout,
            password=settings.REDIS_PASSWORD,
        )
        client = sentinel.master_for(
            svc,
            db=settings.REDIS_DB,
            password=settings.REDIS_PASSWORD,
            socket_timeout=socket_timeout,
            socket_connect_timeout=socket_timeout,
            decode_responses=decode_responses,
            **_resp2_kw(),
        )
        logger.info("Redis client in SENTINEL mode", sentinels=hosts, service=svc)
        return client
    # 直连模式：本机内置 Redis 已拉起时，连接必然成功，收紧超时至亚秒，
    # 避免全链路在"未配置 Redis"场景下反复吃 2s TCP 超时（原来拖慢启动 ~2min）。
    embedded = False
    try:
        from core.redis_embedded import embedded_redis_active
        embedded = embedded_redis_active()
    except Exception:
        pass
    socket_connect_timeout = socket_timeout
    if embedded and not (settings.REDIS_SENTINEL_HOSTS or ""):
        socket_connect_timeout = 0.5
        socket_timeout = min(socket_timeout, 1.0)
    client = redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=settings.REDIS_DB,
        password=settings.REDIS_PASSWORD or None,
        socket_timeout=socket_timeout,
        socket_connect_timeout=socket_connect_timeout,
        decode_responses=decode_responses,
        **_resp2_kw(),
    )
    logger.info("Redis client in DIRECT mode", host=settings.REDIS_HOST, port=settings.REDIS_PORT, embedded=embedded)
    return client


class RedisPool:
    """Redis 连接池管理器"""
    
    def __init__(
        self,
        host: str = None,
        port: int = None,
        db: int = None,
        password: str = None,
        max_connections: int = 20,
        decode_responses: bool = True,
        socket_timeout: float = 2.0,
        sentinel_hosts: Optional[List[Tuple[str, int]]] = None,
        sentinel_service_name: Optional[str] = None
    ):
        """
        初始化 Redis 连接池
        
        Args:
            host: Redis 主机
            port: Redis 端口
            db: Redis 数据库编号
            password: Redis 密码
            max_connections: 最大连接数
            decode_responses: 是否自动解码响应
            socket_timeout: 套接字超时（秒）
            sentinel_hosts: 哨兵地址列表；为 None 时按环境变量 REDIS_SENTINEL_HOSTS 自动判断
            sentinel_service_name: 哨兵监控的 master 服务名（默认 mymaster）
        """
        self.host = host or settings.REDIS_HOST
        self.port = port or settings.REDIS_PORT
        self.db = db or settings.REDIS_DB
        self.password = password or settings.REDIS_PASSWORD
        self.max_connections = max_connections
        self.decode_responses = decode_responses
        self.socket_timeout = socket_timeout
        
        # 哨兵模式：优先用哨兵发现主节点，实现透明故障转移
        if sentinel_hosts is None:
            env_hosts = getattr(settings, "REDIS_SENTINEL_HOSTS", "")
            sentinel_hosts = _parse_sentinel_hosts(env_hosts) if env_hosts else None
        self.sentinel_hosts = list(sentinel_hosts) if sentinel_hosts else []
        self.sentinel_service_name = sentinel_service_name or getattr(
            settings, "REDIS_SENTINEL_SERVICE_NAME", "mymaster"
        )
        self.is_sentinel = bool(self.sentinel_hosts)
        
        self._sentinel = None
        self._pool = None
        self._client = None
        
        logger.info(
            "RedisPool initialized",
            host=self.host,
            port=self.port,
            db=self.db,
            max_connections=self.max_connections,
            sentinel_mode=self.is_sentinel,
            sentinel_hosts=self.sentinel_hosts,
            sentinel_service_name=self.sentinel_service_name
        )
    
    def _get_pool(self):
        """获取连接池（哨兵模式返回 SentinelConnectionPool，连接错误自动重发现 master）"""
        if self._pool is None:
            try:
                import redis
                if self.is_sentinel:
                    self._sentinel = redis.sentinel.Sentinel(
                        self.sentinel_hosts,
                        socket_timeout=self.socket_timeout,
                        socket_connect_timeout=self.socket_timeout,
                        password=self.password,
                    )
                    master = self._sentinel.master_for(
                        self.sentinel_service_name,
                        db=self.db,
                        password=self.password,
                        socket_timeout=self.socket_timeout,
                        socket_connect_timeout=self.socket_timeout,
                        decode_responses=self.decode_responses,
                        max_connections=self.max_connections,
                        **_resp2_kw(),
                    )
                    self._pool = master.connection_pool
                    logger.info(
                        "Redis Sentinel connection pool created",
                        service=self.sentinel_service_name,
                        sentinels=self.sentinel_hosts
                    )
                else:
                    self._pool = redis.ConnectionPool(
                        host=self.host,
                        port=self.port,
                        db=self.db,
                        password=self.password,
                        max_connections=self.max_connections,
                        decode_responses=self.decode_responses,
                        socket_timeout=self.socket_timeout,
                        socket_connect_timeout=self.socket_timeout,
                        retry_on_timeout=False,
                        **_resp2_kw(),
                    )
                    logger.info("Redis connection pool created")
            except ImportError:
                logger.error("redis package not installed")
                raise
            except Exception as e:
                logger.error("Failed to create Redis pool", error=str(e))
                raise
        return self._pool
    
    @contextmanager
    def get_client(self):
        """获取 Redis 客户端（上下文管理器）"""
        pool = self._get_pool()
        client = None
        try:
            import redis
            client = redis.Redis(connection_pool=pool)
            # 测试连接
            client.ping()
            yield client
        except Exception as e:
            logger.error("Redis connection failed", error=str(e))
            raise
        finally:
            if client:
                client.close()
    
    def set(self, key: str, value: Any, expire: int = None) -> bool:
        """
        设置键值
        
        Args:
            key: 键
            value: 值（支持任意 Python 对象）
            expire: 过期时间（秒）
        
        Returns:
            是否成功
        """
        try:
            with self.get_client() as client:
                # 序列化值
                if isinstance(value, (str, int, float, bool)):
                    serialized = value
                else:
                    serialized = pickle.dumps(value)
                
                if expire:
                    return client.setex(key, expire, serialized)
                else:
                    return client.set(key, serialized)
        except Exception as e:
            logger.error("Redis set failed", key=key, error=str(e))
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取值
        
        Args:
            key: 键
            default: 默认值
        
        Returns:
            值
        """
        try:
            with self.get_client() as client:
                value = client.get(key)
                if value is None:
                    return default
                
                # 尝试反序列化
                try:
                    return pickle.loads(value)
                except:
                    return value
        except Exception as e:
            logger.error("Redis get failed", key=key, error=str(e))
            return default
    
    def delete(self, key: str) -> bool:
        """删除键"""
        try:
            with self.get_client() as client:
                return client.delete(key) > 0
        except Exception as e:
            logger.error("Redis delete failed", key=key, error=str(e))
            return False
    
    def exists(self, key: str) -> bool:
        """检查键是否存在"""
        try:
            with self.get_client() as client:
                return client.exists(key) > 0
        except Exception as e:
            logger.error("Redis exists failed", key=key, error=str(e))
            return False
    
    def expire(self, key: str, seconds: int) -> bool:
        """设置过期时间"""
        try:
            with self.get_client() as client:
                return client.expire(key, seconds)
        except Exception as e:
            logger.error("Redis expire failed", key=key, error=str(e))
            return False
    
    def incr(self, key: str, amount: int = 1) -> Optional[int]:
        """原子递增"""
        try:
            with self.get_client() as client:
                return client.incr(key, amount)
        except Exception as e:
            logger.error("Redis incr failed", key=key, error=str(e))
            return None
    
    def decr(self, key: str, amount: int = 1) -> Optional[int]:
        """原子递减"""
        try:
            with self.get_client() as client:
                return client.decr(key, amount)
        except Exception as e:
            logger.error("Redis decr failed", key=key, error=str(e))
            return None
    
    def hset(self, name: str, key: str, value: Any) -> bool:
        """设置哈希字段"""
        try:
            with self.get_client() as client:
                serialized = pickle.dumps(value) if not isinstance(value, str) else value
                return client.hset(name, key, serialized) >= 0
        except Exception as e:
            logger.error("Redis hset failed", name=name, key=key, error=str(e))
            return False
    
    def hget(self, name: str, key: str, default: Any = None) -> Any:
        """获取哈希字段"""
        try:
            with self.get_client() as client:
                value = client.hget(name, key)
                if value is None:
                    return default
                try:
                    return pickle.loads(value)
                except:
                    return value
        except Exception as e:
            logger.error("Redis hget failed", name=name, key=key, error=str(e))
            return default
    
    def hgetall(self, name: str) -> Dict[str, Any]:
        """获取哈希所有字段"""
        try:
            with self.get_client() as client:
                data = client.hgetall(name)
                result = {}
                for k, v in data.items():
                    try:
                        result[k] = pickle.loads(v)
                    except:
                        result[k] = v
                return result
        except Exception as e:
            logger.error("Redis hgetall failed", name=name, error=str(e))
            return {}
    
    def lpush(self, name: str, *values) -> Optional[int]:
        """列表左推入"""
        try:
            with self.get_client() as client:
                serialized = [pickle.dumps(v) if not isinstance(v, str) else v for v in values]
                return client.lpush(name, *serialized)
        except Exception as e:
            logger.error("Redis lpush failed", name=name, error=str(e))
            return None
    
    def rpush(self, name: str, *values) -> Optional[int]:
        """列表右推入"""
        try:
            with self.get_client() as client:
                serialized = [pickle.dumps(v) if not isinstance(v, str) else v for v in values]
                return client.rpush(name, *serialized)
        except Exception as e:
            logger.error("Redis rpush failed", name=name, error=str(e))
            return None
    
    def lrange(self, name: str, start: int, end: int) -> List[Any]:
        """获取列表范围"""
        try:
            with self.get_client() as client:
                values = client.lrange(name, start, end)
                result = []
                for v in values:
                    try:
                        result.append(pickle.loads(v))
                    except:
                        result.append(v)
                return result
        except Exception as e:
            logger.error("Redis lrange failed", name=name, error=str(e))
            return []
    
    def sadd(self, name: str, *values) -> Optional[int]:
        """集合添加元素"""
        try:
            with self.get_client() as client:
                serialized = [pickle.dumps(v) if not isinstance(v, str) else v for v in values]
                return client.sadd(name, *serialized)
        except Exception as e:
            logger.error("Redis sadd failed", name=name, error=str(e))
            return None
    
    def smembers(self, name: str) -> set:
        """获取集合所有成员"""
        try:
            with self.get_client() as client:
                values = client.smembers(name)
                result = set()
                for v in values:
                    try:
                        result.add(pickle.loads(v))
                    except:
                        result.add(v)
                return result
        except Exception as e:
            logger.error("Redis smembers failed", name=name, error=str(e))
            return set()
    
    def flushdb(self) -> bool:
        """清空当前数据库"""
        try:
            with self.get_client() as client:
                return client.flushdb()
        except Exception as e:
            logger.error("Redis flushdb failed", error=str(e))
            return False
    
    def info(self) -> Dict:
        """获取 Redis 信息"""
        try:
            with self.get_client() as client:
                return client.info()
        except Exception as e:
            logger.error("Redis info failed", error=str(e))
            return {}
    
    def ping(self) -> bool:
        """测试连接"""
        try:
            with self.get_client() as client:
                return client.ping()
        except Exception as e:
            logger.error("Redis ping failed", error=str(e))
            return False


class RedisCache:
    """Redis 缓存管理器"""
    
    def __init__(self, redis_pool: RedisPool, default_ttl: int = 3600):
        """
        初始化缓存管理器
        
        Args:
            redis_pool: Redis 连接池
            default_ttl: 默认缓存时间（秒）
        """
        self.redis = redis_pool
        self.default_ttl = default_ttl
        
        logger.info("RedisCache initialized", default_ttl=default_ttl)
    
    def get_or_set(self, key: str, func, ttl: int = None, *args, **kwargs) -> Any:
        """
        获取或设置缓存
        
        Args:
            key: 缓存键
            func: 生成值的函数
            ttl: 缓存时间（秒）
            *args, **kwargs: 传递给 func 的参数
        
        Returns:
            缓存值或新生成的值
        """
        # 尝试从缓存获取
        cached = self.redis.get(key)
        if cached is not None:
            logger.debug("Cache hit", key=key)
            return cached
        
        # 生成新值
        logger.debug("Cache miss", key=key)
        value = func(*args, **kwargs)
        
        # 设置缓存
        ttl = ttl or self.default_ttl
        self.redis.set(key, value, expire=ttl)
        
        return value
    
    def invalidate(self, pattern: str) -> int:
        """
        使缓存失效
        
        Args:
            pattern: 键模式（支持通配符）
        
        Returns:
            删除的键数量
        """
        try:
            with self.redis.get_client() as client:
                keys = client.keys(pattern)
                if keys:
                    return client.delete(*keys)
                return 0
        except Exception as e:
            logger.error("Cache invalidate failed", pattern=pattern, error=str(e))
            return 0
    
    def clear_all(self) -> bool:
        """清空所有缓存"""
        return self.redis.flushdb()


# 全局 Redis 连接池实例
_redis_pool: Optional[RedisPool] = None
_redis_cache: Optional[RedisCache] = None


def get_redis_pool() -> Optional[RedisPool]:
    """获取 Redis 连接池"""
    global _redis_pool
    
    if _redis_pool is not None:
        return _redis_pool
    
    # 检查 Redis 是否配置。历史上 localhost 被直接视为「未配置」而永久降级内存；
    # 接入内置 Redis（core.redis_embedded）后，本机地址同样可能是真实可用实例，
    # 改为探测式判断：端口上有 Redis 响应才建池，否则按原行为内存兜底。
    if not settings.REDIS_HOST:
        logger.warning("Redis not configured, using in-memory storage")
        return None
    if settings.REDIS_HOST == "localhost" and not getattr(settings, "REDIS_SENTINEL_HOSTS", ""):
        try:
            from core.redis_embedded import ping_ok
            if not ping_ok("127.0.0.1", int(settings.REDIS_PORT), timeout=0.4):
                logger.warning("Redis not configured (no local instance answering), using in-memory storage")
                return None
        except Exception:
            logger.warning("Redis not configured, using in-memory storage")
            return None
    
    try:
        _redis_pool = RedisPool()
        # 哨兵模式：master 可能尚未就绪（启动竞态），交给 Sentinel 客户端惰性重连，
        # 不在此处因一次性 ping 失败就永久降级为内存存储。
        if _redis_pool.is_sentinel:
            logger.info("Redis(Sentinel) pool created, lazy-connect on first use")
            return _redis_pool
        if _redis_pool.ping():
            logger.info("Redis connection successful")
            return _redis_pool
        else:
            logger.warning("Redis ping failed, using in-memory storage")
            _redis_pool = None
            return None
    except Exception as e:
        logger.warning("Redis not available, using in-memory storage", error=str(e))
        _redis_pool = None
        return None


def get_redis_cache() -> Optional[RedisCache]:
    """获取 Redis 缓存管理器"""
    global _redis_cache
    
    if _redis_cache is not None:
        return _redis_cache
    
    pool = get_redis_pool()
    if pool is None:
        return None
    
    _redis_cache = RedisCache(pool)
    return _redis_cache


def reset_redis():
    """重置 Redis 连接（用于测试）"""
    global _redis_pool, _redis_cache
    _redis_pool = None
    _redis_cache = None
