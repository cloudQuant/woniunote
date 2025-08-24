#!/usr/bin/env python3
"""
内存优化管理器
提供内存使用监控、优化和泄漏检测功能
"""

import gc
import sys
import psutil
import time
import threading
from typing import Dict, Any, Optional, List, Callable
from functools import wraps
from weakref import WeakSet
from collections import defaultdict
from woniunote.common.unified_logging import get_simple_logger

logger = get_simple_logger('memory_optimizer')

class MemoryMonitor:
    """内存监控器"""
    
    def __init__(self):
        self.process = psutil.Process()
        self.baseline_memory = None
        self.peak_memory = 0
        self.memory_snapshots = []
        self.large_objects = WeakSet()
        self.memory_leaks = defaultdict(int)
        self._monitoring = False
        self._monitor_thread = None
        
    def start_monitoring(self, interval: float = 10.0):
        """开始内存监控"""
        if self._monitoring:
            return
            
        self._monitoring = True
        self.baseline_memory = self.get_current_memory()
        self.peak_memory = self.baseline_memory
        
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            args=(interval,),
            daemon=True
        )
        self._monitor_thread.start()
        
        logger.info("内存监控已启动", {
            'baseline_memory_mb': round(self.baseline_memory / 1024 / 1024, 2),
            'interval_seconds': interval
        })
    
    def stop_monitoring(self):
        """停止内存监控"""
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5.0)
        
        logger.info("内存监控已停止")
    
    def _monitor_loop(self, interval: float):
        """监控循环"""
        while self._monitoring:
            try:
                current_memory = self.get_current_memory()
                self.peak_memory = max(self.peak_memory, current_memory)
                
                # 记录内存快照
                snapshot = {
                    'timestamp': time.time(),
                    'memory_mb': round(current_memory / 1024 / 1024, 2),
                    'memory_percent': self.process.memory_percent(),
                    'gc_counts': gc.get_count()
                }
                
                self.memory_snapshots.append(snapshot)
                
                # 保持最近100个快照
                if len(self.memory_snapshots) > 100:
                    self.memory_snapshots.pop(0)
                
                # 检测内存泄漏
                if self.baseline_memory and current_memory > self.baseline_memory * 1.5:
                    logger.warning("检测到可能的内存泄漏", {
                        'current_memory_mb': round(current_memory / 1024 / 1024, 2),
                        'baseline_memory_mb': round(self.baseline_memory / 1024 / 1024, 2),
                        'increase_percent': round((current_memory / self.baseline_memory - 1) * 100, 2)
                    })
                
                time.sleep(interval)
                
            except Exception as e:
                logger.error(f"内存监控异常: {e}")
                time.sleep(interval)
    
    def get_current_memory(self) -> int:
        """获取当前内存使用量（字节）"""
        return self.process.memory_info().rss
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """获取内存统计信息"""
        current_memory = self.get_current_memory()
        
        stats = {
            'current_memory_mb': round(current_memory / 1024 / 1024, 2),
            'peak_memory_mb': round(self.peak_memory / 1024 / 1024, 2),
            'memory_percent': self.process.memory_percent(),
            'gc_counts': gc.get_count(),
            'gc_thresholds': gc.get_threshold(),
            'large_objects_count': len(self.large_objects)
        }
        
        if self.baseline_memory:
            stats['baseline_memory_mb'] = round(self.baseline_memory / 1024 / 1024, 2)
            stats['memory_increase_mb'] = round((current_memory - self.baseline_memory) / 1024 / 1024, 2)
            stats['memory_increase_percent'] = round((current_memory / self.baseline_memory - 1) * 100, 2)
        
        return stats
    
    def force_gc(self) -> Dict[str, Any]:
        """强制垃圾回收"""
        before_memory = self.get_current_memory()
        before_counts = gc.get_count()
        
        # 执行垃圾回收
        collected = gc.collect()
        
        after_memory = self.get_current_memory()
        after_counts = gc.get_count()
        
        freed_memory = before_memory - after_memory
        
        result = {
            'objects_collected': collected,
            'memory_freed_mb': round(freed_memory / 1024 / 1024, 2),
            'before_memory_mb': round(before_memory / 1024 / 1024, 2),
            'after_memory_mb': round(after_memory / 1024 / 1024, 2),
            'before_counts': before_counts,
            'after_counts': after_counts
        }
        
        logger.info("手动垃圾回收完成", result)
        return result

