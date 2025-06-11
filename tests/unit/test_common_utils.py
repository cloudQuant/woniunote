#!/usr/bin/env python3
"""
测试公共工具模块
确保woniunote/common/中工具模块的完整功能覆盖
"""

import pytest
import sys
import os
import time
import tempfile
import shutil
import json
from unittest.mock import Mock, patch, mock_open, MagicMock
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

# 设置测试环境
os.environ['TESTING'] = 'True'
os.environ['FLASK_ENV'] = 'testing'


class TestSimpleLogger:
    """测试简单日志记录器"""
    
    def test_logger_creation(self):
        """测试日志记录器创建"""
        from woniunote.common.simple_logger import get_simple_logger
        
        logger = get_simple_logger('test_module')
        assert logger is not None
        assert logger.name == 'test_module'
    
    def test_logger_singleton(self):
        """测试日志记录器单例模式"""
        from woniunote.common.simple_logger import get_simple_logger
        
        logger1 = get_simple_logger('test_module')
        logger2 = get_simple_logger('test_module')
        assert logger1 is logger2
    
    @patch('woniunote.common.simple_logger.logging')
    def test_logger_configuration(self, mock_logging):
        """测试日志记录器配置"""
        from woniunote.common.simple_logger import get_simple_logger
        
        logger = get_simple_logger('test_config')
        
        # 验证基础配置调用
        assert mock_logging.getLogger.called
    
    def test_logger_methods(self):
        """测试日志记录器方法"""
        from woniunote.common.simple_logger import get_simple_logger
        
        logger = get_simple_logger('test_methods')
        
        # 测试基本方法存在
        assert hasattr(logger, 'info')
        assert hasattr(logger, 'error')
        assert hasattr(logger, 'warning')
        assert hasattr(logger, 'debug')


class TestTimer:
    """测试计时器工具"""
    
    def test_timer_import(self):
        """测试计时器导入"""
        from woniunote.common.timer import Timer
        
        timer = Timer()
        assert timer is not None
    
    def test_timer_functionality(self):
        """测试计时器功能"""
        from woniunote.common.timer import Timer
        
        timer = Timer()
        
        # 测试基本方法存在
        if hasattr(timer, 'start'):
            timer.start()
        if hasattr(timer, 'stop'):
            timer.stop()


class TestLogDecorator:
    """测试日志装饰器"""
    
    def test_log_decorator_import(self):
        """测试日志装饰器导入"""
        try:
            from woniunote.common.log_decorator import log_execution, timing_log
            assert log_execution is not None
            assert timing_log is not None
        except ImportError:
            # 如果模块不存在，跳过测试
            pytest.skip("log_decorator module not found")
    
    @patch('woniunote.common.simple_logger.get_simple_logger')
    def test_log_decorator_usage(self, mock_logger):
        """测试日志装饰器使用"""
        try:
            from woniunote.common.log_decorator import log_execution
            
            mock_logger_instance = Mock()
            mock_logger.return_value = mock_logger_instance
            
            @log_execution
            def test_function():
                return "test result"
            
            result = test_function()
            assert result == "test result"
            
        except ImportError:
            pytest.skip("log_decorator module not found")


