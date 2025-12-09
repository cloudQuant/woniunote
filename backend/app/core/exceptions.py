"""
全局异常处理模块

本模块定义了应用自定义异常类和全局异常处理器。
通过统一的异常处理机制，确保 API 返回一致的错误响应格式。
"""
from typing import Any, Dict, Optional
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from pydantic import ValidationError
import traceback

from app.core.logger import log_error, log_warning
from app.core.config import settings


# ==================== 自定义异常 ====================

class AppException(Exception):
    """
    应用基础异常类
    
    所有自定义异常都应继承此类。
    
    Attributes:
        code (int): HTTP 状态码
        message (str): 错误信息
        detail (Optional[Any]): 详细错误信息
    """
    def __init__(
        self, 
        code: int = 500, 
        message: str = "服务器内部错误",
        detail: Optional[Any] = None
    ):
        self.code = code
        self.message = message
        self.detail = detail
        super().__init__(message)


class BadRequestException(AppException):
    """
    请求错误异常 (400)
    
    当客户端发送的请求有误时抛出。
    """
    def __init__(self, message: str = "请求参数错误", detail: Optional[Any] = None):
        super().__init__(400, message, detail)


class UnauthorizedException(AppException):
    """
    未授权异常 (401)
    
    当用户未登录或 Token 无效时抛出。
    """
    def __init__(self, message: str = "未授权访问", detail: Optional[Any] = None):
        super().__init__(401, message, detail)


class ForbiddenException(AppException):
    """
    禁止访问异常 (403)
    
    当用户权限不足时抛出。
    """
    def __init__(self, message: str = "禁止访问", detail: Optional[Any] = None):
        super().__init__(403, message, detail)


class NotFoundException(AppException):
    """
    资源不存在异常 (404)
    
    当请求的资源不存在时抛出。
    """
    def __init__(self, message: str = "资源不存在", detail: Optional[Any] = None):
        super().__init__(404, message, detail)


class ConflictException(AppException):
    """
    资源冲突异常 (409)
    
    当请求的操作会导致资源冲突（如重复创建）时抛出。
    """
    def __init__(self, message: str = "资源冲突", detail: Optional[Any] = None):
        super().__init__(409, message, detail)


class ValidationException(AppException):
    """
    验证错误异常 (422)
    
    当数据验证失败时抛出。
    """
    def __init__(self, message: str = "数据验证失败", detail: Optional[Any] = None):
        super().__init__(422, message, detail)


class DatabaseException(AppException):
    """
    数据库错误异常 (500)
    
    当数据库操作失败时抛出。
    """
    def __init__(self, message: str = "数据库操作失败", detail: Optional[Any] = None):
        super().__init__(500, message, detail)


# ==================== 异常处理器 ====================

def create_error_response(
    code: int, 
    message: str, 
    detail: Optional[Any] = None,
    path: Optional[str] = None
) -> JSONResponse:
    """
    创建统一的错误响应
    
    Args:
        code: HTTP 状态码
        message: 错误提示信息
        detail: 详细错误数据（可选）
        path: 请求路径（可选）
        
    Returns:
        JSONResponse: 包含错误信息的 JSON 响应
    """
    content = {
        "code": code,
        "message": message,
        "data": None
    }
    if detail:
        content["detail"] = detail
    if path:
        content["path"] = path
    
    return JSONResponse(status_code=code, content=content)


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """
    处理自定义应用异常
    
    Args:
        request: FastAPI 请求对象
        exc: 捕获的 AppException 实例
        
    Returns:
        JSONResponse: 格式化的错误响应
    """
    log_warning(f"应用异常: {exc.message}", {
        "code": exc.code,
        "path": str(request.url.path),
        "method": request.method,
        "detail": exc.detail
    })
    return create_error_response(
        code=exc.code,
        message=exc.message,
        detail=exc.detail,
        path=str(request.url.path)
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """
    处理 FastAPI 内置 HTTPException
    
    Args:
        request: FastAPI 请求对象
        exc: 捕获的 HTTPException 实例
        
    Returns:
        JSONResponse: 格式化的错误响应
    """
    log_warning(f"HTTP异常: {exc.detail}", {
        "status_code": exc.status_code,
        "path": str(request.url.path),
        "method": request.method
    })
    return create_error_response(
        code=exc.status_code,
        message=str(exc.detail),
        path=str(request.url.path)
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    处理请求参数验证错误
    
    将 Pydantic 的验证错误转换为统一格式。
    
    Args:
        request: FastAPI 请求对象
        exc: 捕获的 RequestValidationError 实例
        
    Returns:
        JSONResponse: 格式化的错误响应 (422)
    """
    errors = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"])
        errors.append({
            "field": field,
            "message": error["msg"],
            "type": error["type"]
        })
    
    log_warning(f"请求验证失败", {
        "path": str(request.url.path),
        "method": request.method,
        "errors": errors
    })
    
    return create_error_response(
        code=422,
        message="请求参数验证失败",
        detail=errors,
        path=str(request.url.path)
    )


async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    """
    处理 SQLAlchemy 数据库异常
    
    捕获数据库层面的错误，如唯一约束冲突、外键约束等，并转换为友好的错误信息。
    
    Args:
        request: FastAPI 请求对象
        exc: 捕获的 SQLAlchemyError 实例
        
    Returns:
        JSONResponse: 格式化的错误响应 (500)
    """
    error_msg = "数据库操作失败"
    
    if isinstance(exc, IntegrityError):
        # 处理唯一约束冲突等
        if "Duplicate entry" in str(exc) or "UNIQUE constraint" in str(exc):
            error_msg = "数据已存在，请勿重复操作"
        elif "foreign key constraint" in str(exc).lower():
            error_msg = "关联数据不存在或被引用"
    
    # 在日志中附带完整的异常信息，方便排查
    log_error(f"数据库异常: {error_msg} - {str(exc)[:500]}", {
        "path": str(request.url.path),
        "method": request.method,
        "error": str(exc)[:500]  # 限制错误信息长度
    })
    
    # 开发环境下，将具体异常信息返回到 detail 字段，方便前端看到真实错误
    detail_data: Optional[Any] = None
    if settings.DEBUG:
        detail_data = {"error": str(exc)[:500]}
    
    return create_error_response(
        code=500,
        message=error_msg,
        detail=detail_data,
        path=str(request.url.path)
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    处理所有未捕获的异常
    
    作为最后的防线，捕获所有未处理的异常，记录堆栈跟踪，并返回 500 错误。
    
    Args:
        request: FastAPI 请求对象
        exc: 捕获的 Exception 实例
        
    Returns:
        JSONResponse: 格式化的错误响应 (500)
    """
    # 记录完整的堆栈跟踪
    tb = traceback.format_exc()
    
    log_error(f"未处理异常: {type(exc).__name__}: {str(exc)}", {
        "path": str(request.url.path),
        "method": request.method,
        "traceback": tb[:2000]  # 限制长度
    })
    
    return create_error_response(
        code=500,
        message="服务器内部错误，请稍后重试",
        path=str(request.url.path)
    )


def register_exception_handlers(app: FastAPI):
    """
    注册所有异常处理器到 FastAPI 应用
    
    Args:
        app: FastAPI 应用实例
    """
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)
