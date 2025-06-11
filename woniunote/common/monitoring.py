#!/usr/bin/env python3
"""
系统监控模块 - 性能指标、资源监控、错误追踪
"""

import time
import psutil
import threading
import logging
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from collections import defaultdict, deque
from functools import wraps
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)

class MetricType(Enum):
    """指标类型"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"

class AlertLevel(Enum):
    """告警级别"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

@dataclass
class MetricValue:
    """指标值"""
    name: str
    value: float
    timestamp: float
    labels: Dict[str, str] = None
    metric_type: MetricType = MetricType.GAUGE

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class Alert:
    """告警信息"""
    id: str
    level: AlertLevel
    message: str
    metric_name: str
    current_value: float
    threshold: float
    timestamp: float
    resolved: bool = False
    resolved_at: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class MetricsCollector:
    """指标收集器"""
    
    def __init__(self, max_history: int = 1000):
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_history))
        self.counters: Dict[str, float] = defaultdict(float)
        self.gauges: Dict[str, float] = defaultdict(float)
        self.histograms: Dict[str, List[float]] = defaultdict(list)
        self.timers: Dict[str, List[float]] = defaultdict(list)
        self.lock = threading.Lock()
        
    def record_counter(self, name: str, value: float = 1, labels: Dict[str, str] = None):
        """记录计数器指标"""
        with self.lock:
            self.counters[name] += value
            metric = MetricValue(name, self.counters[name], time.time(), labels, MetricType.COUNTER)
            self.metrics[name].append(metric)
    
    def record_gauge(self, name: str, value: float, labels: Dict[str, str] = None):
        """记录瞬时值指标"""
        with self.lock:
            self.gauges[name] = value
            metric = MetricValue(name, value, time.time(), labels, MetricType.GAUGE)
            self.metrics[name].append(metric)
    
    def record_histogram(self, name: str, value: float, labels: Dict[str, str] = None):
        """记录直方图指标"""
        with self.lock:
            self.histograms[name].append(value)
            # 保持最近1000个值
            if len(self.histograms[name]) > 1000:
                self.histograms[name] = self.histograms[name][-1000:]
            
            metric = MetricValue(name, value, time.time(), labels, MetricType.HISTOGRAM)
            self.metrics[name].append(metric)
    
    def record_timer(self, name: str, duration: float, labels: Dict[str, str] = None):
        """记录计时器指标"""
        with self.lock:
            self.timers[name].append(duration)
            # 保持最近1000个值
            if len(self.timers[name]) > 1000:
                self.timers[name] = self.timers[name][-1000:]
            
            metric = MetricValue(name, duration, time.time(), labels, MetricType.TIMER)
            self.metrics[name].append(metric)
    
    def get_metrics(self, name: str = None, since: float = None) -> Dict[str, List[Dict[str, Any]]]:
        """获取指标数据"""
        with self.lock:
            result = {}
            
            if name:
                metrics_list = [name] if name in self.metrics else []
            else:
                metrics_list = self.metrics.keys()
            
            for metric_name in metrics_list:
                metrics = self.metrics[metric_name]
                if since:
                    filtered_metrics = [m for m in metrics if m.timestamp >= since]
                else:
                    filtered_metrics = list(metrics)
                
                result[metric_name] = [m.to_dict() for m in filtered_metrics]
            
            return result
    
    def get_summary(self, name: str) -> Optional[Dict[str, Any]]:
        """获取指标摘要"""
        with self.lock:
            if name not in self.metrics:
                return None
            
            metrics = list(self.metrics[name])
            if not metrics:
                return None
            
            latest = metrics[-1]
            values = [m.value for m in metrics]
            
            summary = {
                'name': name,
                'type': latest.metric_type.value,
                'current_value': latest.value,
                'count': len(values),
                'min': min(values),
                'max': max(values),
                'avg': sum(values) / len(values),
                'last_updated': latest.timestamp
            }
            
            # 对于直方图和计时器，添加百分位数
            if latest.metric_type in [MetricType.HISTOGRAM, MetricType.TIMER]:
                sorted_values = sorted(values)
                summary.update({
                    'p50': self._percentile(sorted_values, 50),
                    'p90': self._percentile(sorted_values, 90),
                    'p95': self._percentile(sorted_values, 95),
                    'p99': self._percentile(sorted_values, 99)
                })
            
            return summary
    
    def _percentile(self, sorted_values: List[float], percentile: int) -> float:
        """计算百分位数"""
        if not sorted_values:
            return 0.0
        
        index = (len(sorted_values) - 1) * percentile / 100
        if index.is_integer():
            return sorted_values[int(index)]
        else:
            lower = sorted_values[int(index)]
            upper = sorted_values[int(index) + 1]
            return lower + (upper - lower) * (index - int(index))

