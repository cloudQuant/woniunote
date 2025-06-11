#!/usr/bin/env python3
"""
Phase 6 API安全增强模块
提供API鉴权、请求签名验证、防重放攻击、API访问控制等企业级API安全功能
"""

import os
import time
import hmac
import hashlib
import base64
import json
import logging
import threading
from typing import Dict, Any, List, Optional, Callable, Set, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from functools import wraps
from collections import defaultdict, deque
from flask import request, jsonify, g, session, current_app
import secrets
import ipaddress
from enum import Enum

logger = logging.getLogger(__name__)

class SecurityRiskLevel(Enum):
    """安全风险级别"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class APISecurityEvent(Enum):
    """API安全事件类型"""
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    INVALID_SIGNATURE = "invalid_signature"
    REPLAY_ATTACK = "replay_attack"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    SUSPICIOUS_PAYLOAD = "suspicious_payload"
    BLOCKED_IP = "blocked_ip"
    API_KEY_MISUSE = "api_key_misuse"

@dataclass
class APISecurityLog:
    """API安全日志"""
    timestamp: datetime
    event_type: APISecurityEvent
    risk_level: SecurityRiskLevel
    client_ip: str
    user_agent: str
    endpoint: str
    api_key: Optional[str]
    request_signature: Optional[str]
    details: Dict[str, Any]
    action_taken: str

@dataclass
class APIKey:
    """API密钥"""
    key_id: str
    secret: str
    name: str
    permissions: List[str]
    rate_limit: int
    created_at: datetime
    expires_at: Optional[datetime]
    is_active: bool
    last_used: Optional[datetime]
    usage_count: int

class RequestSignatureValidator:
    """请求签名验证器"""
    
    def __init__(self, signature_ttl: int = 300):
        self.signature_ttl = signature_ttl  # 签名有效期（秒）
        self.used_signatures = deque(maxlen=10000)  # 防重放攻击
        self.lock = threading.Lock()
    
    def generate_signature(self, api_secret: str, method: str, path: str, 
                          body: str, timestamp: str, nonce: str) -> str:
        """生成请求签名"""
        # 构建签名字符串
        string_to_sign = f"{method}\n{path}\n{body}\n{timestamp}\n{nonce}"
        
        # HMAC-SHA256签名
        signature = hmac.new(
            api_secret.encode('utf-8'),
            string_to_sign.encode('utf-8'),
            hashlib.sha256
        ).digest()
        
        return base64.b64encode(signature).decode('utf-8')
    
    def validate_signature(self, api_secret: str, signature: str, method: str, 
                          path: str, body: str, timestamp: str, nonce: str) -> bool:
        """验证请求签名"""
        # 检查时间戳
        try:
            request_time = int(timestamp)
            current_time = int(time.time())
            
            if abs(current_time - request_time) > self.signature_ttl:
                logger.warning(f"Request timestamp expired: {timestamp}")
                return False
        except ValueError:
            logger.warning(f"Invalid timestamp format: {timestamp}")
            return False
        
        # 检查重放攻击
        signature_key = f"{signature}:{timestamp}:{nonce}"
        with self.lock:
            if signature_key in self.used_signatures:
                logger.warning(f"Replay attack detected: {signature_key}")
                return False
            
            self.used_signatures.append(signature_key)
        
        # 验证签名
        expected_signature = self.generate_signature(
            api_secret, method, path, body, timestamp, nonce
        )
        
        return hmac.compare_digest(signature, expected_signature)

class APIKeyManager:
    """API密钥管理器"""
    
    def __init__(self):
        self.api_keys: Dict[str, APIKey] = {}
        self.key_usage = defaultdict(list)  # 使用记录
        self.lock = threading.RLock()
        
        # 默认API密钥（开发用）
        self._create_default_keys()
    
    def _create_default_keys(self):
        """创建默认API密钥"""
        default_key = APIKey(
            key_id="default_api_key",
            secret=os.environ.get('DEFAULT_API_SECRET', 'default-secret-change-me'),
            name="默认API密钥",
            permissions=["read", "write"],
            rate_limit=1000,
            created_at=datetime.now(),
            expires_at=None,
            is_active=True,
            last_used=None,
            usage_count=0
        )
        
        self.api_keys[default_key.key_id] = default_key
    
    def create_api_key(self, name: str, permissions: List[str], 
                      rate_limit: int = 1000, expires_in_days: int = None) -> APIKey:
        """创建API密钥"""
        with self.lock:
            key_id = f"ak_{secrets.token_urlsafe(16)}"
            secret = secrets.token_urlsafe(32)
            
            expires_at = None
            if expires_in_days:
                expires_at = datetime.now() + timedelta(days=expires_in_days)
            
            api_key = APIKey(
                key_id=key_id,
                secret=secret,
                name=name,
                permissions=permissions,
                rate_limit=rate_limit,
                created_at=datetime.now(),
                expires_at=expires_at,
                is_active=True,
                last_used=None,
                usage_count=0
            )
            
            self.api_keys[key_id] = api_key
            
            logger.info(f"Created API key: {key_id} for {name}")
            return api_key
    
    def get_api_key(self, key_id: str) -> Optional[APIKey]:
        """获取API密钥"""
        with self.lock:
            return self.api_keys.get(key_id)
    
    def validate_api_key(self, key_id: str) -> bool:
        """验证API密钥有效性"""
        with self.lock:
            api_key = self.api_keys.get(key_id)
            
            if not api_key:
                return False
            
            if not api_key.is_active:
                return False
            
            if api_key.expires_at and datetime.now() > api_key.expires_at:
                return False
            
            return True
    
    def record_usage(self, key_id: str, endpoint: str, success: bool):
        """记录API密钥使用"""
        with self.lock:
            api_key = self.api_keys.get(key_id)
            if api_key:
                api_key.last_used = datetime.now()
                api_key.usage_count += 1
                
                self.key_usage[key_id].append({
                    'timestamp': datetime.now(),
                    'endpoint': endpoint,
                    'success': success
                })
                
                # 保持最近1000次使用记录
                if len(self.key_usage[key_id]) > 1000:
                    self.key_usage[key_id].pop(0)
    
    def revoke_api_key(self, key_id: str):
        """撤销API密钥"""
        with self.lock:
            api_key = self.api_keys.get(key_id)
            if api_key:
                api_key.is_active = False
                logger.info(f"Revoked API key: {key_id}")
    
    def get_usage_stats(self, key_id: str) -> Dict[str, Any]:
        """获取API密钥使用统计"""
        with self.lock:
            api_key = self.api_keys.get(key_id)
            if not api_key:
                return {}
            
            usage_records = self.key_usage.get(key_id, [])
            
            # 统计最近24小时的使用情况
            cutoff_time = datetime.now() - timedelta(hours=24)
            recent_usage = [
                record for record in usage_records
                if record['timestamp'] >= cutoff_time
            ]
            
            success_count = sum(1 for record in recent_usage if record['success'])
            error_count = len(recent_usage) - success_count
            
            return {
                'key_id': key_id,
                'name': api_key.name,
                'total_usage': api_key.usage_count,
                'recent_24h_usage': len(recent_usage),
                'recent_success_rate': success_count / len(recent_usage) if recent_usage else 0,
                'last_used': api_key.last_used.isoformat() if api_key.last_used else None,
                'is_active': api_key.is_active,
                'expires_at': api_key.expires_at.isoformat() if api_key.expires_at else None
            }

class IPAccessController:
    """IP访问控制器"""
    
    def __init__(self):
        self.whitelist: Set[str] = set()
        self.blacklist: Set[str] = set()
        self.suspicious_ips = defaultdict(int)  # 可疑IP计数
        self.ip_request_history = defaultdict(deque)  # IP请求历史
        self.lock = threading.Lock()
        
        # 默认添加本地IP到白名单
        self.whitelist.update(['127.0.0.1', '::1', 'localhost'])
    
    def add_to_whitelist(self, ip_or_network: str):
        """添加IP到白名单"""
        with self.lock:
            try:
                # 验证IP格式
                ipaddress.ip_network(ip_or_network, strict=False)
                self.whitelist.add(ip_or_network)
                logger.info(f"Added {ip_or_network} to whitelist")
            except ValueError as e:
                logger.error(f"Invalid IP or network: {ip_or_network}, error: {e}")
    
    def add_to_blacklist(self, ip_or_network: str, reason: str = ""):
        """添加IP到黑名单"""
        with self.lock:
            try:
                ipaddress.ip_network(ip_or_network, strict=False)
                self.blacklist.add(ip_or_network)
                logger.warning(f"Added {ip_or_network} to blacklist. Reason: {reason}")
            except ValueError as e:
                logger.error(f"Invalid IP or network: {ip_or_network}, error: {e}")
    
    def is_ip_allowed(self, client_ip: str) -> bool:
        """检查IP是否被允许访问"""
        with self.lock:
            try:
                client_addr = ipaddress.ip_address(client_ip)
                
                # 检查黑名单
                for blocked_network in self.blacklist:
                    if client_addr in ipaddress.ip_network(blocked_network):
                        return False
                
                # 检查白名单（如果有白名单，只允许白名单中的IP）
                if self.whitelist:
                    for allowed_network in self.whitelist:
                        if client_addr in ipaddress.ip_network(allowed_network):
                            return True
                    return False  # 有白名单但不在其中
                
                return True  # 没有白名单限制且不在黑名单中
                
            except ValueError:
                logger.warning(f"Invalid IP address: {client_ip}")
                return False
    
    def record_request(self, client_ip: str, endpoint: str, success: bool):
        """记录IP请求"""
        with self.lock:
            current_time = time.time()
            
            # 记录请求历史
            self.ip_request_history[client_ip].append({
                'timestamp': current_time,
                'endpoint': endpoint,
                'success': success
            })
            
            # 保持最近100个请求记录
            if len(self.ip_request_history[client_ip]) > 100:
                self.ip_request_history[client_ip].popleft()
            
            # 分析可疑行为
            if not success:
                self.suspicious_ips[client_ip] += 1
                
                # 超过阈值自动加入黑名单
                if self.suspicious_ips[client_ip] > 10:
                    self.add_to_blacklist(client_ip, "Too many failed requests")
    
    def analyze_ip_behavior(self, client_ip: str) -> Dict[str, Any]:
        """分析IP行为"""
        with self.lock:
            history = list(self.ip_request_history.get(client_ip, []))
            
            if not history:
                return {}
            
            # 最近1小时的请求
            cutoff_time = time.time() - 3600
            recent_requests = [req for req in history if req['timestamp'] >= cutoff_time]
            
            if not recent_requests:
                return {}
            
            success_count = sum(1 for req in recent_requests if req['success'])
            error_count = len(recent_requests) - success_count
            
            # 分析请求频率
            if len(recent_requests) >= 2:
                time_span = recent_requests[-1]['timestamp'] - recent_requests[0]['timestamp']
                request_rate = len(recent_requests) / max(time_span, 1)
            else:
                request_rate = 0
            
            # 分析访问的端点
            endpoints = [req['endpoint'] for req in recent_requests]
            unique_endpoints = len(set(endpoints))
            
            risk_score = 0
            risk_factors = []
            
            # 风险评估
            if error_count > 5:
                risk_score += 3
                risk_factors.append("高错误率")
            
            if request_rate > 10:  # 每秒超过10个请求
                risk_score += 2
                risk_factors.append("请求频率过高")
            
            if unique_endpoints == 1 and len(recent_requests) > 20:
                risk_score += 1
                risk_factors.append("单一端点高频访问")
            
            # 确定风险级别
            if risk_score >= 5:
                risk_level = SecurityRiskLevel.CRITICAL
            elif risk_score >= 3:
                risk_level = SecurityRiskLevel.HIGH
            elif risk_score >= 1:
                risk_level = SecurityRiskLevel.MEDIUM
            else:
                risk_level = SecurityRiskLevel.LOW
            
            return {
                'client_ip': client_ip,
                'recent_requests_count': len(recent_requests),
                'success_rate': success_count / len(recent_requests),
                'request_rate_per_second': request_rate,
                'unique_endpoints': unique_endpoints,
                'risk_score': risk_score,
                'risk_level': risk_level.value,
                'risk_factors': risk_factors,
                'is_suspicious': self.suspicious_ips[client_ip] > 0
            }

class APIRateLimiter:
    """API速率限制器"""
    
    def __init__(self):
        self.rate_limits: Dict[str, Dict[str, Any]] = {}
        self.request_counts = defaultdict(lambda: defaultdict(int))
        self.lock = threading.Lock()
        
        # 默认速率限制配置
        self.default_limits = {
            'requests_per_minute': 60,
            'requests_per_hour': 1000,
            'burst_limit': 10
        }
    
    def set_rate_limit(self, identifier: str, requests_per_minute: int, 
                      requests_per_hour: int = None, burst_limit: int = None):
        """设置速率限制"""
        with self.lock:
            self.rate_limits[identifier] = {
                'requests_per_minute': requests_per_minute,
                'requests_per_hour': requests_per_hour or requests_per_minute * 60,
                'burst_limit': burst_limit or requests_per_minute // 6
            }
    
    def is_allowed(self, identifier: str, endpoint: str = "default") -> Tuple[bool, Dict[str, Any]]:
        """检查是否允许请求"""
        with self.lock:
            current_time = int(time.time())
            minute_key = current_time // 60
            hour_key = current_time // 3600
            second_key = current_time
            
            # 获取限制配置
            limits = self.rate_limits.get(identifier, self.default_limits)
            
            # 检查分钟级限制
            minute_count = self.request_counts[f"{identifier}:minute"][minute_key]
            if minute_count >= limits['requests_per_minute']:
                return False, {
                    'limit_type': 'minute',
                    'limit': limits['requests_per_minute'],
                    'current': minute_count,
                    'reset_time': (minute_key + 1) * 60
                }
            
            # 检查小时级限制
            hour_count = self.request_counts[f"{identifier}:hour"][hour_key]
            if hour_count >= limits['requests_per_hour']:
                return False, {
                    'limit_type': 'hour',
                    'limit': limits['requests_per_hour'],
                    'current': hour_count,
                    'reset_time': (hour_key + 1) * 3600
                }
            
            # 检查突发限制（秒级）
            recent_seconds = []
            for i in range(10):  # 检查最近10秒
                second_count = self.request_counts[f"{identifier}:second"][second_key - i]
                recent_seconds.append(second_count)
            
            burst_count = sum(recent_seconds)
            if burst_count >= limits['burst_limit']:
                return False, {
                    'limit_type': 'burst',
                    'limit': limits['burst_limit'],
                    'current': burst_count,
                    'reset_time': second_key + 10
                }
            
            # 记录请求
            self.request_counts[f"{identifier}:minute"][minute_key] += 1
            self.request_counts[f"{identifier}:hour"][hour_key] += 1
            self.request_counts[f"{identifier}:second"][second_key] += 1
            
            return True, {}
    
    def get_rate_limit_status(self, identifier: str) -> Dict[str, Any]:
        """获取速率限制状态"""
        with self.lock:
            current_time = int(time.time())
            minute_key = current_time // 60
            hour_key = current_time // 3600
            
            limits = self.rate_limits.get(identifier, self.default_limits)
            
            minute_count = self.request_counts[f"{identifier}:minute"][minute_key]
            hour_count = self.request_counts[f"{identifier}:hour"][hour_key]
            
            return {
                'identifier': identifier,
                'minute_limit': limits['requests_per_minute'],
                'minute_used': minute_count,
                'minute_remaining': max(0, limits['requests_per_minute'] - minute_count),
                'hour_limit': limits['requests_per_hour'],
                'hour_used': hour_count,
                'hour_remaining': max(0, limits['requests_per_hour'] - hour_count),
                'minute_reset_time': (minute_key + 1) * 60,
                'hour_reset_time': (hour_key + 1) * 3600
            }

class APISecurityEnhancer:
    """API安全增强器主类"""
    
    def __init__(self, app=None):
        self.app = app
        self.signature_validator = RequestSignatureValidator()
        self.api_key_manager = APIKeyManager()
        self.ip_controller = IPAccessController()
        self.rate_limiter = APIRateLimiter()
        self.security_logs = deque(maxlen=10000)
        self.lock = threading.Lock()
        
        # 安全配置
        self.require_signature = False  # 是否要求签名验证
        self.require_api_key = True     # 是否要求API密钥
        self.enable_ip_filtering = True  # 是否启用IP过滤
        self.enable_rate_limiting = True # 是否启用速率限制
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """初始化Flask应用"""
        self.app = app
        
        # 注册请求钩子
        app.before_request(self._before_request_security_check)
        app.after_request(self._after_request_security_headers)
        
        logger.info("API security enhancer initialized")
    
    def _before_request_security_check(self):
        """请求前安全检查"""
        # 只对API端点进行检查
        if not request.path.startswith('/api/'):
            return
        
        try:
            client_ip = self._get_client_ip()
            
            # IP访问控制
            if self.enable_ip_filtering and not self.ip_controller.is_ip_allowed(client_ip):
                self._log_security_event(
                    APISecurityEvent.BLOCKED_IP,
                    SecurityRiskLevel.HIGH,
                    f"Blocked IP access: {client_ip}",
                    {'client_ip': client_ip}
                )
                return jsonify({'error': 'Access denied from your IP address'}), 403
            
            # API密钥验证
            if self.require_api_key:
                api_key = request.headers.get('X-API-Key')
                if not api_key or not self.api_key_manager.validate_api_key(api_key):
                    self._log_security_event(
                        APISecurityEvent.UNAUTHORIZED_ACCESS,
                        SecurityRiskLevel.MEDIUM,
                        f"Invalid or missing API key",
                        {'api_key': api_key[:10] + '...' if api_key else None}
                    )
                    return jsonify({'error': 'Invalid or missing API key'}), 401
                
                g.api_key = api_key
            
            # 速率限制
            if self.enable_rate_limiting:
                identifier = api_key if api_key else client_ip
                allowed, limit_info = self.rate_limiter.is_allowed(identifier, request.endpoint)
                
                if not allowed:
                    self._log_security_event(
                        APISecurityEvent.RATE_LIMIT_EXCEEDED,
                        SecurityRiskLevel.MEDIUM,
                        f"Rate limit exceeded for {identifier}",
                        limit_info
                    )
                    
                    response = jsonify({
                        'error': 'Rate limit exceeded',
                        'limit_info': limit_info
                    })
                    response.status_code = 429
                    
                    # 添加速率限制头
                    response.headers['X-RateLimit-Limit'] = str(limit_info.get('limit', 0))
                    response.headers['X-RateLimit-Remaining'] = '0'
                    response.headers['X-RateLimit-Reset'] = str(limit_info.get('reset_time', 0))
                    
                    return response
            
            # 请求签名验证
            if self.require_signature:
                if not self._validate_request_signature():
                    self._log_security_event(
                        APISecurityEvent.INVALID_SIGNATURE,
                        SecurityRiskLevel.HIGH,
                        "Invalid request signature",
                        {}
                    )
                    return jsonify({'error': 'Invalid request signature'}), 401
            
            # 分析IP行为
            behavior_analysis = self.ip_controller.analyze_ip_behavior(client_ip)
            if behavior_analysis.get('risk_level') in ['high', 'critical']:
                self._log_security_event(
                    APISecurityEvent.SUSPICIOUS_PAYLOAD,
                    SecurityRiskLevel.HIGH,
                    f"Suspicious behavior detected from {client_ip}",
                    behavior_analysis
                )
            
        except Exception as e:
            logger.error(f"Security check error: {e}")
            return jsonify({'error': 'Security check failed'}), 500
    
    def _after_request_security_headers(self, response):
        """添加安全响应头"""
        if request.path.startswith('/api/'):
            # API特有的安全头
            response.headers['X-API-Version'] = '1.0'
            response.headers['X-Content-Type-Options'] = 'nosniff'
            response.headers['X-Frame-Options'] = 'DENY'
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            
            # 添加速率限制信息
            if self.enable_rate_limiting and hasattr(g, 'api_key'):
                status = self.rate_limiter.get_rate_limit_status(g.api_key)
                response.headers['X-RateLimit-Limit'] = str(status['minute_limit'])
                response.headers['X-RateLimit-Remaining'] = str(status['minute_remaining'])
                response.headers['X-RateLimit-Reset'] = str(status['minute_reset_time'])
        
        return response
    
    def _validate_request_signature(self) -> bool:
        """验证请求签名"""
        try:
            signature = request.headers.get('X-Signature')
            timestamp = request.headers.get('X-Timestamp')
            nonce = request.headers.get('X-Nonce')
            api_key = getattr(g, 'api_key', None)
            
            if not all([signature, timestamp, nonce, api_key]):
                return False
            
            # 获取API密钥信息
            key_info = self.api_key_manager.get_api_key(api_key)
            if not key_info:
                return False
            
            # 获取请求体
            body = request.get_data(as_text=True) if request.data else ""
            
            # 验证签名
            return self.signature_validator.validate_signature(
                key_info.secret, signature, request.method,
                request.path, body, timestamp, nonce
            )
            
        except Exception as e:
            logger.error(f"Signature validation error: {e}")
            return False
    
    def _get_client_ip(self) -> str:
        """获取客户端IP"""
        # 检查代理头
        if request.headers.get('X-Forwarded-For'):
            return request.headers.get('X-Forwarded-For').split(',')[0].strip()
        elif request.headers.get('X-Real-IP'):
            return request.headers.get('X-Real-IP')
        else:
            return request.remote_addr or '0.0.0.0'
    
    def _log_security_event(self, event_type: APISecurityEvent, risk_level: SecurityRiskLevel,
                           description: str, details: Dict[str, Any]):
        """记录安全事件"""
        with self.lock:
            log_entry = APISecurityLog(
                timestamp=datetime.now(),
                event_type=event_type,
                risk_level=risk_level,
                client_ip=self._get_client_ip(),
                user_agent=request.headers.get('User-Agent', ''),
                endpoint=request.endpoint or request.path,
                api_key=getattr(g, 'api_key', None),
                request_signature=request.headers.get('X-Signature'),
                details=details,
                action_taken="logged"
            )
            
            self.security_logs.append(log_entry)
            
            # 记录到应用日志
            log_level = logging.ERROR if risk_level in [SecurityRiskLevel.HIGH, SecurityRiskLevel.CRITICAL] else logging.WARNING
            logger.log(log_level, f"API Security Event: {description}")
    
    def get_security_summary(self) -> Dict[str, Any]:
        """获取安全摘要"""
        with self.lock:
            recent_logs = [log for log in self.security_logs 
                          if log.timestamp >= datetime.now() - timedelta(hours=24)]
            
            event_counts = defaultdict(int)
            risk_counts = defaultdict(int)
            
            for log in recent_logs:
                event_counts[log.event_type.value] += 1
                risk_counts[log.risk_level.value] += 1
            
            return {
                'total_events_24h': len(recent_logs),
                'event_types': dict(event_counts),
                'risk_levels': dict(risk_counts),
                'critical_events': risk_counts[SecurityRiskLevel.CRITICAL.value],
                'high_risk_events': risk_counts[SecurityRiskLevel.HIGH.value],
                'timestamp': datetime.now().isoformat()
            }
    
    def get_security_logs(self, hours: int = 24, risk_level: SecurityRiskLevel = None) -> List[Dict[str, Any]]:
        """获取安全日志"""
        with self.lock:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            filtered_logs = [
                log for log in self.security_logs
                if log.timestamp >= cutoff_time
            ]
            
            if risk_level:
                filtered_logs = [
                    log for log in filtered_logs
                    if log.risk_level == risk_level
                ]
            
            return [asdict(log) for log in filtered_logs]

# 全局实例
_api_security_enhancer = None

def get_api_security_enhancer() -> APISecurityEnhancer:
    """获取API安全增强器实例"""
    global _api_security_enhancer
    if _api_security_enhancer is None:
        _api_security_enhancer = APISecurityEnhancer()
    return _api_security_enhancer

def init_api_security_enhancement(app):
    """初始化API安全增强"""
    try:
        enhancer = get_api_security_enhancer()
        enhancer.init_app(app)
        
        logger.info("API security enhancement system initialized successfully")
        return enhancer
        
    except Exception as e:
        logger.error(f"Failed to initialize API security enhancement: {e}")
        raise

# 装饰器
def require_api_key(permissions: List[str] = None):
    """API密钥验证装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            enhancer = get_api_security_enhancer()
            
            api_key = request.headers.get('X-API-Key')
            if not api_key or not enhancer.api_key_manager.validate_api_key(api_key):
                return jsonify({'error': 'Invalid or missing API key'}), 401
            
            # 检查权限
            if permissions:
                key_info = enhancer.api_key_manager.get_api_key(api_key)
                if not key_info or not any(perm in key_info.permissions for perm in permissions):
                    return jsonify({'error': 'Insufficient permissions'}), 403
            
            g.api_key = api_key
            return func(*args, **kwargs)
        
        return wrapper
    return decorator

def require_signature():
    """请求签名验证装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            enhancer = get_api_security_enhancer()
            
            if not enhancer._validate_request_signature():
                return jsonify({'error': 'Invalid request signature'}), 401
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator 