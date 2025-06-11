#!/usr/bin/env python3
"""
Phase 6 高级数据库优化模块
提供查询缓存、连接池管理、慢查询分析、索引优化建议等企业级数据库性能优化功能
"""

import os
import time
import threading
import logging
import hashlib
import json
from typing import Dict, Any, List, Optional, Tuple, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
from functools import wraps
from contextlib import contextmanager
import sqlparse
from sqlalchemy import event, text
from sqlalchemy.engine import Engine
from sqlalchemy.pool import QueuePool
import weakref

logger = logging.getLogger(__name__)

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

@dataclass
class IndexSuggestion:
    """索引建议"""
    table_name: str
    columns: List[str]
    index_type: str  # 'btree', 'hash', 'composite'
    estimated_benefit: float
    usage_frequency: int
    reasoning: str

class QueryCache:
    """智能查询缓存"""
    
    def __init__(self, max_size: int = 5000, ttl: int = 300):
        self.max_size = max_size
        self.ttl = ttl
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
            'total_size': 0
        }
    
    def _generate_cache_key(self, query: str, params: tuple = None) -> str:
        """生成缓存键"""
        # 标准化查询文本
        normalized_query = sqlparse.format(query, strip_whitespace=True, keyword_case='upper')
        key_data = f"{normalized_query}:{params or ''}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _evict_expired(self):
        """清理过期缓存"""
        current_time = time.time()
        expired_keys = []
        
        for key, (data, timestamp) in self.cache.items():
            if current_time - timestamp > self.ttl:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.cache[key]
            self.access_times.pop(key, None)
            self.stats['evictions'] += 1
    
    def _evict_lru(self):
        """LRU淘汰"""
        if len(self.cache) <= self.max_size:
            return
        
        # 按访问时间排序，删除最旧的
        sorted_items = sorted(self.access_times.items(), key=lambda x: x[1])
        keys_to_remove = [item[0] for item in sorted_items[:len(self.cache) - self.max_size]]
        
        for key in keys_to_remove:
            self.cache.pop(key, None)
            self.access_times.pop(key, None)
            self.stats['evictions'] += 1
    
    def get(self, query: str, params: tuple = None) -> Optional[Any]:
        """获取缓存结果"""
        with self.lock:
            self._evict_expired()
            
            cache_key = self._generate_cache_key(query, params)
            
            if cache_key in self.cache:
                data, timestamp = self.cache[cache_key]
                self.access_times[cache_key] = time.time()
                self.hit_count += 1
                self.stats['hits'] += 1
                logger.debug(f"Query cache hit: {cache_key[:16]}...")
                return data
            
            self.miss_count += 1
            self.stats['misses'] += 1
            return None
    
    def set(self, query: str, result: Any, params: tuple = None):
        """设置缓存"""
        with self.lock:
            cache_key = self._generate_cache_key(query, params)
            current_time = time.time()
            
            self.cache[cache_key] = (result, current_time)
            self.access_times[cache_key] = current_time
            
            # 检查大小限制
            self._evict_lru()
            
            self.stats['total_size'] = len(self.cache)
    
    def invalidate_table(self, table_name: str):
        """使表相关的缓存失效"""
        with self.lock:
            keys_to_remove = []
            
            for key, (data, timestamp) in self.cache.items():
                # 这里需要解析查询以确定涉及的表
                # 简化处理：如果查询包含表名就使其失效
                if table_name.upper() in str(data).upper():
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                self.cache.pop(key, None)
                self.access_times.pop(key, None)
    
    def clear(self):
        """清空缓存"""
        with self.lock:
            self.cache.clear()
            self.access_times.clear()
            self.stats = {'hits': 0, 'misses': 0, 'evictions': 0, 'total_size': 0}
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        with self.lock:
            total_requests = self.hit_count + self.miss_count
            hit_rate = self.hit_count / total_requests if total_requests > 0 else 0
            
            return {
                'hit_count': self.hit_count,
                'miss_count': self.miss_count,
                'hit_rate': hit_rate,
                'cache_size': len(self.cache),
                'max_size': self.max_size,
                'stats': self.stats.copy()
            }

