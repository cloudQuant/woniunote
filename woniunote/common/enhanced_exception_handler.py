"""
增强异常处理模块
提供具体的异常类型处理和恢复机制
"""
import traceback
import time
from typing import Optional, Dict, Any, Callable
from functools import wraps
from sqlalchemy.exc import (
    SQLAlchemyError, IntegrityError, OperationalError, 
    TimeoutError as SQLTimeoutError, DisconnectionError
)
from redis.exceptions import (
    RedisError, ConnectionError as RedisConnectionError,
    TimeoutError as RedisTimeoutError
)
from woniunote.common.simple_logger import get_simple_logger

logger = get_simple_logger('enhanced_exception_handler')

class DatabaseException(Exception):
    """数据库相关异常"""
    def __init__(self, message: str, original_error: Exception = None):
        self.message = message
        self.original_error = original_error
        super().__init__(self.message)

class CacheException(Exception):
    """缓存相关异常"""
    def __init__(self, message: str, original_error: Exception = None):
        self.message = message
        self.original_error = original_error
        super().__init__(self.message)

class ValidationException(Exception):
    """验证异常"""
    def __init__(self, message: str, field: str = None, value: Any = None):
        self.message = message
        self.field = field
        self.value = value
        super().__init__(self.message)

class BusinessLogicException(Exception):
    """业务逻辑异常"""
    def __init__(self, message: str, code: str = None):
        self.message = message
        self.code = code
        super().__init__(self.message)

