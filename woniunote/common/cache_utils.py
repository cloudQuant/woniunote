#!/usr/bin/env python3
"""
缓存工具模块 - 支持Redis和内存缓存
"""

import time
import json
import hashlib
import logging
from typing import Any, Optional, Dict, Union
from functools import wraps
from threading import Lock

logger = logging.getLogger(__name__)

class MemoryCache:
    """内存缓存实现"""
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.lock = Lock()
    
    def _is_expired(self, item: Dict[str, Any]) -> bool:
        """检查缓存项是否过期"""
        return time.time() > item['expires_at']
    
    def _cleanup_expired(self):
        """清理过期项"""
        current_time = time.time()
        expired_keys = [
            key for key, item in self.cache.items()
            if current_time > item['expires_at']
        ]
        for key in expired_keys:
            del self.cache[key]
    
    def _evict_lru(self):
        """LRU驱逐策略"""
        if len(self.cache) >= self.max_size:
            # 删除最旧的项
            oldest_key = min(
                self.cache.keys(),
                key=lambda k: self.cache[k]['accessed_at']
            )
            del self.cache[oldest_key]
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        with self.lock:
            if key in self.cache:
                item = self.cache[key]
                if not self._is_expired(item):
                    item['accessed_at'] = time.time()
                    return item['value']
                else:
                    del self.cache[key]
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置缓存值"""
        try:
            with self.lock:
                self._cleanup_expired()
                self._evict_lru()
                
                expires_at = time.time() + (ttl or self.default_ttl)
                self.cache[key] = {
                    'value': value,
                    'expires_at': expires_at,
                    'accessed_at': time.time(),
                    'created_at': time.time()
                }
                return True
        except Exception as e:
            logger.error(f"Memory cache set error: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """删除缓存项"""
        with self.lock:
            if key in self.cache:
                del self.cache[key]
                return True
            return False
    
    def clear(self) -> bool:
        """清空缓存"""
        with self.lock:
            self.cache.clear()
            return True
    
    def stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        with self.lock:
            self._cleanup_expired()
            return {
                'size': len(self.cache),
                'max_size': self.max_size,
                'hit_rate': getattr(self, '_hit_count', 0) / max(getattr(self, '_total_count', 1), 1)
            }


class RedisCache:
    """Redis缓存实现"""
    
    def __init__(self, redis_client=None, default_ttl: int = 300, key_prefix: str = "woniunote:"):
        self.redis = redis_client
        self.default_ttl = default_ttl
        self.key_prefix = key_prefix
        self.available = self._test_connection()
    
    def _test_connection(self) -> bool:
        """测试Redis连接"""
        if not self.redis:
            return False
        try:
            self.redis.ping()
            return True
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}")
            return False
    
    def _make_key(self, key: str) -> str:
        """生成带前缀的key"""
        return f"{self.key_prefix}{key}"
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        if not self.available:
            return None
        
        try:
            redis_key = self._make_key(key)
            value = self.redis.get(redis_key)
            if value:
                return json.loads(value.decode('utf-8'))
            return None
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置缓存值"""
        if not self.available:
            return False
        
        try:
            redis_key = self._make_key(key)
            json_value = json.dumps(value, ensure_ascii=False, default=str)
            ttl_seconds = ttl or self.default_ttl
            return self.redis.setex(redis_key, ttl_seconds, json_value)
        except Exception as e:
            logger.error(f"Redis set error: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """删除缓存项"""
        if not self.available:
            return False
        
        try:
            redis_key = self._make_key(key)
            return bool(self.redis.delete(redis_key))
        except Exception as e:
            logger.error(f"Redis delete error: {e}")
            return False
    
    def clear(self) -> bool:
        """清空缓存（匹配前缀的键）"""
        if not self.available:
            return False
        
        try:
            pattern = f"{self.key_prefix}*"
            keys = self.redis.keys(pattern)
            if keys:
                return bool(self.redis.delete(*keys))
            return True
        except Exception as e:
            logger.error(f"Redis clear error: {e}")
            return False


class CacheManager:
    """缓存管理器 - 统一缓存接口"""
    
    def __init__(self, primary_cache=None, fallback_cache=None):
        self.primary = primary_cache
        self.fallback = fallback_cache or MemoryCache()
        
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        # 先尝试主缓存
        if self.primary:
            value = self.primary.get(key)
            if value is not None:
                return value
        
        # 回退到备用缓存
        return self.fallback.get(key)
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置缓存值"""
        success = True
        
        # 设置主缓存
        if self.primary:
            primary_success = self.primary.set(key, value, ttl)
            success = success and primary_success
        
        # 设置备用缓存
        fallback_success = self.fallback.set(key, value, ttl)
        return success and fallback_success
    
    def delete(self, key: str) -> bool:
        """删除缓存项"""
        success = True
        
        if self.primary:
            success = success and self.primary.delete(key)
        
        return success and self.fallback.delete(key)
    
    def clear(self) -> bool:
        """清空缓存"""
        success = True
        
        if self.primary:
            success = success and self.primary.clear()
        
        return success and self.fallback.clear()


def cache_key(*args, **kwargs) -> str:
    """生成缓存键"""
    key_parts = []
    
    # 处理位置参数
    for arg in args:
        if isinstance(arg, (str, int, float)):
            key_parts.append(str(arg))
        else:
            key_parts.append(hashlib.md5(str(arg).encode()).hexdigest()[:8])
    
    # 处理关键字参数
    if kwargs:
        sorted_kwargs = sorted(kwargs.items())
        kwargs_str = "&".join(f"{k}={v}" for k, v in sorted_kwargs)
        key_parts.append(hashlib.md5(kwargs_str.encode()).hexdigest()[:8])
    
    return ":".join(key_parts)


def cached(ttl: int = 300, key_func=None):
    """缓存装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 获取缓存管理器
            cache_manager = getattr(wrapper, '_cache_manager', None)
            if not cache_manager:
                return func(*args, **kwargs)
            
            # 生成缓存键
            if key_func:
                cache_key_str = key_func(*args, **kwargs)
            else:
                func_name = f"{func.__module__}.{func.__name__}"
                cache_key_str = cache_key(func_name, *args, **kwargs)
            
            # 尝试从缓存获取
            cached_result = cache_manager.get(cache_key_str)
            if cached_result is not None:
                logger.debug(f"Cache hit for key: {cache_key_str}")
                return cached_result
            
            # 执行函数并缓存结果
            try:
                result = func(*args, **kwargs)
                cache_manager.set(cache_key_str, result, ttl)
                logger.debug(f"Cache set for key: {cache_key_str}")
                return result
            except Exception as e:
                logger.error(f"Function execution error: {e}")
                raise
        
        return wrapper
    return decorator


# 全局缓存实例
_global_cache_manager = None

def get_cache_manager() -> CacheManager:
    """获取全局缓存管理器"""
    global _global_cache_manager
    if _global_cache_manager is None:
        _global_cache_manager = CacheManager(fallback_cache=MemoryCache())
    return _global_cache_manager

def init_cache(redis_client=None, config=None):
    """初始化缓存系统"""
    global _global_cache_manager
    
    try:
        # 尝试初始化Redis缓存
        primary_cache = None
        if redis_client:
            primary_cache = RedisCache(
                redis_client=redis_client,
                default_ttl=config.get('default_ttl', 300) if config else 300,
                key_prefix=config.get('key_prefix', 'woniunote:') if config else 'woniunote:'
            )
        
        # 初始化内存缓存作为备用
        fallback_config = config.get('memory', {}) if config else {}
        fallback_cache = MemoryCache(
            max_size=fallback_config.get('max_size', 1000),
            default_ttl=fallback_config.get('default_ttl', 300)
        )
        
        _global_cache_manager = CacheManager(
            primary_cache=primary_cache,
            fallback_cache=fallback_cache
        )
        
        logger.info("Cache system initialized successfully")
        return _global_cache_manager
        
    except Exception as e:
        logger.error(f"Cache initialization error: {e}")
        _global_cache_manager = CacheManager(fallback_cache=MemoryCache())
        return _global_cache_manager 