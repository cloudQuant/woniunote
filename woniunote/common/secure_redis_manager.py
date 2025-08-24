#!/usr/bin/env python3
"""
安全Redis缓存管理器
提供安全的Redis键值管理，防止键值注入和冲突
"""

import hashlib
import re
import time
import json
from typing import Any, Optional, Union, List, Dict
from woniunote.common.redisdb import redis_connect
from woniunote.common.unified_logging import get_simple_logger

logger = get_simple_logger('secure_redis_manager')

class SecureRedisManager:
    """安全Redis管理器"""
    
    def __init__(self, key_prefix: str = "woniunote", 
                 key_separator: str = ":", 
                 max_key_length: int = 250):
        """
        初始化安全Redis管理器
        
        Args:
            key_prefix: 键前缀，用于命名空间隔离
            key_separator: 键分隔符
            max_key_length: 最大键长度
        """
        self.key_prefix = key_prefix
        self.key_separator = key_separator
        self.max_key_length = max_key_length
        self.redis_client = None
        self._connect()
    
    def _connect(self):
        """连接Redis"""
        try:
            self.redis_client = redis_connect()
            if self.redis_client:
                logger.info("Redis连接成功")
            else:
                logger.warning("Redis连接失败，将使用内存缓存")
        except Exception as e:
            logger.error(f"Redis连接异常: {e}")
            self.redis_client = None
    
    def _sanitize_key_part(self, key_part: str) -> str:
        """
        清理键部分，确保安全性
        
        Args:
            key_part: 键的一部分
            
        Returns:
            str: 清理后的键部分
        """
        if not isinstance(key_part, str):
            key_part = str(key_part)
        
        # 移除危险字符
        key_part = re.sub(r'[^\w\-\.@]', '_', key_part)
        
        # 限制长度
        if len(key_part) > 100:
            # 对长键进行哈希
            hash_suffix = hashlib.md5(key_part.encode()).hexdigest()[:8]
            key_part = key_part[:92] + hash_suffix
        
        return key_part
    
    def _build_key(self, *key_parts: str) -> str:
        """
        构建安全的Redis键
        
        Args:
            *key_parts: 键的各个部分
            
        Returns:
            str: 完整的Redis键
        """
        # 清理所有键部分
        sanitized_parts = [self._sanitize_key_part(part) for part in key_parts]
        
        # 构建完整键
        full_key = self.key_separator.join([self.key_prefix] + sanitized_parts)
        
        # 检查总长度
        if len(full_key) > self.max_key_length:
            # 对超长键进行哈希
            key_hash = hashlib.sha256(full_key.encode()).hexdigest()[:16]
            full_key = f"{self.key_prefix}{self.key_separator}hashed{self.key_separator}{key_hash}"
        
        return full_key
    
    def set_user_code(self, username: str, code: str, expire_seconds: int = 300) -> bool:
        """
        设置用户验证码
        
        Args:
            username: 用户名
            code: 验证码
            expire_seconds: 过期时间（秒）
            
        Returns:
            bool: 是否设置成功
        """
        if not self.redis_client:
            logger.warning("Redis不可用，无法设置用户验证码")
            return False
        
        try:
            key = self._build_key("user_code", username)
            result = self.redis_client.set(key, code, ex=expire_seconds)
            
            logger.info("设置用户验证码", {
                'username': username,
                'key': key,
                'expire_seconds': expire_seconds,
                'success': bool(result)
            })
            
            return bool(result)
            
        except Exception as e:
            logger.error(f"设置用户验证码失败: {e}")
            return False
    
    def get_user_code(self, username: str) -> Optional[str]:
        """
        获取用户验证码
        
        Args:
            username: 用户名
            
        Returns:
            Optional[str]: 验证码，如果不存在则返回None
        """
        if not self.redis_client:
            logger.warning("Redis不可用，无法获取用户验证码")
            return None
        
        try:
            key = self._build_key("user_code", username)
            code = self.redis_client.get(key)
            
            logger.debug("获取用户验证码", {
                'username': username,
                'key': key,
                'has_code': bool(code)
            })
            
            return code
            
        except Exception as e:
            logger.error(f"获取用户验证码失败: {e}")
            return None
    
    def delete_user_code(self, username: str) -> bool:
        """
        删除用户验证码
        
        Args:
            username: 用户名
            
        Returns:
            bool: 是否删除成功
        """
        if not self.redis_client:
            return False
        
        try:
            key = self._build_key("user_code", username)
            result = self.redis_client.delete(key)
            
            logger.info("删除用户验证码", {
                'username': username,
                'key': key,
                'deleted_count': result
            })
            
            return result > 0
            
        except Exception as e:
            logger.error(f"删除用户验证码失败: {e}")
            return False
    
    def set_user_session(self, user_id: int, session_data: Dict[str, Any], 
                        expire_seconds: int = 3600) -> bool:
        """
        设置用户会话数据
        
        Args:
            user_id: 用户ID
            session_data: 会话数据
            expire_seconds: 过期时间（秒）
            
        Returns:
            bool: 是否设置成功
        """
        if not self.redis_client:
            return False
        
        try:
            key = self._build_key("user_session", str(user_id))
            json_data = json.dumps(session_data)
            result = self.redis_client.set(key, json_data, ex=expire_seconds)
            
            logger.info("设置用户会话", {
                'user_id': user_id,
                'key': key,
                'expire_seconds': expire_seconds,
                'success': bool(result)
            })
            
            return bool(result)
            
        except Exception as e:
            logger.error(f"设置用户会话失败: {e}")
            return False
    
    def get_user_session(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        获取用户会话数据
        
        Args:
            user_id: 用户ID
            
        Returns:
            Optional[Dict]: 会话数据，如果不存在则返回None
        """
        if not self.redis_client:
            return None
        
        try:
            key = self._build_key("user_session", str(user_id))
            json_data = self.redis_client.get(key)
            
            if json_data:
                session_data = json.loads(json_data)
                logger.debug("获取用户会话", {
                    'user_id': user_id,
                    'key': key,
                    'has_session': True
                })
                return session_data
            else:
                logger.debug("用户会话不存在", {
                    'user_id': user_id,
                    'key': key
                })
                return None
                
        except Exception as e:
            logger.error(f"获取用户会话失败: {e}")
            return None
    
    def set_cache(self, cache_type: str, cache_key: str, data: Any, 
                  expire_seconds: int = 300) -> bool:
        """
        设置通用缓存
        
        Args:
            cache_type: 缓存类型
            cache_key: 缓存键
            data: 缓存数据
            expire_seconds: 过期时间（秒）
            
        Returns:
            bool: 是否设置成功
        """
        if not self.redis_client:
            return False
        
        try:
            key = self._build_key("cache", cache_type, cache_key)
            
            # 序列化数据
            if isinstance(data, (dict, list)):
                serialized_data = json.dumps(data)
            else:
                serialized_data = str(data)
            
            result = self.redis_client.set(key, serialized_data, ex=expire_seconds)
            
            logger.debug("设置缓存", {
                'cache_type': cache_type,
                'cache_key': cache_key,
                'key': key,
                'expire_seconds': expire_seconds,
                'success': bool(result)
            })
            
            return bool(result)
            
        except Exception as e:
            logger.error(f"设置缓存失败: {e}")
            return False
    
    def get_cache(self, cache_type: str, cache_key: str, 
                  return_json: bool = False) -> Optional[Any]:
        """
        获取通用缓存
        
        Args:
            cache_type: 缓存类型
            cache_key: 缓存键
            return_json: 是否返回JSON格式
            
        Returns:
            Optional[Any]: 缓存数据，如果不存在则返回None
        """
        if not self.redis_client:
            return None
        
        try:
            key = self._build_key("cache", cache_type, cache_key)
            data = self.redis_client.get(key)
            
            if data is None:
                return None
            
            # 反序列化数据
            if return_json:
                try:
                    return json.loads(data)
                except json.JSONDecodeError:
                    logger.warning(f"缓存数据不是有效JSON: {key}")
                    return data
            else:
                return data
                
        except Exception as e:
            logger.error(f"获取缓存失败: {e}")
            return None
    
    def delete_cache(self, cache_type: str, cache_key: str) -> bool:
        """
        删除缓存
        
        Args:
            cache_type: 缓存类型
            cache_key: 缓存键
            
        Returns:
            bool: 是否删除成功
        """
        if not self.redis_client:
            return False
        
        try:
            key = self._build_key("cache", cache_type, cache_key)
            result = self.redis_client.delete(key)
            
            logger.debug("删除缓存", {
                'cache_type': cache_type,
                'cache_key': cache_key,
                'key': key,
                'deleted_count': result
            })
            
            return result > 0
            
        except Exception as e:
            logger.error(f"删除缓存失败: {e}")
            return False
    
    def clear_user_data(self, username: str) -> bool:
        """
        清除用户相关的所有缓存数据
        
        Args:
            username: 用户名
            
        Returns:
            bool: 是否清除成功
        """
        if not self.redis_client:
            return False
        
        try:
            # 查找用户相关的所有键
            pattern = self._build_key("*", f"*{username}*")
            keys = self.redis_client.keys(pattern)
            
            if keys:
                deleted_count = self.redis_client.delete(*keys)
                logger.info(f"清除用户数据: {username}, 删除键数量: {deleted_count}")
                return deleted_count > 0
            else:
                logger.info(f"用户无缓存数据: {username}")
                return True
                
        except Exception as e:
            logger.error(f"清除用户数据失败: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取Redis统计信息
        
        Returns:
            Dict: 统计信息
        """
        if not self.redis_client:
            return {'connected': False, 'error': 'Redis不可用'}
        
        try:
            info = self.redis_client.info()
            stats = {
                'connected': True,
                'used_memory': info.get('used_memory_human', 'N/A'),
                'connected_clients': info.get('connected_clients', 0),
                'total_commands_processed': info.get('total_commands_processed', 0),
                'keyspace_hits': info.get('keyspace_hits', 0),
                'keyspace_misses': info.get('keyspace_misses', 0),
            }
            
            # 计算命中率
            hits = stats['keyspace_hits']
            misses = stats['keyspace_misses']
            if hits + misses > 0:
                stats['hit_rate'] = hits / (hits + misses)
            else:
                stats['hit_rate'] = 0
            
            return stats
            
        except Exception as e:
            logger.error(f"获取Redis统计信息失败: {e}")
            return {'connected': False, 'error': str(e)}

# 全局实例
secure_redis_manager = SecureRedisManager()

# 便捷函数
def set_user_verification_code(username: str, code: str, expire_seconds: int = 300) -> bool:
    """设置用户验证码"""
    return secure_redis_manager.set_user_code(username, code, expire_seconds)

def get_user_verification_code(username: str) -> Optional[str]:
    """获取用户验证码"""
    return secure_redis_manager.get_user_code(username)

def delete_user_verification_code(username: str) -> bool:
    """删除用户验证码"""
    return secure_redis_manager.delete_user_code(username)

def set_secure_cache(cache_type: str, cache_key: str, data: Any, expire_seconds: int = 300) -> bool:
    """设置安全缓存"""
    return secure_redis_manager.set_cache(cache_type, cache_key, data, expire_seconds)

def get_secure_cache(cache_type: str, cache_key: str, return_json: bool = False) -> Optional[Any]:
    """获取安全缓存"""
    return secure_redis_manager.get_cache(cache_type, cache_key, return_json)