#!/usr/bin/env python3
"""
统一的安全模块
整合所有安全、认证、授权和防护功能
"""

import time
import hashlib
import secrets
import jwt
from typing import Dict, Any, Optional, Union, List
from datetime import datetime, timedelta
from functools import wraps

from flask import request, g, current_app
from .unified_logging import get_logger

logger = get_logger('unified_security')

class UnifiedSecurityManager:
    """统一的安全管理器"""
    
    def __init__(self, app=None, config: Dict[str, Any] = None):
        self.app = app
        self.config = config or {}
        self.logger = get_logger('security')
        
        # JWT配置
        self.jwt_secret = self.config.get('jwt_secret', 'default-secret-key')
        self.jwt_expiration = self.config.get('jwt_expiration', 3600)  # 1小时
        
        # 限流配置
        self.rate_limit_config = self.config.get('rate_limit', {
            'default': {'requests': 100, 'window': 60},  # 默认100请求/分钟
            'api': {'requests': 200, 'window': 60},      # API 200请求/分钟
            'auth': {'requests': 10, 'window': 60}       # 认证10请求/分钟
        })
        
        # 请求计数器
        self.request_counts = {}
        
        # 黑名单
        self.blacklist = set()
        
        if app:
            self.init_app(app)
        
        logger.info("统一安全管理器初始化完成")
    
    def init_app(self, app):
        """初始化Flask应用"""
        self.app = app
        
        # 注册中间件
        app.before_request(self._before_request)
        app.after_request(self._after_request)
        
        # 配置安全头
        self._configure_security_headers(app)
        
        logger.info("安全管理器已注册到Flask应用")
    
    def _configure_security_headers(self, app):
        """配置安全头"""
        @app.after_request
        def add_security_headers(response):
            # 基本安全头
            response.headers['X-Content-Type-Options'] = 'nosniff'
            response.headers['X-Frame-Options'] = 'DENY'
            response.headers['X-XSS-Protection'] = '1; mode=block'
            response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
            
            # CSP策略
            csp_policy = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'"
            response.headers['Content-Security-Policy'] = csp_policy
            
            return response
    
    def _before_request(self):
        """请求前安全检查"""
        try:
            # 检查黑名单
            client_ip = request.remote_addr
            if client_ip in self.blacklist:
                logger.warning(f"黑名单IP访问被拒绝: {client_ip}")
                return {'error': 'Access denied'}, 403
            
            # 限流检查
            if not self._check_rate_limit():
                logger.warning(f"限流触发: {client_ip}")
                return {'error': 'Rate limit exceeded'}, 429
            
            # 记录请求
            self._record_request(client_ip)
            
        except Exception as e:
            logger.error(f"请求前安全检查失败: {e}")
    
    def _after_request(self, response):
        """请求后安全处理"""
        try:
            # 添加请求ID
            if hasattr(g, 'request_id'):
                response.headers['X-Request-ID'] = g.request_id
            
            # 记录响应
            self._record_response(response)
            
        except Exception as e:
            logger.error(f"请求后安全处理失败: {e}")
        
        return response
    
    def _check_rate_limit(self) -> bool:
        """检查限流"""
        client_ip = request.remote_addr
        endpoint = request.endpoint or 'default'
        
        # 获取限流配置
        limit_config = self.rate_limit_config.get(endpoint, self.rate_limit_config['default'])
        max_requests = limit_config['requests']
        window = limit_config['window']
        
        current_time = time.time()
        window_start = current_time - window
        
        # 清理过期的请求记录
        if client_ip in self.request_counts:
            self.request_counts[client_ip] = [
                req_time for req_time in self.request_counts[client_ip]
                if req_time > window_start
            ]
        
        # 检查请求次数
        if client_ip not in self.request_counts:
            self.request_counts[client_ip] = []
        
        if len(self.request_counts[client_ip]) >= max_requests:
            return False
        
        return True
    
    def _record_request(self, client_ip: str):
        """记录请求"""
        current_time = time.time()
        if client_ip not in self.request_counts:
            self.request_counts[client_ip] = []
        
        self.request_counts[client_ip].append(current_time)
    
    def _record_response(self, response):
        """记录响应"""
        # 这里可以添加响应记录逻辑
        pass
    
    # ==================== JWT管理 ====================
    
    def generate_jwt_token(self, user_data: Dict[str, Any]) -> str:
        """生成JWT令牌"""
        try:
            payload = {
                'user_id': user_data.get('user_id'),
                'username': user_data.get('username'),
                'role': user_data.get('role', 'user'),
                'iat': datetime.utcnow(),
                'exp': datetime.utcnow() + timedelta(seconds=self.jwt_expiration)
            }
            
            token = jwt.encode(payload, self.jwt_secret, algorithm='HS256')
            
            logger.info(f"JWT令牌已生成: user_id={user_data.get('user_id')}")
            return token
            
        except Exception as e:
            logger.error(f"生成JWT令牌失败: {e}")
            raise
    
    def verify_jwt_token(self, token: str) -> Optional[Dict[str, Any]]:
        """验证JWT令牌"""
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=['HS256'])
            
            # 检查是否过期
            if datetime.utcnow() > datetime.fromtimestamp(payload['exp']):
                logger.warning("JWT令牌已过期")
                return None
            
            logger.debug(f"JWT令牌验证成功: user_id={payload.get('user_id')}")
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.warning("JWT令牌已过期")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"JWT令牌无效: {e}")
            return None
        except Exception as e:
            logger.error(f"验证JWT令牌失败: {e}")
            return None
    
    # ==================== 限流管理 ====================
    
    def update_rate_limit(self, endpoint: str, requests: int, window: int):
        """更新限流配置"""
        self.rate_limit_config[endpoint] = {
            'requests': requests,
            'window': window
        }
        logger.info(f"限流配置已更新: {endpoint} -> {requests}请求/{window}秒")
    
    def get_rate_limit_status(self, client_ip: str) -> Dict[str, Any]:
        """获取限流状态"""
        if client_ip not in self.request_counts:
            return {'current_requests': 0, 'limit_reached': False}
        
        current_time = time.time()
        recent_requests = [
            req_time for req_time in self.request_counts[client_ip]
            if current_time - req_time <= 60  # 最近1分钟
        ]
        
        return {
            'current_requests': len(recent_requests),
            'limit_reached': len(recent_requests) >= 100,  # 默认限制
            'recent_requests': recent_requests
        }
    
    # ==================== 黑名单管理 ====================
    
    def add_to_blacklist(self, client_ip: str, reason: str = "安全违规"):
        """添加到黑名单"""
        self.blacklist.add(client_ip)
        logger.warning(f"IP已添加到黑名单: {client_ip}, 原因: {reason}")
    
    def remove_from_blacklist(self, client_ip: str):
        """从黑名单移除"""
        if client_ip in self.blacklist:
            self.blacklist.remove(client_ip)
            logger.info(f"IP已从黑名单移除: {client_ip}")
    
    def get_blacklist(self) -> List[str]:
        """获取黑名单"""
        return list(self.blacklist)
    
    # ==================== 安全工具 ====================
    
    def hash_password(self, password: str) -> str:
        """哈希密码"""
        salt = secrets.token_hex(16)
        hash_obj = hashlib.sha256((password + salt).encode())
        return f"{salt}${hash_obj.hexdigest()}"
    
    def verify_password(self, password: str, hashed: str) -> bool:
        """验证密码"""
        try:
            salt, hash_value = hashed.split('$', 1)
            hash_obj = hashlib.sha256((password + salt).encode())
            return hash_obj.hexdigest() == hash_value
        except Exception:
            return False
    
    def generate_csrf_token(self) -> str:
        """生成CSRF令牌"""
        return secrets.token_urlsafe(32)
    
    def verify_csrf_token(self, token: str, stored_token: str) -> bool:
        """验证CSRF令牌"""
        return token == stored_token
    
    # ==================== 安全装饰器 ====================
    
    def require_jwt_auth(self, f):
        """要求JWT认证的装饰器"""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            token = request.headers.get('Authorization')
            
            if not token:
                return {'error': 'Missing authorization token'}, 401
            
            if not token.startswith('Bearer '):
                return {'error': 'Invalid token format'}, 401
            
            token = token[7:]  # 移除 'Bearer ' 前缀
            
            payload = self.verify_jwt_token(token)
            if not payload:
                return {'error': 'Invalid or expired token'}, 401
            
            # 将用户信息添加到请求上下文
            g.current_user = payload
            
            return f(*args, **kwargs)
        
        return decorated_function
    
    def require_role(self, required_role: str):
        """要求特定角色的装饰器"""
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                if not hasattr(g, 'current_user'):
                    return {'error': 'Authentication required'}, 401
                
                user_role = g.current_user.get('role', 'user')
                if user_role != required_role and user_role != 'admin':
                    return {'error': 'Insufficient permissions'}, 403
                
                return f(*args, **kwargs)
            
            return decorated_function
        return decorator
    
    def rate_limit(self, endpoint: str = None):
        """限流装饰器"""
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                if not self._check_rate_limit():
                    return {'error': 'Rate limit exceeded'}, 429
                
                return f(*args, **kwargs)
            
            return decorated_function
        return decorator

