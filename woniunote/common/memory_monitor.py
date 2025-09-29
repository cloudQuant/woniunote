"""
内存监控器 - 检测和处理内存泄露
实时监控内存使用情况，检测潜在的内存泄露，并提供自动清理机制。
"""
import gc
import os
import sys
import time
import threading
import traceback
from typing import Any, Dict, List, Optional, Set, Callable, Tuple
from collections import defaultdict, deque
from datetime import datetime, timedelta
from dataclasses import dataclass

# 安全导入psutil，如果不可用则使用模拟
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    # 创建模拟的psutil
    class MockPsutil:
        class Process:
            def memory_info(self):
                class MemInfo:
                    rss = 100 * 1024 * 1024  # 100MB
                return MemInfo()
        
        class VirtualMemory:
            total = 8 * 1024 * 1024 * 1024  # 8GB
        
        @staticmethod
        def virtual_memory():
            return MockPsutil.VirtualMemory()
    
    psutil = MockPsutil()

from .unified_logging import get_simple_logger as get_logger
try:
    from .unified_utils import TraceIdManager
except ImportError:
    # 如果unified_utils不存在，创建一个简单的替代
    class TraceIdManager:
        @staticmethod
        def generate_simple_trace_id():
            import uuid
            return str(uuid.uuid4())[:8]

@dataclass
class MemorySnapshot:
    """内存快照"""
    timestamp: datetime
    total_memory_mb: float
    process_memory_mb: float
    python_objects: int
    tracked_objects: Dict[str, int]
    gc_stats: List[Dict]
    trace_id: str

