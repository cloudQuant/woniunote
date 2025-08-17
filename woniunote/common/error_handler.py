"""
统一错误处理模块
提供标准化的异常处理、日志记录和错误恢复机制
"""
import sys
import traceback
import functools
import time
from typing import Any, Dict, Optional, Union, Callable
from enum import Enum
from flask import request, session, g, current_app, jsonify
from werkzeug.exceptions import HTTPException

from .simple_logger import get_simple_logger

class ErrorLevel(Enum):
    """错误级别枚举"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ErrorCategory(Enum):
    """错误分类枚举"""
    VALIDATION = "validation"
    DATABASE = "database"
    NETWORK = "network"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    BUSINESS_LOGIC = "business_logic"
    SYSTEM = "system"
    EXTERNAL_SERVICE = "external_service"

class WoniuNoteException(Exception):
    """WoniuNote 基础异常类"""
    
    def __init__(
        self, 
        message: str, 
        error_code: str = None, 
        category: ErrorCategory = ErrorCategory.SYSTEM,
        level: ErrorLevel = ErrorLevel.MEDIUM,
        details: Dict[str, Any] = None,
        user_message: str = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self._generate_error_code()
        self.category = category
        self.level = level
        self.details = details or {}
        self.user_message = user_message or "系统出现异常，请稍后重试"
        self.timestamp = time.time()
    
    def _generate_error_code(self) -> str:
        """生成错误代码"""
        import uuid
        return f"ERR_{int(time.time())}_{str(uuid.uuid4())[:8]}"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'error_code': self.error_code,
            'message': self.message,
            'user_message': self.user_message,
            'category': self.category.value,
            'level': self.level.value,
            'details': self.details,
            'timestamp': self.timestamp
        }

class ValidationException(WoniuNoteException):
    """验证异常"""
    def __init__(self, message: str, field: str = None, **kwargs):
        super().__init__(
            message, 
            category=ErrorCategory.VALIDATION,
            level=ErrorLevel.LOW,
            **kwargs
        )
        if field:
            self.details['field'] = field

class DatabaseException(WoniuNoteException):
    """数据库异常"""
    def __init__(self, message: str, operation: str = None, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.DATABASE,
            level=ErrorLevel.HIGH,
            **kwargs
        )
        if operation:
            self.details['operation'] = operation

class NetworkException(WoniuNoteException):
    """网络异常"""
    def __init__(self, message: str, url: str = None, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.NETWORK,
            level=ErrorLevel.MEDIUM,
            **kwargs
        )
        if url:
            self.details['url'] = url

class AuthenticationException(WoniuNoteException):
    """认证异常"""
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.AUTHENTICATION,
            level=ErrorLevel.HIGH,
            user_message="请重新登录",
            **kwargs
        )

class AuthorizationException(WoniuNoteException):
    """授权异常"""
    def __init__(self, message: str, required_permission: str = None, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.AUTHORIZATION,
            level=ErrorLevel.MEDIUM,
            user_message="您没有权限执行此操作",
            **kwargs
        )
        if required_permission:
            self.details['required_permission'] = required_permission

class BusinessLogicException(WoniuNoteException):
    """业务逻辑异常"""
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.BUSINESS_LOGIC,
            level=ErrorLevel.LOW,
            **kwargs
        )

class ExternalServiceException(WoniuNoteException):
    """外部服务异常"""
    def __init__(self, message: str, service_name: str = None, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.EXTERNAL_SERVICE,
            level=ErrorLevel.MEDIUM,
            **kwargs
        )
        if service_name:
            self.details['service_name'] = service_name

class ErrorLogger:
    """错误日志记录器"""
    
    def __init__(self, logger_name: str = 'error_handler'):
        self.logger = get_simple_logger(logger_name)
        self.sensitive_fields = {
            'password', 'token', 'secret', 'key', 'authorization',
            'cookie', 'session', 'csrf_token', 'api_key'
        }
    
    def sanitize_data(self, data: Any) -> Any:
        """脱敏处理敏感数据"""
        if isinstance(data, dict):
            sanitized = {}
            for key, value in data.items():
                if self._is_sensitive_field(key):
                    sanitized[key] = self._mask_sensitive_value(value)
                elif isinstance(value, (dict, list)):
                    sanitized[key] = self.sanitize_data(value)
                else:
                    sanitized[key] = value
            return sanitized
        elif isinstance(data, list):
            return [self.sanitize_data(item) for item in data]
        elif isinstance(data, str) and len(data) > 50:
            # 长字符串截断
            return data[:50] + "..."
        else:
            return data
    
    def _is_sensitive_field(self, field_name: str) -> bool:
        """检查是否为敏感字段"""
        field_lower = field_name.lower()
        return any(sensitive in field_lower for sensitive in self.sensitive_fields)
    
    def _mask_sensitive_value(self, value: Any) -> str:
        """掩码敏感值"""
        if not value:
            return "[EMPTY]"
        value_str = str(value)
        if len(value_str) <= 4:
            return "[MASKED]"
        return value_str[:2] + "*" * (len(value_str) - 4) + value_str[-2:]
    
    def log_error(
        self, 
        error: Exception, 
        context: Dict[str, Any] = None,
        user_id: str = None,
        request_id: str = None
    ):
        """记录错误日志"""
        context = context or {}
        
        # 获取请求上下文
        request_context = self._get_request_context()
        
        # 安全获取Flask上下文信息
        flask_request_id = None
        flask_user_id = None
        
        try:
            from flask import has_request_context, has_app_context
            if has_app_context() and has_request_context():
                flask_request_id = getattr(g, 'request_id', None)
                flask_user_id = session.get('userid')
        except (RuntimeError, ImportError):
            pass
        
        # 构建日志数据
        log_data = {
            'error_type': type(error).__name__,
            'error_message': str(error),
            'request_id': request_id or flask_request_id,
            'user_id': user_id or flask_user_id,
            'request_context': self.sanitize_data(request_context),
            'additional_context': self.sanitize_data(context),
            'timestamp': time.time()
        }
        
        # 如果是自定义异常，添加更多信息
        if isinstance(error, WoniuNoteException):
            log_data.update({
                'error_code': error.error_code,
                'category': error.category.value,
                'level': error.level.value,
                'details': self.sanitize_data(error.details)
            })
            
            # 根据错误级别选择日志级别
            if error.level == ErrorLevel.CRITICAL:
                self.logger.error("严重错误", log_data)
            elif error.level == ErrorLevel.HIGH:
                self.logger.error("高级错误", log_data)
            elif error.level == ErrorLevel.MEDIUM:
                self.logger.warning("中级错误", log_data)
            else:
                self.logger.info("低级错误", log_data)
        else:
            # 未知异常，记录完整堆栈信息
            log_data['traceback'] = traceback.format_exc()
            self.logger.error("未处理异常", log_data)
    
    def _get_request_context(self) -> Dict[str, Any]:
        """获取请求上下文信息"""
        try:
            # 检查是否在Flask应用上下文中
            from flask import has_request_context
            if has_request_context() and request:
                return {
                    'method': request.method,
                    'path': request.path,
                    'remote_addr': request.remote_addr,
                    'user_agent': request.headers.get('User-Agent', ''),
                    'content_length': request.content_length,
                    'args': dict(request.args),
                    'headers': dict(request.headers)
                }
        except (RuntimeError, ImportError):
            # 请求上下文不可用或不在Flask环境中
            pass
        return {}

class ErrorRecoveryManager:
    """错误恢复管理器"""
    
    def __init__(self):
        self.retry_strategies = {}
        self.fallback_strategies = {}
    
    def register_retry_strategy(
        self, 
        exception_type: type, 
        max_retries: int = 3, 
        delay: float = 1.0,
        backoff_factor: float = 2.0
    ):
        """注册重试策略"""
        self.retry_strategies[exception_type] = {
            'max_retries': max_retries,
            'delay': delay,
            'backoff_factor': backoff_factor
        }
    
    def register_fallback_strategy(
        self, 
        exception_type: type, 
        fallback_func: Callable
    ):
        """注册降级策略"""
        self.fallback_strategies[exception_type] = fallback_func
    
    def execute_with_recovery(
        self, 
        func: Callable, 
        *args, 
        **kwargs
    ) -> Any:
        """执行函数并处理错误恢复"""
        last_exception = None
        
        for exception_type, strategy in self.retry_strategies.items():
            try:
                return self._execute_with_retry(
                    func, 
                    exception_type, 
                    strategy, 
                    *args, 
                    **kwargs
                )
            except exception_type as e:
                last_exception = e
                continue
        
        # 如果重试失败，尝试降级策略
        if last_exception:
            exception_type = type(last_exception)
            if exception_type in self.fallback_strategies:
                fallback_func = self.fallback_strategies[exception_type]
                return fallback_func(*args, **kwargs)
        
        # 如果都失败了，抛出原始异常
        if last_exception:
            raise last_exception
        else:
            return func(*args, **kwargs)
    
    def _execute_with_retry(
        self, 
        func: Callable, 
        exception_type: type, 
        strategy: Dict[str, Any], 
        *args, 
        **kwargs
    ) -> Any:
        """带重试的执行函数"""
        max_retries = strategy['max_retries']
        delay = strategy['delay']
        backoff_factor = strategy['backoff_factor']
        
        for attempt in range(max_retries + 1):
            try:
                return func(*args, **kwargs)
            except exception_type as e:
                if attempt == max_retries:
                    raise e
                
                # 等待后重试
                time.sleep(delay * (backoff_factor ** attempt))

# 全局实例
error_logger = ErrorLogger()
recovery_manager = ErrorRecoveryManager()

def handle_error(
    logger_name: str = None,
    re_raise: bool = True,
    return_value: Any = None,
    log_context: Dict[str, Any] = None
):
    """错误处理装饰器"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # 记录错误
                logger = ErrorLogger(logger_name or func.__module__)
                logger.log_error(e, context=log_context)
                
                # 决定是否重新抛出异常
                if re_raise:
                    raise e
                else:
                    return return_value
        
        return wrapper
    return decorator

