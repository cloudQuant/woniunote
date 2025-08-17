"""
统一的会话管理工具模块
解决会话管理不一致的问题，提供安全的会话验证
"""
import uuid
import logging
from flask import session, request
from functools import wraps

logger = logging.getLogger(__name__)

# 标准化的会话键名
SESSION_KEYS = {
    'is_login': 'main_islogin',
    'user_id': 'main_userid', 
    'username': 'main_username',
    'nickname': 'main_nickname',
    'role': 'main_role',
    'session_id': 'main_session_id'
}

# 向后兼容的旧键名映射
LEGACY_KEYS = {
    'islogin': SESSION_KEYS['is_login'],
    'userid': SESSION_KEYS['user_id'],
    'username': SESSION_KEYS['username'], 
    'nickname': SESSION_KEYS['nickname'],
    'role': SESSION_KEYS['role']
}

def create_user_session(user_id, username, nickname, role):
    """
    创建标准化的用户会话
    
    Args:
        user_id: 用户ID
        username: 用户名
        nickname: 昵称
        role: 用户角色
        
    Returns:
        str: 生成的会话ID
    """
    session_id = str(uuid.uuid4())
    
    # 设置标准化的会话数据
    session[SESSION_KEYS['session_id']] = session_id
    session[SESSION_KEYS['is_login']] = 'true'
    session[SESSION_KEYS['user_id']] = user_id
    session[SESSION_KEYS['username']] = username
    session[SESSION_KEYS['nickname']] = nickname
    session[SESSION_KEYS['role']] = role
    
    # 为向后兼容保留旧键名（但不推荐使用）
    session['islogin'] = 'true'
    session['userid'] = user_id
    session['username'] = username
    session['nickname'] = nickname
    session['role'] = role
    
    logger.info(f"用户会话已创建: user_id={user_id}, username={username}, session_id={session_id}")
    return session_id

def get_current_user():
    """
    获取当前登录用户信息
    
    Returns:
        dict: 用户信息字典，如果未登录返回None
    """
    if not is_user_logged_in():
        return None
    
    return {
        'user_id': session.get(SESSION_KEYS['user_id']),
        'username': session.get(SESSION_KEYS['username']),
        'nickname': session.get(SESSION_KEYS['nickname']),
        'role': session.get(SESSION_KEYS['role']),
        'session_id': session.get(SESSION_KEYS['session_id'])
    }

def is_user_logged_in():
    """
    检查用户是否已登录
    支持标准键名和向后兼容
    
    Returns:
        bool: 是否已登录
    """
    # 优先使用标准键名
    is_logged_in = session.get(SESSION_KEYS['is_login']) == 'true'
    
    # 向后兼容检查
    if not is_logged_in:
        is_logged_in = session.get('islogin') == 'true'
    
    # 进一步验证用户信息完整性
    if is_logged_in:
        user_id = session.get(SESSION_KEYS['user_id']) or session.get('userid')
        username = session.get(SESSION_KEYS['username']) or session.get('username')
        if not user_id or not username:
            logger.warning("会话数据不完整，清除会话")
            clear_user_session()
            return False
    
    return is_logged_in

def clear_user_session():
    """
    清除用户会话数据
    """
    # 清除标准键名
    for key in SESSION_KEYS.values():
        session.pop(key, None)
    
    # 清除向后兼容的键名
    for key in LEGACY_KEYS.keys():
        session.pop(key, None)
    
    logger.info("用户会话已清除")

def validate_user_session():
    """
    验证当前会话的有效性
    检查会话数据的完整性和一致性
    
    Returns:
        bool: 会话是否有效
    """
    if not is_user_logged_in():
        return False
    
    try:
        # 检查会话数据一致性
        standard_user_id = session.get(SESSION_KEYS['user_id'])
        legacy_user_id = session.get('userid')
        
        if standard_user_id and legacy_user_id and str(standard_user_id) != str(legacy_user_id):
            logger.warning("会话数据不一致，清除会话")
            clear_user_session()
            return False
        
        # 检查必要字段
        required_fields = [SESSION_KEYS['user_id'], SESSION_KEYS['username']]
        for field in required_fields:
            if not session.get(field):
                logger.warning(f"缺少必要的会话字段: {field}")
                clear_user_session()
                return False
        
        return True
        
    except Exception as e:
        logger.error(f"会话验证异常: {e}")
        clear_user_session()
        return False

def require_login(f):
    """
    登录验证装饰器
    要求用户必须登录才能访问
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not validate_user_session():
            logger.warning(f"未授权访问: {request.endpoint}, IP: {request.remote_addr}")
            return '未登录', 401
        return f(*args, **kwargs)
    return decorated_function

def require_role(required_role):
    """
    角色验证装饰器
    要求用户具有特定角色才能访问
    
    Args:
        required_role: 所需角色（'admin', 'editor', 'user'）
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not validate_user_session():
                return '未登录', 401
            
            user_role = session.get(SESSION_KEYS['role']) or session.get('role')
            
            # 角色权限层级：admin > editor > user
            role_hierarchy = {'admin': 3, 'editor': 2, 'user': 1}
            
            user_level = role_hierarchy.get(user_role, 0)
            required_level = role_hierarchy.get(required_role, 999)
            
            if user_level < required_level:
                logger.warning(f"权限不足: 用户角色={user_role}, 需要角色={required_role}, "
                             f"访问={request.endpoint}, IP={request.remote_addr}")
                return '权限不足', 403
                
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def get_session_info():
    """
    获取会话调试信息
    
    Returns:
        dict: 会话信息
    """
    return {
        'is_logged_in': is_user_logged_in(),
        'current_user': get_current_user(),
        'session_keys': {key: session.get(key) for key in SESSION_KEYS.values()},
        'legacy_keys': {key: session.get(key) for key in LEGACY_KEYS.keys()},
        'session_valid': validate_user_session()
    }

def migrate_legacy_session():
    """
    将旧的会话格式迁移到新格式
    用于平滑过渡
    """
    if session.get('islogin') == 'true' and not session.get(SESSION_KEYS['is_login']):
        user_id = session.get('userid')
        username = session.get('username')
        nickname = session.get('nickname')
        role = session.get('role')
        
        if user_id and username:
            create_user_session(user_id, username, nickname or username, role or 'user')
            logger.info(f"会话已迁移到新格式: user_id={user_id}")
            return True
    
    return False