"""
安全密码处理模块
提供bcrypt加密和验证功能，替代不安全的MD5哈希
"""
import bcrypt
import hashlib
import time
from woniunote.common.simple_logger import get_simple_logger

logger = get_simple_logger('secure_password')

class SecurePassword:
    """安全密码处理类"""
    
    def __init__(self):
        # bcrypt工作因子(rounds)，决定计算复杂度
        # 12是目前推荐的安全级别，可根据需要调整
        self.rounds = 12
    
    def hash_password(self, password: str) -> str:
        """
        使用bcrypt安全地哈希密码
        
        Args:
            password: 明文密码
            
        Returns:
            str: bcrypt哈希后的密码
        """
        if not password:
            raise ValueError("密码不能为空")
        
        try:
            # 生成salt并哈希密码
            salt = bcrypt.gensalt(rounds=self.rounds)
            hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
            
            logger.info("密码哈希成功", {
                'hash_method': 'bcrypt',
                'rounds': self.rounds
            })
            
            return hashed.decode('utf-8')
            
        except Exception as e:
            logger.error(f"密码哈希失败: {e}")
            raise
    
    def verify_password(self, password: str, hashed_password: str) -> bool:
        """
        验证密码是否正确
        
        Args:
            password: 明文密码
            hashed_password: 存储的哈希密码
            
        Returns:
            bool: 密码是否匹配
        """
        if not password or not hashed_password:
            return False
        
        try:
            # 验证密码
            result = bcrypt.checkpw(
                password.encode('utf-8'), 
                hashed_password.encode('utf-8')
            )
            
            logger.info("密码验证完成", {
                'verification_result': result
            })
            
            return result
            
        except Exception as e:
            logger.error(f"密码验证失败: {e}")
            return False
    
    def is_bcrypt_hash(self, hashed_password: str) -> bool:
        """
        检查是否为bcrypt哈希格式
        
        Args:
            hashed_password: 哈希密码
            
        Returns:
            bool: 是否为bcrypt格式
        """
        if not hashed_password:
            return False
        
        # bcrypt哈希格式: $2b$rounds$salt+hash
        return (hashed_password.startswith('$2b$') or 
                hashed_password.startswith('$2a$') or 
                hashed_password.startswith('$2y$'))
    
    def is_md5_hash(self, hashed_password: str) -> bool:
        """
        检查是否为MD5哈希格式
        
        Args:
            hashed_password: 哈希密码
            
        Returns:
            bool: 是否为MD5格式
        """
        if not hashed_password:
            return False
        
        # MD5哈希长度为32个十六进制字符
        return len(hashed_password) == 32 and all(c in '0123456789abcdef' for c in hashed_password.lower())
    
    def migrate_md5_to_bcrypt(self, password: str, md5_hash: str) -> str:
        """
        将MD5哈希迁移到bcrypt
        仅在密码验证成功时调用
        
        Args:
            password: 明文密码
            md5_hash: 现有的MD5哈希
            
        Returns:
            str: 新的bcrypt哈希
        """
        # 首先验证MD5哈希是否正确
        if not self.verify_md5_password(password, md5_hash):
            raise ValueError("MD5密码验证失败，无法迁移")
        
        # 生成新的bcrypt哈希
        new_hash = self.hash_password(password)
        
        logger.info("密码从MD5迁移到bcrypt成功", {
            'migration_completed': True
        })
        
        return new_hash
    
    def verify_md5_password(self, password: str, md5_hash: str) -> bool:
        """
        验证MD5密码（仅用于迁移）
        
        Args:
            password: 明文密码
            md5_hash: MD5哈希
            
        Returns:
            bool: 密码是否匹配
        """
        if not password or not md5_hash:
            return False
        
        try:
            calculated_hash = hashlib.md5(password.encode('utf-8')).hexdigest()
            return calculated_hash == md5_hash.lower()
        except Exception as e:
            logger.error(f"MD5密码验证失败: {e}")
            return False
    
    def verify_password_any_format(self, password: str, stored_hash: str) -> tuple:
        """
        验证密码，自动检测哈希格式
        
        Args:
            password: 明文密码
            stored_hash: 存储的哈希密码
            
        Returns:
            tuple: (验证结果, 是否需要迁移, 新哈希)
        """
        if not password or not stored_hash:
            logger.warning("密码或哈希为空", {
                'has_password': bool(password),
                'has_stored_hash': bool(stored_hash)
            })
            return False, False, None
        
        logger.info("开始验证密码", {
            'stored_hash_length': len(stored_hash),
            'stored_hash_prefix': stored_hash[:10] if len(stored_hash) > 10 else stored_hash,
            'is_bcrypt': self.is_bcrypt_hash(stored_hash),
            'is_md5': self.is_md5_hash(stored_hash)
        })
        
        # 检查是否为bcrypt格式
        if self.is_bcrypt_hash(stored_hash):
            logger.info("检测到bcrypt格式密码")
            result = self.verify_password(password, stored_hash)
            return result, False, None
        
        # 检查是否为MD5格式
        elif self.is_md5_hash(stored_hash):
            logger.info("检测到MD5格式密码，尝试验证")
            result = self.verify_md5_password(password, stored_hash)
            logger.info("MD5密码验证结果", {
                'verification_result': result
            })
            if result:
                # 密码正确，需要迁移到bcrypt
                new_hash = self.hash_password(password)
                logger.warning("检测到MD5密码，已自动迁移到bcrypt", {
                    'migration_needed': True
                })
                return True, True, new_hash
            return False, False, None
        
        else:
            logger.error("未知的密码哈希格式", {
                'hash_format': 'unknown',
                'hash_length': len(stored_hash),
                'hash_prefix': stored_hash[:10] if len(stored_hash) > 10 else stored_hash,
                'hash_full': stored_hash  # 临时调试，完整哈希值
            })
            return False, False, None

# 全局实例
secure_password = SecurePassword()

def hash_password(password: str) -> str:
    """便捷函数：哈希密码"""
    return secure_password.hash_password(password)

def verify_password(password: str, hashed_password: str) -> bool:
    """便捷函数：验证密码"""
    return secure_password.verify_password(password, hashed_password)

def verify_password_with_migration(password: str, stored_hash: str) -> tuple:
    """便捷函数：验证密码并处理迁移"""
    return secure_password.verify_password_any_format(password, stored_hash)