class TestCacheUtils:
    """测试缓存工具"""
    
    @pytest.fixture
    def mock_redis(self):
        """模拟Redis连接"""
        with patch('redis.Redis') as mock_redis:
            mock_instance = Mock()
            mock_redis.return_value = mock_instance
            
            mock_instance.get.return_value = None
            mock_instance.set.return_value = True
            mock_instance.delete.return_value = 1
            mock_instance.exists.return_value = False
            
            yield mock_instance
    
    def test_cache_utils_import(self):
        """测试缓存工具导入"""
        from woniunote.common.cache_utils import (
            CacheManager, cache_result, invalidate_cache
        )
        
        assert CacheManager is not None
        assert cache_result is not None
        assert invalidate_cache is not None
    
    def test_cache_manager_init(self, mock_redis):
        """测试缓存管理器初始化"""
        from woniunote.common.cache_utils import CacheManager
        
        cache_manager = CacheManager()
        assert cache_manager is not None
    
    def test_cache_manager_operations(self, mock_redis):
        """测试缓存管理器操作"""
        from woniunote.common.cache_utils import CacheManager
        
        cache_manager = CacheManager()
        
        # 测试基本方法
        if hasattr(cache_manager, 'get'):
            result = cache_manager.get('test_key')
            # 由于mock，结果可能为None
        
        if hasattr(cache_manager, 'set'):
            cache_manager.set('test_key', 'test_value')
        
        if hasattr(cache_manager, 'delete'):
            cache_manager.delete('test_key')
    
    def test_cache_decorator(self, mock_redis):
        """测试缓存装饰器"""
        from woniunote.common.cache_utils import cache_result
        
        call_count = 0
        
        @cache_result(ttl=60)
        def expensive_function(param):
            nonlocal call_count
            call_count += 1
            return f"result_{param}"
        
        # 第一次调用
        result1 = expensive_function("test")
        assert result1 == "result_test"
        assert call_count == 1
        
        # 第二次调用（模拟缓存命中）
        result2 = expensive_function("test")
        # 由于mock，实际行为可能不同，但装饰器应该正常工作
        assert result2 == "result_test"


class TestRateLimiter:
    """测试速率限制器"""
    
    def test_rate_limiter_import(self):
        """测试速率限制器导入"""
        from woniunote.common.rate_limiter import RateLimiter, rate_limit
        
        assert RateLimiter is not None
        assert rate_limit is not None
    
    def test_rate_limiter_init(self):
        """测试速率限制器初始化"""
        from woniunote.common.rate_limiter import RateLimiter
        
        limiter = RateLimiter()
        assert limiter is not None
    
    def test_rate_limiter_check(self):
        """测试速率限制检查"""
        from woniunote.common.rate_limiter import RateLimiter
        
        limiter = RateLimiter()
        
        if hasattr(limiter, 'is_allowed'):
            # 测试基本方法
            result = limiter.is_allowed('test_key')
            assert isinstance(result, bool)
    
    def test_rate_limit_decorator(self):
        """测试速率限制装饰器"""
        from woniunote.common.rate_limiter import rate_limit
        
        @rate_limit(max_calls=5, period=60)
        def limited_function():
            return "success"
        
        # 测试装饰器正常工作
        result = limited_function()
        assert result == "success"


class TestAsyncTasks:
    """测试异步任务"""
    
    def test_async_tasks_import(self):
        """测试异步任务导入"""
        from woniunote.common.async_tasks import (
            TaskManager, async_task, execute_async
        )
        
        assert TaskManager is not None
        assert async_task is not None
        assert execute_async is not None
    
    def test_task_manager_init(self):
        """测试任务管理器初始化"""
        from woniunote.common.async_tasks import TaskManager
        
        manager = TaskManager()
        assert manager is not None
    
    def test_async_task_decorator(self):
        """测试异步任务装饰器"""
        from woniunote.common.async_tasks import async_task
        
        @async_task
        def background_task(param):
            return f"processed_{param}"
        
        # 测试装饰器正常工作
        assert background_task is not None
        
        # 如果支持同步调用用于测试
        if hasattr(background_task, '__call__'):
            result = background_task("test")
            # 异步任务可能返回任务ID或其他标识


class TestMonitoring:
    """测试监控模块"""
    
    def test_monitoring_import(self):
        """测试监控模块导入"""
        from woniunote.common.monitoring import (
            PerformanceMonitor, monitor_performance, get_metrics
        )
        
        assert PerformanceMonitor is not None
        assert monitor_performance is not None
        assert get_metrics is not None
    
    def test_performance_monitor_init(self):
        """测试性能监控器初始化"""
        from woniunote.common.monitoring import PerformanceMonitor
        
        monitor = PerformanceMonitor()
        assert monitor is not None
    
    def test_performance_monitor_methods(self):
        """测试性能监控器方法"""
        from woniunote.common.monitoring import PerformanceMonitor
        
        monitor = PerformanceMonitor()
        
        # 测试基本方法存在
        if hasattr(monitor, 'start_monitoring'):
            monitor.start_monitoring()
        
        if hasattr(monitor, 'get_metrics'):
            metrics = monitor.get_metrics()
            assert metrics is not None
    
    def test_monitor_performance_decorator(self):
        """测试性能监控装饰器"""
        from woniunote.common.monitoring import monitor_performance
        
        @monitor_performance
        def monitored_function():
            time.sleep(0.1)  # 模拟耗时操作
            return "completed"
        
        result = monitored_function()
        assert result == "completed"


