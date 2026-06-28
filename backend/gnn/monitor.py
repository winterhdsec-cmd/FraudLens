"""
GNN推理监控模块
收集性能指标、资源使用、错误统计
"""
import time
import threading
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import json


class InferenceMonitor:
    """
    推理监控器
    
    收集指标:
    - 推理耗时 (P50/P90/P99)
    - 内存使用
    - 吞吐量 (QPS)
    - 错误率
    - 降级次数
    - 缓存命中率
    """
    
    def __init__(self, max_history: int = 1000):
        """
        Args:
            max_history: 最大历史记录数
        """
        self.max_history = max_history
        self._lock = threading.Lock()
        
        # 指标存储
        self.metrics_history: List[Dict[str, Any]] = []
        self.counters = defaultdict(int)
        self.timers: Dict[str, List[float]] = defaultdict(list)
        
        # 实时指标
        self.start_time = datetime.now()
        self.total_requests = 0
        self.total_errors = 0
        self.total_fallbacks = 0
        self.total_cache_hits = 0
    
    def record_request(
        self,
        duration: float,
        success: bool = True,
        fallback_used: bool = False,
        cache_hit: bool = False,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        记录一次推理请求
        
        Args:
            duration: 耗时(秒)
            success: 是否成功
            fallback_used: 是否使用降级
            cache_hit: 是否缓存命中
            metadata: 额外元数据
        """
        with self._lock:
            record = {
                'timestamp': datetime.now().isoformat(),
                'duration': duration,
                'success': success,
                'fallback_used': fallback_used,
                'cache_hit': cache_hit,
                'metadata': metadata or {}
            }
            
            self.metrics_history.append(record)
            
            # 限制历史记录数量
            if len(self.metrics_history) > self.max_history:
                self.metrics_history = self.metrics_history[-self.max_history:]
            
            # 更新计数器
            self.total_requests += 1
            if not success:
                self.total_errors += 1
            if fallback_used:
                self.total_fallbacks += 1
            if cache_hit:
                self.total_cache_hits += 1
            
            # 记录耗时分布
            self.timers['inference_time'].append(duration)
            if len(self.timers['inference_time']) > self.max_history:
                self.timers['inference_time'] = self.timers['inference_time'][-self.max_history:]
    
    def get_percentiles(self, timer_name: str) -> Dict[str, float]:
        """
        获取耗时分位数
        
        Args:
            timer_name: 计时器名称
            
        Returns:
            {p50, p90, p99, avg, min, max}
        """
        with self._lock:
            times = self.timers.get(timer_name, [])
            
            if not times:
                return {
                    'p50': 0, 'p90': 0, 'p99': 0,
                    'avg': 0, 'min': 0, 'max': 0, 'count': 0
                }
            
            sorted_times = sorted(times)
            n = len(sorted_times)
            
            return {
                'p50': sorted_times[int(n * 0.5)] if n > 0 else 0,
                'p90': sorted_times[int(n * 0.9)] if n > 0 else 0,
                'p99': sorted_times[int(n * 0.99)] if n > 0 else 0,
                'avg': sum(sorted_times) / n if n > 0 else 0,
                'min': sorted_times[0] if n > 0 else 0,
                'max': sorted_times[-1] if n > 0 else 0,
                'count': n
            }
    
    def get_summary(self, time_window_minutes: int = 60) -> Dict[str, Any]:
        """
        获取监控摘要
        
        Args:
            time_window_minutes: 时间窗口(分钟)
            
        Returns:
            监控摘要
        """
        with self._lock:
            now = datetime.now()
            window_start = now - timedelta(minutes=time_window_minutes)
            
            # 过滤时间窗口内的记录
            recent_records = [
                r for r in self.metrics_history
                if datetime.fromisoformat(r['timestamp']) >= window_start
            ]
            
            # 计算指标
            total = len(recent_records)
            successes = sum(1 for r in recent_records if r['success'])
            errors = total - successes
            fallbacks = sum(1 for r in recent_records if r['fallback_used'])
            cache_hits = sum(1 for r in recent_records if r['cache_hit'])
            
            durations = [r['duration'] for r in recent_records]
            
            # 计算QPS
            uptime_seconds = (now - self.start_time).total_seconds()
            qps = self.total_requests / uptime_seconds if uptime_seconds > 0 else 0
            
            return {
                'uptime_seconds': uptime_seconds,
                'total_requests': self.total_requests,
                'total_errors': self.total_errors,
                'total_fallbacks': self.total_fallbacks,
                'total_cache_hits': self.total_cache_hits,
                'window': {
                    'minutes': time_window_minutes,
                    'total': total,
                    'successes': successes,
                    'errors': errors,
                    'fallbacks': fallbacks,
                    'cache_hits': cache_hits,
                    'success_rate': successes / total if total > 0 else 0,
                    'error_rate': errors / total if total > 0 else 0,
                    'fallback_rate': fallbacks / total if total > 0 else 0,
                    'cache_hit_rate': cache_hits / total if total > 0 else 0
                },
                'latency': self.get_percentiles('inference_time'),
                'qps': qps
            }
    
    def get_recent_errors(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取最近的错误记录
        
        Args:
            limit: 最大返回数量
            
        Returns:
            错误记录列表
        """
        with self._lock:
            errors = [r for r in self.metrics_history if not r['success']]
            return errors[-limit:]
    
    def reset(self):
        """重置所有指标"""
        with self._lock:
            self.metrics_history.clear()
            self.timers.clear()
            self.total_requests = 0
            self.total_errors = 0
            self.total_fallbacks = 0
            self.total_cache_hits = 0
            self.start_time = datetime.now()
    
    def export_metrics(self) -> Dict[str, Any]:
        """
        导出所有指标(用于持久化或传输)
        
        Returns:
            指标字典
        """
        with self._lock:
            return {
                'start_time': self.start_time.isoformat(),
                'total_requests': self.total_requests,
                'total_errors': self.total_errors,
                'total_fallbacks': self.total_fallbacks,
                'total_cache_hits': self.total_cache_hits,
                'metrics_history': self.metrics_history[-100:],  # 最近100条
                'timers': {k: v[-100:] for k, v in self.timers.items()},  # 最近100条
                'counters': dict(self.counters)
            }
    
    def import_metrics(self, data: Dict[str, Any]):
        """
        导入指标(用于恢复)
        
        Args:
            data: 指标数据
        """
        with self._lock:
            self.start_time = datetime.fromisoformat(data.get('start_time', datetime.now().isoformat()))
            self.total_requests = data.get('total_requests', 0)
            self.total_errors = data.get('total_errors', 0)
            self.total_fallbacks = data.get('total_fallbacks', 0)
            self.total_cache_hits = data.get('total_cache_hits', 0)
            self.metrics_history = data.get('metrics_history', [])
            self.timers = {k: v for k, v in data.get('timers', {}).items()}
            self.counters = defaultdict(int, data.get('counters', {}))


# 全局单例
_monitor: Optional[InferenceMonitor] = None


def get_monitor() -> InferenceMonitor:
    """获取全局监控器"""
    global _monitor
    if not _monitor:
        _monitor = InferenceMonitor()
    return _monitor


class InferenceTimer:
    """
    推理计时器上下文管理器
    
    用法:
        with InferenceTimer() as timer:
            # 执行推理
            result = detector.detect(cases)
        
        # 自动记录到监控器
    """
    
    def __init__(self, monitor: Optional[InferenceMonitor] = None):
        self.monitor = monitor or get_monitor()
        self.start_time = None
        self.duration = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.duration = time.time() - self.start_time
        
        # 记录到监控器
        success = exc_type is None
        self.monitor.record_request(
            duration=self.duration,
            success=success,
            fallback_used=False,  # 需要外部设置
            cache_hit=False  # 需要外部设置
        )
        
        return False  # 不吞掉异常
