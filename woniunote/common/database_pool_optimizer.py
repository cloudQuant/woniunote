"""
数据库连接池优化模块
提供连接池监控、优化和健康检查功能
"""
import time
import threading
from typing import Dict, Any, Optional
from sqlalchemy import event, pool
from sqlalchemy.engine import Engine
from sqlalchemy.pool import QueuePool
from woniunote.common.simple_logger import get_simple_logger

logger = get_simple_logger('database_pool')

class DatabasePoolOptimizer:
    """数据库连接池优化器"""
    
    def __init__(self):
        self.pool_stats = {
            'connections_created': 0,
            'connections_closed': 0,
            'connections_active': 0,
            'connections_checked_out': 0,
            'pool_overflows': 0,
            'pool_invalidated': 0,
            'query_count': 0,
            'slow_queries': 0,
            'total_query_time': 0.0,
            'last_reset': time.time()
        }
        self.slow_query_threshold = 1.0  # 1秒
        self.lock = threading.Lock()
        self.monitoring_enabled = True
    
    def get_optimized_engine_options(self, database_uri: str) -> Dict[str, Any]:
        """获取优化的数据库引擎选项"""
        base_options = {
            'poolclass': QueuePool,
            'pool_pre_ping': True,
            'pool_recycle': 3600,  # 1小时回收连接
            'pool_timeout': 30,    # 30秒获取连接超时
            'max_overflow': 10,    # 最大溢出连接数
            'echo': False,         # 生产环境关闭SQL日志
            'echo_pool': False,    # 关闭连接池日志
        }
        
        # 根据数据库类型优化配置
        if 'mysql' in database_uri.lower():
            base_options.update({
                'pool_size': 20,      # MySQL连接池大小
                'connect_args': {
                    'connect_timeout': 10,
                    'read_timeout': 30,
                    'write_timeout': 30,
                    'charset': 'utf8mb4',
                    'autocommit': True,
                }
            })
        elif 'postgresql' in database_uri.lower():
            base_options.update({
                'pool_size': 15,      # PostgreSQL连接池大小
                'connect_args': {
                    'connect_timeout': 10,
                    'application_name': 'woniunote',
                }
            })
        elif 'sqlite' in database_uri.lower():
            base_options.update({
                'pool_size': 5,       # SQLite连接池大小较小
                'max_overflow': 0,    # SQLite不支持并发写入
                'poolclass': pool.StaticPool,
                'connect_args': {
                    'check_same_thread': False,
                    'timeout': 30,
                }
            })
        else:
            # 默认配置
            base_options['pool_size'] = 10
        
        logger.info(f"数据库连接池配置: pool_size={base_options.get('pool_size')}, "
                   f"max_overflow={base_options.get('max_overflow')}")
        
        return base_options
    
    def setup_monitoring(self, engine: Engine):
        """设置数据库连接池监控"""
        if not self.monitoring_enabled:
            return
        
        @event.listens_for(engine, "connect")
        def on_connect(dbapi_conn, connection_record):
            """连接创建事件"""
            with self.lock:
                self.pool_stats['connections_created'] += 1
            logger.debug("数据库连接已创建")
        
        @event.listens_for(engine, "checkout")
        def on_checkout(dbapi_conn, connection_record, connection_proxy):
            """连接检出事件"""
            with self.lock:
                self.pool_stats['connections_checked_out'] += 1
                self.pool_stats['connections_active'] += 1
        
        @event.listens_for(engine, "checkin")
        def on_checkin(dbapi_conn, connection_record):
            """连接检入事件"""
            with self.lock:
                self.pool_stats['connections_active'] = max(0, self.pool_stats['connections_active'] - 1)
        
        @event.listens_for(engine, "close")
        def on_close(dbapi_conn, connection_record):
            """连接关闭事件"""
            with self.lock:
                self.pool_stats['connections_closed'] += 1
            logger.debug("数据库连接已关闭")
        
        @event.listens_for(engine, "invalidate")
        def on_invalidate(dbapi_conn, connection_record, exception):
            """连接无效化事件"""
            with self.lock:
                self.pool_stats['pool_invalidated'] += 1
            logger.warning(f"数据库连接被无效化: {exception}")
        
        @event.listens_for(engine, "before_cursor_execute")
        def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            """查询执行前事件"""
            context._query_start_time = time.time()
        
        @event.listens_for(engine, "after_cursor_execute")
        def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            """查询执行后事件"""
            if hasattr(context, '_query_start_time'):
                execution_time = time.time() - context._query_start_time
                
                with self.lock:
                    self.pool_stats['query_count'] += 1
                    self.pool_stats['total_query_time'] += execution_time
                    
                    if execution_time > self.slow_query_threshold:
                        self.pool_stats['slow_queries'] += 1
                        logger.warning(f"慢查询检测: {execution_time:.3f}s - {statement[:100]}...")
        
        logger.info("数据库连接池监控已启用")
    
    def get_pool_status(self, engine: Engine) -> Dict[str, Any]:
        """获取连接池状态"""
        try:
            pool = engine.pool
            pool_status = {
                'pool_size': getattr(pool, 'size', 0),
                'checked_out_connections': getattr(pool, 'checkedout', 0),
                'overflow_connections': getattr(pool, 'overflow', 0),
                'checked_in_connections': getattr(pool, 'checkedin', 0),
                'total_connections': getattr(pool, 'checkedout', 0) + getattr(pool, 'checkedin', 0),
                'pool_status': 'healthy'
            }
            
            # 检查连接池健康状态
            if pool_status['checked_out_connections'] >= pool_status['pool_size'] * 0.9:
                pool_status['pool_status'] = 'warning_high_usage'
            
            if pool_status['overflow_connections'] > 0:
                pool_status['pool_status'] = 'overflow_active'
            
            # 添加统计信息
            with self.lock:
                pool_status.update(self.pool_stats.copy())
            
            return pool_status
            
        except Exception as e:
            logger.error(f"获取连接池状态失败: {e}")
            return {'error': str(e)}
    
    def optimize_pool_settings(self, engine: Engine, current_load: float = 0.0) -> Dict[str, Any]:
        """动态优化连接池设置"""
        try:
            pool_status = self.get_pool_status(engine)
            recommendations = []
            
            # 基于当前负载优化
            if current_load > 0.8:  # 高负载
                if pool_status.get('overflow_connections', 0) > 0:
                    recommendations.append("考虑增加pool_size以减少overflow")
                
                if pool_status.get('slow_queries', 0) > pool_status.get('query_count', 1) * 0.1:
                    recommendations.append("慢查询较多，建议优化SQL或增加连接超时")
            
            elif current_load < 0.3:  # 低负载
                if pool_status.get('checked_in_connections', 0) > pool_status.get('pool_size', 0) * 0.7:
                    recommendations.append("连接池可能过大，可以考虑减少pool_size")
            
            # 连接回收建议
            avg_query_time = 0
            if pool_status.get('query_count', 0) > 0:
                avg_query_time = pool_status.get('total_query_time', 0) / pool_status.get('query_count', 1)
            
            if avg_query_time > 0.5:
                recommendations.append("平均查询时间较长，建议优化查询或增加pool_timeout")
            
            return {
                'current_status': pool_status,
                'recommendations': recommendations,
                'optimal_settings': self._calculate_optimal_settings(pool_status, current_load)
            }
            
        except Exception as e:
            logger.error(f"连接池优化分析失败: {e}")
            return {'error': str(e)}
    
    def _calculate_optimal_settings(self, pool_status: Dict[str, Any], load: float) -> Dict[str, Any]:
        """计算最优设置"""
        current_size = pool_status.get('pool_size', 10)
        
        # 基于负载计算建议的连接池大小
        if load > 0.8:
            suggested_size = min(current_size + 5, 50)  # 最大50个连接
        elif load < 0.3:
            suggested_size = max(current_size - 2, 5)   # 最小5个连接
        else:
            suggested_size = current_size
        
        return {
            'pool_size': suggested_size,
            'max_overflow': max(suggested_size // 2, 5),
            'pool_timeout': 30 if load > 0.7 else 20,
            'pool_recycle': 3600 if load < 0.5 else 1800,
        }
    
    def reset_stats(self):
        """重置统计信息"""
        with self.lock:
            self.pool_stats = {
                'connections_created': 0,
                'connections_closed': 0,
                'connections_active': 0,
                'connections_checked_out': 0,
                'pool_overflows': 0,
                'pool_invalidated': 0,
                'query_count': 0,
                'slow_queries': 0,
                'total_query_time': 0.0,
                'last_reset': time.time()
            }
        logger.info("连接池统计信息已重置")
    
    def health_check(self, engine: Engine) -> Dict[str, Any]:
        """连接池健康检查"""
        try:
            # 测试连接
            with engine.connect() as conn:
                result = conn.execute("SELECT 1").fetchone()
                if result[0] != 1:
                    return {'healthy': False, 'error': '连接测试失败'}
            
            # 获取连接池状态
            pool_status = self.get_pool_status(engine)
            
            # 健康检查评分
            health_score = 100
            issues = []
            
            # 检查连接池使用率
            usage_rate = (pool_status.get('checked_out_connections', 0) / 
                         max(pool_status.get('pool_size', 1), 1))
            
            if usage_rate > 0.9:
                health_score -= 20
                issues.append('连接池使用率过高')
            
            # 检查慢查询比例
            query_count = pool_status.get('query_count', 1)
            slow_query_rate = pool_status.get('slow_queries', 0) / query_count
            
            if slow_query_rate > 0.1:
                health_score -= 15
                issues.append('慢查询比例过高')
            
            # 检查连接池溢出
            if pool_status.get('overflow_connections', 0) > 0:
                health_score -= 10
                issues.append('连接池发生溢出')
            
            return {
                'healthy': health_score >= 70,
                'health_score': health_score,
                'issues': issues,
                'pool_status': pool_status,
                'usage_rate': usage_rate,
                'slow_query_rate': slow_query_rate
            }
            
        except Exception as e:
            logger.error(f"连接池健康检查失败: {e}")
            return {
                'healthy': False,
                'error': str(e),
                'health_score': 0
            }

# 全局连接池优化器实例
pool_optimizer = DatabasePoolOptimizer()

def init_database_pool_optimization(app, engine):
    """初始化数据库连接池优化"""
    try:
        # 设置监控
        pool_optimizer.setup_monitoring(engine)
        
        # 记录初始状态
        initial_status = pool_optimizer.get_pool_status(engine)
        logger.info(f"数据库连接池初始化完成: {initial_status}")
        
        return pool_optimizer
        
    except Exception as e:
        logger.error(f"数据库连接池优化初始化失败: {e}")
        return None

def get_pool_optimizer():
    """获取连接池优化器实例"""
    return pool_optimizer