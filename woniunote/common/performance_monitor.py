"""
性能监控和报告优化模块
提供实时性能监控、自动化报告生成和性能优化建议
"""
import time
import threading
import psutil
import gc
from typing import Dict, List, Any, Optional, Callable
from collections import deque, defaultdict
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from flask import Flask, request, g, current_app
from woniunote.common.simple_logger import get_simple_logger

logger = get_simple_logger('performance_monitor')

@dataclass
class PerformanceMetric:
    """性能指标数据结构"""
    timestamp: float
    metric_name: str
    value: float
    tags: Dict[str, str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = {}

@dataclass
class RequestMetric:
    """请求性能指标"""
    timestamp: float
    endpoint: str
    method: str
    duration: float
    status_code: int
    memory_usage: float
    cpu_usage: float
    query_count: int = 0
    cache_hits: int = 0
    cache_misses: int = 0

class PerformanceCollector:
    """性能数据收集器"""
    
    def __init__(self, max_metrics: int = 10000):
        self.max_metrics = max_metrics
        self.metrics = deque(maxlen=max_metrics)
        self.request_metrics = deque(maxlen=max_metrics)
        self.lock = threading.RLock()
        
        # 系统监控
        self.system_metrics = {
            'cpu_percent': deque(maxlen=100),
            'memory_percent': deque(maxlen=100),
            'disk_io': deque(maxlen=100),
            'network_io': deque(maxlen=100),
        }
        
        # 应用指标
        self.app_metrics = {
            'response_times': defaultdict(list),
            'error_rates': defaultdict(int),
            'request_counts': defaultdict(int),
            'active_connections': 0,
            'db_connections': 0,
            'cache_hit_rate': 0.0,
        }
        
        # 监控配置
        self.monitoring_enabled = True
        self.collection_interval = 5.0  # 秒
        self.alert_thresholds = {
            'response_time': 2.0,      # 2秒
            'cpu_usage': 80.0,         # 80%
            'memory_usage': 85.0,      # 85%
            'error_rate': 5.0,         # 5%
            'db_connections': 50,      # 50个连接
        }
        
        # 启动系统监控线程
        self._start_system_monitoring()
    
    def collect_metric(self, name: str, value: float, tags: Dict[str, str] = None):
        """收集性能指标"""
        if not self.monitoring_enabled:
            return
        
        metric = PerformanceMetric(
            timestamp=time.time(),
            metric_name=name,
            value=value,
            tags=tags or {}
        )
        
        with self.lock:
            self.metrics.append(metric)
    
    def collect_request_metric(self, endpoint: str, method: str, duration: float, 
                             status_code: int, **kwargs):
        """收集请求性能指标"""
        if not self.monitoring_enabled:
            return
        
        # 获取系统资源使用情况
        process = psutil.Process()
        memory_usage = process.memory_percent()
        cpu_usage = process.cpu_percent()
        
        metric = RequestMetric(
            timestamp=time.time(),
            endpoint=endpoint,
            method=method,
            duration=duration,
            status_code=status_code,
            memory_usage=memory_usage,
            cpu_usage=cpu_usage,
            **kwargs
        )
        
        with self.lock:
            self.request_metrics.append(metric)
            
            # 更新应用指标
            self._update_app_metrics(metric)
    
    def _update_app_metrics(self, metric: RequestMetric):
        """更新应用级指标"""
        endpoint_key = f"{metric.method} {metric.endpoint}"
        
        # 响应时间
        self.app_metrics['response_times'][endpoint_key].append(metric.duration)
        
        # 请求计数
        self.app_metrics['request_counts'][endpoint_key] += 1
        
        # 错误率
        if metric.status_code >= 400:
            self.app_metrics['error_rates'][endpoint_key] += 1
        
        # 缓存命中率计算
        total_cache_requests = metric.cache_hits + metric.cache_misses
        if total_cache_requests > 0:
            self.app_metrics['cache_hit_rate'] = metric.cache_hits / total_cache_requests
    
    def _start_system_monitoring(self):
        """启动系统监控线程"""
        def monitor_system():
            while self.monitoring_enabled:
                try:
                    # CPU使用率
                    cpu_percent = psutil.cpu_percent(interval=1)
                    self.system_metrics['cpu_percent'].append({
                        'timestamp': time.time(),
                        'value': cpu_percent
                    })
                    
                    # 内存使用率
                    memory = psutil.virtual_memory()
                    self.system_metrics['memory_percent'].append({
                        'timestamp': time.time(),
                        'value': memory.percent
                    })
                    
                    # 磁盘IO
                    disk_io = psutil.disk_io_counters()
                    if disk_io:
                        self.system_metrics['disk_io'].append({
                            'timestamp': time.time(),
                            'read_bytes': disk_io.read_bytes,
                            'write_bytes': disk_io.write_bytes
                        })
                    
                    # 网络IO
                    network_io = psutil.net_io_counters()
                    if network_io:
                        self.system_metrics['network_io'].append({
                            'timestamp': time.time(),
                            'bytes_sent': network_io.bytes_sent,
                            'bytes_recv': network_io.bytes_recv
                        })
                    
                    time.sleep(self.collection_interval)
                    
                except Exception as e:
                    logger.error(f"系统监控异常: {e}")
                    time.sleep(self.collection_interval)
        
        monitor_thread = threading.Thread(target=monitor_system, daemon=True)
        monitor_thread.start()
        logger.info("系统性能监控线程已启动")
    
    def get_metrics_summary(self, time_range: int = 3600) -> Dict[str, Any]:
        """获取性能指标摘要"""
        current_time = time.time()
        start_time = current_time - time_range
        
        with self.lock:
            # 过滤时间范围内的请求
            recent_requests = [
                req for req in self.request_metrics 
                if req.timestamp >= start_time
            ]
        
        if not recent_requests:
            return {'message': '无数据', 'time_range': time_range}
        
        # 计算统计信息
        durations = [req.duration for req in recent_requests]
        memory_usage = [req.memory_usage for req in recent_requests]
        cpu_usage = [req.cpu_usage for req in recent_requests]
        
        # 错误率计算
        error_count = sum(1 for req in recent_requests if req.status_code >= 400)
        error_rate = (error_count / len(recent_requests)) * 100 if recent_requests else 0
        
        # 按端点分组统计
        endpoint_stats = defaultdict(list)
        for req in recent_requests:
            endpoint_key = f"{req.method} {req.endpoint}"
            endpoint_stats[endpoint_key].append(req.duration)
        
        # 最慢端点
        slowest_endpoints = []
        for endpoint, times in endpoint_stats.items():
            avg_time = sum(times) / len(times)
            slowest_endpoints.append({
                'endpoint': endpoint,
                'avg_response_time': round(avg_time, 3),
                'request_count': len(times),
                'max_response_time': round(max(times), 3)
            })
        
        slowest_endpoints.sort(key=lambda x: x['avg_response_time'], reverse=True)
        
        return {
            'time_range_seconds': time_range,
            'total_requests': len(recent_requests),
            'error_rate_percent': round(error_rate, 2),
            'response_time': {
                'avg': round(sum(durations) / len(durations), 3),
                'min': round(min(durations), 3),
                'max': round(max(durations), 3),
                'p95': round(sorted(durations)[int(len(durations) * 0.95)], 3),
                'p99': round(sorted(durations)[int(len(durations) * 0.99)], 3),
            },
            'system_resources': {
                'avg_memory_percent': round(sum(memory_usage) / len(memory_usage), 2),
                'avg_cpu_percent': round(sum(cpu_usage) / len(cpu_usage), 2),
                'max_memory_percent': round(max(memory_usage), 2),
                'max_cpu_percent': round(max(cpu_usage), 2),
            },
            'slowest_endpoints': slowest_endpoints[:10],
            'current_system': self._get_current_system_status()
        }
    
    def _get_current_system_status(self) -> Dict[str, Any]:
        """获取当前系统状态"""
        try:
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                'cpu_percent': psutil.cpu_percent(),
                'memory_percent': memory.percent,
                'memory_available_gb': round(memory.available / (1024**3), 2),
                'disk_percent': disk.percent,
                'disk_free_gb': round(disk.free / (1024**3), 2),
                'boot_time': psutil.boot_time(),
                'process_count': len(psutil.pids()),
            }
        except Exception as e:
            logger.error(f"获取系统状态失败: {e}")
            return {'error': str(e)}
    
    def check_performance_alerts(self) -> List[Dict[str, Any]]:
        """检查性能警报"""
        alerts = []
        
        try:
            # 获取最近的指标
            recent_metrics = self.get_metrics_summary(300)  # 最近5分钟
            
            # 检查响应时间
            avg_response_time = recent_metrics.get('response_time', {}).get('avg', 0)
            if avg_response_time > self.alert_thresholds['response_time']:
                alerts.append({
                    'type': 'response_time',
                    'severity': 'warning',
                    'message': f'平均响应时间过高: {avg_response_time}s',
                    'threshold': self.alert_thresholds['response_time'],
                    'current_value': avg_response_time
                })
            
            # 检查错误率
            error_rate = recent_metrics.get('error_rate_percent', 0)
            if error_rate > self.alert_thresholds['error_rate']:
                alerts.append({
                    'type': 'error_rate',
                    'severity': 'critical',
                    'message': f'错误率过高: {error_rate}%',
                    'threshold': self.alert_thresholds['error_rate'],
                    'current_value': error_rate
                })
            
            # 检查系统资源
            system_status = self._get_current_system_status()
            
            if system_status.get('cpu_percent', 0) > self.alert_thresholds['cpu_usage']:
                alerts.append({
                    'type': 'cpu_usage',
                    'severity': 'warning',
                    'message': f'CPU使用率过高: {system_status["cpu_percent"]}%',
                    'threshold': self.alert_thresholds['cpu_usage'],
                    'current_value': system_status['cpu_percent']
                })
            
            if system_status.get('memory_percent', 0) > self.alert_thresholds['memory_usage']:
                alerts.append({
                    'type': 'memory_usage',
                    'severity': 'critical',
                    'message': f'内存使用率过高: {system_status["memory_percent"]}%',
                    'threshold': self.alert_thresholds['memory_usage'],
                    'current_value': system_status['memory_percent']
                })
            
        except Exception as e:
            logger.error(f"性能警报检查失败: {e}")
            alerts.append({
                'type': 'monitoring_error',
                'severity': 'error',
                'message': f'监控系统异常: {str(e)}'
            })
        
        return alerts
    
    def generate_optimization_suggestions(self) -> List[Dict[str, Any]]:
        """生成性能优化建议"""
        suggestions = []
        
        try:
            metrics = self.get_metrics_summary(3600)  # 最近1小时
            
            # 响应时间优化建议
            avg_response_time = metrics.get('response_time', {}).get('avg', 0)
            if avg_response_time > 1.0:
                suggestions.append({
                    'category': 'response_time',
                    'priority': 'high' if avg_response_time > 2.0 else 'medium',
                    'suggestion': '考虑优化慢查询、添加缓存或优化数据库索引',
                    'current_value': f'{avg_response_time}s',
                    'target_value': '< 1.0s'
                })
            
            # 慢端点优化建议
            slowest_endpoints = metrics.get('slowest_endpoints', [])
            if slowest_endpoints and slowest_endpoints[0]['avg_response_time'] > 2.0:
                suggestions.append({
                    'category': 'slow_endpoints',
                    'priority': 'high',
                    'suggestion': f'优化慢端点: {slowest_endpoints[0]["endpoint"]}',
                    'current_value': f'{slowest_endpoints[0]["avg_response_time"]}s',
                    'details': slowest_endpoints[:5]
                })
            
            # 内存使用优化建议
            max_memory = metrics.get('system_resources', {}).get('max_memory_percent', 0)
            if max_memory > 80:
                suggestions.append({
                    'category': 'memory_usage',
                    'priority': 'medium',
                    'suggestion': '考虑优化内存使用，增加缓存清理策略',
                    'current_value': f'{max_memory}%',
                    'target_value': '< 80%'
                })
            
            # 错误率优化建议
            error_rate = metrics.get('error_rate_percent', 0)
            if error_rate > 2.0:
                suggestions.append({
                    'category': 'error_rate',
                    'priority': 'critical' if error_rate > 5.0 else 'high',
                    'suggestion': '检查应用错误日志，修复常见错误',
                    'current_value': f'{error_rate}%',
                    'target_value': '< 1%'
                })
            
            # 缓存命中率建议
            cache_hit_rate = self.app_metrics.get('cache_hit_rate', 0) * 100
            if cache_hit_rate < 70:
                suggestions.append({
                    'category': 'cache_performance',
                    'priority': 'medium',
                    'suggestion': '优化缓存策略，提高缓存命中率',
                    'current_value': f'{cache_hit_rate:.1f}%',
                    'target_value': '> 80%'
                })
            
        except Exception as e:
            logger.error(f"生成优化建议失败: {e}")
        
        return suggestions

