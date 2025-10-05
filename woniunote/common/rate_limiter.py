'''
API限流工具 - 支持多种限流算法
'''

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
    def __init__(self, max_requests: int, window_size: int = 60):
        self.max_requests = max_requests
        self.window_size = window_size
        self.requests: Dict[str, deque] = defaultdict(deque)
        self.lock = Lock()
    
    def is_allowed(self, key: str) -> Tuple[bool, Dict[str, any]]:
        current_time = time.time()
        with self.lock:
            request_times = self.requests[key]
            while request_times and current_time - request_times[0] > self.window_size:
                request_times.popleft()
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
    def __init__(self, capacity: int, refill_rate: float, refill_period: int = 1):
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.refill_period = refill_period
        self.buckets: Dict[str, Dict] = defaultdict(lambda: {
            'tokens': capacity,
            'last_refill': time.time()
        })
        self.lock = Lock()
    
    def _refill_bucket(self, bucket: Dict) -> None:
        current_time = time.time()
        time_passed = current_time - bucket['last_refill']
        if time_passed >= self.refill_period:
            periods = int(time_passed / self.refill_period)
            tokens_to_add = periods * self.refill_rate
            bucket['tokens'] = min(self.capacity, bucket['tokens'] + tokens_to_add)
            bucket['last_refill'] = current_time
    
    def is_allowed(self, key: str, tokens_required: int = 1) -> Tuple[bool, Dict[str, any]]:
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
    def __init__(self, default_limiter=None, max_calls=None, period=None):
        self.limiters: Dict[str, any] = {}
        if max_calls is not None and period is not None:
            self.default_limiter = SlidingWindowLimiter(max_calls, period)
        else:
            self.default_limiter = default_limiter or SlidingWindowLimiter(100000, 60)
        self.global_limiter = SlidingWindowLimiter(5000000, 60)
    
    def add_limiter(self, name: str, limiter) -> None:
        self.limiters[name] = limiter
    
    def get_limiter(self, name: str):
        return self.limiters.get(name, self.default_limiter)
    
    def check_rate_limit(self, key: str, limiter_name: str = None) -> Tuple[bool, Dict[str, any]]:
        limiter = self.get_limiter(limiter_name) if limiter_name else self.default_limiter
        return limiter.is_allowed(key)
    
    def check_global_limit(self, key: str) -> Tuple[bool, Dict[str, any]]:
        return self.global_limiter.is_allowed(key)
    
    def is_allowed(self, key: str) -> bool:
        result = self.default_limiter.is_allowed(key)
        if isinstance(result, tuple):
            return result[0]
        return result

def get_client_key(request) -> str:
    if hasattr(g, 'user_id') and g.user_id:
        return f"user:{g.user_id}"
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    if client_ip and ',' in client_ip:
        client_ip = client_ip.split(',')[0].strip()
    user_agent = request.headers.get('User-Agent', '')
    user_agent_hash = hashlib.md5(user_agent.encode()).hexdigest()[:8]
    return f"ip:{client_ip}:{user_agent_hash}"

def create_rate_limit_response(limit_info: Dict[str, any]) -> tuple:
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

_global_rate_limiter = None

def get_rate_limiter() -> RateLimiter:
    global _global_rate_limiter
    if _global_rate_limiter is None:
        _global_rate_limiter = RateLimiter()
        _global_rate_limiter.add_limiter('strict', SlidingWindowLimiter(500000, 60))
        _global_rate_limiter.add_limiter('moderate', SlidingWindowLimiter(1500000, 60))
        _global_rate_limiter.add_limiter('lenient', SlidingWindowLimiter(5000000, 60))
        _global_rate_limiter.add_limiter('api', TokenBucketLimiter(1000000, 200000, 1))
        _global_rate_limiter.add_limiter('upload', TokenBucketLimiter(100000, 20000, 10))
    return _global_rate_limiter

