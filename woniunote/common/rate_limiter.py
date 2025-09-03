#!/usr/bin/env python3
"""
API限流工具 - 支持多种限流算法
"""

import time
import hashlib
import logging
from collections import defaultdict, deque
from threading import Lock
from typing import Dict, Optional, Tuple, Callable
from functools import wraps
from flask import request, jsonify, g

logger = logging.getLogger(__name__)

class SlidingWindowLimiter:
    """滑动窗口限流器"""
    
    def __init__(self, max_requests: int, window_size: int = 60):
        """
        :param max_requests: 窗口内最大请求数
        :param window_size: 窗口大小（秒）
        """
        self.max_requests = max_requests
        self.window_size = window_size
        self.requests: Dict[str, deque] = defaultdict(deque)
        self.lock = Lock()
    
    def is_allowed(self, key: str) -> Tuple[bool, Dict[str, any]]:
        """检查是否允许请求"""
        current_time = time.time()
        
        with self.lock:
            # 清理过期请求
            request_times = self.requests[key]
            while request_times and current_time - request_times[0] > self.window_size:
                request_times.popleft()
            
            # 检查限流
            if len(request_times) >= self.max_requests:
                oldest_request = request_times[0]
                reset_time = oldest_request + self.window_size
                return False, {
                    'allowed': False,
                    'limit': self.max_requests,
                    'remaining': 0,
                    'reset_time': reset_time,
                    'retry_after': int(reset_time - current_time) + 1
                }
            
            # 记录当前请求
            request_times.append(current_time)
            remaining = self.max_requests - len(request_times)
            
            return True, {
                'allowed': True,
                'limit': self.max_requests,
                'remaining': remaining,
                'reset_time': current_time + self.window_size,
                'retry_after': 0
            }


