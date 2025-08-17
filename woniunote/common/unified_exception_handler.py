#!/usr/bin/env python3
"""
统一异常处理系统
提供标准化的异常处理、错误码管理和响应格式
"""

import sys
import time
import traceback
from enum import Enum
from typing import Dict, Any, Optional, Tuple, Union
from functools import wraps
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, DataError, OperationalError
from flask import jsonify, request
from woniunote.common.simple_logger import get_simple_logger

logger = get_simple_logger('unified_exception_handler')

class ErrorCode(Enum):
    """统一错误码枚举"""
    
    # 系统错误 (1000-1999)
    SYSTEM_ERROR = (1000, "系统内部错误")
    DATABASE_ERROR = (1001, "数据库操作失败")
    NETWORK_ERROR = (1002, "网络连接错误")
    CONFIG_ERROR = (1003, "配置错误")
    
    # 业务错误 (2000-2999)
    VALIDATION_ERROR = (2000, "参数验证失败")
    AUTHENTICATION_ERROR = (2001, "身份验证失败")
    AUTHORIZATION_ERROR = (2002, "权限不足")
    RESOURCE_NOT_FOUND = (2003, "资源未找到")
    RESOURCE_CONFLICT = (2004, "资源冲突")
    BUSINESS_LOGIC_ERROR = (2005, "业务逻辑错误")
    
    # 用户错误 (3000-3999)
    INVALID_INPUT = (3000, "输入无效")
    MISSING_PARAMETER = (3001, "缺少必需参数")
    INVALID_FORMAT = (3002, "格式错误")
    RATE_LIMIT_EXCEEDED = (3003, "请求频率过高")
    FILE_TOO_LARGE = (3004, "文件过大")
    UNSUPPORTED_FILE_TYPE = (3005, "不支持的文件类型")
    
    # 外部服务错误 (4000-4999)
    EXTERNAL_SERVICE_ERROR = (4000, "外部服务错误")
    REDIS_ERROR = (4001, "Redis连接错误")
    EMAIL_SERVICE_ERROR = (4002, "邮件服务错误")
    
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message

class BusinessException(Exception):
    """业务异常基类"""
    
    def __init__(self, error_code: ErrorCode, detail: str = None, data: Any = None):
        self.error_code = error_code
        self.detail = detail or error_code.message
        self.data = data
        super().__init__(self.detail)

class ValidationException(BusinessException):
    """验证异常"""
    
    def __init__(self, detail: str = None, field: str = None, data: Any = None):
        self.field = field
        super().__init__(ErrorCode.VALIDATION_ERROR, detail, data)

class AuthenticationException(BusinessException):
    """认证异常"""
    
    def __init__(self, detail: str = None):
        super().__init__(ErrorCode.AUTHENTICATION_ERROR, detail)

class AuthorizationException(BusinessException):
    """授权异常"""
    
    def __init__(self, detail: str = None, required_permission: str = None):
        self.required_permission = required_permission
        super().__init__(ErrorCode.AUTHORIZATION_ERROR, detail)

class ResourceNotFoundException(BusinessException):
    """资源未找到异常"""
    
    def __init__(self, resource_type: str = None, resource_id: Any = None):
        self.resource_type = resource_type
        self.resource_id = resource_id
        detail = f"{resource_type} {resource_id} 未找到" if resource_type and resource_id else "资源未找到"
        super().__init__(ErrorCode.RESOURCE_NOT_FOUND, detail)