class MemoryOptimizer:
    """内存优化器"""
    
    def __init__(self):
        self.monitor = MemoryMonitor()
        self.optimization_rules = []
        self.auto_optimize = False
        
    def register_optimization_rule(self, rule: Callable[[], bool], description: str):
        """注册优化规则"""
        self.optimization_rules.append({
            'rule': rule,
            'description': description
        })
        
    def optimize_memory(self) -> Dict[str, Any]:
        """执行内存优化"""
        results = {
            'start_time': time.time(),
            'optimizations_applied': [],
            'total_memory_freed_mb': 0
        }
        
        before_stats = self.monitor.get_memory_stats()
        
        # 执行垃圾回收
        gc_result = self.monitor.force_gc()
        results['optimizations_applied'].append('garbage_collection')
        results['total_memory_freed_mb'] += gc_result['memory_freed_mb']
        
        # 应用优化规则
        for rule_info in self.optimization_rules:
            try:
                if rule_info['rule']():
                    results['optimizations_applied'].append(rule_info['description'])
                    logger.info(f"应用优化规则: {rule_info['description']}")
            except Exception as e:
                logger.error(f"优化规则执行失败: {rule_info['description']}, 错误: {e}")
        
        after_stats = self.monitor.get_memory_stats()
        
        results.update({
            'end_time': time.time(),
            'before_memory_mb': before_stats['current_memory_mb'],
            'after_memory_mb': after_stats['current_memory_mb'],
            'duration_seconds': time.time() - results['start_time']
        })
        
        logger.info("内存优化完成", results)
        return results

def memory_profiler(func_name: str = None):
    """内存性能分析装饰器"""
    def decorator(func):
        name = func_name or f"{func.__module__}.{func.__name__}"
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 记录开始状态
            process = psutil.Process()
            start_memory = process.memory_info().rss
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                
                # 记录结束状态
                end_memory = process.memory_info().rss
                end_time = time.time()
                
                memory_diff = end_memory - start_memory
                duration = end_time - start_time
                
                # 记录性能数据
                perf_data = {
                    'function': name,
                    'duration_ms': round(duration * 1000, 2),
                    'memory_diff_mb': round(memory_diff / 1024 / 1024, 2),
                    'start_memory_mb': round(start_memory / 1024 / 1024, 2),
                    'end_memory_mb': round(end_memory / 1024 / 1024, 2)
                }
                
                # 如果内存增长超过10MB或执行时间超过1秒，记录警告
                if abs(memory_diff) > 10 * 1024 * 1024 or duration > 1.0:
                    logger.warning("函数性能问题", perf_data)
                else:
                    logger.debug("函数性能数据", perf_data)
                
                return result
                
            except Exception as e:
                # 即使出现异常也记录内存使用
                end_memory = process.memory_info().rss
                memory_diff = end_memory - start_memory
                
                logger.error("函数执行异常", {
                    'function': name,
                    'error': str(e),
                    'memory_diff_mb': round(memory_diff / 1024 / 1024, 2)
                })
                raise
        
        return wrapper
    return decorator

def large_object_tracker(obj, description: str = None):
    """大对象跟踪器"""
    size = sys.getsizeof(obj)
    
    # 跟踪大于1MB的对象
    if size > 1024 * 1024:
        logger.info("发现大对象", {
            'description': description or str(type(obj)),
            'size_mb': round(size / 1024 / 1024, 2),
            'object_type': type(obj).__name__
        })
        
        # 将对象添加到全局监控器（如果存在）
        if hasattr(memory_optimizer, 'monitor'):
            memory_optimizer.monitor.large_objects.add(obj)
    
    return obj

def optimize_list_memory(data_list: List[Any], chunk_size: int = 1000) -> List[List[Any]]:
    """优化列表内存使用，将大列表分块处理"""
    if len(data_list) <= chunk_size:
        return [data_list]
    
    chunks = []
    for i in range(0, len(data_list), chunk_size):
        chunk = data_list[i:i + chunk_size]
        chunks.append(chunk)
    
    logger.info("列表分块优化", {
        'original_size': len(data_list),
        'chunk_size': chunk_size,
        'chunks_count': len(chunks)
    })
    
    return chunks

def clear_cache_if_memory_high(threshold_mb: int = 1000):
    """如果内存使用过高，清除缓存"""
    process = psutil.Process()
    current_memory_mb = process.memory_info().rss / 1024 / 1024
    
    if current_memory_mb > threshold_mb:
        logger.warning("内存使用过高，开始清除缓存", {
            'current_memory_mb': round(current_memory_mb, 2),
            'threshold_mb': threshold_mb
        })
        
        # 清除Python垃圾回收
        collected = gc.collect()
        
        # 这里可以添加其他缓存清除逻辑
        # 例如清除Redis缓存、文件缓存等
        
        new_memory_mb = process.memory_info().rss / 1024 / 1024
        freed_mb = current_memory_mb - new_memory_mb
        
        logger.info("缓存清除完成", {
            'objects_collected': collected,
            'memory_freed_mb': round(freed_mb, 2),
            'new_memory_mb': round(new_memory_mb, 2)
        })
        
        return True
    
    return False

# 全局内存优化器实例
memory_optimizer = MemoryOptimizer()

# 便捷函数
def start_memory_monitoring(interval: float = 10.0):
    """启动内存监控"""
    memory_optimizer.monitor.start_monitoring(interval)

def get_memory_stats() -> Dict[str, Any]:
    """获取内存统计"""
    return memory_optimizer.monitor.get_memory_stats()

def optimize_memory() -> Dict[str, Any]:
    """执行内存优化"""
    return memory_optimizer.optimize_memory()

def stop_memory_monitoring():
    """停止内存监控"""
    memory_optimizer.monitor.stop_monitoring()