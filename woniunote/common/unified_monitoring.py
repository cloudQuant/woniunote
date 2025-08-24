#!/usr/bin/env python3
"""
统一的监控系统模块
整合所有监控、性能分析和智能运维功能
"""

import time
import threading
import psutil
from typing import Dict, Any, List, Optional
from collections import defaultdict, deque
from datetime import datetime, timedelta
from functools import wraps

from .unified_logging import get_logger

logger = get_logger('unified_monitoring')

class UnifiedMonitoringSystem:
    """统一的监控系统"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = get_logger('monitoring')
        
        # 监控配置
        self.collect_interval = self.config.get('collect_interval', 30)
        self.alert_thresholds = self.config.get('alert_thresholds', {
            'cpu': 80.0,
            'memory': 80.0,
            'disk': 85.0,
            'network': 1000000  # 1MB/s
        })
        
        # 数据存储
        self.metrics_history = defaultdict(lambda: deque(maxlen=1000))
        self.alerts = deque(maxlen=100)
        self.system_status = {}
        
        # 监控线程
        self._monitoring_thread = None
        self._stop_monitoring = False
        
        # 启动监控
        self.start_monitoring()
        
        logger.info("统一监控系统初始化完成")
    
    def start_monitoring(self):
        """启动监控"""
        if self._monitoring_thread and self._monitoring_thread.is_alive():
            return
        
        self._stop_monitoring = False
        self._monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self._monitoring_thread.start()
        logger.info("监控系统已启动")
    
    def stop_monitoring(self):
        """停止监控"""
        self._stop_monitoring = True
        if self._monitoring_thread:
            self._monitoring_thread.join(timeout=5)
        logger.info("监控系统已停止")
    
    def _monitoring_loop(self):
        """监控主循环"""
        while not self._stop_monitoring:
            try:
                # 收集系统指标
                self._collect_system_metrics()
                
                # 检查告警
                self._check_alerts()
                
                # 等待下次收集
                time.sleep(self.collect_interval)
                
            except Exception as e:
                logger.error(f"监控循环异常: {e}")
                time.sleep(5)
    
    def _collect_system_metrics(self):
        """收集系统指标"""
        try:
            current_time = time.time()
            
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            self.metrics_history['cpu'].append({
                'timestamp': current_time,
                'value': cpu_percent
            })
            
            # 内存使用率
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            self.metrics_history['memory'].append({
                'timestamp': current_time,
                'value': memory_percent,
                'available': memory.available,
                'total': memory.total
            })
            
            # 磁盘使用率
            disk = psutil.disk_usage('/')
            disk_percent = (disk.total - disk.free) / disk.total * 100
            self.metrics_history['disk'].append({
                'timestamp': current_time,
                'value': disk_percent,
                'free': disk.free,
                'total': disk.total
            })
            
            # 网络使用率
            network = psutil.net_io_counters()
            network_bytes = network.bytes_sent + network.bytes_recv
            self.metrics_history['network'].append({
                'timestamp': current_time,
                'value': network_bytes,
                'bytes_sent': network.bytes_sent,
                'bytes_recv': network.bytes_recv
            })
            
            # 更新系统状态
            self.system_status = {
                'cpu_percent': cpu_percent,
                'memory_percent': memory_percent,
                'disk_percent': disk_percent,
                'network_bytes': network_bytes,
                'last_update': current_time
            }
            
        except Exception as e:
            logger.error(f"收集系统指标失败: {e}")
    
    def _check_alerts(self):
        """检查告警"""
        try:
            current_metrics = self.system_status
            
            # CPU告警
            if current_metrics.get('cpu_percent', 0) > self.alert_thresholds['cpu']:
                self._create_alert('CPU', 'high', 
                                 f"CPU使用率过高: {current_metrics['cpu_percent']:.1f}%")
            
            # 内存告警
            if current_metrics.get('memory_percent', 0) > self.alert_thresholds['memory']:
                self._create_alert('Memory', 'high',
                                 f"内存使用率过高: {current_metrics['memory_percent']:.1f}%")
            
            # 磁盘告警
            if current_metrics.get('disk_percent', 0) > self.alert_thresholds['disk']:
                self._create_alert('Disk', 'high',
                                 f"磁盘使用率过高: {current_metrics['disk_percent']:.1f}%")
            
        except Exception as e:
            logger.error(f"检查告警失败: {e}")
    
    def _create_alert(self, alert_type: str, severity: str, message: str):
        """创建告警"""
        alert = {
            'type': alert_type,
            'severity': severity,
            'message': message,
            'timestamp': datetime.now().isoformat()
        }
        
        self.alerts.append(alert)
        logger.warning(f"告警: {message}")
    
    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        return {
            'current_metrics': self.system_status,
            'alerts': list(self.alerts)[-10:],  # 最近10个告警
            'timestamp': datetime.now().isoformat()
        }
    
    def get_metrics_history(self, metric_type: str, hours: int = 24) -> List[Dict[str, Any]]:
        """获取指标历史"""
        if metric_type not in self.metrics_history:
            return []
        
        cutoff_time = time.time() - (hours * 3600)
        return [
            metric for metric in self.metrics_history[metric_type]
            if metric['timestamp'] > cutoff_time
        ]
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """获取性能摘要"""
        try:
            summary = {}
            
            for metric_type in ['cpu', 'memory', 'disk', 'network']:
                if metric_type in self.metrics_history:
                    metrics = list(self.metrics_history[metric_type])
                    if metrics:
                        values = [m['value'] for m in metrics]
                        summary[metric_type] = {
                            'current': values[-1] if values else 0,
                            'average': sum(values) / len(values) if values else 0,
                            'max': max(values) if values else 0,
                            'min': min(values) if values else 0
                        }
            
            return summary
            
        except Exception as e:
            logger.error(f"获取性能摘要失败: {e}")
            return {}
    
    def run_capacity_analysis(self) -> Dict[str, Any]:
        """运行容量分析"""
        try:
            analysis = {
                'timestamp': datetime.now().isoformat(),
                'recommendations': [],
                'warnings': []
            }
            
            current_metrics = self.system_status
            
            # CPU分析
            cpu_percent = current_metrics.get('cpu_percent', 0)
            if cpu_percent > 90:
                analysis['warnings'].append("CPU使用率极高，建议检查进程或增加资源")
            elif cpu_percent > 70:
                analysis['recommendations'].append("CPU使用率较高，建议优化代码或增加资源")
            
            # 内存分析
            memory_percent = current_metrics.get('memory_percent', 0)
            if memory_percent > 90:
                analysis['warnings'].append("内存使用率极高，建议检查内存泄漏或增加内存")
            elif memory_percent > 80:
                analysis['recommendations'].append("内存使用率较高，建议优化内存使用或增加内存")
            
            # 磁盘分析
            disk_percent = current_metrics.get('disk_percent', 0)
            if disk_percent > 95:
                analysis['warnings'].append("磁盘空间严重不足，建议立即清理或扩容")
            elif disk_percent > 85:
                analysis['recommendations'].append("磁盘空间不足，建议定期清理或考虑扩容")
            
            return analysis
            
        except Exception as e:
            logger.error(f"容量分析失败: {e}")
            return {'error': str(e)}
    
    def get_health_score(self) -> Dict[str, Any]:
        """获取健康评分"""
        try:
            current_metrics = self.system_status
            
            # 计算各项指标的得分
            scores = {}
            
            # CPU得分 (越低越好)
            cpu_percent = current_metrics.get('cpu_percent', 0)
            scores['cpu'] = max(0, 100 - cpu_percent)
            
            # 内存得分 (越低越好)
            memory_percent = current_metrics.get('memory_percent', 0)
            scores['memory'] = max(0, 100 - memory_percent)
            
            # 磁盘得分 (越低越好)
            disk_percent = current_metrics.get('disk_percent', 0)
            scores['disk'] = max(0, 100 - disk_percent)
            
            # 综合得分
            overall_score = sum(scores.values()) / len(scores)
            
            # 健康等级
            if overall_score >= 80:
                health_level = 'excellent'
            elif overall_score >= 60:
                health_level = 'good'
            elif overall_score >= 40:
                health_level = 'fair'
            else:
                health_level = 'poor'
            
            return {
                'overall_score': round(overall_score, 1),
                'health_level': health_level,
                'component_scores': scores,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"计算健康评分失败: {e}")
            return {'error': str(e)}

# ==================== 全局实例和工厂函数 ====================

# 全局监控系统实例
_global_monitoring_system = None

def init_unified_monitoring_system(config: Dict[str, Any] = None) -> UnifiedMonitoringSystem:
    """初始化全局监控系统"""
    global _global_monitoring_system
    _global_monitoring_system = UnifiedMonitoringSystem(config)
    return _global_monitoring_system

def get_monitoring_system() -> Optional[UnifiedMonitoringSystem]:
    """获取全局监控系统"""
    return _global_monitoring_system

def get_performance_monitor():
    """获取性能监控器（向后兼容）"""
    system = get_monitoring_system()
    if system:
        return system
    return None

def get_metrics_collector():
    """获取指标收集器（向后兼容）"""
    system = get_monitoring_system()
    if system:
        return system
    return None

# ==================== 向后兼容 ====================

# 为了向后兼容，保留旧的函数名
init_monitoring = init_unified_monitoring_system
get_performance_monitor_legacy = get_performance_monitor
get_metrics_collector_legacy = get_metrics_collector

# 向后兼容的函数
def monitor_function(func=None, **kwargs):
    """监控函数装饰器"""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            # 简单的函数监控
            start_time = time.time()
            try:
                result = f(*args, **kwargs)
                execution_time = time.time() - start_time
                logger.debug(f"函数 {f.__name__} 执行时间: {execution_time:.3f}s")
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(f"函数 {f.__name__} 执行失败，耗时: {execution_time:.3f}s 错误: {e}")
                raise
        return wrapper
    
    if func:
        return decorator(func)
    return decorator

# 更多向后兼容的函数
def init_intelligent_ops_management(config: Dict[str, Any] = None):
    """初始化智能运维管理（向后兼容）"""
    return init_unified_monitoring_system(config)

def monitor_function_health(func=None, **kwargs):
    """监控函数健康状态（向后兼容）"""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            # 简单的函数健康监控
            start_time = time.time()
            try:
                result = f(*args, **kwargs)
                execution_time = time.time() - start_time
                logger.debug(f"函数 {f.__name__} 健康执行，耗时: {execution_time:.3f}s")
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(f"函数 {f.__name__} 健康检查失败，耗时: {execution_time:.3f}s 错误: {e}")
                raise
        return wrapper
    
    if func:
        return decorator(func)
    return decorator

# 更多向后兼容的函数
def get_ops_manager():
    """获取运维管理器（向后兼容）"""
    return get_monitoring_system()
