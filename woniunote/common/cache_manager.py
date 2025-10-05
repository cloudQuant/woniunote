"""
缓存管理工具 - 为文章性能优化提供缓存支持
"""

import time
import json
import hashlib
from typing import Any, Optional, Dict, List
from functools import wraps
from woniunote.common.unified_logging import get_simple_logger

logger = get_simple_logger('cache_manager')

# 内存缓存存储
_memory_cache: Dict[str, Dict[str, Any]] = {}
_cache_stats = {
    'hits': 0,
    'misses': 0,
    'sets': 0,
    'deletes': 0
}

class CacheManager:
    """简化的缓存管理器"""
    
    @staticmethod
    def get_cache_key(prefix: str, *args, **kwargs) -> str:
        """生成缓存键"""
        key_parts = [prefix]
        
        # 添加位置参数
        for arg in args:
            key_parts.append(str(arg))
        
        # 添加关键字参数
        for k, v in sorted(kwargs.items()):
            key_parts.append(f"{k}:{v}")
        
        # 生成最终键
        key = ":".join(key_parts)
        
        # 如果键太长，使用哈希
        if len(key) > 200:
            key_hash = hashlib.md5(key.encode()).hexdigest()
            key = f"{prefix}:hash:{key_hash}"
        
        return key
    
    @staticmethod
    def set(key: str, value: Any, timeout: int = 300) -> bool:
        """设置缓存"""
        try:
            expire_time = time.time() + timeout
            _memory_cache[key] = {
                'value': value,
                'expire_time': expire_time,
                'created_time': time.time()
            }
            _cache_stats['sets'] += 1
            
            logger.debug(f"缓存设置成功: {key}", {
                'timeout': timeout,
                'expire_time': expire_time
            })
            return True
            
        except Exception as e:
            logger.error(f"缓存设置失败: {key}", {
                'error': str(e)
            })
            return False
    
    @staticmethod
    def get(key: str) -> Optional[Any]:
        """获取缓存"""
        try:
            if key not in _memory_cache:
                _cache_stats['misses'] += 1
                logger.debug(f"缓存未命中: {key}")
                return None
            
            cache_item = _memory_cache[key]
            current_time = time.time()
            
            # 检查是否过期
            if current_time > cache_item['expire_time']:
                del _memory_cache[key]
                _cache_stats['misses'] += 1
                logger.debug(f"缓存已过期: {key}")
                return None
            
            _cache_stats['hits'] += 1
            logger.debug(f"缓存命中: {key}")
            return cache_item['value']
            
        except Exception as e:
            logger.error(f"缓存获取失败: {key}", {
                'error': str(e)
            })
            _cache_stats['misses'] += 1
            return None
    
    @staticmethod
    def delete(key: str) -> bool:
        """删除缓存"""
        try:
            if key in _memory_cache:
                del _memory_cache[key]
                _cache_stats['deletes'] += 1
                logger.debug(f"缓存删除成功: {key}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"缓存删除失败: {key}", {
                'error': str(e)
            })
            return False
    
    @staticmethod
    def clear_by_prefix(prefix: str) -> int:
        """根据前缀清除缓存"""
        try:
            keys_to_delete = [key for key in _memory_cache.keys() if key.startswith(prefix)]
            deleted_count = 0
            
            for key in keys_to_delete:
                if CacheManager.delete(key):
                    deleted_count += 1
            
            logger.info(f"按前缀清除缓存完成: {prefix}", {
                'deleted_count': deleted_count,
                'total_keys': len(keys_to_delete)
            })
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"按前缀清除缓存失败: {prefix}", {
                'error': str(e)
            })
            return 0
    
    @staticmethod
    def get_stats() -> Dict[str, Any]:
        """获取缓存统计信息"""
        total_requests = _cache_stats['hits'] + _cache_stats['misses']
        hit_rate = (_cache_stats['hits'] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'hits': _cache_stats['hits'],
            'misses': _cache_stats['misses'],
            'sets': _cache_stats['sets'],
            'deletes': _cache_stats['deletes'],
            'total_requests': total_requests,
            'hit_rate': round(hit_rate, 2),
            'cache_size': len(_memory_cache),
            'memory_usage_kb': CacheManager._estimate_memory_usage()
        }
    
    @staticmethod
    def _estimate_memory_usage() -> float:
        """估算内存使用量（KB）"""
        try:
            import sys
            total_size = 0
            
            for key, value in _memory_cache.items():
                total_size += sys.getsizeof(key)
                total_size += sys.getsizeof(value)
                if isinstance(value.get('value'), (str, dict, list)):
                    total_size += sys.getsizeof(value['value'])
            
            return round(total_size / 1024, 2)
            
        except Exception:
            return 0.0
    
    @staticmethod
    def cleanup_expired() -> int:
        """清理过期缓存"""
        try:
            current_time = time.time()
            expired_keys = []
            
            for key, cache_item in _memory_cache.items():
                if current_time > cache_item['expire_time']:
                    expired_keys.append(key)
            
            cleaned_count = 0
            for key in expired_keys:
                if CacheManager.delete(key):
                    cleaned_count += 1
            
            if cleaned_count > 0:
                logger.info(f"清理过期缓存完成", {
                    'cleaned_count': cleaned_count,
                    'remaining_count': len(_memory_cache)
                })
            
            return cleaned_count
            
        except Exception as e:
            logger.error(f"清理过期缓存失败", {
                'error': str(e)
            })
            return 0

def cached(key_prefix: str, timeout: int = 300):
    """缓存装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存键
            cache_key = CacheManager.get_cache_key(key_prefix, *args, **kwargs)
            
            # 尝试从缓存获取
            cached_result = CacheManager.get(cache_key)
            if cached_result is not None:
                logger.debug(f"函数缓存命中: {func.__name__}", {
                    'cache_key': cache_key
                })
                return cached_result
            
            # 执行函数
            start_time = time.time()
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            # 存储到缓存
            if result is not None:
                CacheManager.set(cache_key, result, timeout)
                logger.debug(f"函数结果已缓存: {func.__name__}", {
                    'cache_key': cache_key,
                    'execution_time_ms': round(execution_time * 1000, 2),
                    'timeout': timeout
                })
            
            return result
        
        return wrapper
    return decorator

def clear_cache_by_prefix(prefix: str) -> int:
    """清除指定前缀的缓存"""
    return CacheManager.clear_by_prefix(prefix)

def get_cache_stats() -> Dict[str, Any]:
    """获取缓存统计信息"""
    return CacheManager.get_stats()

def cleanup_expired_cache() -> int:
    """清理过期缓存"""
    return CacheManager.cleanup_expired()

# 定期清理过期缓存
import threading
import atexit

def _periodic_cleanup():
    """定期清理任务"""
    while True:
        try:
            time.sleep(300)  # 每5分钟清理一次
            cleanup_expired_cache()
        except Exception as e:
            logger.error(f"定期清理任务异常: {e}")

# 启动清理线程
_cleanup_thread = threading.Thread(target=_periodic_cleanup, daemon=True)
_cleanup_thread.start()

# 程序退出时清理
atexit.register(lambda: logger.info("缓存管理器关闭", CacheManager.get_stats()))