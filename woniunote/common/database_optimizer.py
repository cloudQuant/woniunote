#!/usr/bin/env python3
"""
数据库查询优化模块
提供查询缓存、慢查询监控、索引建议等功能
"""

import time
import logging
import hashlib
import json
from typing import Dict, List, Any, Optional, Callable
from functools import wraps
from contextlib import contextmanager
from sqlalchemy import event, text
from sqlalchemy.engine import Engine
from sqlalchemy.pool import Pool
from collections import defaultdict, deque
from threading import Lock
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class QueryOptimizer:
    """数据库查询优化器"""
    
    def __init__(self):
        self.slow_queries = deque(maxlen=1000)  # 慢查询记录
        self.query_stats = defaultdict(lambda: {
            'count': 0,
            'total_time': 0.0,
            'avg_time': 0.0,
            'max_time': 0.0,
            'min_time': float('inf')
        })
        self.query_cache = {}  # 查询结果缓存
        self.cache_ttl = 300  # 5分钟缓存
        self.lock = Lock()
        self.slow_query_threshold = 1.0  # 慢查询阈值（秒）
        
    def normalize_query(self, query: str) -> str:
        """标准化查询语句，用于统计"""
        try:
            # 移除多余空格和换行
            normalized = ' '.join(query.split())
            
            # 替换参数占位符
            import re
            # 替换数字参数
            normalized = re.sub(r'\b\d+\b', '?', normalized)
            # 替换字符串参数
            normalized = re.sub(r"'[^']*'", '?', normalized)
            normalized = re.sub(r'"[^"]*"', '?', normalized)
            
            return normalized.lower()
        except Exception as e:
            logger.error(f"Query normalization error: {e}")
            return query
    
    def get_query_hash(self, query: str) -> str:
        """生成查询哈希值"""
        return hashlib.md5(query.encode()).hexdigest()[:12]
    
    def record_query(self, query: str, duration: float, result_count: int = 0):
        """记录查询统计"""
        with self.lock:
            normalized_query = self.normalize_query(query)
            query_hash = self.get_query_hash(normalized_query)
            
            # 更新统计信息
            stats = self.query_stats[query_hash]
            stats['count'] += 1
            stats['total_time'] += duration
            stats['avg_time'] = stats['total_time'] / stats['count']
            stats['max_time'] = max(stats['max_time'], duration)
            stats['min_time'] = min(stats['min_time'], duration)
            stats['last_query'] = normalized_query
            stats['result_count'] = result_count
            
            # 记录慢查询
            if duration > self.slow_query_threshold:
                slow_query = {
                    'query': normalized_query,
                    'duration': duration,
                    'timestamp': datetime.now(),
                    'result_count': result_count,
                    'query_hash': query_hash
                }
                self.slow_queries.append(slow_query)
                logger.warning(f"Slow query detected ({duration:.3f}s): {normalized_query[:100]}...")
    
    def get_slow_queries(self, limit: int = 50) -> List[Dict]:
        """获取慢查询列表"""
        with self.lock:
            return list(self.slow_queries)[-limit:]
    
    def get_query_stats(self, top_n: int = 20) -> List[Dict]:
        """获取查询统计信息"""
        with self.lock:
            # 按平均时间排序
            sorted_stats = sorted(
                self.query_stats.items(),
                key=lambda x: x[1]['avg_time'],
                reverse=True
            )
            
            result = []
            for query_hash, stats in sorted_stats[:top_n]:
                result.append({
                    'query_hash': query_hash,
                    'query': stats.get('last_query', 'Unknown'),
                    'count': stats['count'],
                    'avg_time': round(stats['avg_time'], 4),
                    'max_time': round(stats['max_time'], 4),
                    'total_time': round(stats['total_time'], 4),
                    'result_count': stats.get('result_count', 0)
                })
            
            return result
    
    def suggest_indexes(self) -> List[Dict]:
        """基于慢查询建议索引"""
        suggestions = []
        
        with self.lock:
            for slow_query in self.slow_queries:
                query = slow_query['query']
                
                # 简单的索引建议逻辑
                if 'where' in query.lower():
                    # 提取WHERE条件中的字段
                    import re
                    where_match = re.search(r'where\s+(.+?)(?:\s+order\s+by|\s+group\s+by|\s+limit|$)', query, re.IGNORECASE)
                    if where_match:
                        where_clause = where_match.group(1)
                        # 查找字段名
                        field_matches = re.findall(r'(\w+)\s*[=<>!]', where_clause)
                        for field in field_matches:
                            if field.lower() not in ['and', 'or', 'not']:
                                suggestions.append({
                                    'query_hash': slow_query['query_hash'],
                                    'suggested_index': field,
                                    'reason': f'Field "{field}" used in WHERE clause',
                                    'query_duration': slow_query['duration']
                                })
        
        # 去重并按影响排序
        unique_suggestions = {}
        for suggestion in suggestions:
            key = suggestion['suggested_index']
            if key not in unique_suggestions or suggestion['query_duration'] > unique_suggestions[key]['query_duration']:
                unique_suggestions[key] = suggestion
        
        return sorted(unique_suggestions.values(), key=lambda x: x['query_duration'], reverse=True)
    
    def clear_stats(self):
        """清空统计信息"""
        with self.lock:
            self.query_stats.clear()
            self.slow_queries.clear()
            logger.info("Query statistics cleared")

