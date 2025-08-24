#!/usr/bin/env python3
"""
统一的工具函数模块
整合所有工具相关功能：计时器、追踪ID、清理管理等
"""

import os
import time
import uuid
import hashlib
import threading
import weakref
from typing import Dict, Any, Optional, List, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from functools import wraps
import re

from .unified_logging import get_logger

logger = get_logger('unified_utils')

# ==================== 枚举定义 ====================

class TimerType(Enum):
    """计时器类型"""
    FUNCTION = "function"          # 函数计时
    BLOCK = "block"                # 代码块计时
    PERFORMANCE = "performance"    # 性能计时

class CleanupPriority(Enum):
    """清理优先级"""
    LOW = "low"                    # 低优先级
    NORMAL = "normal"              # 普通优先级
    HIGH = "high"                  # 高优先级
    CRITICAL = "critical"          # 关键优先级

# ==================== 数据类定义 ====================

@dataclass
class TimerResult:
    """计时结果"""
    name: str
    duration: float
    start_time: float
    end_time: float
    type: TimerType
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class CleanupTask:
    """清理任务"""
    name: str
    func: Callable
    priority: CleanupPriority
    dependencies: List[str] = field(default_factory=list)
    executed: bool = False
    error: Optional[str] = None

# ==================== 计时器管理器 ====================

class TimerManager:
    """计时器管理器"""
    
    def __init__(self):
        self.timers: Dict[str, TimerResult] = {}
        self.active_timers: Dict[str, float] = {}
        self._lock = threading.RLock()
        
        logger.info("计时器管理器初始化完成")
    
    def start_timer(self, name: str, timer_type: TimerType = TimerType.FUNCTION) -> str:
        """开始计时"""
        timer_id = f"{name}_{uuid.uuid4().hex[:8]}"
        
        with self._lock:
            self.active_timers[timer_id] = time.time()
        
        return timer_id
    
    def stop_timer(self, timer_id: str, metadata: Dict[str, Any] = None) -> Optional[TimerResult]:
        """停止计时"""
        with self._lock:
            if timer_id not in self.active_timers:
                return None
            
            start_time = self.active_timers.pop(timer_id)
            end_time = time.time()
            duration = end_time - start_time
            
            # 提取名称和类型
            name = timer_id.rsplit('_', 1)[0]
            timer_type = TimerType.FUNCTION
            
            result = TimerResult(
                name=name,
                duration=duration,
                start_time=start_time,
                end_time=end_time,
                type=timer_type,
                metadata=metadata or {}
            )
            
            self.timers[timer_id] = result
            
            return result
    
    def get_timer_stats(self) -> Dict[str, Any]:
        """获取计时统计"""
        with self._lock:
            if not self.timers:
                return {'total_timers': 0}
            
            durations = [timer.duration for timer in self.timers.values()]
            return {
                'total_timers': len(self.timers),
                'active_timers': len(self.active_timers),
                'avg_duration': sum(durations) / len(durations),
                'min_duration': min(durations),
                'max_duration': max(durations),
                'total_duration': sum(durations)
            }
    
    def clear_timers(self):
        """清除所有计时器"""
        with self._lock:
            self.timers.clear()
            self.active_timers.clear()

# ==================== 追踪ID管理器 ====================

class TraceIdManager:
    """追踪ID管理器"""
    
    def __init__(self):
        self.trace_ids: Dict[int, str] = {}
        self._lock = threading.RLock()
        
        logger.info("追踪ID管理器初始化完成")
    
    def generate_trace_id(self, prefix: str = "trace") -> str:
        """生成追踪ID"""
        trace_id = f"{prefix}_{uuid.uuid4().hex[:16]}"
        
        with self._lock:
            self.trace_ids[threading.get_ident()] = trace_id
        
        return trace_id
    
    def get_current_trace_id(self) -> Optional[str]:
        """获取当前线程的追踪ID"""
        with self._lock:
            return self.trace_ids.get(threading.get_ident())
    
    def set_trace_id(self, trace_id: str):
        """设置当前线程的追踪ID"""
        with self._lock:
            self.trace_ids[threading.get_ident()] = trace_id
    
    def clear_trace_id(self):
        """清除当前线程的追踪ID"""
        with self._lock:
            self.trace_ids.pop(threading.get_ident(), None)
    
    def get_all_trace_ids(self) -> Dict[int, str]:
        """获取所有追踪ID"""
        with self._lock:
            return self.trace_ids.copy()

# ==================== 清理管理器 ====================

