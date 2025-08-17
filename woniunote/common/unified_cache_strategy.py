#!/usr/bin/env python3
"""
统一缓存策略系统
提供多层缓存、缓存失效、缓存预热等功能
"""

import time
import json
import hashlib
import threading
from typing import Dict, Any, Optional, List, Callable, Union
from functools import wraps
from enum import Enum
from dataclasses import dataclass, asdict
from woniunote.common.simple_logger import get_simple_logger
from woniunote.common.secure_redis_manager import secure_redis_manager

logger = get_simple_logger('unified_cache_strategy')

class CacheLevel(Enum):
    """缓存级别"""
    L1_MEMORY = "l1_memory"      # 内存缓存（最快，容量小）
    L2_REDIS = "l2_redis"        # Redis缓存（快，容量中）
    L3_DATABASE = "l3_database"  # 数据库缓存（慢，容量大）

class CacheStrategy(Enum):
    """缓存策略"""
    CACHE_ASIDE = "cache_aside"          # 旁路缓存
    WRITE_THROUGH = "write_through"      # 写穿透
    WRITE_BEHIND = "write_behind"        # 写回
    REFRESH_AHEAD = "refresh_ahead"      # 预刷新

@dataclass
class CacheConfig:
    """缓存配置"""
    ttl: int = 300                      # 存活时间（秒）
    max_size: int = 1000                # 最大条目数
    strategy: CacheStrategy = CacheStrategy.CACHE_ASIDE
    levels: List[CacheLevel] = None     # 缓存级别
    serialize: bool = True              # 是否序列化
    compress: bool = False              # 是否压缩
    
    def __post_init__(self):
        if self.levels is None:
            self.levels = [CacheLevel.L1_MEMORY, CacheLevel.L2_REDIS]

class MemoryCache:
    """内存缓存实现"""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.cache = {}
        self.access_times = {}
        self.lock = threading.RLock()
    
    def get(self, key: str) -> Optional[Any]:
        with self.lock:
            if key in self.cache:
                self.access_times[key] = time.time()
                return self.cache[key]
            return None
    
    def set(self, key: str, value: Any, ttl: int = 300):
        with self.lock:
            # 如果缓存已满，移除最老的条目
            if len(self.cache) >= self.max_size:
                self._evict_lru()
            
            self.cache[key] = {
                'value': value,
                'created_at': time.time(),
                'ttl': ttl
            }
            self.access_times[key] = time.time()
    
    def delete(self, key: str):
        with self.lock:
            self.cache.pop(key, None)
            self.access_times.pop(key, None)
    
    def clear(self):
        with self.lock:
            self.cache.clear()
            self.access_times.clear()
    
    def _evict_lru(self):
        """移除最近最少使用的条目"""
        if not self.access_times:
            return
        
        lru_key = min(self.access_times.keys(), 
                     key=lambda k: self.access_times[k])
        self.delete(lru_key)
    
    def cleanup_expired(self):
        """清理过期条目"""
        current_time = time.time()
        expired_keys = []
        
        with self.lock:
            for key, item in self.cache.items():
                if current_time - item['created_at'] > item['ttl']:
                    expired_keys.append(key)
            
            for key in expired_keys:
                self.delete(key)
        
        return len(expired_keys)

