"""
全局异常处理
定义自定义异常和全局异常处理器
"""
from typing import Any, Dict, Optional
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from pydantic import ValidationError
import traceback

from app.core.logger import log_error, log_warning


# ==================== 自定义异常 ====================

class AppException(Exception):
    """应用基础异常"""
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
    """请求错误（400）"""
    def __init__(self, message: str = "请求参数错误", detail: Optional[Any] = None):
        super().__init__(400, message, detail)


class UnauthorizedException(AppException):
    """未授权（401）"""
    def __init__(self, message: str = "未授权访问", detail: Optional[Any] = None):
        super().__init__(401, message, detail)


class ForbiddenException(AppException):
    """禁止访问（403）"""
    def __init__(self, message: str = "禁止访问", detail: Optional[Any] = None):
        super().__init__(403, message, detail)


class NotFoundException(AppException):
    """资源不存在（404）"""
    def __init__(self, message: str = "资源不存在", detail: Optional[Any] = None):
        super().__init__(404, message, detail)


class ConflictException(AppException):
    """资源冲突（409）"""
    def __init__(self, message: str = "资源冲突", detail: Optional[Any] = None):
        super().__init__(409, message, detail)


class ValidationException(AppException):
    """验证错误（422）"""
    def __init__(self, message: str = "数据验证失败", detail: Optional[Any] = None):
        super().__init__(422, message, detail)


class DatabaseException(AppException):
    """数据库错误（500）"""
    def __init__(self, message: str = "数据库操作失败", detail: Optional[Any] = None):
        super().__init__(500, message, detail)


# ==================== 异常处理器 ====================

def create_error_response(
    code: int, 
    message: str, 
    detail: Optional[Any] = None,
    path: Optional[str] = None
) -> JSONResponse:
    """创建统一的错误响应"""
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
    """处理自定义应用异常"""
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
    """处理FastAPI HTTPException"""
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
    """处理请求验证错误"""
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
    """处理SQLAlchemy数据库异常"""
    error_msg = "数据库操作失败"
    
    if isinstance(exc, IntegrityError):
        # 处理唯一约束冲突等
        if "Duplicate entry" in str(exc) or "UNIQUE constraint" in str(exc):
            error_msg = "数据已存在，请勿重复操作"
        elif "foreign key constraint" in str(exc).lower():
            error_msg = "关联数据不存在或被引用"
    
    log_error(f"数据库异常: {error_msg}", {
        "path": str(request.url.path),
        "method": request.method,
        "error": str(exc)[:500]  # 限制错误信息长度
    })
    
    return create_error_response(
        code=500,
        message=error_msg,
        path=str(request.url.path)
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """处理所有未捕获的异常"""
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
    """注册所有异常处理器到FastAPI应用"""
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)
