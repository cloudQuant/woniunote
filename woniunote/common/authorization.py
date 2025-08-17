"""
统一的授权管理模块
提供基于角色和权限的访问控制
"""
import logging
from enum import Enum
from functools import wraps
from flask import session, request, jsonify
from .session_utils import get_current_user, validate_user_session

logger = logging.getLogger(__name__)

class Role(Enum):
    """用户角色枚举"""
    ADMIN = "admin"
    EDITOR = "editor" 
    USER = "user"
    GUEST = "guest"

class Permission(Enum):
    """权限枚举"""
    # 用户管理权限
    USER_CREATE = "user.create"
    USER_READ = "user.read"
    USER_UPDATE = "user.update"
    USER_DELETE = "user.delete"
    
    # 文章管理权限
    ARTICLE_CREATE = "article.create"
    ARTICLE_READ = "article.read"
    ARTICLE_UPDATE = "article.update"
    ARTICLE_DELETE = "article.delete"
    ARTICLE_PUBLISH = "article.publish"
    ARTICLE_MODERATE = "article.moderate"
    
    # 评论管理权限
    COMMENT_CREATE = "comment.create"
    COMMENT_READ = "comment.read"
    COMMENT_UPDATE = "comment.update"
    COMMENT_DELETE = "comment.delete"
    COMMENT_MODERATE = "comment.moderate"
    
    # 系统管理权限
    SYSTEM_CONFIG = "system.config"
    SYSTEM_MONITOR = "system.monitor"
    SYSTEM_BACKUP = "system.backup"
    
    # 文件管理权限
    FILE_UPLOAD = "file.upload"
    FILE_DELETE = "file.delete"

# 角色权限映射
ROLE_PERMISSIONS = {
    Role.ADMIN: [
        # 管理员拥有所有权限
        Permission.USER_CREATE, Permission.USER_READ, Permission.USER_UPDATE, Permission.USER_DELETE,
        Permission.ARTICLE_CREATE, Permission.ARTICLE_READ, Permission.ARTICLE_UPDATE, 
        Permission.ARTICLE_DELETE, Permission.ARTICLE_PUBLISH, Permission.ARTICLE_MODERATE,
        Permission.COMMENT_CREATE, Permission.COMMENT_READ, Permission.COMMENT_UPDATE,
        Permission.COMMENT_DELETE, Permission.COMMENT_MODERATE,
        Permission.SYSTEM_CONFIG, Permission.SYSTEM_MONITOR, Permission.SYSTEM_BACKUP,
        Permission.FILE_UPLOAD, Permission.FILE_DELETE
    ],
    Role.EDITOR: [
        # 编辑者权限
        Permission.USER_READ,
        Permission.ARTICLE_CREATE, Permission.ARTICLE_READ, Permission.ARTICLE_UPDATE,
        Permission.ARTICLE_PUBLISH, Permission.ARTICLE_MODERATE,
        Permission.COMMENT_CREATE, Permission.COMMENT_READ, Permission.COMMENT_UPDATE,
        Permission.COMMENT_MODERATE,
        Permission.FILE_UPLOAD
    ],
    Role.USER: [
        # 普通用户权限
        Permission.USER_READ,
        Permission.ARTICLE_CREATE, Permission.ARTICLE_READ, Permission.ARTICLE_UPDATE,
        Permission.COMMENT_CREATE, Permission.COMMENT_READ, Permission.COMMENT_UPDATE,
        Permission.FILE_UPLOAD
    ],
    Role.GUEST: [
        # 访客权限
        Permission.ARTICLE_READ,
        Permission.COMMENT_READ
    ]
}

class AuthorizationManager:
    """授权管理器"""
    
    def __init__(self):
        self.role_permissions = ROLE_PERMISSIONS
    
    def get_user_role(self, user_info=None):
        """
        获取用户角色
        
        Args:
            user_info: 用户信息，如果不提供则从当前会话获取
            
        Returns:
            Role: 用户角色
        """
        if not user_info:
            user_info = get_current_user()
        
        if not user_info:
            return Role.GUEST
        
        role_str = user_info.get('role', 'user').lower()
        
        try:
            return Role(role_str)
        except ValueError:
            logger.warning(f"未知的用户角色: {role_str}")
            return Role.USER
    
    def get_user_permissions(self, user_info=None):
        """
        获取用户权限列表
        
        Args:
            user_info: 用户信息
            
        Returns:
            List[Permission]: 权限列表
        """
        role = self.get_user_role(user_info)
        return self.role_permissions.get(role, [])
    
    def has_permission(self, permission, user_info=None):
        """
        检查用户是否具有指定权限
        
        Args:
            permission: 权限枚举
            user_info: 用户信息
            
        Returns:
            bool: 是否具有权限
        """
        if isinstance(permission, str):
            try:
                permission = Permission(permission)
            except ValueError:
                logger.error(f"未知的权限: {permission}")
                return False
        
        user_permissions = self.get_user_permissions(user_info)
        return permission in user_permissions
    
    def check_resource_ownership(self, resource_user_id, user_info=None):
        """
        检查资源所有权
        用户只能操作自己的资源，除非有管理权限
        
        Args:
            resource_user_id: 资源所有者ID
            user_info: 当前用户信息
            
        Returns:
            bool: 是否有权操作
        """
        if not user_info:
            user_info = get_current_user()
        
        if not user_info:
            return False
        
        current_user_id = user_info.get('user_id')
        role = self.get_user_role(user_info)
        
        # 管理员和编辑者可以操作任何资源
        if role in [Role.ADMIN, Role.EDITOR]:
            return True
        
        # 普通用户只能操作自己的资源
        return str(current_user_id) == str(resource_user_id)
    
    def log_authorization_attempt(self, permission, success, user_info=None, resource_info=None):
        """
        记录授权尝试
        
        Args:
            permission: 尝试的权限
            success: 是否成功
            user_info: 用户信息
            resource_info: 资源信息
        """
        if not user_info:
            user_info = get_current_user()
        
        log_data = {
            'permission': permission.value if isinstance(permission, Permission) else permission,
            'success': success,
            'user_id': user_info.get('user_id') if user_info else None,
            'username': user_info.get('username') if user_info else None,
            'role': user_info.get('role') if user_info else None,
            'endpoint': request.endpoint,
            'remote_addr': request.remote_addr,
            'user_agent': request.user_agent.string if request.user_agent else None
        }
        
        if resource_info:
            log_data['resource_info'] = resource_info
        
        if success:
            logger.info("授权成功", log_data)
        else:
            logger.warning("授权失败", log_data)

