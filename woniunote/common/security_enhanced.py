#!/usr/bin/env python3
"""
Phase 5 增强安全模块
提供JWT认证、CSRF保护、API安全、数据加密、审计日志等企业级安全功能
"""

import os
import jwt
import time
import hmac
import hashlib
import secrets
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Callable
from functools import wraps
from dataclasses import dataclass, asdict
from flask import request, session, current_app, g, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import ipaddress
import re
from enum import Enum
import threading

logger = logging.getLogger(__name__)

class SecurityLevel(Enum):
    """安全级别枚举"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ThreatType(Enum):
    """威胁类型枚举"""
    BRUTE_FORCE = "brute_force"
    SQL_INJECTION = "sql_injection"
    XSS = "xss"
    CSRF = "csrf"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    DATA_BREACH_ATTEMPT = "data_breach_attempt"

@dataclass
class SecurityEvent:
    """安全事件记录"""
    event_id: str
    timestamp: datetime
    event_type: ThreatType
    severity: SecurityLevel
    source_ip: str
    user_id: Optional[str]
    endpoint: str
    description: str
    details: Dict[str, Any]
    action_taken: str

class SecurityAuditLogger:
    """安全审计日志记录器"""
    
    def __init__(self):
        self.events = []
        self.max_events = 10000
        self.lock = threading.Lock()
        
        # 设置专门的安全日志文件
        self.security_logger = logging.getLogger('security_audit')
        handler = logging.FileHandler('security_audit.log')
        formatter = logging.Formatter(
            '%(asctime)s - SECURITY - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.security_logger.addHandler(handler)
        self.security_logger.setLevel(logging.INFO)
    
    def log_security_event(self, event: SecurityEvent):
        """记录安全事件"""
        with self.lock:
            self.events.append(event)
            if len(self.events) > self.max_events:
                self.events.pop(0)
        
        # 写入日志文件
        log_message = {
            'event_id': event.event_id,
            'timestamp': event.timestamp.isoformat(),
            'type': event.event_type.value,
            'severity': event.severity.value,
            'source_ip': event.source_ip,
            'user_id': event.user_id,
            'endpoint': event.endpoint,
            'description': event.description,
            'details': event.details,
            'action_taken': event.action_taken
        }
        
        if event.severity in [SecurityLevel.HIGH, SecurityLevel.CRITICAL]:
            self.security_logger.error(json.dumps(log_message))
        elif event.severity == SecurityLevel.MEDIUM:
            self.security_logger.warning(json.dumps(log_message))
        else:
            self.security_logger.info(json.dumps(log_message))
    
    def get_recent_events(self, hours: int = 24, severity: SecurityLevel = None) -> List[SecurityEvent]:
        """获取最近的安全事件"""
        with self.lock:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            filtered_events = [
                event for event in self.events
                if event.timestamp >= cutoff_time
            ]
            
            if severity:
                filtered_events = [
                    event for event in filtered_events
                    if event.severity == severity
                ]
            
            return sorted(filtered_events, key=lambda x: x.timestamp, reverse=True)

class DataEncryption:
    """数据加密工具"""
    
    def __init__(self, master_key: str = None):
        if master_key:
            self.master_key = master_key.encode()
        else:
            self.master_key = os.environ.get('MASTER_ENCRYPTION_KEY', 'default-key-change-me').encode()
        
        # 初始化Fernet加密器
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'salt_',
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(self.master_key))
        self.cipher_suite = Fernet(key)
    
    def encrypt_data(self, data: str) -> str:
        """加密数据"""
        try:
            encrypted_data = self.cipher_suite.encrypt(data.encode())
            return base64.urlsafe_b64encode(encrypted_data).decode()
        except Exception as e:
            logger.error(f"Data encryption error: {e}")
            raise
    
    def decrypt_data(self, encrypted_data: str) -> str:
        """解密数据"""
        try:
            decoded_data = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted_data = self.cipher_suite.decrypt(decoded_data)
            return decrypted_data.decode()
        except Exception as e:
            logger.error(f"Data decryption error: {e}")
            raise
    
    def encrypt_sensitive_fields(self, data: Dict[str, Any], sensitive_fields: List[str]) -> Dict[str, Any]:
        """加密敏感字段"""
        encrypted_data = data.copy()
        for field in sensitive_fields:
            if field in encrypted_data and encrypted_data[field]:
                encrypted_data[field] = self.encrypt_data(str(encrypted_data[field]))
        return encrypted_data
    
    def decrypt_sensitive_fields(self, data: Dict[str, Any], sensitive_fields: List[str]) -> Dict[str, Any]:
        """解密敏感字段"""
        decrypted_data = data.copy()
        for field in sensitive_fields:
            if field in decrypted_data and decrypted_data[field]:
                try:
                    decrypted_data[field] = self.decrypt_data(decrypted_data[field])
                except:
                    # 如果解密失败，可能是未加密的数据
                    pass
        return decrypted_data

class JWTManager:
    """JWT令牌管理器"""
    
    def __init__(self, secret_key: str = None, algorithm: str = 'HS256'):
        self.secret_key = secret_key or os.environ.get('JWT_SECRET_KEY', 'jwt-secret-change-me')
        self.algorithm = algorithm
        self.default_expires_in = 3600  # 1小时
        
        # 黑名单令牌存储
        self.blacklist = set()
        self.lock = threading.Lock()
    
    def generate_token(self, payload: Dict[str, Any], expires_in: int = None) -> str:
        """生成JWT令牌"""
        try:
            expires_in = expires_in or self.default_expires_in
            now = datetime.utcnow()
            
            token_payload = {
                'iat': now,
                'exp': now + timedelta(seconds=expires_in),
                'jti': secrets.token_urlsafe(16),  # 令牌ID，用于撤销
                **payload
            }
            
            token = jwt.encode(token_payload, self.secret_key, algorithm=self.algorithm)
            return token
            
        except Exception as e:
            logger.error(f"JWT token generation error: {e}")
            raise
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """验证JWT令牌"""
        try:
            # 检查黑名单
            with self.lock:
                if token in self.blacklist:
                    raise jwt.InvalidTokenError("Token is blacklisted")
            
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.warning("JWT token expired")
            raise
        except jwt.InvalidTokenError as e:
            logger.warning(f"JWT token invalid: {e}")
            raise
    
    def revoke_token(self, token: str):
        """撤销令牌"""
        with self.lock:
            self.blacklist.add(token)
    
    def cleanup_blacklist(self):
        """清理过期的黑名单令牌"""
        with self.lock:
            # 这里应该实现更智能的清理逻辑
            # 可以存储令牌的过期时间，只删除已过期的令牌
            pass

class CSRFProtection:
    """CSRF保护"""
    
    def __init__(self):
        self.tokens = {}
        self.token_lifetime = 3600  # 1小时
        self.lock = threading.Lock()
    
    def generate_csrf_token(self, session_id: str) -> str:
        """生成CSRF令牌"""
        token = secrets.token_urlsafe(32)
        
        with self.lock:
            self.tokens[session_id] = {
                'token': token,
                'created_at': time.time()
            }
        
        return token
    
    def validate_csrf_token(self, session_id: str, token: str) -> bool:
        """验证CSRF令牌"""
        with self.lock:
            if session_id not in self.tokens:
                return False
            
            stored_token = self.tokens[session_id]
            
            # 检查令牌是否过期
            if time.time() - stored_token['created_at'] > self.token_lifetime:
                del self.tokens[session_id]
                return False
            
            # 验证令牌
            return hmac.compare_digest(stored_token['token'], token)
    
    def cleanup_expired_tokens(self):
        """清理过期令牌"""
        with self.lock:
            current_time = time.time()
            expired_sessions = [
                session_id for session_id, data in self.tokens.items()
                if current_time - data['created_at'] > self.token_lifetime
            ]
            
            for session_id in expired_sessions:
                del self.tokens[session_id]

class InputValidator:
    """输入验证器"""
    
    def __init__(self):
        # XSS危险模式
        self.xss_patterns = [
            r'<script[^>]*>.*?</script>',
            r'javascript:',
            r'on\w+\s*=',
            r'<iframe[^>]*>.*?</iframe>',
            r'<object[^>]*>.*?</object>',
            r'<embed[^>]*>.*?</embed>',
            r'<form[^>]*>.*?</form>',
        ]
        
        # SQL注入模式
        self.sql_injection_patterns = [
            r"('|(\')|;|\-\-|\||\*|\%)",  # 修复不平衡的括号和转义字符
            r"((%3D)|(=))[^\n]*((%27)|(')|(%3B)|(;))",  # 修正转义字符
            r"\w*((%27)|(')|(%6F)|o|(%4F))((\%72)|r|(\%52))",
            r"((%27)|(\')|(%60))union",  # 添加反引号检测
            r"exec(\s|\+)+(s|x)p\w+",
            r"UNION[^a-zA-Z0-9]+(ALL\s+)?SELECT",
        ]
        
        self.compiled_xss_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.xss_patterns]
        self.compiled_sql_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.sql_injection_patterns]
    
    def validate_input(self, input_data: str, check_xss: bool = True, check_sql: bool = True) -> Dict[str, Any]:
        """验证输入数据"""
        result = {
            'is_safe': True,
            'threats': [],
            'sanitized_data': input_data
        }
        
        if check_xss:
            for pattern in self.compiled_xss_patterns:
                if pattern.search(input_data):
                    result['is_safe'] = False
                    result['threats'].append('XSS')
                    break
        
        if check_sql:
            for pattern in self.compiled_sql_patterns:
                if pattern.search(input_data):
                    result['is_safe'] = False
                    result['threats'].append('SQL_INJECTION')
                    break
        
        # 基本清理
        if not result['is_safe']:
            sanitized = input_data
            for pattern in self.compiled_xss_patterns:
                sanitized = pattern.sub('', sanitized)
            result['sanitized_data'] = sanitized
        
        return result
    
    def validate_email(self, email: str) -> bool:
        """验证邮箱格式"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    def validate_password_strength(self, password: str) -> Dict[str, Any]:
        """验证密码强度"""
        result = {
            'is_strong': True,
            'score': 0,
            'requirements': [],
            'suggestions': []
        }
        
        # 长度检查
        if len(password) >= 12:
            result['score'] += 2
        elif len(password) >= 8:
            result['score'] += 1
        else:
            result['is_strong'] = False
            result['suggestions'].append('密码长度至少8位')
        
        # 复杂性检查
        if re.search(r'[a-z]', password):
            result['score'] += 1
            result['requirements'].append('包含小写字母')
        else:
            result['is_strong'] = False
            result['suggestions'].append('添加小写字母')
        
        if re.search(r'[A-Z]', password):
            result['score'] += 1
            result['requirements'].append('包含大写字母')
        else:
            result['suggestions'].append('添加大写字母')
        
        if re.search(r'\d', password):
            result['score'] += 1
            result['requirements'].append('包含数字')
        else:
            result['suggestions'].append('添加数字')
        
        if re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            result['score'] += 1
            result['requirements'].append('包含特殊字符')
        else:
            result['suggestions'].append('添加特殊字符')
        
        # 常见密码检查
        common_passwords = ['password', '123456', 'admin', 'root', 'user']
        if password.lower() in common_passwords:
            result['is_strong'] = False
            result['score'] = 0
            result['suggestions'].append('避免使用常见密码')
        
        result['is_strong'] = result['score'] >= 4
        return result