class MultiLevelCache:
    """多级缓存系统"""
    
    def __init__(self, config: CacheConfig):
        self.config = config
        self.memory_cache = MemoryCache(config.max_size)
        self.redis_cache = secure_redis_manager
        self.hit_stats = {
            'l1_hits': 0,
            'l2_hits': 0,
            'misses': 0,
            'total_requests': 0
        }
        self.lock = threading.RLock()
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        with self.lock:
            self.hit_stats['total_requests'] += 1
        
        cache_key = self._build_cache_key(key)
        
        # L1: 内存缓存
        if CacheLevel.L1_MEMORY in self.config.levels:
            value = self.memory_cache.get(cache_key)
            if value is not None:
                with self.lock:
                    self.hit_stats['l1_hits'] += 1
                logger.debug(f"L1缓存命中: {key}")
                return self._deserialize(value['value'])
        
        # L2: Redis缓存
        if CacheLevel.L2_REDIS in self.config.levels:
            try:
                redis_value = self.redis_cache.get_cache('unified', cache_key, return_json=True)
                if redis_value is not None:
                    with self.lock:
                        self.hit_stats['l2_hits'] += 1
                    
                    # 回填L1缓存
                    if CacheLevel.L1_MEMORY in self.config.levels:
                        self.memory_cache.set(cache_key, redis_value, self.config.ttl)
                    
                    logger.debug(f"L2缓存命中: {key}")
                    return self._deserialize(redis_value)
            except Exception as e:
                logger.warning(f"Redis缓存读取失败: {e}")
        
        # 缓存未命中
        with self.lock:
            self.hit_stats['misses'] += 1
        logger.debug(f"缓存未命中: {key}")
        return None
    
    def set(self, key: str, value: Any, ttl: int = None):
        """设置缓存值"""
        ttl = ttl or self.config.ttl
        cache_key = self._build_cache_key(key)
        serialized_value = self._serialize(value)
        
        # L1: 内存缓存
        if CacheLevel.L1_MEMORY in self.config.levels:
            self.memory_cache.set(cache_key, serialized_value, ttl)
        
        # L2: Redis缓存
        if CacheLevel.L2_REDIS in self.config.levels:
            try:
                self.redis_cache.set_cache('unified', cache_key, serialized_value, ttl)
            except Exception as e:
                logger.warning(f"Redis缓存写入失败: {e}")
        
        logger.debug(f"缓存已设置: {key}, TTL: {ttl}秒")
    
    def delete(self, key: str):
        """删除缓存值"""
        cache_key = self._build_cache_key(key)
        
        # L1: 内存缓存
        if CacheLevel.L1_MEMORY in self.config.levels:
            self.memory_cache.delete(cache_key)
        
        # L2: Redis缓存
        if CacheLevel.L2_REDIS in self.config.levels:
            try:
                self.redis_cache.delete_cache('unified', cache_key)
            except Exception as e:
                logger.warning(f"Redis缓存删除失败: {e}")
        
        logger.debug(f"缓存已删除: {key}")
    
    def clear(self, pattern: str = None):
        """清空缓存"""
        if pattern:
            # 模式匹配清空
            # 实现模式匹配逻辑（简化实现）
            pass
        else:
            # 清空所有缓存
            if CacheLevel.L1_MEMORY in self.config.levels:
                self.memory_cache.clear()
            
            logger.info("缓存已清空")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        with self.lock:
            stats = self.hit_stats.copy()
        
        if stats['total_requests'] > 0:
            stats['l1_hit_rate'] = stats['l1_hits'] / stats['total_requests']
            stats['l2_hit_rate'] = stats['l2_hits'] / stats['total_requests']
            stats['total_hit_rate'] = (stats['l1_hits'] + stats['l2_hits']) / stats['total_requests']
            stats['miss_rate'] = stats['misses'] / stats['total_requests']
        else:
            stats.update({
                'l1_hit_rate': 0.0,
                'l2_hit_rate': 0.0,
                'total_hit_rate': 0.0,
                'miss_rate': 0.0
            })
        
        return stats
    
    def _build_cache_key(self, key: str) -> str:
        """构建缓存键"""
        # 添加命名空间和版本信息
        namespace = "woniunote"
        version = "v1"
        return f"{namespace}:{version}:{key}"
    
    def _serialize(self, value: Any) -> Any:
        """序列化值"""
        if not self.config.serialize:
            return value
        
        try:
            if isinstance(value, (dict, list)):
                return json.dumps(value, ensure_ascii=False)
            else:
                return value
        except Exception as e:
            logger.warning(f"序列化失败: {e}")
            return value
    
    def _deserialize(self, value: Any) -> Any:
        """反序列化值"""
        if not self.config.serialize:
            return value
        
        try:
            if isinstance(value, str):
                return json.loads(value)
            else:
                return value
        except Exception as e:
            logger.warning(f"反序列化失败: {e}")
            return value

class CacheManager:
    """缓存管理器"""
    
    def __init__(self):
        self.caches = {}
        self.default_config = CacheConfig()
        self.lock = threading.RLock()
    
    def get_cache(self, name: str, config: CacheConfig = None) -> MultiLevelCache:
        """获取或创建缓存实例"""
        with self.lock:
            if name not in self.caches:
                cache_config = config or self.default_config
                self.caches[name] = MultiLevelCache(cache_config)
                logger.info(f"创建缓存实例: {name}")
            
            return self.caches[name]
    
    def invalidate_cache(self, name: str, key: str = None):
        """使缓存失效"""
        with self.lock:
            if name in self.caches:
                if key:
                    self.caches[name].delete(key)
                else:
                    self.caches[name].clear()
                logger.info(f"缓存失效: {name}, key: {key}")
    
    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """获取所有缓存统计"""
        stats = {}
        with self.lock:
            for name, cache in self.caches.items():
                stats[name] = cache.get_stats()
        return stats