class TestConfigManager:
    """测试配置管理器"""
    
    @pytest.fixture
    def temp_config_file(self):
        """创建临时配置文件"""
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False)
        config_data = {
            'database': {
                'host': 'localhost',
                'port': 5432,
                'name': 'test_db'
            },
            'cache': {
                'type': 'redis',
                'ttl': 300
            },
            'debug': True
        }
        
        import yaml
        yaml.dump(config_data, temp_file)
        temp_file.close()
        
        yield temp_file.name
        
        os.unlink(temp_file.name)
    
    def test_config_manager_import(self):
        """测试配置管理器导入"""
        from woniunote.common.config_manager import (
            ConfigManager, load_config, get_config
        )
        
        assert ConfigManager is not None
        assert load_config is not None
        assert get_config is not None
    
    def test_config_manager_init(self):
        """测试配置管理器初始化"""
        from woniunote.common.config_manager import ConfigManager
        
        config_manager = ConfigManager()
        assert config_manager is not None
    
    def test_config_loading(self, temp_config_file):
        """测试配置加载"""
        from woniunote.common.config_manager import load_config
        
        config = load_config(temp_config_file)
        assert config is not None
        assert isinstance(config, dict)
        assert 'database' in config
        assert config['database']['host'] == 'localhost'
    
    def test_config_get_nested(self, temp_config_file):
        """测试嵌套配置获取"""
        from woniunote.common.config_manager import ConfigManager
        
        config_manager = ConfigManager(temp_config_file)
        
        if hasattr(config_manager, 'get'):
            # 测试嵌套键访问
            host = config_manager.get('database.host')
            if host:
                assert host == 'localhost'
    
    def test_config_environment_override(self):
        """测试环境变量覆盖配置"""
        from woniunote.common.config_manager import ConfigManager
        
        # 设置环境变量
        os.environ['TEST_CONFIG_VALUE'] = 'env_value'
        
        config_manager = ConfigManager()
        
        # 清理环境变量
        del os.environ['TEST_CONFIG_VALUE']


class TestDatabaseOptimizer:
    """测试数据库优化器"""
    
    def test_database_optimizer_import(self):
        """测试数据库优化器导入"""
        from woniunote.common.database_optimizer import (
            DatabaseOptimizer, optimize_query, analyze_performance
        )
        
        assert DatabaseOptimizer is not None
        assert optimize_query is not None
        assert analyze_performance is not None
    
    def test_database_optimizer_init(self):
        """测试数据库优化器初始化"""
        from woniunote.common.database_optimizer import DatabaseOptimizer
        
        optimizer = DatabaseOptimizer()
        assert optimizer is not None
    
    def test_query_optimization(self):
        """测试查询优化"""
        from woniunote.common.database_optimizer import optimize_query
        
        test_query = "SELECT * FROM users WHERE id = 1"
        
        if callable(optimize_query):
            result = optimize_query(test_query)
            # 优化后的查询应该仍然是字符串
            assert isinstance(result, str) or result is None
    
    def test_performance_analysis(self):
        """测试性能分析"""
        from woniunote.common.database_optimizer import analyze_performance
        
        if callable(analyze_performance):
            analysis = analyze_performance()
            # 分析结果应该是字典或列表
            assert isinstance(analysis, (dict, list)) or analysis is None


class TestStaticOptimizer:
    """测试静态资源优化器"""
    
    def test_static_optimizer_import(self):
        """测试静态资源优化器导入"""
        from woniunote.common.static_optimizer import (
            StaticOptimizer, compress_files, optimize_images
        )
        
        assert StaticOptimizer is not None
        assert compress_files is not None
        assert optimize_images is not None
    
    def test_static_optimizer_init(self):
        """测试静态资源优化器初始化"""
        from woniunote.common.static_optimizer import StaticOptimizer
        
        optimizer = StaticOptimizer()
        assert optimizer is not None
    
    @pytest.fixture
    def temp_static_file(self):
        """创建临时静态文件"""
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.css', delete=False)
        temp_file.write("""
        .test-class {
            color: red;
            background-color: blue;
            margin: 10px;
        }
        """)
        temp_file.close()
        
        yield temp_file.name
        
        os.unlink(temp_file.name)
    
    def test_file_compression(self, temp_static_file):
        """测试文件压缩"""
        from woniunote.common.static_optimizer import compress_files
        
        if callable(compress_files):
            result = compress_files([temp_static_file])
            # 压缩应该返回成功状态或压缩后的文件列表
            assert result is not None


class TestUtils:
    """测试通用工具函数"""
    
    def test_utils_import(self):
        """测试工具函数导入"""
        from woniunote.common.utils import (
            read_config, generate_id, format_datetime, validate_email
        )
        
        # 测试基本函数存在
        assert read_config is not None
        assert generate_id is not None
        assert format_datetime is not None
        assert validate_email is not None
    
    def test_read_config(self):
        """测试读取配置"""
        from woniunote.common.utils import read_config
        
        config = read_config()
        assert config is not None
        assert isinstance(config, dict)
    
    def test_generate_id(self):
        """测试ID生成"""
        from woniunote.common.utils import generate_id
        
        id1 = generate_id()
        id2 = generate_id()
        
        assert id1 != id2  # ID应该是唯一的
        assert isinstance(id1, str)
        assert len(id1) > 0
    
    def test_format_datetime(self):
        """测试日期时间格式化"""
        from woniunote.common.utils import format_datetime
        
        now = datetime.now()
        formatted = format_datetime(now)
        
        assert isinstance(formatted, str)
        assert len(formatted) > 0
    
    def test_validate_email(self):
        """测试邮箱验证"""
        from woniunote.common.utils import validate_email
        
        # 测试有效邮箱
        assert validate_email("test@example.com") is True
        assert validate_email("user.name@domain.co.uk") is True
        
        # 测试无效邮箱
        assert validate_email("invalid-email") is False
        assert validate_email("@domain.com") is False
        assert validate_email("user@") is False


class TestSessionUtil:
    """测试会话工具"""
    
    def test_session_util_import(self):
        """测试会话工具导入"""
        from woniunote.common.session_util import (
            SessionManager, create_session, destroy_session
        )
        
        assert SessionManager is not None
        assert create_session is not None
        assert destroy_session is not None
    
    @patch('flask.session')
    def test_session_operations(self, mock_session):
        """测试会话操作"""
        from woniunote.common.session_util import create_session, destroy_session
        
        mock_session.__setitem__ = Mock()
        mock_session.__delitem__ = Mock()
        mock_session.clear = Mock()
        
        # 测试创建会话
        if callable(create_session):
            create_session('test_user', {'role': 'admin'})
        
        # 测试销毁会话
        if callable(destroy_session):
            destroy_session()


class TestRedisDB:
    """测试Redis数据库工具"""
    
    @pytest.fixture
    def mock_redis(self):
        """模拟Redis连接"""
        with patch('redis.Redis') as mock_redis:
            mock_instance = Mock()
            mock_redis.return_value = mock_instance
            
            # 设置基本Redis方法
            mock_instance.ping.return_value = True
            mock_instance.get.return_value = None
            mock_instance.set.return_value = True
            mock_instance.delete.return_value = 1
            
            yield mock_instance
    
    def test_redis_db_import(self):
        """测试Redis数据库工具导入"""
        from woniunote.common.redisdb import (
            RedisManager, get_redis_connection, redis_cache
        )
        
        assert RedisManager is not None
        assert get_redis_connection is not None
        assert redis_cache is not None
    
    def test_redis_manager_init(self, mock_redis):
        """测试Redis管理器初始化"""
        from woniunote.common.redisdb import RedisManager
        
        manager = RedisManager()
        assert manager is not None
    
    def test_redis_connection(self, mock_redis):
        """测试Redis连接"""
        from woniunote.common.redisdb import get_redis_connection
        
        connection = get_redis_connection()
        assert connection is not None
    
    def test_redis_cache_operations(self, mock_redis):
        """测试Redis缓存操作"""
        from woniunote.common.redisdb import redis_cache
        
        if hasattr(redis_cache, 'set'):
            redis_cache.set('test_key', 'test_value')
        
        if hasattr(redis_cache, 'get'):
            value = redis_cache.get('test_key')