class CleanupManager:
    """清理管理器"""
    
    def __init__(self):
        self.cleanup_tasks: Dict[str, CleanupTask] = {}
        self.execution_order: List[str] = []
        self._lock = threading.RLock()
        
        logger.info("清理管理器初始化完成")
    
    def register_cleanup_task(self, name: str, func: Callable, 
                             priority: CleanupPriority = CleanupPriority.NORMAL,
                             dependencies: List[str] = None):
        """注册清理任务"""
        with self._lock:
            self.cleanup_tasks[name] = CleanupTask(
                name=name,
                func=func,
                priority=priority,
                dependencies=dependencies or []
            )
            
            # 重新计算执行顺序
            self._calculate_execution_order()
    
    def _calculate_execution_order(self):
        """计算执行顺序"""
        # 按优先级排序
        priority_order = {
            CleanupPriority.CRITICAL: 0,
            CleanupPriority.HIGH: 1,
            CleanupPriority.NORMAL: 2,
            CleanupPriority.LOW: 3
        }
        
        sorted_tasks = sorted(
            self.cleanup_tasks.values(),
            key=lambda x: (priority_order[x.priority], x.name)
        )
        
        self.execution_order = [task.name for task in sorted_tasks]
    
    def execute_cleanup(self, task_name: str = None) -> Dict[str, Any]:
        """执行清理任务"""
        results = {}
        
        with self._lock:
            if task_name:
                # 执行指定任务
                if task_name in self.cleanup_tasks:
                    results[task_name] = self._execute_single_task(task_name)
            else:
                # 执行所有任务
                for task_name in self.execution_order:
                    results[task_name] = self._execute_single_task(task_name)
        
        return results
    
    def _execute_single_task(self, task_name: str) -> Dict[str, Any]:
        """执行单个清理任务"""
        task = self.cleanup_tasks[task_name]
        
        if task.executed:
            return {'status': 'already_executed', 'error': None}
        
        # 检查依赖
        for dep in task.dependencies:
            if dep not in self.cleanup_tasks or not self.cleanup_tasks[dep].executed:
                return {'status': 'dependency_not_met', 'error': f'依赖任务 {dep} 未执行'}
        
        try:
            # 执行任务
            start_time = time.time()
            result = task.func()
            duration = time.time() - start_time
            
            task.executed = True
            
            return {
                'status': 'success',
                'result': result,
                'duration': duration,
                'error': None
            }
            
        except Exception as e:
            task.error = str(e)
            logger.error(f"清理任务 {task_name} 执行失败: {e}")
            
            return {
                'status': 'failed',
                'result': None,
                'duration': 0,
                'error': str(e)
            }
    
    def get_cleanup_status(self) -> Dict[str, Any]:
        """获取清理状态"""
        with self._lock:
            return {
                'total_tasks': len(self.cleanup_tasks),
                'executed_tasks': sum(1 for task in self.cleanup_tasks.values() if task.executed),
                'failed_tasks': sum(1 for task in self.cleanup_tasks.values() if task.error),
                'execution_order': self.execution_order.copy(),
                'tasks': {
                    name: {
                        'priority': task.priority.value,
                        'dependencies': task.dependencies,
                        'executed': task.executed,
                        'error': task.error
                    }
                    for name, task in self.cleanup_tasks.items()
                }
            }

# ==================== 工具函数 ====================

def generate_uuid(prefix: str = "") -> str:
    """生成UUID"""
    uuid_str = str(uuid.uuid4())
    if prefix:
        return f"{prefix}_{uuid_str}"
    return uuid_str

def generate_hash(data: str, algorithm: str = "md5", length: int = None) -> str:
    """生成哈希值"""
    if algorithm == "md5":
        hash_obj = hashlib.md5(data.encode())
    elif algorithm == "sha1":
        hash_obj = hashlib.sha1(data.encode())
    elif algorithm == "sha256":
        hash_obj = hashlib.sha256(data.encode())
    else:
        raise ValueError(f"不支持的哈希算法: {algorithm}")
    
    hash_value = hash_obj.hexdigest()
    
    if length:
        return hash_value[:length]
    
    return hash_value

def safe_filename(filename: str, max_length: int = 255) -> str:
    """生成安全的文件名"""
    # 移除或替换不安全的字符
    safe_name = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # 限制长度
    if len(safe_name) > max_length:
        name, ext = os.path.splitext(safe_name)
        safe_name = name[:max_length-len(ext)] + ext
    
    return safe_name

def ensure_directory(path: str) -> bool:
    """确保目录存在"""
    try:
        Path(path).mkdir(parents=True, exist_ok=True)
        return True
    except Exception as e:
        logger.error(f"创建目录失败 {path}: {e}")
        return False

