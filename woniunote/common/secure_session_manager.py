"""
安全Session管理模块
提供安全的会话管理、防止会话固化攻击和会话劫持
"""
import os
import time
import hashlib
import secrets
from typing import Optional, Dict, Any, Union
from flask import Flask, session, request, g
from woniunote.common.simple_logger import get_simple_logger

logger = get_simple_logger('secure_session_manager')

class SecureSessionManager:
    """安全会话管理器"""
    
    def __init__(self, app: Flask = None):
        self.app = app
        self.session_timeout = 3600  # 1小时超时
        self.session_regenerate_interval = 1800  # 30分钟重新生成
        self.max_sessions_per_user = 5  # 每用户最大会话数
        
        # 会话安全配置
        self.security_config = {
            'httponly': True,
            'secure': True,  # 仅HTTPS
            'samesite': 'Strict',
            'session_protection': 'strong'
        }
        
        if app:
            self.init_app(app)
    
    def init_app(self, app: Flask):
        """初始化Flask应用"""
        self.app = app
        
        # 配置会话安全
        app.config.update({
            'SESSION_COOKIE_HTTPONLY': self.security_config['httponly'],
            'SESSION_COOKIE_SECURE': self.security_config['secure'],
            'SESSION_COOKIE_SAMESITE': self.security_config['samesite'],
            'PERMANENT_SESSION_LIFETIME': self.session_timeout
        })
        
        # 注册会话处理器
        app.before_request(self._before_request)
        app.after_request(self._after_request)
        
        logger.info("安全会话管理器初始化完成", {
            'session_timeout': self.session_timeout,
            'regenerate_interval': self.session_regenerate_interval
        })
    
    def _before_request(self):
        """请求前会话检查"""
        try:
            # 检查会话有效性
            if not self._is_session_valid():
                self.clear_session("会话无效或过期")
                return
            
            # 检查会话安全
            if not self._check_session_security():
                self.clear_session("会话安全检查失败")
                return
            
            # 更新会话活动时间
            self._update_session_activity()
            
            # 定期重新生成会话ID
            if self._should_regenerate_session():
                self._regenerate_session_id()
                
        except Exception as e:
            logger.error(f"会话前置检查失败: {e}")
            self.clear_session("会话检查异常")
    
    def _after_request(self, response):
        """请求后会话处理"""
        try:
            # 更新会话安全标记
            self._update_session_security_markers()
            
        except Exception as e:
            logger.error(f"会话后置处理失败: {e}")
        
        return response
    
    def create_session(self, user_id: Union[int, str], username: str, 
                      role: str = 'user', additional_data: Dict[str, Any] = None) -> bool:
        """
        创建安全会话
        
        Args:
            user_id: 用户ID
            username: 用户名
            role: 用户角色
            additional_data: 额外数据
            
        Returns:
            bool: 创建是否成功
        """
        try:
            # 清理现有会话
            session.clear()
            
            # 生成新的会话ID
            self._regenerate_session_id()
            
            current_time = time.time()
            
            # 设置基本会话数据
            session_data = {
                'user_id': str(user_id),
                'username': username,
                'role': role,
                'created_at': current_time,
                'last_activity': current_time,
                'last_regenerated': current_time,
                'session_id': self._generate_session_token(),
                'ip_address': self._get_client_ip(),
                'user_agent_hash': self._hash_user_agent(),
                'csrf_token': self._generate_csrf_token(),
                'login_type': 'standard'
            }
            
            # 添加额外数据
            if additional_data:
                session_data.update(additional_data)
            
            # 设置会话数据
            for key, value in session_data.items():
                session[key] = value
            
            # 标记会话为永久（受PERMANENT_SESSION_LIFETIME控制）
            session.permanent = True
            
            logger.info("用户会话创建成功", {
                'user_id': user_id,
                'username': username,
                'role': role,
                'ip_address': session_data['ip_address'],
                'session_id': session_data['session_id'][:8] + '...'
            })
            
            return True
            
        except Exception as e:
            logger.error(f"创建会话失败: {e}", {
                'user_id': user_id,
                'username': username
            })
            return False
    
    def validate_session(self) -> bool:
        """
        验证当前会话
        
        Returns:
            bool: 会话是否有效
        """
        return self._is_session_valid() and self._check_session_security()
    
    def clear_session(self, reason: str = "用户登出"):
        """
        清理会话
        
        Args:
            reason: 清理原因
        """
        user_id = session.get('user_id')
        username = session.get('username')
        
        session.clear()
        
        logger.info("用户会话已清理", {
            'user_id': user_id,
            'username': username,
            'reason': reason
        })
    
    def refresh_session(self) -> bool:
        """
        刷新会话（延长有效期）
        
        Returns:
            bool: 刷新是否成功
        """
        if not self.validate_session():
            return False
        
        try:
            session['last_activity'] = time.time()
            
            # 如果距离上次重新生成超过阈值，重新生成会话ID
            if self._should_regenerate_session():
                self._regenerate_session_id()
            
            return True
            
        except Exception as e:
            logger.error(f"会话刷新失败: {e}")
            return False
    
    def _is_session_valid(self) -> bool:
        """检查会话是否有效"""
        if not session:
            return False
        
        # 检查必要字段
        required_fields = ['user_id', 'username', 'created_at', 'last_activity']
        for field in required_fields:
            if field not in session:
                logger.warning(f"会话缺少必要字段: {field}")
                return False
        
        # 检查会话超时
        current_time = time.time()
        last_activity = session.get('last_activity', 0)
        
        if current_time - last_activity > self.session_timeout:
            logger.info("会话超时", {
                'user_id': session.get('user_id'),
                'last_activity': last_activity,
                'timeout_seconds': self.session_timeout
            })
            return False
        
        return True
    
    def _check_session_security(self) -> bool:
        """检查会话安全性"""
        try:
            # 检查IP地址一致性
            current_ip = self._get_client_ip()
            session_ip = session.get('ip_address')
            
            if session_ip and current_ip != session_ip:
                logger.warning("会话IP地址不匹配", {
                    'user_id': session.get('user_id'),
                    'session_ip': session_ip,
                    'current_ip': current_ip
                })
                return False
            
            # 检查User-Agent一致性（哈希比较）
            current_ua_hash = self._hash_user_agent()
            session_ua_hash = session.get('user_agent_hash')
            
            if session_ua_hash and current_ua_hash != session_ua_hash:
                logger.warning("会话User-Agent不匹配", {
                    'user_id': session.get('user_id')
                })
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"会话安全检查异常: {e}")
            return False
    
    def _update_session_activity(self):
        """更新会话活动时间"""
        session['last_activity'] = time.time()
    
    def _should_regenerate_session(self) -> bool:
        """判断是否应该重新生成会话ID"""
        if 'last_regenerated' not in session:
            return True
        
        current_time = time.time()
        last_regenerated = session.get('last_regenerated', 0)
        
        return current_time - last_regenerated > self.session_regenerate_interval
    
    def _regenerate_session_id(self):
        """重新生成会话ID"""
        try:
            # 保存现有会话数据
            old_data = dict(session)
            
            # 清理并重新生成
            session.clear()
            session.update(old_data)
            
            # 更新重新生成时间和会话令牌
            session['last_regenerated'] = time.time()
            session['session_id'] = self._generate_session_token()
            
            logger.info("会话ID已重新生成", {
                'user_id': session.get('user_id'),
                'new_session_id': session['session_id'][:8] + '...'
            })
            
        except Exception as e:
            logger.error(f"会话ID重新生成失败: {e}")
    
    def _update_session_security_markers(self):
        """更新会话安全标记"""
        if session:
            session['last_seen'] = time.time()
            
            # 更新安全标记
            if 'security_check_count' not in session:
                session['security_check_count'] = 0
            session['security_check_count'] += 1
    
    def _generate_session_token(self) -> str:
        """生成会话令牌"""
        return secrets.token_urlsafe(32)
    
    def _generate_csrf_token(self) -> str:
        """生成CSRF令牌"""
        return secrets.token_urlsafe(32)
    
    def _get_client_ip(self) -> str:
        """获取客户端IP地址"""
        # 按优先级检查各种IP头
        ip_headers = [
            'X-Forwarded-For',
            'X-Real-IP', 
            'X-Forwarded',
            'X-Cluster-Client-IP',
            'CF-Connecting-IP'  # Cloudflare
        ]
        
        for header in ip_headers:
            ip = request.headers.get(header)
            if ip:
                # 处理多个IP的情况（取第一个）
                return ip.split(',')[0].strip()
        
        return request.remote_addr or 'unknown'
    
    def _hash_user_agent(self) -> str:
        """对User-Agent进行哈希"""
        user_agent = request.headers.get('User-Agent', '')
        return hashlib.sha256(user_agent.encode()).hexdigest()
    
    def get_session_info(self) -> Dict[str, Any]:
        """获取会话信息"""
        if not session:
            return {'logged_in': False}
        
        return {
            'logged_in': True,
            'user_id': session.get('user_id'),
            'username': session.get('username'),
            'role': session.get('role'),
            'created_at': session.get('created_at'),
            'last_activity': session.get('last_activity'),
            'session_age': time.time() - session.get('created_at', 0),
            'time_until_timeout': self.session_timeout - (time.time() - session.get('last_activity', 0))
        }
    
    def require_login(self, redirect_url: str = '/login') -> bool:
        """
        要求登录装饰器助手
        
        Args:
            redirect_url: 重定向URL
            
        Returns:
            bool: 是否已登录
        """
        if not self.validate_session():
            # 可以在这里添加重定向逻辑
            return False
        
        return True

# 全局会话管理器实例
session_manager = SecureSessionManager()

def init_secure_session_management(app: Flask):
    """初始化安全会话管理"""
    session_manager.init_app(app)
    return session_manager

# 便捷函数
def create_user_session(user_id: Union[int, str], username: str, 
                       role: str = 'user', **kwargs) -> bool:
    """便捷函数：创建用户会话"""
    return session_manager.create_session(user_id, username, role, kwargs)

def validate_current_session() -> bool:
    """便捷函数：验证当前会话"""
    return session_manager.validate_session()

def clear_current_session(reason: str = "用户登出"):
    """便捷函数：清理当前会话"""
    session_manager.clear_session(reason)

def get_current_session_info() -> Dict[str, Any]:
    """便捷函数：获取当前会话信息"""
    return session_manager.get_session_info()