class TokenBucketLimiter:
    """令牌桶限流器"""
    
    def __init__(self, capacity: int, refill_rate: float, refill_period: int = 1):
        """
        :param capacity: 桶容量
        :param refill_rate: 每个周期补充的令牌数
        :param refill_period: 补充周期（秒）
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.refill_period = refill_period
        self.buckets: Dict[str, Dict] = defaultdict(lambda: {
            'tokens': capacity,
            'last_refill': time.time()
        })
        self.lock = Lock()
    
    def _refill_bucket(self, bucket: Dict) -> None:
        """补充令牌"""
        current_time = time.time()
        time_passed = current_time - bucket['last_refill']
        
        if time_passed >= self.refill_period:
            periods = int(time_passed / self.refill_period)
            tokens_to_add = periods * self.refill_rate
            bucket['tokens'] = min(self.capacity, bucket['tokens'] + tokens_to_add)
            bucket['last_refill'] = current_time
    
    def is_allowed(self, key: str, tokens_required: int = 1) -> Tuple[bool, Dict[str, any]]:
        """检查是否允许请求"""
        with self.lock:
            bucket = self.buckets[key]
            self._refill_bucket(bucket)
            
            if bucket['tokens'] >= tokens_required:
                bucket['tokens'] -= tokens_required
                return True, {
                    'allowed': True,
                    'limit': self.capacity,
                    'remaining': int(bucket['tokens']),
                    'retry_after': 0
                }
            else:
                # 计算下次可用时间
                tokens_needed = tokens_required - bucket['tokens']
                periods_to_wait = (tokens_needed + self.refill_rate - 1) // self.refill_rate
                retry_after = int(periods_to_wait * self.refill_period) + 1
                
                return False, {
                    'allowed': False,
                    'limit': self.capacity,
                    'remaining': int(bucket['tokens']),
                    'retry_after': retry_after
                }


class RateLimiter:
    """统一限流管理器"""
    
    def __init__(self, default_limiter=None, max_calls=None, period=None):
        self.limiters: Dict[str, any] = {}
        
        # 如果提供了max_calls和period，创建一个简单的限流器
        if max_calls is not None and period is not None:
            self.default_limiter = SlidingWindowLimiter(max_calls, period)
        else:
            self.default_limiter = default_limiter or SlidingWindowLimiter(100, 60)
            
        self.global_limiter = SlidingWindowLimiter(1000, 60)  # 全局限流
    
    def add_limiter(self, name: str, limiter) -> None:
        """添加限流器"""
        self.limiters[name] = limiter
    
    def get_limiter(self, name: str):
        """获取限流器"""
        return self.limiters.get(name, self.default_limiter)
    
    def check_rate_limit(self, key: str, limiter_name: str = None) -> Tuple[bool, Dict[str, any]]:
        """检查限流"""
        limiter = self.get_limiter(limiter_name) if limiter_name else self.default_limiter
        return limiter.is_allowed(key)
    
    def check_global_limit(self, key: str) -> Tuple[bool, Dict[str, any]]:
        """检查全局限流"""
        return self.global_limiter.is_allowed(key)
    
    def is_allowed(self, key: str) -> bool:
        """检查是否允许请求（兼容性方法）"""
        result = self.default_limiter.is_allowed(key)
        if isinstance(result, tuple):
            return result[0]  # 返回布尔值部分
        return result


def get_client_key(request) -> str:
    """生成客户端唯一标识"""
    # 优先使用用户ID
    if hasattr(g, 'user_id') and g.user_id:
        return f"user:{g.user_id}"
    
    # 使用IP地址
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    if client_ip and ',' in client_ip:
        client_ip = client_ip.split(',')[0].strip()
    
    # 添加User-Agent作为额外标识
    user_agent = request.headers.get('User-Agent', '')
    user_agent_hash = hashlib.md5(user_agent.encode()).hexdigest()[:8]
    
    return f"ip:{client_ip}:{user_agent_hash}"


def create_rate_limit_response(limit_info: Dict[str, any]) -> tuple:
    """创建限流响应"""
    response_data = {
        'error': 'Rate limit exceeded',
        'message': f"Too many requests. Limit: {limit_info['limit']}, Remaining: {limit_info['remaining']}",
        'retry_after': limit_info.get('retry_after', 60)
    }
    
    headers = {
        'X-RateLimit-Limit': str(limit_info['limit']),
        'X-RateLimit-Remaining': str(limit_info['remaining']),
        'Retry-After': str(limit_info.get('retry_after', 60))
    }
    
    if 'reset_time' in limit_info:
        headers['X-RateLimit-Reset'] = str(int(limit_info['reset_time']))
    
    response = jsonify(response_data), 429, headers
    return response


# 全局限流器实例
_global_rate_limiter = None

def get_rate_limiter() -> RateLimiter:
    """获取全局限流器"""
    global _global_rate_limiter
    if _global_rate_limiter is None:
        _global_rate_limiter = RateLimiter()
        
        # 配置不同类型的限流器 (已增加10倍容量)
        _global_rate_limiter.add_limiter('strict', SlidingWindowLimiter(200, 60))  # 严格限流: 200次/分钟
        _global_rate_limiter.add_limiter('moderate', SlidingWindowLimiter(600, 60))  # 中等限流: 600次/分钟
        _global_rate_limiter.add_limiter('lenient', SlidingWindowLimiter(2000, 60))  # 宽松限流: 2000次/分钟
        _global_rate_limiter.add_limiter('api', TokenBucketLimiter(500, 100, 1))  # API限流: 500容量，100令牌/秒
        _global_rate_limiter.add_limiter('upload', TokenBucketLimiter(50, 10, 10))  # 上传限流: 50容量，10令牌/10秒
        
    return _global_rate_limiter


def rate_limit(limit_type: str = 'default', key_func: Optional[Callable] = None):
    """限流装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            rate_limiter = get_rate_limiter()
            
            # 生成限流键
            if key_func:
                key = key_func()
            else:
                key = get_client_key(request)
            
            # 检查全局限流
            global_allowed, global_info = rate_limiter.check_global_limit(key)
            if not global_allowed:
                logger.warning(f"Global rate limit exceeded for key: {key}")
                return create_rate_limit_response(global_info)
            
            # 检查特定限流
            allowed, limit_info = rate_limiter.check_rate_limit(key, limit_type)
            if not allowed:
                logger.warning(f"Rate limit exceeded for key: {key}, type: {limit_type}")
                return create_rate_limit_response(limit_info)
            
            # 添加限流头信息到响应
            try:
                response = func(*args, **kwargs)
                
                # 如果响应是tuple形式，添加头信息
                if isinstance(response, tuple) and len(response) >= 2:
                    data, status_code = response[0], response[1]
                    headers = response[2] if len(response) > 2 else {}
                elif hasattr(response, 'headers'):
                    # Flask Response对象
                    headers = response.headers
                else:
                    return response
                
                # 添加限流头信息
                if isinstance(headers, dict):
                    headers.update({
                        'X-RateLimit-Limit': str(limit_info['limit']),
                        'X-RateLimit-Remaining': str(limit_info['remaining'])
                    })
                    if 'reset_time' in limit_info:
                        headers['X-RateLimit-Reset'] = str(int(limit_info['reset_time']))
                elif hasattr(headers, '__setitem__'):
                    headers['X-RateLimit-Limit'] = str(limit_info['limit'])
                    headers['X-RateLimit-Remaining'] = str(limit_info['remaining'])
                    if 'reset_time' in limit_info:
                        headers['X-RateLimit-Reset'] = str(int(limit_info['reset_time']))
                
                return response
                
            except Exception as e:
                logger.error(f"Error in rate limited function: {e}")
                raise
        
        return wrapper
    return decorator


