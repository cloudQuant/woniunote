"""
增强的错误处理系统
提供统一的错误处理、日志记录和错误恢复机制
"""
import os
import sys
import traceback
import logging
import time
from typing import Any, Dict, Optional, Callable, Type
from functools import wraps
from flask import Flask, request, jsonify, render_template, current_app
from werkzeug.exceptions import HTTPException
from sqlalchemy.exc import SQLAlchemyError

from .simple_logger import get_simple_logger
from .trace_id_manager import TraceIdManager

class ErrorSeverity:
    """错误严重级别"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class WoniuNoteError(Exception):
    """WoniuNote自定义异常基类"""
    
    def __init__(self, message: str, error_code: str = None, 
                 severity: str = ErrorSeverity.MEDIUM, 
                 details: Dict[str, Any] = None,
                 recoverable: bool = True):
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.severity = severity
        self.details = details or {}
        self.recoverable = recoverable
        self.timestamp = time.time()
        self.trace_id = TraceIdManager.generate_simple_trace_id()
        
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'error_code': self.error_code,
            'message': self.message,
            'severity': self.severity,
            'details': self.details,
            'recoverable': self.recoverable,
            'timestamp': self.timestamp,
            'trace_id': self.trace_id
        }

class DatabaseError(WoniuNoteError):
    """数据库错误"""
    pass

class ValidationError(WoniuNoteError):
    """验证错误"""
    def __init__(self, message: str, field: str = None, **kwargs):
        super().__init__(message, severity=ErrorSeverity.LOW, **kwargs)
        if field:
            self.details['field'] = field

class AuthenticationError(WoniuNoteError):
    """认证错误"""
    def __init__(self, message: str = "认证失败", **kwargs):
        super().__init__(message, severity=ErrorSeverity.HIGH, recoverable=False, **kwargs)

class AuthorizationError(WoniuNoteError):
    """授权错误"""
    def __init__(self, message: str = "权限不足", **kwargs):
        super().__init__(message, severity=ErrorSeverity.HIGH, recoverable=False, **kwargs)

class BusinessLogicError(WoniuNoteError):
    """业务逻辑错误"""
    pass

class ExternalServiceError(WoniuNoteError):
    """外部服务错误"""
    def __init__(self, message: str, service_name: str = None, **kwargs):
        super().__init__(message, severity=ErrorSeverity.MEDIUM, **kwargs)
        if service_name:
            self.details['service_name'] = service_name

class EnhancedErrorHandler:
    """增强的错误处理器"""
    
    def __init__(self, app: Flask = None):
        self.app = app
        self.logger = get_simple_logger('error_handler')
        self.error_stats = {}
        self.recovery_handlers = {}
        
        if app:
            self.init_app(app)
    
    def init_app(self, app: Flask):
        """初始化Flask应用的错误处理"""
        self.app = app
        
        # 注册错误处理器
        app.errorhandler(WoniuNoteError)(self.handle_woniunote_error)
        app.errorhandler(SQLAlchemyError)(self.handle_database_error)
        app.errorhandler(HTTPException)(self.handle_http_error)
        app.errorhandler(Exception)(self.handle_generic_error)
        
        # 注册请求前后钩子
        app.before_request(self.before_request)
        app.after_request(self.after_request)
        
        self.logger.info("错误处理器初始化完成")
    
    def before_request(self):
        """请求前处理"""
        # 记录请求开始时间
        request.start_time = time.time()
        
        # 生成请求跟踪ID
        if not hasattr(request, 'trace_id'):
            request.trace_id = TraceIdManager.generate_simple_trace_id()
    
    def after_request(self, response):
        """请求后处理"""
        try:
            # 计算请求处理时间
            if hasattr(request, 'start_time'):
                duration = time.time() - request.start_time
                
                # 记录慢请求
                if duration > 2.0:  # 超过2秒的请求
                    self.logger.warning("慢请求检测", {
                        'trace_id': getattr(request, 'trace_id', ''),
                        'endpoint': request.endpoint,
                        'method': request.method,
                        'duration_s': round(duration, 3),
                        'status_code': response.status_code
                    })
            
            return response
            
        except Exception as e:
            self.logger.error(f"请求后处理异常: {e}")
            return response
    
    def handle_woniunote_error(self, error: WoniuNoteError):
        """处理WoniuNote自定义错误"""
        self._log_error(error)
        self._update_error_stats(error.error_code)
        
        # 尝试错误恢复
        if error.recoverable and error.error_code in self.recovery_handlers:
            try:
                recovery_result = self.recovery_handlers[error.error_code](error)
                if recovery_result:
                    self.logger.info(f"错误恢复成功: {error.error_code}")
                    return recovery_result
            except Exception as recovery_error:
                self.logger.error(f"错误恢复失败: {recovery_error}")
        
        # 返回错误响应
        return self._create_error_response(error)
    
    def handle_database_error(self, error: SQLAlchemyError):
        """处理数据库错误"""
        wrapped_error = DatabaseError(
            message="数据库操作失败",
            details={'original_error': str(error)},
            severity=ErrorSeverity.HIGH
        )
        
        return self.handle_woniunote_error(wrapped_error)
    
    def handle_http_error(self, error: HTTPException):
        """处理HTTP错误"""
        wrapped_error = WoniuNoteError(
            message=error.description or f"HTTP {error.code} 错误",
            error_code=f"HTTP_{error.code}",
            severity=ErrorSeverity.MEDIUM if error.code < 500 else ErrorSeverity.HIGH,
            details={'status_code': error.code}
        )
        
        return self.handle_woniunote_error(wrapped_error)
    
    def handle_generic_error(self, error: Exception):
        """处理通用异常"""
        wrapped_error = WoniuNoteError(
            message=f"系统异常: {str(error)}",
            error_code="SYSTEM_ERROR",
            severity=ErrorSeverity.CRITICAL,
            details={
                'error_type': type(error).__name__,
                'traceback': traceback.format_exc()
            }
        )
        
        return self.handle_woniunote_error(wrapped_error)
    
    def _log_error(self, error: WoniuNoteError):
        """记录错误日志"""
        log_data = {
            'trace_id': error.trace_id,
            'error_code': error.error_code,
            'severity': error.severity,
            'message': error.message,
            'details': error.details,
            'endpoint': getattr(request, 'endpoint', ''),
            'method': getattr(request, 'method', ''),
            'remote_addr': getattr(request, 'remote_addr', ''),
            'user_agent': str(getattr(request, 'user_agent', '')) if hasattr(request, 'user_agent') else ''
        }
        
        # 根据严重级别选择日志级别
        if error.severity == ErrorSeverity.CRITICAL:
            self.logger.critical("严重错误", log_data)
        elif error.severity == ErrorSeverity.HIGH:
            self.logger.error("高级错误", log_data)
        elif error.severity == ErrorSeverity.MEDIUM:
            self.logger.warning("中级错误", log_data)
        else:
            self.logger.info("低级错误", log_data)
    
    def _update_error_stats(self, error_code: str):
        """更新错误统计"""
        if error_code not in self.error_stats:
            self.error_stats[error_code] = {
                'count': 0,
                'first_seen': time.time(),
                'last_seen': time.time()
            }
        
        self.error_stats[error_code]['count'] += 1
        self.error_stats[error_code]['last_seen'] = time.time()
    
    def _create_error_response(self, error: WoniuNoteError):
        """创建错误响应"""
        # 判断是否为AJAX请求
        if request.is_json or 'application/json' in request.headers.get('Accept', ''):
            response_data = {
                'success': False,
                'error': {
                    'code': error.error_code,
                    'message': error.message,
                    'trace_id': error.trace_id
                }
            }
            
            # 开发环境添加详细信息
            if current_app.debug:
                response_data['error']['details'] = error.details
            
            status_code = 500 if error.severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL] else 400
            return jsonify(response_data), status_code
        
        else:
            # 返回HTML错误页面
            try:
                return render_template('error.html', 
                                     error=error,
                                     trace_id=error.trace_id,
                                     error_message=error.message), 500
            except:
                # 如果模板不存在，返回简单的HTML
                return f"""
                <html>
                <head><title>错误 - {error.error_code}</title></head>
                <body>
                    <h1>系统错误</h1>
                    <p>{error.message}</p>
                    <p>错误追踪ID: {error.trace_id}</p>
                </body>
                </html>
                """, 500
    
    def register_recovery_handler(self, error_code: str, handler: Callable):
        """注册错误恢复处理器"""
        self.recovery_handlers[error_code] = handler
        self.logger.info(f"注册错误恢复处理器: {error_code}")
    
    def get_error_stats(self) -> Dict[str, Any]:
        """获取错误统计信息"""
        return {
            'total_errors': len(self.error_stats),
            'error_breakdown': self.error_stats.copy(),
            'top_errors': sorted(
                self.error_stats.items(),
                key=lambda x: x[1]['count'],
                reverse=True
            )[:10]
        }

# 错误处理装饰器
def handle_errors(error_types: tuple = (Exception,), 
                 default_message: str = "操作失败",
                 severity: str = ErrorSeverity.MEDIUM):
    """错误处理装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except WoniuNoteError:
                # 重新抛出WoniuNote错误
                raise
            except error_types as e:
                # 包装为WoniuNote错误
                raise WoniuNoteError(
                    message=f"{default_message}: {str(e)}",
                    error_code=f"{func.__name__}_ERROR",
                    severity=severity,
                    details={'original_error': str(e), 'function': func.__name__}
                )
        return wrapper
    return decorator

def safe_execute(func: Callable, *args, 
                default_return=None, 
                error_message: str = "操作失败",
                **kwargs) -> Any:
    """安全执行函数，捕获异常并返回默认值"""
    try:
        return func(*args, **kwargs)
    except Exception as e:
        logger = get_simple_logger('safe_execute')
        logger.error(f"{error_message}: {e}")
        return default_return

# 全局错误处理器实例
error_handler = EnhancedErrorHandler()

def init_error_handling(app: Flask):
    """初始化错误处理"""
    error_handler.init_app(app)
    return error_handler