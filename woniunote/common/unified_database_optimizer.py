#!/usr/bin/env python3
"""
统一的数据库优化模块
整合所有数据库优化、性能监控和查询优化功能
"""

import os
import time
import threading
import hashlib
import json
import sqlparse
from typing import Dict, Any, List, Optional, Union, Callable, Tuple
from collections import defaultdict, deque
from functools import wraps
from contextlib import contextmanager
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict

from sqlalchemy import event, text, inspect
from sqlalchemy.engine import Engine
from sqlalchemy.pool import QueuePool
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from .unified_logging import get_logger
from .unified_error_handler import DatabaseException

logger = get_logger('unified_database_optimizer')

# ==================== 数据类定义 ====================

@dataclass
class QueryAnalysis:
    """查询分析结果"""
    query_hash: str
    query_text: str
    execution_time: float
    execution_count: int
    avg_execution_time: float
    max_execution_time: float
    min_execution_time: float
    last_execution: datetime
    tables_accessed: List[str]
    index_usage: Dict[str, Any]
    optimization_suggestions: List[str]
    result_count: int = 0

@dataclass
class IndexSuggestion:
    """索引建议"""
    table_name: str
    columns: List[str]
    index_type: str  # 'btree', 'hash', 'composite'
    estimated_benefit: float
    usage_frequency: int
    reasoning: str
    priority: str = 'medium'  # 'low', 'medium', 'high', 'critical'

@dataclass
class ConnectionPoolStats:
    """连接池统计信息"""
    pool_size: int
    checked_out: int
    overflow: int
    checked_in: int
    total_connections: int
    usage_rate: float
    health_status: str

# ==================== 查询缓存管理器 ====================

class QueryCache:
    """智能查询缓存管理器"""
    
    def __init__(self, max_size: int = 5000, default_ttl: int = 300):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache = {}
        self.access_times = {}
        self.hit_count = 0
        self.miss_count = 0
        self.lock = threading.RLock()
        
        # 缓存统计
        self.stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'total_size': 0,
            'memory_usage': 0
        }
        
        # 启动清理线程
        self._cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self._cleanup_thread.start()
    
    def _generate_cache_key(self, query: str, params: tuple = None) -> str:
        """生成缓存键"""
        try:
            # 标准化查询文本
            normalized_query = sqlparse.format(query, strip_whitespace=True, keyword_case='upper')
            key_data = f"{normalized_query}:{params or ''}"
            return hashlib.md5(key_data.encode()).hexdigest()
        except Exception:
            # 如果sqlparse失败，使用简单哈希
            key_data = f"{query}:{params or ''}"
            return hashlib.md5(key_data.encode()).hexdigest()
    
    def get(self, query: str, params: tuple = None) -> Optional[Any]:
        """获取缓存的查询结果"""
        cache_key = self._generate_cache_key(query, params)
        
        with self.lock:
            if cache_key in self.cache:
                data, timestamp, ttl = self.cache[cache_key]
                
                # 检查是否过期
                if time.time() - timestamp > ttl:
                    del self.cache[cache_key]
                    del self.access_times[cache_key]
                    self.stats['evictions'] += 1
                    return None
                
                # 更新访问时间
                self.access_times[cache_key] = time.time()
                self.hit_count += 1
                self.stats['hits'] += 1
                
                return data
            
            self.miss_count += 1
            self.stats['misses'] += 1
            return None
    
    def set(self, query: str, data: Any, ttl: int = None, params: tuple = None) -> None:
        """设置查询缓存"""
        if ttl is None:
            ttl = self.default_ttl
        
        cache_key = self._generate_cache_key(query, params)
        current_time = time.time()
        
        with self.lock:
            # 如果缓存已满，删除最旧的条目
            if len(self.cache) >= self.max_size:
                self._evict_lru()
            
            # 存储数据
            self.cache[cache_key] = (data, current_time, ttl)
            self.access_times[cache_key] = current_time
            
            # 更新统计
            self.stats['total_size'] = len(self.cache)
            self.stats['memory_usage'] = sum(len(str(v[0])) for v in self.cache.values())
    
    def invalidate(self, pattern: str = None) -> int:
        """使缓存失效"""
        with self.lock:
            if pattern is None:
                # 清除所有缓存
                count = len(self.cache)
                self.cache.clear()
                self.access_times.clear()
                self.stats['total_size'] = 0
                self.stats['memory_usage'] = 0
                return count
            
            # 根据模式清除缓存
            count = 0
            keys_to_remove = []
            
            for key in self.cache.keys():
                if pattern in key:
                    keys_to_remove.append(key)
                    count += 1
            
            for key in keys_to_remove:
                del self.cache[key]
                del self.access_times[key]
            
            self.stats['total_size'] = len(self.cache)
            self.stats['memory_usage'] = sum(len(str(v[0])) for v in self.cache.values())
            
            return count
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        with self.lock:
            hit_rate = self.hit_count / max(1, self.hit_count + self.miss_count)
            return {
                'cache_size': len(self.cache),
                'max_size': self.max_size,
                'hit_rate': hit_rate,
                'total_hits': self.hit_count,
                'total_misses': self.miss_count,
                'evictions': self.stats['evictions'],
                'memory_usage': self.stats['memory_usage'],
                'default_ttl': self.default_ttl
            }
    
    def _evict_lru(self) -> None:
        """LRU淘汰策略"""
        if len(self.cache) <= self.max_size:
            return
        
        # 按访问时间排序，删除最旧的
        sorted_items = sorted(self.access_times.items(), key=lambda x: x[1])
        keys_to_remove = [item[0] for item in sorted_items[:len(self.cache) - self.max_size]]
        
        for key in keys_to_remove:
            del self.cache[key]
            del self.access_times[key]
        
        self.stats['evictions'] += len(keys_to_remove)
    
    def _cleanup_loop(self) -> None:
        """清理过期缓存的循环"""
        while True:
            try:
                time.sleep(60)  # 每分钟清理一次
                self._cleanup_expired()
            except Exception as e:
                logger.error(f"缓存清理失败: {e}")
    
    def _cleanup_expired(self) -> None:
        """清理过期缓存"""
        current_time = time.time()
        expired_keys = []
        
        with self.lock:
            for key, (data, timestamp, ttl) in self.cache.items():
                if current_time - timestamp > ttl:
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self.cache[key]
                self.access_times.pop(key, None)
                self.stats['evictions'] += 1
            
            if expired_keys:
                logger.debug(f"清理了 {len(expired_keys)} 个过期缓存条目")