# 全局授权管理器实例
auth_manager = AuthorizationManager()

def require_permission(permission, check_ownership=False, resource_user_id_param=None):
    """
    权限验证装饰器
    
    Args:
        permission: 所需权限
        check_ownership: 是否检查资源所有权
        resource_user_id_param: 资源所有者ID的参数名（如果检查所有权）
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 首先验证会话
            if not validate_user_session():
                auth_manager.log_authorization_attempt(permission, False)
                return jsonify({'error': '未登录'}), 401
            
            user_info = get_current_user()
            
            # 检查权限
            if not auth_manager.has_permission(permission, user_info):
                auth_manager.log_authorization_attempt(permission, False, user_info)
                return jsonify({'error': '权限不足'}), 403
            
            # 检查资源所有权（如果需要）
            if check_ownership and resource_user_id_param:
                resource_user_id = None
                
                # 从请求参数中获取资源所有者ID
                if resource_user_id_param in request.form:
                    resource_user_id = request.form.get(resource_user_id_param)
                elif resource_user_id_param in request.args:
                    resource_user_id = request.args.get(resource_user_id_param)
                elif resource_user_id_param in kwargs:
                    resource_user_id = kwargs[resource_user_id_param]
                
                if resource_user_id and not auth_manager.check_resource_ownership(resource_user_id, user_info):
                    auth_manager.log_authorization_attempt(
                        permission, False, user_info, 
                        {'resource_user_id': resource_user_id}
                    )
                    return jsonify({'error': '无权操作此资源'}), 403
            
            # 记录成功的授权
            auth_manager.log_authorization_attempt(permission, True, user_info)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def require_role(required_role):
    """
    角色验证装饰器
    
    Args:
        required_role: 所需角色
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not validate_user_session():
                return jsonify({'error': '未登录'}), 401
            
            user_info = get_current_user()
            current_role = auth_manager.get_user_role(user_info)
            
            # 角色权限层级
            role_hierarchy = {
                Role.ADMIN: 4,
                Role.EDITOR: 3, 
                Role.USER: 2,
                Role.GUEST: 1
            }
            
            if isinstance(required_role, str):
                required_role = Role(required_role)
            
            current_level = role_hierarchy.get(current_role, 0)
            required_level = role_hierarchy.get(required_role, 999)
            
            if current_level < required_level:
                logger.warning(f"角色权限不足: 当前角色={current_role.value}, 需要角色={required_role.value}")
                return jsonify({'error': '角色权限不足'}), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def check_article_permission(action):
    """
    文章权限检查装饰器
    
    Args:
        action: 操作类型（'create', 'read', 'update', 'delete', 'publish'）
    """
    permission_map = {
        'create': Permission.ARTICLE_CREATE,
        'read': Permission.ARTICLE_READ,
        'update': Permission.ARTICLE_UPDATE,
        'delete': Permission.ARTICLE_DELETE,
        'publish': Permission.ARTICLE_PUBLISH
    }
    
    permission = permission_map.get(action)
    if not permission:
        raise ValueError(f"未知的文章操作: {action}")
    
    # 对于更新和删除操作，需要检查所有权
    check_ownership = action in ['update', 'delete']
    
    return require_permission(permission, check_ownership, 'userid')

def check_comment_permission(action):
    """
    评论权限检查装饰器
    
    Args:
        action: 操作类型（'create', 'read', 'update', 'delete'）
    """
    permission_map = {
        'create': Permission.COMMENT_CREATE,
        'read': Permission.COMMENT_READ,
        'update': Permission.COMMENT_UPDATE,
        'delete': Permission.COMMENT_DELETE
    }
    
    permission = permission_map.get(action)
    if not permission:
        raise ValueError(f"未知的评论操作: {action}")
    
    # 对于更新和删除操作，需要检查所有权
    check_ownership = action in ['update', 'delete']
    
    return require_permission(permission, check_ownership, 'userid')

# 便捷函数
def has_permission(permission, user_info=None):
    """检查用户权限"""
    return auth_manager.has_permission(permission, user_info)

def get_current_user_role():
    """获取当前用户角色"""
    return auth_manager.get_user_role()

def can_edit_resource(resource_user_id):
    """检查是否可以编辑资源"""
    return auth_manager.check_resource_ownership(resource_user_id)