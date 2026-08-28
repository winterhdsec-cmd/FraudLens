"""
限流器 - 防止 DDoS 攻击和 API 滥用
支持多种限流策略:固定窗口、滑动窗口、令牌桶
"""
import time
import hashlib
from typing import Optional, Dict, Tuple
from collections import defaultdict
from core.logger import logger
from core.config import settings


class RateLimiter:
    """限流器基类"""
    
    def is_allowed(self, key: str) -> Tuple[bool, Dict]:
        """检查是否允许请求"""
        raise NotImplementedError
    
    def get_remaining(self, key: str) -> int:
        """获取剩余配额"""
        raise NotImplementedError


class FixedWindowRateLimiter(RateLimiter):
    """固定窗口限流器"""
    
    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = defaultdict(list)
        
        logger.info(
            "FixedWindowRateLimiter initialized",
            max_requests=max_requests,
            window_seconds=window_seconds
        )
    
    def is_allowed(self, key: str) -> Tuple[bool, Dict]:
        """检查是否允许请求"""
        now = time.time()
        window_start = now - self.window_seconds
        
        # 清理过期请求
        self.requests[key] = [t for t in self.requests[key] if t > window_start]
        
        # 检查是否超限
        if len(self.requests[key]) >= self.max_requests:
            logger.warning(
                "Rate limit exceeded",
                key=key,
                requests=len(self.requests[key]),
                max_requests=self.max_requests
            )
            return False, {
                "limit": self.max_requests,
                "remaining": 0,
                "reset": int(self.requests[key][0] + self.window_seconds) if self.requests[key] else int(now + self.window_seconds)
            }
        
        # 记录请求
        self.requests[key].append(now)
        
        return True, {
            "limit": self.max_requests,
            "remaining": self.max_requests - len(self.requests[key]),
            "reset": int(now + self.window_seconds)
        }
    
    def get_remaining(self, key: str) -> int:
        """获取剩余配额"""
        now = time.time()
        window_start = now - self.window_seconds
        
        self.requests[key] = [t for t in self.requests[key] if t > window_start]
        
        return max(0, self.max_requests - len(self.requests[key]))


class SlidingWindowRateLimiter(RateLimiter):
    """滑动窗口限流器"""
    
    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = defaultdict(list)
        
        logger.info(
            "SlidingWindowRateLimiter initialized",
            max_requests=max_requests,
            window_seconds=window_seconds
        )
    
    def is_allowed(self, key: str) -> Tuple[bool, Dict]:
        """检查是否允许请求"""
        now = time.time()
        window_start = now - self.window_seconds
        
        # 清理过期请求
        self.requests[key] = [t for t in self.requests[key] if t > window_start]
        
        # 检查是否超限
        if len(self.requests[key]) >= self.max_requests:
            return False, {
                "limit": self.max_requests,
                "remaining": 0,
                "reset": int(self.requests[key][0] + self.window_seconds) if self.requests[key] else int(now + self.window_seconds)
            }
        
        # 记录请求
        self.requests[key].append(now)
        
        return True, {
            "limit": self.max_requests,
            "remaining": self.max_requests - len(self.requests[key]),
            "reset": int(now + self.window_seconds)
        }
    
    def get_remaining(self, key: str) -> int:
        """获取剩余配额"""
        now = time.time()
        window_start = now - self.window_seconds
        
        self.requests[key] = [t for t in self.requests[key] if t > window_start]
        
        return max(0, self.max_requests - len(self.requests[key]))


class TokenBucketRateLimiter(RateLimiter):
    """令牌桶限流器"""
    
    def __init__(self, max_tokens: int = 100, refill_rate: float = 1.0):
        """
        初始化令牌桶
        
        Args:
            max_tokens: 桶最大容量
            refill_rate: 每秒补充令牌数
        """
        self.max_tokens = max_tokens
        self.refill_rate = refill_rate
        self.buckets = {}  # key -> (tokens, last_refill_time)
        
        logger.info(
            "TokenBucketRateLimiter initialized",
            max_tokens=max_tokens,
            refill_rate=refill_rate
        )
    
    def is_allowed(self, key: str) -> Tuple[bool, Dict]:
        """检查是否允许请求"""
        now = time.time()
        
        # 初始化桶
        if key not in self.buckets:
            self.buckets[key] = (self.max_tokens, now)
        
        tokens, last_refill = self.buckets[key]
        
        # 补充令牌
        elapsed = now - last_refill
        tokens = min(self.max_tokens, tokens + elapsed * self.refill_rate)
        
        # 检查是否有令牌
        if tokens < 1:
            return False, {
                "limit": self.max_tokens,
                "remaining": 0,
                "reset": int(now + (1 - tokens) / self.refill_rate)
            }
        
        # 消耗令牌
        tokens -= 1
        self.buckets[key] = (tokens, now)
        
        return True, {
            "limit": self.max_tokens,
            "remaining": int(tokens),
            "reset": int(now + (self.max_tokens - tokens) / self.refill_rate)
        }
    
    def get_remaining(self, key: str) -> int:
        """获取剩余配额"""
        if key not in self.buckets:
            return self.max_tokens
        
        now = time.time()
        tokens, last_refill = self.buckets[key]
        
        elapsed = now - last_refill
        tokens = min(self.max_tokens, tokens + elapsed * self.refill_rate)
        
        return int(tokens)


# 全局限流器实例
_rate_limiters: Dict[str, RateLimiter] = {}


def get_rate_limiter(
    name: str = "default",
    strategy: str = "sliding_window",
    max_requests: int = None,
    window_seconds: int = None
) -> RateLimiter:
    """获取限流器实例"""
    if name in _rate_limiters:
        return _rate_limiters[name]
    
    # 使用配置中的默认值
    if max_requests is None:
        max_requests = settings.RATE_LIMIT_REQUESTS
    if window_seconds is None:
        window_seconds = settings.RATE_LIMIT_WINDOW
    
    # 根据策略创建限流器
    if strategy == "fixed_window":
        limiter = FixedWindowRateLimiter(max_requests, window_seconds)
    elif strategy == "sliding_window":
        limiter = SlidingWindowRateLimiter(max_requests, window_seconds)
    elif strategy == "token_bucket":
        limiter = TokenBucketRateLimiter(max_requests, 1.0)  # 每秒补充1个令牌
    else:
        logger.warning(f"Unknown strategy: {strategy}, using sliding_window")
        limiter = SlidingWindowRateLimiter(max_requests, window_seconds)
    
    _rate_limiters[name] = limiter
    return limiter


def reset_rate_limiters():
    """重置所有限流器(用于测试)"""
    global _rate_limiters
    _rate_limiters = {}
