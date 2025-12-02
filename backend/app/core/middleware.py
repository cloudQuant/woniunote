"""
中间件配置
"""
import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from app.core.logger import log_info, log_error, log_warning


class LoggingMiddleware(BaseHTTPMiddleware):
    """请求日志中间件"""
    
    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.time()
        
        # 获取请求信息
        method = request.method
        path = request.url.path
        client_ip = request.client.host if request.client else "unknown"
        
        try:
            response = await call_next(request)
            
            # 计算响应时间
            duration_ms = (time.time() - start_time) * 1000
            
            # 记录请求日志
            log_info(
                f"HTTP {method} {path}",
                {
                    "status": response.status_code,
                    "duration_ms": f"{duration_ms:.2f}",
                    "client_ip": client_ip
                }
            )
            
            # 记录警告（4xx错误）
            if 400 <= response.status_code < 500:
                log_warning(
                    f"Client error: {method} {path}",
                    {"status": response.status_code, "client_ip": client_ip}
                )
            
            # 记录错误（5xx错误）
            elif response.status_code >= 500:
                log_error(
                    f"Server error: {method} {path}",
                    {"status": response.status_code, "client_ip": client_ip}
                )
            
            return response
            
        except Exception as e:
            # 计算响应时间
            duration_ms = (time.time() - start_time) * 1000
            
            # 记录异常
            log_error(
                f"Request exception: {method} {path}",
                {
                    "error": repr(e),
                    "duration_ms": f"{duration_ms:.2f}",
                    "client_ip": client_ip,
                },
            )
            raise
