"""
健康检查和监控指标模块
提供系统状态监控和性能指标收集
"""
import time
import asyncio
import psutil
import platform
from typing import Dict, Any, List
from datetime import datetime, timedelta
from collections import defaultdict
from core.logger import logger
from core.config import settings


class HealthChecker:
    """系统健康检查器"""
    
    def __init__(self):
        self.start_time = datetime.utcnow()
        self.checks = {}
        
        logger.info("HealthChecker initialized")
    
    def register_check(self, name: str, check_func):
        """注册健康检查项"""
        self.checks[name] = check_func
        logger.info(f"Health check registered: {name}")
    
    async def check_all(self) -> Dict[str, Any]:
        """执行所有健康检查"""
        results = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "uptime_seconds": (datetime.utcnow() - self.start_time).total_seconds(),
            "checks": {}
        }
        
        for name, check_func in self.checks.items():
            try:
                start = time.time()
                result = await check_func() if asyncio.iscoroutinefunction(check_func) else check_func()
                duration = time.time() - start
                
                results["checks"][name] = {
                    "status": "healthy" if result.get("healthy", True) else "unhealthy",
                    "latency_ms": round(duration * 1000, 2),
                    "details": result
                }
                
                if not result.get("healthy", True):
                    results["status"] = "unhealthy"
                    
            except Exception as e:
                logger.error(f"Health check failed: {name}", error=str(e))
                results["checks"][name] = {
                    "status": "unhealthy",
                    "error": str(e)
                }
                results["status"] = "unhealthy"
        
        return results
    
    def check_database(self) -> Dict[str, Any]:
        """检查数据库连接"""
        try:
            from database import db
            from sqlalchemy import text
            # 执行简单查询测试连接
            db.session.execute(text("SELECT 1"))
            return {"healthy": True, "message": "Database connection OK"}
        except Exception as e:
            return {"healthy": False, "error": str(e)}
    
    def check_redis(self) -> Dict[str, Any]:
        """检查 Redis 连接"""
        try:
            from core.redis_pool import get_redis_pool
            pool = get_redis_pool()
            if pool and pool.ping():
                return {"healthy": True, "message": "Redis connection OK"}
            return {"healthy": False, "message": "Redis not available"}
        except Exception as e:
            return {"healthy": False, "error": str(e)}
    
    def check_disk_space(self) -> Dict[str, Any]:
        """检查磁盘空间"""
        try:
            disk = psutil.disk_usage('/')
            free_gb = disk.free / (1024**3)
            total_gb = disk.total / (1024**3)
            percent = disk.percent
            
            healthy = percent < 90  # 磁盘使用超过 90% 视为不健康
            
            return {
                "healthy": healthy,
                "free_gb": round(free_gb, 2),
                "total_gb": round(total_gb, 2),
                "percent_used": percent
            }
        except Exception as e:
            return {"healthy": False, "error": str(e)}
    
    def check_memory(self) -> Dict[str, Any]:
        """检查内存使用"""
        try:
            memory = psutil.virtual_memory()
            available_gb = memory.available / (1024**3)
            total_gb = memory.total / (1024**3)
            percent = memory.percent
            
            healthy = percent < 90  # 内存使用超过 90% 视为不健康
            
            return {
                "healthy": healthy,
                "available_gb": round(available_gb, 2),
                "total_gb": round(total_gb, 2),
                "percent_used": percent
            }
        except Exception as e:
            return {"healthy": False, "error": str(e)}
    
    def get_system_info(self) -> Dict[str, Any]:
        """获取系统信息"""
        return {
            "platform": platform.system(),
            "platform_release": platform.release(),
            "python_version": platform.python_version(),
            "cpu_count": psutil.cpu_count(logical=True),
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "boot_time": datetime.fromtimestamp(psutil.boot_time()).isoformat()
        }


class MetricsCollector:
    """性能指标收集器"""
    
    def __init__(self):
        self.metrics = defaultdict(lambda: {
            "count": 0,
            "total_time": 0,
            "min_time": float('inf'),
            "max_time": 0,
            "errors": 0
        })
        
        self.request_count = 0
        self.error_count = 0
        self.start_time = time.time()
        
        logger.info("MetricsCollector initialized")
    
    def record_request(self, endpoint: str, duration: float, success: bool = True):
        """记录请求指标"""
        self.request_count += 1
        
        if not success:
            self.error_count += 1
        
        metric = self.metrics[endpoint]
        metric["count"] += 1
        metric["total_time"] += duration
        metric["min_time"] = min(metric["min_time"], duration)
        metric["max_time"] = max(metric["max_time"], duration)
        
        if not success:
            metric["errors"] += 1
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取所有指标"""
        uptime = time.time() - self.start_time
        
        result = {
            "uptime_seconds": round(uptime, 2),
            "total_requests": self.request_count,
            "total_errors": self.error_count,
            "error_rate": round(self.error_count / max(self.request_count, 1) * 100, 2),
            "requests_per_second": round(self.request_count / max(uptime, 1), 2),
            "endpoints": {}
        }
        
        for endpoint, metric in self.metrics.items():
            count = metric["count"]
            avg_time = metric["total_time"] / max(count, 1)
            
            result["endpoints"][endpoint] = {
                "count": count,
                "avg_time_ms": round(avg_time * 1000, 2),
                "min_time_ms": round(metric["min_time"] * 1000, 2) if metric["min_time"] != float('inf') else 0,
                "max_time_ms": round(metric["max_time"] * 1000, 2),
                "errors": metric["errors"],
                "error_rate": round(metric["errors"] / max(count, 1) * 100, 2)
            }
        
        return result
    
    def reset(self):
        """重置所有指标"""
        self.metrics.clear()
        self.request_count = 0
        self.error_count = 0
        self.start_time = time.time()
        
        logger.info("Metrics reset")


# 全局实例
_health_checker: HealthChecker = None
_metrics_collector: MetricsCollector = None


def get_health_checker() -> HealthChecker:
    """获取健康检查器"""
    global _health_checker
    if _health_checker is None:
        _health_checker = HealthChecker()
        # 注册默认检查项
        _health_checker.register_check("database", _health_checker.check_database)
        _health_checker.register_check("redis", _health_checker.check_redis)
        _health_checker.register_check("disk", _health_checker.check_disk_space)
        _health_checker.register_check("memory", _health_checker.check_memory)
    return _health_checker


def get_metrics_collector() -> MetricsCollector:
    """获取指标收集器"""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


def reset_health_checker():
    """重置健康检查器（用于测试）"""
    global _health_checker
    _health_checker = None


def reset_metrics_collector():
    """重置指标收集器（用于测试）"""
    global _metrics_collector
    _metrics_collector = None
