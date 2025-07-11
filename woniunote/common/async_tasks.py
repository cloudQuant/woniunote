#!/usr/bin/env python3
"""
异步任务处理器 - 处理耗时操作
"""

import time
import queue
import threading
import logging
import json
import uuid
from typing import Callable, Any, Dict, Optional, List
from functools import wraps
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, Future
from enum import Enum

logger = logging.getLogger(__name__)

class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class TaskPriority(Enum):
    """任务优先级"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4

class Task:
    """任务对象"""
    
    def __init__(self, task_id: str, func: Callable, args: tuple = (), kwargs: dict = None,
                 priority: TaskPriority = TaskPriority.NORMAL, max_retries: int = 3):
        self.task_id = task_id
        self.func = func
        self.args = args
        self.kwargs = kwargs or {}
        self.priority = priority
        self.max_retries = max_retries
        self.retry_count = 0
        self.status = TaskStatus.PENDING
        self.result = None
        self.error = None
        self.created_at = datetime.now()
        self.started_at = None
        self.completed_at = None
        self.progress = 0
        self.metadata = {}
    
    def __lt__(self, other):
        """用于优先级队列排序"""
        return self.priority.value > other.priority.value
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'task_id': self.task_id,
            'status': self.status.value,
            'priority': self.priority.value,
            'progress': self.progress,
            'retry_count': self.retry_count,
            'max_retries': self.max_retries,
            'created_at': self.created_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'result': self.result,
            'error': str(self.error) if self.error else None,
            'metadata': self.metadata
        }

class TaskExecutor:
    """任务执行器"""
    
    def __init__(self, max_workers: int = 4, queue_size: int = 1000):
        self.max_workers = max_workers
        self.queue_size = queue_size
        self.task_queue = queue.PriorityQueue(maxsize=queue_size)
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.tasks: Dict[str, Task] = {}
        self.futures: Dict[str, Future] = {}
        self.running = False
        self.worker_threads: List[threading.Thread] = []
        self.lock = threading.Lock()
        
        # 统计信息
        self.stats = {
            'total_tasks': 0,
            'completed_tasks': 0,
            'failed_tasks': 0,
            'cancelled_tasks': 0,
            'queue_size': 0,
            'active_workers': 0
        }
    
    def start(self):
        """启动任务执行器"""
        if self.running:
            return
        
        self.running = True
        logger.info(f"Starting task executor with {self.max_workers} workers")
        
        # 启动工作线程
        for i in range(self.max_workers):
            worker = threading.Thread(target=self._worker_loop, name=f"TaskWorker-{i}")
            worker.daemon = True
            worker.start()
            self.worker_threads.append(worker)
    
    def stop(self, timeout: float = 30):
        """停止任务执行器"""
        if not self.running:
            return
        
        logger.info("Stopping task executor...")
        self.running = False
        
        # 等待队列中的任务完成
        try:
            # 向队列添加停止信号
            for _ in range(self.max_workers):
                self.task_queue.put((0, None), timeout=1)
        except queue.Full:
            pass
        
        # 等待工作线程结束
        for worker in self.worker_threads:
            worker.join(timeout=timeout / len(self.worker_threads))
        
        # 关闭线程池
        self.executor.shutdown(wait=True)
        
        logger.info("Task executor stopped")
    
    def _worker_loop(self):
        """工作线程循环"""
        while self.running:
            try:
                # 获取任务（带超时避免阻塞）
                priority_item = self.task_queue.get(timeout=1)
                
                if priority_item is None or priority_item[1] is None:
                    # 停止信号
                    break
                
                _, task = priority_item
                self._execute_task(task)
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Worker error: {e}")
    
    def _execute_task(self, task: Task):
        """执行单个任务"""
        with self.lock:
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now()
            self.stats['active_workers'] += 1
        
        try:
            logger.debug(f"Executing task {task.task_id}")
            
            # 检查任务是否包含进度回调
            if 'progress_callback' not in task.kwargs:
                task.kwargs['progress_callback'] = lambda p: self._update_progress(task.task_id, p)
            
            # 执行任务
            result = task.func(*task.args, **task.kwargs)
            
            with self.lock:
                task.status = TaskStatus.COMPLETED
                task.result = result
                task.completed_at = datetime.now()
                task.progress = 100
                self.stats['completed_tasks'] += 1
            
            logger.debug(f"Task {task.task_id} completed successfully")
            
        except Exception as e:
            logger.error(f"Task {task.task_id} failed: {e}")
            
            with self.lock:
                task.error = e
                task.retry_count += 1
                
                # 检查是否需要重试
                if task.retry_count < task.max_retries:
                    task.status = TaskStatus.PENDING
                    # 重新添加到队列（降低优先级）
                    retry_priority = max(TaskPriority.LOW.value, task.priority.value - 1)
                    self.task_queue.put((retry_priority, task))
                    logger.info(f"Task {task.task_id} scheduled for retry ({task.retry_count}/{task.max_retries})")
                else:
                    task.status = TaskStatus.FAILED
                    task.completed_at = datetime.now()
                    self.stats['failed_tasks'] += 1
                    logger.error(f"Task {task.task_id} failed permanently after {task.retry_count} retries")
        
        finally:
            with self.lock:
                self.stats['active_workers'] -= 1
                self.stats['queue_size'] = self.task_queue.qsize()
    
    def _update_progress(self, task_id: str, progress: int):
        """更新任务进度"""
        with self.lock:
            if task_id in self.tasks:
                self.tasks[task_id].progress = min(100, max(0, progress))
    
    def submit_task(self, func: Callable, args: tuple = (), kwargs: dict = None,
                   priority: TaskPriority = TaskPriority.NORMAL, 
                   max_retries: int = 3, task_id: str = None) -> str:
        """提交任务"""
        if not self.running:
            raise RuntimeError("Task executor is not running")
        
        if task_id is None:
            task_id = str(uuid.uuid4())
        
        task = Task(
            task_id=task_id,
            func=func,
            args=args,
            kwargs=kwargs or {},
            priority=priority,
            max_retries=max_retries
        )
        
        with self.lock:
            self.tasks[task_id] = task
            self.stats['total_tasks'] += 1
        
        try:
            self.task_queue.put((priority.value, task), timeout=5)
            logger.info(f"Task {task_id} submitted successfully")
            return task_id
        except queue.Full:
            with self.lock:
                del self.tasks[task_id]
                self.stats['total_tasks'] -= 1
            raise RuntimeError("Task queue is full")
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        with self.lock:
            task = self.tasks.get(task_id)
            return task.to_dict() if task else None
    
    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        with self.lock:
            task = self.tasks.get(task_id)
            if task and task.status == TaskStatus.PENDING:
                task.status = TaskStatus.CANCELLED
                task.completed_at = datetime.now()
                self.stats['cancelled_tasks'] += 1
                return True
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self.lock:
            stats = self.stats.copy()
            stats['queue_size'] = self.task_queue.qsize()
            return stats
    
    def cleanup_completed_tasks(self, max_age_hours: int = 24):
        """清理已完成的任务"""
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        
        with self.lock:
            tasks_to_remove = []
            for task_id, task in self.tasks.items():
                if (task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED] 
                    and task.completed_at 
                    and task.completed_at < cutoff_time):
                    tasks_to_remove.append(task_id)
            
            for task_id in tasks_to_remove:
                del self.tasks[task_id]
            
            logger.info(f"Cleaned up {len(tasks_to_remove)} completed tasks")


# 全局任务执行器
_global_task_executor = None

def get_task_executor() -> TaskExecutor:
    """获取全局任务执行器"""
    global _global_task_executor
    if _global_task_executor is None:
        _global_task_executor = TaskExecutor()
        _global_task_executor.start()
    return _global_task_executor

def init_task_executor(max_workers: int = 4, queue_size: int = 1000):
    """初始化任务执行器"""
    global _global_task_executor
    
    try:
        if _global_task_executor:
            _global_task_executor.stop()
        
        _global_task_executor = TaskExecutor(max_workers=max_workers, queue_size=queue_size)
        _global_task_executor.start()
        
        logger.info(f"Task executor initialized with {max_workers} workers")
        return _global_task_executor
        
    except Exception as e:
        logger.error(f"Task executor initialization error: {e}")
        raise

def async_task(priority: TaskPriority = TaskPriority.NORMAL, max_retries: int = 3):
    """异步任务装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            executor = get_task_executor()
            task_id = executor.submit_task(
                func=func,
                args=args,
                kwargs=kwargs,
                priority=priority,
                max_retries=max_retries
            )
            return task_id
        
        # 添加同步执行方法
        wrapper.sync = func
        return wrapper
    
    return decorator

