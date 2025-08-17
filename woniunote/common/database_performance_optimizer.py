#!/usr/bin/env python3
"""
数据库性能优化器
提供查询优化、索引建议、性能监控等功能
"""

import time
import threading
from typing import Dict, Any, List, Optional, Callable
from collections import defaultdict, deque
from functools import wraps
from sqlalchemy import text, event
from sqlalchemy.engine import Engine
from sqlalchemy.pool import QueuePool
from woniunote.common.simple_logger import get_simple_logger
from woniunote.common.db_connection_manager import get_connection_manager

logger = get_simple_logger('database_performance_optimizer')

class QueryMonitor:
    """查询监控器"""
    
    def __init__(self, slow_query_threshold: float = 1.0):
        self.slow_query_threshold = slow_query_threshold
        self.query_stats = defaultdict(lambda: {
            'count': 0,
            'total_time': 0.0,
            'avg_time': 0.0,
            'max_time': 0.0,
            'min_time': float('inf')
        })
        self.slow_queries = deque(maxlen=100)  # 保存最近100个慢查询
        self.active_queries = {}
        self._lock = threading.RLock()
    
    def start_query(self, query_id: str, sql: str, params: Any = None):
        """开始查询监控"""
        with self._lock:
            self.active_queries[query_id] = {
                'sql': sql,
                'params': params,
                'start_time': time.time(),
                'thread_id': threading.get_ident()
            }
    
    def end_query(self, query_id: str, success: bool = True, error: str = None):
        """结束查询监控"""
        with self._lock:
            if query_id not in self.active_queries:
                return
            
            query_info = self.active_queries.pop(query_id)
            duration = time.time() - query_info['start_time']
            
            # 更新统计信息
            sql_hash = hash(query_info['sql'])
            stats = self.query_stats[sql_hash]
            stats['count'] += 1
            stats['total_time'] += duration
            stats['avg_time'] = stats['total_time'] / stats['count']
            stats['max_time'] = max(stats['max_time'], duration)
            stats['min_time'] = min(stats['min_time'], duration)
            
            # 记录慢查询
            if duration > self.slow_query_threshold:
                slow_query = {
                    'sql': query_info['sql'],
                    'params': query_info['params'],
                    'duration': duration,
                    'timestamp': time.time(),
                    'success': success,
                    'error': error,
                    'thread_id': query_info['thread_id']
                }
                self.slow_queries.append(slow_query)
                
                logger.warning("检测到慢查询", {
                    'sql': query_info['sql'][:200] + '...' if len(query_info['sql']) > 200 else query_info['sql'],
                    'duration_seconds': round(duration, 3),
                    'success': success
                })
    
    def get_query_stats(self) -> Dict[str, Any]:
        """获取查询统计信息"""
        with self._lock:
            return {
                'total_queries': sum(stats['count'] for stats in self.query_stats.values()),
                'slow_queries_count': len(self.slow_queries),
                'active_queries_count': len(self.active_queries),
                'avg_query_time': sum(stats['avg_time'] * stats['count'] for stats in self.query_stats.values()) / 
                                max(sum(stats['count'] for stats in self.query_stats.values()), 1),
                'slowest_queries': sorted(
                    [(sql_hash, stats) for sql_hash, stats in self.query_stats.items()],
                    key=lambda x: x[1]['max_time'],
                    reverse=True
                )[:10]
            }
    
    def get_slow_queries(self, limit: int = 20) -> List[Dict[str, Any]]:
        """获取慢查询列表"""
        with self._lock:
            return list(self.slow_queries)[-limit:]

class DatabaseOptimizer:
    """数据库优化器"""
    
    def __init__(self):
        self.query_monitor = QueryMonitor()
        self.optimization_recommendations = []
        self._setup_event_listeners()
    
    def _setup_event_listeners(self):
        """设置数据库事件监听器"""
        @event.listens_for(Engine, "before_cursor_execute")
        def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            query_id = f"{threading.get_ident()}_{time.time()}"
            context._query_id = query_id
            context._query_start_time = time.time()
            self.query_monitor.start_query(query_id, statement, parameters)
        
        @event.listens_for(Engine, "after_cursor_execute")
        def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            if hasattr(context, '_query_id'):
                self.query_monitor.end_query(context._query_id, success=True)
    
    def analyze_query_performance(self, sql: str, params: Any = None) -> Dict[str, Any]:
        """分析查询性能"""
        try:
            with get_connection_manager().get_session() as session:
                # 执行EXPLAIN分析
                explain_sql = f"EXPLAIN {sql}"
                explain_result = session.execute(text(explain_sql), params or {})
                explain_rows = explain_result.fetchall()
                
                analysis = {
                    'sql': sql,
                    'explain_plan': [dict(row) for row in explain_rows],
                    'recommendations': []
                }
                
                # 分析执行计划并生成建议
                for row in explain_rows:
                    row_dict = dict(row)
                    
                    # 检查全表扫描
                    if 'ALL' in str(row_dict.get('type', '')):
                        analysis['recommendations'].append({
                            'type': 'INDEX_MISSING',
                            'message': '检测到全表扫描，建议添加索引',
                            'table': row_dict.get('table'),
                            'severity': 'HIGH'
                        })
                    
                    # 检查大量行扫描
                    rows = row_dict.get('rows', 0)
                    if isinstance(rows, int) and rows > 10000:
                        analysis['recommendations'].append({
                            'type': 'LARGE_SCAN',
                            'message': f'扫描行数过多({rows}行)，考虑优化查询条件',
                            'table': row_dict.get('table'),
                            'severity': 'MEDIUM'
                        })
                
                return analysis
                
        except Exception as e:
            logger.error(f"查询性能分析失败: {e}")
            return {'error': str(e)}
    
    def suggest_indexes(self, table_name: str) -> List[Dict[str, Any]]:
        """建议索引优化"""
        suggestions = []
        
        try:
            with get_connection_manager().get_session() as session:
                # 检查现有索引
                show_indexes_sql = f"SHOW INDEX FROM {table_name}"
                indexes_result = session.execute(text(show_indexes_sql))
                existing_indexes = [dict(row) for row in indexes_result.fetchall()]
                
                # 检查表结构
                describe_sql = f"DESCRIBE {table_name}"
                columns_result = session.execute(text(describe_sql))
                columns = [dict(row) for row in columns_result.fetchall()]
                
                # 基于常见查询模式建议索引
                foreign_key_columns = [col for col in columns if col['Field'].endswith('id') and col['Field'] != 'id']
                for fk_col in foreign_key_columns:
                    has_index = any(idx['Column_name'] == fk_col['Field'] for idx in existing_indexes)
                    if not has_index:
                        suggestions.append({
                            'type': 'FOREIGN_KEY_INDEX',
                            'column': fk_col['Field'],
                            'sql': f"CREATE INDEX idx_{table_name}_{fk_col['Field']} ON {table_name}({fk_col['Field']})",
                            'reason': '外键列建议添加索引以提高JOIN性能'
                        })
                
                # 检查时间字段索引
                time_columns = [col for col in columns if 'time' in col['Field'].lower() or 'date' in col['Field'].lower()]
                for time_col in time_columns:
                    has_index = any(idx['Column_name'] == time_col['Field'] for idx in existing_indexes)
                    if not has_index:
                        suggestions.append({
                            'type': 'TIME_INDEX',
                            'column': time_col['Field'],
                            'sql': f"CREATE INDEX idx_{table_name}_{time_col['Field']} ON {table_name}({time_col['Field']})",
                            'reason': '时间字段建议添加索引以提高范围查询性能'
                        })
                
                return suggestions
                
        except Exception as e:
            logger.error(f"索引建议分析失败: {e}")
            return []
    
    def optimize_connection_pool(self) -> Dict[str, Any]:
        """优化连接池配置"""
        try:
            connection_manager = get_connection_manager()
            current_stats = connection_manager.get_connection_stats()
            
            recommendations = []
            optimizations = {}
            
            # 分析连接池使用情况
            if current_stats.get('active_sessions', 0) > 80:  # 假设连接池大小为100
                recommendations.append({
                    'type': 'POOL_SIZE_INCREASE',
                    'message': '活跃连接数过高，建议增加连接池大小',
                    'current_active': current_stats.get('active_sessions'),
                    'suggested_pool_size': current_stats.get('active_sessions') * 1.2
                })
            
            if current_stats.get('failed_sessions', 0) > current_stats.get('successful_sessions', 1) * 0.05:
                recommendations.append({
                    'type': 'CONNECTION_RELIABILITY',
                    'message': '连接失败率过高，检查网络和数据库配置',
                    'failure_rate': current_stats.get('failed_sessions') / max(current_stats.get('successful_sessions'), 1)
                })
            
            return {
                'current_stats': current_stats,
                'recommendations': recommendations,
                'optimizations': optimizations
            }
            
        except Exception as e:
            logger.error(f"连接池优化分析失败: {e}")
            return {'error': str(e)}
    
    def generate_performance_report(self) -> Dict[str, Any]:
        """生成性能报告"""
        query_stats = self.query_monitor.get_query_stats()
        slow_queries = self.query_monitor.get_slow_queries()
        
        # 分析最常用的表
        table_usage = defaultdict(int)
        for query in slow_queries:
            sql = query['sql'].upper()
            # 简单的表名提取（实际项目中可能需要更复杂的SQL解析）
            words = sql.split()
            for i, word in enumerate(words):
                if word in ['FROM', 'JOIN', 'UPDATE', 'INTO'] and i + 1 < len(words):
                    table_name = words[i + 1].strip('`').strip("'").strip('"')
                    table_usage[table_name] += 1
        
        report = {
            'timestamp': time.time(),
            'query_statistics': query_stats,
            'slow_queries_sample': slow_queries[:10],
            'table_usage': dict(table_usage),
            'recommendations': []
        }
        
        # 生成优化建议
        if query_stats['slow_queries_count'] > 10:
            report['recommendations'].append({
                'type': 'SLOW_QUERY_OPTIMIZATION',
                'priority': 'HIGH',
                'message': f'检测到{query_stats["slow_queries_count"]}个慢查询，建议优化'
            })
        
        if query_stats['avg_query_time'] > 0.5:
            report['recommendations'].append({
                'type': 'AVERAGE_PERFORMANCE',
                'priority': 'MEDIUM',
                'message': f'平均查询时间{query_stats["avg_query_time"]:.2f}秒，建议优化'
            })
        
        return report

