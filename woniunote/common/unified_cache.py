#!/usr/bin/env python3
"""
统一的缓存策略模块
整合所有缓存相关功能：内存缓存、Redis缓存、静态资源缓存等
"""

import os
import time
import json
import hashlib
import gzip
import threading
from typing import Dict, Any, Optional, List, Callable, Union, Tuple
from functools import wraps
from enum import Enum
from dataclasses import dataclass, asdict
from pathlib import Path

from .unified_logging import get_logger

logger = get_logger('unified_cache')

# ==================== 枚举定义 ====================

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
    LRU = "lru"                          # 最近最少使用
    TTL = "ttl"                          # 时间到期

# ==================== 数据类定义 ====================

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

@dataclass
class CacheStats:
    """缓存统计信息"""
    hits: int = 0
    misses: int = 0
    sets: int = 0
    deletes: int = 0
    evictions: int = 0
    memory_size: int = 0
    redis_size: int = 0
    hit_rate: float = 0.0
    total_requests: int = 0

# ==================== 内存缓存实现 ====================

class MemoryCache:
    """内存缓存实现"""
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache = {}
        self.access_times = {}
        self.expiry_times = {}
        self.lock = threading.RLock()
        
        # 启动清理线程
        self._cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self._cleanup_thread.start()
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        with self.lock:
            if key in self.cache:
                # 检查是否过期
                if time.time() > self.expiry_times.get(key, 0):
                    del self.cache[key]
                    del self.access_times[key]
                    del self.expiry_times[key]
                    return None
                
                # 更新访问时间
                self.access_times[key] = time.time()
                return self.cache[key]
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置缓存值"""
        try:
            with self.lock:
                # 如果缓存已满，移除最老的条目
                if len(self.cache) >= self.max_size:
                    self._evict_lru()
                
                ttl = ttl or self.default_ttl
                expires_at = time.time() + ttl
                
                self.cache[key] = value
                self.access_times[key] = time.time()
                self.expiry_times[key] = expires_at
                
                return True
        except Exception as e:
            logger.error(f"Memory cache set error: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """删除缓存项"""
        with self.lock:
            if key in self.cache:
                del self.cache[key]
                del self.access_times[key]
                del self.expiry_times[key]
                return True
            return False
    
    def clear(self) -> bool:
        """清空缓存"""
        with self.lock:
            self.cache.clear()
            self.access_times.clear()
            self.expiry_times.clear()
            return True
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        with self.lock:
            return {
                'size': len(self.cache),
                'max_size': self.max_size,
                'usage_percent': (len(self.cache) / self.max_size) * 100
            }
    
    def _evict_lru(self):
        """移除最近最少使用的条目"""
        if not self.access_times:
            return
        
        lru_key = min(self.access_times.keys(), 
                     key=lambda k: self.access_times[k])
        self.delete(lru_key)
    
    def _cleanup_expired(self):
        """清理过期条目"""
        current_time = time.time()
        expired_keys = []
        
        with self.lock:
            for key, expiry_time in self.expiry_times.items():
                if current_time > expiry_time:
                    expired_keys.append(key)
            
            for key in expired_keys:
                self.delete(key)
    
    def _cleanup_loop(self):
        """清理循环"""
        while True:
            try:
                time.sleep(60)  # 每分钟清理一次
                self._cleanup_expired()
            except Exception as e:
                logger.error(f"Memory cache cleanup error: {e}")

# ==================== Redis缓存实现 ====================

class RedisCache:
    """Redis缓存实现"""
    
    def __init__(self, redis_client=None, default_ttl: int = 3600):
        self.redis_client = redis_client
        self.default_ttl = default_ttl
        self.available = redis_client is not None
        
        if not self.available:
            logger.warning("Redis客户端未配置，Redis缓存功能不可用")
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        if not self.available:
            return None
        
        try:
            value = self.redis_client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Redis cache get error: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置缓存值"""
        if not self.available:
            return False
        
        try:
            ttl = ttl or self.default_ttl
            serialized_value = json.dumps(value, ensure_ascii=False)
            return self.redis_client.setex(key, ttl, serialized_value)
        except Exception as e:
            logger.error(f"Redis cache set error: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """删除缓存项"""
        if not self.available:
            return False
        
        try:
            return bool(self.redis_client.delete(key))
        except Exception as e:
            logger.error(f"Redis cache delete error: {e}")
            return False
    
    def clear(self, pattern: str = "*") -> bool:
        """清空缓存"""
        if not self.available:
            return False
        
        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                return bool(self.redis_client.delete(*keys))
            return True
        except Exception as e:
            logger.error(f"Redis cache clear error: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        if not self.available:
            return {'available': False}
        
        try:
            info = self.redis_client.info()
            return {
                'available': True,
                'used_memory': info.get('used_memory', 0),
                'used_memory_human': info.get('used_memory_human', '0B'),
                'connected_clients': info.get('connected_clients', 0),
                'total_commands_processed': info.get('total_commands_processed', 0)
            }
        except Exception as e:
            logger.error(f"Redis stats error: {e}")
            return {'available': False, 'error': str(e)}

# ==================== 静态资源缓存优化器 ====================

class StaticCacheOptimizer:
    """静态资源缓存优化器"""
    
    def __init__(self):
        self.cache_headers = {}
        self.compressed_files = {}
        self.file_hashes = {}
        self.last_modified_times = {}
        
        # 缓存配置
        self.cache_config = {
            # 文件类型到缓存时长的映射 (秒)
            '.css': 31536000,      # 1年
            '.js': 31536000,       # 1年
            '.png': 2592000,       # 30天
            '.jpg': 2592000,       # 30天
            '.jpeg': 2592000,      # 30天
            '.gif': 2592000,       # 30天
            '.ico': 31536000,      # 1年
            '.woff': 31536000,     # 1年
            '.woff2': 31536000,    # 1年
            '.ttf': 31536000,      # 1年
            '.eot': 31536000,      # 1年
            '.svg': 2592000,       # 30天
            '.webp': 2592000,      # 30天
            'default': 86400,      # 1天
        }
        
        # 需要压缩的文件类型
        self.compressible_types = {
            '.css', '.js', '.html', '.htm', '.xml', '.json', '.svg', '.txt'
        }
    
    def get_cache_headers(self, file_path: str) -> Dict[str, str]:
        """获取缓存头"""
        file_ext = Path(file_path).suffix.lower()
        cache_duration = self.cache_config.get(file_ext, self.cache_config['default'])
        
        return {
            'Cache-Control': f'public, max-age={cache_duration}',
            'Expires': time.strftime('%a, %d %b %Y %H:%M:%S GMT', 
                                   time.gmtime(time.time() + cache_duration))
        }
    
    def should_compress(self, file_path: str) -> bool:
        """判断文件是否应该压缩"""
        file_ext = Path(file_path).suffix.lower()
        return file_ext in self.compressible_types
    
    def compress_content(self, content: bytes) -> bytes:
        """压缩内容"""
        try:
            return gzip.compress(content)
        except Exception as e:
            logger.error(f"Content compression error: {e}")
            return content
    
    def get_file_hash(self, file_path: str) -> str:
        """获取文件哈希值"""
        if file_path in self.file_hashes:
            return self.file_hashes[file_path]
        
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
                file_hash = hashlib.md5(content).hexdigest()[:8]
                self.file_hashes[file_path] = file_hash
                return file_hash
        except Exception as e:
            logger.error(f"File hash error: {e}")
            return ""

# ==================== 统一缓存管理器 ====================

class UnifiedCacheManager:
    """统一的缓存管理器"""
    
    def __init__(self, config: CacheConfig = None, redis_client=None):
        self.config = config or CacheConfig()
        self.logger = get_logger('unified_cache')
        
        # 初始化各个缓存层
        self.memory_cache = MemoryCache(
            max_size=self.config.max_size,
            default_ttl=self.config.ttl
        )
        
        self.redis_cache = RedisCache(
            redis_client=redis_client,
            default_ttl=self.config.ttl
        )
        
        self.static_optimizer = StaticCacheOptimizer()
        
        # 统计信息
        self.stats = CacheStats()
        
        # 缓存键生成器
        self.key_generator = CacheKeyGenerator()
        
        logger.info("统一缓存管理器初始化完成")
    
    def get(self, key: str, params: Dict[str, Any] = None) -> Optional[Any]:
        """获取缓存值（多层缓存）"""
        cache_key = self.key_generator.generate_key(key, params)
        
        # 首先尝试内存缓存
        value = self.memory_cache.get(cache_key)
        if value is not None:
            self.stats.hits += 1
            return value
        
        # 然后尝试Redis缓存
        value = self.redis_cache.get(cache_key)
        if value is not None:
            # 回填到内存缓存
            self.memory_cache.set(cache_key, value, self.config.ttl)
            self.stats.hits += 1
            return value
        
        self.stats.misses += 1
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None, 
            params: Dict[str, Any] = None) -> bool:
        """设置缓存值（多层缓存）"""
        cache_key = self.key_generator.generate_key(key, params)
        ttl = ttl or self.config.ttl
        
        success = True
        
        # 根据策略设置缓存
        if self.config.strategy == CacheStrategy.WRITE_THROUGH:
            # 写穿透：同时写入所有层
            success &= self.memory_cache.set(cache_key, value, ttl)
            success &= self.redis_cache.set(cache_key, value, ttl)
        elif self.config.strategy == CacheStrategy.WRITE_BEHIND:
            # 写回：先写内存，异步写Redis
            success &= self.memory_cache.set(cache_key, value, ttl)
            # 异步写入Redis
            threading.Thread(target=self._async_set_redis, 
                           args=(cache_key, value, ttl), 
                           daemon=True).start()
        else:
            # 默认策略：只写内存
            success &= self.memory_cache.set(cache_key, value, ttl)
        
        if success:
            self.stats.sets += 1
        
        return success
    
    def delete(self, key: str, params: Dict[str, Any] = None) -> bool:
        """删除缓存值"""
        cache_key = self.key_generator.generate_key(key, params)
        
        success = True
        success &= self.memory_cache.delete(cache_key)
        success &= self.redis_cache.delete(cache_key)
        
        if success:
            self.stats.deletes += 1
        
        return success
    
    def clear(self, pattern: str = None) -> int:
        """清空缓存"""
        count = 0
        
        if pattern:
            # 根据模式清除
            count += self.memory_cache.clear()
            count += self.redis_cache.clear(pattern)
        else:
            # 清除所有
            count += self.memory_cache.clear()
            count += self.redis_cache.clear()
        
        return count
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        self.stats.total_requests = self.stats.hits + self.stats.misses
        if self.stats.total_requests > 0:
            self.stats.hit_rate = (self.stats.hits / self.stats.total_requests) * 100
        
        memory_stats = self.memory_cache.get_stats()
        redis_stats = self.redis_cache.get_stats()
        
        return {
            'overall': asdict(self.stats),
            'memory': memory_stats,
            'redis': redis_stats,
            'config': asdict(self.config)
        }
    
    def optimize_static_files(self, file_path: str) -> Dict[str, Any]:
        """优化静态文件缓存"""
        return {
            'cache_headers': self.static_optimizer.get_cache_headers(file_path),
            'should_compress': self.static_optimizer.should_compress(file_path),
            'file_hash': self.static_optimizer.get_file_hash(file_path)
        }
    
    def _async_set_redis(self, key: str, value: Any, ttl: int):
        """异步设置Redis缓存"""
        try:
            self.redis_cache.set(key, value, ttl)
        except Exception as e:
            logger.error(f"Async Redis set error: {e}")

# ==================== 缓存键生成器 ====================

class CacheKeyGenerator:
    """缓存键生成器"""
    
    def __init__(self):
        self.prefix = "woniunote"
        self.separator = ":"
    
    def generate_key(self, key: str, params: Dict[str, Any] = None) -> str:
        """生成缓存键"""
        if not params:
            return f"{self.prefix}{self.separator}{key}"
        
        # 将参数序列化并哈希
        try:
            param_str = json.dumps(params, sort_keys=True, ensure_ascii=False)
            param_hash = hashlib.md5(param_str.encode()).hexdigest()[:8]
            return f"{self.prefix}{self.separator}{key}{self.separator}{param_hash}"
        except Exception:
            # 如果序列化失败，使用简单拼接
            param_str = str(hash(str(params)))
            return f"{self.prefix}{self.separator}{key}{self.separator}{param_str}"

# ==================== 装饰器 ====================

def cached(ttl: int = 300, key_prefix: str = "", cache_manager: UnifiedCacheManager = None):
    """
    缓存装饰器
    
    Args:
        ttl: 缓存生存时间（秒）
        key_prefix: 缓存键前缀
        cache_manager: 缓存管理器实例
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存键
            cache_key = f"{key_prefix}:{func.__name__}:{hash(str(args) + str(kwargs))}"
            
            # 尝试从缓存获取
            if cache_manager:
                cached_result = cache_manager.get(cache_key)
                if cached_result is not None:
                    return cached_result
            
            # 执行函数
            result = func(*args, **kwargs)
            
            # 缓存结果
            if cache_manager:
                cache_manager.set(cache_key, result, ttl)
            
            return result
        
        return wrapper
    return decorator

def cache_invalidate(pattern: str = None, cache_manager: UnifiedCacheManager = None):
    """
    缓存失效装饰器
    
    Args:
        pattern: 失效模式
        cache_manager: 缓存管理器实例
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            
            # 失效相关缓存
            if cache_manager and pattern:
                cache_manager.clear(pattern)
            
            return result
        
        return wrapper
    return decorator

# ==================== 全局实例和工厂函数 ====================

# 全局缓存管理器实例
_global_cache_manager = None

def init_unified_cache_manager(config: CacheConfig = None, redis_client=None) -> UnifiedCacheManager:
    """初始化全局缓存管理器"""
    global _global_cache_manager
    _global_cache_manager = UnifiedCacheManager(config, redis_client)
    return _global_cache_manager

def get_cache_manager() -> Optional[UnifiedCacheManager]:
    """获取全局缓存管理器"""
    return _global_cache_manager

# ==================== 向后兼容 ====================

# 为了向后兼容，保留旧的函数名
init_advanced_cache = init_unified_cache_manager
get_advanced_cache = get_cache_manager
init_cache = init_unified_cache_manager