class IPWhitelist:
    """IP白名单管理"""
    
    def __init__(self):
        self.whitelist = set()
        self.lock = threading.Lock()
        
        # 默认允许本地访问
        self.add_to_whitelist('127.0.0.1')
        self.add_to_whitelist('::1')
    
    def add_to_whitelist(self, ip_or_network: str):
        """添加IP到白名单"""
        with self.lock:
            try:
                # 尝试解析为网络或IP
                network = ipaddress.ip_network(ip_or_network, strict=False)
                self.whitelist.add(str(network))
            except ValueError:
                logger.error(f"Invalid IP or network: {ip_or_network}")
    
    def remove_from_whitelist(self, ip_or_network: str):
        """从白名单移除IP"""
        with self.lock:
            self.whitelist.discard(ip_or_network)
    
    def is_whitelisted(self, ip: str) -> bool:
        """检查IP是否在白名单中"""
        with self.lock:
            try:
                client_ip = ipaddress.ip_address(ip)
                for network_str in self.whitelist:
                    network = ipaddress.ip_network(network_str)
                    if client_ip in network:
                        return True
                return False
            except ValueError:
                return False

class SecurityManager:
    """安全管理器主类"""
    
    def __init__(self, app=None):
        self.app = app
        self.audit_logger = SecurityAuditLogger()
        self.data_encryption = DataEncryption()
        self.jwt_manager = JWTManager()
        self.csrf_protection = CSRFProtection()
        self.input_validator = InputValidator()
        self.ip_whitelist = IPWhitelist()
        
        # 安全配置
        self.max_login_attempts = 5
        self.lockout_duration = 300  # 5分钟
        self.failed_attempts = {}
        self.lock = threading.Lock()
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """初始化Flask应用"""
        self.app = app
        
        # 注册请求钩子
        app.before_request(self.before_request_security_check)
        app.after_request(self.after_request_security_headers)
        
        # 注册模板全局函数
        app.jinja_env.globals['csrf_token'] = self.get_csrf_token
        app.jinja_env.globals['is_secure_context'] = self.is_secure_context
    
    def before_request_security_check(self):
        """请求前安全检查"""
        try:
            # 获取客户端IP
            client_ip = self.get_client_ip()
            
            # IP白名单检查（仅对管理端点）
            if request.path.startswith('/admin/') and not self.ip_whitelist.is_whitelisted(client_ip):
                self.log_security_event(
                    ThreatType.UNAUTHORIZED_ACCESS,
                    SecurityLevel.HIGH,
                    f"Unauthorized admin access from {client_ip}",
                    {'attempted_path': request.path}
                )
                return jsonify({'error': 'Access denied'}), 403
            
            # 检查登录失败次数
            if self.is_ip_locked(client_ip):
                self.log_security_event(
                    ThreatType.BRUTE_FORCE,
                    SecurityLevel.HIGH,
                    f"Blocked login attempt from locked IP {client_ip}",
                    {'lockout_remaining': self.get_lockout_remaining(client_ip)}
                )
                return jsonify({'error': 'Too many failed attempts. Try again later.'}), 429
            
            # 输入验证（POST/PUT请求）
            if request.method in ['POST', 'PUT', 'PATCH']:
                if request.is_json:
                    self.validate_json_input(request.get_json())
                elif request.form:
                    self.validate_form_input(request.form.to_dict())
            
        except Exception as e:
            logger.error(f"Security check error: {e}")
    
    def after_request_security_headers(self, response):
        """添加安全响应头"""
        from flask import request
        
        # 基础安全头
        security_headers = {
            'X-Content-Type-Options': 'nosniff',
            'X-XSS-Protection': '1; mode=block',
            'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
            'Content-Security-Policy': "default-src 'self' data: blob:; script-src 'self' 'unsafe-inline' 'unsafe-eval' https:; style-src 'self' 'unsafe-inline' https: data:; font-src 'self' data: https:; img-src 'self' data: blob: https:; frame-src 'self'; connect-src 'self' https:",
            'Referrer-Policy': 'strict-origin-when-cross-origin',
            'Permissions-Policy': 'geolocation=(), microphone=(), camera=()'
        }
        
        # 根据请求路径设置X-Frame-Options
        if ('ueditor' in request.path.lower() or 
            request.path.endswith('/uedit') or
            'dialogs' in request.path.lower()):
            security_headers['X-Frame-Options'] = 'SAMEORIGIN'
        else:
            security_headers['X-Frame-Options'] = 'DENY'
        
        for header, value in security_headers.items():
            response.headers[header] = value
        
        return response
    
    def validate_json_input(self, data: Dict[str, Any]):
        """验证JSON输入"""
        if not data:
            return
        
        for key, value in data.items():
            if isinstance(value, str):
                validation_result = self.input_validator.validate_input(value)
                if not validation_result['is_safe']:
                    self.log_security_event(
                        ThreatType.XSS if 'XSS' in validation_result['threats'] else ThreatType.SQL_INJECTION,
                        SecurityLevel.HIGH,
                        f"Malicious input detected in field {key}",
                        {
                            'field': key,
                            'threats': validation_result['threats'],
                            'original_value': value[:100]  # 只记录前100个字符
                        }
                    )
                    raise ValueError(f"Invalid input in field {key}")
    
    def validate_form_input(self, data: Dict[str, Any]):
        """验证表单输入"""
        for key, value in data.items():
            if isinstance(value, str):
                validation_result = self.input_validator.validate_input(value)
                if not validation_result['is_safe']:
                    self.log_security_event(
                        ThreatType.XSS if 'XSS' in validation_result['threats'] else ThreatType.SQL_INJECTION,
                        SecurityLevel.HIGH,
                        f"Malicious input detected in form field {key}",
                        {
                            'field': key,
                            'threats': validation_result['threats']
                        }
                    )
                    raise ValueError(f"Invalid input in field {key}")
    
    def record_login_attempt(self, ip: str, success: bool, user_id: str = None):
        """记录登录尝试"""
        with self.lock:
            if success:
                # 成功登录，清除失败记录
                if ip in self.failed_attempts:
                    del self.failed_attempts[ip]
                
                self.log_security_event(
                    ThreatType.UNAUTHORIZED_ACCESS,
                    SecurityLevel.LOW,
                    f"Successful login from {ip}",
                    {'user_id': user_id, 'success': True}
                )
            else:
                # 失败登录，增加计数
                if ip not in self.failed_attempts:
                    self.failed_attempts[ip] = {
                        'count': 0,
                        'first_attempt': time.time(),
                        'last_attempt': time.time()
                    }
                
                self.failed_attempts[ip]['count'] += 1
                self.failed_attempts[ip]['last_attempt'] = time.time()
                
                severity = SecurityLevel.MEDIUM if self.failed_attempts[ip]['count'] < 3 else SecurityLevel.HIGH
                
                self.log_security_event(
                    ThreatType.BRUTE_FORCE,
                    severity,
                    f"Failed login attempt from {ip}",
                    {
                        'attempt_count': self.failed_attempts[ip]['count'],
                        'user_id': user_id,
                        'success': False
                    }
                )
    
    def is_ip_locked(self, ip: str) -> bool:
        """检查IP是否被锁定"""
        with self.lock:
            if ip not in self.failed_attempts:
                return False
            
            attempts = self.failed_attempts[ip]
            if attempts['count'] >= self.max_login_attempts:
                # 检查是否仍在锁定期内
                if time.time() - attempts['last_attempt'] < self.lockout_duration:
                    return True
                else:
                    # 锁定期已过，清除记录
                    del self.failed_attempts[ip]
                    return False
            
            return False
    
    def get_lockout_remaining(self, ip: str) -> int:
        """获取剩余锁定时间"""
        with self.lock:
            if ip not in self.failed_attempts:
                return 0
            
            attempts = self.failed_attempts[ip]
            if attempts['count'] >= self.max_login_attempts:
                remaining = self.lockout_duration - (time.time() - attempts['last_attempt'])
                return max(0, int(remaining))
            
            return 0
    
    def get_client_ip(self) -> str:
        """获取客户端IP地址"""
        # 检查代理头
        if request.headers.get('X-Forwarded-For'):
            return request.headers.get('X-Forwarded-For').split(',')[0].strip()
        elif request.headers.get('X-Real-IP'):
            return request.headers.get('X-Real-IP')
        else:
            return request.remote_addr or '0.0.0.0'
    
    def get_csrf_token(self) -> str:
        """获取CSRF令牌（模板函数）"""
        session_id = session.get('session_id', 'default')
        return self.csrf_protection.generate_csrf_token(session_id)
    
    def verify_csrf_token(self, token: str) -> bool:
        """验证CSRF令牌"""
        session_id = session.get('session_id', 'default')
        return self.csrf_protection.validate_csrf_token(session_id, token)
    
    def is_secure_context(self) -> bool:
        """检查是否为安全上下文（模板函数）"""
        return request.is_secure or request.headers.get('X-Forwarded-Proto') == 'https'
    
    def log_security_event(self, threat_type: ThreatType, severity: SecurityLevel, 
                          description: str, details: Dict[str, Any] = None):
        """记录安全事件"""
        event = SecurityEvent(
            event_id=secrets.token_urlsafe(16),
            timestamp=datetime.now(),
            event_type=threat_type,
            severity=severity,
            source_ip=self.get_client_ip(),
            user_id=session.get('userid'),
            endpoint=request.endpoint or request.path,
            description=description,
            details=details or {},
            action_taken="logged"
        )
        
        self.audit_logger.log_security_event(event)
    
    def get_security_summary(self) -> Dict[str, Any]:
        """获取安全摘要"""
        recent_events = self.audit_logger.get_recent_events(24)
        
        return {
            'total_events_24h': len(recent_events),
            'high_severity_events': len([e for e in recent_events if e.severity == SecurityLevel.HIGH]),
            'critical_events': len([e for e in recent_events if e.severity == SecurityLevel.CRITICAL]),
            'blocked_ips': len([ip for ip, data in self.failed_attempts.items() if data['count'] >= self.max_login_attempts]),
            'active_lockouts': len([ip for ip in self.failed_attempts.keys() if self.is_ip_locked(ip)]),
            'threat_types': {
                threat_type.value: len([e for e in recent_events if e.event_type == threat_type])
                for threat_type in ThreatType
            }
        }

