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
import os # Added for path validation

from .unified_logging import get_logger

logger = get_logger('unified_monitoring')

class UnifiedMonitoringSystem:
    """统一的监控系统"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """初始化统一监控系统"""
        self.logger = get_logger('unified_monitoring')
        self.config = config or {}
        
        # 检测操作系统
        import platform
        self.os_type = platform.system().lower()
        self.logger.info(f"检测到操作系统: {self.os_type}")
        
        # 根据操作系统调整告警阈值
        if self.os_type == 'darwin':  # macOS
            self.alert_thresholds = {
                'cpu': self.config.get('cpu_threshold', 85.0),      # macOS CPU 阈值稍高
                'memory': self.config.get('memory_threshold', 90.0), # macOS 内存阈值更高，因为会积极使用内存
                'disk': self.config.get('disk_threshold', 85.0),     # 磁盘阈值保持不变
                'network': self.config.get('network_threshold', 80.0)
            }
        else:  # Linux/Windows
            self.alert_thresholds = {
                'cpu': self.config.get('cpu_threshold', 80.0),
                'memory': self.config.get('memory_threshold', 80.0),
                'disk': self.config.get('disk_threshold', 85.0),
                'network': self.config.get('network_threshold', 80.0)
            }
        
        # 监控配置
        self.collect_interval = self.config.get('collect_interval', 5) # Changed from 30 to 5
        self.metrics_history = defaultdict(lambda: deque(maxlen=1000))
        self.alerts = deque(maxlen=100)
        self.system_status = {}
        
        # 启动监控线程
        self._monitoring_enabled = True
        self._monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self._monitor_thread.start()
        
        self.logger.info("统一监控系统初始化完成，收集间隔: 5秒")
    
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
        """监控循环"""
        while self._monitoring_enabled:
            try:
                self._collect_system_metrics()
                self._check_alerts()
                
                # 确保收集间隔是有效的整数值
                interval = self.collect_interval
                if interval is None or not isinstance(interval, (int, float)) or interval <= 0:
                    interval = 30  # 默认30秒
                    logger.warning(f"无效的收集间隔，使用默认值: {interval}秒")
                time.sleep(interval)
                
            except Exception as e:
                logger.error(f"监控循环异常: {e}")
                time.sleep(5)  # 出错时等待5秒再继续
    
    def _collect_system_metrics(self):
        """收集系统指标"""
        try:
            current_time = time.time()
            
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=0.1)
            self.metrics_history['cpu'].append({
                'timestamp': current_time,
                'value': cpu_percent
            })
            
            # 内存使用率 - 根据操作系统使用不同的计算方式
            memory = psutil.virtual_memory()
            if self.os_type == 'darwin':  # macOS
                # macOS 上，使用更准确的计算方式，类似 htop 的显示
                # 计算实际被应用程序使用的内存（不包括缓存）
                try:
                    # 使用 vm_stat 命令获取更详细的内存信息
                    import subprocess
                    result = subprocess.run(['vm_stat'], capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        vm_stats = {}
                        for line in result.stdout.split('\n'):
                            if ':' in line:
                                key, value = line.split(':', 1)
                                key = key.strip()
                                value = value.strip().rstrip('.')
                                if value.isdigit():
                                    vm_stats[key] = int(value)
                        
                        if 'Pages active' in vm_stats and 'Pages wired down' in vm_stats:
                            # 计算实际使用的内存（活动页面 + 固定页面）
                            page_size = 16384  # 16KB
                            active_pages = vm_stats.get('Pages active', 0)
                            wired_pages = vm_stats.get('Pages wired down', 0)
                            used_memory = (active_pages + wired_pages) * page_size
                            memory_percent = (used_memory / memory.total) * 100
                        else:
                            # 回退到 available 计算
                            memory_percent = (memory.total - memory.available) / memory.total * 100
                    else:
                        # 回退到 available 计算
                        memory_percent = (memory.total - memory.available) / memory.total * 100
                        
                except Exception as e:
                    # 回退到 available 计算
                    memory_percent = (memory.total - memory.available) / memory.total * 100
                
                memory_used_gb = (memory.total - memory.available) / (1024**3)
                memory_available_gb = memory.available / (1024**3)
                memory_total_gb = memory.total / (1024**3)
                
                # 记录详细的内存信息用于调试
                self.logger.debug(f"macOS 内存计算: 总内存={memory_total_gb:.1f}GB, 已用={memory_used_gb:.1f}GB, 可用={memory_available_gb:.1f}GB, 使用率={memory_percent:.1f}%")
                
            else:  # Linux/Windows
                # 其他系统使用标准的 percent 计算
                memory_percent = memory.percent
                memory_used_gb = memory.used / (1024**3)
                memory_available_gb = memory.available / (1024**3)
                memory_total_gb = memory.total / (1024**3)
            
            self.metrics_history['memory'].append({
                'timestamp': current_time,
                'value': memory_percent,
                'available': memory.available,
                'total': memory.total,
                'used_gb': memory_used_gb,
                'available_gb': memory_available_gb,
                'total_gb': memory_total_gb,
                'os_type': self.os_type
            })
            
            # 磁盘使用率 - 修复路径问题
            disk_percent = 0
            disk_total = 0
            disk_free = 0
            
            # 尝试多个可能的磁盘路径
            disk_paths = ['/', '/System/Volumes/Data', '/Users']
            for path in disk_paths:
                try:
                    if os.path.exists(path):
                        disk = psutil.disk_usage(path)
                        # 优先使用根目录，除非其他路径使用率明显更高且合理
                        if path == '/' or (disk.percent > disk_percent and disk.percent < 95):
                            disk_percent = disk.percent
                            disk_total = disk.total
                            disk_free = disk.free
                            break
                except Exception as e:
                    continue
            
            # 如果没有找到有效的磁盘路径，使用根目录
            if disk_percent == 0:
                try:
                    disk = psutil.disk_usage('/')
                    disk_percent = disk.percent
                    disk_total = disk.total
                    disk_free = disk.free
                except Exception as e:
                    disk_percent = 0
                    disk_total = 0
                    disk_free = 0
            
            self.metrics_history['disk'].append({
                'timestamp': current_time,
                'value': disk_percent,
                'free': disk_free,
                'total': disk_total
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
            
            # 确保告警阈值是有效的数值
            cpu_threshold = self.alert_thresholds.get('cpu', 80.0)
            memory_threshold = self.alert_thresholds.get('memory', 80.0)
            disk_threshold = self.alert_thresholds.get('disk', 85.0)
            
            # 验证阈值类型
            if not isinstance(cpu_threshold, (int, float)) or cpu_threshold <= 0:
                cpu_threshold = 80.0
            if not isinstance(memory_threshold, (int, float)) or memory_threshold <= 0:
                memory_threshold = 80.0
            if not isinstance(disk_threshold, (int, float)) or disk_threshold <= 0:
                disk_threshold = 85.0
            
            # CPU告警
            cpu_percent = current_metrics.get('cpu_percent', 0)
            if isinstance(cpu_percent, (int, float)) and cpu_percent > cpu_threshold:
                self._create_alert('CPU', 'high', 
                                 f"CPU使用率过高: {cpu_percent:.1f}%")
            
            # 内存告警
            memory_percent = current_metrics.get('memory_percent', 0)
            if isinstance(memory_percent, (int, float)) and memory_percent > memory_threshold:
                self._create_alert('Memory', 'high',
                                 f"内存使用率过高: {memory_percent:.1f}%")
            
            # 磁盘告警
            disk_percent = current_metrics.get('disk_percent', 0)
            if isinstance(disk_percent, (int, float)) and disk_percent > disk_threshold:
                self._create_alert('Disk', 'high',
                                 f"磁盘使用率过高: {disk_percent:.1f}%")
            
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
    
    def get_system_overview(self) -> Dict[str, Any]:
        """获取系统概览"""
        try:
            # 获取当前系统状态
            current_time = time.time()
            
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # 内存使用率
            memory = psutil.virtual_memory()
            if self.os_type == 'darwin':  # macOS
                # macOS 上，使用更准确的计算方式，类似 htop 的显示
                # 计算实际被应用程序使用的内存（不包括缓存）
                try:
                    # 使用 vm_stat 命令获取更详细的内存信息
                    import subprocess
                    result = subprocess.run(['vm_stat'], capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        vm_stats = {}
                        for line in result.stdout.split('\n'):
                            if ':' in line:
                                key, value = line.split(':', 1)
                                key = key.strip()
                                value = value.strip().rstrip('.')
                                if value.isdigit():
                                    vm_stats[key] = int(value)
                        
                        if 'Pages active' in vm_stats and 'Pages wired down' in vm_stats:
                            # 计算实际使用的内存（活动页面 + 固定页面）
                            page_size = 16384  # 16KB
                            active_pages = vm_stats.get('Pages active', 0)
                            wired_pages = vm_stats.get('Pages wired down', 0)
                            used_memory = (active_pages + wired_pages) * page_size
                            memory_percent = (used_memory / memory.total) * 100
                        else:
                            # 回退到 available 计算
                            memory_percent = (memory.total - memory.available) / memory.total * 100
                    else:
                        # 回退到 available 计算
                        memory_percent = (memory.total - memory.available) / memory.total * 100
                        
                except Exception as e:
                    # 回退到 available 计算
                    memory_percent = (memory.total - memory.available) / memory.total * 100
                
                memory_used_gb = (memory.total - memory.available) / (1024**3)
                memory_available_gb = memory.available / (1024**3)
                memory_total_gb = memory.total / (1024**3)
            else:  # Linux/Windows
                # 其他系统使用标准的 percent 计算
                memory_percent = memory.percent
                memory_used_gb = memory.used / (1024**3)
                memory_available_gb = memory.available / (1024**3)
                memory_total_gb = memory.total / (1024**3)
            
            # 磁盘使用率
            disk_percent = 0
            disk_total = 0
            disk_free = 0
            
            # 尝试多个可能的磁盘路径
            disk_paths = ['/', '/System/Volumes/Data', '/Users']
            for path in disk_paths:
                try:
                    if os.path.exists(path):
                        disk = psutil.disk_usage(path)
                        # 优先使用根目录，除非其他路径使用率明显更高且合理
                        if path == '/' or (disk.percent > disk_percent and disk.percent < 95):
                            disk_percent = disk.percent
                            disk_total = disk.total
                            disk_free = disk.free
                            break
                except Exception as e:
                    continue
            
            # 如果没有找到有效的磁盘路径，使用根目录
            if disk_percent == 0:
                try:
                    disk = psutil.disk_usage('/')
                    disk_percent = disk.percent
                    disk_total = disk.total
                    disk_free = disk.free
                except Exception as e:
                    disk_percent = 0
                    disk_total = 0
                    disk_free = 0
            
            # 网络使用情况
            network = psutil.net_io_counters()
            
            # 系统负载
            try:
                load_avg = psutil.getloadavg()
            except AttributeError:
                load_avg = (0, 0, 0)
            
            return {
                'timestamp': current_time,
                'cpu': {
                    'usage_percent': cpu_percent,
                    'status': 'normal' if cpu_percent < 80 else 'warning' if cpu_percent < 95 else 'critical'
                },
                'memory': {
                    'usage_percent': memory_percent,
                    'total_gb': memory_total_gb,
                    'available_gb': memory_available_gb,
                    'status': 'normal' if memory_percent < 80 else 'warning' if memory_percent < 95 else 'critical'
                },
                'disk': {
                    'usage_percent': disk_percent,
                    'total_gb': disk_total / (1024**3),
                    'free_gb': disk_free / (1024**3),
                    'status': 'normal' if disk_percent < 85 else 'warning' if disk_percent < 95 else 'critical'
                },
                'network': {
                    'bytes_sent': network.bytes_sent,
                    'bytes_recv': network.bytes_recv,
                    'packets_sent': network.packets_sent,
                    'packets_recv': network.packets_recv
                },
                'load_average': {
                    '1min': load_avg[0],
                    '5min': load_avg[1],
                    '15min': load_avg[2]
                },
                'alerts_count': len(self.alerts),
                'system_status': 'healthy' if len(self.alerts) == 0 else 'warning' if len(self.alerts) < 3 else 'critical'
            }
            
        except Exception as e:
            logger.error(f"获取系统概览失败: {e}")
            return {
                'error': str(e),
                'timestamp': time.time(),
                'system_status': 'error'
            }
    
    def run_capacity_analysis(self) -> Dict[str, Any]:
        """运行容量分析"""
        try:
            current_time = time.time()
            
            # 分析CPU容量
            cpu_history = list(self.metrics_history['cpu'])
            if cpu_history:
                cpu_avg = sum(item['value'] for item in cpu_history[-10:]) / len(cpu_history[-10:])
                cpu_trend = 'stable'
                if len(cpu_history) >= 20:
                    recent_avg = sum(item['value'] for item in cpu_history[-10:]) / 10
                    older_avg = sum(item['value'] for item in cpu_history[-20:-10]) / 10
                    if recent_avg > older_avg * 1.2:
                        cpu_trend = 'increasing'
                    elif recent_avg < older_avg * 0.8:
                        cpu_trend = 'decreasing'
            else:
                cpu_avg = 0
                cpu_trend = 'unknown'
            
            # 分析内存容量
            memory = psutil.virtual_memory()
            memory_usage = memory.percent
            memory_trend = 'stable'  # 简化版本，实际可以基于历史数据计算
            
            # 分析磁盘容量
            disk = psutil.disk_usage('/')
            disk_usage = disk.percent
            disk_trend = 'stable'  # 简化版本，实际可以基于历史数据计算
            
            # 容量建议
            recommendations = []
            if cpu_avg > 80:
                recommendations.append("CPU使用率较高，建议优化计算密集型任务或增加CPU资源")
            if memory_usage > 85:
                recommendations.append("内存使用率较高，建议检查内存泄漏或增加内存资源")
            if disk_usage > 90:
                recommendations.append("磁盘使用率较高，建议清理临时文件或增加存储空间")
            
            return {
                'timestamp': current_time,
                'cpu_analysis': {
                    'current_usage': cpu_avg,
                    'trend': cpu_trend,
                    'capacity_status': 'adequate' if cpu_avg < 70 else 'limited' if cpu_avg < 90 else 'critical'
                },
                'memory_analysis': {
                    'current_usage': memory_usage,
                    'trend': memory_trend,
                    'capacity_status': 'adequate' if memory_usage < 70 else 'limited' if memory_usage < 90 else 'critical'
                },
                'disk_analysis': {
                    'current_usage': disk_usage,
                    'trend': disk_trend,
                    'capacity_status': 'adequate' if disk_usage < 80 else 'limited' if disk_usage < 95 else 'critical'
                },
                'recommendations': recommendations,
                'overall_capacity': 'adequate' if len(recommendations) == 0 else 'limited' if len(recommendations) < 2 else 'critical'
            }
            
        except Exception as e:
            logger.error(f"容量分析失败: {e}")
            return {
                'error': str(e),
                'timestamp': time.time(),
                'overall_capacity': 'error'
            }
    
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

    def record_counter(self, metric_name: str, value: int = 1, tags: Dict[str, str] = None):
        """记录计数器指标"""
        try:
            current_time = time.time()
            metric_key = f"{metric_name}_{hash(str(tags)) if tags else 'default'}"
            
            if metric_key not in self.metrics_history:
                self.metrics_history[metric_key] = deque(maxlen=1000)
            
            self.metrics_history[metric_key].append({
                'timestamp': current_time,
                'value': value,
                'tags': tags or {},
                'type': 'counter'
            })
            
            logger.debug(f"记录计数器指标: {metric_name} = {value}")
            
        except Exception as e:
            logger.error(f"记录计数器指标失败: {e}")
    
    def record_timer(self, metric_name: str, duration: float, tags: Dict[str, str] = None):
        """记录计时器指标"""
        try:
            current_time = time.time()
            metric_key = f"{metric_name}_{hash(str(tags)) if tags else 'default'}"
            
            if metric_key not in self.metrics_history:
                self.metrics_history[metric_key] = deque(maxlen=1000)
            
            self.metrics_history[metric_key].append({
                'timestamp': current_time,
                'value': duration,
                'tags': tags or {},
                'type': 'timer'
            })
            
            logger.debug(f"记录计时器指标: {metric_name} = {duration:.3f}s")
            
        except Exception as e:
            logger.error(f"记录计时器指标失败: {e}")
    
    def record_request(self, method: str, endpoint: str, status_code: int, duration: float, **kwargs):
        """记录请求指标"""
        try:
            current_time = time.time()
            
            # 提取额外参数
            user_id = kwargs.get('user_id')
            ip_address = kwargs.get('ip_address')
            user_agent = kwargs.get('user_agent')
            
            # 构建标签
            tags = {
                'method': method,
                'endpoint': endpoint,
                'status_code': str(status_code)
            }
            
            # 添加可选标签
            if user_id:
                tags['user_id'] = str(user_id)
            if ip_address:
                tags['ip_address'] = str(ip_address)
            if user_agent:
                tags['user_agent'] = str(user_agent)[:100]  # 限制长度
            
            # 记录请求计数
            self.record_counter('requests.total', 1, tags)
            
            # 记录请求时长
            self.record_timer('requests.duration', duration, tags)
            
            # 记录状态码分布
            self.record_counter(f'requests.status.{status_code}', 1, {
                'method': method,
                'endpoint': endpoint
            })
            
            # 如果有用户ID，记录用户相关指标
            if user_id:
                self.record_counter('requests.by_user', 1, {
                    'user_id': str(user_id),
                    'method': method,
                    'endpoint': endpoint
                })
            
            logger.debug(f"记录请求指标: {method} {endpoint} {status_code} {duration:.3f}s user_id:{user_id}")
            
        except Exception as e:
            logger.error(f"记录请求指标失败: {e}")
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """获取指标摘要"""
        try:
            summary = {
                'timestamp': time.time(),
                'total_metrics': len(self.metrics_history),
                'metrics_by_type': defaultdict(int),
                'recent_metrics': {}
            }
            
            for metric_key, history in self.metrics_history.items():
                if history:
                    latest = history[-1]
                    metric_type = latest.get('type', 'unknown')
                    summary['metrics_by_type'][metric_type] += 1
                    
                    # 记录最近的指标值
                    if len(summary['recent_metrics']) < 10:  # 限制数量
                        summary['recent_metrics'][metric_key] = {
                            'value': latest['value'],
                            'timestamp': latest['timestamp'],
                            'type': metric_type
                        }
            
            return summary
            
        except Exception as e:
            logger.error(f"获取指标摘要失败: {e}")
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
    
    # 处理带参数的装饰器调用
    if func is None:
        # @monitor_function() 或 @monitor_function
        return decorator
    elif callable(func):
        # @monitor_function 直接装饰函数
        return decorator(func)
    else:
        # @monitor_function('upload.file') 带参数的装饰器
        def param_decorator(f):
            return decorator(f)
        return param_decorator

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