# ==================== 连接池管理器 ====================

class ConnectionPoolManager:
    """数据库连接池管理器"""
    
    def __init__(self, engine: Engine):
        self.engine = engine
        self.pool = engine.pool
        self.stats = {
            'total_connections': 0,
            'active_connections': 0,
            'overflow_connections': 0,
            'checked_out_connections': 0,
            'checked_in_connections': 0,
            'connection_errors': 0
        }
        self._lock = threading.RLock()
        
        # 启动监控线程
        self._monitor_thread = threading.Thread(target=self._monitor_pool, daemon=True)
        self._monitor_thread.start()
        
        # 注册事件监听器
        self._register_event_listeners()
    
    def _register_event_listeners(self):
        """注册数据库事件监听器"""
        @event.listens_for(self.engine, 'checkout')
        def receive_checkout(dbapi_connection, connection_record, connection_proxy):
            with self._lock:
                self.stats['checked_out_connections'] += 1
                self.stats['active_connections'] += 1
        
        @event.listens_for(self.engine, 'checkin')
        def receive_checkin(dbapi_connection, connection_record):
            with self._lock:
                self.stats['checked_in_connections'] += 1
                self.stats['active_connections'] -= 1
        
        @event.listens_for(self.engine, 'connect')
        def receive_connect(dbapi_connection, connection_record):
            with self._lock:
                self.stats['total_connections'] += 1
        
        @event.listens_for(self.engine, 'close')
        def receive_close(dbapi_connection):
            with self._lock:
                self.stats['total_connections'] -= 1
    
    def get_pool_status(self) -> ConnectionPoolStats:
        """获取连接池状态"""
        if not isinstance(self.pool, QueuePool):
            return ConnectionPoolStats(
                pool_size=0,
                checked_out=0,
                overflow=0,
                checked_in=0,
                total_connections=0,
                usage_rate=0.0,
                health_status='unsupported'
            )
        
        with self._lock:
            pool_size = self.pool.size()
            checked_out = self.pool.checkedout()
            overflow = self.pool.overflow()
            checked_in = self.pool.checkedin()
            total_connections = pool_size + overflow
            
            usage_rate = checked_out / max(1, pool_size)
            
            # 健康状态评估
            if usage_rate > 0.9:
                health_status = 'critical'
            elif usage_rate > 0.7:
                health_status = 'warning'
            elif usage_rate > 0.5:
                health_status = 'normal'
            else:
                health_status = 'good'
            
            return ConnectionPoolStats(
                pool_size=pool_size,
                checked_out=checked_out,
                overflow=overflow,
                checked_in=checked_in,
                total_connections=total_connections,
                usage_rate=usage_rate,
                health_status=health_status
            )
    
    def optimize_pool(self, target_size: int = None, max_overflow: int = None) -> Dict[str, Any]:
        """优化连接池配置"""
        try:
            if target_size is not None:
                self.pool.resize(target_size)
            
            if max_overflow is not None:
                self.pool._max_overflow = max_overflow
            
            logger.info("连接池配置已优化", {
                'new_size': self.pool.size(),
                'new_max_overflow': self.pool._max_overflow
            })
            
            return {
                'success': True,
                'new_size': self.pool.size(),
                'new_max_overflow': self.pool._max_overflow
            }
            
        except Exception as e:
            logger.error(f"连接池优化失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def _monitor_pool(self) -> None:
        """监控连接池状态"""
        while True:
            try:
                time.sleep(30)  # 每30秒监控一次
                
                if isinstance(self.pool, QueuePool):
                    with self._lock:
                        self.stats['total_connections'] = self.pool.size() + self.pool.overflow()
                        self.stats['active_connections'] = self.pool.size()
                        self.stats['overflow_connections'] = self.pool.overflow()
                        self.stats['checked_out_connections'] = self.pool.checkedout()
                        self.stats['checked_in_connections'] = self.pool.checkedin()
                    
                    # 检查连接池健康状态
                    pool_status = self.get_pool_status()
                    if pool_status.health_status == 'critical':
                        logger.warning("连接池使用率过高", {
                            'usage_rate': pool_status.usage_rate,
                            'checked_out': pool_status.checked_out,
                            'pool_size': pool_status.pool_size
                        })
                        
            except Exception as e:
                logger.error(f"连接池监控失败: {e}")

# ==================== 慢查询分析器 ====================

class SlowQueryAnalyzer:
    """慢查询分析器"""
    
    def __init__(self, threshold: float = 1.0):
        self.threshold = threshold
        self.slow_queries = deque(maxlen=1000)
        self.query_patterns = defaultdict(list)
        self.query_stats = defaultdict(lambda: {
            'count': 0,
            'total_time': 0.0,
            'avg_time': 0.0,
            'max_time': 0.0,
            'min_time': float('inf'),
            'result_count': 0
        })
        self._lock = threading.RLock()
    
    def record_query(self, query: str, execution_time: float, params: Dict[str, Any] = None, 
                    result_count: int = 0) -> None:
        """记录查询执行时间"""
        if execution_time >= self.threshold:
            with self._lock:
                query_info = {
                    'query': query,
                    'execution_time': execution_time,
                    'params': params,
                    'timestamp': datetime.now(),
                    'pattern': self._extract_query_pattern(query),
                    'result_count': result_count
                }
                
                self.slow_queries.append(query_info)
                
                # 分析查询模式
                pattern = query_info['pattern']
                self.query_patterns[pattern].append(query_info)
                
                # 更新统计信息
                query_hash = self._get_query_hash(query)
                stats = self.query_stats[query_hash]
                stats['count'] += 1
                stats['total_time'] += execution_time
                stats['avg_time'] = stats['total_time'] / stats['count']
                stats['max_time'] = max(stats['max_time'], execution_time)
                stats['min_time'] = min(stats['min_time'], execution_time)
                stats['result_count'] = result_count
                
                logger.warning("检测到慢查询", {
                    'execution_time': execution_time,
                    'threshold': self.threshold,
                    'pattern': pattern,
                    'result_count': result_count
                })
    
    def get_slow_queries(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取慢查询列表"""
        with self._lock:
            return list(self.slow_queries)[-limit:]
    
    def get_query_patterns(self) -> Dict[str, List[Dict[str, Any]]]:
        """获取查询模式分析"""
        with self._lock:
            return dict(self.query_patterns)
    
    def get_slow_query_stats(self) -> Dict[str, Any]:
        """获取慢查询统计"""
        with self._lock:
            if not self.slow_queries:
                return {'total_slow_queries': 0}
            
            execution_times = [q['execution_time'] for q in self.slow_queries]
            return {
                'total_slow_queries': len(self.slow_queries),
                'avg_execution_time': sum(execution_times) / len(execution_times),
                'max_execution_time': max(execution_times),
                'min_execution_time': min(execution_times),
                'threshold': self.threshold,
                'patterns_count': len(self.query_patterns)
            }
    
    def _extract_query_pattern(self, query: str) -> str:
        """提取查询模式"""
        try:
            # 使用sqlparse解析查询
            parsed = sqlparse.parse(query)
            if parsed:
                # 获取第一个语句
                stmt = parsed[0]
                # 提取表名和操作类型
                tables = []
                operation = 'SELECT'
                
                for token in stmt.tokens:
                    if token.ttype is sqlparse.tokens.Keyword:
                        if token.value.upper() in ['SELECT', 'INSERT', 'UPDATE', 'DELETE']:
                            operation = token.value.upper()
                    elif hasattr(token, 'get_name'):
                        tables.append(token.get_name())
                
                return f"{operation}({','.join(tables)})"
        except Exception:
            pass
        
        # 简单的模式提取：移除具体值，保留结构
        import re
        
        # 移除字符串字面量
        pattern = re.sub(r"'[^']*'", "'*'", query)
        
        # 移除数字
        pattern = re.sub(r'\b\d+\b', '*', pattern)
        
        # 移除参数占位符
        pattern = re.sub(r':\w+', '*', pattern)
        
        return pattern.strip()
    
    def _get_query_hash(self, query: str) -> str:
        """获取查询哈希值"""
        return hashlib.md5(query.encode()).hexdigest()[:12]

# ==================== 索引优化器 ====================

class IndexOptimizer:
    """索引优化器"""
    
    def __init__(self, engine: Engine):
        self.engine = engine
        self.index_suggestions = []
        self.table_stats = {}
    
    def analyze_table_indexes(self, table_name: str) -> Dict[str, Any]:
        """分析表的索引情况"""
        try:
            with self.engine.connect() as conn:
                # 获取表信息
                inspector = inspect(self.engine)
                indexes = inspector.get_indexes(table_name)
                columns = inspector.get_columns(table_name)
                
                # 分析索引使用情况
                index_analysis = {
                    'table_name': table_name,
                    'total_indexes': len(indexes),
                    'indexes': indexes,
                    'columns': columns,
                    'suggestions': []
                }
                
                # 检查是否有主键
                primary_key = inspector.get_pk_constraint(table_name)
                if not primary_key['constrained_columns']:
                    index_analysis['suggestions'].append({
                        'type': 'warning',
                        'message': '表缺少主键',
                        'priority': 'high'
                    })
                
                # 检查常用查询字段是否有索引
                common_query_fields = self._get_common_query_fields(table_name)
                for field in common_query_fields:
                    if not self._has_index_for_field(indexes, field):
                        index_analysis['suggestions'].append({
                            'type': 'suggestion',
                            'message': f'建议为字段 {field} 添加索引',
                            'priority': 'medium',
                            'field': field
                        })
                
                return index_analysis
                
        except Exception as e:
            logger.error(f"分析表索引失败: {e}")
            return {'error': str(e)}
    
    def generate_index_sql(self, table_name: str, field: str, index_type: str = 'btree') -> str:
        """生成创建索引的SQL语句"""
        index_name = f"idx_{table_name}_{field}"
        return f"CREATE INDEX {index_name} ON {table_name} ({field}) USING {index_type};"
    
    def _has_index_for_field(self, indexes: List[Dict], field: str) -> bool:
        """检查字段是否有索引"""
        for index in indexes:
            if field in index['column_names']:
                return True
        return False
    
    def _get_common_query_fields(self, table_name: str) -> List[str]:
        """获取常用查询字段（这里可以根据实际使用情况调整）"""
        # 常见的查询字段模式
        common_patterns = ['id', 'name', 'user_id', 'created_at', 'updated_at', 'status']
        return common_patterns

# ==================== 性能监控器 ====================

class DatabasePerformanceMonitor:
    """数据库性能监控器"""
    
    def __init__(self):
        self.metrics = {
            'query_count': 0,
            'slow_query_count': 0,
            'error_count': 0,
            'total_execution_time': 0.0,
            'avg_execution_time': 0.0,
            'max_execution_time': 0.0,
            'min_execution_time': float('inf')
        }
        self.query_history = deque(maxlen=1000)
        self.error_history = deque(maxlen=100)
        self._lock = threading.RLock()
    
    def record_query(self, query: str, execution_time: float, success: bool = True, 
                    error: str = None, result_count: int = 0) -> None:
        """记录查询执行情况"""
        with self._lock:
            # 更新基本指标
            self.metrics['query_count'] += 1
            self.metrics['total_execution_time'] += execution_time
            
            if execution_time > self.metrics['max_execution_time']:
                self.metrics['max_execution_time'] = execution_time
            
            if execution_time < self.metrics['min_execution_time']:
                self.metrics['min_execution_time'] = execution_time
            
            # 更新平均执行时间
            self.metrics['avg_execution_time'] = self.metrics['total_execution_time'] / self.metrics['query_count']
            
            # 记录查询历史
            query_record = {
                'query': query,
                'execution_time': execution_time,
                'success': success,
                'timestamp': datetime.now(),
                'error': error,
                'result_count': result_count
            }
            self.query_history.append(query_record)
            
            # 记录错误
            if not success:
                self.metrics['error_count'] += 1
                self.error_history.append(query_record)
    
    def get_performance_report(self) -> Dict[str, Any]:
        """获取性能报告"""
        with self._lock:
            return {
                'metrics': self.metrics.copy(),
                'recent_queries': list(self.query_history)[-10:],
                'recent_errors': list(self.error_history)[-10:],
                'timestamp': datetime.now().isoformat()
            }
    
    def reset_metrics(self) -> None:
        """重置性能指标"""
        with self._lock:
            self.metrics = {
                'query_count': 0,
                'slow_query_count': 0,
                'error_count': 0,
                'total_execution_time': 0.0,
                'avg_execution_time': 0.0,
                'max_execution_time': 0.0,
                'min_execution_time': float('inf')
            }
            self.query_history.clear()
            self.error_history.clear()

# ==================== 统一数据库优化器 ====================

class UnifiedDatabaseOptimizer:
    """统一的数据库优化器"""
    
    def __init__(self, engine: Engine, config: Dict[str, Any] = None):
        self.engine = engine
        self.config = config or {}
        self.logger = get_logger('database_optimizer')
        
        # 初始化各个组件
        self.query_cache = QueryCache(
            max_size=self.config.get('cache_max_size', 1000),
            default_ttl=self.config.get('cache_default_ttl', 300)
        )
        
        self.connection_pool = ConnectionPoolManager(engine)
        
        self.slow_query_analyzer = SlowQueryAnalyzer(
            threshold=self.config.get('slow_query_threshold', 1.0)
        )
        
        self.index_optimizer = IndexOptimizer(engine)
        
        self.performance_monitor = DatabasePerformanceMonitor()
        
        logger.info("统一数据库优化器初始化完成")
    
    def optimize_query(self, query: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """查询优化建议"""
        try:
            # 这里可以实现更复杂的查询优化逻辑
            # 例如：重写查询、添加提示等
            
            # 简单的优化建议
            suggestions = []
            
            if 'SELECT *' in query.upper():
                suggestions.append("避免使用 SELECT *，明确指定需要的字段")
            
            if 'WHERE' not in query.upper() and 'LIMIT' not in query.upper():
                suggestions.append("考虑添加 WHERE 条件或 LIMIT 限制")
            
            if 'ORDER BY' in query.upper() and 'LIMIT' not in query.upper():
                suggestions.append("ORDER BY 配合 LIMIT 使用可以提高性能")
            
            if 'JOIN' in query.upper():
                suggestions.append("确保JOIN字段有适当的索引")
            
            return {
                'original_query': query,
                'suggestions': suggestions,
                'optimized': len(suggestions) == 0,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"查询优化失败: {e}")
            return {'error': str(e)}
    
    def get_performance_report(self) -> Dict[str, Any]:
        """获取性能报告"""
        return {
            'query_cache': self.query_cache.get_stats(),
            'connection_pool': self.connection_pool.get_pool_status(),
            'slow_queries': self.slow_query_analyzer.get_slow_query_stats(),
            'performance': self.performance_monitor.get_performance_report()
        }
    
    def optimize_connection_pool(self) -> Dict[str, Any]:
        """优化连接池"""
        return self.connection_pool.optimize_pool()
    
    def analyze_slow_queries(self) -> Dict[str, Any]:
        """分析慢查询"""
        return {
            'recent_slow_queries': self.slow_query_analyzer.get_slow_queries(),
            'query_patterns': self.slow_query_analyzer.get_query_patterns(),
            'stats': self.slow_query_analyzer.get_slow_query_stats()
        }
    
    def analyze_table_indexes(self, table_name: str) -> Dict[str, Any]:
        """分析表索引"""
        return self.index_optimizer.analyze_table_indexes(table_name)
    
    def generate_index_sql(self, table_name: str, field: str, index_type: str = 'btree') -> str:
        """生成索引SQL"""
        return self.index_optimizer.generate_index_sql(table_name, field, index_type)
    
    def clear_cache(self, pattern: str = None) -> int:
        """清除缓存"""
        return self.query_cache.invalidate(pattern)
    
    def reset_metrics(self) -> None:
        """重置性能指标"""
        self.performance_monitor.reset_metrics()
        logger.info("数据库性能指标已重置")

# ==================== 装饰器 ====================

def cached_query(ttl: int = 300, key_prefix: str = ""):
    """
    查询缓存装饰器
    
    Args:
        ttl: 缓存生存时间（秒）
        key_prefix: 缓存键前缀
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存键
            cache_key = f"{key_prefix}:{func.__name__}:{hash(str(args) + str(kwargs))}"
            
            # 尝试从缓存获取
            optimizer = get_database_optimizer()
            if optimizer:
                cached_result = optimizer.query_cache.get(cache_key)
                if cached_result is not None:
                    return cached_result
            
            # 执行查询
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                # 记录性能指标
                if optimizer:
                    optimizer.performance_monitor.record_query(
                        f"Function: {func.__name__}", 
                        execution_time, 
                        success=True
                    )
                    
                    # 缓存结果
                    optimizer.query_cache.set(cache_key, result, ttl)
                
                return result
                
            except Exception as e:
                execution_time = time.time() - start_time
                
                # 记录错误
                if optimizer:
                    optimizer.performance_monitor.record_query(
                        f"Function: {func.__name__}", 
                        execution_time, 
                        success=False, 
                        error=str(e)
                    )
                
                raise
        
        return wrapper
    return decorator

def monitor_query_performance():
    """查询性能监控装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                # 记录性能指标
                optimizer = get_database_optimizer()
                if optimizer:
                    optimizer.performance_monitor.record_query(
                        f"Function: {func.__name__}", 
                        execution_time, 
                        success=True
                    )
                    
                    # 检查是否为慢查询
                    optimizer.slow_query_analyzer.record_query(
                        f"Function: {func.__name__}", 
                        execution_time, 
                        kwargs
                    )
                
                return result
                
            except Exception as e:
                execution_time = time.time() - start_time
                
                # 记录错误
                optimizer = get_database_optimizer()
                if optimizer:
                    optimizer.performance_monitor.record_query(
                        f"Function: {func.__name__}", 
                        execution_time, 
                        success=False, 
                        error=str(e)
                    )
                
                raise
        
        return wrapper
    return decorator

# ==================== 全局实例和工厂函数 ====================

# 全局数据库优化器实例
_global_database_optimizer = None

def init_unified_database_optimizer(engine: Engine, config: Dict[str, Any] = None) -> UnifiedDatabaseOptimizer:
    """初始化全局数据库优化器"""
    global _global_database_optimizer
    _global_database_optimizer = UnifiedDatabaseOptimizer(engine, config)
    return _global_database_optimizer

def get_database_optimizer() -> Optional[UnifiedDatabaseOptimizer]:
    """获取全局数据库优化器"""
    return _global_database_optimizer
# ==================== 向后兼容 ====================

# 为了向后兼容，保留旧的函数名
init_database_advanced_optimization = init_unified_database_optimizer
get_database_optimizer_legacy = get_database_optimizer

# 向后兼容的函数
def init_database_monitoring(engine: Engine, config: Dict[str, Any] = None):
    """初始化数据库监控（向后兼容）"""
    return init_unified_database_optimizer(engine, config)

def get_database_health():
    """获取数据库健康状态（向后兼容）"""
    optimizer = get_database_optimizer()
    if optimizer:
        return optimizer.get_performance_report()
    return {'error': '数据库优化器未初始化'}

def get_query_optimizer():
    """获取查询优化器（向后兼容）"""
    optimizer = get_database_optimizer()
    if optimizer:
        return optimizer
    return None

