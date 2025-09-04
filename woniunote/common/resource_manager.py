"""
资源管理器 - 解决内存泄露和资源管理问题
统一管理数据库连接、文件句柄、缓存等资源的生命周期
"""
import gc
import os
import sys
import time
import weakref
import threading
import traceback
import functools
from typing import Any, Dict, List, Optional, Set, Callable
from contextlib import contextmanager, ExitStack
from collections import defaultdict, deque
from datetime import datetime, timedelta

from .unified_logging import get_simple_logger
from .unified_logging import get_simple_logger as get_logger

try:
    from .trace_id_manager import TraceIdManager
except ImportError:
    # 如果trace_id_manager不存在，创建一个简单的替代
    class TraceIdManager:
        @staticmethod
        def generate_simple_trace_id():
            import uuid
            return str(uuid.uuid4())[:8]

class ResourceTracker:
    """资源跟踪器 - 跟踪和管理各种资源的生命周期"""
    
    def __init__(self):
        self.logger = get_simple_logger('resource_tracker')
        self._tracked_resources = weakref.WeakSet()
        self._resource_stats = defaultdict(int)
        self._resource_history = deque(maxlen=1000)
        self._cleanup_callbacks = []
        self._lock = threading.RLock()
        
        # 启动资源监控
        self._monitoring_enabled = True
        self._monitor_thread = threading.Thread(target=self._monitor_resources, daemon=True)
        self._monitor_thread.start()
    
    def track_resource(self, resource, resource_type: str, metadata: dict = None):
        """跟踪资源"""
        with self._lock:
            try:
                self._tracked_resources.add(resource)
                self._resource_stats[resource_type] += 1
                
                entry = {
                    'resource_type': resource_type,
                    'timestamp': datetime.now(),
                    'action': 'created',
                    'metadata': metadata or {},
                    'resource_id': id(resource)
                }
                self._resource_history.append(entry)
                
                self.logger.debug(f"跟踪资源: {resource_type}", {
                    'resource_id': id(resource),
                    'metadata': metadata
                })
                
            except Exception as e:
                self.logger.error(f"跟踪资源失败: {e}")
    
    def untrack_resource(self, resource, resource_type: str):
        """取消跟踪资源"""
        with self._lock:
            try:
                if resource in self._tracked_resources:
                    self._tracked_resources.discard(resource)
                    self._resource_stats[resource_type] = max(0, self._resource_stats[resource_type] - 1)
                    
                    entry = {
                        'resource_type': resource_type,
                        'timestamp': datetime.now(),
                        'action': 'released',
                        'resource_id': id(resource)
                    }
                    self._resource_history.append(entry)
                    
                    self.logger.debug(f"释放资源: {resource_type}", {
                        'resource_id': id(resource)
                    })
                    
            except Exception as e:
                self.logger.error(f"释放资源失败: {e}")
    
    def get_resource_stats(self) -> Dict[str, int]:
        """获取资源统计信息"""
        with self._lock:
            return dict(self._resource_stats)
    
    def get_resource_history(self, limit: int = 100) -> List[Dict]:
        """获取资源历史记录"""
        with self._lock:
            return list(self._resource_history)[-limit:]
    
    def _monitor_resources(self):
        """资源监控线程"""
        while self._monitoring_enabled:
            try:
                time.sleep(30)  # 每30秒检查一次
                
                with self._lock:
                    stats = dict(self._resource_stats)
                    total_resources = len(self._tracked_resources)
                    
                    # 记录资源使用情况
                    if total_resources > 0:
                        self.logger.info("资源使用统计", {
                            'total_resources': total_resources,
                            'resource_breakdown': stats,
                            'memory_usage_mb': self._get_memory_usage()
                        })
                    
                    # 检查资源泄露
                    self._check_resource_leaks(stats)
                    
            except Exception as e:
                self.logger.error(f"资源监控异常: {e}")
    
    def _get_memory_usage(self) -> float:
        """获取内存使用量(MB)"""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except ImportError:
            return 0.0
    
    def _check_resource_leaks(self, stats: Dict[str, int]):
        """检查资源泄露"""
        # 检查是否有资源数量异常增长
        for resource_type, count in stats.items():
            if count > 100:  # 阈值可配置
                self.logger.warning(f"可能的资源泄露: {resource_type}", {
                    'count': count,
                    'trace_id': TraceIdManager.generate_simple_trace_id()
                })
    
    def register_cleanup_callback(self, callback: Callable):
        """注册清理回调"""
        self._cleanup_callbacks.append(callback)
    
    def cleanup_all(self):
        """清理所有资源"""
        with self._lock:
            self.logger.info("开始清理所有资源")
            
            # 执行注册的清理回调
            for callback in self._cleanup_callbacks:
                try:
                    callback()
                except Exception as e:
                    self.logger.error(f"清理回调执行失败: {e}")
            
            # 强制垃圾收集
            gc.collect()
            
            self.logger.info("资源清理完成")
    
    def shutdown(self):
        """关闭资源跟踪器"""
        self._monitoring_enabled = False
        self.cleanup_all()

