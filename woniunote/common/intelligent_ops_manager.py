#!/usr/bin/env python3
"""
Phase 6 智能运维管理模块
提供自动故障检测、系统自愈、容量规划、智能告警等智能化运维功能
"""

import os
import time
import threading
import logging
import json
import subprocess
import psutil
from typing import Dict, Any, List, Optional, Callable, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
from functools import wraps
from enum import Enum
import statistics
import math

logger = logging.getLogger(__name__)

class AlertLevel(Enum):
    """告警级别"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class SystemComponent(Enum):
    """系统组件"""
    CPU = "cpu"
    MEMORY = "memory"
    DISK = "disk"
    NETWORK = "network"
    DATABASE = "database"
    APPLICATION = "application"
    CACHE = "cache"

class HealthStatus(Enum):
    """健康状态"""
    HEALTHY = "healthy"
    WARNING = "warning"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"

@dataclass
class SystemMetric:
    """系统指标"""
    component: SystemComponent
    metric_name: str
    value: float
    unit: str
    timestamp: datetime
    threshold_warning: Optional[float]
    threshold_critical: Optional[float]

@dataclass
class Alert:
    """告警"""
    alert_id: str
    level: AlertLevel
    component: SystemComponent
    title: str
    description: str
    timestamp: datetime
    resolved_at: Optional[datetime]
    auto_resolved: bool
    actions_taken: List[str]
    metadata: Dict[str, Any]

@dataclass
class HealthCheck:
    """健康检查"""
    component: SystemComponent
    name: str
    status: HealthStatus
    message: str
    timestamp: datetime
    response_time: float
    details: Dict[str, Any]

class SystemMonitor:
    """系统监控器"""
    
    def __init__(self, check_interval: int = 30):
        self.check_interval = check_interval
        self.metrics_history = defaultdict(deque)
        self.alerts = []
        self.health_checks = defaultdict(list)
        self.lock = threading.RLock()
        self.running = False
        self.monitor_thread = None
        
        # 阈值配置
        self.thresholds = {
            SystemComponent.CPU: {'warning': 70.0, 'critical': 90.0},
            SystemComponent.MEMORY: {'warning': 80.0, 'critical': 95.0},
            SystemComponent.DISK: {'warning': 85.0, 'critical': 95.0},
            SystemComponent.NETWORK: {'warning': 80.0, 'critical': 95.0}
        }
    
    def start_monitoring(self):
        """启动监控"""
        if not self.running:
            self.running = True
            self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
            self.monitor_thread.start()
            logger.info("System monitoring started")
    
    def stop_monitoring(self):
        """停止监控"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join()
        logger.info("System monitoring stopped")
    
    def _monitoring_loop(self):
        """监控循环"""
        while self.running:
            try:
                self._collect_system_metrics()
                self._check_health()
                self._analyze_trends()
                time.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                time.sleep(5)
    
    def _collect_system_metrics(self):
        """收集系统指标"""
        current_time = datetime.now()
        
        try:
            # CPU指标
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_metric = SystemMetric(
                component=SystemComponent.CPU,
                metric_name="usage_percent",
                value=cpu_percent,
                unit="%",
                timestamp=current_time,
                threshold_warning=self.thresholds[SystemComponent.CPU]['warning'],
                threshold_critical=self.thresholds[SystemComponent.CPU]['critical']
            )
            
            # 内存指标
            memory = psutil.virtual_memory()
            memory_metric = SystemMetric(
                component=SystemComponent.MEMORY,
                metric_name="usage_percent",
                value=memory.percent,
                unit="%",
                timestamp=current_time,
                threshold_warning=self.thresholds[SystemComponent.MEMORY]['warning'],
                threshold_critical=self.thresholds[SystemComponent.MEMORY]['critical']
            )
            
            # 磁盘指标
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            disk_metric = SystemMetric(
                component=SystemComponent.DISK,
                metric_name="usage_percent",
                value=disk_percent,
                unit="%",
                timestamp=current_time,
                threshold_warning=self.thresholds[SystemComponent.DISK]['warning'],
                threshold_critical=self.thresholds[SystemComponent.DISK]['critical']
            )
            
            # 网络指标
            network = psutil.net_io_counters()
            network_metric = SystemMetric(
                component=SystemComponent.NETWORK,
                metric_name="bytes_sent",
                value=network.bytes_sent,
                unit="bytes",
                timestamp=current_time,
                threshold_warning=None,
                threshold_critical=None
            )
            
            # 存储指标
            with self.lock:
                for metric in [cpu_metric, memory_metric, disk_metric, network_metric]:
                    self.metrics_history[f"{metric.component.value}_{metric.metric_name}"].append(metric)
                    
                    # 保持最近1000个数据点
                    if len(self.metrics_history[f"{metric.component.value}_{metric.metric_name}"]) > 1000:
                        self.metrics_history[f"{metric.component.value}_{metric.metric_name}"].popleft()
                    
                    # 检查阈值
                    self._check_threshold(metric)
                    
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
    
    def _check_threshold(self, metric: SystemMetric):
        """检查阈值"""
        if metric.threshold_critical and metric.value >= metric.threshold_critical:
            self._trigger_alert(
                AlertLevel.CRITICAL,
                metric.component,
                f"{metric.component.value.title()} Critical",
                f"{metric.metric_name} is at {metric.value}{metric.unit} (threshold: {metric.threshold_critical}{metric.unit})",
                {'metric': asdict(metric)}
            )
        elif metric.threshold_warning and metric.value >= metric.threshold_warning:
            self._trigger_alert(
                AlertLevel.WARNING,
                metric.component,
                f"{metric.component.value.title()} Warning",
                f"{metric.metric_name} is at {metric.value}{metric.unit} (threshold: {metric.threshold_warning}{metric.unit})",
                {'metric': asdict(metric)}
            )
    
    def _check_health(self):
        """执行健康检查"""
        current_time = datetime.now()
        
        # 检查进程健康
        try:
            start_time = time.time()
            process_count = len(psutil.pids())
            response_time = time.time() - start_time
            
            status = HealthStatus.HEALTHY
            message = f"Process count: {process_count}"
            
            if process_count > 1000:
                status = HealthStatus.WARNING
                message += " (high process count)"
            
            health_check = HealthCheck(
                component=SystemComponent.APPLICATION,
                name="process_count",
                status=status,
                message=message,
                timestamp=current_time,
                response_time=response_time,
                details={'process_count': process_count}
            )
            
            with self.lock:
                self.health_checks[SystemComponent.APPLICATION].append(health_check)
                if len(self.health_checks[SystemComponent.APPLICATION]) > 100:
                    self.health_checks[SystemComponent.APPLICATION].pop(0)
                    
        except Exception as e:
            logger.error(f"Health check error: {e}")
    
    def _analyze_trends(self):
        """分析趋势"""
        with self.lock:
            for metric_key, metrics in self.metrics_history.items():
                if len(metrics) >= 10:  # 至少需要10个数据点
                    self._analyze_metric_trend(metric_key, list(metrics)[-10:])
    
    def _analyze_metric_trend(self, metric_key: str, recent_metrics: List[SystemMetric]):
        """分析指标趋势"""
        try:
            values = [m.value for m in recent_metrics]
            times = [(m.timestamp.timestamp() - recent_metrics[0].timestamp.timestamp()) / 60 for m in recent_metrics]
            
            # 计算趋势
            if len(values) >= 2:
                # 简单线性回归计算斜率
                n = len(values)
                sum_x = sum(times)
                sum_y = sum(values)
                sum_xy = sum(x * y for x, y in zip(times, values))
                sum_x2 = sum(x * x for x in times)
                
                if n * sum_x2 - sum_x * sum_x != 0:
                    slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
                    
                    # 如果趋势增长过快，发出预警
                    if slope > 5:  # 每分钟增长超过5个单位
                        component = recent_metrics[0].component
                        self._trigger_alert(
                            AlertLevel.WARNING,
                            component,
                            f"{component.value.title()} Trend Alert",
                            f"Rapid increase detected in {metric_key}: {slope:.2f} per minute",
                            {'slope': slope, 'metric_key': metric_key}
                        )
                        
        except Exception as e:
            logger.warning(f"Trend analysis error for {metric_key}: {e}")
    
    def _trigger_alert(self, level: AlertLevel, component: SystemComponent,
                      title: str, description: str, metadata: Dict[str, Any]):
        """触发告警"""
        alert = Alert(
            alert_id=f"alert_{int(time.time())}_{component.value}",
            level=level,
            component=component,
            title=title,
            description=description,
            timestamp=datetime.now(),
            resolved_at=None,
            auto_resolved=False,
            actions_taken=[],
            metadata=metadata
        )
        
        with self.lock:
            self.alerts.append(alert)
            
            # 保持最近1000个告警
            if len(self.alerts) > 1000:
                self.alerts.pop(0)
        
        logger.warning(f"Alert triggered: {title} - {description}")
    
    def get_current_metrics(self) -> Dict[str, Any]:
        """获取当前指标"""
        with self.lock:
            current_metrics = {}
            
            for metric_key, metrics in self.metrics_history.items():
                if metrics:
                    latest_metric = metrics[-1]
                    current_metrics[metric_key] = {
                        'value': latest_metric.value,
                        'unit': latest_metric.unit,
                        'timestamp': latest_metric.timestamp.isoformat(),
                        'threshold_warning': latest_metric.threshold_warning,
                        'threshold_critical': latest_metric.threshold_critical
                    }
            
            return current_metrics
    
    def get_alerts(self, hours: int = 24, level: AlertLevel = None) -> List[Dict[str, Any]]:
        """获取告警列表"""
        with self.lock:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            filtered_alerts = [
                alert for alert in self.alerts
                if alert.timestamp >= cutoff_time
            ]
            
            if level:
                filtered_alerts = [
                    alert for alert in filtered_alerts
                    if alert.level == level
                ]
            
            return [asdict(alert) for alert in filtered_alerts]

