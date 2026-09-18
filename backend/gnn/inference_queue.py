"""
GNN异步推理队列
支持后台处理、进度推送、并发控制
"""
import asyncio
import threading
import time
import uuid
from enum import Enum
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, field
from datetime import datetime
import json


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class InferenceTask:
    """推理任务"""
    task_id: str
    cases: List[Dict[str, Any]]
    use_gnn: bool = True
    training_epochs: int = 100
    incremental: bool = False
    
    # 状态
    status: TaskStatus = TaskStatus.PENDING
    progress: float = 0.0
    stage: str = ""
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    
    # 时间戳
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # 进度回调
    progress_callbacks: List[Callable] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "status": self.status.value,
            "progress": self.progress,
            "stage": self.stage,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error": self.error,
            "result_summary": {
                "gang_count": len(self.result.get("gangs", [])) if self.result else 0,
                "metrics": self.result.get("metrics", {}) if self.result else {}
            } if self.status == TaskStatus.COMPLETED else None
        }


class InferenceQueue:
    """
    推理队列管理器
    
    特性:
    - 异步任务提交
    - 后台线程处理
    - 进度实时推送
    - 并发控制(单例执行,避免资源竞争)
    - 任务状态查询
    """
    
    def __init__(self, max_concurrent: int = 1):
        """
        Args:
            max_concurrent: 最大并发任务数(默认1,避免GPU/CPU资源竞争)
        """
        self.max_concurrent = max_concurrent
        self.tasks: Dict[str, InferenceTask] = {}
        self.task_queue: List[str] = []  # task_id队列
        self._lock = threading.Lock()
        self._worker_thread: Optional[threading.Thread] = None
        self._running = False
        self._detector = None  # 延迟初始化
        
        # 启动worker
        self._start_worker()
    
    def _start_worker(self):
        """启动后台worker线程"""
        if self._worker_thread and self._worker_thread.is_alive():
            return
        
        self._running = True
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker_thread.start()
    
    def _worker_loop(self):
        """Worker主循环"""
        while self._running:
            task_id = None
            
            with self._lock:
                if self.task_queue:
                    task_id = self.task_queue.pop(0)
            
            if task_id:
                self._process_task(task_id)
            else:
                time.sleep(0.1)  # 空闲等待
    
    def _process_task(self, task_id: str):
        """处理单个任务"""
        task = self.tasks.get(task_id)
        if not task:
            return
        
        try:
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now()
            
            # 延迟初始化detector
            if not self._detector:
                from .gang_detector import GangDetector
                self._detector = GangDetector()
            
            # 定义进度回调
            def on_progress(stage: str, percent: float):
                task.stage = stage
                task.progress = percent
                # 触发所有回调
                for cb in task.progress_callbacks:
                    try:
                        cb(task.to_dict())
                    except Exception:
                        pass
            
            # 执行检测
            result = self._detector.detect(
                cases=task.cases,
                use_gnn=task.use_gnn,
                training_epochs=task.training_epochs,
                incremental=task.incremental,
                progress_callback=on_progress
            )
            
            task.result = result
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()
            task.progress = 1.0
            task.stage = "done"
            
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            task.completed_at = datetime.now()
    
    def submit(
        self,
        cases: List[Dict[str, Any]],
        use_gnn: bool = True,
        training_epochs: int = 100,
        incremental: bool = False,
        progress_callback: Optional[Callable] = None
    ) -> str:
        """
        提交推理任务
        
        Returns:
            task_id: 任务ID
        """
        task_id = str(uuid.uuid4())
        
        task = InferenceTask(
            task_id=task_id,
            cases=cases,
            use_gnn=use_gnn,
            training_epochs=training_epochs,
            incremental=incremental
        )
        
        if progress_callback:
            task.progress_callbacks.append(progress_callback)
        
        with self._lock:
            self.tasks[task_id] = task
            self.task_queue.append(task_id)
        
        return task_id
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """查询任务状态"""
        task = self.tasks.get(task_id)
        return task.to_dict() if task else None
    
    def get_result(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务结果"""
        task = self.tasks.get(task_id)
        if task and task.status == TaskStatus.COMPLETED:
            return task.result
        return None
    
    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        task = self.tasks.get(task_id)
        if not task:
            return False
        
        if task.status in [TaskStatus.PENDING, TaskStatus.RUNNING]:
            task.status = TaskStatus.CANCELLED
            task.completed_at = datetime.now()
            return True
        return False
    
    def list_tasks(self, status: Optional[TaskStatus] = None) -> List[Dict[str, Any]]:
        """列出所有任务"""
        tasks = list(self.tasks.values())
        if status:
            tasks = [t for t in tasks if t.status == status]
        return [t.to_dict() for t in tasks]
    
    def cleanup(self, max_age_hours: int = 24):
        """清理过期任务"""
        now = datetime.now()
        to_remove = []
        
        for task_id, task in self.tasks.items():
            if task.completed_at:
                age_hours = (now - task.completed_at).total_seconds() / 3600
                if age_hours > max_age_hours:
                    to_remove.append(task_id)
        
        with self._lock:
            for task_id in to_remove:
                del self.tasks[task_id]
        
        return len(to_remove)
    
    def shutdown(self):
        """关闭队列"""
        self._running = False
        if self._worker_thread:
            self._worker_thread.join(timeout=5)


# 全局单例
_queue: Optional[InferenceQueue] = None


def get_inference_queue() -> InferenceQueue:
    """获取全局推理队列"""
    global _queue
    if not _queue:
        _queue = InferenceQueue(max_concurrent=1)
    return _queue