def cache_result(cache_name: str = 'default', ttl: int = 300, 
                key_func: Callable = None, config: CacheConfig = None):
    """缓存结果装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存键
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = f"{func.__module__}.{func.__name__}:{hash(str(args) + str(sorted(kwargs.items())))}"
            
            # 获取缓存实例
            cache = cache_manager.get_cache(cache_name, config)
            
            # 尝试从缓存获取
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"缓存命中: {cache_key}")
                return cached_result
            
            # 执行函数并缓存结果
            try:
                result = func(*args, **kwargs)
                cache.set(cache_key, result, ttl)
                logger.debug(f"结果已缓存: {cache_key}")
                return result
            except Exception as e:
                logger.error(f"函数执行失败: {func.__name__}, 错误: {e}")
                raise
        
        return wrapper
    return decorator

def cache_invalidate(cache_name: str = 'default', key_func: Callable = None):
    """缓存失效装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 执行函数
            result = func(*args, **kwargs)
            
            # 生成失效键
            if key_func:
                cache_key = key_func(*args, **kwargs)
                cache_manager.invalidate_cache(cache_name, cache_key)
            else:
                # 清空整个缓存
                cache_manager.invalidate_cache(cache_name)
            
            return result
        
        return wrapper
    return decorator

def warm_up_cache(cache_name: str, data_loader: Callable, 
                 key_extractor: Callable, ttl: int = 300):
    """缓存预热"""
    try:
        cache = cache_manager.get_cache(cache_name)
        data_items = data_loader()
        
        warm_up_count = 0
        for item in data_items:
            try:
                key = key_extractor(item)
                cache.set(key, item, ttl)
                warm_up_count += 1
            except Exception as e:
                logger.warning(f"缓存预热单项失败: {e}")
        
        logger.info(f"缓存预热完成: {cache_name}, 预热数量: {warm_up_count}")
        return warm_up_count
        
    except Exception as e:
        logger.error(f"缓存预热失败: {cache_name}, 错误: {e}")
        return 0

class ArticleCache:
    """文章缓存专用类"""
    
    def __init__(self):
        self.config = CacheConfig(ttl=600, max_size=500)  # 10分钟TTL
        self.cache = cache_manager.get_cache('articles', self.config)
    
    def get_article(self, article_id: int) -> Optional[Dict[str, Any]]:
        """获取文章缓存"""
        return self.cache.get(f"article:{article_id}")
    
    def set_article(self, article_id: int, article_data: Dict[str, Any]):
        """设置文章缓存"""
        self.cache.set(f"article:{article_id}", article_data)
    
    def invalidate_article(self, article_id: int):
        """使文章缓存失效"""
        self.cache.delete(f"article:{article_id}")
    
    def get_article_list(self, page: int, page_size: int) -> Optional[Dict[str, Any]]:
        """获取文章列表缓存"""
        return self.cache.get(f"article_list:{page}:{page_size}")
    
    def set_article_list(self, page: int, page_size: int, list_data: Dict[str, Any]):
        """设置文章列表缓存"""
        self.cache.set(f"article_list:{page}:{page_size}", list_data, ttl=300)  # 5分钟TTL
    
    def invalidate_article_lists(self):
        """使所有文章列表缓存失效"""
        # 简化实现：清空整个缓存
        self.cache.clear()

class UserCache:
    """用户缓存专用类"""
    
    def __init__(self):
        self.config = CacheConfig(ttl=1800, max_size=1000)  # 30分钟TTL
        self.cache = cache_manager.get_cache('users', self.config)
    
    def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """获取用户缓存"""
        return self.cache.get(f"user:{user_id}")
    
    def set_user(self, user_id: int, user_data: Dict[str, Any]):
        """设置用户缓存"""
        self.cache.set(f"user:{user_id}", user_data)
    
    def invalidate_user(self, user_id: int):
        """使用户缓存失效"""
        self.cache.delete(f"user:{user_id}")
    
    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """根据用户名获取用户缓存"""
        return self.cache.get(f"user_username:{username}")
    
    def set_user_by_username(self, username: str, user_data: Dict[str, Any]):
        """根据用户名设置用户缓存"""
        self.cache.set(f"user_username:{username}", user_data)

# 全局实例
cache_manager = CacheManager()
article_cache = ArticleCache()
user_cache = UserCache()

# 便捷函数
def get_cache(name: str, config: CacheConfig = None) -> MultiLevelCache:
    """获取缓存实例便捷函数"""
    return cache_manager.get_cache(name, config)

def invalidate_cache(name: str, key: str = None):
    """缓存失效便捷函数"""
    cache_manager.invalidate_cache(name, key)

def get_cache_stats() -> Dict[str, Dict[str, Any]]:
    """获取缓存统计便捷函数"""
    return cache_manager.get_all_stats()