class AutoHealer:
    """自动修复器"""
    
    def __init__(self):
        self.healing_actions = {}
        self.healing_history = []
        self.lock = threading.Lock()
        
        # 注册默认修复动作
        self._register_default_actions()
    
    def _register_default_actions(self):
        """注册默认修复动作"""
        self.healing_actions = {
            f"{SystemComponent.MEMORY.value}_critical": self._free_memory,
            f"{SystemComponent.DISK.value}_critical": self._clean_disk,
            f"{SystemComponent.APPLICATION.value}_unhealthy": self._restart_service
        }
    
    def register_healing_action(self, trigger: str, action: Callable):
        """注册修复动作"""
        with self.lock:
            self.healing_actions[trigger] = action
            logger.info(f"Registered healing action for trigger: {trigger}")
    
    def trigger_healing(self, alert: Alert) -> bool:
        """触发自动修复"""
        trigger_key = f"{alert.component.value}_{alert.level.value}"
        
        with self.lock:
            action = self.healing_actions.get(trigger_key)
            
            if action:
                try:
                    logger.info(f"Triggering auto-healing for: {trigger_key}")
                    
                    start_time = time.time()
                    result = action(alert)
                    duration = time.time() - start_time
                    
                    healing_record = {
                        'timestamp': datetime.now(),
                        'alert_id': alert.alert_id,
                        'trigger': trigger_key,
                        'action': action.__name__,
                        'success': result,
                        'duration': duration,
                        'details': alert.metadata
                    }
                    
                    self.healing_history.append(healing_record)
                    
                    # 保持最近100个修复记录
                    if len(self.healing_history) > 100:
                        self.healing_history.pop(0)
                    
                    if result:
                        alert.auto_resolved = True
                        alert.resolved_at = datetime.now()
                        alert.actions_taken.append(f"Auto-healed by {action.__name__}")
                        logger.info(f"Auto-healing successful for {trigger_key}")
                    else:
                        logger.warning(f"Auto-healing failed for {trigger_key}")
                    
                    return result
                    
                except Exception as e:
                    logger.error(f"Auto-healing error for {trigger_key}: {e}")
                    return False
            
            return False
    
    def _free_memory(self, alert: Alert) -> bool:
        """释放内存"""
        try:
            # 触发垃圾回收
            import gc
            collected = gc.collect()
            
            # 清理系统缓存（Linux）
            if os.name == 'posix':
                try:
                    subprocess.run(['sync'], check=True)
                    subprocess.run(['echo', '1', '>', '/proc/sys/vm/drop_caches'], shell=True)
                except subprocess.CalledProcessError:
                    pass
            
            logger.info(f"Memory freed: {collected} objects collected")
            return True
            
        except Exception as e:
            logger.error(f"Failed to free memory: {e}")
            return False
    
    def _clean_disk(self, alert: Alert) -> bool:
        """清理磁盘空间"""
        try:
            cleaned_space = 0
            
            # 清理临时文件
            temp_dirs = ['/tmp', '/var/tmp']
            for temp_dir in temp_dirs:
                if os.path.exists(temp_dir):
                    for root, dirs, files in os.walk(temp_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            try:
                                file_size = os.path.getsize(file_path)
                                # 删除超过7天的临时文件
                                if time.time() - os.path.getmtime(file_path) > 7 * 24 * 3600:
                                    os.remove(file_path)
                                    cleaned_space += file_size
                            except OSError:
                                pass
            
            # 清理日志文件（保留最近的）
            log_dirs = ['logs', '/var/log']
            for log_dir in log_dirs:
                if os.path.exists(log_dir):
                    for file in os.listdir(log_dir):
                        if file.endswith('.log') and file.startswith('old_'):
                            file_path = os.path.join(log_dir, file)
                            try:
                                file_size = os.path.getsize(file_path)
                                os.remove(file_path)
                                cleaned_space += file_size
                            except OSError:
                                pass
            
            logger.info(f"Disk cleaned: {cleaned_space / 1024 / 1024:.2f} MB freed")
            return cleaned_space > 0
            
        except Exception as e:
            logger.error(f"Failed to clean disk: {e}")
            return False
    
    def _restart_service(self, alert: Alert) -> bool:
        """重启服务"""
        try:
            # 这里应该实现具体的服务重启逻辑
            # 由于安全原因，这里只是模拟
            logger.info("Service restart simulation - would restart application components")
            
            # 可以根据具体需求实现：
            # - 重启Web服务器
            # - 重启数据库连接
            # - 重启缓存服务
            # - 等等
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to restart service: {e}")
            return False
    
    def get_healing_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """获取修复历史"""
        with self.lock:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            recent_history = [
                record for record in self.healing_history
                if record['timestamp'] >= cutoff_time
            ]
            
            # 转换datetime对象为字符串
            for record in recent_history:
                record['timestamp'] = record['timestamp'].isoformat()
            
            return recent_history

class CapacityPlanner:
    """容量规划器"""
    
    def __init__(self):
        self.predictions = {}
        self.lock = threading.Lock()
    
    def analyze_capacity_trends(self, metrics_history: Dict[str, deque]) -> Dict[str, Any]:
        """分析容量趋势"""
        with self.lock:
            predictions = {}
            
            for metric_key, metrics in metrics_history.items():
                if len(metrics) >= 20:  # 至少需要20个数据点
                    prediction = self._predict_capacity(metric_key, list(metrics))
                    if prediction:
                        predictions[metric_key] = prediction
            
            self.predictions = predictions
            return predictions
    
    def _predict_capacity(self, metric_key: str, metrics: List[SystemMetric]) -> Optional[Dict[str, Any]]:
        """预测容量"""
        try:
            # 取最近的数据点
            recent_metrics = metrics[-20:]
            values = [m.value for m in recent_metrics]
            times = [m.timestamp.timestamp() for m in recent_metrics]
            
            # 计算增长率
            if len(values) >= 2:
                time_span = (times[-1] - times[0]) / 3600  # 转换为小时
                if time_span > 0:
                    growth_rate = (values[-1] - values[0]) / time_span  # 每小时增长率
                    
                    # 预测未来容量
                    current_value = values[-1]
                    threshold = recent_metrics[0].threshold_critical or 100
                    
                    if growth_rate > 0:
                        # 计算到达阈值的时间
                        time_to_threshold = (threshold - current_value) / growth_rate
                        
                        # 预测未来1天、7天、30天的值
                        predictions = {
                            '1_day': current_value + growth_rate * 24,
                            '7_days': current_value + growth_rate * 24 * 7,
                            '30_days': current_value + growth_rate * 24 * 30
                        }
                        
                        # 生成建议
                        recommendations = []
                        if time_to_threshold < 24:
                            recommendations.append(f"Critical: Will reach threshold in {time_to_threshold:.1f} hours")
                        elif time_to_threshold < 7 * 24:
                            recommendations.append(f"Warning: Will reach threshold in {time_to_threshold/24:.1f} days")
                        
                        if growth_rate > threshold * 0.1:  # 增长率超过阈值的10%
                            recommendations.append("High growth rate detected, consider scaling")
                        
                        return {
                            'current_value': current_value,
                            'growth_rate_per_hour': growth_rate,
                            'time_to_threshold_hours': time_to_threshold if growth_rate > 0 else None,
                            'predictions': predictions,
                            'recommendations': recommendations,
                            'confidence': min(len(values) / 20, 1.0)  # 置信度基于数据点数量
                        }
            
            return None
            
        except Exception as e:
            logger.error(f"Capacity prediction error for {metric_key}: {e}")
            return None
    
    def get_capacity_recommendations(self) -> List[Dict[str, Any]]:
        """获取容量建议"""
        with self.lock:
            recommendations = []
            
            for metric_key, prediction in self.predictions.items():
                if prediction and prediction['recommendations']:
                    recommendations.append({
                        'metric': metric_key,
                        'current_value': prediction['current_value'],
                        'growth_rate': prediction['growth_rate_per_hour'],
                        'recommendations': prediction['recommendations'],
                        'confidence': prediction['confidence']
                    })
            
            # 按紧急程度排序
            recommendations.sort(key=lambda x: x['growth_rate'], reverse=True)
            
            return recommendations

class IntelligentOpsManager:
    """智能运维管理器主类"""
    
    def __init__(self, app=None):
        self.app = app
        self.system_monitor = SystemMonitor()
        self.auto_healer = AutoHealer()
        self.capacity_planner = CapacityPlanner()
        
        # 运维统计
        self.ops_stats = {
            'alerts_triggered': 0,
            'auto_healings_attempted': 0,
            'auto_healings_successful': 0,
            'capacity_warnings': 0
        }
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """初始化Flask应用"""
        self.app = app
        
        # 启动系统监控
        self.system_monitor.start_monitoring()
        
        # 注册应用关闭时的清理
        import atexit
        atexit.register(self.cleanup)
        
        logger.info("Intelligent ops manager initialized")
    
    def cleanup(self):
        """清理资源"""
        self.system_monitor.stop_monitoring()
    
    def process_alert(self, alert: Alert) -> bool:
        """处理告警"""
        self.ops_stats['alerts_triggered'] += 1
        
        # 尝试自动修复
        if alert.level in [AlertLevel.CRITICAL, AlertLevel.ERROR]:
            self.ops_stats['auto_healings_attempted'] += 1
            
            if self.auto_healer.trigger_healing(alert):
                self.ops_stats['auto_healings_successful'] += 1
                return True
        
        return False
    
    def run_capacity_analysis(self) -> Dict[str, Any]:
        """运行容量分析"""
        metrics_history = self.system_monitor.metrics_history
        capacity_analysis = self.capacity_planner.analyze_capacity_trends(metrics_history)
        
        recommendations = self.capacity_planner.get_capacity_recommendations()
        if recommendations:
            self.ops_stats['capacity_warnings'] += len(recommendations)
        
        return {
            'analysis': capacity_analysis,
            'recommendations': recommendations,
            'timestamp': datetime.now().isoformat()
        }
    
    def get_system_overview(self) -> Dict[str, Any]:
        """获取系统概览"""
        current_metrics = self.system_monitor.get_current_metrics()
        recent_alerts = self.system_monitor.get_alerts(hours=24)
        healing_history = self.auto_healer.get_healing_history(hours=24)
        capacity_recommendations = self.capacity_planner.get_capacity_recommendations()
        
        # 计算健康分数
        health_score = self._calculate_health_score(current_metrics, recent_alerts)
        
        return {
            'health_score': health_score,
            'current_metrics': current_metrics,
            'alerts_24h': len(recent_alerts),
            'critical_alerts_24h': len([a for a in recent_alerts if a['level'] == AlertLevel.CRITICAL.value]),
            'auto_healings_24h': len(healing_history),
            'successful_healings_24h': len([h for h in healing_history if h['success']]),
            'capacity_warnings': len(capacity_recommendations),
            'ops_stats': self.ops_stats.copy(),
            'timestamp': datetime.now().isoformat()
        }
    
    def _calculate_health_score(self, metrics: Dict[str, Any], alerts: List[Dict[str, Any]]) -> float:
        """计算系统健康分数"""
        try:
            base_score = 100.0
            
            # 根据当前指标调整分数
            for metric_key, metric_data in metrics.items():
                value = metric_data['value']
                warning_threshold = metric_data.get('threshold_warning')
                critical_threshold = metric_data.get('threshold_critical')
                
                if critical_threshold and value >= critical_threshold:
                    base_score -= 20
                elif warning_threshold and value >= warning_threshold:
                    base_score -= 10
            
            # 根据最近告警调整分数
            critical_alerts = len([a for a in alerts if a['level'] == AlertLevel.CRITICAL.value])
            error_alerts = len([a for a in alerts if a['level'] == AlertLevel.ERROR.value])
            warning_alerts = len([a for a in alerts if a['level'] == AlertLevel.WARNING.value])
            
            base_score -= critical_alerts * 15
            base_score -= error_alerts * 10
            base_score -= warning_alerts * 5
            
            # 确保分数在0-100之间
            return max(0, min(100, base_score))
            
        except Exception as e:
            logger.error(f"Health score calculation error: {e}")
            return 50.0  # 默认分数

# 全局实例
_ops_manager = None

def get_ops_manager() -> IntelligentOpsManager:
    """获取智能运维管理器实例"""
    global _ops_manager
    if _ops_manager is None:
        _ops_manager = IntelligentOpsManager()
    return _ops_manager

def init_intelligent_ops_management(app):
    """初始化智能运维管理"""
    try:
        ops_manager = get_ops_manager()
        ops_manager.init_app(app)
        
        logger.info("Intelligent ops management system initialized successfully")
        return ops_manager
        
    except Exception as e:
        logger.error(f"Failed to initialize intelligent ops management: {e}")
        raise

# 装饰器
def monitor_function_health(component: SystemComponent = SystemComponent.APPLICATION):
    """函数健康监控装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                
                # 记录成功执行
                execution_time = time.time() - start_time
                if execution_time > 5.0:  # 执行时间超过5秒发出警告
                    ops_manager = get_ops_manager()
                    ops_manager.system_monitor._trigger_alert(
                        AlertLevel.WARNING,
                        component,
                        f"Slow Function Execution",
                        f"Function {func.__name__} took {execution_time:.2f}s to execute",
                        {'function': func.__name__, 'execution_time': execution_time}
                    )
                
                return result
                
            except Exception as e:
                # 记录执行错误
                ops_manager = get_ops_manager()
                ops_manager.system_monitor._trigger_alert(
                    AlertLevel.ERROR,
                    component,
                    f"Function Execution Error",
                    f"Function {func.__name__} failed: {str(e)}",
                    {'function': func.__name__, 'error': str(e)}
                )
                raise
        
        return wrapper
    return decorator 