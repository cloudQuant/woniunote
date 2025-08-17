"""
增强的日志记录系统
提供结构化日志记录、性能监控和敏感信息脱敏
"""
import os
import time
import json
import logging
import logging.handlers
import threading
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Union
from enum import Enum
from pathlib import Path
from collections import defaultdict, deque

class LogLevel(Enum):
    """日志级别"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class LogCategory(Enum):
    """日志分类"""
    ACCESS = "access"
    ERROR = "error"
    PERFORMANCE = "performance"
    SECURITY = "security"
    BUSINESS = "business"
    SYSTEM = "system"
    AUDIT = "audit"

class PerformanceMetrics:
    """性能指标收集器"""
    
    def __init__(self, max_samples: int = 1000):
        self.max_samples = max_samples
        self.metrics = defaultdict(lambda: deque(maxlen=max_samples))
        self.lock = threading.Lock()
    
    def record_metric(self, name: str, value: float, timestamp: float = None):
        """记录性能指标"""
        timestamp = timestamp or time.time()
        with self.lock:
            self.metrics[name].append({
                'value': value,
                'timestamp': timestamp
            })
    
    def get_stats(self, name: str, time_window: int = 3600) -> Dict[str, float]:
        """获取指标统计信息"""
        with self.lock:
            if name not in self.metrics:
                return {}
            
            current_time = time.time()
            cutoff_time = current_time - time_window
            
            # 过滤时间窗口内的数据
            recent_values = [
                item['value'] for item in self.metrics[name]
                if item['timestamp'] >= cutoff_time
            ]
            
            if not recent_values:
                return {}
            
            return {
                'count': len(recent_values),
                'avg': sum(recent_values) / len(recent_values),
                'min': min(recent_values),
                'max': max(recent_values),
                'p50': self._percentile(recent_values, 50),
                'p95': self._percentile(recent_values, 95),
                'p99': self._percentile(recent_values, 99)
            }
    
    def _percentile(self, values: list, percentile: int) -> float:
        """计算百分位数"""
        if not values:
            return 0.0
        
        sorted_values = sorted(values)
        k = (len(sorted_values) - 1) * percentile / 100
        f = int(k)
        c = k - f
        
        if f + 1 < len(sorted_values):
            return sorted_values[f] * (1 - c) + sorted_values[f + 1] * c
        else:
            return sorted_values[f]

class SecurityLogger:
    """安全事件日志记录器"""
    
    def __init__(self, logger_name: str = 'security'):
        self.logger_name = logger_name
        self.suspicious_patterns = {
            'sql_injection': [
                r'union\s+select', r'drop\s+table', r'delete\s+from',
                r'insert\s+into', r'update\s+set', r'or\s+1\s*=\s*1'
            ],
            'xss_attempt': [
                r'<script[^>]*>', r'javascript:', r'onerror\s*=',
                r'onload\s*=', r'eval\s*\(', r'alert\s*\('
            ],
            'path_traversal': [
                r'\.\./.*\.\./.*\.\.',  r'\.\.\\.*\.\.\\.*\.\.',
                r'/etc/passwd', r'c:\\windows\\system32'
            ]
        }
    
    def detect_suspicious_activity(self, content: str) -> Dict[str, list]:
        """检测可疑活动"""
        import re
        
        detected = {}
        for pattern_type, patterns in self.suspicious_patterns.items():
            matches = []
            for pattern in patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    matches.append(pattern)
            
            if matches:
                detected[pattern_type] = matches
        
        return detected
    
    def log_security_event(
        self, 
        event_type: str, 
        details: Dict[str, Any],
        severity: str = 'medium'
    ):
        """记录安全事件"""
        enhanced_logger = EnhancedLogger(self.logger_name)
        
        security_log = {
            'category': LogCategory.SECURITY.value,
            'event_type': event_type,
            'severity': severity,
            'details': details,
            'timestamp': time.time()
        }
        
        if severity in ['high', 'critical']:
            enhanced_logger.error(f"安全事件: {event_type}", security_log)
        else:
            enhanced_logger.warning(f"安全事件: {event_type}", security_log)

class EnhancedLogger:
    """增强的日志记录器"""
    
    def __init__(
        self, 
        logger_name: str,
        log_dir: str = None,
        max_file_size: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 5
    ):
        self.logger_name = logger_name
        self.log_dir = log_dir or self._get_default_log_dir()
        self.max_file_size = max_file_size
        self.backup_count = backup_count
        
        # 确保日志目录存在
        Path(self.log_dir).mkdir(parents=True, exist_ok=True)
        
        # 创建logger
        self.logger = self._setup_logger()
        
        # 性能指标收集器
        self.performance_metrics = PerformanceMetrics()
        
        # 安全日志记录器
        self.security_logger = SecurityLogger(logger_name)
        
        # 敏感字段列表
        self.sensitive_fields = {
            'password', 'token', 'secret', 'key', 'authorization',
            'cookie', 'session', 'csrf_token', 'api_key', 'private_key',
            'access_token', 'refresh_token', 'email', 'phone', 'id_card'
        }
    
    def _get_default_log_dir(self) -> str:
        """获取默认日志目录"""
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base_dir, '..', 'enhanced_logs')
    
    def _setup_logger(self) -> logging.Logger:
        """设置logger"""
        logger = logging.getLogger(self.logger_name)
        logger.setLevel(logging.DEBUG)
        
        # 避免重复添加handler
        if logger.handlers:
            return logger
        
        # 文件handler
        log_file = os.path.join(self.log_dir, f'{self.logger_name}.log')
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, 
            maxBytes=self.max_file_size,
            backupCount=self.backup_count,
            encoding='utf-8'
        )
        
        # 格式化器
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        return logger
    
    def sanitize_data(self, data: Any) -> Any:
        """脱敏处理"""
        if isinstance(data, dict):
            sanitized = {}
            for key, value in data.items():
                if self._is_sensitive_field(key):
                    sanitized[key] = self._mask_value(value)
                elif isinstance(value, (dict, list)):
                    sanitized[key] = self.sanitize_data(value)
                else:
                    sanitized[key] = value
            return sanitized
        elif isinstance(data, list):
            return [self.sanitize_data(item) for item in data]
        elif isinstance(data, str):
            # 检测可疑内容
            suspicious = self.security_logger.detect_suspicious_activity(data)
            if suspicious:
                self.security_logger.log_security_event(
                    'suspicious_content_detected',
                    {'patterns': suspicious, 'content_length': len(data)}
                )
            return data
        else:
            return data
    
    def _is_sensitive_field(self, field_name: str) -> bool:
        """检查是否为敏感字段"""
        field_lower = field_name.lower()
        return any(sensitive in field_lower for sensitive in self.sensitive_fields)
    
    def _mask_value(self, value: Any) -> str:
        """掩码敏感值"""
        if not value:
            return "[EMPTY]"
        value_str = str(value)
        if len(value_str) <= 4:
            return "[MASKED]"
        return value_str[:2] + "*" * (len(value_str) - 4) + value_str[-2:]
    
    def _create_log_entry(
        self, 
        level: LogLevel,
        message: str,
        category: LogCategory = LogCategory.SYSTEM,
        context: Dict[str, Any] = None,
        performance_data: Dict[str, float] = None
    ) -> Dict[str, Any]:
        """创建日志条目"""
        from flask import request, session, g
        
        log_entry = {
            'timestamp': time.time(),
            'datetime': datetime.now().isoformat(),
            'level': level.value,
            'category': category.value,
            'message': message,
            'logger_name': self.logger_name
        }
        
        # 添加请求上下文
        try:
            if request:
                log_entry['request'] = {
                    'method': request.method,
                    'path': request.path,
                    'remote_addr': request.remote_addr,
                    'user_agent': request.headers.get('User-Agent', '')[:200],
                    'request_id': getattr(g, 'request_id', None)
                }
        except RuntimeError:
            pass
        
        # 添加用户上下文
        try:
            if session:
                log_entry['user'] = {
                    'user_id': session.get('userid'),
                    'username': session.get('username'),
                    'role': session.get('role')
                }
        except RuntimeError:
            pass
        
        # 添加自定义上下文
        if context:
            log_entry['context'] = self.sanitize_data(context)
        
        # 添加性能数据
        if performance_data:
            log_entry['performance'] = performance_data
            # 记录到性能指标收集器
            for metric_name, value in performance_data.items():
                self.performance_metrics.record_metric(
                    f"{self.logger_name}.{metric_name}", 
                    value
                )
        
        return log_entry
    
    def debug(
        self, 
        message: str, 
        context: Dict[str, Any] = None,
        category: LogCategory = LogCategory.SYSTEM
    ):
        """调试日志"""
        log_entry = self._create_log_entry(LogLevel.DEBUG, message, category, context)
        self.logger.debug(json.dumps(log_entry, ensure_ascii=False))
    
    def info(
        self, 
        message: str, 
        context: Dict[str, Any] = None,
        category: LogCategory = LogCategory.SYSTEM
    ):
        """信息日志"""
        log_entry = self._create_log_entry(LogLevel.INFO, message, category, context)
        self.logger.info(json.dumps(log_entry, ensure_ascii=False))
    
    def warning(
        self, 
        message: str, 
        context: Dict[str, Any] = None,
        category: LogCategory = LogCategory.SYSTEM
    ):
        """警告日志"""
        log_entry = self._create_log_entry(LogLevel.WARNING, message, category, context)
        self.logger.warning(json.dumps(log_entry, ensure_ascii=False))
    
    def error(
        self, 
        message: str, 
        context: Dict[str, Any] = None,
        category: LogCategory = LogCategory.ERROR,
        exception: Exception = None
    ):
        """错误日志"""
        if exception:
            import traceback
            if context is None:
                context = {}
            context['exception'] = {
                'type': type(exception).__name__,
                'message': str(exception),
                'traceback': traceback.format_exc()
            }
        
        log_entry = self._create_log_entry(LogLevel.ERROR, message, category, context)
        self.logger.error(json.dumps(log_entry, ensure_ascii=False))
    
    def critical(
        self, 
        message: str, 
        context: Dict[str, Any] = None,
        category: LogCategory = LogCategory.ERROR
    ):
        """严重错误日志"""
        log_entry = self._create_log_entry(LogLevel.CRITICAL, message, category, context)
        self.logger.critical(json.dumps(log_entry, ensure_ascii=False))
    
    def access_log(
        self, 
        action: str, 
        resource: str = None,
        result: str = "success",
        context: Dict[str, Any] = None
    ):
        """访问日志"""
        access_context = {
            'action': action,
            'resource': resource,
            'result': result
        }
        if context:
            access_context.update(context)
        
        self.info(f"访问: {action}", access_context, LogCategory.ACCESS)
    
    def performance_log(
        self, 
        operation: str,
        duration: float,
        context: Dict[str, Any] = None
    ):
        """性能日志"""
        performance_data = {
            'duration': duration,
            'operation': operation
        }
        
        level = LogLevel.INFO
        if duration > 5.0:  # 超过5秒的操作记录为警告
            level = LogLevel.WARNING
        elif duration > 10.0:  # 超过10秒的操作记录为错误
            level = LogLevel.ERROR
        
        log_entry = self._create_log_entry(
            level, 
            f"性能监控: {operation}",
            LogCategory.PERFORMANCE,
            context,
            performance_data
        )
        
        if level == LogLevel.ERROR:
            self.logger.error(json.dumps(log_entry, ensure_ascii=False))
        elif level == LogLevel.WARNING:
            self.logger.warning(json.dumps(log_entry, ensure_ascii=False))
        else:
            self.logger.info(json.dumps(log_entry, ensure_ascii=False))
    
    def audit_log(
        self, 
        action: str, 
        target: str = None,
        old_value: Any = None,
        new_value: Any = None,
        context: Dict[str, Any] = None
    ):
        """审计日志"""
        audit_context = {
            'action': action,
            'target': target
        }
        
        if old_value is not None:
            audit_context['old_value'] = self.sanitize_data(old_value)
        if new_value is not None:
            audit_context['new_value'] = self.sanitize_data(new_value)
        if context:
            audit_context.update(context)
        
        self.info(f"审计: {action}", audit_context, LogCategory.AUDIT)
    
    def get_performance_stats(self, metric_name: str = None, time_window: int = 3600) -> Dict:
        """获取性能统计"""
        if metric_name:
            return self.performance_metrics.get_stats(
                f"{self.logger_name}.{metric_name}", 
                time_window
            )
        else:
            # 返回所有指标
            stats = {}
            for name in self.performance_metrics.metrics:
                if name.startswith(f"{self.logger_name}."):
                    metric_name = name[len(f"{self.logger_name}."):]
                    stats[metric_name] = self.performance_metrics.get_stats(name, time_window)
            return stats

def performance_monitor(operation_name: str = None):
    """性能监控装饰器"""
    def decorator(func):
        import functools
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            operation = operation_name or f"{func.__module__}.{func.__name__}"
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                # 记录性能日志
                logger = EnhancedLogger(func.__module__)
                logger.performance_log(operation, duration)
                
                return result
            except Exception as e:
                duration = time.time() - start_time
                
                # 记录错误和性能数据
                logger = EnhancedLogger(func.__module__)
                logger.performance_log(operation, duration, {'status': 'error'})
                logger.error(f"操作失败: {operation}", exception=e)
                
                raise e
        
        return wrapper
    return decorator

def audit_trail(action: str = None, target_field: str = None):
    """审计追踪装饰器"""
    def decorator(func):
        import functools
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            audit_action = action or f"{func.__module__}.{func.__name__}"
            
            # 尝试获取目标对象
            target = None
            if target_field and kwargs.get(target_field):
                target = kwargs[target_field]
            
            # 记录审计日志
            logger = EnhancedLogger(func.__module__)
            
            try:
                result = func(*args, **kwargs)
                logger.audit_log(audit_action, target, context={'status': 'success'})
                return result
            except Exception as e:
                logger.audit_log(audit_action, target, context={
                    'status': 'error',
                    'error': str(e)
                })
                raise e
        
        return wrapper
    return decorator

# 创建全局实例
def get_enhanced_logger(name: str) -> EnhancedLogger:
    """获取增强日志记录器实例"""
    return EnhancedLogger(name)