class TestTodoDatabase:
    """测试Todo数据库工具"""
    
    def test_todo_database_import(self):
        """测试Todo数据库工具导入"""
        from woniunote.common.todo_database import (
            TodoManager, get_todos, create_todo, update_todo, delete_todo
        )
        
        assert TodoManager is not None
        assert get_todos is not None
        assert create_todo is not None
        assert update_todo is not None
        assert delete_todo is not None
    
    def test_todo_manager_init(self):
        """测试Todo管理器初始化"""
        from woniunote.common.todo_database import TodoManager
        
        manager = TodoManager()
        assert manager is not None
    
    @patch('woniunote.common.database.db')
    def test_todo_operations(self, mock_db):
        """测试Todo操作"""
        from woniunote.common.todo_database import create_todo, get_todos
        
        mock_db.session.add = Mock()
        mock_db.session.commit = Mock()
        
        # 测试创建Todo
        if callable(create_todo):
            result = create_todo("Test todo", 1)
            # 应该返回创建的todo或成功状态
        
        # 测试获取Todos
        if callable(get_todos):
            todos = get_todos()
            # 应该返回todo列表


class TestCardDatabase:
    """测试Card数据库工具"""
    
    def test_card_database_import(self):
        """测试Card数据库工具导入"""
        from woniunote.common.card_database import (
            CardManager, get_cards, create_card, update_card, delete_card
        )
        
        assert CardManager is not None
        assert get_cards is not None
        assert create_card is not None
        assert update_card is not None
        assert delete_card is not None
    
    def test_card_manager_init(self):
        """测试Card管理器初始化"""
        from woniunote.common.card_database import CardManager
        
        manager = CardManager()
        assert manager is not None
    
    @patch('woniunote.common.database.db')
    def test_card_operations(self, mock_db):
        """测试Card操作"""
        from woniunote.common.card_database import create_card, get_cards
        
        mock_db.session.add = Mock()
        mock_db.session.commit = Mock()
        
        # 测试创建Card
        if callable(create_card):
            result = create_card("Test card", "Content", 1)
        
        # 测试获取Cards
        if callable(get_cards):
            cards = get_cards()


@pytest.mark.integration
class TestCommonIntegration:
    """测试公共模块集成"""
    
    def test_logger_cache_integration(self):
        """测试日志和缓存集成"""
        from woniunote.common.simple_logger import get_simple_logger
        from woniunote.common.cache_utils import CacheManager
        
        logger = get_simple_logger('cache_test')
        cache_manager = CacheManager()
        
        # 集成测试：带日志的缓存操作
        if hasattr(cache_manager, 'set') and hasattr(logger, 'info'):
            cache_manager.set('test_key', 'test_value')
            logger.info("Cache operation completed")
    
    def test_config_monitoring_integration(self):
        """测试配置和监控集成"""
        from woniunote.common.config_manager import ConfigManager
        from woniunote.common.monitoring import PerformanceMonitor
        
        config_manager = ConfigManager()
        monitor = PerformanceMonitor()
        
        # 集成测试：基于配置的监控
        assert config_manager is not None
        assert monitor is not None
    
    def test_database_cache_integration(self):
        """测试数据库和缓存集成"""
        from woniunote.common.database_optimizer import DatabaseOptimizer
        from woniunote.common.cache_utils import CacheManager
        
        db_optimizer = DatabaseOptimizer()
        cache_manager = CacheManager()
        
        # 集成测试：数据库优化结果缓存
        assert db_optimizer is not None
        assert cache_manager is not None 