def get_file_size(file_path: str) -> int:
    """获取文件大小"""
    try:
        return os.path.getsize(file_path)
    except OSError:
        return 0

def format_file_size(size_bytes: int) -> str:
    """格式化文件大小"""
    if size_bytes == 0:
        return "0B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f}{size_names[i]}"

# ==================== 装饰器 ====================

def timer(name: str = None, manager: TimerManager = None):
    """计时装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            timer_name = name or func.__name__
            timer_mgr = manager or get_timer_manager()
            
            if timer_mgr:
                timer_id = timer_mgr.start_timer(timer_name)
                try:
                    result = func(*args, **kwargs)
                    timer_mgr.stop_timer(timer_id, {'args_count': len(args), 'kwargs_count': len(kwargs)})
                    return result
                except Exception as e:
                    timer_mgr.stop_timer(timer_id, {'error': str(e)})
                    raise
            else:
                return func(*args, **kwargs)
        
        return wrapper
    return decorator

def trace_id(prefix: str = "func", manager: TraceIdManager = None):
    """追踪ID装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            trace_mgr = manager or get_trace_id_manager()
            
            if trace_mgr:
                trace_id = trace_mgr.generate_trace_id(prefix)
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    trace_mgr.clear_trace_id()
            else:
                return func(*args, **kwargs)
        
        return wrapper
    return decorator

def cleanup_task(name: str, priority: CleanupPriority = CleanupPriority.NORMAL, 
                 dependencies: List[str] = None, manager: CleanupManager = None):
    """清理任务装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cleanup_mgr = manager or get_cleanup_manager()
            
            if cleanup_mgr:
                cleanup_mgr.register_cleanup_task(name, func, priority, dependencies)
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator

# ==================== 统一工具管理器 ====================

class UnifiedUtilsManager:
    """统一工具管理器"""
    
    def __init__(self):
        self.timer_manager = TimerManager()
        self.trace_id_manager = TraceIdManager()
        self.cleanup_manager = CleanupManager()
        
        logger.info("统一工具管理器初始化完成")
    
    def get_timer_manager(self) -> TimerManager:
        """获取计时器管理器"""
        return self.timer_manager
    
    def get_trace_id_manager(self) -> TraceIdManager:
        """获取追踪ID管理器"""
        return self.trace_id_manager
    
    def get_cleanup_manager(self) -> CleanupManager:
        """获取清理管理器"""
        return self.cleanup_manager
    
    def get_summary(self) -> Dict[str, Any]:
        """获取工具管理器摘要"""
        return {
            'timer': self.timer_manager.get_timer_stats(),
            'trace_id': {
                'active_traces': len(self.trace_id_manager.get_all_trace_ids())
            },
            'cleanup': self.cleanup_manager.get_cleanup_status()
        }

# ==================== 全局实例和工厂函数 ====================

# 全局工具管理器实例
_global_utils_manager = None

def init_unified_utils() -> UnifiedUtilsManager:
    """初始化全局工具管理器"""
    global _global_utils_manager
    _global_utils_manager = UnifiedUtilsManager()
    return _global_utils_manager

def get_utils_manager() -> Optional[UnifiedUtilsManager]:
    """获取全局工具管理器"""
    return _global_utils_manager

def get_timer_manager() -> Optional[TimerManager]:
    """获取计时器管理器"""
    if _global_utils_manager:
        return _global_utils_manager.get_timer_manager()
    return None

def get_trace_id_manager() -> Optional[TraceIdManager]:
    """获取追踪ID管理器"""
    if _global_utils_manager:
        return _global_utils_manager.get_trace_id_manager()
    return None

def get_cleanup_manager() -> Optional[CleanupManager]:
    """获取清理管理器"""
    if _global_utils_manager:
        return _global_utils_manager.get_cleanup_manager()
    return None

# ==================== 向后兼容 ====================

# 为了向后兼容，保留旧的函数名
init_timer = init_unified_utils
get_timer = get_timer_manager
init_trace_id_manager = init_unified_utils
get_trace_id_manager_legacy = get_trace_id_manager
init_cleanup_manager = init_unified_utils
get_cleanup_manager_legacy = get_cleanup_manager

# 向后兼容的函数
def can_use_minute():
    """检查是否可以使用分钟级别的计时（向后兼容）"""
    timer_mgr = get_timer_manager()
    if timer_mgr:
        return timer_mgr.get_timer_stats().get('total_timers', 0)
    # 如果没有初始化，返回一个默认值
    return 1