class UnifiedExceptionHandler:
    """统一异常处理器"""
    
    def __init__(self):
        self.error_handlers = {
            BusinessException: self._handle_business_exception,
            SQLAlchemyError: self._handle_database_exception,
            IntegrityError: self._handle_integrity_exception,
            DataError: self._handle_data_exception,
            OperationalError: self._handle_operational_exception,
            ValueError: self._handle_value_exception,
            TypeError: self._handle_type_exception,
            KeyError: self._handle_key_exception,
            AttributeError: self._handle_attribute_exception,
            FileNotFoundError: self._handle_file_not_found_exception,
            PermissionError: self._handle_permission_exception,
        }
    
    def handle_exception(self, exc: Exception, context: Dict[str, Any] = None) -> Tuple[Dict[str, Any], int]:
        """
        处理异常并返回标准化响应
        
        Args:
            exc: 异常实例
            context: 异常上下文信息
            
        Returns:
            Tuple[Dict, int]: (响应数据, HTTP状态码)
        """
        context = context or {}
        exc_type = type(exc)
        
        # 记录异常信息
        self._log_exception(exc, context)
        
        # 查找合适的处理器
        handler = self._find_handler(exc_type)
        
        if handler:
            return handler(exc, context)
        else:
            # 默认处理器
            return self._handle_unknown_exception(exc, context)
    
    def _find_handler(self, exc_type: type) -> Optional[callable]:
        """查找异常处理器"""
        # 精确匹配
        if exc_type in self.error_handlers:
            return self.error_handlers[exc_type]
        
        # 继承匹配
        for handler_type, handler in self.error_handlers.items():
            if issubclass(exc_type, handler_type):
                return handler
        
        return None
    
    def _log_exception(self, exc: Exception, context: Dict[str, Any]):
        """记录异常日志"""
        exc_info = {
            'exception_type': type(exc).__name__,
            'exception_message': str(exc),
            'context': context
        }
        
        # 对于系统级异常，记录完整堆栈
        if not isinstance(exc, BusinessException):
            exc_info['traceback'] = traceback.format_exc()
        
        # 根据异常类型选择日志级别
        if isinstance(exc, BusinessException):
            logger.warning("业务异常", exc_info)
        elif isinstance(exc, (ValueError, TypeError, KeyError)):
            logger.error("程序逻辑异常", exc_info)
        else:
            logger.error("系统异常", exc_info)
    
    def _handle_business_exception(self, exc: BusinessException, context: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
        """处理业务异常"""
        response = {
            'success': False,
            'error_code': exc.error_code.code,
            'error_message': exc.detail,
            'timestamp': context.get('timestamp', int(time.time() * 1000))
        }
        
        if exc.data is not None:
            response['data'] = exc.data
        
        # 根据错误类型确定HTTP状态码
        if exc.error_code in [ErrorCode.AUTHENTICATION_ERROR]:
            status_code = 401
        elif exc.error_code in [ErrorCode.AUTHORIZATION_ERROR]:
            status_code = 403
        elif exc.error_code in [ErrorCode.RESOURCE_NOT_FOUND]:
            status_code = 404
        elif exc.error_code in [ErrorCode.RESOURCE_CONFLICT]:
            status_code = 409
        elif exc.error_code in [ErrorCode.RATE_LIMIT_EXCEEDED]:
            status_code = 429
        else:
            status_code = 400
        
        return response, status_code
    
    def _handle_database_exception(self, exc: SQLAlchemyError, context: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
        """处理数据库异常"""
        response = {
            'success': False,
            'error_code': ErrorCode.DATABASE_ERROR.code,
            'error_message': "数据库操作失败",
            'timestamp': context.get('timestamp', int(time.time() * 1000))
        }
        
        return response, 500
    
    def _handle_integrity_exception(self, exc: IntegrityError, context: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
        """处理数据完整性异常"""
        response = {
            'success': False,
            'error_code': ErrorCode.RESOURCE_CONFLICT.code,
            'error_message': "数据约束冲突",
            'timestamp': context.get('timestamp', int(time.time() * 1000))
        }
        
        return response, 409
    
    def _handle_data_exception(self, exc: DataError, context: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
        """处理数据错误异常"""
        response = {
            'success': False,
            'error_code': ErrorCode.INVALID_INPUT.code,
            'error_message': "数据格式错误",
            'timestamp': context.get('timestamp', int(time.time() * 1000))
        }
        
        return response, 400
    
    def _handle_operational_exception(self, exc: OperationalError, context: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
        """处理数据库操作异常"""
        response = {
            'success': False,
            'error_code': ErrorCode.DATABASE_ERROR.code,
            'error_message': "数据库连接错误",
            'timestamp': context.get('timestamp', int(time.time() * 1000))
        }
        
        return response, 503
    
    def _handle_value_exception(self, exc: ValueError, context: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
        """处理值错误异常"""
        response = {
            'success': False,
            'error_code': ErrorCode.INVALID_INPUT.code,
            'error_message': str(exc) if str(exc) else "参数值错误",
            'timestamp': context.get('timestamp', int(time.time() * 1000))
        }
        
        return response, 400
    
    def _handle_type_exception(self, exc: TypeError, context: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
        """处理类型错误异常"""
        response = {
            'success': False,
            'error_code': ErrorCode.INVALID_INPUT.code,
            'error_message': "参数类型错误",
            'timestamp': context.get('timestamp', int(time.time() * 1000))
        }
        
        return response, 400
    
    def _handle_key_exception(self, exc: KeyError, context: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
        """处理键错误异常"""
        response = {
            'success': False,
            'error_code': ErrorCode.MISSING_PARAMETER.code,
            'error_message': f"缺少必需参数: {str(exc)}",
            'timestamp': context.get('timestamp', int(time.time() * 1000))
        }
        
        return response, 400
    
    def _handle_attribute_exception(self, exc: AttributeError, context: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
        """处理属性错误异常"""
        response = {
            'success': False,
            'error_code': ErrorCode.SYSTEM_ERROR.code,
            'error_message': "系统内部错误",
            'timestamp': context.get('timestamp', int(time.time() * 1000))
        }
        
        return response, 500
    
    def _handle_file_not_found_exception(self, exc: FileNotFoundError, context: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
        """处理文件未找到异常"""
        response = {
            'success': False,
            'error_code': ErrorCode.RESOURCE_NOT_FOUND.code,
            'error_message': "文件未找到",
            'timestamp': context.get('timestamp', int(time.time() * 1000))
        }
        
        return response, 404
    
    def _handle_permission_exception(self, exc: PermissionError, context: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
        """处理权限错误异常"""
        response = {
            'success': False,
            'error_code': ErrorCode.AUTHORIZATION_ERROR.code,
            'error_message': "权限不足",
            'timestamp': context.get('timestamp', int(time.time() * 1000))
        }
        
        return response, 403
    
    def _handle_unknown_exception(self, exc: Exception, context: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
        """处理未知异常"""
        response = {
            'success': False,
            'error_code': ErrorCode.SYSTEM_ERROR.code,
            'error_message': "系统内部错误",
            'timestamp': context.get('timestamp', int(time.time() * 1000))
        }
        
        return response, 500

def exception_handler(include_traceback: bool = False):
    """异常处理装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                handler = UnifiedExceptionHandler()
                context = {
                    'function': f"{func.__module__}.{func.__name__}",
                    'args_count': len(args),
                    'kwargs_keys': list(kwargs.keys()),
                    'timestamp': int(time.time() * 1000)
                }
                
                # 添加请求上下文（如果在Flask请求中）
                try:
                    if request:
                        context.update({
                            'method': request.method,
                            'path': request.path,
                            'remote_addr': request.remote_addr,
                            'user_agent': request.user_agent.string if request.user_agent else None
                        })
                except:
                    pass
                
                response_data, status_code = handler.handle_exception(e, context)
                
                # 如果是Flask环境，返回JSON响应
                try:
                    return jsonify(response_data), status_code
                except:
                    # 非Flask环境，直接返回数据
                    return response_data
        
        return wrapper
    return decorator

def raise_business_error(error_code: ErrorCode, detail: str = None, data: Any = None):
    """抛出业务异常的便捷函数"""
    raise BusinessException(error_code, detail, data)

def raise_validation_error(detail: str, field: str = None, data: Any = None):
    """抛出验证异常的便捷函数"""
    raise ValidationException(detail, field, data)

def raise_auth_error(detail: str = None):
    """抛出认证异常的便捷函数"""
    raise AuthenticationException(detail)

def raise_permission_error(detail: str = None, required_permission: str = None):
    """抛出权限异常的便捷函数"""
    raise AuthorizationException(detail, required_permission)

def raise_not_found_error(resource_type: str = None, resource_id: Any = None):
    """抛出资源未找到异常的便捷函数"""
    raise ResourceNotFoundException(resource_type, resource_id)

# 全局异常处理器实例
global_exception_handler = UnifiedExceptionHandler()

# 便捷函数
def handle_exception(exc: Exception, context: Dict[str, Any] = None) -> Tuple[Dict[str, Any], int]:
    """处理异常的便捷函数"""
    return global_exception_handler.handle_exception(exc, context)