"""
Agent任务管理器
支持异步任务执行、状态追踪和结果缓存
"""

import asyncio
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TaskInfo:
    id: str
    status: TaskStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress: float = 0.0
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class AgentTaskManager:
    """Agent任务管理器"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._tasks: Dict[str, TaskInfo] = {}
            cls._instance._results: Dict[str, Any] = {}
            cls._instance._max_tasks = 1000
        return cls._instance
    
    def create_task(self, metadata: Dict[str, Any] = None) -> str:
        """创建新任务"""
        task_id = f"task_{uuid.uuid4().hex[:12]}"
        
        if len(self._tasks) >= self._max_tasks:
            self._cleanup_old_tasks()
        
        self._tasks[task_id] = TaskInfo(
            id=task_id,
            status=TaskStatus.PENDING,
            created_at=datetime.now(),
            metadata=metadata or {}
        )
        
        logger.info(f"Created task: {task_id}")
        return task_id
    
    def start_task(self, task_id: str):
        """标记任务开始"""
        if task_id in self._tasks:
            self._tasks[task_id].status = TaskStatus.RUNNING
            self._tasks[task_id].started_at = datetime.now()
            logger.info(f"Task started: {task_id}")
    
    def update_progress(self, task_id: str, progress: float):
        """更新任务进度"""
        if task_id in self._tasks:
            self._tasks[task_id].progress = min(100.0, max(0.0, progress))
    
    def complete_task(self, task_id: str, result: Dict[str, Any]):
        """标记任务完成"""
        if task_id in self._tasks:
            self._tasks[task_id].status = TaskStatus.COMPLETED
            self._tasks[task_id].completed_at = datetime.now()
            self._tasks[task_id].progress = 100.0
            self._tasks[task_id].result = result
            self._results[task_id] = result
            logger.info(f"Task completed: {task_id}")
    
    def fail_task(self, task_id: str, error: str):
        """标记任务失败"""
        if task_id in self._tasks:
            self._tasks[task_id].status = TaskStatus.FAILED
            self._tasks[task_id].completed_at = datetime.now()
            self._tasks[task_id].error = error
            logger.error(f"Task failed: {task_id}, error: {error}")
    
    def cancel_task(self, task_id: str):
        """取消任务"""
        if task_id in self._tasks:
            self._tasks[task_id].status = TaskStatus.CANCELLED
            self._tasks[task_id].completed_at = datetime.now()
            logger.info(f"Task cancelled: {task_id}")
    
    def get_task(self, task_id: str) -> Optional[TaskInfo]:
        """获取任务信息"""
        return self._tasks.get(task_id)
    
    def get_result(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务结果"""
        return self._results.get(task_id) or self._tasks.get(task_id, {}).get("result")
    
    def get_status(self, task_id: str) -> Optional[TaskStatus]:
        """获取任务状态"""
        task = self._tasks.get(task_id)
        return task.status if task else None
    
    def list_tasks(self, status: TaskStatus = None, limit: int = 50) -> list:
        """列出任务"""
        tasks = list(self._tasks.values())
        
        if status:
            tasks = [t for t in tasks if t.status == status]
        
        tasks.sort(key=lambda x: x.created_at, reverse=True)
        return tasks[:limit]
    
    def _cleanup_old_tasks(self):
        """清理旧任务"""
        completed_ids = [
            tid for tid, task in self._tasks.items()
            if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]
        ]
        
        for tid in completed_ids[:len(completed_ids) // 2]:
            del self._tasks[tid]
            self._results.pop(tid, None)
        
        logger.info(f"Cleaned up {len(completed_ids) // 2} old tasks")
    
    async def execute_async(
        self,
        task_id: str,
        coro: Callable,
        progress_callback: Callable = None,
    ) -> Any:
        """异步执行任务"""
        try:
            self.start_task(task_id)
            
            if progress_callback:
                result = await coro(progress_callback)
            else:
                result = await coro()
            
            self.complete_task(task_id, result)
            return result
            
        except Exception as e:
            self.fail_task(task_id, str(e))
            raise


task_manager = AgentTaskManager()
