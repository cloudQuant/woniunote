"""
中间件配置模块

本模块定义了应用的中间件，用于处理请求和响应。
"""
import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from app.core.logger import log_info, log_error, log_warning


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    请求日志中间件
    
    记录每个 HTTP 请求的详细信息，包括：
    - 请求方法和路径
    - 响应状态码
    - 请求耗时
    - 客户端 IP
    
    同时会根据响应状态码记录不同级别的日志：
    - 2xx/3xx: INFO
    - 4xx: WARNING
    - 5xx: ERROR
    """
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """
        处理请求
        
        Args:
            request: 请求对象
            call_next: 下一个中间件或路由处理函数
            
        Returns:
            Response: 响应对象
        """
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