class PerformanceMonitor:
    """性能监控器主类"""
    
    def __init__(self, app: Flask = None):
        self.app = app
        self.collector = PerformanceCollector()
        self.monitoring_enabled = True
        self.alert_callbacks: List[Callable] = []
        
        if app:
            self.init_app(app)
    
    def init_app(self, app: Flask):
        """初始化Flask应用"""
        self.app = app
        
        # 注册请求处理器
        self._setup_request_monitoring()
        
        # 启动性能检查线程
        self._start_performance_checking()
        
        logger.info("性能监控器初始化完成")
    
    def _setup_request_monitoring(self):
        """设置请求监控"""
        @self.app.before_request
        def before_request():
            """请求开始时的处理"""
            if not self.monitoring_enabled:
                return
            
            g.start_time = time.time()
            g.start_memory = psutil.Process().memory_info().rss
            
            # 记录垃圾收集前状态
            g.gc_before = {
                'gen0': len(gc.get_objects()),
                'collections': gc.get_stats()
            }
        
        @self.app.after_request
        def after_request(response):
            """请求结束时的处理"""
            if not self.monitoring_enabled or not hasattr(g, 'start_time'):
                return response
            
            try:
                # 计算请求处理时间
                duration = time.time() - g.start_time
                
                # 获取内存使用变化
                current_memory = psutil.Process().memory_info().rss
                memory_delta = current_memory - g.start_memory
                
                # 收集请求指标
                self.collector.collect_request_metric(
                    endpoint=request.endpoint or 'unknown',
                    method=request.method,
                    duration=duration,
                    status_code=response.status_code,
                    memory_delta=memory_delta,
                    query_count=getattr(g, 'query_count', 0),
                    cache_hits=getattr(g, 'cache_hits', 0),
                    cache_misses=getattr(g, 'cache_misses', 0)
                )
                
                # 记录慢请求
                if duration > 2.0:
                    logger.warning(f"慢请求检测: {request.method} {request.endpoint} - {duration:.3f}s")
                
            except Exception as e:
                logger.error(f"请求监控处理异常: {e}")
            
            return response
    
    def _start_performance_checking(self):
        """启动性能检查线程"""
        def check_performance():
            while self.monitoring_enabled:
                try:
                    # 检查性能警报
                    alerts = self.collector.check_performance_alerts()
                    
                    # 触发警报回调
                    for alert in alerts:
                        for callback in self.alert_callbacks:
                            try:
                                callback(alert)
                            except Exception as e:
                                logger.error(f"警报回调执行失败: {e}")
                    
                    time.sleep(60)  # 每分钟检查一次
                    
                except Exception as e:
                    logger.error(f"性能检查异常: {e}")
                    time.sleep(60)
        
        check_thread = threading.Thread(target=check_performance, daemon=True)
        check_thread.start()
        logger.info("性能检查线程已启动")
    
    def add_alert_callback(self, callback: Callable):
        """添加警报回调函数"""
        self.alert_callbacks.append(callback)
    
    def get_performance_report(self, time_range: int = 3600) -> Dict[str, Any]:
        """获取性能报告"""
        return {
            'timestamp': datetime.now().isoformat(),
            'time_range_seconds': time_range,
            'summary': self.collector.get_metrics_summary(time_range),
            'alerts': self.collector.check_performance_alerts(),
            'optimization_suggestions': self.collector.generate_optimization_suggestions(),
            'monitoring_status': {
                'enabled': self.monitoring_enabled,
                'collector_metrics': len(self.collector.metrics),
                'request_metrics': len(self.collector.request_metrics),
                'alert_callbacks': len(self.alert_callbacks)
            }
        }
    
    def enable_monitoring(self):
        """启用监控"""
        self.monitoring_enabled = True
        self.collector.monitoring_enabled = True
        logger.info("性能监控已启用")
    
    def disable_monitoring(self):
        """禁用监控"""
        self.monitoring_enabled = False
        self.collector.monitoring_enabled = False
        logger.info("性能监控已禁用")

# 全局性能监控器实例
performance_monitor = PerformanceMonitor()

def init_performance_monitoring(app: Flask):
    """初始化性能监控"""
    try:
        performance_monitor.init_app(app)
        
        # 添加默认警报处理
        def default_alert_handler(alert):
            severity = alert.get('severity', 'info')
            if severity in ['critical', 'error']:
                logger.error(f"性能警报: {alert['message']}")
            else:
                logger.warning(f"性能警报: {alert['message']}")
        
        performance_monitor.add_alert_callback(default_alert_handler)
        
        logger.info("性能监控初始化成功")
        return performance_monitor
        
    except Exception as e:
        logger.error(f"性能监控初始化失败: {e}")
        return None

def get_performance_monitor():
    """获取性能监控器实例"""
    return performance_monitor