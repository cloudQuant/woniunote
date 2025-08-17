"""
清理管理器 - 主动清理和维护系统资源
定期执行清理任务，防止内存泄露和资源积累
"""
import gc
import os
import time
import threading
import traceback
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime, timedelta
from contextlib import contextmanager

from .simple_logger import get_simple_logger
from .trace_id_manager import TraceIdManager
from .memory_monitor import get_memory_detector, trigger_memory_cleanup
from .resource_manager import resource_manager

class CleanupTask:
    """清理任务"""
    
    def __init__(self, name: str, func: Callable, interval_seconds: int, description: str = ""):
        self.name = name
        self.func = func
        self.interval_seconds = interval_seconds
        self.description = description
        self.last_run = None
        self.run_count = 0
        self.failure_count = 0
        self.last_error = None
    
    def should_run(self) -> bool:
        """检查是否应该执行"""
        if self.last_run is None:
            return True
        
        elapsed = (datetime.now() - self.last_run).total_seconds()
        return elapsed >= self.interval_seconds
    
    def run(self) -> bool:
        """执行清理任务"""
        try:
            self.func()
            self.last_run = datetime.now()
            self.run_count += 1
            self.last_error = None
            return True
        except Exception as e:
            self.failure_count += 1
            self.last_error = str(e)
            return False

