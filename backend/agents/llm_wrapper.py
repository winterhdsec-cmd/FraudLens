"""
Rate-limited LLM wrapper for FraudLens.
Limits concurrent LLM API calls to avoid throttling.
"""
import threading
import time
import json
import re
from typing import Optional
from core.circuit_breaker import CircuitBreaker, CircuitBreakerOpenError


class MockLLM:
    """当 LLM API Key 未配置时使用的模拟 LLM，返回格式化分析结果"""

    def invoke(self, prompt: str, **kwargs):
        if '团伙' in prompt and '画像' in prompt:
            return json.dumps({
                "gang_name": "智能识别犯罪团伙",
                "characteristics": ["诈骗话术标准化", "资金快速分散转移"],
                "primary_scam_type": "冒充客服/投资理财诈骗",
                "risk_level": "HIGH",
                "description": "AI自动研判识别的犯罪团伙，建议进一步侦查核实。"
            })
        # 案件分析
        return json.dumps({
            "cases": [{
                "case_id": "FC_MOCK_001",
                "scam_type": "冒充客服诈骗",
                "risk_level": "HIGH",
                "victim_name": "待核实受害人",
                "amount": "未知金额",
                "description": "AI模拟分析结果：系统检测到此案件具有诈骗特征，建议人工复核确认。",
                "keywords": ["冒充客服", "转账", "诈骗"],
                "steps": [{"step": "初步接触", "description": "骗子通过电话联系受害人"}]
            }],
            "entities": {"phone_numbers": [], "bank_accounts": []}
        })


class RateLimitedLLM:
    """Thread-safe wrapper that limits concurrent LLM invocations per second and concurrency."""

    def __init__(self, llm, max_concurrent: int = 2, calls_per_second: int = 5, use_circuit_breaker: bool = True):
        self._llm = llm
        self._semaphore = threading.Semaphore(max_concurrent)
        self._call_times = []
        self._lock = threading.Lock()
        self._calls_per_second = calls_per_second
        self._stats = {'total': 0, 'errors': 0, 'total_time_ms': 0}
        
        # 熔断器保护
        self._circuit_breaker = None
        if use_circuit_breaker:
            self._circuit_breaker = CircuitBreaker(
                name="llm_api",
                failure_threshold=5,
                recovery_timeout=60
            )

    def invoke(self, prompt: str, **kwargs):
        with self._semaphore:
            self._rate_limit()
            t0 = time.time()
            try:
                if self._circuit_breaker:
                    result = self._circuit_breaker.call(self._llm.invoke, prompt, **kwargs)
                else:
                    result = self._llm.invoke(prompt, **kwargs)
                
                if hasattr(result, 'content'):
                    result = result.content
                elapsed = int((time.time() - t0) * 1000)
                with self._lock:
                    self._stats['total'] += 1
                    self._stats['total_time_ms'] += elapsed
                return result
            except CircuitBreakerOpenError:
                with self._lock:
                    self._stats['errors'] += 1
                raise
            except Exception as e:
                with self._lock:
                    self._stats['errors'] += 1
                raise

    def _rate_limit(self):
        with self._lock:
            now = time.time()
            self._call_times = [t for t in self._call_times if now - t < 1.0]
            if len(self._call_times) >= self._calls_per_second:
                sleep = 1.0 - (now - self._call_times[0])
                if sleep > 0:
                    time.sleep(sleep)
            self._call_times.append(time.time())

    @property
    def stats(self):
        with self._lock:
            avg = self._stats['total_time_ms'] / max(self._stats['total'], 1)
            return {**self._stats, 'avg_ms': int(avg)}


def wrap_llm(llm, max_concurrent=2):
    """Convenience factory."""
    if llm is None:
        return None
    return RateLimitedLLM(llm, max_concurrent=max_concurrent)