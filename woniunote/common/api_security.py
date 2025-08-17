"""
API 安全模块
提供 API 认证、授权、限流等安全功能
"""
import time
import jwt
import hashlib
import logging
from typing import Dict, Any, Optional, List, Callable
from functools import wraps
from flask import request, jsonify, current_app, g
from werkzeug.exceptions import Unauthorized, Forbidden, TooManyRequests

logger = logging.getLogger(__name__)

class APIRateLimiter:
    """API 限流器"""
    
    def __init__(self, redis_client=None):
        self.redis_client = redis_client
        self.memory_cache = {}
        self.cleanup_interval = 60  # 清理间隔（秒）
        self.last_cleanup = time.time()
    
    def _get_client_id(self) -> str:
        """获取客户端标识"""
        # 优先使用认证用户ID
        if hasattr(g, 'current_user') and g.current_user:
            return f"user:{g.current_user.get('user_id', 'unknown')}"
        
        # 使用IP地址
        client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        if ',' in client_ip:
            client_ip = client_ip.split(',')[0].strip()
        
        return f"ip:{client_ip}"
    
    def _cleanup_memory_cache(self):
        """清理内存缓存"""
        current_time = time.time()
        if current_time - self.last_cleanup < self.cleanup_interval:
            return
        
        expired_keys = []
        for key, data in self.memory_cache.items():
            if current_time > data['reset_time']:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.memory_cache[key]
        
        self.last_cleanup = current_time
    
    def is_allowed(self, limit: int, window: int, key_suffix: str = "") -> tuple:
        """
        检查是否允许请求
        
        Args:
            limit: 限制次数
            window: 时间窗口（秒）
            key_suffix: 键后缀
            
        Returns:
            (allowed, remaining, reset_time)
        """
        client_id = self._get_client_id()
        key = f"rate_limit:{client_id}:{key_suffix}" if key_suffix else f"rate_limit:{client_id}"
        
        current_time = time.time()
        
        if self.redis_client:
            return self._check_redis_limit(key, limit, window, current_time)
        else:
            return self._check_memory_limit(key, limit, window, current_time)
    
    def _check_redis_limit(self, key: str, limit: int, window: int, current_time: float) -> tuple:
        """Redis 限流检查"""
        try:
            pipe = self.redis_client.pipeline()
            pipe.multi()
            
            # 使用滑动窗口算法
            window_start = current_time - window
            
            # 清除过期记录
            pipe.zremrangebyscore(key, 0, window_start)
            
            # 添加当前请求
            pipe.zadd(key, {str(current_time): current_time})
            
            # 获取当前窗口内的请求数
            pipe.zcard(key)
            
            # 设置过期时间
            pipe.expire(key, window + 1)
            
            results = pipe.execute()
            count = results[2]
            
            remaining = max(0, limit - count)
            reset_time = int(current_time + window)
            
            return count <= limit, remaining, reset_time
            
        except Exception as e:
            logger.error(f"Redis 限流检查失败: {e}")
            # Redis 失败时允许请求，但记录日志
            return True, limit, int(current_time + window)
    
    def _check_memory_limit(self, key: str, limit: int, window: int, current_time: float) -> tuple:
        """内存限流检查"""
        self._cleanup_memory_cache()
        
        if key not in self.memory_cache:
            self.memory_cache[key] = {
                'requests': [],
                'reset_time': current_time + window
            }
        
        data = self.memory_cache[key]
        
        # 清除过期请求
        window_start = current_time - window
        data['requests'] = [req_time for req_time in data['requests'] if req_time > window_start]
        
        # 添加当前请求
        data['requests'].append(current_time)
        
        count = len(data['requests'])
        remaining = max(0, limit - count)
        reset_time = int(current_time + window)
        
        return count <= limit, remaining, reset_time