class CleanupManager:
    """清理管理器"""
    
    def __init__(self):
        self.logger = get_simple_logger('cleanup_manager')
        self._tasks = {}
        self._running = False
        self._thread = None
        self._lock = threading.RLock()
        
        # 注册默认清理任务
        self._register_default_tasks()
        
        self.logger.info("清理管理器初始化完成")
    
    def _register_default_tasks(self):
        """注册默认清理任务"""
        # 垃圾收集任务
        self.register_task(
            "garbage_collection", 
            self._gc_cleanup, 
            300,  # 5分钟
            "强制垃圾收集，清理未引用对象"
        )
        
        # 内存检查和清理
        self.register_task(
            "memory_cleanup",
            self._memory_cleanup,
            600,  # 10分钟
            "检查内存使用情况并清理"
        )
        
        # 资源管理器清理
        self.register_task(
            "resource_cleanup",
            self._resource_cleanup,
            900,  # 15分钟
            "清理资源管理器的缓存和统计"
        )
        
        # 日志清理
        self.register_task(
            "log_cleanup",
            self._log_cleanup,
            3600,  # 1小时
            "清理过期的日志条目"
        )
        
        # 会话清理
        self.register_task(
            "session_cleanup",
            self._session_cleanup,
            1800,  # 30分钟
            "清理过期的数据库会话"
        )
    
    def register_task(self, name: str, func: Callable, interval_seconds: int, description: str = ""):
        """注册清理任务"""
        with self._lock:
            task = CleanupTask(name, func, interval_seconds, description)
            self._tasks[name] = task
            
            self.logger.info(f"注册清理任务: {name}", {
                'interval_seconds': interval_seconds,
                'description': description
            })
    
    def unregister_task(self, name: str):
        """注销清理任务"""
        with self._lock:
            if name in self._tasks:
                del self._tasks[name]
                self.logger.info(f"注销清理任务: {name}")
    
    def start(self):
        """启动清理管理器"""
        if self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self._thread.start()
        
        self.logger.info("清理管理器启动")
    
    def stop(self):
        """停止清理管理器"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        
        self.logger.info("清理管理器停止")
    
    def _cleanup_loop(self):
        """清理循环"""
        while self._running:
            try:
                self._run_pending_tasks()
                time.sleep(60)  # 每分钟检查一次
                
            except Exception as e:
                self.logger.error(f"清理循环异常: {e}")
                time.sleep(60)
    
    def _run_pending_tasks(self):
        """运行待执行的任务"""
        with self._lock:
            tasks_to_run = [
                task for task in self._tasks.values()
                if task.should_run()
            ]
        
        for task in tasks_to_run:
            try:
                trace_id = TraceIdManager.generate_simple_trace_id()
                
                self.logger.debug(f"执行清理任务: {task.name}", {
                    'trace_id': trace_id,
                    'description': task.description
                })
                
                start_time = time.time()
                success = task.run()
                execution_time = time.time() - start_time
                
                if success:
                    self.logger.info(f"清理任务完成: {task.name}", {
                        'trace_id': trace_id,
                        'execution_time_s': round(execution_time, 2),
                        'run_count': task.run_count
                    })
                else:
                    self.logger.error(f"清理任务失败: {task.name}", {
                        'trace_id': trace_id,
                        'error': task.last_error,
                        'failure_count': task.failure_count
                    })
                    
            except Exception as e:
                self.logger.error(f"执行清理任务异常: {task.name}", {
                    'error': str(e),
                    'traceback': traceback.format_exc()
                })
    
    def _gc_cleanup(self):
        """垃圾收集清理"""
        try:
            # 获取清理前的对象计数
            before_objects = len(gc.get_objects())
            
            # 强制垃圾收集
            collected = gc.collect()
            
            # 获取清理后的对象计数
            after_objects = len(gc.get_objects())
            
            self.logger.info("垃圾收集完成", {
                'collected_objects': collected,
                'objects_before': before_objects,
                'objects_after': after_objects,
                'objects_freed': before_objects - after_objects
            })
            
        except Exception as e:
            self.logger.error(f"垃圾收集失败: {e}")
            raise
    
    def _memory_cleanup(self):
        """内存清理"""
        try:
            # 获取内存报告
            memory_detector = get_memory_detector()
            memory_report = memory_detector.get_memory_report()
            
            current_memory = memory_report.get('current_memory', {}).get('process_memory_mb', 0)
            warning_threshold = memory_report.get('thresholds', {}).get('warning_mb', 512)
            
            # 如果内存使用超过阈值，触发清理
            if current_memory > warning_threshold:
                self.logger.warning(f"内存使用超过阈值，触发清理", {
                    'current_memory_mb': current_memory,
                    'threshold_mb': warning_threshold
                })
                
                trigger_memory_cleanup()
            
            self.logger.debug("内存清理检查完成", {
                'current_memory_mb': current_memory,
                'threshold_mb': warning_threshold
            })
            
        except Exception as e:
            self.logger.error(f"内存清理失败: {e}")
            raise
    
    def _resource_cleanup(self):
        """资源清理"""
        try:
            # 清理资源管理器的缓存
            resource_manager.cleanup_session_cache()
            
            # 获取资源统计
            resource_stats = resource_manager.get_system_resource_info()
            
            self.logger.debug("资源清理完成", {
                'resource_stats': resource_stats
            })
            
        except Exception as e:
            self.logger.error(f"资源清理失败: {e}")
            raise
    
    def _log_cleanup(self):
        """日志清理"""
        try:
            # 这里可以实现日志文件清理逻辑
            # 例如删除过期的日志文件，压缩大文件等
            
            self.logger.debug("日志清理完成")
            
        except Exception as e:
            self.logger.error(f"日志清理失败: {e}")
            raise
    
    def _session_cleanup(self):
        """会话清理"""
        try:
            # 清理过期的数据库会话
            # 这个需要根据具体的会话管理实现来定制
            
            self.logger.debug("会话清理完成")
            
        except Exception as e:
            self.logger.error(f"会话清理失败: {e}")
            raise
    
    def force_cleanup_all(self):
        """强制执行所有清理任务"""
        self.logger.info("开始强制清理所有任务")
        
        with self._lock:
            tasks = list(self._tasks.values())
        
        for task in tasks:
            try:
                task.run()
                self.logger.info(f"强制清理任务完成: {task.name}")
            except Exception as e:
                self.logger.error(f"强制清理任务失败: {task.name}, 错误: {e}")
        
        self.logger.info("强制清理所有任务完成")
    
    def get_cleanup_status(self) -> Dict[str, Any]:
        """获取清理状态"""
        with self._lock:
            tasks_status = {}
            for name, task in self._tasks.items():
                tasks_status[name] = {
                    'description': task.description,
                    'interval_seconds': task.interval_seconds,
                    'last_run': task.last_run.isoformat() if task.last_run else None,
                    'run_count': task.run_count,
                    'failure_count': task.failure_count,
                    'last_error': task.last_error,
                    'should_run': task.should_run()
                }
            
            return {
                'running': self._running,
                'total_tasks': len(self._tasks),
                'tasks': tasks_status
            }

# 创建全局清理管理器
cleanup_manager = CleanupManager()

def start_cleanup_manager():
    """启动清理管理器"""
    cleanup_manager.start()

def stop_cleanup_manager():
    """停止清理管理器"""
    cleanup_manager.stop()

def force_cleanup():
    """强制执行清理"""
    cleanup_manager.force_cleanup_all()

def get_cleanup_status():
    """获取清理状态"""
    return cleanup_manager.get_cleanup_status()

def register_cleanup_task(name: str, func: Callable, interval_seconds: int, description: str = ""):
    """注册自定义清理任务"""
    cleanup_manager.register_task(name, func, interval_seconds, description)