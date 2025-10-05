'''
内存监控器 - 检测和处理内存泄露
实时监控内存使用情况，检测潜在的内存泄露，并提供自动清理机制。
'''
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
    class MockPsutil:
        class Process:
            def memory_info(self):
                class MemInfo:
                    rss = 100 * 1024 * 1024
                return MemInfo()
        class VirtualMemory:
            total = 8 * 1024 * 1024 * 1024
        @staticmethod
        def virtual_memory():
            return MockPsutil.VirtualMemory()
    psutil = MockPsutil()

from .unified_logging import get_simple_logger as get_logger
try:
    from .unified_utils import TraceIdManager
except ImportError:
    class TraceIdManager:
        @staticmethod
        def generate_simple_trace_id():
            import uuid
            return str(uuid.uuid4())[:8]

@dataclass
class MemorySnapshot:
    timestamp: datetime
    total_memory_mb: float
    process_memory_mb: float
    python_objects: int
    tracked_objects: Dict[str, int]
    gc_stats: List[Dict]
    trace_id: str

class MemoryLeakDetector:
    def __init__(self, check_interval: int = 60, history_size: int = 100):
        self.logger = get_logger('memory_leak_detector')
        self.check_interval = check_interval
        self.history_size = history_size
        self._snapshots = deque(maxlen=history_size)
        self._object_trackers = defaultdict(set)
        self._leak_warnings = defaultdict(int)
        self._monitoring_enabled = True
        self._lock = threading.RLock()
        self.memory_warning_threshold_mb = 512
        self.memory_critical_threshold_mb = 1024
        self.growth_rate_threshold = 0.1
        try:
            if not PSUTIL_AVAILABLE:
                self.logger.warning("psutil不可用，无法生成初始快照")
                self._create_fallback_snapshot()
            else:
                initial_snapshot = self.take_snapshot()
                if initial_snapshot:
                    self.logger.info("初始内存快照生成成功")
                else:
                    self.logger.warning("初始内存快照生成失败，使用模拟数据")
                    self._create_fallback_snapshot()
        except Exception as e:
            self.logger.error(f"初始快照生成异常: {repr(e)}")
            self._create_fallback_snapshot()
        self._monitor_thread = threading.Thread(target=self._monitor_memory, daemon=True)
        self._monitor_thread.start()
        self.logger.info("内存泄露检测器启动", {
            'check_interval': check_interval,
            'warning_threshold_mb': self.memory_warning_threshold_mb,
            'critical_threshold_mb': self.memory_critical_threshold_mb,
            'initial_snapshots': len(self._snapshots)
        })
    
    def take_snapshot(self) -> Optional[MemorySnapshot]:
        if not PSUTIL_AVAILABLE:
            self.logger.warning("psutil不可用，使用备用快照")
            return self._create_fallback_snapshot()
        process = psutil.Process()
        memory_info = process.memory_info()
        system_memory = psutil.virtual_memory()
        python_objects = len(gc.get_objects())
        try:
            stats_data = gc.get_stats()
            gc_stats = [
                {
                    'generation': i,
                    'collections': stats.get('collections', 0),
                    'collected': stats.get('collected', 0),
                    'uncollectable': stats.get('uncollectable', 0)
                }
                for i, stats in enumerate(stats_data)
            ]
        except Exception as e:
            self.logger.warning(f"无法获取GC统计信息: {repr(e)}")
            gc_stats = []
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

    def _create_fallback_snapshot(self) -> Optional[MemorySnapshot]:
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
        with self._lock:
            self._object_trackers[obj_type].add(id(obj))
    
    def untrack_object(self, obj: Any, obj_type: str):
        with self._lock:
            self._object_trackers[obj_type].discard(id(obj))
    
    def _monitor_memory(self):
        while self._monitoring_enabled:
            try:
                snapshot = self.take_snapshot()
                if snapshot:
                    self._analyze_memory_usage(snapshot)
                    self._detect_memory_leaks()
                time.sleep(self.check_interval)
            except Exception as e:
                self.logger.debug(f"内存监控异常: {repr(e)}")
                time.sleep(self.check_interval * 2)
    
    def _analyze_memory_usage(self, snapshot: MemorySnapshot):
        if snapshot.process_memory_mb > self.memory_critical_threshold_mb:
            self.logger.error("内存使用达到临界阈值", {
                'current_memory_mb': snapshot.process_memory_mb,
                'threshold_mb': self.memory_critical_threshold_mb,
                'trace_id': snapshot.trace_id
            })
            self._trigger_memory_cleanup()
        elif snapshot.process_memory_mb > self.memory_warning_threshold_mb:
            self.logger.warning("内存使用达到警告阈值", {
                'current_memory_mb': snapshot.process_memory_mb,
                'threshold_mb': self.memory_warning_threshold_mb,
                'trace_id': snapshot.trace_id
            })
    
    def _detect_memory_leaks(self):
        with self._lock:
            if len(self._snapshots) < 10:
                return
            recent_snapshots = list(self._snapshots)[-10:]
            self._analyze_memory_growth(recent_snapshots)
            self._analyze_object_growth(recent_snapshots)
    
    def _analyze_memory_growth(self, snapshots: List[MemorySnapshot]):
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
                self._leak_warnings['memory_growth'] += 1
    
    def _analyze_object_growth(self, snapshots: List[MemorySnapshot]):
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
                self._analyze_tracked_objects_growth(snapshots)
                self._leak_warnings['object_growth'] += 1
    
    def _analyze_tracked_objects_growth(self, snapshots: List[MemorySnapshot]):
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
        self.logger.info("开始内存清理")
        try:
            gc.collect()
            with self._lock:
                for obj_type, obj_set in self._object_trackers.items():
                    valid_objects = set()
                    for obj_id in obj_set:
                        valid_objects.add(obj_id)
                    self._object_trackers[obj_type] = valid_objects
            collected = gc.collect()
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
        self._monitoring_enabled = False
        self.logger.info("内存监控器关闭")

class MemoryProfiler:
    def __init__(self, detector: MemoryLeakDetector):
        self.detector = detector
        self.logger = get_logger('memory_profiler')
    
    def profile_function(self, func: Callable, *args, **kwargs) -> Tuple[Any, Dict[str, Any]]:
        before_snapshot = self.detector.take_snapshot()
        try:
            result = func(*args, **kwargs)
            after_snapshot = self.detector.take_snapshot()
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
    def wrapper(*args, **kwargs):
        profiler = MemoryProfiler(_global_memory_detector)
        result, profile_data = profiler.profile_function(func, *args, **kwargs)
        logger = get_logger('memory_profile')
        logger.info(f"函数 {func.__name__} 内存分析", {
            'function': func.__name__,
            **profile_data,
            'trace_id': TraceIdManager.generate_simple_trace_id()
        })
        return result
    return wrapper

_global_memory_detector = MemoryLeakDetector()

def get_memory_detector() -> MemoryLeakDetector:
    return _global_memory_detector

def get_memory_report() -> Dict[str, Any]:
    try:
        return _global_memory_detector.get_memory_report()
    except Exception as e:
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
    _global_memory_detector._trigger_memory_cleanup()

def track_object(obj: Any, obj_type: str):
    _global_memory_detector.track_object(obj, obj_type)

def untrack_object(obj: Any, obj_type: str):
    _global_memory_detector.untrack_object(obj, obj_type)