class ConnectionPoolManager:
    """连接池管理器"""
    
    def __init__(self, engine):
        self.engine = engine
        self.pool_stats = defaultdict(list)
        self.connection_metrics = deque(maxlen=1000)
        self.lock = threading.Lock()
        
        # 监控连接池事件
        self._setup_pool_monitoring()
    
    def _setup_pool_monitoring(self):
        """设置连接池监控"""
        
        @event.listens_for(self.engine, "connect")
        def receive_connect(dbapi_connection, connection_record):
            """连接创建事件"""
            with self.lock:
                self.connection_metrics.append({
                    'event': 'connect',
                    'timestamp': time.time(),
                    'connection_id': id(dbapi_connection)
                })
        
        @event.listens_for(self.engine, "checkout")
        def receive_checkout(dbapi_connection, connection_record, connection_proxy):
            """连接检出事件"""
            with self.lock:
                self.connection_metrics.append({
                    'event': 'checkout',
                    'timestamp': time.time(),
                    'connection_id': id(dbapi_connection)
                })
        
        @event.listens_for(self.engine, "checkin")
        def receive_checkin(dbapi_connection, connection_record):
            """连接检入事件"""
            with self.lock:
                self.connection_metrics.append({
                    'event': 'checkin',
                    'timestamp': time.time(),
                    'connection_id': id(dbapi_connection)
                })
    
    def get_pool_status(self) -> Dict[str, Any]:
        """获取连接池状态"""
        try:
            pool = self.engine.pool
            
            status = {
                'size': pool.size(),
                'checked_out': pool.checkedout(),
                'overflow': pool.overflow(),
                'invalidated': pool.invalidated(),
                'pool_class': pool.__class__.__name__
            }
            
            if isinstance(pool, QueuePool):
                status.update({
                    'timeout': pool._timeout,
                    'max_overflow': pool._max_overflow,
                    'pre_ping': pool._pre_ping
                })
            
            return status
        except Exception as e:
            logger.error(f"Error getting pool status: {e}")
            return {}
    
    def get_connection_history(self, minutes: int = 60) -> List[Dict[str, Any]]:
        """获取连接历史"""
        with self.lock:
            cutoff_time = time.time() - (minutes * 60)
            recent_metrics = [
                metric for metric in self.connection_metrics
                if metric['timestamp'] >= cutoff_time
            ]
            return recent_metrics
    
    def analyze_connection_patterns(self) -> Dict[str, Any]:
        """分析连接模式"""
        with self.lock:
            if not self.connection_metrics:
                return {}
            
            recent_metrics = list(self.connection_metrics)[-100:]  # 最近100个事件
            
            event_counts = defaultdict(int)
            connection_lifetimes = {}
            checkout_times = {}
            
            for metric in recent_metrics:
                event_counts[metric['event']] += 1
                
                if metric['event'] == 'checkout':
                    checkout_times[metric['connection_id']] = metric['timestamp']
                elif metric['event'] == 'checkin':
                    connection_id = metric['connection_id']
                    if connection_id in checkout_times:
                        lifetime = metric['timestamp'] - checkout_times[connection_id]
                        connection_lifetimes[connection_id] = lifetime
                        del checkout_times[connection_id]
            
            avg_lifetime = sum(connection_lifetimes.values()) / len(connection_lifetimes) if connection_lifetimes else 0
            
            return {
                'event_counts': dict(event_counts),
                'avg_connection_lifetime': avg_lifetime,
                'active_connections': len(checkout_times),
                'total_events': len(recent_metrics)
            }

