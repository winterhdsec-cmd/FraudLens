"""
熔断器模式 - 防止级联故障
参考：https://martinfowler.com/bliki/CircuitBreaker.html
"""
import time
from enum import Enum
from typing import Callable, Any, Optional
from datetime import datetime, timedelta
from core.logger import logger


class CircuitState(Enum):
    """熔断器状态"""
    CLOSED = "closed"      # 正常状态，允许请求通过
    OPEN = "open"          # 熔断状态，拒绝请求
    HALF_OPEN = "half_open"  # 半开状态，允许少量请求试探


class CircuitBreaker:
    """
    熔断器实现
    
    状态转换：
    - CLOSED -> OPEN: 失败次数达到阈值
    - OPEN -> HALF_OPEN: 超时后自动转换
    - HALF_OPEN -> CLOSED: 试探成功
    - HALF_OPEN -> OPEN: 试探失败
    """
    
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exceptions: tuple = (Exception,)
    ):
        """
        初始化熔断器
        
        Args:
            name: 熔断器名称
            failure_threshold: 失败阈值，达到后触发熔断
            recovery_timeout: 恢复超时（秒），OPEN状态持续时间
            expected_exceptions: 需要捕获的异常类型
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exceptions = expected_exceptions
        
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.success_count = 0
        
        logger.info(
            "Circuit breaker initialized",
            name=name,
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout
        )
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        通过熔断器调用函数
        
        Args:
            func: 要调用的函数
            *args: 位置参数
            **kwargs: 关键字参数
        
        Returns:
            函数返回值
        
        Raises:
            CircuitBreakerOpenError: 熔断器打开时抛出
        """
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                logger.info("Circuit breaker transitioning to HALF_OPEN", name=self.name)
            else:
                raise CircuitBreakerOpenError(
                    f"Circuit breaker {self.name} is OPEN, rejecting request"
                )
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exceptions as e:
            self._on_failure(e)
            raise
    
    async def async_call(self, func: Callable, *args, **kwargs) -> Any:
        """
        异步版本的熔断器调用
        
        Args:
            func: 异步函数
            *args: 位置参数
            **kwargs: 关键字参数
        
        Returns:
            函数返回值
        
        Raises:
            CircuitBreakerOpenError: 熔断器打开时抛出
        """
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                logger.info("Circuit breaker transitioning to HALF_OPEN", name=self.name)
            else:
                raise CircuitBreakerOpenError(
                    f"Circuit breaker {self.name} is OPEN, rejecting request"
                )
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exceptions as e:
            self._on_failure(e)
            raise
    
    def _on_success(self):
        """成功回调"""
        if self.state == CircuitState.HALF_OPEN:
            logger.info(
                "Circuit breaker transitioning to CLOSED",
                name=self.name,
                reason="successful probe"
            )
            self.state = CircuitState.CLOSED
        
        self.failure_count = 0
        self.success_count += 1
    
    def _on_failure(self, exception: Exception):
        """失败回调"""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        
        logger.warning(
            "Circuit breaker failure recorded",
            name=self.name,
            failure_count=self.failure_count,
            exception=str(exception)
        )
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.error(
                "Circuit breaker OPENED",
                name=self.name,
                failure_count=self.failure_count
            )
    
    def _should_attempt_reset(self) -> bool:
        """判断是否应该尝试重置"""
        if self.last_failure_time is None:
            return True
        
        time_since_failure = datetime.utcnow() - self.last_failure_time
        return time_since_failure.total_seconds() >= self.recovery_timeout
    
    def get_state(self) -> dict:
        """获取熔断器状态信息"""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure_time": self.last_failure_time.isoformat() if self.last_failure_time else None
        }
    
    def reset(self):
        """手动重置熔断器"""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        logger.info("Circuit breaker manually reset", name=self.name)


class CircuitBreakerOpenError(Exception):
    """熔断器打开异常"""
    pass


# 全局熔断器注册表
_circuit_breakers: dict[str, CircuitBreaker] = {}


def get_circuit_breaker(name: str, **kwargs) -> CircuitBreaker:
    """获取或创建熔断器"""
    if name not in _circuit_breakers:
        _circuit_breakers[name] = CircuitBreaker(name, **kwargs)
    return _circuit_breakers[name]


def list_circuit_breakers() -> list[dict]:
    """列出所有熔断器状态"""
    return [cb.get_state() for cb in _circuit_breakers.values()]
