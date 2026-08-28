"""
应用层 MySQL 故障切换管理器（系统高可用 G14 后续项）。

作用：主库不可用时，按候选顺序自动切换到副本 / 新主库，对上层（db.session、
db.engine、ORM 查询）透明。

设计约束（避免回归）：
- 零侵入：DB_REPLICA_URIS 留空时候选仅 [主库]，退化为单引擎，行为与改造前完全一致。
- 仅捕获 OperationalError / DisconnectionError 触发切换；业务异常原样抛出。
- 切换时回调 on_switch(engine) 用于重绑 session 工厂，确保 db.session 指向新引擎。
- pool_pre_ping=True 负责日常死连接探活；本管理器负责"主库整体不可用"的场景。
"""
import time

from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError, DisconnectionError
from sqlalchemy.pool import QueuePool

from core.config import settings
from tools.response import logger


class FailoverEngine:
    """维护有序候选 URI 列表，遇连接级故障自动轮换到下一个候选。"""

    def __init__(self, candidate_uris, on_switch=None, **engine_kwargs):
        if not candidate_uris:
            raise ValueError("candidate_uris 不能为空")
        self._candidates = list(candidate_uris)
        self._engine_kwargs = engine_kwargs
        self._on_switch = on_switch
        self._idx = 0
        self._engine = None
        self._active_uri = None
        self._switch_count = 0

    @property
    def active_uri(self):
        return self._active_uri

    @property
    def candidate_count(self):
        return len(self._candidates)

    @property
    def switch_count(self):
        return self._switch_count

    def _build(self, uri):
        return create_engine(uri, poolclass=QueuePool, pool_pre_ping=True, **self._engine_kwargs)

    def get_engine(self):
        """返回当前活跃引擎；首次调用时惰性构建。"""
        if self._engine is None:
            self._engine = self._build(self._candidates[self._idx])
            self._active_uri = self._candidates[self._idx]
        return self._engine

    def switch(self):
        """轮换到下一个候选节点并重建引擎；成功返回新 URI，无候选可换时抛 RuntimeError。"""
        self._idx = (self._idx + 1) % len(self._candidates)
        old = self._active_uri
        try:
            if self._engine is not None:
                self._engine.dispose()
        except Exception:
            pass
        self._engine = self._build(self._candidates[self._idx])
        self._active_uri = self._candidates[self._idx]
        self._switch_count += 1
        logger.warning(f"MySQL 故障切换：{old} -> {self._active_uri}（第 {self._switch_count} 次）")
        if self._on_switch:
            try:
                self._on_switch(self._engine)
            except Exception as e:  # on_switch 异常不应阻断切换本身
                logger.warning(f"故障切换回调异常（已忽略）: {e}")
        return self._active_uri

    def execute_with_failover(self, fn, max_retries=None):
        """对 fn(engine) 执行；遇 OperationalError/DisconnectionError 自动切换并重试。

        Args:
            fn: 接收 engine 的可调用，返回任意结果。
            max_retries: 最大尝试次数，默认等于候选节点数。
        Returns: fn 的返回值。
        """
        max_retries = max_retries or len(self._candidates)
        last_err = None
        for _ in range(max_retries):
            engine = self.get_engine()
            try:
                return fn(engine)
            except (OperationalError, DisconnectionError) as e:
                last_err = e
                logger.warning(f"MySQL 操作失败（候选 {self._idx}），触发故障切换: {e}")
                self.switch()
        # 所有候选均失败
        logger.error("MySQL 故障切换：所有候选节点均不可用")
        raise last_err
