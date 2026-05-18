"""
Rate-limited LLM wrapper for FraudLens.
Limits concurrent LLM API calls to avoid throttling.
"""
import threading
import time
from typing import Optional


class RateLimitedLLM:
    """Thread-safe wrapper that limits concurrent LLM invocations per second and concurrency."""

    def __init__(self, llm, max_concurrent: int = 2, calls_per_second: int = 5):
        self._llm = llm
        self._semaphore = threading.Semaphore(max_concurrent)
        self._call_times = []
        self._lock = threading.Lock()
        self._calls_per_second = calls_per_second
        self._stats = {'total': 0, 'errors': 0, 'total_time_ms': 0}

    def invoke(self, prompt: str, **kwargs):
        with self._semaphore:
            self._rate_limit()
            t0 = time.time()
            try:
                result = self._llm.invoke(prompt, **kwargs)
                elapsed = int((time.time() - t0) * 1000)
                with self._lock:
                    self._stats['total'] += 1
                    self._stats['total_time_ms'] += elapsed
                return result
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