def init_rate_limiter(config=None):
    """初始化限流器"""
    global _global_rate_limiter
    
    try:
        _global_rate_limiter = RateLimiter()
        
        if config:
            # 根据配置添加限流器
            for name, limiter_config in config.items():
                limiter_type = limiter_config.get('type', 'sliding_window')
                
                if limiter_type == 'sliding_window':
                    limiter = SlidingWindowLimiter(
                        max_requests=limiter_config.get('max_requests', 100),
                        window_size=limiter_config.get('window_size', 60)
                    )
                elif limiter_type == 'token_bucket':
                    limiter = TokenBucketLimiter(
                        capacity=limiter_config.get('capacity', 50),
                        refill_rate=limiter_config.get('refill_rate', 10),
                        refill_period=limiter_config.get('refill_period', 1)
                    )
                else:
                    logger.warning(f"Unknown limiter type: {limiter_type}")
                    continue
                
                _global_rate_limiter.add_limiter(name, limiter)
        else:
            # 使用默认配置
            get_rate_limiter()
        
        logger.info("Rate limiter initialized successfully")
        return _global_rate_limiter
        
    except Exception as e:
        logger.error(f"Rate limiter initialization error: {e}")
        _global_rate_limiter = RateLimiter()
        return _global_rate_limiter


# IP白名单管理
class IPWhitelist:
    """IP白名单管理"""
    
    def __init__(self, whitelist_ips=None):
        self.whitelist = set(whitelist_ips or [])
        self.lock = Lock()
    
    def add_ip(self, ip: str) -> None:
        """添加IP到白名单"""
        with self.lock:
            self.whitelist.add(ip)
    
    def remove_ip(self, ip: str) -> None:
        """从白名单移除IP"""
        with self.lock:
            self.whitelist.discard(ip)
    
    def is_whitelisted(self, ip: str) -> bool:
        """检查IP是否在白名单"""
        with self.lock:
            return ip in self.whitelist
    
    def get_whitelist(self) -> set:
        """获取白名单"""
        with self.lock:
            return self.whitelist.copy()


# 全局IP白名单
_ip_whitelist = None

def get_ip_whitelist() -> IPWhitelist:
    """获取IP白名单管理器"""
    global _ip_whitelist
    if _ip_whitelist is None:
        # 默认白名单IP
        default_whitelist = ['127.0.0.1', '::1', 'localhost']
        _ip_whitelist = IPWhitelist(default_whitelist)
    return _ip_whitelist


def bypass_rate_limit_if_whitelisted(func):
    """如果IP在白名单中则跳过限流"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        if client_ip and ',' in client_ip:
            client_ip = client_ip.split(',')[0].strip()
        
        whitelist = get_ip_whitelist()
        if whitelist.is_whitelisted(client_ip):
            logger.debug(f"Bypassing rate limit for whitelisted IP: {client_ip}")
            # 跳过限流，直接执行原函数
            return args[0](*args[1:], **kwargs) if args else func(**kwargs)
        
        return func(*args, **kwargs)
    
    return wrapper 