def database_error_handler(
    operation: str = None,
    rollback: bool = True
):
    """数据库错误处理装饰器"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # 数据库回滚
                if rollback:
                    try:
                        from .database import db
                        db.session.rollback()
                    except Exception:
                        pass
                
                # 转换为数据库异常
                if not isinstance(e, DatabaseException):
                    db_error = DatabaseException(
                        message=f"数据库操作失败: {str(e)}",
                        operation=operation or func.__name__,
                        details={'original_error': str(e)}
                    )
                    error_logger.log_error(db_error)
                    raise db_error
                else:
                    error_logger.log_error(e)
                    raise e
        
        return wrapper
    return decorator

def api_error_handler(
    service_name: str = None,
    timeout: float = 30.0
):
    """API错误处理装饰器"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # 转换为外部服务异常
                if not isinstance(e, ExternalServiceException):
                    api_error = ExternalServiceException(
                        message=f"API调用失败: {str(e)}",
                        service_name=service_name or func.__name__,
                        details={'original_error': str(e)}
                    )
                    error_logger.log_error(api_error)
                    raise api_error
                else:
                    error_logger.log_error(e)
                    raise e
        
        return wrapper
    return decorator

def create_error_response(
    error: Exception, 
    status_code: int = 500
) -> tuple:
    """创建标准化错误响应"""
    if isinstance(error, WoniuNoteException):
        return jsonify(error.to_dict()), status_code
    elif isinstance(error, HTTPException):
        return jsonify({
            'error_code': f'HTTP_{error.code}',
            'message': error.description,
            'user_message': error.description
        }), error.code
    else:
        return jsonify({
            'error_code': 'UNKNOWN_ERROR',
            'message': str(error),
            'user_message': '系统出现未知错误'
        }), status_code

# 注册默认的恢复策略
recovery_manager.register_retry_strategy(DatabaseException, max_retries=3, delay=0.5)
recovery_manager.register_retry_strategy(NetworkException, max_retries=2, delay=1.0)