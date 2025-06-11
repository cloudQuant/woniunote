#!/usr/bin/env python3
"""
测试高级数据库优化模块
确保QueryCache、SlowQueryAnalyzer、IndexOptimizer等组件的完整功能覆盖
"""

import pytest
import time
import hashlib
import threading
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from collections import deque

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from woniunote.common.database_advanced_optimizer import (
    QueryCache, SlowQueryAnalyzer, IndexOptimizer, ConnectionPoolManager,
    DatabaseAdvancedOptimizer, QueryAnalysis, IndexSuggestion,
    get_database_optimizer, init_database_advanced_optimization, cached_query
)


class TestQueryCache:
    """测试查询缓存类"""
    
    def test_init(self):
        """测试初始化"""
        cache = QueryCache(max_size=100, ttl=60)
        assert cache.max_size == 100
        assert cache.ttl == 60
        assert cache.hit_count == 0
        assert cache.miss_count == 0
        
    def test_generate_cache_key(self):
        """测试缓存键生成"""
        cache = QueryCache()
        
        # 测试基本查询
        key1 = cache._generate_cache_key("SELECT * FROM users")
        key2 = cache._generate_cache_key("SELECT * FROM users")
        assert key1 == key2
        
        # 测试带参数的查询
        key3 = cache._generate_cache_key("SELECT * FROM users WHERE id = %s", (1,))
        key4 = cache._generate_cache_key("SELECT * FROM users WHERE id = %s", (2,))
        assert key3 != key4
        
        # 测试查询标准化
        key5 = cache._generate_cache_key("select * from users")
        key6 = cache._generate_cache_key("SELECT * FROM USERS")
        assert key5 == key6
    
    def test_set_and_get(self):
        """测试设置和获取缓存"""
        cache = QueryCache(max_size=5, ttl=1)
        
        # 测试设置和获取
        cache.set("SELECT 1", "result1")
        result = cache.get("SELECT 1")
        assert result == "result1"
        assert cache.hit_count == 1
        
        # 测试缓存未命中
        result = cache.get("SELECT 2")
        assert result is None
        assert cache.miss_count == 1
    
    def test_ttl_expiration(self):
        """测试TTL过期"""
        cache = QueryCache(max_size=5, ttl=1)
        
        cache.set("SELECT 1", "result1")
        assert cache.get("SELECT 1") == "result1"
        
        # 等待过期
        time.sleep(1.1)
        cache._evict_expired()
        
        result = cache.get("SELECT 1")
        assert result is None
    
    def test_lru_eviction(self):
        """测试LRU淘汰"""
        cache = QueryCache(max_size=2, ttl=60)
        
        # 填满缓存
        cache.set("SELECT 1", "result1")
        cache.set("SELECT 2", "result2")
        
        # 访问第一个缓存项
        cache.get("SELECT 1")
        
        # 添加第三个项，应该淘汰SELECT 2
        cache.set("SELECT 3", "result3")
        
        assert cache.get("SELECT 1") == "result1"
        assert cache.get("SELECT 2") is None
        assert cache.get("SELECT 3") == "result3"
    
    def test_invalidate_table(self):
        """测试表级缓存失效"""
        cache = QueryCache()
        
        cache.set("SELECT * FROM users", "result1")
        cache.set("SELECT * FROM posts", "result2")
        
        # 使users表相关缓存失效
        cache.invalidate_table("users")
        
        # users相关查询应该失效，posts相关查询应该保留
        assert cache.get("SELECT * FROM users") is None
        assert cache.get("SELECT * FROM posts") == "result2"
    
    def test_clear(self):
        """测试清空缓存"""
        cache = QueryCache()
        
        cache.set("SELECT 1", "result1")
        cache.set("SELECT 2", "result2")
        
        cache.clear()
        
        assert cache.get("SELECT 1") is None
        assert cache.get("SELECT 2") is None
        assert cache.cache == {}
        assert cache.access_times == {}
    
    def test_get_stats(self):
        """测试获取统计信息"""
        cache = QueryCache()
        
        cache.set("SELECT 1", "result1")
        cache.get("SELECT 1")  # 命中
        cache.get("SELECT 2")  # 未命中
        
        stats = cache.get_stats()
        
        assert stats['hit_count'] == 1
        assert stats['miss_count'] == 1
        assert stats['hit_rate'] == 0.5
        assert stats['cache_size'] == 1
    
    def test_thread_safety(self):
        """测试线程安全"""
        cache = QueryCache()
        
        def worker(thread_id):
            for i in range(10):
                cache.set(f"SELECT {thread_id}_{i}", f"result_{thread_id}_{i}")
                cache.get(f"SELECT {thread_id}_{i}")
        
        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # 检查数据一致性
        stats = cache.get_stats()
        assert stats['hit_count'] == 50  # 5 threads * 10 hits each


