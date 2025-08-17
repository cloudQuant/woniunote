"""
高级缓存策略模块
实现多层缓存、智能失效、预热等功能
"""
import time
import json
import hashlib
import logging
import threading
from typing import Any, Dict, List, Optional, Callable, Union
from functools import wraps
from concurrent.futures import ThreadPoolExecutor
import redis
from flask import g, current_app

logger = logging.getLogger(__name__)

class CacheLevel:
    """缓存级别枚举"""
    MEMORY = "memory"  # 内存缓存（最快，容量小）
    REDIS = "redis"    # Redis缓存（快，容量大）
    DATABASE = "database"  # 数据库（慢，持久化）

class CacheStrategy:
    """缓存策略枚举"""
    LRU = "lru"        # 最近最少使用
    TTL = "ttl"        # 时间到期
    WRITE_THROUGH = "write_through"    # 写透
    WRITE_BACK = "write_back"          # 写回
    REFRESH_AHEAD = "refresh_ahead"    # 提前刷新

class AdvancedCacheManager:
    """高级缓存管理器"""
    
    def __init__(self, redis_client=None, default_ttl=3600):
        self.redis_client = redis_client
        self.default_ttl = default_ttl
        self.memory_cache = {}
        self.cache_stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0,
            'memory_size': 0,
            'redis_size': 0
        }
        self.refresh_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="cache_refresh")
        self._lock = threading.RLock()
        
        # 缓存配置
        self.memory_max_size = 1000  # 内存缓存最大条目数
        self.refresh_threshold = 0.8  # 缓存刷新阈值（TTL的80%时刷新）
        
    def _generate_cache_key(self, key: str, params: Dict = None) -> str:
        """生成缓存键"""
        if params:
            # 将参数序列化并哈希，确保键的唯一性
            param_str = json.dumps(params, sort_keys=True, ensure_ascii=False)
            param_hash = hashlib.md5(param_str.encode()).hexdigest()[:8]
            return f"{key}:{param_hash}"
        return key
    
    def _get_from_memory(self, key: str) -> tuple:
        """从内存缓存获取数据"""
        with self._lock:
            if key in self.memory_cache:
                entry = self.memory_cache[key]
                if entry['expires_at'] > time.time():
                    # 更新访问时间（LRU）
                    entry['accessed_at'] = time.time()
                    self.cache_stats['hits'] += 1
                    return entry['data'], True
                else:
                    # 过期删除
                    del self.memory_cache[key]
                    self.cache_stats['memory_size'] = len(self.memory_cache)
        return None, False
    
    def _set_to_memory(self, key: str, data: Any, ttl: int):
        """设置内存缓存"""
        with self._lock:
            # 检查内存缓存大小，必要时清理
            if len(self.memory_cache) >= self.memory_max_size:
                self._cleanup_memory_cache()
            
            expires_at = time.time() + ttl
            self.memory_cache[key] = {
                'data': data,
                'expires_at': expires_at,
                'accessed_at': time.time(),
                'created_at': time.time()
            }
            self.cache_stats['memory_size'] = len(self.memory_cache)
            self.cache_stats['sets'] += 1
    
    def _cleanup_memory_cache(self):
        """清理内存缓存（LRU策略）"""
        current_time = time.time()
        
        # 首先移除过期条目
        expired_keys = [
            key for key, entry in self.memory_cache.items()
            if entry['expires_at'] <= current_time
        ]
        for key in expired_keys:
            del self.memory_cache[key]
        
        # 如果还是太多，移除最少访问的条目
        if len(self.memory_cache) >= self.memory_max_size:
            sorted_items = sorted(
                self.memory_cache.items(),
                key=lambda x: x[1]['accessed_at']
            )
            # 移除最旧的25%
            remove_count = len(sorted_items) // 4
            for key, _ in sorted_items[:remove_count]:
                del self.memory_cache[key]
        
        logger.debug(f"内存缓存清理完成，当前大小: {len(self.memory_cache)}")
    
    def _get_from_redis(self, key: str) -> tuple:
        """从Redis获取数据"""
        if not self.redis_client:
            return None, False
        
        try:
            cached = self.redis_client.get(key)
            if cached:
                data = json.loads(cached)
                self.cache_stats['hits'] += 1
                return data, True
        except (redis.RedisError, json.JSONDecodeError) as e:
            logger.warning(f"Redis缓存读取失败: {e}")
        
        return None, False
    
    def _set_to_redis(self, key: str, data: Any, ttl: int):
        """设置Redis缓存"""
        if not self.redis_client:
            return
        
        try:
            cached_data = json.dumps(data, ensure_ascii=False, default=str)
            self.redis_client.setex(key, ttl, cached_data)
            self.cache_stats['sets'] += 1
        except (redis.RedisError, json.JSONEncodeError) as e:
            logger.warning(f"Redis缓存写入失败: {e}")
    
    def get(self, key: str, params: Dict = None, levels: List[str] = None) -> tuple:
        """
        多层缓存获取
        
        Args:
            key: 缓存键
            params: 参数字典
            levels: 缓存级别列表
            
        Returns:
            (data, found) 元组
        """
        if levels is None:
            levels = [CacheLevel.MEMORY, CacheLevel.REDIS]
        
        cache_key = self._generate_cache_key(key, params)
        
        # 按级别顺序查找
        for level in levels:
            if level == CacheLevel.MEMORY:
                data, found = self._get_from_memory(cache_key)
                if found:
                    logger.debug(f"内存缓存命中: {cache_key}")
                    return data, True
                    
            elif level == CacheLevel.REDIS:
                data, found = self._get_from_redis(cache_key)
                if found:
                    logger.debug(f"Redis缓存命中: {cache_key}")
                    # 将数据提升到内存缓存
                    self._set_to_memory(cache_key, data, self.default_ttl // 2)
                    return data, True
        
        self.cache_stats['misses'] += 1
        return None, False
    
    def set(self, key: str, data: Any, ttl: int = None, params: Dict = None, 
           levels: List[str] = None):
        """
        多层缓存设置
        
        Args:
            key: 缓存键
            data: 缓存数据
            ttl: 过期时间
            params: 参数字典
            levels: 缓存级别列表
        """
        if ttl is None:
            ttl = self.default_ttl
        
        if levels is None:
            levels = [CacheLevel.MEMORY, CacheLevel.REDIS]
        
        cache_key = self._generate_cache_key(key, params)
        
        for level in levels:
            if level == CacheLevel.MEMORY:
                self._set_to_memory(cache_key, data, ttl)
            elif level == CacheLevel.REDIS:
                self._set_to_redis(cache_key, data, ttl)
        
        logger.debug(f"缓存设置完成: {cache_key}, levels: {levels}")
    
    def delete(self, key: str, params: Dict = None, levels: List[str] = None):
        """删除缓存"""
        if levels is None:
            levels = [CacheLevel.MEMORY, CacheLevel.REDIS]
        
        cache_key = self._generate_cache_key(key, params)
        
        for level in levels:
            if level == CacheLevel.MEMORY:
                with self._lock:
                    if cache_key in self.memory_cache:
                        del self.memory_cache[cache_key]
                        self.cache_stats['deletes'] += 1
                        self.cache_stats['memory_size'] = len(self.memory_cache)
                        
            elif level == CacheLevel.REDIS and self.redis_client:
                try:
                    self.redis_client.delete(cache_key)
                    self.cache_stats['deletes'] += 1
                except redis.RedisError as e:
                    logger.warning(f"Redis缓存删除失败: {e}")
    
    def delete_pattern(self, pattern: str, level: str = CacheLevel.REDIS):
        """按模式删除缓存"""
        if level == CacheLevel.REDIS and self.redis_client:
            try:
                keys = self.redis_client.keys(pattern)
                if keys:
                    self.redis_client.delete(*keys)
                    logger.info(f"按模式删除缓存: {pattern}, 删除数量: {len(keys)}")
            except redis.RedisError as e:
                logger.warning(f"Redis模式删除失败: {e}")
        
        elif level == CacheLevel.MEMORY:
            with self._lock:
                import fnmatch
                keys_to_delete = [
                    key for key in self.memory_cache.keys()
                    if fnmatch.fnmatch(key, pattern)
                ]
                for key in keys_to_delete:
                    del self.memory_cache[key]
                self.cache_stats['memory_size'] = len(self.memory_cache)
                logger.info(f"内存缓存模式删除: {pattern}, 删除数量: {len(keys_to_delete)}")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        total_requests = self.cache_stats['hits'] + self.cache_stats['misses']
        hit_rate = (self.cache_stats['hits'] / total_requests * 100) if total_requests > 0 else 0
        
        stats = self.cache_stats.copy()
        stats['hit_rate'] = round(hit_rate, 2)
        stats['total_requests'] = total_requests
        
        # Redis统计
        if self.redis_client:
            try:
                redis_info = self.redis_client.info('memory')
                stats['redis_memory_usage'] = redis_info.get('used_memory', 0)
                stats['redis_memory_human'] = redis_info.get('used_memory_human', '0B')
            except redis.RedisError:
                stats['redis_memory_usage'] = 0
                stats['redis_memory_human'] = '0B'
        
        return stats
    
    def warm_up(self, warm_up_functions: List[Callable]):
        """缓存预热"""
        logger.info("开始缓存预热...")
        
        def run_warmup():
            for func in warm_up_functions:
                try:
                    func()
                    logger.debug(f"缓存预热函数执行成功: {func.__name__}")
                except Exception as e:
                    logger.error(f"缓存预热函数执行失败 {func.__name__}: {e}")
        
        # 异步执行预热
        self.refresh_executor.submit(run_warmup)
    
    def refresh_cache(self, key: str, refresh_func: Callable, params: Dict = None):
        """异步刷新缓存"""
        def refresh():
            try:
                new_data = refresh_func(**params) if params else refresh_func()
                self.set(key, new_data, params=params)
                logger.debug(f"缓存刷新完成: {key}")
            except Exception as e:
                logger.error(f"缓存刷新失败 {key}: {e}")
        
        self.refresh_executor.submit(refresh)

# 全局缓存管理器实例
_cache_manager = None

def get_cache_manager() -> AdvancedCacheManager:
    """获取全局缓存管理器"""
    global _cache_manager
    if _cache_manager is None:
        # 尝试获取Redis连接
        try:
            from woniunote.common.redisdb import get_redis_client
            redis_client = get_redis_client()
        except ImportError:
            redis_client = None
            logger.warning("Redis客户端不可用，仅使用内存缓存")
        
        _cache_manager = AdvancedCacheManager(redis_client=redis_client)
    
    return _cache_manager

def multi_level_cache(key: str, ttl: int = 3600, levels: List[str] = None, 
                     auto_refresh: bool = False):
    """
    多层缓存装饰器
    
    Args:
        key: 缓存键（可以使用占位符）
        ttl: 过期时间
        levels: 缓存级别
        auto_refresh: 是否自动刷新
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_manager = get_cache_manager()
            
            # 生成缓存键，包含函数参数
            cache_key = key
            params = {}
            
            # 如果缓存键包含占位符，用参数替换
            if '{' in cache_key:
                # 从函数参数中提取占位符值
                import inspect
                sig = inspect.signature(func)
                bound_args = sig.bind(*args, **kwargs)
                bound_args.apply_defaults()
                cache_key = cache_key.format(**bound_args.arguments)
                params = bound_args.arguments
            
            # 尝试从缓存获取
            cached_data, found = cache_manager.get(cache_key, params, levels)
            if found:
                return cached_data
            
            # 缓存未命中，执行函数
            result = func(*args, **kwargs)
            
            # 设置缓存
            cache_manager.set(cache_key, result, ttl, params, levels)
            
            # 如果启用自动刷新，在TTL的80%时异步刷新
            if auto_refresh:
                refresh_time = ttl * cache_manager.refresh_threshold
                cache_manager.refresh_executor.submit(
                    _schedule_refresh, cache_manager, cache_key, func, 
                    args, kwargs, params, refresh_time
                )
            
            return result
        
        return wrapper
    return decorator

def _schedule_refresh(cache_manager, cache_key, func, args, kwargs, params, delay):
    """计划缓存刷新"""
    time.sleep(delay)
    try:
        new_data = func(*args, **kwargs)
        cache_manager.set(cache_key, new_data, params=params)
        logger.debug(f"自动刷新缓存完成: {cache_key}")
    except Exception as e:
        logger.error(f"自动刷新缓存失败 {cache_key}: {e}")

# 便捷装饰器
def cache_page(ttl: int = 300):
    """页面缓存装饰器"""
    return multi_level_cache(
        key="page:{func.__name__}:{args[0] if args else 'default'}",
        ttl=ttl,
        levels=[CacheLevel.REDIS]
    )

def cache_api(ttl: int = 600):
    """API缓存装饰器"""
    return multi_level_cache(
        key="api:{func.__name__}",
        ttl=ttl,
        levels=[CacheLevel.MEMORY, CacheLevel.REDIS]
    )

def cache_database_query(ttl: int = 1800):
    """数据库查询缓存装饰器"""
    return multi_level_cache(
        key="db:{func.__name__}",
        ttl=ttl,
        levels=[CacheLevel.MEMORY, CacheLevel.REDIS],
        auto_refresh=True
    )

# 缓存失效器
class CacheInvalidator:
    """缓存失效管理器"""
    
    def __init__(self, cache_manager: AdvancedCacheManager):
        self.cache_manager = cache_manager
        self.invalidation_rules = {}
    
    def register_rule(self, trigger_pattern: str, invalidate_patterns: List[str]):
        """注册失效规则"""
        self.invalidation_rules[trigger_pattern] = invalidate_patterns
    
    def invalidate(self, trigger_key: str):
        """执行缓存失效"""
        import fnmatch
        
        for pattern, invalidate_patterns in self.invalidation_rules.items():
            if fnmatch.fnmatch(trigger_key, pattern):
                for invalidate_pattern in invalidate_patterns:
                    self.cache_manager.delete_pattern(invalidate_pattern)
                    logger.info(f"缓存失效: {invalidate_pattern} (触发: {trigger_key})")

# 全局缓存失效器
_cache_invalidator = None

def get_cache_invalidator() -> CacheInvalidator:
    """获取全局缓存失效器"""
    global _cache_invalidator
    if _cache_invalidator is None:
        _cache_invalidator = CacheInvalidator(get_cache_manager())
        
        # 注册默认失效规则
        _cache_invalidator.register_rule(
            "article:*:update", 
            ["article:*", "homepage:*", "api:*articles*"]
        )
        _cache_invalidator.register_rule(
            "user:*:update",
            ["user:*", "api:*users*"]
        )
    
    return _cache_invalidator