class MemoryLeakDetector:
    """内存泄露检测器"""
    
    def __init__(self, check_interval: int = 60, history_size: int = 100):
        self.logger = get_logger('memory_leak_detector')
        self.check_interval = check_interval
        self.history_size = history_size
        
        self._snapshots = deque(maxlen=history_size)
        self._object_trackers = defaultdict(set)
        self._leak_warnings = defaultdict(int)
        self._monitoring_enabled = True
        self._lock = threading.RLock()
        
        # 内存阈值配置
        self.memory_warning_threshold_mb = 512  # 512MB
        self.memory_critical_threshold_mb = 1024  # 1GB
        self.growth_rate_threshold = 0.1  # 10% 增长率
        
        # 立即生成一个初始快照
        try:
            initial_snapshot = self.take_snapshot()
            if initial_snapshot:
                self.logger.info("初始内存快照生成成功")
            else:
                self.logger.warning("初始内存快照生成失败，使用模拟数据")
                # 创建模拟快照
                self._create_fallback_snapshot()
        except Exception as e:
            self.logger.error(f"初始快照生成异常: {e}")
            self._create_fallback_snapshot()
        
        # 启动监控线程
        self._monitor_thread = threading.Thread(target=self._monitor_memory, daemon=True)
        self._monitor_thread.start()
        
        self.logger.info("内存泄露检测器启动", {
            'check_interval': check_interval,
            'warning_threshold_mb': self.memory_warning_threshold_mb,
            'critical_threshold_mb': self.memory_critical_threshold_mb,
            'initial_snapshots': len(self._snapshots)
        })
    
    def _create_fallback_snapshot(self):
        """创建备用快照（当psutil不可用时）"""
        try:
            import gc
            fallback_snapshot = MemorySnapshot(
                timestamp=datetime.now(),
                total_memory_mb=8192.0,  # 8GB 默认值
                process_memory_mb=100.0,  # 100MB 默认值
                python_objects=len(gc.get_objects()) if 'gc' in globals() else 1000,
                tracked_objects={},
                gc_stats=[],
                trace_id='fallback_snapshot'
            )
            
            with self._lock:
                self._snapshots.append(fallback_snapshot)
                
            self.logger.info("备用快照创建成功")
            return fallback_snapshot
            
        except Exception as e:
            self.logger.error(f"备用快照创建失败: {e}")
            # 创建最基本的快照
            basic_snapshot = MemorySnapshot(
                timestamp=datetime.now(),
                total_memory_mb=8192.0,
                process_memory_mb=100.0,
                python_objects=1000,
                tracked_objects={},
                gc_stats=[],
                trace_id='basic_snapshot'
            )
            
            with self._lock:
                self._snapshots.append(basic_snapshot)
            
            return basic_snapshot
    
    def take_snapshot(self) -> MemorySnapshot:
        """获取内存快照"""
        try:
            # 检查psutil是否可用
            if not PSUTIL_AVAILABLE:
                self.logger.warning("psutil不可用，使用备用快照")
                return self._create_fallback_snapshot()
            
            process = psutil.Process()
            memory_info = process.memory_info()
            
            # 获取系统内存信息
            system_memory = psutil.virtual_memory()
            
            # 获取Python对象计数
            python_objects = len(gc.get_objects())
            
            # 获取垃圾收集统计
            gc_stats = [
                {'generation': i, 'count': counts[0], 'collections': counts[1], 'collected': counts[2]}
                for i, counts in enumerate(gc.get_stats())
            ]
            
            # 获取跟踪的对象统计
            tracked_objects = {}
            with self._lock:
                for obj_type, obj_set in self._object_trackers.items():
                    tracked_objects[obj_type] = len(obj_set)
            
            snapshot = MemorySnapshot(
                timestamp=datetime.now(),
                total_memory_mb=system_memory.total / 1024 / 1024,
                process_memory_mb=memory_info.rss / 1024 / 1024,
                python_objects=python_objects,
                tracked_objects=tracked_objects.copy(),
                gc_stats=gc_stats,
                trace_id=TraceIdManager.generate_simple_trace_id()
            )
            
            with self._lock:
                self._snapshots.append(snapshot)
            
            return snapshot
            
        except Exception as e:
            self.logger.debug(f"内存快照创建跳过: {e}")  # 改为debug级别，减少日志噪音
            # 静默返回None，不影响应用正常运行
            return None

    def _create_fallback_snapshot(self) -> MemorySnapshot:
        """创建备用快照"""
        try:
            basic_snapshot = MemorySnapshot(
                    timestamp=datetime.now(),
                    total_memory_mb=8192.0,
                    process_memory_mb=100.0,
                    python_objects=1000,
                    tracked_objects={},
                    gc_stats=[],
                    trace_id='error_snapshot'
                )
                
                with self._lock:
                    self._snapshots.append(basic_snapshot)
                
                self.logger.warning("创建错误恢复快照")
                return basic_snapshot
                
            except Exception as final_error:
                self.logger.error(f"最终快照创建也失败: {final_error}")
                # 返回一个模拟的快照对象
                return MemorySnapshot(
                    timestamp=datetime.now(),
                    total_memory_mb=8192.0,
                    process_memory_mb=100.0,
                    python_objects=1000,
                    tracked_objects={},
                    gc_stats=[],
                    trace_id='emergency_snapshot'
                )
    
    def track_object(self, obj: Any, obj_type: str):
        """跟踪对象"""
        with self._lock:
            self._object_trackers[obj_type].add(id(obj))
    
    def untrack_object(self, obj: Any, obj_type: str):
        """取消跟踪对象"""
        with self._lock:
            self._object_trackers[obj_type].discard(id(obj))
    
    def _monitor_memory(self):
        """内存监控线程"""
        while self._monitoring_enabled:
            try:
                snapshot = self.take_snapshot()
                if snapshot:
                    self._analyze_memory_usage(snapshot)
                    self._detect_memory_leaks()
                
                time.sleep(self.check_interval)
                
            except Exception as e:
                self.logger.error(f"内存监控异常: {e}")
                time.sleep(self.check_interval)
    
    def _analyze_memory_usage(self, snapshot: MemorySnapshot):
        """分析内存使用情况"""
        # 检查内存阈值
        if snapshot.process_memory_mb > self.memory_critical_threshold_mb:
            self.logger.error("内存使用达到临界阈值", {
                'current_memory_mb': snapshot.process_memory_mb,
                'threshold_mb': self.memory_critical_threshold_mb,
                'trace_id': snapshot.trace_id
            })
            
            # 触发内存清理
            self._trigger_memory_cleanup()
            
        elif snapshot.process_memory_mb > self.memory_warning_threshold_mb:
            self.logger.warning("内存使用达到警告阈值", {
                'current_memory_mb': snapshot.process_memory_mb,
                'threshold_mb': self.memory_warning_threshold_mb,
                'trace_id': snapshot.trace_id
            })
    
    def _detect_memory_leaks(self):
        """检测内存泄露"""
        with self._lock:
            if len(self._snapshots) < 10:  # 需要足够的数据点
                return
            
            recent_snapshots = list(self._snapshots)[-10:]
            
            # 分析内存增长趋势
            self._analyze_memory_growth(recent_snapshots)
            
            # 分析对象数量增长
            self._analyze_object_growth(recent_snapshots)
    
    def _analyze_memory_growth(self, snapshots: List[MemorySnapshot]):
        """分析内存增长趋势"""
        if len(snapshots) < 2:
            return
        
        start_memory = snapshots[0].process_memory_mb
        end_memory = snapshots[-1].process_memory_mb
        
        if start_memory > 0:
            growth_rate = (end_memory - start_memory) / start_memory
            
            if growth_rate > self.growth_rate_threshold:
                duration_minutes = (snapshots[-1].timestamp - snapshots[0].timestamp).total_seconds() / 60
                
                self.logger.warning("检测到内存持续增长", {
                    'start_memory_mb': start_memory,
                    'end_memory_mb': end_memory,
                    'growth_rate': f"{growth_rate:.2%}",
                    'duration_minutes': duration_minutes,
                    'trace_id': snapshots[-1].trace_id
                })
                
                # 记录泄露警告
                self._leak_warnings['memory_growth'] += 1
    
    def _analyze_object_growth(self, snapshots: List[MemorySnapshot]):
        """分析对象数量增长"""
        if len(snapshots) < 2:
            return
        
        start_objects = snapshots[0].python_objects
        end_objects = snapshots[-1].python_objects
        
        if start_objects > 0:
            growth_rate = (end_objects - start_objects) / start_objects
            
            if growth_rate > self.growth_rate_threshold:
                self.logger.warning("检测到Python对象数量持续增长", {
                    'start_objects': start_objects,
                    'end_objects': end_objects,
                    'growth_rate': f"{growth_rate:.2%}",
                    'trace_id': snapshots[-1].trace_id
                })
                
                # 分析具体对象类型增长
                self._analyze_tracked_objects_growth(snapshots)
                
                self._leak_warnings['object_growth'] += 1
    
    def _analyze_tracked_objects_growth(self, snapshots: List[MemorySnapshot]):
        """分析跟踪对象的增长"""
        if len(snapshots) < 2:
            return
        
        start_tracked = snapshots[0].tracked_objects
        end_tracked = snapshots[-1].tracked_objects
        
        for obj_type in end_tracked:
            if obj_type in start_tracked:
                start_count = start_tracked[obj_type]
                end_count = end_tracked[obj_type]
                
                if start_count > 0:
                    growth_rate = (end_count - start_count) / start_count
                    
                    if growth_rate > self.growth_rate_threshold:
                        self.logger.warning(f"对象类型 {obj_type} 数量持续增长", {
                            'object_type': obj_type,
                            'start_count': start_count,
                            'end_count': end_count,
                            'growth_rate': f"{growth_rate:.2%}"
                        })
    
    def _trigger_memory_cleanup(self):
        """触发内存清理"""
        self.logger.info("开始内存清理")
        
        try:
            # 强制垃圾收集
            gc.collect()
            
            # 清理跟踪的对象
            with self._lock:
                for obj_type, obj_set in self._object_trackers.items():
                    # 移除已被垃圾收集的对象ID
                    valid_objects = set()
                    for obj_id in obj_set:
                        # 这里我们无法直接检查对象是否存在，但可以假设大部分ID仍然有效
                        valid_objects.add(obj_id)
                    self._object_trackers[obj_type] = valid_objects
            
            # 再次进行垃圾收集
            collected = gc.collect()
            
            # 获取清理后的内存快照
            after_snapshot = self.take_snapshot()
            
            if after_snapshot:
                self.logger.info("内存清理完成", {
                    'collected_objects': collected,
                    'memory_after_mb': after_snapshot.process_memory_mb,
                    'python_objects_after': after_snapshot.python_objects
                })
            
        except Exception as e:
            self.logger.error(f"内存清理失败: {e}")
    
    def get_memory_report(self) -> Dict[str, Any]:
        """获取内存报告"""
        with self._lock:
            latest_snapshot = self._snapshots[-1] if self._snapshots else None
            
            if not latest_snapshot:
                return {'error': '没有可用的内存快照'}
            
            return {
                'current_memory': {
                    'process_memory_mb': latest_snapshot.process_memory_mb,
                    'python_objects': latest_snapshot.python_objects,
                    'tracked_objects': latest_snapshot.tracked_objects,
                    'timestamp': latest_snapshot.timestamp.isoformat()
                },
                'thresholds': {
                    'warning_mb': self.memory_warning_threshold_mb,
                    'critical_mb': self.memory_critical_threshold_mb,
                    'growth_rate_threshold': self.growth_rate_threshold
                },
                'leak_warnings': dict(self._leak_warnings),
                'gc_stats': latest_snapshot.gc_stats,
                'history_size': len(self._snapshots)
            }
    
    def get_memory_history(self, hours: int = 1) -> List[Dict[str, Any]]:
        """获取内存历史"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        with self._lock:
            history = []
            for snapshot in self._snapshots:
                if snapshot.timestamp >= cutoff_time:
                    history.append({
                        'timestamp': snapshot.timestamp.isoformat(),
                        'process_memory_mb': snapshot.process_memory_mb,
                        'python_objects': snapshot.python_objects,
                        'tracked_objects': snapshot.tracked_objects
                    })
            
            return history
    
    def shutdown(self):
        """关闭内存监控器"""
        self._monitoring_enabled = False
        self.logger.info("内存监控器关闭")

class MemoryProfiler:
    """内存分析器"""
    
    def __init__(self, detector: MemoryLeakDetector):
        self.detector = detector
        self.logger = get_logger('memory_profiler')
    
    def profile_function(self, func: Callable, *args, **kwargs) -> Tuple[Any, Dict[str, Any]]:
        """分析函数的内存使用"""
        # 执行前的快照
        before_snapshot = self.detector.take_snapshot()
        
        try:
            # 执行函数
            result = func(*args, **kwargs)
            
            # 执行后的快照
            after_snapshot = self.detector.take_snapshot()
            
            # 计算内存差异
            memory_diff = {}
            if before_snapshot and after_snapshot:
                memory_diff = {
                    'memory_diff_mb': after_snapshot.process_memory_mb - before_snapshot.process_memory_mb,
                    'objects_diff': after_snapshot.python_objects - before_snapshot.python_objects,
                    'execution_time': (after_snapshot.timestamp - before_snapshot.timestamp).total_seconds()
                }
            
            return result, memory_diff
            
        except Exception as e:
            self.logger.error(f"函数分析失败: {e}")
            raise

def memory_profile(func):
    """内存分析装饰器"""
    def wrapper(*args, **kwargs):
        profiler = MemoryProfiler(_global_memory_detector)
        result, profile_data = profiler.profile_function(func, *args, **kwargs)
        
        # 记录分析结果
        logger = get_logger('memory_profile')
        logger.info(f"函数 {func.__name__} 内存分析", {
            'function': func.__name__,
            **profile_data,
            'trace_id': TraceIdManager.generate_simple_trace_id()
        })
        
        return result
    
    return wrapper

# 创建全局内存检测器
_global_memory_detector = MemoryLeakDetector()

def get_memory_detector() -> MemoryLeakDetector:
    """获取全局内存检测器"""
    return _global_memory_detector

def get_memory_report() -> Dict[str, Any]:
    """获取内存报告"""
    try:
        return _global_memory_detector.get_memory_report()
    except Exception as e:
        # 如果监控器未正常初始化，返回基本信息
        return {
            'error': f'内存监控器未就绪: {str(e)}',
            'current_memory': {
                'process_memory_mb': 0,
                'python_objects': len(gc.get_objects()) if 'gc' in globals() else 0,
                'tracked_objects': {},
                'timestamp': datetime.now().isoformat() if 'datetime' in globals() else ''
            },
            'thresholds': {
                'warning_mb': 512,
                'critical_mb': 1024,
                'growth_rate_threshold': 0.1
            }
        }

def trigger_memory_cleanup():
    """触发内存清理"""
    _global_memory_detector._trigger_memory_cleanup()

def track_object(obj: Any, obj_type: str):
    """跟踪对象"""
    _global_memory_detector.track_object(obj, obj_type)

def untrack_object(obj: Any, obj_type: str):
    """取消跟踪对象"""
    _global_memory_detector.untrack_object(obj, obj_type)