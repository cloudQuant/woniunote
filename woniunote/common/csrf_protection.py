"""
增强的 CSRF 保护模块
提供全面的跨站请求伪造防护
"""
import os
import hmac
import hashlib
import time
import secrets
import logging
from typing import Optional, Dict, Any
from functools import wraps
from flask import request, session, current_app, jsonify, abort
from werkzeug.exceptions import Forbidden

logger = logging.getLogger(__name__)

class CSRFProtection:
    """CSRF 保护管理器"""
    
    def __init__(self, app=None, secret_key=None):
        self.app = app
        self.secret_key = secret_key or self._generate_secret_key()
        self.token_timeout = 3600  # 1小时
        self.token_length = 32
        self.exempt_views = set()
        self.exempt_blueprints = set()
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """初始化应用"""
        app.config.setdefault('CSRF_ENABLED', True)
        app.config.setdefault('CSRF_TOKEN_TIMEOUT', 3600)
        app.config.setdefault('CSRF_TOKEN_LENGTH', 32)
        app.config.setdefault('CSRF_HEADER_NAME', 'X-CSRFToken')
        app.config.setdefault('CSRF_FIELD_NAME', 'csrf_token')
        
        # 注册请求处理器
        app.before_request(self._before_request)
        app.context_processor(self._context_processor)
        
        # 将保护器实例附加到应用
        app.csrf = self
    
    def _generate_secret_key(self) -> str:
        """生成密钥"""
        return secrets.token_hex(32)
    
    def generate_csrf_token(self) -> str:
        """生成CSRF令牌"""
        timestamp = str(int(time.time()))
        token_data = f"{timestamp}:{secrets.token_hex(16)}"
        
        # 使用HMAC签名
        signature = hmac.new(
            self.secret_key.encode(),
            token_data.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return f"{token_data}:{signature}"
    
    def _get_token_key(self) -> str:
        """获取当前会话的令牌密钥"""
        if 'csrf_token_key' not in session:
            session['csrf_token_key'] = secrets.token_hex(16)
        return session['csrf_token_key']
    
    def generate_token(self) -> str:
        """生成 CSRF 令牌"""
        token_key = self._get_token_key()
        timestamp = str(int(time.time()))
        
        # 创建令牌数据
        token_data = f"{token_key}:{timestamp}"
        
        # 使用 HMAC 签名
        signature = hmac.new(
            self.secret_key.encode(),
            token_data.encode(),
            hashlib.sha256
        ).hexdigest()
        
        token = f"{token_data}:{signature}"
        
        # Base64 编码使其 URL 安全
        import base64
        encoded_token = base64.urlsafe_b64encode(token.encode()).decode().rstrip('=')
        
        logger.debug("生成新的 CSRF 令牌")
        return encoded_token
    
    def validate_token(self, token: str) -> bool:
        """验证 CSRF 令牌"""
        if not token:
            return False
        
        try:
            # Base64 解码
            import base64
            # 添加必要的填充
            token += '=' * (4 - len(token) % 4)
            decoded_token = base64.urlsafe_b64decode(token.encode()).decode()
            
            # 解析令牌
            parts = decoded_token.split(':')
            if len(parts) != 3:
                return False
            
            token_key, timestamp, signature = parts
            
            # 验证时间戳
            token_time = int(timestamp)
            current_time = int(time.time())
            if current_time - token_time > self.token_timeout:
                logger.warning("CSRF 令牌已过期")
                return False
            
            # 验证会话密钥
            session_key = session.get('csrf_token_key')
            if not session_key or token_key != session_key:
                logger.warning("CSRF 令牌会话密钥不匹配")
                return False
            
            # 验证签名
            expected_data = f"{token_key}:{timestamp}"
            expected_signature = hmac.new(
                self.secret_key.encode(),
                expected_data.encode(),
                hashlib.sha256
            ).hexdigest()
            
            if not hmac.compare_digest(signature, expected_signature):
                logger.warning("CSRF 令牌签名验证失败")
                return False
            
            return True
            
        except (ValueError, TypeError) as e:
            logger.warning(f"CSRF 令牌格式错误: {e}")
            return False
    
    def _get_token_from_request(self) -> Optional[str]:
        """从请求中获取 CSRF 令牌"""
        # 1. 从表单字段获取
        token = request.form.get(current_app.config['CSRF_FIELD_NAME'])
        if token:
            return token
        
        # 2. 从请求头获取
        token = request.headers.get(current_app.config['CSRF_HEADER_NAME'])
        if token:
            return token
        
        # 3. 从查询参数获取（不推荐，但提供兼容性）
        token = request.args.get(current_app.config['CSRF_FIELD_NAME'])
        if token:
            return token
        
        return None
    
    def _should_check_csrf(self) -> bool:
        """判断是否需要检查 CSRF"""
        # CSRF 功能未启用
        if not current_app.config.get('CSRF_ENABLED', True):
            return False
        
        # 安全的方法不需要检查
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return False
        
        # 检查视图是否被豁免
        endpoint = request.endpoint
        if endpoint in self.exempt_views:
            return False
        
        # 特殊豁免：登录路由
        if endpoint == 'user.login':
            return False
        
        # 检查蓝图是否被豁免
        if endpoint and '.' in endpoint:
            blueprint = endpoint.split('.')[0]
            if blueprint in self.exempt_blueprints:
                return False
        
        return True
    
    def _before_request(self):
        """请求前处理"""
        if not self._should_check_csrf():
            return
        
        token = self._get_token_from_request()
        
        if not token:
            logger.warning(f"缺少 CSRF 令牌: {request.endpoint}")
            self._handle_csrf_error("缺少 CSRF 令牌")
            return
        
        if not self.validate_token(token):
            logger.warning(f"CSRF 令牌验证失败: {request.endpoint}")
            self._handle_csrf_error("CSRF 令牌无效")
            return
    
    def _handle_csrf_error(self, message: str):
        """处理 CSRF 错误"""
        # 记录安全日志
        logger.warning(f"CSRF 攻击尝试: endpoint={request.endpoint}, method={request.method}, "
                      f"remote_addr={request.remote_addr}, user_agent={request.user_agent.string}, "
                      f"referer={request.referrer}, message={message}")
        
        # 根据请求类型返回不同响应
        if request.is_json or 'application/json' in request.headers.get('Accept', ''):
            response = jsonify({
                'error': 'CSRF token missing or invalid',
                'message': message,
                'code': 'CSRF_ERROR'
            })
            response.status_code = 403
            abort(response)
        else:
            abort(403, description=message)
    
    def _context_processor(self):
        """模板上下文处理器"""
        return {
            'csrf_token': self.get_token,
            'csrf_token_field': self._csrf_token_field
        }
    
    def get_token(self) -> str:
        """获取当前 CSRF 令牌"""
        if 'csrf_token' not in session:
            session['csrf_token'] = self.generate_token()
        return session['csrf_token']
    
    def _csrf_token_field(self) -> str:
        """生成 CSRF 令牌隐藏字段 HTML"""
        token = self.get_token()
        field_name = current_app.config['CSRF_FIELD_NAME']
        return f'<input type="hidden" name="{field_name}" value="{token}"/>'
    
    def exempt(self, view_or_blueprint):
        """豁免装饰器"""
        if isinstance(view_or_blueprint, str):
            # 蓝图名称
            self.exempt_blueprints.add(view_or_blueprint)
            return view_or_blueprint
        else:
            # 视图函数
            if hasattr(view_or_blueprint, '__name__'):
                self.exempt_views.add(view_or_blueprint.__name__)
            return view_or_blueprint

# 全局 CSRF 保护实例
csrf = CSRFProtection()

def csrf_protect(f):
    """CSRF 保护装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_app.config.get('CSRF_ENABLED', True):
            # 检查请求方法
            if request.method in ('POST', 'PUT', 'DELETE', 'PATCH'):
                token = csrf._get_token_from_request()
                if not token or not csrf.validate_token(token):
                    csrf._handle_csrf_error("CSRF 令牌验证失败")
        
        return f(*args, **kwargs)
    
    return decorated_function

def csrf_exempt(f):
    """CSRF 豁免装饰器"""
    csrf.exempt_views.add(f.__name__)
    # Also add the qualified endpoint name
    csrf.exempt_views.add(f.__qualname__)
    return f

def require_csrf_token(f):
    """强制要求 CSRF 令牌的装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = csrf._get_token_from_request()
        if not token or not csrf.validate_token(token):
            csrf._handle_csrf_error("此操作需要有效的 CSRF 令牌")
        return f(*args, **kwargs)
    
    return decorated_function

# 便捷函数
def get_csrf_token() -> str:
    """获取当前 CSRF 令牌"""
    return csrf.get_token()

def validate_csrf_token(token: str) -> bool:
    """验证 CSRF 令牌"""
    return csrf.validate_token(token)

def generate_csrf_field() -> str:
    """生成 CSRF 令牌表单字段"""
    return csrf._csrf_token_field()

def generate_csrf_token() -> str:
    """生成新的 CSRF 令牌 (用于验证脚本)"""
    return csrf.generate_csrf_token()

class CSRFError(Forbidden):
    """CSRF 错误异常"""
    description = 'CSRF token missing or invalid'