# 预定义的异步任务函数

@async_task(priority=TaskPriority.NORMAL, max_retries=2)
def async_send_email(recipient: str, subject: str, content: str, **kwargs):
    """异步发送邮件"""
    from woniunote.common.utils import send_email
    
    progress_callback = kwargs.pop('progress_callback', lambda p: None)
    
    try:
        progress_callback(10)
        
        # 模拟邮件发送过程
        result = send_email(recipient, content)
        
        progress_callback(50)
        time.sleep(0.1)  # 模拟网络延迟
        progress_callback(100)
        
        return {
            'success': True,
            'recipient': recipient,
            'subject': subject,
            'sent_at': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Email sending failed: {e}")
        raise

@async_task(priority=TaskPriority.LOW, max_retries=1)
def async_compress_image(source_path: str, dest_path: str, width: int = 800, **kwargs):
    """异步压缩图片"""
    from woniunote.common.utils import compress_image
    
    progress_callback = kwargs.pop('progress_callback', lambda p: None)
    
    try:
        progress_callback(10)
        
        result = compress_image(source_path, dest_path, width)
        
        progress_callback(50)
        time.sleep(0.1)  # 模拟处理时间
        progress_callback(100)
        
        return {
            'success': True,
            'source': source_path,
            'destination': dest_path,
            'processed_at': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Image compression failed: {e}")
        raise

@async_task(priority=TaskPriority.HIGH, max_retries=3)
def async_backup_data(data: Dict[str, Any], backup_path: str, **kwargs):
    """异步备份数据"""
    progress_callback = kwargs.pop('progress_callback', lambda p: None)
    
    try:
        progress_callback(10)
        
        # 模拟备份过程
        with open(backup_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        progress_callback(50)
        time.sleep(0.2)  # 模拟I/O操作
        progress_callback(100)
        
        return {
            'success': True,
            'backup_path': backup_path,
            'data_size': len(str(data)),
            'backed_up_at': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Data backup failed: {e}")
        raise

@async_task(priority=TaskPriority.URGENT, max_retries=5)
def async_send_notification(user_id: str, message: str, notification_type: str = 'info', **kwargs):
    """异步发送通知"""
    progress_callback = kwargs.pop('progress_callback', lambda p: None)
    
    try:
        progress_callback(20)
        
        # 模拟通知发送
        notification_data = {
            'user_id': user_id,
            'message': message,
            'type': notification_type,
            'sent_at': datetime.now().isoformat()
        }
        
        progress_callback(60)
        time.sleep(0.1)  # 模拟API调用
        progress_callback(100)
        
        logger.info(f"Notification sent to user {user_id}: {message}")
        
        return notification_data
        
    except Exception as e:
        logger.error(f"Notification sending failed: {e}")
        raise

def shutdown_task_executor():
    """关闭任务执行器"""
    global _global_task_executor
    if _global_task_executor:
        _global_task_executor.stop()
        _global_task_executor = None
        logger.info("Task executor shutdown completed") 