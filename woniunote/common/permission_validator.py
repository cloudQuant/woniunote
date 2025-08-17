"""
权限验证模块
提供安全的权限检查和访问控制
"""
from typing import List, Optional, Union
from woniunote.common.simple_logger import get_simple_logger

logger = get_simple_logger('permission_validator')

class PermissionError(Exception):
    """权限异常"""
    pass

class PermissionValidator:
    """权限验证器"""
    
    # 定义角色层级
    ROLE_HIERARCHY = {
        'guest': 0,
        'user': 10,
        'editor': 20,
        'admin': 30,
        'superadmin': 40
    }
    
    # 定义权限类型
    PERMISSIONS = {
        'read': 'read',
        'write': 'write',
        'edit': 'edit',
        'delete': 'delete',
        'admin': 'admin'
    }
    
    @classmethod
    def safe_compare_ids(cls, id1: Union[int, str], id2: Union[int, str]) -> bool:
        """
        安全地比较两个ID，避免类型转换漏洞
        
        Args:
            id1: 第一个ID
            id2: 第二个ID
            
        Returns:
            bool: 是否相等
        """
        try:
            # 确保都转换为整数进行比较
            int_id1 = int(id1) if id1 is not None else None
            int_id2 = int(id2) if id2 is not None else None
            
            if int_id1 is None or int_id2 is None:
                return False
                
            return int_id1 == int_id2
            
        except (ValueError, TypeError) as e:
            logger.error(f"ID比较时类型转换失败: {e}", {
                'id1': str(id1),
                'id2': str(id2),
                'id1_type': type(id1).__name__,
                'id2_type': type(id2).__name__
            })
            return False
    
    @classmethod
    def get_role_level(cls, role: str) -> int:
        """
        获取角色权限级别
        
        Args:
            role: 角色名称
            
        Returns:
            int: 权限级别
        """
        if not role or not isinstance(role, str):
            return cls.ROLE_HIERARCHY['guest']
        
        return cls.ROLE_HIERARCHY.get(role.lower(), cls.ROLE_HIERARCHY['guest'])
    
    @classmethod
    def has_role_permission(cls, user_role: str, required_role: str) -> bool:
        """
        检查用户角色是否满足要求
        
        Args:
            user_role: 用户角色
            required_role: 所需角色
            
        Returns:
            bool: 是否有权限
        """
        user_level = cls.get_role_level(user_role)
        required_level = cls.get_role_level(required_role)
        
        return user_level >= required_level
    
    @classmethod
    def check_ownership_or_role(cls, user_id: Union[int, str], 
                               resource_owner_id: Union[int, str],
                               user_role: str,
                               required_roles: List[str] = None) -> bool:
        """
        检查用户是否为资源所有者或具有特定角色
        
        Args:
            user_id: 用户ID
            resource_owner_id: 资源所有者ID
            user_role: 用户角色
            required_roles: 允许的角色列表
            
        Returns:
            bool: 是否有权限
            
        Raises:
            PermissionError: 权限不足时抛出异常
        """
        # 检查所有权
        is_owner = cls.safe_compare_ids(user_id, resource_owner_id)
        
        # 检查角色权限
        has_role_permission = False
        if required_roles:
            for role in required_roles:
                if cls.has_role_permission(user_role, role):
                    has_role_permission = True
                    break
        
        # 记录权限检查结果
        logger.info("权限检查", {
            'user_id': str(user_id),
            'resource_owner_id': str(resource_owner_id),
            'user_role': user_role,
            'required_roles': required_roles,
            'is_owner': is_owner,
            'has_role_permission': has_role_permission,
            'access_granted': is_owner or has_role_permission
        })
        
        if not (is_owner or has_role_permission):
            raise PermissionError(f"用户 {user_id} 无权限访问资源 {resource_owner_id}")
        
        return True
    
    @classmethod
    def check_article_permission(cls, user_id: Union[int, str],
                                article_owner_id: Union[int, str],
                                user_role: str,
                                action: str = 'edit') -> bool:
        """
        检查文章操作权限
        
        Args:
            user_id: 用户ID
            article_owner_id: 文章所有者ID
            user_role: 用户角色
            action: 操作类型 (read/edit/delete)
            
        Returns:
            bool: 是否有权限
        """
        # 定义不同操作所需的角色权限
        action_roles = {
            'read': [],  # 所有人都可以读取已发布的文章
            'edit': ['editor', 'admin'],  # 编辑需要editor权限
            'delete': ['admin']  # 删除需要admin权限
        }
        
        required_roles = action_roles.get(action, ['admin'])
        
        try:
            return cls.check_ownership_or_role(
                user_id, article_owner_id, user_role, required_roles
            )
        except PermissionError:
            logger.warning("文章权限检查失败", {
                'user_id': str(user_id),
                'article_owner_id': str(article_owner_id),
                'user_role': user_role,
                'action': action
            })
            return False
    
    @classmethod
    def check_user_permission(cls, user_id: Union[int, str],
                             target_user_id: Union[int, str],
                             user_role: str,
                             action: str = 'edit') -> bool:
        """
        检查用户操作权限
        
        Args:
            user_id: 操作用户ID
            target_user_id: 目标用户ID
            user_role: 操作用户角色
            action: 操作类型
            
        Returns:
            bool: 是否有权限
        """
        action_roles = {
            'view': ['user'],
            'edit': ['admin'],
            'delete': ['admin']
        }
        
        required_roles = action_roles.get(action, ['admin'])
        
        try:
            return cls.check_ownership_or_role(
                user_id, target_user_id, user_role, required_roles
            )
        except PermissionError:
            logger.warning("用户权限检查失败", {
                'user_id': str(user_id),
                'target_user_id': str(target_user_id),
                'user_role': user_role,
                'action': action
            })
            return False
    
    @classmethod
    def validate_role(cls, role: str) -> str:
        """
        验证并标准化角色名称
        
        Args:
            role: 角色名称
            
        Returns:
            str: 标准化的角色名称
        """
        if not role or not isinstance(role, str):
            return 'guest'
        
        normalized_role = role.lower().strip()
        
        if normalized_role in cls.ROLE_HIERARCHY:
            return normalized_role
        else:
            logger.warning(f"未知角色: {role}，使用默认guest角色")
            return 'guest'
    
    @classmethod
    def sanitize_user_id(cls, user_id: Union[int, str]) -> Optional[int]:
        """
        清理和验证用户ID
        
        Args:
            user_id: 用户ID
            
        Returns:
            int: 清理后的用户ID，如果无效则返回None
        """
        if user_id is None:
            return None
        
        try:
            int_id = int(user_id)
            if int_id <= 0:
                return None
            return int_id
        except (ValueError, TypeError):
            logger.error(f"无效的用户ID: {user_id}")
            return None

# 便捷函数
def check_article_permission(user_id: Union[int, str],
                           article_owner_id: Union[int, str],
                           user_role: str,
                           action: str = 'edit') -> bool:
    """便捷函数：检查文章权限"""
    return PermissionValidator.check_article_permission(
        user_id, article_owner_id, user_role, action
    )

def safe_compare_ids(id1: Union[int, str], id2: Union[int, str]) -> bool:
    """便捷函数：安全比较ID"""
    return PermissionValidator.safe_compare_ids(id1, id2)