class SystemMonitor:
    """系统资源监控器"""
    
    def __init__(self, collect_interval: int = 30):
        self.collect_interval = collect_interval
        self.running = False
        self.monitor_thread = None
        self.metrics_collector = MetricsCollector()
        
    def start(self):
        """启动监控"""
        if self.running:
            return
        
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("System monitor started")
    
    def stop(self):
        """停止监控"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("System monitor stopped")
    
    def _monitor_loop(self):
        """监控循环"""
        while self.running:
            try:
                self._collect_system_metrics()
                time.sleep(self.collect_interval)
            except Exception as e:
                logger.error(f"System monitor error: {e}")
                time.sleep(self.collect_interval)
    
    def _collect_system_metrics(self):
        """收集系统指标"""
        try:
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            self.metrics_collector.record_gauge('system.cpu.usage_percent', cpu_percent)
            
            # 内存使用情况
            memory = psutil.virtual_memory()
            self.metrics_collector.record_gauge('system.memory.usage_percent', memory.percent)
            self.metrics_collector.record_gauge('system.memory.available_mb', memory.available / 1024 / 1024)
            self.metrics_collector.record_gauge('system.memory.used_mb', memory.used / 1024 / 1024)
            
            # 磁盘使用情况
            disk = psutil.disk_usage('/')
            self.metrics_collector.record_gauge('system.disk.usage_percent', 
                                              (disk.used / disk.total) * 100)
            self.metrics_collector.record_gauge('system.disk.free_gb', disk.free / 1024 / 1024 / 1024)
            
            # 网络IO
            net_io = psutil.net_io_counters()
            self.metrics_collector.record_counter('system.network.bytes_sent', net_io.bytes_sent)
            self.metrics_collector.record_counter('system.network.bytes_recv', net_io.bytes_recv)
            
            # 磁盘IO
            disk_io = psutil.disk_io_counters()
            if disk_io:
                self.metrics_collector.record_counter('system.disk.read_bytes', disk_io.read_bytes)
                self.metrics_collector.record_counter('system.disk.write_bytes', disk_io.write_bytes)
            
            # 进程信息
            process = psutil.Process()
            process_memory = process.memory_info()
            self.metrics_collector.record_gauge('process.memory.rss_mb', 
                                              process_memory.rss / 1024 / 1024)
            self.metrics_collector.record_gauge('process.cpu.usage_percent', 
                                              process.cpu_percent())
            
            # 文件描述符
            try:
                fd_count = len(process.open_files()) + len(process.connections())
                self.metrics_collector.record_gauge('process.fd.count', fd_count)
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                pass
            
        except Exception as e:
            logger.error(f"Failed to collect system metrics: {e}")

class AlertManager:
    """告警管理器"""
    
    def __init__(self, max_alerts: int = 1000):
        self.alerts: Dict[str, Alert] = {}
        self.alert_history: deque = deque(maxlen=max_alerts)
        self.alert_rules: Dict[str, Dict[str, Any]] = {}
        self.callbacks: List[Callable[[Alert], None]] = []
        self.lock = threading.Lock()
    
    def add_rule(self, metric_name: str, threshold: float, 
                level: AlertLevel = AlertLevel.WARNING,
                comparison: str = 'gt', duration: int = 60):
        """添加告警规则
        
        Args:
            metric_name: 指标名称
            threshold: 阈值
            level: 告警级别
            comparison: 比较方式 ('gt', 'lt', 'gte', 'lte', 'eq', 'ne')
            duration: 持续时间（秒）
        """
        with self.lock:
            self.alert_rules[metric_name] = {
                'threshold': threshold,
                'level': level,
                'comparison': comparison,
                'duration': duration,
                'triggered_at': None
            }
    
    def check_metric(self, metric: MetricValue):
        """检查指标是否触发告警"""
        with self.lock:
            rule = self.alert_rules.get(metric.name)
            if not rule:
                return
            
            # 检查是否满足告警条件
            triggered = self._evaluate_condition(
                metric.value, rule['threshold'], rule['comparison']
            )
            
            current_time = time.time()
            alert_id = f"{metric.name}_{rule['level'].value}"
            
            if triggered:
                # 检查持续时间
                if rule['triggered_at'] is None:
                    rule['triggered_at'] = current_time
                elif current_time - rule['triggered_at'] >= rule['duration']:
                    # 触发告警
                    if alert_id not in self.alerts or self.alerts[alert_id].resolved:
                        alert = Alert(
                            id=alert_id,
                            level=rule['level'],
                            message=f"Metric {metric.name} {rule['comparison']} {rule['threshold']}",
                            metric_name=metric.name,
                            current_value=metric.value,
                            threshold=rule['threshold'],
                            timestamp=current_time
                        )
                        
                        self.alerts[alert_id] = alert
                        self.alert_history.append(alert)
                        self._trigger_callbacks(alert)
            else:
                # 重置触发时间
                rule['triggered_at'] = None
                
                # 解决告警
                if alert_id in self.alerts and not self.alerts[alert_id].resolved:
                    self.alerts[alert_id].resolved = True
                    self.alerts[alert_id].resolved_at = current_time
    
    def _evaluate_condition(self, value: float, threshold: float, comparison: str) -> bool:
        """评估告警条件"""
        if comparison == 'gt':
            return value > threshold
        elif comparison == 'lt':
            return value < threshold
        elif comparison == 'gte':
            return value >= threshold
        elif comparison == 'lte':
            return value <= threshold
        elif comparison == 'eq':
            return value == threshold
        elif comparison == 'ne':
            return value != threshold
        else:
            return False
    
    def add_callback(self, callback: Callable[[Alert], None]):
        """添加告警回调"""
        with self.lock:
            self.callbacks.append(callback)
    
    def _trigger_callbacks(self, alert: Alert):
        """触发告警回调"""
        for callback in self.callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"Alert callback error: {e}")
    
    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """获取活跃告警"""
        with self.lock:
            return [alert.to_dict() for alert in self.alerts.values() if not alert.resolved]
    
    def get_alert_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取告警历史"""
        with self.lock:
            recent_alerts = list(self.alert_history)[-limit:]
            return [alert.to_dict() for alert in recent_alerts]

