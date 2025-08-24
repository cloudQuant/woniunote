#!/usr/bin/env python3
"""
统一的会话管理模块
整合所有会话相关功能，提供统一的接口和安全的会话管理
"""

import os
import time
import uuid
import hashlib
import secrets
import threading
import traceback
from typing import Optional, Dict, Any, Union, Generator
from contextlib import contextmanager
from functools import wraps
from datetime import datetime, timedelta

from flask import Flask, session, request, g
from sqlalchemy.orm import Session as SQLAlchemySession
from sqlalchemy.exc import SQLAlchemyError

from .simple_logger import get_simple_logger
from .trace_id_manager import TraceIdManager
from .unified_error_handler import DatabaseException

logger = get_simple_logger('unified_session')

class UnifiedSessionManager:
    """
    统一的会话管理器
    整合Flask会话管理、数据库会话管理和安全会话管理
    """
    
    def __init__(self, app: Flask = None, dbsession: SQLAlchemySession = None):
        self.app = app
        self.dbsession = dbsession
        
        # 标准化的会话键名
        self.session_keys = {
            'is_login': 'main_islogin',
            'user_id': 'main_userid',
            'username': 'main_username',
            'nickname': 'main_nickname',
            'role': 'main_role',
            'session_id': 'main_session_id',
            'created_at': 'main_created_at',
            'last_activity': 'main_last_activity'
        }
        
        # 向后兼容的旧键名映射
        self.legacy_keys = {
            'islogin': self.session_keys['is_login'],
            'userid': self.session_keys['user_id'],
            'username': self.session_keys['username'],
            'nickname': self.session_keys['nickname'],
            'role': self.session_keys['role']
        }
        
        # 会话安全配置
        self.security_config = {
            'session_timeout': 3600,  # 1小时超时
            'session_regenerate_interval': 1800,  # 30分钟重新生成
            'max_sessions_per_user': 5,  # 每用户最大会话数
            'httponly': True,
            'secure': True,  # 仅HTTPS
            'samesite': 'Strict',
            'session_protection': 'strong'
        }
        
        # 数据库会话管理
        self._active_sessions = {}
        self._session_stats = {
            'total_sessions': 0,
            'active_sessions': 0,
            'committed_sessions': 0,
            'rolled_back_sessions': 0,
            'failed_sessions': 0
        }
        self._lock = threading.RLock()
        
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
            'PERMANENT_SESSION_LIFETIME': self.security_config['session_timeout']
        })
        
        # 注册会话处理器
        app.before_request(self._before_request)
        app.after_request(self._after_request)
        
        logger.info("统一会话管理器初始化完成", {
            'session_timeout': self.security_config['session_timeout'],
            'regenerate_interval': self.security_config['session_regenerate_interval']
        })
    
    # ==================== Flask会话管理 ====================
    
    def create_user_session(self, user_id: Union[int, str], username: str, 
                           nickname: str = None, role: str = 'user', 
                           additional_data: Dict[str, Any] = None) -> str:
        """
        创建标准化的用户会话
        
        Args:
            user_id: 用户ID
            username: 用户名
            nickname: 昵称
            role: 用户角色
            additional_data: 额外数据
            
        Returns:
            str: 生成的会话ID
        """
        session_id = str(uuid.uuid4())
        current_time = time.time()
        
        # 设置标准化的会话数据
        session[self.session_keys['session_id']] = session_id
        session[self.session_keys['is_login']] = 'true'
        session[self.session_keys['user_id']] = user_id
        session[self.session_keys['username']] = username
        session[self.session_keys['nickname']] = nickname or username
        session[self.session_keys['role']] = role
        session[self.session_keys['created_at']] = current_time
        session[self.session_keys['last_activity']] = current_time
        
        # 为向后兼容保留旧键名（但不推荐使用）
        session['islogin'] = 'true'
        session['userid'] = user_id
        session['username'] = username
        session['nickname'] = nickname or username
        session['role'] = role
        
        # 设置额外数据
        if additional_data:
            for key, value in additional_data.items():
                session[f"main_{key}"] = value
        
        # 生成会话令牌
        session_token = self._generate_session_token(user_id, session_id)
        session['main_session_token'] = session_token
        
        logger.info("用户会话已创建", {
            'user_id': user_id,
            'username': username,
            'session_id': session_id,
            'role': role
        })
        
        return session_id
    
    def is_user_logged_in(self) -> bool:
        """
        检查用户是否已登录
        支持标准键名和向后兼容
        
        Returns:
            bool: 是否已登录
        """
        # 优先使用标准键名
        is_logged_in = session.get(self.session_keys['is_login']) == 'true'
        
        # 向后兼容检查
        if not is_logged_in:
            is_logged_in = session.get('islogin') == 'true'
        
        # 进一步验证用户信息完整性
        if is_logged_in:
            user_id = session.get(self.session_keys['user_id']) or session.get('userid')
            username = session.get(self.session_keys['username']) or session.get('username')
            
            if not user_id or not username:
                logger.warning("会话数据不完整，清除会话")
                self.clear_user_session("会话数据不完整")
                return False
            
            # 检查会话是否过期
            if self._is_session_expired():
                logger.info("会话已过期，清除会话")
                self.clear_user_session("会话已过期")
                return False
        
        return is_logged_in
    
    def get_current_user(self) -> Optional[Dict[str, Any]]:
        """
        获取当前登录用户信息
        
        Returns:
            dict: 用户信息字典，如果未登录返回None
        """
        if not self.is_user_logged_in():
            return None
        
        return {
            'user_id': session.get(self.session_keys['user_id']),
            'username': session.get(self.session_keys['username']),
            'nickname': session.get(self.session_keys['nickname']),
            'role': session.get(self.session_keys['role']),
            'session_id': session.get(self.session_keys['session_id']),
            'created_at': session.get(self.session_keys['created_at']),
            'last_activity': session.get(self.session_keys['last_activity'])
        }
    
    def clear_user_session(self, reason: str = "用户登出"):
        """清除用户会话"""
        try:
            user_info = self.get_current_user()
            if user_info:
                logger.info("清除用户会话", {
                    'user_id': user_info['user_id'],
                    'username': user_info['username'],
                    'reason': reason
                })
            
            # 清除所有会话数据
            for key in self.session_keys.values():
                session.pop(key, None)
            
            # 清除向后兼容的键名
            for key in self.legacy_keys.values():
                session.pop(key, None)
            
            # 清除其他可能的会话数据
            session.clear()
            
        except Exception as e:
            logger.error(f"清除会话失败: {e}")
    
    def refresh_session(self) -> bool:
        """刷新会话，延长有效期"""
        try:
            if not self.is_user_logged_in():
                return False
            
            current_time = time.time()
            session[self.session_keys['last_activity']] = current_time
            
            # 检查是否需要重新生成会话ID
            if self._should_regenerate_session():
                self._regenerate_session_id()
            
            return True
            
        except Exception as e:
            logger.error(f"刷新会话失败: {e}")
            return False
    
    # ==================== 数据库会话管理 ====================
    
    @contextmanager
    def managed_db_session(self, operation: str = "unknown", trace_id: str = None):
        """
        受管理的数据库会话上下文管理器
        
        Args:
            operation: 操作名称
            trace_id: 追踪ID
            
        Yields:
            SQLAlchemySession: 数据库会话对象
        """
        if not self.dbsession:
            raise RuntimeError("数据库会话未初始化")
        
        if not trace_id:
            trace_id = TraceIdManager.generate_simple_trace_id()
        
        session_info = {
            'trace_id': trace_id,
            'operation': operation,
            'start_time': time.time(),
            'thread_id': threading.get_ident()
        }
        
        with self._lock:
            self._active_sessions[trace_id] = session_info
            self._session_stats['total_sessions'] += 1
            self._session_stats['active_sessions'] += 1
        
        logger.debug("开始数据库会话", {
            'trace_id': trace_id,
            'operation': operation,
            'active_sessions': self._session_stats['active_sessions']
        })
        
        try:
            yield self.dbsession
            
            # 会话成功完成
            self.dbsession.commit()
            
            with self._lock:
                self._session_stats['committed_sessions'] += 1
            
            session_info['status'] = 'committed'
            logger.debug("数据库会话提交成功", {
                'trace_id': trace_id,
                'operation': operation,
                'duration_ms': round((time.time() - session_info['start_time']) * 1000, 2)
            })
            
        except SQLAlchemyError as e:
            # 数据库错误，回滚事务
            try:
                self.dbsession.rollback()
                with self._lock:
                    self._session_stats['rolled_back_sessions'] += 1
                session_info['status'] = 'rolled_back'
                
                logger.error("数据库会话回滚", {
                    'trace_id': trace_id,
                    'operation': operation,
                    'error': str(e),
                    'error_type': type(e).__name__
                })
            except Exception as rollback_error:
                logger.error("数据库会话回滚失败", {
                    'trace_id': trace_id,
                    'operation': operation,
                    'rollback_error': str(rollback_error)
                })
            
            raise DatabaseException(
                f"数据库操作失败: {operation}",
                operation=operation,
                details={'error': str(e), 'trace_id': trace_id}
            )
            
        except Exception as e:
            # 其他异常，也需要回滚
            try:
                self.dbsession.rollback()
                with self._lock:
                    self._session_stats['rolled_back_sessions'] += 1
                session_info['status'] = 'rolled_back'
                
                logger.error("数据库会话异常回滚", {
                    'trace_id': trace_id,
                    'operation': operation,
                    'error': str(e),
                    'error_type': type(e).__name__
                })
            except Exception as rollback_error:
                logger.error("数据库会话异常回滚失败", {
                    'trace_id': trace_id,
                    'operation': operation,
                    'rollback_error': str(rollback_error)
                })
            
            raise
            
        finally:
            # 清理会话信息
            with self._lock:
                self._session_stats['active_sessions'] -= 1
                if trace_id in self._active_sessions:
                    del self._active_sessions[trace_id]
    
    def get_db_session(self) -> Optional[SQLAlchemySession]:
        """获取数据库会话对象"""
        return self.dbsession
    
    def get_session_stats(self) -> Dict[str, Any]:
        """获取会话统计信息"""
        with self._lock:
            return self._session_stats.copy()
    
    # ==================== 安全会话管理 ====================
    
    def _before_request(self):
        """请求前会话检查"""
        try:
            # 检查会话有效性
            if not self._is_session_valid():
                self.clear_user_session("会话无效或过期")
                return
            
            # 检查会话安全
            if not self._check_session_security():
                self.clear_user_session("会话安全检查失败")
                return
            
            # 更新会话活动时间
            self._update_session_activity()
            
            # 定期重新生成会话ID
            if self._should_regenerate_session():
                self._regenerate_session_id()
                
        except Exception as e:
            logger.error(f"会话前置检查失败: {e}")
            self.clear_user_session("会话检查异常")
    
    def _after_request(self, response):
        """请求后会话处理"""
        try:
            # 更新会话安全标记
            self._update_session_security_markers()
            
        except Exception as e:
            logger.error(f"会话后置处理失败: {e}")
        
        return response
    
    def _is_session_valid(self) -> bool:
        """检查会话是否有效"""
        if not self.is_user_logged_in():
            return False
        
        # 检查会话是否过期
        if self._is_session_expired():
            return False
        
        # 检查会话令牌
        if not self._validate_session_token():
            return False
        
        return True
    
    def _is_session_expired(self) -> bool:
        """检查会话是否过期"""
        last_activity = session.get(self.session_keys['last_activity'])
        if not last_activity:
            return True
        
        current_time = time.time()
        return (current_time - last_activity) > self.security_config['session_timeout']
    
    def _check_session_security(self) -> bool:
        """检查会话安全性"""
        # 检查用户代理
        user_agent = request.headers.get('User-Agent')
        if not user_agent:
            logger.warning("缺少User-Agent头")
            return False
        
        # 检查IP地址变化（可选）
        # 这里可以添加IP地址检查逻辑
        
        return True
    
    def _update_session_activity(self):
        """更新会话活动时间"""
        session[self.session_keys['last_activity']] = time.time()
    
    def _should_regenerate_session(self) -> bool:
        """检查是否需要重新生成会话ID"""
        last_regeneration = session.get('main_last_regeneration', 0)
        current_time = time.time()
        return (current_time - last_regeneration) > self.security_config['session_regenerate_interval']
    
    def _regenerate_session_id(self):
        """重新生成会话ID"""
        try:
            old_session_id = session.get(self.session_keys['session_id'])
            new_session_id = str(uuid.uuid4())
            
            # 更新会话ID
            session[self.session_keys['session_id']] = new_session_id
            session['main_last_regeneration'] = time.time()
            
            # 重新生成会话令牌
            user_id = session.get(self.session_keys['user_id'])
            if user_id:
                new_token = self._generate_session_token(user_id, new_session_id)
                session['main_session_token'] = new_token
            
            logger.info("会话ID已重新生成", {
                'old_session_id': old_session_id,
                'new_session_id': new_session_id
            })
            
        except Exception as e:
            logger.error(f"重新生成会话ID失败: {e}")
    
    def _generate_session_token(self, user_id: Union[int, str], session_id: str) -> str:
        """生成会话令牌"""
        data = f"{user_id}:{session_id}:{secrets.token_urlsafe(16)}"
        return hashlib.sha256(data.encode()).hexdigest()
    
    def _validate_session_token(self) -> bool:
        """验证会话令牌"""
        user_id = session.get(self.session_keys['user_id'])
        session_id = session.get(self.session_keys['session_id'])
        stored_token = session.get('main_session_token')
        
        if not all([user_id, session_id, stored_token]):
            return False
        
        expected_token = self._generate_session_token(user_id, session_id)
        return stored_token == expected_token
    
    def _update_session_security_markers(self):
        """更新会话安全标记"""
        # 这里可以添加更多的安全标记更新逻辑
        pass
    
    # ==================== 工具方法 ====================
    
    def migrate_legacy_session(self):
        """迁移旧版本会话数据"""
        try:
            # 检查是否有旧版本会话数据
            if session.get('islogin') == 'true' and not session.get(self.session_keys['is_login']):
                # 迁移数据
                session[self.session_keys['is_login']] = 'true'
                session[self.session_keys['user_id']] = session.get('userid')
                session[self.session_keys['username']] = session.get('username')
                session[self.session_keys['nickname']] = session.get('nickname')
                session[self.session_keys['role']] = session.get('role')
                
                # 生成新的会话ID和令牌
                session_id = str(uuid.uuid4())
                session[self.session_keys['session_id']] = session_id
                session[self.session_keys['created_at']] = time.time()
                session[self.session_keys['last_activity']] = time.time()
                
                user_id = session.get(self.session_keys['user_id'])
                if user_id:
                    session_token = self._generate_session_token(user_id, session_id)
                    session['main_session_token'] = session_token
                
                logger.info("旧版本会话数据迁移完成")
                
        except Exception as e:
            logger.error(f"会话数据迁移失败: {e}")
    
    def get_session_info(self) -> Dict[str, Any]:
        """获取会话详细信息"""
        user_info = self.get_current_user()
        if not user_info:
            return {}
        
        return {
            **user_info,
            'session_keys': self.session_keys,
            'security_config': self.security_config,
            'db_session_stats': self.get_session_stats()
        }
    
    def validate_user_session(self) -> bool:
        """验证用户会话的完整性"""
        try:
            if not self.is_user_logged_in():
                return False
            
            # 检查必需字段
            required_fields = ['user_id', 'username', 'role']
            for field in required_fields:
                if not session.get(self.session_keys[field]):
                    logger.warning(f"会话缺少必需字段: {field}")
                    return False
            
            # 检查会话是否过期
            if self._is_session_expired():
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"验证用户会话失败: {e}")
            return False

