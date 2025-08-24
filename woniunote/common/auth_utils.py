"""
统一认证和权限验证工具模块
提供一致的用户认证和权限检查功能
"""
from flask import session, request, jsonify, abort
from functools import wraps
from typing import Optional, Dict, Any
from woniunote.common.unified_logging import get_simple_logger

logger = get_simple_logger('auth_utils')

class AuthError(Exception):
    """认证错误异常"""
    pass

class PermissionError(Exception):
    """权限错误异常"""
    pass

def get_current_user_info() -> Dict[str, Any]:
    """
    获取当前用户信息
    
    Returns:
        Dict[str, Any]: 用户信息字典，如果未登录则返回空字典
    """
    # 统一使用secure_session_manager中的用户信息
    if session.get('user_id') and session.get('username'):
        return {
            'user_id': session.get('user_id'),
            'username': session.get('username'),
            'nickname': session.get('nickname', ''),
            'role': session.get('role', 'user'),
            'is_logged_in': True
        }
    
    # 兼容性检查：处理旧的session键
    if session.get('main_islogin') == 'true':
        return {
            'user_id': session.get('main_userid'),
            'username': session.get('main_username', ''),
            'nickname': session.get('main_nickname', ''),
            'role': session.get('main_role', 'user'),
            'is_logged_in': True
        }
    
    if session.get('islogin') == 'true':
        return {
            'user_id': session.get('userid'),
            'username': session.get('username', ''),
            'nickname': session.get('nickname', ''),
            'role': session.get('role', 'user'),
            'is_logged_in': True
        }
    
    return {'is_logged_in': False}

def is_authenticated() -> bool:
    """
    检查用户是否已认证
    
    Returns:
        bool: 如果用户已登录返回True，否则返回False
    """
    user_info = get_current_user_info()
    return user_info.get('is_logged_in', False)

def get_current_user_id() -> Optional[str]:
    """
    获取当前用户ID
    
    Returns:
        Optional[str]: 用户ID，如果未登录返回None
    """
    user_info = get_current_user_info()
    return user_info.get('user_id') if user_info.get('is_logged_in') else None

def get_current_user_role() -> str:
    """
    获取当前用户角色
    
    Returns:
        str: 用户角色，默认为'guest'
    """
    user_info = get_current_user_info()
    return user_info.get('role', 'guest') if user_info.get('is_logged_in') else 'guest'

def has_permission(required_role: str) -> bool:
    """
    检查用户是否具有指定权限
    
    Args:
        required_role: 需要的角色
        
    Returns:
        bool: 如果用户具有权限返回True，否则返回False
    """
    if not is_authenticated():
        return False
    
    current_role = get_current_user_role()
    
    # 角色层级：admin > editor > user > guest
    role_hierarchy = {
        'guest': 0,
        'user': 1,
        'editor': 2,
        'admin': 3
    }
    
    current_level = role_hierarchy.get(current_role, 0)
    required_level = role_hierarchy.get(required_role, 0)
    
    return current_level >= required_level

def require_login(f):
    """
    装饰器：要求用户登录
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_authenticated():
            logger.warning("未授权访问尝试", {
                'endpoint': request.endpoint,
                'method': request.method,
                'ip': request.remote_addr,
                'user_agent': request.headers.get('User-Agent', '')[:100]
            })
            
            if request.is_json:
                return jsonify({
                    'error': 'Authentication required',
                    'message': '需要登录才能访问此资源'
                }), 401
            else:
                abort(401)
        
        return f(*args, **kwargs)
    return decorated_function

def require_role(required_role: str):
    """
    装饰器：要求特定角色权限
    
    Args:
        required_role: 需要的角色
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not is_authenticated():
                logger.warning("未登录用户尝试访问受保护资源", {
                    'endpoint': request.endpoint,
                    'required_role': required_role,
                    'ip': request.remote_addr
                })
                
                if request.is_json:
                    return jsonify({
                        'error': 'Authentication required',
                        'message': '需要登录才能访问此资源'
                    }), 401
                else:
                    abort(401)
            
            if not has_permission(required_role):
                user_info = get_current_user_info()
                logger.warning("权限不足", {
                    'endpoint': request.endpoint,
                    'user_id': user_info.get('user_id'),
                    'user_role': user_info.get('role'),
                    'required_role': required_role,
                    'ip': request.remote_addr
                })
                
                if request.is_json:
                    return jsonify({
                        'error': 'Permission denied',
                        'message': f'需要{required_role}权限才能访问此资源'
                    }), 403
                else:
                    abort(403)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def require_admin(f):
    """
    装饰器：要求管理员权限
    """
    return require_role('admin')(f)

def require_editor(f):
    """
    装饰器：要求编辑者权限
    """
    return require_role('editor')(f)

def check_resource_ownership(resource_user_id: str) -> bool:
    """
    检查当前用户是否拥有资源的所有权
    
    Args:
        resource_user_id: 资源的用户ID
        
    Returns:
        bool: 如果是资源所有者或管理员返回True
    """
    current_user_id = get_current_user_id()
    if not current_user_id:
        return False
    
    # 资源所有者或管理员可以访问
    return (current_user_id == str(resource_user_id) or 
            has_permission('admin'))

def require_ownership_or_admin(f):
    """
    装饰器：要求资源所有权或管理员权限
    需要在路由函数中提供user_id参数
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 从URL参数或请求中获取user_id
        resource_user_id = (kwargs.get('user_id') or 
                          request.args.get('user_id') or
                          request.form.get('user_id') or
                          request.json.get('user_id') if request.is_json else None)
        
        if not resource_user_id:
            logger.error("无法确定资源所有者", {
                'endpoint': request.endpoint,
                'kwargs': kwargs,
                'args': request.args.to_dict()
            })
            
            if request.is_json:
                return jsonify({
                    'error': 'Bad request',
                    'message': '无法确定资源所有者'
                }), 400
            else:
                abort(400)
        
        if not check_resource_ownership(resource_user_id):
            user_info = get_current_user_info()
            logger.warning("尝试访问他人资源", {
                'endpoint': request.endpoint,
                'current_user_id': user_info.get('user_id'),
                'resource_user_id': resource_user_id,
                'ip': request.remote_addr
            })
            
            if request.is_json:
                return jsonify({
                    'error': 'Permission denied',
                    'message': '只能访问自己的资源'
                }), 403
            else:
                abort(403)
        
        return f(*args, **kwargs)
    return decorated_function

# 便捷函数
def login_required(f):
    """别名函数：要求登录"""
    return require_login(f)

def admin_required(f):
    """别名函数：要求管理员权限"""
    return require_admin(f)

def editor_required(f):
    """别名函数：要求编辑者权限"""
    return require_editor(f)