class EnhancedExceptionHandler:
    """增强异常处理器"""
    
    def __init__(self):
        self.retry_config = {
            'database': {'max_retries': 3, 'delay': 1.0},
            'cache': {'max_retries': 2, 'delay': 0.5},
            'network': {'max_retries': 3, 'delay': 2.0}
        }
        
        # 异常处理器映射
        self.exception_handlers = {
            IntegrityError: self._handle_integrity_error,
            OperationalError: self._handle_operational_error,
            SQLTimeoutError: self._handle_sql_timeout_error,
            DisconnectionError: self._handle_disconnection_error,
            RedisConnectionError: self._handle_redis_connection_error,
            RedisTimeoutError: self._handle_redis_timeout_error,
            ValidationException: self._handle_validation_error,
            BusinessLogicException: self._handle_business_logic_error
        }
    
    def handle_exception(self, exception: Exception, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        处理异常并返回结果
        
        Args:
            exception: 捕获的异常
            context: 异常上下文信息
            
        Returns:
            Dict: 处理结果
        """
        context = context or {}
        exception_type = type(exception)
        
        # 记录异常基本信息
        logger.error("异常处理开始", {
            'exception_type': exception_type.__name__,
            'exception_message': str(exception),
            'context': context,
            'traceback': traceback.format_exc()
        })
        
        # 查找对应的处理器
        handler = self.exception_handlers.get(exception_type)
        if not handler:
            # 查找父类处理器
            for exc_type, exc_handler in self.exception_handlers.items():
                if isinstance(exception, exc_type):
                    handler = exc_handler
                    break
        
        if handler:
            return handler(exception, context)
        else:
            return self._handle_generic_error(exception, context)
    
    def _handle_integrity_error(self, error: IntegrityError, context: Dict[str, Any]) -> Dict[str, Any]:
        """处理数据完整性错误"""
        logger.warning("数据完整性错误", {
            'error': str(error.orig),
            'context': context
        })
        
        # 判断是否为重复键错误
        error_message = str(error.orig).lower()
        if 'duplicate' in error_message or 'unique' in error_message:
            return {
                'success': False,
                'error_type': 'duplicate_entry',
                'message': '数据已存在，请检查输入',
                'recoverable': True,
                'retry': False
            }
        
        return {
            'success': False,
            'error_type': 'integrity_error',
            'message': '数据完整性错误',
            'recoverable': False,
            'retry': False
        }
    
    def _handle_operational_error(self, error: OperationalError, context: Dict[str, Any]) -> Dict[str, Any]:
        """处理数据库操作错误"""
        logger.error("数据库操作错误", {
            'error': str(error.orig),
            'context': context
        })
        
        error_message = str(error.orig).lower()
        
        # 连接问题
        if any(keyword in error_message for keyword in ['connection', 'connect', 'host']):
            return {
                'success': False,
                'error_type': 'database_connection',
                'message': '数据库连接失败',
                'recoverable': True,
                'retry': True,
                'retry_config': self.retry_config['database']
            }
        
        # 权限问题
        if 'access denied' in error_message or 'permission' in error_message:
            return {
                'success': False,
                'error_type': 'database_permission',
                'message': '数据库权限不足',
                'recoverable': False,
                'retry': False
            }
        
        return {
            'success': False,
            'error_type': 'database_operation',
            'message': '数据库操作失败',
            'recoverable': True,
            'retry': True,
            'retry_config': self.retry_config['database']
        }
    
    def _handle_sql_timeout_error(self, error: SQLTimeoutError, context: Dict[str, Any]) -> Dict[str, Any]:
        """处理SQL超时错误"""
        logger.warning("SQL查询超时", {
            'error': str(error),
            'context': context
        })
        
        return {
            'success': False,
            'error_type': 'sql_timeout',
            'message': '查询超时，请稍后重试',
            'recoverable': True,
            'retry': True,
            'retry_config': self.retry_config['database']
        }
    
    def _handle_disconnection_error(self, error: DisconnectionError, context: Dict[str, Any]) -> Dict[str, Any]:
        """处理数据库断线错误"""
        logger.error("数据库连接断开", {
            'error': str(error),
            'context': context
        })
        
        return {
            'success': False,
            'error_type': 'database_disconnection',
            'message': '数据库连接断开',
            'recoverable': True,
            'retry': True,
            'retry_config': self.retry_config['database']
        }
    
    def _handle_redis_connection_error(self, error: RedisConnectionError, context: Dict[str, Any]) -> Dict[str, Any]:
        """处理Redis连接错误"""
        logger.warning("Redis连接失败", {
            'error': str(error),
            'context': context
        })
        
        return {
            'success': False,
            'error_type': 'redis_connection',
            'message': 'Redis连接失败，使用备用方案',
            'recoverable': True,
            'retry': True,
            'retry_config': self.retry_config['cache'],
            'fallback': 'memory_cache'
        }
    
    def _handle_redis_timeout_error(self, error: RedisTimeoutError, context: Dict[str, Any]) -> Dict[str, Any]:
        """处理Redis超时错误"""
        logger.warning("Redis操作超时", {
            'error': str(error),
            'context': context
        })
        
        return {
            'success': False,
            'error_type': 'redis_timeout',
            'message': 'Redis操作超时',
            'recoverable': True,
            'retry': True,
            'retry_config': self.retry_config['cache']
        }
    
    def _handle_validation_error(self, error: ValidationException, context: Dict[str, Any]) -> Dict[str, Any]:
        """处理验证错误"""
        logger.info("数据验证失败", {
            'field': error.field,
            'value': str(error.value) if error.value is not None else None,
            'message': error.message,
            'context': context
        })
        
        return {
            'success': False,
            'error_type': 'validation_error',
            'message': error.message,
            'field': error.field,
            'recoverable': True,
            'retry': False
        }
    
    def _handle_business_logic_error(self, error: BusinessLogicException, context: Dict[str, Any]) -> Dict[str, Any]:
        """处理业务逻辑错误"""
        logger.info("业务逻辑错误", {
            'code': error.code,
            'message': error.message,
            'context': context
        })
        
        return {
            'success': False,
            'error_type': 'business_logic_error',
            'message': error.message,
            'code': error.code,
            'recoverable': True,
            'retry': False
        }
    
    def _handle_generic_error(self, error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
        """处理通用错误"""
        logger.error("未分类异常", {
            'exception_type': type(error).__name__,
            'error': str(error),
            'context': context,
            'traceback': traceback.format_exc()
        })
        
        return {
            'success': False,
            'error_type': 'generic_error',
            'message': '系统错误，请稍后重试',
            'recoverable': False,
            'retry': False
        }

# 全局异常处理器实例
exception_handler = EnhancedExceptionHandler()

def handle_database_errors(fallback_return=None, context: Dict[str, Any] = None):
    """数据库异常处理装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except SQLAlchemyError as e:
                result = exception_handler.handle_exception(e, context)
                logger.error(f"数据库操作失败: {func.__name__}", result)
                return fallback_return
            except Exception as e:
                result = exception_handler.handle_exception(e, context)
                logger.error(f"未预期异常: {func.__name__}", result)
                return fallback_return
        return wrapper
    return decorator

def handle_cache_errors(fallback_return=None, context: Dict[str, Any] = None):
    """缓存异常处理装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except RedisError as e:
                result = exception_handler.handle_exception(e, context)
                logger.warning(f"缓存操作失败: {func.__name__}", result)
                return fallback_return
            except Exception as e:
                result = exception_handler.handle_exception(e, context)
                logger.error(f"缓存操作异常: {func.__name__}", result)
                return fallback_return
        return wrapper
    return decorator

def safe_execute(func: Callable, *args, fallback_return=None, 
                context: Dict[str, Any] = None, **kwargs):
    """安全执行函数"""
    try:
        return func(*args, **kwargs)
    except Exception as e:
        result = exception_handler.handle_exception(e, context)
        logger.error(f"安全执行失败: {func.__name__ if hasattr(func, '__name__') else 'unknown'}", result)
        return fallback_return