class ManagedResource:
    """受管理的资源基类"""
    
    def __init__(self, resource_type: str, metadata: dict = None):
        self.resource_type = resource_type
        self.metadata = metadata or {}
        self.created_at = datetime.now()
        self.trace_id = TraceIdManager.generate_simple_trace_id()
        
        # 注册到全局跟踪器
        resource_manager.tracker.track_resource(self, resource_type, metadata)
    
    def __del__(self):
        """析构时自动释放资源"""
        try:
            resource_manager.tracker.untrack_resource(self, self.resource_type)
        except:
            pass  # 避免析构器异常
    
    def cleanup(self):
        """清理资源（子类重写）"""
        pass

class ManagedDatabaseConnection(ManagedResource):
    """受管理的数据库连接"""
    
    def __init__(self, connection, metadata: dict = None):
        super().__init__("database_connection", metadata)
        self.connection = connection
        self._closed = False
    
    def __enter__(self):
        return self.connection
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()
    
    def cleanup(self):
        """关闭数据库连接"""
        if not self._closed and self.connection:
            try:
                if hasattr(self.connection, 'close'):
                    self.connection.close()
                self._closed = True
            except Exception as e:
                resource_manager.logger.error(f"关闭数据库连接失败: {e}")

class ManagedFileHandle(ManagedResource):
    """受管理的文件句柄"""
    
    def __init__(self, file_handle, filename: str, mode: str):
        metadata = {'filename': filename, 'mode': mode}
        super().__init__("file_handle", metadata)
        self.file_handle = file_handle
        self.filename = filename
        self._closed = False
    
    def __enter__(self):
        return self.file_handle
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()
    
    def read(self, *args, **kwargs):
        return self.file_handle.read(*args, **kwargs)
    
    def write(self, *args, **kwargs):
        return self.file_handle.write(*args, **kwargs)
    
    def cleanup(self):
        """关闭文件句柄"""
        if not self._closed and self.file_handle:
            try:
                if hasattr(self.file_handle, 'close'):
                    self.file_handle.close()
                self._closed = True
            except Exception as e:
                resource_manager.logger.error(f"关闭文件句柄失败: {e}")