# ==================== 全局实例和工厂函数 ====================

# 全局会话管理器实例
_global_session_manager = None

def init_unified_session_manager(app: Flask, dbsession: SQLAlchemySession = None) -> UnifiedSessionManager:
    """初始化全局会话管理器"""
    global _global_session_manager
    _global_session_manager = UnifiedSessionManager(app, dbsession)
    return _global_session_manager

def get_session_manager() -> UnifiedSessionManager:
    """获取全局会话管理器"""
    if _global_session_manager is None:
        raise RuntimeError("会话管理器未初始化，请先调用 init_unified_session_manager")
    return _global_session_manager

def create_user_session(user_id, username, nickname=None, role='user', additional_data=None):
    """便捷函数：创建用户会话"""
    manager = get_session_manager()
    return manager.create_user_session(user_id, username, nickname, role, additional_data)

def is_user_logged_in():
    """便捷函数：检查用户是否已登录"""
    manager = get_session_manager()
    return manager.is_user_logged_in()

def get_current_user():
    """便捷函数：获取当前用户信息"""
    manager = get_session_manager()
    return manager.get_current_user()

def clear_user_session(reason="用户登出"):
    """便捷函数：清除用户会话"""
    manager = get_session_manager()
    return manager.clear_user_session(reason)

# 向后兼容的别名
create_user_session_legacy = create_user_session
is_user_logged_in_legacy = is_user_logged_in
get_current_user_legacy = get_current_user
clear_user_session_legacy = clear_user_session
