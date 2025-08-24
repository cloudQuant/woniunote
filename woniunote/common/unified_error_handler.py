#!/usr/bin/env python3
"""
统一的错误处理模块
整合所有错误处理、异常管理和错误恢复功能
"""

import sys
import traceback
import logging
from typing import Dict, Any, Optional, Callable, Type, Union
from functools import wraps
from datetime import datetime

from .unified_logging import get_logger

logger = get_logger('unified_error_handler')

# ==================== 统一异常基类 ====================

class WoniuNoteBaseException(Exception):
    """WoniuNote异常基类"""
    
    def __init__(self, message: str, error_code: str = None, details: Dict[str, Any] = None, 
                 context: Dict[str, Any] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        self.context = context or {}
        self.timestamp = datetime.now()
        self.traceback = traceback.format_exc()
        
        # 记录异常
        self._log_exception()
    
    def _log_exception(self):
        """记录异常信息"""
        logger.error(f"异常发生: {self.error_code}", {
            'message': self.message,
            'error_code': self.error_code,
            'details': self.details,
            'context': self.context,
            'timestamp': self.timestamp.isoformat(),
            'traceback': self.traceback
        })
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'error_code': self.error_code,
            'message': self.message,
            'details': self.details,
            'context': self.context,
            'timestamp': self.timestamp.isoformat()
        }
    
    def __str__(self):
        return f"{self.error_code}: {self.message}"

# ==================== 具体异常类型 ====================

class ValidationException(WoniuNoteBaseException):
    """数据验证异常"""
    
    def __init__(self, message: str, field: str = None, value: Any = None, **kwargs):
        details = {'field': field, 'value': value}
        super().__init__(message, "VALIDATION_ERROR", details, **kwargs)

class DatabaseException(WoniuNoteBaseException):
    """数据库操作异常"""
    
    def __init__(self, message: str, operation: str = None, table: str = None, **kwargs):
        details = {'operation': operation, 'table': table}
        super().__init__(message, "DATABASE_ERROR", details, **kwargs)

class AuthenticationException(WoniuNoteBaseException):
    """认证异常"""
    
    def __init__(self, message: str, user_id: str = None, username: str = None, **kwargs):
        details = {'user_id': user_id, 'username': username}
        super().__init__(message, "AUTHENTICATION_ERROR", details, **kwargs)

class AuthorizationException(WoniuNoteBaseException):
    """授权异常"""
    
    def __init__(self, message: str, user_id: str = None, resource: str = None, 
                 required_permission: str = None, **kwargs):
        details = {
            'user_id': user_id, 
            'resource': resource, 
            'required_permission': required_permission
        }
        super().__init__(message, "AUTHORIZATION_ERROR", details, **kwargs)

class BusinessLogicException(WoniuNoteBaseException):
    """业务逻辑异常"""
    
    def __init__(self, message: str, business_rule: str = None, affected_data: Any = None, **kwargs):
        details = {'business_rule': business_rule, 'affected_data': affected_data}
        super().__init__(message, "BUSINESS_LOGIC_ERROR", details, **kwargs)

class ExternalServiceException(WoniuNoteBaseException):
    """外部服务异常"""
    
    def __init__(self, message: str, service_name: str = None, service_url: str = None, 
                 response_code: int = None, **kwargs):
        details = {
            'service_name': service_name, 
            'service_url': service_url, 
            'response_code': response_code
        }
        super().__init__(message, "EXTERNAL_SERVICE_ERROR", details, **kwargs)

class NetworkException(WoniuNoteBaseException):
    """网络异常"""
    
    def __init__(self, message: str, endpoint: str = None, connection_type: str = None, **kwargs):
        details = {'endpoint': endpoint, 'connection_type': connection_type}
        super().__init__(message, "NETWORK_ERROR", details, **kwargs)

class CacheException(WoniuNoteBaseException):
    """缓存异常"""
    
    def __init__(self, message: str, cache_key: str = None, cache_type: str = None, **kwargs):
        details = {'cache_key': cache_key, 'cache_type': cache_type}
        super().__init__(message, "CACHE_ERROR", details, **kwargs)