class TestSlowQueryAnalyzer:
    """测试慢查询分析器"""
    
    def test_init(self):
        """测试初始化"""
        analyzer = SlowQueryAnalyzer(slow_threshold=2.0)
        assert analyzer.slow_threshold == 2.0
        assert len(analyzer.slow_queries) == 0
        assert len(analyzer.query_patterns) == 0
    
    def test_analyze_query_normal(self):
        """测试分析正常查询"""
        analyzer = SlowQueryAnalyzer(slow_threshold=1.0)
        
        analysis = analyzer.analyze_query("SELECT * FROM users", 0.5)
        
        assert analysis.execution_time == 0.5
        assert analysis.query_text == "SELECT * FROM users"
        assert len(analyzer.slow_queries) == 0  # 不是慢查询
    
    def test_analyze_query_slow(self):
        """测试分析慢查询"""
        analyzer = SlowQueryAnalyzer(slow_threshold=1.0)
        
        analysis = analyzer.analyze_query("SELECT * FROM users", 2.0)
        
        assert analysis.execution_time == 2.0
        assert len(analyzer.slow_queries) == 1  # 是慢查询
        
        slow_query = analyzer.slow_queries[0]
        assert slow_query['execution_time'] == 2.0
        assert slow_query['query'] == "SELECT * FROM users"
    
    def test_extract_tables(self):
        """测试提取表名"""
        analyzer = SlowQueryAnalyzer()
        
        # 测试FROM子句
        tables = analyzer._extract_tables("SELECT * FROM users")
        assert 'users' in tables
        
        # 测试JOIN子句
        tables = analyzer._extract_tables("SELECT * FROM users JOIN posts ON users.id = posts.user_id")
        assert 'users' in tables
        assert 'posts' in tables
        
        # 测试UPDATE语句
        tables = analyzer._extract_tables("UPDATE users SET name = 'test'")
        assert 'users' in tables
    
    def test_generate_optimization_suggestions(self):
        """测试生成优化建议"""
        analyzer = SlowQueryAnalyzer()
        
        # 测试WHERE子句建议
        suggestions = analyzer._generate_optimization_suggestions("SELECT * FROM users WHERE id = 1", 0.6)
        assert any("索引" in suggestion for suggestion in suggestions)
        
        # 测试SELECT *建议
        suggestions = analyzer._generate_optimization_suggestions("SELECT * FROM users", 0.1)
        assert any("SELECT *" in suggestion for suggestion in suggestions)
        
        # 测试JOIN建议
        suggestions = analyzer._generate_optimization_suggestions("SELECT * FROM users JOIN posts", 1.5)
        assert any("JOIN" in suggestion for suggestion in suggestions)
        
        # 测试ORDER BY建议
        suggestions = analyzer._generate_optimization_suggestions("SELECT * FROM users ORDER BY name", 0.9)
        assert any("ORDER BY" in suggestion for suggestion in suggestions)
    
    def test_get_slow_queries(self):
        """测试获取慢查询列表"""
        analyzer = SlowQueryAnalyzer(slow_threshold=1.0)
        
        # 添加几个慢查询
        analyzer.analyze_query("SELECT 1", 2.0)
        analyzer.analyze_query("SELECT 2", 3.0)
        analyzer.analyze_query("SELECT 3", 1.5)
        
        slow_queries = analyzer.get_slow_queries(limit=2)
        assert len(slow_queries) == 2
        
        # 检查顺序（最新的在后面）
        assert slow_queries[-1]['query'] == "SELECT 3"
    
    def test_get_query_patterns(self):
        """测试获取查询模式统计"""
        analyzer = SlowQueryAnalyzer(slow_threshold=1.0)
        
        # 分析多个查询
        analyzer.analyze_query("SELECT * FROM users", 0.5)
        analyzer.analyze_query("SELECT * FROM users WHERE id = 1", 2.0)
        analyzer.analyze_query("SELECT * FROM posts", 0.3)
        
        patterns = analyzer.get_query_patterns()
        
        assert len(patterns) > 0
        for pattern, stats in patterns.items():
            assert 'count' in stats
            assert 'avg_execution_time' in stats
            assert 'max_execution_time' in stats
            assert 'is_slow' in stats


class TestIndexOptimizer:
    """测试索引优化器"""
    
    def test_init(self):
        """测试初始化"""
        optimizer = IndexOptimizer()
        assert len(optimizer.query_analysis) == 0
        assert len(optimizer.table_access_patterns) == 0
        assert len(optimizer.column_usage) == 0
    
    def test_record_query_access(self):
        """测试记录查询访问"""
        optimizer = IndexOptimizer()
        
        optimizer.record_query_access("SELECT * FROM users WHERE id = 1", 0.5)
        
        assert len(optimizer.query_analysis) > 0
        assert optimizer.table_access_patterns['users'] == 1
        assert optimizer.column_usage['id'] == 1
    
    def test_extract_query_columns(self):
        """测试提取查询列"""
        optimizer = IndexOptimizer()
        
        # 测试WHERE条件中的列
        columns = optimizer._extract_query_columns("SELECT * FROM users WHERE id = 1 AND name = 'test'")
        assert 'id' in columns
        assert 'name' in columns
        
        # 测试ORDER BY中的列
        columns = optimizer._extract_query_columns("SELECT * FROM users ORDER BY created_at")
        assert 'created_at' in columns
        
        # 测试GROUP BY中的列
        columns = optimizer._extract_query_columns("SELECT count(*) FROM users GROUP BY status")
        assert 'status' in columns
    
    def test_extract_tables_from_query(self):
        """测试从查询中提取表名"""
        optimizer = IndexOptimizer()
        
        tables = optimizer._extract_tables_from_query("SELECT * FROM users")
        assert 'users' in tables
        
        tables = optimizer._extract_tables_from_query("UPDATE posts SET title = 'test'")
        assert 'posts' in tables
    
    def test_suggest_indexes(self):
        """测试索引建议"""
        optimizer = IndexOptimizer()
        
        # 记录一些查询访问
        for i in range(10):
            optimizer.record_query_access(f"SELECT * FROM users WHERE id = {i}", 0.5)
            optimizer.record_query_access(f"SELECT * FROM users WHERE name = 'user{i}'", 0.3)
        
        suggestions = optimizer.suggest_indexes()
        
        assert len(suggestions) > 0
        for suggestion in suggestions:
            assert isinstance(suggestion, IndexSuggestion)
            assert suggestion.usage_frequency >= 5  # 阈值检查
            assert suggestion.estimated_benefit > 0


class TestConnectionPoolManager:
    """测试连接池管理器"""
    
    def test_init(self):
        """测试初始化"""
        mock_engine = Mock()
        manager = ConnectionPoolManager(mock_engine)
        
        assert manager.engine == mock_engine
        assert len(manager.pool_stats) == 0
        assert len(manager.connection_metrics) == 0
    
    @patch('woniunote.common.database_advanced_optimizer.event')
    def test_setup_pool_monitoring(self, mock_event):
        """测试设置连接池监控"""
        mock_engine = Mock()
        manager = ConnectionPoolManager(mock_engine)
        
        # 验证事件监听器注册
        assert mock_event.listens_for.call_count >= 3  # connect, checkout, checkin
    
    def test_get_pool_status(self):
        """测试获取连接池状态"""
        mock_engine = Mock()
        mock_pool = Mock()
        mock_pool.size.return_value = 10
        mock_pool.checkedout.return_value = 5
        mock_pool.overflow.return_value = 2
        mock_pool.invalidated.return_value = 0
        mock_pool.__class__.__name__ = "QueuePool"
        mock_pool._timeout = 30
        mock_pool._max_overflow = 10
        mock_pool._pre_ping = True
        
        mock_engine.pool = mock_pool
        
        manager = ConnectionPoolManager(mock_engine)
        status = manager.get_pool_status()
        
        assert status['size'] == 10
        assert status['checked_out'] == 5
        assert status['overflow'] == 2
        assert status['pool_class'] == "QueuePool"
        assert status['timeout'] == 30
    
    def test_get_connection_history(self):
        """测试获取连接历史"""
        mock_engine = Mock()
        manager = ConnectionPoolManager(mock_engine)
        
        # 添加一些连接指标
        current_time = time.time()
        manager.connection_metrics.append({
            'event': 'connect',
            'timestamp': current_time,
            'connection_id': 1
        })
        manager.connection_metrics.append({
            'event': 'checkout',
            'timestamp': current_time - 3600,  # 1小时前
            'connection_id': 1
        })
        
        # 获取最近30分钟的历史
        history = manager.get_connection_history(minutes=30)
        assert len(history) == 1  # 只有一个在时间范围内
        assert history[0]['event'] == 'connect'
    
    def test_analyze_connection_patterns(self):
        """测试分析连接模式"""
        mock_engine = Mock()
        manager = ConnectionPoolManager(mock_engine)
        
        # 添加连接事件
        current_time = time.time()
        manager.connection_metrics.extend([
            {'event': 'checkout', 'timestamp': current_time, 'connection_id': 1},
            {'event': 'checkin', 'timestamp': current_time + 10, 'connection_id': 1},
            {'event': 'connect', 'timestamp': current_time, 'connection_id': 2}
        ])
        
        patterns = manager.analyze_connection_patterns()
        
        assert 'event_counts' in patterns
        assert 'avg_connection_lifetime' in patterns
        assert 'active_connections' in patterns
        assert patterns['event_counts']['checkout'] == 1
        assert patterns['event_counts']['checkin'] == 1


class TestDatabaseAdvancedOptimizer:
    """测试高级数据库优化器主类"""
    
    def test_init(self):
        """测试初始化"""
        optimizer = DatabaseAdvancedOptimizer(slow_query_threshold=2.0)
        
        assert optimizer.slow_query_analyzer.slow_threshold == 2.0
        assert isinstance(optimizer.query_cache, QueryCache)
        assert isinstance(optimizer.index_optimizer, IndexOptimizer)
        assert optimizer.connection_pool_manager is None  # 需要app初始化
    
    @patch('woniunote.common.database_advanced_optimizer.SQLAlchemy')
    @patch('woniunote.common.database_advanced_optimizer.event')
    def test_init_app(self, mock_event, mock_sqlalchemy):
        """测试Flask应用初始化"""
        mock_app = Mock()
        mock_db = Mock()
        mock_engine = Mock()
        mock_db.get_engine.return_value = mock_engine
        mock_sqlalchemy.return_value = mock_db
        
        optimizer = DatabaseAdvancedOptimizer()
        optimizer.init_app(mock_app)
        
        assert optimizer.app == mock_app
        assert optimizer.connection_pool_manager is not None
    
    def test_cached_query_context_manager(self):
        """测试缓存查询上下文管理器"""
        optimizer = DatabaseAdvancedOptimizer()
        
        # 模拟缓存未命中
        with optimizer.cached_query("SELECT 1") as result:
            assert result is None
        
        # 设置缓存
        optimizer.query_cache.set("SELECT 1", "cached_result")
        
        # 模拟缓存命中
        with optimizer.cached_query("SELECT 1") as result:
            assert result == "cached_result"
    
    def test_invalidate_table_cache(self):
        """测试使表缓存失效"""
        optimizer = DatabaseAdvancedOptimizer()
        
        optimizer.query_cache.set("SELECT * FROM users", "result")
        optimizer.invalidate_table_cache("users")
        
        result = optimizer.query_cache.get("SELECT * FROM users")
        assert result is None
    
    def test_get_optimization_report(self):
        """测试获取优化报告"""
        optimizer = DatabaseAdvancedOptimizer()
        
        # 添加一些测试数据
        optimizer.slow_query_analyzer.analyze_query("SELECT 1", 2.0)
        optimizer.index_optimizer.record_query_access("SELECT * FROM users WHERE id = 1", 0.5)
        
        report = optimizer.get_optimization_report()
        
        assert 'timestamp' in report
        assert 'cache_stats' in report
        assert 'slow_queries' in report
        assert 'query_patterns' in report
        assert 'index_suggestions' in report
        assert 'optimization_stats' in report
    
    def test_apply_automatic_optimizations(self):
        """测试应用自动优化"""
        optimizer = DatabaseAdvancedOptimizer()
        
        # 填充一些缓存
        optimizer.query_cache.set("SELECT 1", "result1")
        optimizer.query_cache.set("SELECT 2", "result2")
        
        optimizations = optimizer.apply_automatic_optimizations()
        
        assert isinstance(optimizations, list)
        assert optimizer.optimization_stats['optimizations_applied'] > 0


class TestGlobalFunctions:
    """测试全局函数"""
    
    def test_get_database_optimizer(self):
        """测试获取数据库优化器实例"""
        optimizer1 = get_database_optimizer()
        optimizer2 = get_database_optimizer()
        
        # 应该返回同一个实例（单例模式）
        assert optimizer1 is optimizer2
        assert isinstance(optimizer1, DatabaseAdvancedOptimizer)
    
    @patch('woniunote.common.database_advanced_optimizer.get_database_optimizer')
    def test_init_database_advanced_optimization(self, mock_get_optimizer):
        """测试初始化高级数据库优化"""
        mock_app = Mock()
        mock_optimizer = Mock()
        mock_get_optimizer.return_value = mock_optimizer
        
        result = init_database_advanced_optimization(mock_app, slow_query_threshold=1.5)
        
        assert result == mock_optimizer
        mock_optimizer.init_app.assert_called_once_with(mock_app)
        assert mock_optimizer.slow_query_analyzer.slow_threshold == 1.5
    
    def test_cached_query_decorator(self):
        """测试查询缓存装饰器"""
        call_count = 0
        
        @cached_query(ttl=300)
        def test_function(arg1, arg2):
            nonlocal call_count
            call_count += 1
            return f"result_{arg1}_{arg2}"
        
        # 第一次调用
        result1 = test_function("a", "b")
        assert result1 == "result_a_b"
        assert call_count == 1
        
        # 第二次调用（应该从缓存获取）
        result2 = test_function("a", "b")
        assert result2 == "result_a_b"
        assert call_count == 1  # 没有增加，说明使用了缓存
        
        # 不同参数的调用
        result3 = test_function("c", "d")
        assert result3 == "result_c_d"
        assert call_count == 2


class TestQueryAnalysisDataClass:
    """测试QueryAnalysis数据类"""
    
    def test_query_analysis_creation(self):
        """测试QueryAnalysis创建"""
        analysis = QueryAnalysis(
            query_hash="abc123",
            query_text="SELECT 1",
            execution_time=1.5,
            execution_count=1,
            avg_execution_time=1.5,
            max_execution_time=1.5,
            min_execution_time=1.5,
            last_execution=datetime.now(),
            tables_accessed=["users"],
            index_usage={},
            optimization_suggestions=["Add index"]
        )
        
        assert analysis.query_hash == "abc123"
        assert analysis.query_text == "SELECT 1"
        assert analysis.execution_time == 1.5
        assert "users" in analysis.tables_accessed
        assert "Add index" in analysis.optimization_suggestions