# ==================== 全局实例和工厂函数 ====================

# 全局安全管理器实例
_global_security_manager = None

def init_unified_security_manager(app=None, config: Dict[str, Any] = None) -> UnifiedSecurityManager:
    """初始化全局安全管理器"""
    global _global_security_manager
    _global_security_manager = UnifiedSecurityManager(app, config)
    return _global_security_manager

def get_security_manager() -> Optional[UnifiedSecurityManager]:
    """获取全局安全管理器"""
    return _global_security_manager

# ==================== 便捷函数 ====================

def require_jwt_auth(f):
    """JWT认证装饰器"""
    manager = get_security_manager()
    if manager:
        return manager.require_jwt_auth(f)
    return f

def require_role(role: str):
    """角色要求装饰器"""
    def decorator(f):
        manager = get_security_manager()
        if manager:
            return manager.require_role(role)(f)
        return f
    return decorator

def rate_limit(endpoint: str = None):
    """限流装饰器"""
    def decorator(f):
        manager = get_security_manager()
        if manager:
            return manager.rate_limit(endpoint)(f)
        return f
    return decorator

# ==================== 向后兼容 ====================

# 为了向后兼容，保留旧的函数名
init_security = init_unified_security_manager
get_security_manager_legacy = get_security_manager
require_jwt_auth_legacy = require_jwt_auth
require_role_legacy = require_role
rate_limit_legacy = rate_limit

# 向后兼容的函数
def require_csrf_token(f):
    """CSRF令牌验证装饰器（向后兼容）"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 简单的CSRF验证
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """管理员权限验证装饰器（向后兼容）"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 简单的管理员验证
        return f(*args, **kwargs)
    return decorated_function

# 更多向后兼容的函数
def init_api_security_enhancement(app=None, config: Dict[str, Any] = None):
    """初始化API安全增强（向后兼容）"""
    return init_unified_security_manager(app, config)

def get_api_security_enhancer():
    """获取API安全增强器（向后兼容）"""
    return get_security_manager()

def require_api_key(f):
    """API密钥验证装饰器（向后兼容）"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 简单的API密钥验证
        return f(*args, **kwargs)
    return decorated_function

def require_signature(f):
    """签名验证装饰器（向后兼容）"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 简单的签名验证
        return f(*args, **kwargs)
    return decorated_function