# 全局安全管理器实例
_security_manager = None

def get_security_manager() -> SecurityManager:
    """获取安全管理器实例"""
    global _security_manager
    if _security_manager is None:
        _security_manager = SecurityManager()
    return _security_manager

def init_security(app):
    """初始化安全系统"""
    try:
        security_manager = get_security_manager()
        security_manager.init_app(app)
        
        logger.info("Enhanced security system initialized successfully")
        return security_manager
        
    except Exception as e:
        logger.error(f"Failed to initialize security system: {e}")
        raise

# 装饰器函数
def require_jwt_auth(f):
    """JWT认证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Missing or invalid authorization header'}), 401
        
        token = auth_header.split(' ')[1]
        try:
            security_manager = get_security_manager()
            payload = security_manager.jwt_manager.verify_token(token)
            g.current_user = payload
            return f(*args, **kwargs)
        except Exception as e:
            return jsonify({'error': 'Invalid token'}), 401
    
    return decorated_function

def require_csrf_token(f):
    """CSRF保护装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.method in ['POST', 'PUT', 'DELETE', 'PATCH']:
            token = request.form.get('csrf_token') or request.headers.get('X-CSRF-Token')
            if not token:
                return jsonify({'error': 'CSRF token missing'}), 400
            
            security_manager = get_security_manager()
            if not security_manager.verify_csrf_token(token):
                return jsonify({'error': 'Invalid CSRF token'}), 400
        
        return f(*args, **kwargs)
    
    return decorated_function

def admin_required(f):
    """管理员权限装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('role') == 'admin':
            security_manager = get_security_manager()
            security_manager.log_security_event(
                ThreatType.UNAUTHORIZED_ACCESS,
                SecurityLevel.HIGH,
                "Unauthorized admin access attempt",
                {'user_id': session.get('userid'), 'endpoint': request.endpoint}
            )
            return jsonify({'error': 'Admin access required'}), 403
        
        return f(*args, **kwargs)
    
    return decorated_function 