class TestIndexSuggestionDataClass:
    """测试IndexSuggestion数据类"""
    
    def test_index_suggestion_creation(self):
        """测试IndexSuggestion创建"""
        suggestion = IndexSuggestion(
            table_name="users",
            columns=["id", "name"],
            index_type="composite",
            estimated_benefit=0.8,
            usage_frequency=10,
            reasoning="High usage columns"
        )
        
        assert suggestion.table_name == "users"
        assert suggestion.columns == ["id", "name"]
        assert suggestion.index_type == "composite"
        assert suggestion.estimated_benefit == 0.8
        assert suggestion.usage_frequency == 10
        assert suggestion.reasoning == "High usage columns"


@pytest.mark.unit
class TestEdgeCases:
    """测试边界情况和错误处理"""
    
    def test_query_cache_empty_query(self):
        """测试空查询处理"""
        cache = QueryCache()
        
        cache.set("", "empty_result")
        result = cache.get("")
        assert result == "empty_result"
    
    def test_slow_query_analyzer_empty_query(self):
        """测试慢查询分析器处理空查询"""
        analyzer = SlowQueryAnalyzer()
        
        analysis = analyzer.analyze_query("", 1.0)
        assert analysis.query_text == ""
        assert analysis.tables_accessed == []
    
    def test_index_optimizer_malformed_sql(self):
        """测试索引优化器处理格式错误的SQL"""
        optimizer = IndexOptimizer()
        
        # 不应该抛出异常
        optimizer.record_query_access("INVALID SQL STATEMENT", 1.0)
        
        # 应该仍能生成建议（即使为空）
        suggestions = optimizer.suggest_indexes()
        assert isinstance(suggestions, list)
    
    def test_connection_pool_manager_error_handling(self):
        """测试连接池管理器错误处理"""
        mock_engine = Mock()
        mock_engine.pool.side_effect = Exception("Pool error")
        
        manager = ConnectionPoolManager(mock_engine)
        
        # 应该返回空字典而不是抛出异常
        status = manager.get_pool_status()
        assert status == {}


@pytest.mark.integration
class TestIntegrationScenarios:
    """测试集成场景"""
    
    def test_full_optimization_workflow(self):
        """测试完整的优化工作流"""
        optimizer = DatabaseAdvancedOptimizer(slow_query_threshold=1.0)
        
        # 1. 模拟查询执行
        queries = [
            ("SELECT * FROM users WHERE id = 1", 0.5),
            ("SELECT * FROM users WHERE name = 'test'", 2.0),  # 慢查询
            ("SELECT * FROM posts WHERE user_id = 1", 0.3),
            ("SELECT * FROM users WHERE id = 2", 0.4),
        ]
        
        for query, execution_time in queries:
            optimizer.slow_query_analyzer.analyze_query(query, execution_time)
            optimizer.index_optimizer.record_query_access(query, execution_time)
        
        # 2. 获取优化报告
        report = optimizer.get_optimization_report()
        
        assert len(report['slow_queries']) == 1
        assert report['slow_queries'][0]['query'] == "SELECT * FROM users WHERE name = 'test'"
        
        # 3. 应用自动优化
        optimizations = optimizer.apply_automatic_optimizations()
        assert isinstance(optimizations, list)
        
        # 4. 检查索引建议
        suggestions = optimizer.index_optimizer.suggest_indexes()
        assert isinstance(suggestions, list)
    
    def test_concurrent_operations(self):
        """测试并发操作"""
        optimizer = DatabaseAdvancedOptimizer()
        
        def worker(thread_id):
            for i in range(10):
                query = f"SELECT * FROM table_{thread_id} WHERE id = {i}"
                optimizer.slow_query_analyzer.analyze_query(query, 0.5)
                optimizer.index_optimizer.record_query_access(query, 0.5)
                optimizer.query_cache.set(query, f"result_{thread_id}_{i}")
                optimizer.query_cache.get(query)
        
        threads = []
        for i in range(3):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # 验证数据一致性
        report = optimizer.get_optimization_report()
        assert len(report['query_patterns']) > 0
        assert report['cache_stats']['hit_count'] == 30  # 3 threads * 10 hits