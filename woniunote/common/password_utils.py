"""
安全的密码哈希工具模块
使用 bcrypt 替代不安全的 MD5 哈希算法
"""
import bcrypt
import hashlib
import logging

logger = logging.getLogger(__name__)

def hash_password(password: str) -> str:
    """
    使用 bcrypt 对密码进行安全哈希
    
    Args:
        password: 明文密码
        
    Returns:
        str: bcrypt 哈希后的密码
    """
    if not password:
        raise ValueError("密码不能为空")
    
    # 使用 bcrypt 生成盐并哈希密码
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    
    return hashed.decode('utf-8')

def verify_password(password: str, hashed_password: str) -> bool:
    """
    验证密码是否匹配哈希值
    支持新的 bcrypt 哈希和旧的 MD5 哈希（用于迁移）
    
    Args:
        password: 明文密码
        hashed_password: 哈希后的密码
        
    Returns:
        bool: 密码是否匹配
    """
    if not password or not hashed_password:
        return False
    
    password_bytes = password.encode('utf-8')
    
    # 检查是否是新的 bcrypt 哈希（以 $2b$ 开头）
    if hashed_password.startswith('$2b$'):
        try:
            hashed_bytes = hashed_password.encode('utf-8')
            return bcrypt.checkpw(password_bytes, hashed_bytes)
        except (ValueError, TypeError) as e:
            logger.error(f"bcrypt 密码验证失败: {e}")
            return False
    
    # 向后兼容：支持旧的 MD5 哈希（32位十六进制字符串）
    elif len(hashed_password) == 32 and all(c in '0123456789abcdef' for c in hashed_password.lower()):
        logger.warning("检测到旧的 MD5 密码哈希，建议用户更新密码")
        md5_hash = hashlib.md5(password_bytes).hexdigest()
        return md5_hash == hashed_password
    
    # 未知格式的哈希
    else:
        logger.error(f"未知的密码哈希格式: {hashed_password[:10]}...")
        return False

def migrate_md5_to_bcrypt(md5_password: str, plain_password: str) -> str:
    """
    将 MD5 哈希密码迁移到 bcrypt
    只有在验证 MD5 密码正确的情况下才进行迁移
    
    Args:
        md5_password: 旧的 MD5 哈希密码
        plain_password: 用户输入的明文密码
        
    Returns:
        str: 新的 bcrypt 哈希密码，如果验证失败返回原密码
    """
    # 首先验证 MD5 密码是否正确
    if verify_password(plain_password, md5_password):
        # 验证成功，生成新的 bcrypt 哈希
        new_hash = hash_password(plain_password)
        logger.info("密码哈希已从 MD5 迁移到 bcrypt")
        return new_hash
    else:
        # 验证失败，保持原密码不变
        logger.warning("MD5 密码验证失败，无法迁移到 bcrypt")
        return md5_password

def is_bcrypt_hash(password_hash: str) -> bool:
    """
    检查密码哈希是否为 bcrypt 格式
    
    Args:
        password_hash: 密码哈希字符串
        
    Returns:
        bool: 是否为 bcrypt 格式
    """
    return password_hash.startswith('$2b$') if password_hash else False

def is_md5_hash(password_hash: str) -> bool:
    """
    检查密码哈希是否为 MD5 格式
    
    Args:
        password_hash: 密码哈希字符串
        
    Returns:
        bool: 是否为 MD5 格式
    """
    if not password_hash:
        return False
    return (len(password_hash) == 32 and 
            all(c in '0123456789abcdef' for c in password_hash.lower()))