class APIKeyAuth:
    """API Key 认证"""
    
    def __init__(self, redis_client=None):
        self.redis_client = redis_client
        self.api_keys = {}  # 内存缓存
    
    def generate_api_key(self, user_id: int, name: str = "", permissions: List[str] = None) -> str:
        """生成 API Key"""
        import secrets
        
        api_key = f"wn_{secrets.token_urlsafe(32)}"
        
        key_data = {
            'user_id': user_id,
            'name': name,
            'permissions': permissions or [],
            'created_at': time.time(),
            'last_used': None,
            'usage_count': 0
        }
        
        # 存储到 Redis 或内存
        if self.redis_client:
            try:
                import json
                self.redis_client.setex(
                    f"api_key:{api_key}", 
                    86400 * 365,  # 1年过期
                    json.dumps(key_data, default=str)
                )
            except Exception as e:
                logger.error(f"API Key 存储失败: {e}")
        else:
            self.api_keys[api_key] = key_data
        
        logger.info(f"生成新的 API Key: user_id={user_id}, name={name}")
        return api_key
    
    def validate_api_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        """验证 API Key"""
        if not api_key or not api_key.startswith('wn_'):
            return None
        
        key_data = None
        
        # 从 Redis 或内存获取
        if self.redis_client:
            try:
                import json
                cached_data = self.redis_client.get(f"api_key:{api_key}")
                if cached_data:
                    key_data = json.loads(cached_data)
            except Exception as e:
                logger.error(f"API Key 验证失败: {e}")
        else:
            key_data = self.api_keys.get(api_key)
        
        if not key_data:
            return None
        
        # 更新使用统计
        key_data['last_used'] = time.time()
        key_data['usage_count'] = key_data.get('usage_count', 0) + 1
        
        # 更新缓存
        if self.redis_client:
            try:
                import json
                self.redis_client.setex(
                    f"api_key:{api_key}",
                    86400 * 365,
                    json.dumps(key_data, default=str)
                )
            except Exception:
                pass
        
        return key_data
    
    def revoke_api_key(self, api_key: str) -> bool:
        """撤销 API Key"""
        if self.redis_client:
            try:
                result = self.redis_client.delete(f"api_key:{api_key}")
                return result > 0
            except Exception as e:
                logger.error(f"API Key 撤销失败: {e}")
                return False
        else:
            return self.api_keys.pop(api_key, None) is not None

class JWTManager:
    """JWT 令牌管理"""
    
    def __init__(self, secret_key: str, algorithm: str = 'HS256'):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.default_expiry = 3600  # 1小时
    
    def generate_token(self, payload: Dict[str, Any], expires_in: int = None) -> str:
        """生成 JWT 令牌"""
        if expires_in is None:
            expires_in = self.default_expiry
        
        payload = payload.copy()
        payload['exp'] = time.time() + expires_in
        payload['iat'] = time.time()
        
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def validate_token(self, token: str) -> Optional[Dict[str, Any]]:
        """验证 JWT 令牌"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("JWT 令牌已过期")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"JWT 令牌无效: {e}")
            return None

# 全局实例
try:
    from woniunote.common.redisdb import get_redis_client
    redis_client = get_redis_client()
except ImportError:
    redis_client = None

rate_limiter = APIRateLimiter(redis_client)
api_key_auth = APIKeyAuth(redis_client)

def rate_limit(limit: int = 100, window: int = 3600, key_suffix: str = ""):
    """
    限流装饰器
    
    Args:
        limit: 限制次数
        window: 时间窗口（秒）
        key_suffix: 键后缀，用于区分不同端点
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            allowed, remaining, reset_time = rate_limiter.is_allowed(limit, window, key_suffix)
            
            if not allowed:
                logger.warning(f"限流触发: {request.endpoint}, client: {rate_limiter._get_client_id()}")
                
                response = jsonify({
                    'error': 'Rate limit exceeded',
                    'message': f'Too many requests. Limit: {limit} per {window} seconds',
                    'retry_after': reset_time - int(time.time())
                })
                response.status_code = 429
                response.headers['X-RateLimit-Limit'] = str(limit)
                response.headers['X-RateLimit-Remaining'] = str(remaining)
                response.headers['X-RateLimit-Reset'] = str(reset_time)
                response.headers['Retry-After'] = str(reset_time - int(time.time()))
                
                return response
            
            # 添加限流头
            result = f(*args, **kwargs)
            if hasattr(result, 'headers'):
                result.headers['X-RateLimit-Limit'] = str(limit)
                result.headers['X-RateLimit-Remaining'] = str(remaining)
                result.headers['X-RateLimit-Reset'] = str(reset_time)
            
            return result
        
        return decorated_function
    return decorator