class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self):
        self.metrics_collector = MetricsCollector()
        self.request_times = defaultdict(list)
        self.lock = threading.Lock()
    
    def record_request(self, endpoint: str, method: str, status_code: int, 
                      duration: float, user_id: str = None):
        """记录请求指标"""
        labels = {
            'endpoint': endpoint,
            'method': method,
            'status': str(status_code)
        }
        
        # 记录请求计数
        self.metrics_collector.record_counter('http.requests.total', 1, labels)
        
        # 记录响应时间
        self.metrics_collector.record_timer('http.request.duration', duration, labels)
        
        # 记录错误率
        if status_code >= 400:
            self.metrics_collector.record_counter('http.requests.errors', 1, labels)
        
        # 记录用户请求
        if user_id:
            user_labels = labels.copy()
            user_labels['user_id'] = user_id
            self.metrics_collector.record_counter('http.requests.by_user', 1, user_labels)
    
    def record_database_query(self, query_type: str, duration: float, success: bool = True):
        """记录数据库查询指标"""
        labels = {
            'query_type': query_type,
            'success': str(success)
        }
        
        self.metrics_collector.record_counter('db.queries.total', 1, labels)
        self.metrics_collector.record_timer('db.query.duration', duration, labels)
        
        if not success:
            self.metrics_collector.record_counter('db.queries.errors', 1, labels)
    
    def record_cache_operation(self, operation: str, hit: bool = None):
        """记录缓存操作指标"""
        labels = {'operation': operation}
        
        self.metrics_collector.record_counter('cache.operations.total', 1, labels)
        
        if hit is not None:
            hit_labels = labels.copy()
            hit_labels['hit'] = str(hit)
            self.metrics_collector.record_counter('cache.operations.by_result', 1, hit_labels)
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """获取性能摘要"""
        summaries = {}
        
        # 获取关键指标摘要
        key_metrics = [
            'http.requests.total',
            'http.request.duration',
            'http.requests.errors',
            'db.queries.total',
            'db.query.duration',
            'cache.operations.total'
        ]
        
        for metric in key_metrics:
            summary = self.metrics_collector.get_summary(metric)
            if summary:
                summaries[metric] = summary
        
        return summaries