def rate_limit(limit_type: str = 'default', key_func: Optional[Callable] = None):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            rate_limiter = get_rate_limiter()
            if key_func:
                key = key_func()
            else:
                key = get_client_key(request)
            global_allowed, global_info = rate_limiter.check_global_limit(key)
            if not global_allowed:
                logger.warning(f"Global rate limit exceeded for key: {key}")
                return create_rate_limit_response(global_info)
            allowed, limit_info = rate_limiter.check_rate_limit(key, limit_type)
            if not allowed:
                logger.warning(f"Rate limit exceeded for key: {key}, type: {limit_type}")
                return create_rate_limit_response(limit_info)
            try:
                response = func(*args, **kwargs)
                if isinstance(response, tuple) and len(response) >= 2:
                    data, status_code = response[0], response[1]
                    headers = response[2] if len(response) > 2 else {}
                elif hasattr(response, 'headers'):
                    headers = response.headers
                else:
                    return response
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
        if isinstance(config, dict):
            for name, rule in config.items():
                try:
                    if isinstance(rule, dict):
                        limiter_type = rule.get('type', 'sliding_window').lower()
                        if limiter_type == 'token_bucket':
                            capacity = rule.get('capacity')
                            refill_rate = rule.get('refill_rate')
                            refill_period = rule.get('refill_period')
                            
                            if capacity is None or refill_rate is None or refill_period is None:
                                # 使用默认值，不输出警告
                                capacity = 50 if capacity is None else capacity
                                refill_rate = 10 if refill_rate is None else refill_rate
                                refill_period = 1 if refill_period is None else refill_period
                            
                            limiter = TokenBucketLimiter(
                                capacity=int(capacity),
                                refill_rate=float(refill_rate),
                                refill_period=int(refill_period)
                            )
                        else:
                            max_requests = rule.get('max_requests')
                            window_size = rule.get('window_size')
                            
                            if max_requests is None or window_size is None:
                                # 使用默认值，不输出警告
                                max_requests = 100 if max_requests is None else max_requests
                                window_size = 60 if window_size is None else window_size
                            
                            limiter = SlidingWindowLimiter(
                                max_requests=int(max_requests),
                                window_size=int(window_size)
                            )
                        _global_rate_limiter.add_limiter(name, limiter)
                    elif isinstance(rule, str) and ' per ' in rule:
                        parts = rule.split(' ')
                        max_requests = int(parts[0])
                        period_unit = parts[2]
                        if "minute" in period_unit:
                            window_size = 60
                        elif "hour" in period_unit:
                            window_size = 3600
                        else:
                            window_size = 1
                        limiter = SlidingWindowLimiter(max_requests=max_requests, window_size=window_size)
                        _global_rate_limiter.add_limiter(name, limiter)
                    else:
                        logger.warning(f"限流配置 {name} 格式无效，使用默认值")
                except (ValueError, TypeError, IndexError) as e:
                    logger.warning(f"解析限流规则 '{name}' 失败: {e}，使用默认值")
        else:
            get_rate_limiter()
        logger.info("Rate limiter initialized successfully")
        return _global_rate_limiter
    except Exception as e:
        logger.error(f"Rate limiter initialization error: {repr(e)}")
        _global_rate_limiter = RateLimiter()
        return _global_rate_limiter

class IPWhitelist:
    def __init__(self, whitelist_ips=None):
        self.whitelist = set(whitelist_ips or [])
        self.lock = Lock()
    
    def add_ip(self, ip: str) -> None:
        with self.lock:
            self.whitelist.add(ip)
    
    def remove_ip(self, ip: str) -> None:
        with self.lock:
            self.whitelist.discard(ip)
    
    def is_whitelisted(self, ip: str) -> bool:
        with self.lock:
            return ip in self.whitelist
    
    def get_whitelist(self) -> set:
        with self.lock:
            return self.whitelist.copy()

_ip_whitelist = None

def get_ip_whitelist() -> IPWhitelist:
    global _ip_whitelist
    if _ip_whitelist is None:
        default_whitelist = ['127.0.0.1', '::1', 'localhost']
        _ip_whitelist = IPWhitelist(default_whitelist)
    return _ip_whitelist

def bypass_rate_limit_if_whitelisted(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        if client_ip and ',' in client_ip:
            client_ip = client_ip.split(',')[0].strip()
        whitelist = get_ip_whitelist()
        if whitelist.is_whitelisted(client_ip):
            logger.debug(f"Bypassing rate limit for whitelisted IP: {client_ip}")
            return args[0](*args[1:], **kwargs) if args else func(**kwargs)
        return func(*args, **kwargs)
    return wrapper
