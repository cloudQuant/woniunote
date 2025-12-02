"""
请求限流中间件
使用令牌桶算法实现简单的限流功能
"""
import time
import threading
from collections import defaultdict
from typing import Dict, Tuple
from fastapi import Request, HTTPException, status


class RateLimiter:
    """
    简单的内存限流器
    生产环境建议使用 Redis 实现分布式限流
    """
    
    def __init__(self):
        # {key: (tokens, last_update_time)}
        self._buckets: Dict[str, Tuple[float, float]] = defaultdict(lambda: (0, 0))
        self._lock = threading.Lock()
    
    def is_allowed(
        self, 
        key: str, 
        max_requests: int = 60, 
        window_seconds: int = 60
    ) -> Tuple[bool, int]:
        """
        检查是否允许请求
        
        Args:
            key: 限流key（如IP地址、用户ID等）
            max_requests: 时间窗口内最大请求数
            window_seconds: 时间窗口（秒）
            
        Returns:
            (是否允许, 剩余请求数)
        """
        now = time.time()
        
        with self._lock:
            tokens, last_update = self._buckets[key]
            
            # 计算应该补充的令牌数
            elapsed = now - last_update
            refill = elapsed * (max_requests / window_seconds)
            tokens = min(max_requests, tokens + refill)
            
            if tokens >= 1:
                tokens -= 1
                self._buckets[key] = (tokens, now)
                return True, int(tokens)
            else:
                self._buckets[key] = (tokens, now)
                return False, 0
    
    def cleanup(self, max_age_seconds: int = 3600):
        """清理过期的限流记录"""
        now = time.time()
        with self._lock:
            expired_keys = [
                key for key, (_, last_update) in self._buckets.items()
                if now - last_update > max_age_seconds
            ]
            for key in expired_keys:
                del self._buckets[key]


# 全局限流器实例
rate_limiter = RateLimiter()


# 不同接口的限流配置
RATE_LIMIT_CONFIG = {
    # 格式: "路由前缀": (最大请求数, 时间窗口秒数)
    "/api/auth/login": (5, 60),        # 登录: 每分钟5次
    "/api/auth/register": (3, 60),     # 注册: 每分钟3次
    "/api/captcha/generate": (10, 60), # 验证码: 每分钟10次
    "/api/comments": (20, 60),         # 评论: 每分钟20次
    "/api/upload": (10, 60),           # 上传: 每分钟10次
    "default": (120, 60),              # 默认: 每分钟120次
}


def get_rate_limit_config(path: str) -> Tuple[int, int]:
    """获取路径对应的限流配置"""
    for prefix, config in RATE_LIMIT_CONFIG.items():
        if prefix != "default" and path.startswith(prefix):
            return config
    return RATE_LIMIT_CONFIG["default"]


async def rate_limit_middleware(request: Request, call_next):
    """
    限流中间件
    """
    # 获取客户端IP
    client_ip = request.client.host if request.client else "unknown"
    path = request.url.path
    
    # 获取限流配置
    max_requests, window_seconds = get_rate_limit_config(path)
    
    # 构建限流key（IP + 路径前缀）
    # 对于认证相关接口，只使用IP
    if path.startswith("/api/auth/"):
        limit_key = f"auth:{client_ip}"
    else:
        limit_key = f"{client_ip}:{path.split('/')[2] if len(path.split('/')) > 2 else 'root'}"
    
    # 检查限流
    allowed, remaining = rate_limiter.is_allowed(limit_key, max_requests, window_seconds)
    
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="请求过于频繁，请稍后再试",
            headers={"Retry-After": str(window_seconds)}
        )
    
    # 继续处理请求
    response = await call_next(request)
    
    # 添加限流相关响应头
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    response.headers["X-RateLimit-Limit"] = str(max_requests)
    
    return response
