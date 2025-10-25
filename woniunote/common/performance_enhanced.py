#!/usr/bin/env python3
"""
Phase 5 高级性能优化模块
提供智能缓存策略、连接池优化、内存管理、异步处理增强等企业级性能功能
"""

import os
import gc
import time
import psutil
import asyncio
import threading
import multiprocessing
import logging
import json
import hashlib
from typing import Dict, Any, List, Optional, Callable, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from functools import wraps, lru_cache
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor, as_completed
import weakref
from enum import Enum
import pickle
import gzip
import base64

logger = logging.getLogger(__name__)

class CacheStrategy(Enum):
    """缓存策略枚举"""
    LRU = "lru"
    LFU = "lfu"
    FIFO = "fifo"
    ADAPTIVE = "adaptive"
    TIME_BASED = "time_based"

class PerformanceLevel(Enum):
    """性能级别枚举"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class PerformanceMetrics:
    """性能指标数据类"""
    timestamp: datetime
    cpu_usage: float
    memory_usage: float
    cache_hit_rate: float
    query_avg_time: float
    active_connections: int
    thread_count: int
    gc_count: int
    performance_score: float

class SmartCache:
    """智能缓存系统"""
    
    def __init__(self, max_size: int = 10000, strategy: CacheStrategy = CacheStrategy.ADAPTIVE):
        self.max_size = max_size
        self.strategy = strategy
        self.cache_data = {}
        self.access_count = defaultdict(int)
        self.access_time = {}
        self.creation_time = {}
        self.hit_count = 0
        self.miss_count = 0
        self.lock = threading.RLock()
        
        # 自适应参数
        self.adaptive_threshold = 0.8  # 命中率阈值
        self.strategy_switch_count = 0
        self.last_strategy_switch = time.time()
        
    def _calculate_cache_score(self, key: str) -> float:
        """计算缓存项的分数（用于智能淘汰）"""
        current_time = time.time()
        
        # 访问频率分数
        frequency_score = self.access_count[key] / 100.0
        
        # 时间新鲜度分数
        if key in self.access_time:
            time_since_access = current_time - self.access_time[key]
            recency_score = max(0, 1 - time_since_access / 3600)  # 1小时内的权重
        else:
            recency_score = 0
        
        # 数据年龄分数
        if key in self.creation_time:
            age = current_time - self.creation_time[key]
            age_score = max(0, 1 - age / 7200)  # 2小时内的权重
        else:
            age_score = 0
        
        # 综合分数
        return frequency_score * 0.4 + recency_score * 0.4 + age_score * 0.2
    
    def _evict_items(self, count: int = 1):
        """智能淘汰缓存项"""
        if len(self.cache_data) <= count:
            return
        
        if self.strategy == CacheStrategy.LRU:
            # LRU: 淘汰最近最少使用的
            sorted_items = sorted(
                self.access_time.items(),
                key=lambda x: x[1]
            )
            keys_to_remove = [item[0] for item in sorted_items[:count]]
        
        elif self.strategy == CacheStrategy.LFU:
            # LFU: 淘汰使用频率最低的
            sorted_items = sorted(
                self.access_count.items(),
                key=lambda x: x[1]
            )
            keys_to_remove = [item[0] for item in sorted_items[:count]]
        
        elif self.strategy == CacheStrategy.FIFO:
            # FIFO: 淘汰最早创建的
            sorted_items = sorted(
                self.creation_time.items(),
                key=lambda x: x[1]
            )
            keys_to_remove = [item[0] for item in sorted_items[:count]]
        
        elif self.strategy == CacheStrategy.ADAPTIVE:
            # 自适应: 基于综合分数
            scores = {
                key: self._calculate_cache_score(key)
                for key in self.cache_data.keys()
            }
            sorted_items = sorted(scores.items(), key=lambda x: x[1])
            keys_to_remove = [item[0] for item in sorted_items[:count]]
        
        else:  # TIME_BASED
            # 基于时间的淘汰
            current_time = time.time()
            expired_keys = [
                key for key, timestamp in self.creation_time.items()
                if current_time - timestamp > 3600  # 1小时过期
            ]
            keys_to_remove = expired_keys[:count] if len(expired_keys) >= count else list(self.cache_data.keys())[:count]
        
        # 删除选中的项
        for key in keys_to_remove:
            if key in self.cache_data:
                del self.cache_data[key]
                del self.access_count[key]
                if key in self.access_time:
                    del self.access_time[key]
                if key in self.creation_time:
                    del self.creation_time[key]
    
    def _adaptive_strategy_adjustment(self):
        """自适应策略调整"""
        if self.strategy != CacheStrategy.ADAPTIVE:
            return
        
        total_requests = self.hit_count + self.miss_count
        if total_requests < 100:  # 样本太小，不调整
            return
        
        current_hit_rate = self.hit_count / total_requests
        current_time = time.time()
        
        # 如果命中率低于阈值，考虑切换策略
        if current_hit_rate < self.adaptive_threshold:
            if current_time - self.last_strategy_switch > 300:  # 5分钟内只能切换一次
                # 尝试不同的策略
                strategies = [CacheStrategy.LRU, CacheStrategy.LFU, CacheStrategy.TIME_BASED]
                self.strategy = strategies[self.strategy_switch_count % len(strategies)]
                self.strategy_switch_count += 1
                self.last_strategy_switch = current_time
                
                logger.info(f"Adaptive cache strategy switched to {self.strategy.value}")
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存项"""
        with self.lock:
            if key in self.cache_data:
                self.hit_count += 1
                self.access_count[key] += 1
                self.access_time[key] = time.time()
                
                # 解压数据（如果已压缩）
                data = self.cache_data[key]
                if isinstance(data, dict) and 'compressed' in data:
                    try:
                        compressed_data = base64.b64decode(data['data'])
                        return pickle.loads(gzip.decompress(compressed_data))
                    except Exception as e:
                        logger.error(f"Cache decompression error: {e}")
                        return None
                
                return data
            else:
                self.miss_count += 1
                self._adaptive_strategy_adjustment()
                return None
    
    def set(self, key: str, value: Any, ttl: int = None, compress: bool = False) -> bool:
        """设置缓存项"""
        try:
            with self.lock:
                # 检查是否需要淘汰
                if len(self.cache_data) >= self.max_size:
                    self._evict_items(max(1, self.max_size // 10))  # 淘汰10%的项
                
                # 数据压缩（对大对象）
                if compress or (hasattr(value, '__sizeof__') and value.__sizeof__() > 1024):
                    try:
                        serialized = pickle.dumps(value)
                        if len(serialized) > 512:  # 大于512字节才压缩
                            compressed = gzip.compress(serialized)
                            encoded = base64.b64encode(compressed).decode()
                            value = {
                                'compressed': True,
                                'data': encoded,
                                'original_size': len(serialized),
                                'compressed_size': len(compressed)
                            }
                    except Exception as e:
                        logger.warning(f"Cache compression failed: {e}")
                
                self.cache_data[key] = value
                self.access_count[key] = 1
                self.access_time[key] = time.time()
                self.creation_time[key] = time.time()
                
                return True
                
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """删除缓存项"""
        with self.lock:
            if key in self.cache_data:
                del self.cache_data[key]
                del self.access_count[key]
                if key in self.access_time:
                    del self.access_time[key]
                if key in self.creation_time:
                    del self.creation_time[key]
                return True
            return False
    
    def clear(self):
        """清空缓存"""
        with self.lock:
            self.cache_data.clear()
            self.access_count.clear()
            self.access_time.clear()
            self.creation_time.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        with self.lock:
            total_requests = self.hit_count + self.miss_count
            hit_rate = self.hit_count / total_requests if total_requests > 0 else 0
            
            # 计算内存使用情况
            memory_usage = 0
            for value in self.cache_data.values():
                try:
                    if hasattr(value, '__sizeof__'):
                        memory_usage += value.__sizeof__()
                    else:
                        memory_usage += len(str(value))
                except:
                    memory_usage += 100  # 估算值
            
            return {
                'size': len(self.cache_data),
                'max_size': self.max_size,
                'hit_count': self.hit_count,
                'miss_count': self.miss_count,
                'hit_rate': hit_rate,
                'strategy': self.strategy.value,
                'memory_usage_bytes': memory_usage,
                'memory_usage_mb': memory_usage / 1024 / 1024,
                'strategy_switches': self.strategy_switch_count
            }

class ConnectionPoolOptimizer:
    """连接池优化器"""
    
    def __init__(self):
        self.pool_stats = {}
        self.connection_metrics = defaultdict(list)
        self.lock = threading.Lock()
        
    def monitor_connection_pool(self, pool_name: str, pool_info: Dict[str, Any]):
        """监控连接池状态"""
        with self.lock:
            timestamp = time.time()
            
            # 记录连接池指标
            metrics = {
                'timestamp': timestamp,
                'size': pool_info.get('size', 0),
                'checked_out': pool_info.get('checked_out', 0),
                'overflow': pool_info.get('overflow', 0),
                'invalid': pool_info.get('invalid', 0)
            }
            
            self.connection_metrics[pool_name].append(metrics)
            
            # 保持最近100个记录
            if len(self.connection_metrics[pool_name]) > 100:
                self.connection_metrics[pool_name].pop(0)
            
            # 更新统计信息
            self.pool_stats[pool_name] = metrics
    
    def get_pool_recommendations(self, pool_name: str) -> List[str]:
        """获取连接池优化建议"""
        recommendations = []
        
        with self.lock:
            if pool_name not in self.connection_metrics:
                return recommendations
            
            recent_metrics = self.connection_metrics[pool_name][-10:]  # 最近10个记录
            
            if recent_metrics:
                avg_checked_out = sum(m['checked_out'] for m in recent_metrics) / len(recent_metrics)
                avg_size = sum(m['size'] for m in recent_metrics) / len(recent_metrics)
                avg_overflow = sum(m['overflow'] for m in recent_metrics) / len(recent_metrics)
                
                # 检查连接池使用率
                utilization = avg_checked_out / avg_size if avg_size > 0 else 0
                
                if utilization > 0.9:
                    recommendations.append("连接池使用率过高，建议增加池大小")
                elif utilization < 0.3:
                    recommendations.append("连接池使用率过低，可考虑减少池大小")
                
                if avg_overflow > 0:
                    recommendations.append("存在连接溢出，建议增加池大小或优化连接使用")
                
                # 检查无效连接
                recent_invalid = [m['invalid'] for m in recent_metrics[-5:]]
                if any(invalid > 0 for invalid in recent_invalid):
                    recommendations.append("检测到无效连接，建议检查网络稳定性")
        
        return recommendations

class MemoryOptimizer:
    """内存优化器"""
    
    def __init__(self):
        self.gc_stats = []
        self.memory_snapshots = []
        self.weak_references = weakref.WeakValueDictionary()
        self.memory_threshold = 0.85  # 85%内存使用率阈值
        
    def get_memory_info(self) -> Dict[str, Any]:
        """获取内存信息"""
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            system_memory = psutil.virtual_memory()
            
            return {
                'process_memory_mb': memory_info.rss / 1024 / 1024,
                'process_memory_percent': process.memory_percent(),
                'system_memory_percent': system_memory.percent,
                'system_available_mb': system_memory.available / 1024 / 1024,
                'system_total_mb': system_memory.total / 1024 / 1024
            }
        except Exception as e:
            logger.error(f"Memory info collection error: {e}")
            return {}
    
    def trigger_gc_if_needed(self) -> bool:
        """根据需要触发垃圾回收"""
        memory_info = self.get_memory_info()
        
        if memory_info and memory_info.get('system_memory_percent', 0) > self.memory_threshold * 100:
            logger.info("Memory threshold exceeded, triggering garbage collection")
            
            # 记录GC前状态
            before_memory = memory_info['process_memory_mb']
            before_objects = len(gc.get_objects())
            
            # 执行垃圾回收
            gc_start = time.time()
            collected = gc.collect()
            gc_duration = time.time() - gc_start
            
            # 记录GC后状态
            after_memory = self.get_memory_info()['process_memory_mb']
            after_objects = len(gc.get_objects())
            
            # 记录GC统计
            gc_stat = {
                'timestamp': time.time(),
                'duration': gc_duration,
                'objects_before': before_objects,
                'objects_after': after_objects,
                'memory_before_mb': before_memory,
                'memory_after_mb': after_memory,
                'memory_freed_mb': before_memory - after_memory,
                'objects_collected': collected
            }
            
            self.gc_stats.append(gc_stat)
            
            # 保持最近50个GC记录
            if len(self.gc_stats) > 50:
                self.gc_stats.pop(0)
            
            logger.info(f"GC completed: freed {gc_stat['memory_freed_mb']:.2f}MB, collected {collected} objects")
            return True
        
        return False
    
    def create_memory_snapshot(self) -> str:
        """创建内存快照"""
        snapshot_id = f"snapshot_{int(time.time())}"
        
        try:
            memory_info = self.get_memory_info()
            object_counts = {}
            
            # 统计对象类型
            for obj in gc.get_objects():
                obj_type = type(obj).__name__
                object_counts[obj_type] = object_counts.get(obj_type, 0) + 1
            
            snapshot = {
                'id': snapshot_id,
                'timestamp': time.time(),
                'memory_info': memory_info,
                'object_counts': object_counts,
                'total_objects': len(gc.get_objects())
            }
            
            self.memory_snapshots.append(snapshot)
            
            # 保持最近10个快照
            if len(self.memory_snapshots) > 10:
                self.memory_snapshots.pop(0)
            
            return snapshot_id
            
        except Exception as e:
            logger.error(f"Memory snapshot creation error: {e}")
            return ""
    
    def get_memory_recommendations(self) -> List[str]:
        """获取内存优化建议"""
        recommendations = []
        
        if len(self.memory_snapshots) < 2:
            return recommendations
        
        latest = self.memory_snapshots[-1]
        previous = self.memory_snapshots[-2]
        
        # 内存增长分析
        memory_growth = latest['memory_info']['process_memory_mb'] - previous['memory_info']['process_memory_mb']
        if memory_growth > 50:  # 增长超过50MB
            recommendations.append(f"内存使用量增长较快（+{memory_growth:.1f}MB），建议检查是否存在内存泄漏")
        
        # 对象数量分析
        object_growth = latest['total_objects'] - previous['total_objects']
        if object_growth > 10000:  # 对象增长超过1万
            recommendations.append(f"对象数量增长较快（+{object_growth}），建议检查对象生命周期管理")
        
        # GC频率分析
        if len(self.gc_stats) > 5:
            recent_gcs = self.gc_stats[-5:]
            avg_interval = (recent_gcs[-1]['timestamp'] - recent_gcs[0]['timestamp']) / 4
            if avg_interval < 60:  # GC间隔小于1分钟
                recommendations.append("垃圾回收过于频繁，建议优化对象创建和销毁模式")
        
        return recommendations

class AsyncTaskOptimizer:
    """异步任务优化器"""
    
    def __init__(self, max_workers: int = None):
        self.max_workers = max_workers or min(32, (os.cpu_count() or 1) + 4)
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
        self.task_queue = deque()
        self.completed_tasks = []
        self.failed_tasks = []
        self.task_stats = defaultdict(list)
        self.lock = threading.Lock()
        
    def submit_task(self, func: Callable, *args, priority: int = 5, timeout: int = 300, **kwargs) -> str:
        """提交异步任务"""
        task_id = f"task_{int(time.time() * 1000)}_{id(func)}"
        
        task_info = {
            'id': task_id,
            'function': func.__name__,
            'priority': priority,
            'timeout': timeout,
            'submitted_at': time.time(),
            'status': 'pending'
        }
        
        with self.lock:
            self.task_queue.append(task_info)
        
        # 提交到线程池
        future = self.executor.submit(self._execute_task, task_info, func, *args, **kwargs)
        task_info['future'] = future
        
        return task_id
    
    def _execute_task(self, task_info: Dict, func: Callable, *args, **kwargs) -> Any:
        """执行任务"""
        start_time = time.time()
        task_info['started_at'] = start_time
        task_info['status'] = 'running'
        
        try:
            result = func(*args, **kwargs)
            end_time = time.time()
            
            task_info.update({
                'status': 'completed',
                'completed_at': end_time,
                'duration': end_time - start_time,
                'result': result
            })
            
            with self.lock:
                self.completed_tasks.append(task_info)
                self.task_stats[func.__name__].append({
                    'duration': task_info['duration'],
                    'timestamp': end_time,
                    'success': True
                })
            
            return result
            
        except Exception as e:
            end_time = time.time()
            
            task_info.update({
                'status': 'failed',
                'completed_at': end_time,
                'duration': end_time - start_time,
                'error': str(e)
            })
            
            with self.lock:
                self.failed_tasks.append(task_info)
                self.task_stats[func.__name__].append({
                    'duration': task_info['duration'],
                    'timestamp': end_time,
                    'success': False,
                    'error': str(e)
                })
            
            logger.error(f"Task {task_info['id']} failed: {e}")
            raise
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        # 在各个列表中搜索任务
        all_tasks = list(self.task_queue) + self.completed_tasks + self.failed_tasks
        
        for task in all_tasks:
            if task['id'] == task_id:
                task_copy = task.copy()
                # 移除不可序列化的对象
                if 'future' in task_copy:
                    del task_copy['future']
                return task_copy
        
        return None
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计"""
        with self.lock:
            total_completed = len(self.completed_tasks)
            total_failed = len(self.failed_tasks)
            total_tasks = total_completed + total_failed
            
            if total_tasks == 0:
                return {
                    'total_tasks': 0,
                    'success_rate': 0,
                    'avg_duration': 0,
                    'function_stats': {}
                }
            
            # 计算平均执行时间
            all_durations = []
            for task in self.completed_tasks + self.failed_tasks:
                if 'duration' in task:
                    all_durations.append(task['duration'])
            
            avg_duration = sum(all_durations) / len(all_durations) if all_durations else 0
            
            # 按函数统计
            function_stats = {}
            for func_name, stats in self.task_stats.items():
                successful = [s for s in stats if s['success']]
                function_stats[func_name] = {
                    'total_calls': len(stats),
                    'successful_calls': len(successful),
                    'success_rate': len(successful) / len(stats) if stats else 0,
                    'avg_duration': sum(s['duration'] for s in successful) / len(successful) if successful else 0
                }
            
            return {
                'total_tasks': total_tasks,
                'completed_tasks': total_completed,
                'failed_tasks': total_failed,
                'success_rate': total_completed / total_tasks,
                'avg_duration': avg_duration,
                'queue_size': len(self.task_queue),
                'function_stats': function_stats
            }

class PerformanceMonitorAdvanced:
    """高级性能监控器"""
    
    def __init__(self):
        self.metrics_history = deque(maxlen=1000)
        self.alert_thresholds = {
            'cpu_usage': 80.0,
            'memory_usage': 85.0,
            'cache_hit_rate': 70.0,
            'query_avg_time': 1000.0,  # 毫秒
            'error_rate': 5.0
        }
        self.alerts = []
        self.lock = threading.Lock()
        
    def collect_metrics(self) -> PerformanceMetrics:
        """收集性能指标"""
        try:
            # 系统指标 - 使用非阻塞模式获取更准确的CPU使用率
            cpu_usage = psutil.cpu_percent(interval=None)
            
            # 如果第一次调用返回0，使用带间隔的方式
            if cpu_usage == 0 or not hasattr(self, '_perf_cpu_initialized'):
                cpu_usage = psutil.cpu_percent(interval=1.0)
                self._perf_cpu_initialized = True
            
            # 平滑处理
            if not hasattr(self, '_perf_cpu_samples'):
                self._perf_cpu_samples = []
            
            self._perf_cpu_samples.append(cpu_usage)
            if len(self._perf_cpu_samples) > 5:
                self._perf_cpu_samples.pop(0)
            
            cpu_usage = sum(self._perf_cpu_samples) / len(self._perf_cpu_samples)
            
            memory = psutil.virtual_memory()
            memory_usage = memory.percent
            
            # 应用指标（需要从其他组件获取）
            cache_hit_rate = 0.0  # 从缓存管理器获取
            query_avg_time = 0.0  # 从数据库优化器获取
            active_connections = 0  # 从连接池获取
            thread_count = threading.active_count()
            gc_count = len(gc.get_objects())
            
            # 计算性能分数
            performance_score = self._calculate_performance_score(
                cpu_usage, memory_usage, cache_hit_rate, query_avg_time
            )
            
            metrics = PerformanceMetrics(
                timestamp=datetime.now(),
                cpu_usage=cpu_usage,
                memory_usage=memory_usage,
                cache_hit_rate=cache_hit_rate,
                query_avg_time=query_avg_time,
                active_connections=active_connections,
                thread_count=thread_count,
                gc_count=gc_count,
                performance_score=performance_score
            )
            
            with self.lock:
                self.metrics_history.append(metrics)
                self._check_alerts(metrics)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Metrics collection error: {e}")
            return None
    
    def _calculate_performance_score(self, cpu: float, memory: float, 
                                   cache_hit_rate: float, query_time: float) -> float:
        """计算综合性能分数"""
        # CPU分数 (越低越好)
        cpu_score = max(0, 100 - cpu)
        
        # 内存分数 (越低越好)
        memory_score = max(0, 100 - memory)
        
        # 缓存命中率分数 (越高越好)
        cache_score = cache_hit_rate
        
        # 查询时间分数 (越低越好)
        query_score = max(0, 100 - query_time / 10)
        
        # 综合分数
        performance_score = (cpu_score * 0.3 + memory_score * 0.3 + 
                           cache_score * 0.2 + query_score * 0.2)
        
        return min(100, max(0, performance_score))
    
    def _check_alerts(self, metrics: PerformanceMetrics):
        """检查告警条件"""
        current_time = time.time()
        
        # CPU告警
        if metrics.cpu_usage > self.alert_thresholds['cpu_usage']:
            self.alerts.append({
                'timestamp': current_time,
                'type': 'cpu_high',
                'message': f"CPU使用率过高: {metrics.cpu_usage:.1f}%",
                'severity': 'warning' if metrics.cpu_usage < 90 else 'critical'
            })
        
        # 内存告警
        if metrics.memory_usage > self.alert_thresholds['memory_usage']:
            self.alerts.append({
                'timestamp': current_time,
                'type': 'memory_high',
                'message': f"内存使用率过高: {metrics.memory_usage:.1f}%",
                'severity': 'warning' if metrics.memory_usage < 95 else 'critical'
            })
        
        # 缓存命中率告警
        if metrics.cache_hit_rate < self.alert_thresholds['cache_hit_rate']:
            self.alerts.append({
                'timestamp': current_time,
                'type': 'cache_low',
                'message': f"缓存命中率过低: {metrics.cache_hit_rate:.1f}%",
                'severity': 'warning'
            })
        
        # 查询时间告警
        if metrics.query_avg_time > self.alert_thresholds['query_avg_time']:
            self.alerts.append({
                'timestamp': current_time,
                'type': 'query_slow',
                'message': f"查询平均时间过长: {metrics.query_avg_time:.0f}ms",
                'severity': 'warning'
            })
        
        # 保持最近100个告警
        if len(self.alerts) > 100:
            self.alerts = self.alerts[-100:]
    
    def get_performance_summary(self, hours: int = 1) -> Dict[str, Any]:
        """获取性能摘要"""
        with self.lock:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            recent_metrics = [
                m for m in self.metrics_history
                if m.timestamp >= cutoff_time
            ]
        
        if not recent_metrics:
            return {}
        
        # 计算统计值
        cpu_values = [m.cpu_usage for m in recent_metrics]
        memory_values = [m.memory_usage for m in recent_metrics]
        performance_scores = [m.performance_score for m in recent_metrics]
        
        return {
            'time_range_hours': hours,
            'sample_count': len(recent_metrics),
            'cpu_usage': {
                'avg': sum(cpu_values) / len(cpu_values),
                'max': max(cpu_values),
                'min': min(cpu_values)
            },
            'memory_usage': {
                'avg': sum(memory_values) / len(memory_values),
                'max': max(memory_values),
                'min': min(memory_values)
            },
            'performance_score': {
                'avg': sum(performance_scores) / len(performance_scores),
                'max': max(performance_scores),
                'min': min(performance_scores)
            },
            'recent_alerts': [a for a in self.alerts if a['timestamp'] > time.time() - hours * 3600]
        }

class PerformanceEnhancementManager:
    """性能增强管理器主类"""
    
    def __init__(self, app=None):
        self.app = app
        self.smart_cache = SmartCache()
        self.connection_optimizer = ConnectionPoolOptimizer()
        self.memory_optimizer = MemoryOptimizer()
        self.async_optimizer = AsyncTaskOptimizer()
        self.performance_monitor = PerformanceMonitorAdvanced()
        
        # 性能优化配置
        self.auto_optimization_enabled = True
        self.optimization_interval = 300  # 5分钟
        self.last_optimization = time.time()
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """初始化Flask应用"""
        self.app = app
        
        # 启动后台优化任务
        if self.auto_optimization_enabled:
            self._start_background_optimization()
        
        logger.info("Performance enhancement manager initialized")
    
    def _start_background_optimization(self):
        """启动后台优化任务"""
        def optimization_worker():
            while self.auto_optimization_enabled:
                try:
                    self._run_optimization_cycle()
                    time.sleep(self.optimization_interval)
                except Exception as e:
                    logger.error(f"Background optimization error: {e}")
                    time.sleep(60)  # 出错后等待1分钟
        
        optimization_thread = threading.Thread(target=optimization_worker, daemon=True)
        optimization_thread.start()
    
    def _run_optimization_cycle(self):
        """运行优化周期"""
        current_time = time.time()
        
        # 收集性能指标
        metrics = self.performance_monitor.collect_metrics()
        
        # 内存优化
        if self.memory_optimizer.trigger_gc_if_needed():
            logger.info("Automatic garbage collection triggered")
        
        # 缓存优化
        cache_stats = self.smart_cache.get_stats()
        if cache_stats['hit_rate'] < 0.7 and cache_stats['size'] > 100:
            # 如果命中率低，触发缓存策略调整
            self.smart_cache._adaptive_strategy_adjustment()
        
        # 创建内存快照（每小时一次）
        if current_time - self.last_optimization > 3600:
            self.memory_optimizer.create_memory_snapshot()
            self.last_optimization = current_time
        
        logger.debug("Optimization cycle completed")
    
    def get_comprehensive_report(self) -> Dict[str, Any]:
        """获取综合性能报告"""
        return {
            'timestamp': datetime.now().isoformat(),
            'cache_stats': self.smart_cache.get_stats(),
            'memory_info': self.memory_optimizer.get_memory_info(),
            'async_stats': self.async_optimizer.get_performance_stats(),
            'performance_summary': self.performance_monitor.get_performance_summary(),
            'optimization_recommendations': self._get_optimization_recommendations()
        }
    
    def _get_optimization_recommendations(self) -> List[str]:
        """获取优化建议"""
        recommendations = []
        
        # 缓存优化建议
        cache_stats = self.smart_cache.get_stats()
        if cache_stats['hit_rate'] < 0.6:
            recommendations.append("缓存命中率较低，建议检查缓存策略")
        
        if cache_stats['memory_usage_mb'] > 100:
            recommendations.append("缓存内存使用较高，考虑调整缓存大小")
        
        # 内存优化建议
        recommendations.extend(self.memory_optimizer.get_memory_recommendations())
        
        # 异步任务建议
        async_stats = self.async_optimizer.get_performance_stats()
        if async_stats['success_rate'] < 0.9:
            recommendations.append("异步任务成功率较低，建议检查任务实现")
        
        return recommendations

# 全局性能增强管理器实例
_performance_manager = None

def get_performance_manager() -> PerformanceEnhancementManager:
    """获取性能增强管理器实例"""
    global _performance_manager
    if _performance_manager is None:
        _performance_manager = PerformanceEnhancementManager()
    return _performance_manager

def init_performance_enhancement(app):
    """初始化性能增强系统"""
    try:
        performance_manager = get_performance_manager()
        performance_manager.init_app(app)
        
        logger.info("Performance enhancement system initialized successfully")
        return performance_manager
        
    except Exception as e:
        logger.error(f"Failed to initialize performance enhancement system: {e}")
        raise

# 装饰器函数
def smart_cache(ttl: int = 300, strategy: CacheStrategy = CacheStrategy.ADAPTIVE):
    """智能缓存装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存键
            cache_key = f"{func.__name__}:{hashlib.md5(str(args + tuple(kwargs.items())).encode()).hexdigest()}"
            
            # 尝试从缓存获取
            performance_manager = get_performance_manager()
            cached_result = performance_manager.smart_cache.get(cache_key)
            
            if cached_result is not None:
                return cached_result
            
            # 执行函数并缓存结果
            result = func(*args, **kwargs)
            performance_manager.smart_cache.set(cache_key, result, ttl)
            
            return result
        
        return wrapper
    return decorator

def async_task(priority: int = 5, timeout: int = 300):
    """异步任务装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            performance_manager = get_performance_manager()
            task_id = performance_manager.async_optimizer.submit_task(
                func, *args, priority=priority, timeout=timeout, **kwargs
            )
            return task_id
        
        return wrapper
    return decorator

def monitor_performance(func):
    """性能监控装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        
        try:
            result = func(*args, **kwargs)
            duration = time.time() - start_time
            
            # 记录性能指标
            performance_manager = get_performance_manager()
            logger.debug(f"Function {func.__name__} executed in {duration:.3f}s")
            
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Function {func.__name__} failed after {duration:.3f}s: {e}")
            raise
    
    return wrapper 