class SlowQueryAnalyzer:
    """慢查询分析器"""
    
    def __init__(self, slow_threshold: float = 1.0):
        self.slow_threshold = slow_threshold
        self.slow_queries = deque(maxlen=1000)
        self.query_patterns = defaultdict(list)
        self.lock = threading.Lock()
    
    def analyze_query(self, query: str, execution_time: float, params: tuple = None) -> QueryAnalysis:
        """分析查询"""
        query_hash = hashlib.md5(query.encode()).hexdigest()
        
        with self.lock:
            # 记录慢查询
            if execution_time > self.slow_threshold:
                self.slow_queries.append({
                    'query': query,
                    'execution_time': execution_time,
                    'timestamp': datetime.now(),
                    'params': params
                })
            
            # 更新查询模式统计
            pattern_key = self._extract_query_pattern(query)
            self.query_patterns[pattern_key].append({
                'execution_time': execution_time,
                'timestamp': time.time()
            })
            
            # 生成分析结果
            return self._generate_analysis(query, query_hash, execution_time)
    
    def _extract_query_pattern(self, query: str) -> str:
        """提取查询模式"""
        try:
            parsed = sqlparse.parse(query)[0]
            tokens = [token.ttype for token in parsed.flatten() if token.ttype]
            return str(tokens)
        except:
            return query[:50]  # 简化处理
    
    def _generate_analysis(self, query: str, query_hash: str, execution_time: float) -> QueryAnalysis:
        """生成查询分析"""
        
        # 提取表名
        tables_accessed = self._extract_tables(query)
        
        # 生成优化建议
        suggestions = self._generate_optimization_suggestions(query, execution_time)
        
        return QueryAnalysis(
            query_hash=query_hash,
            query_text=query,
            execution_time=execution_time,
            execution_count=1,
            avg_execution_time=execution_time,
            max_execution_time=execution_time,
            min_execution_time=execution_time,
            last_execution=datetime.now(),
            tables_accessed=tables_accessed,
            index_usage={},
            optimization_suggestions=suggestions
        )
    
    def _extract_tables(self, query: str) -> List[str]:
        """提取查询中的表名"""
        try:
            parsed = sqlparse.parse(query)[0]
            tables = []
            
            # 简化的表名提取逻辑
            tokens = list(parsed.flatten())
            for i, token in enumerate(tokens):
                if token.ttype is None and token.value.upper() in ['FROM', 'JOIN', 'UPDATE', 'INSERT']:
                    # 查找下一个可能的表名
                    for j in range(i + 1, min(i + 5, len(tokens))):
                        next_token = tokens[j]
                        if (next_token.ttype is None and 
                            next_token.value.isalnum() and 
                            not next_token.value.upper() in sqlparse.keywords.KEYWORDS):
                            tables.append(next_token.value)
                            break
            
            return list(set(tables))
        except:
            return []
    
    def _generate_optimization_suggestions(self, query: str, execution_time: float) -> List[str]:
        """生成优化建议"""
        suggestions = []
        
        query_upper = query.upper()
        
        # 检查是否使用索引
        if 'WHERE' in query_upper and execution_time > 0.5:
            suggestions.append("考虑在WHERE子句的列上添加索引")
        
        # 检查JOIN优化
        if 'JOIN' in query_upper and execution_time > 1.0:
            suggestions.append("检查JOIN条件是否有适当的索引")
        
        # 检查SELECT *
        if 'SELECT *' in query_upper:
            suggestions.append("避免使用SELECT *，只选择需要的列")
        
        # 检查ORDER BY
        if 'ORDER BY' in query_upper and execution_time > 0.8:
            suggestions.append("考虑在ORDER BY列上添加索引")
        
        # 检查子查询
        if query_upper.count('SELECT') > 1:
            suggestions.append("考虑将子查询改写为JOIN")
        
        # 检查LIMIT
        if 'LIMIT' not in query_upper and 'SELECT' in query_upper:
            suggestions.append("考虑添加LIMIT子句限制结果集大小")
        
        return suggestions
    
    def get_slow_queries(self, limit: int = 20) -> List[Dict[str, Any]]:
        """获取慢查询列表"""
        with self.lock:
            return list(self.slow_queries)[-limit:]
    
    def get_query_patterns(self) -> Dict[str, Any]:
        """获取查询模式统计"""
        with self.lock:
            patterns_summary = {}
            
            for pattern, executions in self.query_patterns.items():
                if executions:
                    avg_time = sum(e['execution_time'] for e in executions) / len(executions)
                    max_time = max(e['execution_time'] for e in executions)
                    count = len(executions)
                    
                    patterns_summary[pattern] = {
                        'count': count,
                        'avg_execution_time': avg_time,
                        'max_execution_time': max_time,
                        'is_slow': avg_time > self.slow_threshold
                    }
            
            return patterns_summary