def require_api_key(permissions: List[str] = None):
    """
    API Key 认证装饰器
    
    Args:
        permissions: 所需权限列表
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 从头部获取 API Key
            api_key = request.headers.get('X-API-Key')
            if not api_key:
                api_key = request.args.get('api_key')
            
            if not api_key:
                return jsonify({'error': 'API Key required'}), 401
            
            # 验证 API Key
            key_data = api_key_auth.validate_api_key(api_key)
            if not key_data:
                return jsonify({'error': 'Invalid API Key'}), 401
            
            # 检查权限
            if permissions:
                user_permissions = key_data.get('permissions', [])
                if not any(perm in user_permissions for perm in permissions):
                    return jsonify({'error': 'Insufficient permissions'}), 403
            
            # 将用户信息添加到 g
            g.current_user = key_data
            g.api_authenticated = True
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator

def require_jwt_token():
    """JWT 令牌认证装饰器"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            auth_header = request.headers.get('Authorization')
            if not auth_header or not auth_header.startswith('Bearer '):
                return jsonify({'error': 'JWT token required'}), 401
            
            token = auth_header.split(' ')[1]
            
            jwt_manager = JWTManager(current_app.config['SECRET_KEY'])
            payload = jwt_manager.validate_token(token)
            
            if not payload:
                return jsonify({'error': 'Invalid or expired token'}), 401
            
            g.current_user = payload
            g.jwt_authenticated = True
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator

def api_response(data: Any = None, message: str = "", status: int = 200, 
                errors: List[str] = None) -> tuple:
    """
    标准化 API 响应格式
    
    Args:
        data: 响应数据
        message: 响应消息
        status: HTTP 状态码
        errors: 错误列表
        
    Returns:
        (response, status_code)
    """
    response = {
        'success': status < 400,
        'status': status,
        'message': message,
        'timestamp': int(time.time())
    }
    
    if data is not None:
        response['data'] = data
    
    if errors:
        response['errors'] = errors
    
    # 添加请求追踪ID
    if hasattr(g, 'request_id'):
        response['request_id'] = g.request_id
    
    return jsonify(response), status

def validate_content_type(allowed_types: List[str] = ['application/json']):
    """验证请求内容类型装饰器"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            content_type = request.headers.get('Content-Type', '')
            
            if not any(allowed_type in content_type for allowed_type in allowed_types):
                return api_response(
                    message=f"Content-Type must be one of: {', '.join(allowed_types)}",
                    status=415
                )
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator

def log_api_access():
    """API 访问日志装饰器"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            start_time = time.time()
            
            # 记录请求
            logger.info(f"API 请求: {request.method} {request.path}", extra={
                'endpoint': request.endpoint,
                'method': request.method,
                'path': request.path,
                'remote_addr': request.remote_addr,
                'user_agent': request.user_agent.string,
                'authenticated': hasattr(g, 'current_user')
            })
            
            try:
                result = f(*args, **kwargs)
                duration = time.time() - start_time
                
                # 记录响应
                status_code = result[1] if isinstance(result, tuple) else 200
                logger.info(f"API 响应: {status_code}, 耗时: {duration:.3f}s")
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                logger.error(f"API 错误: {str(e)}, 耗时: {duration:.3f}s")
                raise
        
        return decorated_function
    return decorator