class ResourceManager:
    """资源管理器主类"""
    
    def __init__(self):
        self.logger = get_simple_logger('resource_manager')
        self.tracker = ResourceTracker()
        self._session_cache = {}
        self._cache_cleanup_threshold = 1000
        
        # 注册应用关闭时的清理
        import atexit
        atexit.register(self.cleanup_on_exit)
    
    @contextmanager
    def managed_database_connection(self, database_info, metadata: dict = None):
        """管理数据库连接的上下文管理器"""
        connection = None
        try:
            from .utils import get_db_connection
            connection = get_db_connection(database_info)
            if not connection:
                raise Exception("Failed to establish database connection")
            
            managed_conn = ManagedDatabaseConnection(connection, metadata)
            yield managed_conn.connection
            
        except Exception as e:
            self.logger.error(f"数据库连接异常: {e}")
            if connection:
                try:
                    connection.rollback()
                except:
                    pass
            raise
        finally:
            if connection:
                try:
                    connection.close()
                except:
                    pass
    
    @contextmanager
    def managed_file(self, filename: str, mode: str = 'r', encoding: str = 'utf-8', **kwargs):
        """管理文件句柄的上下文管理器"""
        file_handle = None
        try:
            file_handle = open(filename, mode, encoding=encoding, **kwargs)
            managed_file = ManagedFileHandle(file_handle, filename, mode)
            yield managed_file
            
        except Exception as e:
            self.logger.error(f"文件操作异常: {filename}, {e}")
            raise
        finally:
            if file_handle:
                try:
                    file_handle.close()
                except:
                    pass
    
    def cleanup_session_cache(self):
        """清理会话缓存"""
        try:
            if len(self._session_cache) > self._cache_cleanup_threshold:
                # 清理一半的缓存项
                items_to_remove = len(self._session_cache) // 2
                keys_to_remove = list(self._session_cache.keys())[:items_to_remove]
                
                for key in keys_to_remove:
                    del self._session_cache[key]
                
                self.logger.info(f"清理会话缓存，移除 {items_to_remove} 项")
        except Exception as e:
            self.logger.error(f"清理会话缓存失败: {e}")
    
    def force_garbage_collection(self):
        """强制垃圾收集"""
        try:
            # 清理会话缓存
            self.cleanup_session_cache()
            
            # 强制垃圾收集
            collected = gc.collect()
            
            self.logger.info(f"强制垃圾收集完成，回收对象数: {collected}")
            
            return collected
        except Exception as e:
            self.logger.error(f"强制垃圾收集失败: {e}")
            return 0
    
    def get_system_resource_info(self) -> Dict[str, Any]:
        """获取系统资源信息"""
        try:
            import psutil
            process = psutil.Process()
            
            return {
                'memory_usage_mb': process.memory_info().rss / 1024 / 1024,
                'memory_percent': process.memory_percent(),
                'cpu_percent': process.cpu_percent(),
                'open_files': len(process.open_files()) if hasattr(process, 'open_files') else 0,
                'connections': len(process.connections()) if hasattr(process, 'connections') else 0,
                'threads': process.num_threads(),
                'tracked_resources': self.tracker.get_resource_stats()
            }
        except ImportError:
            return {
                'tracked_resources': self.tracker.get_resource_stats(),
                'gc_objects': len(gc.get_objects())
            }
    
    def cleanup_on_exit(self):
        """应用退出时的清理"""
        self.logger.info("应用退出，开始清理资源")
        try:
            self.tracker.shutdown()
            self.force_garbage_collection()
        except Exception as e:
            self.logger.error(f"退出清理失败: {e}")

def resource_monitor(resource_type: str, metadata: dict = None):
    """装饰器：监控函数的资源使用"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            trace_id = TraceIdManager.generate_simple_trace_id()
            
            # 记录开始时的资源状态
            start_memory = resource_manager._get_memory_usage() if hasattr(resource_manager, '_get_memory_usage') else 0
            start_time = time.time()
            
            try:
                # 执行函数
                result = func(*args, **kwargs)
                
                # 记录结束时的资源状态
                end_memory = resource_manager._get_memory_usage() if hasattr(resource_manager, '_get_memory_usage') else 0
                end_time = time.time()
                
                # 记录资源使用情况
                resource_manager.logger.info(f"函数 {func.__name__} 资源使用", {
                    'trace_id': trace_id,
                    'resource_type': resource_type,
                    'execution_time_s': round(end_time - start_time, 3),
                    'memory_diff_mb': round(end_memory - start_memory, 2) if start_memory and end_memory else 0,
                    'metadata': metadata
                })
                
                return result
                
            except Exception as e:
                resource_manager.logger.error(f"函数 {func.__name__} 执行异常", {
                    'trace_id': trace_id,
                    'resource_type': resource_type,
                    'error': str(e),
                    'metadata': metadata
                })
                raise
                
        return wrapper
    return decorator

# 创建全局资源管理器实例
resource_manager = ResourceManager()

# 为向后兼容提供的便捷函数
def get_managed_db_connection(database_info, metadata: dict = None):
    """获取受管理的数据库连接"""
    return resource_manager.managed_database_connection(database_info, metadata)

def get_managed_file(filename: str, mode: str = 'r', encoding: str = 'utf-8', **kwargs):
    """获取受管理的文件句柄"""
    return resource_manager.managed_file(filename, mode, encoding, **kwargs)

def cleanup_resources():
    """清理所有资源"""
    resource_manager.force_garbage_collection()

def get_resource_stats():
    """获取资源统计信息"""
    return resource_manager.get_system_resource_info()