class IndexOptimizer:
    """索引优化器"""
    
    def __init__(self):
        self.query_analysis = defaultdict(list)
        self.table_access_patterns = defaultdict(int)
        self.column_usage = defaultdict(int)
        self.lock = threading.Lock()
    
    def record_query_access(self, query: str, execution_time: float):
        """记录查询访问"""
        with self.lock:
            # 分析查询中的列使用情况
            columns = self._extract_query_columns(query)
            tables = self._extract_tables_from_query(query)
            
            for table in tables:
                self.table_access_patterns[table] += 1
            
            for column in columns:
                self.column_usage[column] += 1
            
            # 记录查询分析
            self.query_analysis[query].append({
                'execution_time': execution_time,
                'timestamp': time.time(),
                'columns': columns,
                'tables': tables
            })
    
    def _extract_query_columns(self, query: str) -> List[str]:
        """提取查询中使用的列"""
        columns = []
        
        try:
            # 简化的列提取逻辑
            query_upper = query.upper()
            
            # WHERE条件中的列
            if 'WHERE' in query_upper:
                where_part = query_upper.split('WHERE')[1].split('ORDER BY')[0].split('GROUP BY')[0]
                # 查找等号前的标识符
                import re
                column_matches = re.findall(r'(\w+)\s*[=<>!]', where_part)
                columns.extend(column_matches)
            
            # ORDER BY中的列
            if 'ORDER BY' in query_upper:
                order_part = query_upper.split('ORDER BY')[1].split('LIMIT')[0]
                import re
                order_columns = re.findall(r'(\w+)', order_part)
                columns.extend(order_columns)
            
            # GROUP BY中的列
            if 'GROUP BY' in query_upper:
                group_part = query_upper.split('GROUP BY')[1].split('ORDER BY')[0].split('LIMIT')[0]
                import re
                group_columns = re.findall(r'(\w+)', group_part)
                columns.extend(group_columns)
            
        except Exception as e:
            logger.warning(f"Error extracting columns: {e}")
        
        return list(set(columns))
    
    def _extract_tables_from_query(self, query: str) -> List[str]:
        """从查询中提取表名"""
        # 这里可以重用之前的逻辑
        try:
            parsed = sqlparse.parse(query)[0]
            tables = []
            
            tokens = list(parsed.flatten())
            for i, token in enumerate(tokens):
                if token.ttype is None and token.value.upper() in ['FROM', 'JOIN', 'UPDATE', 'INSERT']:
                    for j in range(i + 1, min(i + 5, len(tokens))):
                        next_token = tokens[j]
                        if (next_token.ttype is None and 
                            next_token.value.isalnum() and 
                            not next_token.value.upper() in sqlparse.keywords.KEYWORDS):
                            tables.append(next_token.value)
                            break
            
            return list(set(tables))
        except:
            return []
    
    def suggest_indexes(self) -> List[IndexSuggestion]:
        """建议索引"""
        suggestions = []
        
        with self.lock:
            # 分析最常用的列
            sorted_columns = sorted(self.column_usage.items(), key=lambda x: x[1], reverse=True)
            
            for column, usage_count in sorted_columns[:20]:  # 前20个最常用的列
                if usage_count >= 5:  # 使用次数阈值
                    # 估算收益
                    estimated_benefit = min(usage_count * 0.1, 1.0)
                    
                    suggestions.append(IndexSuggestion(
                        table_name="auto_detected",  # 需要进一步分析确定表名
                        columns=[column],
                        index_type="btree",
                        estimated_benefit=estimated_benefit,
                        usage_frequency=usage_count,
                        reasoning=f"列 {column} 在查询中使用频率高 ({usage_count} 次)"
                    ))
            
            # 分析复合索引机会
            # 查找经常一起出现的列
            column_combinations = defaultdict(int)
            
            for analyses in self.query_analysis.values():
                for analysis in analyses:
                    columns = analysis['columns']
                    if len(columns) >= 2:
                        # 为所有列组合计数
                        for i in range(len(columns)):
                            for j in range(i + 1, len(columns)):
                                combo = tuple(sorted([columns[i], columns[j]]))
                                column_combinations[combo] += 1
            
            # 为高频组合建议复合索引
            for combo, count in sorted(column_combinations.items(), key=lambda x: x[1], reverse=True):
                if count >= 3:  # 组合使用阈值
                    suggestions.append(IndexSuggestion(
                        table_name="auto_detected",
                        columns=list(combo),
                        index_type="composite",
                        estimated_benefit=min(count * 0.15, 1.0),
                        usage_frequency=count,
                        reasoning=f"列组合 {combo} 经常一起使用 ({count} 次)"
                    ))
        
        return suggestions[:10]  # 返回前10个建议