# 全局监控实例
_global_metrics_collector = None
_global_system_monitor = None
_global_alert_manager = None
_global_performance_monitor = None

def get_metrics_collector() -> MetricsCollector:
    """获取全局指标收集器"""
    global _global_metrics_collector
    if _global_metrics_collector is None:
        _global_metrics_collector = MetricsCollector()
    return _global_metrics_collector

def get_system_monitor() -> SystemMonitor:
    """获取全局系统监控器"""
    global _global_system_monitor
    if _global_system_monitor is None:
        _global_system_monitor = SystemMonitor()
    return _global_system_monitor

def get_alert_manager() -> AlertManager:
    """获取全局告警管理器"""
    global _global_alert_manager
    if _global_alert_manager is None:
        _global_alert_manager = AlertManager()
        
        # 添加默认告警规则
        _global_alert_manager.add_rule('system.cpu.usage_percent', 80, AlertLevel.WARNING)
        _global_alert_manager.add_rule('system.cpu.usage_percent', 95, AlertLevel.CRITICAL)
        _global_alert_manager.add_rule('system.memory.usage_percent', 85, AlertLevel.WARNING)
        _global_alert_manager.add_rule('system.memory.usage_percent', 95, AlertLevel.CRITICAL)
        _global_alert_manager.add_rule('http.request.duration', 5.0, AlertLevel.WARNING)
        _global_alert_manager.add_rule('http.request.duration', 10.0, AlertLevel.ERROR)
        
    return _global_alert_manager

def get_performance_monitor() -> PerformanceMonitor:
    """获取全局性能监控器"""
    global _global_performance_monitor
    if _global_performance_monitor is None:
        _global_performance_monitor = PerformanceMonitor()
    return _global_performance_monitor

def monitor_function(metric_name: str = None, record_errors: bool = True):
    """函数监控装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            monitor = get_performance_monitor()
            name = metric_name or f"{func.__module__}.{func.__name__}"
            
            start_time = time.time()
            success = True
            
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                if record_errors:
                    monitor.metrics_collector.record_counter(f"{name}.errors", 1)
                raise
            finally:
                duration = time.time() - start_time
                monitor.metrics_collector.record_timer(f"{name}.duration", duration)
                monitor.metrics_collector.record_counter(f"{name}.calls", 1)
                
                if not success and record_errors:
                    monitor.metrics_collector.record_counter(f"{name}.failures", 1)
        
        return wrapper
    return decorator

def init_monitoring(config: Dict[str, Any] = None):
    """初始化监控系统"""
    try:
        # 初始化系统监控
        system_monitor = get_system_monitor()
        if config and config.get('system_monitoring', True):
            system_monitor.start()
        
        # 初始化告警管理器
        alert_manager = get_alert_manager()
        
        # 添加日志告警回调
        def log_alert(alert: Alert):
            level_map = {
                AlertLevel.INFO: logging.INFO,
                AlertLevel.WARNING: logging.WARNING,
                AlertLevel.ERROR: logging.ERROR,
                AlertLevel.CRITICAL: logging.CRITICAL
            }
            logger.log(level_map[alert.level], f"ALERT: {alert.message}")
        
        alert_manager.add_callback(log_alert)
        
        logger.info("Monitoring system initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize monitoring: {e}")
        raise

def shutdown_monitoring():
    """关闭监控系统"""
    global _global_system_monitor
    
    if _global_system_monitor:
        _global_system_monitor.stop()
    
    logger.info("Monitoring system shutdown completed") 