class ConfigurationException(WoniuNoteBaseException):
    """配置异常"""
    
    def __init__(self, message: str, config_key: str = None, config_file: str = None, **kwargs):
        details = {'config_key': config_key, 'config_file': config_file}
        super().__init__(message, "CONFIGURATION_ERROR", details, **kwargs)

class ResourceNotFoundException(WoniuNoteBaseException):
    """资源未找到异常"""
    
    def __init__(self, message: str, resource_type: str = None, resource_id: str = None, **kwargs):
        details = {'resource_type': resource_type, 'resource_id': resource_id}
        super().__init__(message, "RESOURCE_NOT_FOUND", details, **kwargs)

# ==================== 统一错误处理器 ====================

class UnifiedErrorHandler:
    """统一的错误处理器"""
    
    def __init__(self):
        self.error_categories = {
            'validation': ValidationException,
            'database': DatabaseException,
            'authentication': AuthenticationException,
            'authorization': AuthorizationException,
            'business_logic': BusinessLogicException,
            'external_service': ExternalServiceException,
            'network': NetworkException,
            'cache': CacheException,
            'configuration': ConfigurationException,
            'resource_not_found': ResourceNotFoundException
        }
        
        self.recovery_handlers: Dict[Type[WoniuNoteBaseException], Callable] = {}
        self.error_stats = {
            'total_errors': 0,
            'errors_by_type': {},
            'errors_by_category': {},
            'recovery_attempts': 0,
            'recovery_successes': 0
        }
        
        self.logger = get_logger('error_handler')
    
    def handle_exception(self, exception: Exception, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        统一异常处理
        
        Args:
            exception: 异常对象
            context: 上下文信息
            
        Returns:
            dict: 错误响应信息
        """
        try:
            # 更新错误统计
            self._update_error_stats(exception)
            
            # 转换为WoniuNote异常
            woniu_exception = self._convert_to_woniu_exception(exception, context)
            
            # 尝试恢复
            recovery_result = self._attempt_recovery(woniu_exception)
            
            # 记录错误
            self._log_error(woniu_exception, context)
            
            # 返回错误响应
            return self._format_error_response(woniu_exception, recovery_result)
            
        except Exception as e:
            # 如果错误处理本身出错，记录并返回通用错误
            self.logger.error(f"错误处理失败: {e}")
            return {
                'error_code': 'ERROR_HANDLER_FAILURE',
                'message': '内部错误处理失败',
                'timestamp': datetime.now().isoformat()
            }
    
    def register_recovery_handler(self, exception_type: Type[WoniuNoteBaseException], 
                                handler: Callable) -> None:
        """
        注册恢复处理器
        
        Args:
            exception_type: 异常类型
            handler: 恢复处理函数
        """
        self.recovery_handlers[exception_type] = handler
        self.logger.info(f"注册恢复处理器: {exception_type.__name__}")
    
    def register_error_category(self, category: str, exception_class: Type[WoniuNoteBaseException]) -> None:
        """
        注册错误类别
        
        Args:
            category: 错误类别
            exception_class: 异常类
        """
        self.error_categories[category] = exception_class
        self.logger.info(f"注册错误类别: {category} -> {exception_class.__name__}")
    
    def get_error_stats(self) -> Dict[str, Any]:
        """获取错误统计信息"""
        return self.error_stats.copy()
    
    def reset_error_stats(self) -> None:
        """重置错误统计"""
        self.error_stats = {
            'total_errors': 0,
            'errors_by_type': {},
            'errors_by_category': {},
            'recovery_attempts': 0,
            'recovery_successes': 0
        }
        self.logger.info("错误统计已重置")
    
    # ==================== 私有方法 ====================
    
    def _convert_to_woniu_exception(self, exception: Exception, 
                                   context: Dict[str, Any] = None) -> WoniuNoteBaseException:
        """转换为WoniuNote异常"""
        if isinstance(exception, WoniuNoteBaseException):
            return exception
        
        # 根据异常类型创建相应的WoniuNote异常
        if isinstance(exception, ValueError):
            return ValidationException(str(exception), context=context)
        elif isinstance(exception, KeyError):
            return ValidationException(f"缺少必需的键: {exception}", context=context)
        elif isinstance(exception, TypeError):
            return ValidationException(f"类型错误: {exception}", context=context)
        elif isinstance(exception, FileNotFoundError):
            return ResourceNotFoundException(f"文件未找到: {exception}", context=context)
        elif isinstance(exception, PermissionError):
            return AuthorizationException(f"权限不足: {exception}", context=context)
        elif isinstance(exception, ConnectionError):
            return NetworkException(f"连接错误: {exception}", context=context)
        elif isinstance(exception, TimeoutError):
            return NetworkException(f"超时错误: {exception}", context=context)
        else:
            # 通用异常
            return WoniuNoteBaseException(
                str(exception),
                error_code="UNKNOWN_ERROR",
                details={'original_exception': type(exception).__name__},
                context=context
            )
    
    def _attempt_recovery(self, exception: WoniuNoteBaseException) -> Dict[str, Any]:
        """尝试错误恢复"""
        self.error_stats['recovery_attempts'] += 1
        
        # 查找恢复处理器
        for exception_type, handler in self.recovery_handlers.items():
            if isinstance(exception, exception_type):
                try:
                    result = handler(exception)
                    if result and result.get('success'):
                        self.error_stats['recovery_successes'] += 1
                        return {
                            'recovered': True,
                            'recovery_method': handler.__name__,
                            'recovery_result': result
                        }
                except Exception as e:
                    self.logger.error(f"恢复处理器执行失败: {e}")
        
        return {'recovered': False}
    
    def _update_error_stats(self, exception: Exception) -> None:
        """更新错误统计"""
        self.error_stats['total_errors'] += 1
        
        # 按类型统计
        exception_type = type(exception).__name__
        self.error_stats['errors_by_type'][exception_type] = \
            self.error_stats['errors_by_type'].get(exception_type, 0) + 1
        
        # 按类别统计
        if isinstance(exception, WoniuNoteBaseException):
            category = exception.error_code.split('_')[0].lower()
            self.error_stats['errors_by_category'][category] = \
                self.error_stats['errors_by_category'].get(category, 0) + 1
    
    def _log_error(self, exception: WoniuNoteBaseException, context: Dict[str, Any] = None) -> None:
        """记录错误信息"""
        log_data = {
            'error_code': exception.error_code,
            'message': exception.message,
            'details': exception.details,
            'context': context or {},
            'timestamp': exception.timestamp.isoformat()
        }
        
        if exception.error_code in ['AUTHENTICATION_ERROR', 'AUTHORIZATION_ERROR']:
            self.logger.warning("安全相关错误", log_data)
        elif exception.error_code in ['DATABASE_ERROR', 'NETWORK_ERROR']:
            self.logger.error("系统错误", log_data)
        else:
            self.logger.error("应用错误", log_data)
    
    def _format_error_response(self, exception: WoniuNoteBaseException, 
                              recovery_result: Dict[str, Any]) -> Dict[str, Any]:
        """格式化错误响应"""
        response = exception.to_dict()
        response['recovery'] = recovery_result
        
        # 在生产环境中隐藏敏感信息
        if self._is_production_environment():
            response.pop('traceback', None)
            response.pop('context', None)
        
        return response
    
    def _is_production_environment(self) -> bool:
        """检查是否为生产环境"""
        # 这里可以根据实际的环境变量或配置来判断
        return False

# ==================== 装饰器 ====================

def handle_errors(error_handler: UnifiedErrorHandler = None):
    """
    错误处理装饰器
    
    Args:
        error_handler: 错误处理器实例，如果为None则使用全局实例
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # 获取错误处理器
                handler = error_handler or get_error_handler()
                
                # 处理错误
                context = {
                    'function': func.__name__,
                    'module': func.__module__,
                    'args': str(args),
                    'kwargs': str(kwargs)
                }
                
                error_response = handler.handle_exception(e, context)
                
                # 根据函数类型返回不同的结果
                if func.__name__.startswith('get_') or func.__name__.startswith('is_'):
                    # 查询类函数返回None
                    return None
                else:
                    # 操作类函数抛出异常
                    raise e
        
        return wrapper
    return decorator

def retry_on_error(max_retries: int = 3, delay: float = 1.0, 
                   exceptions: tuple = (Exception,)):
    """
    错误重试装饰器
    
    Args:
        max_retries: 最大重试次数
        delay: 重试延迟（秒）
        exceptions: 需要重试的异常类型
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt < max_retries:
                        logger.warning(f"函数执行失败，准备重试: {func.__name__}", {
                            'attempt': attempt + 1,
                            'max_retries': max_retries,
                            'error': str(e)
                        })
                        
                        import time
                        time.sleep(delay * (2 ** attempt))  # 指数退避
                    else:
                        logger.error(f"函数执行失败，已达到最大重试次数: {func.__name__}", {
                            'max_retries': max_retries,
                            'final_error': str(e)
                        })
                        raise e
            
            # 这里不会执行到，但为了类型检查
            raise last_exception
        
        return wrapper
    return decorator

# ==================== 全局实例和工厂函数 ====================

# 全局错误处理器实例
_global_error_handler = None

def init_unified_error_handler() -> UnifiedErrorHandler:
    """初始化全局错误处理器"""
    global _global_error_handler
    _global_error_handler = UnifiedErrorHandler()
    
    # 注册默认的恢复处理器
    _register_default_recovery_handlers(_global_error_handler)
    
    return _global_error_handler

def get_error_handler() -> UnifiedErrorHandler:
    """获取全局错误处理器"""
    if _global_error_handler is None:
        raise RuntimeError("错误处理器未初始化，请先调用 init_unified_error_handler")
    return _global_error_handler

def _register_default_recovery_handlers(handler: UnifiedErrorHandler):
    """注册默认的恢复处理器"""
    
    @handler.register_recovery_handler(DatabaseException)
    def retry_database_operation(exception: DatabaseException):
        """重试数据库操作"""
        # 这里可以实现数据库重连逻辑
        return {'success': False, 'message': '数据库重试功能待实现'}
    
    @handler.register_recovery_handler(NetworkException)
    def retry_network_operation(exception: NetworkException):
        """重试网络操作"""
        # 这里可以实现网络重试逻辑
        return {'success': False, 'message': '网络重试功能待实现'}
    
    @handler.register_recovery_handler(CacheException)
    def fallback_to_database(exception: CacheException):
        """缓存失败时回退到数据库"""
        # 这里可以实现缓存回退逻辑
        return {'success': False, 'message': '缓存回退功能待实现'}

# ==================== 便捷函数 ====================

def raise_validation_error(message: str, field: str = None, value: Any = None, **kwargs):
    """抛出验证异常"""
    raise ValidationException(message, field, value, **kwargs)

def raise_database_error(message: str, operation: str = None, table: str = None, **kwargs):
    """抛出数据库异常"""
    raise DatabaseException(message, operation, table, **kwargs)

def raise_auth_error(message: str, user_id: str = None, username: str = None, **kwargs):
    """抛出认证异常"""
    raise AuthenticationException(message, user_id, username, **kwargs)

def raise_permission_error(message: str, user_id: str = None, resource: str = None, 
                          required_permission: str = None, **kwargs):
    """抛出权限异常"""
    raise AuthorizationException(message, user_id, resource, required_permission, **kwargs)

def raise_business_error(message: str, business_rule: str = None, affected_data: Any = None, **kwargs):
    """抛出业务逻辑异常"""
    raise BusinessLogicException(message, business_rule, affected_data, **kwargs)

def raise_resource_not_found(message: str, resource_type: str = None, resource_id: str = None, **kwargs):
    """抛出资源未找到异常"""
    raise ResourceNotFoundException(message, resource_type, resource_id, **kwargs)

# ==================== 向后兼容 ====================

# 为了向后兼容，保留旧的异常类名
WoniuNoteException = WoniuNoteBaseException
WoniuNoteError = WoniuNoteBaseException

# 旧的异常类（已废弃，建议使用新的）
class ValidationError(ValidationException):
    """已废弃，请使用 ValidationException"""
    pass

class DatabaseError(DatabaseException):
    """已废弃，请使用 DatabaseException"""
    pass

class AuthError(AuthenticationException):
    """已废弃，请使用 AuthenticationException"""
    pass

class PermissionError(AuthorizationException):
    """已废弃，请使用 AuthorizationException"""
    pass