class DatabaseAdvancedOptimizer:
    """高级数据库优化器主类"""
    
    def __init__(self, app=None, slow_query_threshold: float = 1.0):
        self.app = app
        self.query_cache = QueryCache()
        self.slow_query_analyzer = SlowQueryAnalyzer(slow_query_threshold)
        self.index_optimizer = IndexOptimizer()
        self.connection_pool_manager = None
        
        # 优化统计
        self.optimization_stats = {
            'cache_hits': 0,
            'cache_misses': 0,
            'slow_queries_detected': 0,
            'optimizations_applied': 0
        }
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """初始化Flask应用"""
        self.app = app
        
        # 获取数据库引擎
        from flask_sqlalchemy import SQLAlchemy
        db = SQLAlchemy()
        engine = db.get_engine()
        
        # 初始化连接池管理器
        self.connection_pool_manager = ConnectionPoolManager(engine)
        
        # 设置查询监控
        self._setup_query_monitoring(engine)
        
        logger.info("Advanced database optimizer initialized")
    
    def _setup_query_monitoring(self, engine):
        """设置查询监控"""
        
        @event.listens_for(engine, "before_cursor_execute")
        def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            """查询执行前事件"""
            context._query_start_time = time.time()
        
        @event.listens_for(engine, "after_cursor_execute")
        def receive_after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            """查询执行后事件"""
            if hasattr(context, '_query_start_time'):
                execution_time = time.time() - context._query_start_time
                
                # 分析查询
                self.slow_query_analyzer.analyze_query(statement, execution_time, parameters)
                self.index_optimizer.record_query_access(statement, execution_time)
                
                # 更新统计
                if execution_time > self.slow_query_analyzer.slow_threshold:
                    self.optimization_stats['slow_queries_detected'] += 1
    
    @contextmanager
    def cached_query(self, query: str, params: tuple = None):
        """缓存查询上下文管理器"""
        # 尝试从缓存获取
        cached_result = self.query_cache.get(query, params)
        
        if cached_result is not None:
            self.optimization_stats['cache_hits'] += 1
            yield cached_result
        else:
            self.optimization_stats['cache_misses'] += 1
            # 执行查询并缓存结果
            # 这里需要实际的查询执行逻辑
            yield None
    
    def invalidate_table_cache(self, table_name: str):
        """使表缓存失效"""
        self.query_cache.invalidate_table(table_name)
    
    def get_optimization_report(self) -> Dict[str, Any]:
        """获取优化报告"""
        return {
            'timestamp': datetime.now().isoformat(),
            'cache_stats': self.query_cache.get_stats(),
            'slow_queries': self.slow_query_analyzer.get_slow_queries(10),
            'query_patterns': self.slow_query_analyzer.get_query_patterns(),
            'index_suggestions': [asdict(suggestion) for suggestion in self.index_optimizer.suggest_indexes()],
            'connection_pool_status': self.connection_pool_manager.get_pool_status() if self.connection_pool_manager else {},
            'connection_patterns': self.connection_pool_manager.analyze_connection_patterns() if self.connection_pool_manager else {},
            'optimization_stats': self.optimization_stats.copy()
        }
    
    def apply_automatic_optimizations(self) -> List[str]:
        """应用自动优化"""
        applied_optimizations = []
        
        try:
            # 清理过期缓存
            cache_stats_before = self.query_cache.get_stats()
            # QueryCache内部会自动清理过期项
            cache_stats_after = self.query_cache.get_stats()
            
            if cache_stats_before['cache_size'] > cache_stats_after['cache_size']:
                applied_optimizations.append("清理了过期查询缓存")
            
            # 分析连接池状态并提出建议
            if self.connection_pool_manager:
                pool_status = self.connection_pool_manager.get_pool_status()
                
                if pool_status.get('checked_out', 0) > pool_status.get('size', 10) * 0.8:
                    applied_optimizations.append("检测到连接池使用率高，建议增加连接池大小")
                
                patterns = self.connection_pool_manager.analyze_connection_patterns()
                if patterns.get('avg_connection_lifetime', 0) > 300:  # 5分钟
                    applied_optimizations.append("检测到连接生命周期过长，建议优化连接管理")
            
            # 更新统计
            self.optimization_stats['optimizations_applied'] += len(applied_optimizations)
            
        except Exception as e:
            logger.error(f"Error applying automatic optimizations: {e}")
            applied_optimizations.append(f"自动优化过程中出现错误: {str(e)}")
        
        return applied_optimizations

# 全局实例
_db_optimizer = None

def get_database_optimizer() -> DatabaseAdvancedOptimizer:
    """获取数据库优化器实例"""
    global _db_optimizer
    if _db_optimizer is None:
        _db_optimizer = DatabaseAdvancedOptimizer()
    return _db_optimizer

def init_database_advanced_optimization(app, slow_query_threshold: float = 1.0):
    """初始化高级数据库优化"""
    try:
        db_optimizer = get_database_optimizer()
        db_optimizer.slow_query_analyzer.slow_threshold = slow_query_threshold
        db_optimizer.init_app(app)
        
        logger.info("Advanced database optimization system initialized successfully")
        return db_optimizer
        
    except Exception as e:
        logger.error(f"Failed to initialize advanced database optimization: {e}")
        raise

# 装饰器
def cached_query(ttl: int = 300):
    """查询缓存装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存键
            cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            
            db_optimizer = get_database_optimizer()
            cached_result = db_optimizer.query_cache.get(cache_key)
            
            if cached_result is not None:
                return cached_result
            
            # 执行函数并缓存结果
            result = func(*args, **kwargs)
            db_optimizer.query_cache.set(cache_key, result)
            
            return result
        
        return wrapper
    return decorator 