def query_performance_monitor(threshold: float = 1.0):
    """查询性能监控装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            query_id = f"{func.__name__}_{threading.get_ident()}_{start_time}"
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                if duration > threshold:
                    logger.warning("慢函数检测", {
                        'function': f"{func.__module__}.{func.__name__}",
                        'duration_seconds': round(duration, 3),
                        'args_count': len(args),
                        'kwargs_keys': list(kwargs.keys())
                    })
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                logger.error("函数执行异常", {
                    'function': f"{func.__module__}.{func.__name__}",
                    'duration_seconds': round(duration, 3),
                    'error': str(e)
                })
                raise
        
        return wrapper
    return decorator

def optimize_query_batch_size(items: List[Any], batch_size: int = 100, 
                            process_func: Callable = None) -> List[Any]:
    """优化批量查询，避免大量数据一次性加载"""
    results = []
    total_batches = (len(items) + batch_size - 1) // batch_size
    
    logger.info("开始批量处理", {
        'total_items': len(items),
        'batch_size': batch_size,
        'total_batches': total_batches
    })
    
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        batch_num = (i // batch_size) + 1
        
        start_time = time.time()
        
        if process_func:
            batch_results = process_func(batch)
        else:
            batch_results = batch
        
        results.extend(batch_results)
        
        duration = time.time() - start_time
        logger.debug(f"批次{batch_num}/{total_batches}处理完成", {
            'batch_size': len(batch),
            'duration_seconds': round(duration, 3)
        })
    
    return results

# 全局数据库优化器实例
database_optimizer = DatabaseOptimizer()

# 便捷函数
def get_query_performance_stats() -> Dict[str, Any]:
    """获取查询性能统计"""
    return database_optimizer.query_monitor.get_query_stats()

def get_slow_queries(limit: int = 20) -> List[Dict[str, Any]]:
    """获取慢查询列表"""
    return database_optimizer.query_monitor.get_slow_queries(limit)

def generate_db_performance_report() -> Dict[str, Any]:
    """生成数据库性能报告"""
    return database_optimizer.generate_performance_report()

def analyze_query(sql: str, params: Any = None) -> Dict[str, Any]:
    """分析查询性能"""
    return database_optimizer.analyze_query_performance(sql, params)