class QueryCache:
    """查询结果缓存"""
    
    def __init__(self, cache_manager=None, default_ttl: int = 300):
        self.cache_manager = cache_manager
        self.default_ttl = default_ttl
        self.hit_count = 0
        self.miss_count = 0
        self.lock = Lock()
    
    def get_cache_key(self, query: str, params: tuple = None) -> str:
        """生成缓存键"""
        key_data = f"{query}_{params or ''}"
        return f"query_cache:{hashlib.md5(key_data.encode()).hexdigest()}"
    
    def get(self, query: str, params: tuple = None) -> Optional[Any]:
        """获取缓存的查询结果"""
        if not self.cache_manager:
            return None
        
        try:
            cache_key = self.get_cache_key(query, params)
            result = self.cache_manager.get(cache_key)
            
            with self.lock:
                if result is not None:
                    self.hit_count += 1
                    logger.debug(f"Query cache hit: {cache_key}")
                else:
                    self.miss_count += 1
            
            return result
        except Exception as e:
            logger.error(f"Query cache get error: {e}")
            return None
    
    def set(self, query: str, result: Any, params: tuple = None, ttl: int = None) -> bool:
        """缓存查询结果"""
        if not self.cache_manager:
            return False
        
        try:
            cache_key = self.get_cache_key(query, params)
            ttl = ttl or self.default_ttl
            
            # 限制缓存结果大小
            if len(str(result)) > 100000:  # 100KB限制
                logger.warning(f"Query result too large to cache: {len(str(result))} bytes")
                return False
            
            success = self.cache_manager.set(cache_key, result, ttl)
            if success:
                logger.debug(f"Query result cached: {cache_key}")
            
            return success
        except Exception as e:
            logger.error(f"Query cache set error: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        with self.lock:
            total_requests = self.hit_count + self.miss_count
            hit_rate = (self.hit_count / total_requests) if total_requests > 0 else 0
            
            return {
                'hit_count': self.hit_count,
                'miss_count': self.miss_count,
                'hit_rate': round(hit_rate, 4),
                'total_requests': total_requests
            }

class ConnectionPoolMonitor:
    """连接池监控"""
    
    def __init__(self):
        self.pool_stats = {
            'created_connections': 0,
            'closed_connections': 0,
            'active_connections': 0,
            'checked_out_connections': 0,
            'overflow_connections': 0,
            'invalid_connections': 0
        }
        self.lock = Lock()
    
    def on_connect(self, dbapi_connection, connection_record):
        """连接创建事件"""
        with self.lock:
            self.pool_stats['created_connections'] += 1
        logger.debug("Database connection created")
    
    def on_checkout(self, dbapi_connection, connection_record, connection_proxy):
        """连接检出事件"""
        with self.lock:
            self.pool_stats['checked_out_connections'] += 1
    
    def on_checkin(self, dbapi_connection, connection_record):
        """连接归还事件"""
        with self.lock:
            self.pool_stats['checked_out_connections'] -= 1
    
    def on_close(self, dbapi_connection, connection_record):
        """连接关闭事件"""
        with self.lock:
            self.pool_stats['closed_connections'] += 1
        logger.debug("Database connection closed")
    
    def on_invalidate(self, dbapi_connection, connection_record, exception):
        """连接失效事件"""
        with self.lock:
            self.pool_stats['invalid_connections'] += 1
        logger.warning(f"Database connection invalidated: {exception}")
    
    def get_stats(self) -> Dict[str, int]:
        """获取连接池统计"""
        with self.lock:
            return self.pool_stats.copy()

# 全局实例
_query_optimizer = None
_query_cache = None
_pool_monitor = None

def get_query_optimizer() -> QueryOptimizer:
    """获取查询优化器实例"""
    global _query_optimizer
    if _query_optimizer is None:
        _query_optimizer = QueryOptimizer()
    return _query_optimizer

def get_query_cache() -> QueryCache:
    """获取查询缓存实例"""
    global _query_cache
    if _query_cache is None:
        from woniunote.common.cache_utils import get_cache_manager
        _query_cache = QueryCache(get_cache_manager())
    return _query_cache

def get_pool_monitor() -> ConnectionPoolMonitor:
    """获取连接池监控实例"""
    global _pool_monitor
    if _pool_monitor is None:
        _pool_monitor = ConnectionPoolMonitor()
    return _pool_monitor

def monitor_query(func):
    """查询监控装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        
        try:
            result = func(*args, **kwargs)
            
            # 记录查询统计
            duration = time.time() - start_time
            
            # 尝试提取查询语句
            query = ""
            if args and hasattr(args[0], 'statement'):
                query = str(args[0].statement)
            elif 'query' in kwargs:
                query = str(kwargs['query'])
            
            result_count = len(result) if hasattr(result, '__len__') else 0
            
            optimizer = get_query_optimizer()
            optimizer.record_query(query, duration, result_count)
            
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Query execution error after {duration:.3f}s: {e}")
            raise
    
    return wrapper

@contextmanager
def cached_query(query: str, params: tuple = None, ttl: int = None):
    """缓存查询上下文管理器"""
    query_cache = get_query_cache()
    
    # 尝试从缓存获取
    cached_result = query_cache.get(query, params)
    if cached_result is not None:
        yield cached_result
        return
    
    # 执行查询并缓存结果
    try:
        yield None  # 让调用者执行查询
    except Exception as e:
        raise
    # 注意：实际的缓存逻辑需要在调用者中处理

def init_database_monitoring(app):
    """初始化数据库监控"""
    try:
        # 注册SQLAlchemy事件监听器
        from sqlalchemy import event
        
        # 查询监控
        @event.listens_for(Engine, "before_cursor_execute")
        def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            context._query_start_time = time.time()
            context._query_statement = statement
        
        @event.listens_for(Engine, "after_cursor_execute")
        def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            if hasattr(context, '_query_start_time'):
                duration = time.time() - context._query_start_time
                
                optimizer = get_query_optimizer()
                result_count = cursor.rowcount if hasattr(cursor, 'rowcount') else 0
                optimizer.record_query(statement, duration, result_count)
        
        # 连接池监控
        pool_monitor = get_pool_monitor()
        event.listen(Engine, "connect", pool_monitor.on_connect)
        event.listen(Pool, "checkout", pool_monitor.on_checkout)
        event.listen(Pool, "checkin", pool_monitor.on_checkin)
        event.listen(Pool, "close", pool_monitor.on_close)
        event.listen(Pool, "invalidate", pool_monitor.on_invalidate)
        
        logger.info("Database monitoring initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize database monitoring: {e}")

def get_database_health() -> Dict[str, Any]:
    """获取数据库健康状态"""
    try:
        optimizer = get_query_optimizer()
        query_cache = get_query_cache()
        pool_monitor = get_pool_monitor()
        
        health_data = {
            'slow_queries_count': len(optimizer.slow_queries),
            'total_unique_queries': len(optimizer.query_stats),
            'cache_stats': query_cache.get_stats(),
            'pool_stats': pool_monitor.get_stats(),
            'index_suggestions': len(optimizer.suggest_indexes()),
            'timestamp': datetime.now().isoformat()
        }
        
        # 健康状态评估
        if health_data['slow_queries_count'] > 50:
            health_data['status'] = 'warning'
            health_data['issues'] = ['Too many slow queries detected']
        elif health_data['cache_stats']['hit_rate'] < 0.5 and health_data['cache_stats']['total_requests'] > 100:
            health_data['status'] = 'warning'
            health_data['issues'] = ['Low cache hit rate']
        else:
            health_data['status'] = 'healthy'
            health_data['issues'] = []
        
        return health_data
        
    except Exception as e:
        logger.error(f"Error getting database health: {e}")
        return {
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }


# 为了兼容性，提供DatabaseOptimizer别名
DatabaseOptimizer = QueryOptimizer 