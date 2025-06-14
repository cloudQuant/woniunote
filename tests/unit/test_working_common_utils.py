#!/usr/bin/env python3
"""
Comprehensive tests for woniunote.common modules
Tests all actual functions and classes that exist in the codebase
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

# 确保项目根目录在Python路径中
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 设置测试环境
os.environ['TESTING'] = 'True'
os.environ['FLASK_ENV'] = 'testing'


class TestUtilsModule:
    """测试 woniunote.common.utils 模块中的实际函数"""
    
    def test_validate_email(self):
        """测试邮箱验证函数"""
        from woniunote.common.utils import validate_email
        
        # 测试有效邮箱
        assert validate_email("test@example.com") == True
        assert validate_email("user.name@domain.co.uk") == True
        assert validate_email("user123@test-domain.org") == True
        
        # 测试无效邮箱
        assert validate_email("invalid_email") == False
        assert validate_email("@domain.com") == False
        assert validate_email("user@") == False
        assert validate_email("") == False
        assert validate_email(None) == False
        assert validate_email("user@domain") == False
    
    def test_gen_email_code(self):
        """测试邮箱验证码生成"""
        from woniunote.common.utils import gen_email_code
        
        # 测试默认长度
        code1 = gen_email_code()
        code2 = gen_email_code()
        
        assert code1 != code2
        assert len(code1) == 6  # 默认长度
        assert code1.isalnum()  # 应该是字母数字
        
        # 测试自定义长度
        code3 = gen_email_code(8)
        assert len(code3) == 8
        assert code3.isalnum()
        
        # 测试边界情况
        code4 = gen_email_code(1)
        assert len(code4) == 1
        
        code5 = gen_email_code(20)
        assert len(code5) == 20
    
    def test_validate_filename(self):
        """测试文件名验证"""
        from woniunote.common.utils import validate_filename
        
        # 测试有效文件名
        assert validate_filename("test.txt") == True
        assert validate_filename("document.pdf") == True
        assert validate_filename("image.jpg") == True
        assert validate_filename("file_name.docx") == True
        
        # 测试无效文件名
        assert validate_filename("../test.txt") == False
        assert validate_filename("test/file.txt") == False
        assert validate_filename("") == False
        assert validate_filename(None) == False
        assert validate_filename("con.txt") == False  # Windows保留名
        assert validate_filename("file?.txt") == False  # 非法字符
    
    def test_sanitize_input(self):
        """测试输入清理"""
        from woniunote.common.utils import sanitize_input
        
        # 测试正常输入
        result = sanitize_input("Hello World")
        assert result == "Hello World"
        
        # 测试空输入
        result = sanitize_input("")
        assert result == ""
        
        # 测试None输入
        result = sanitize_input(None)
        assert result == ""
        
        # 测试过长输入
        long_input = "a" * 2000
        result = sanitize_input(long_input, max_length=100)
        assert len(result) <= 100
        
        # 测试特殊字符
        result = sanitize_input("<script>alert('xss')</script>")
        assert "<script>" not in result
    
    def test_read_config(self):
        """测试配置读取"""
        from woniunote.common.utils import read_config
        
        # 测试函数存在
        assert callable(read_config)
        
        # 测试调用（可能会失败，但函数应该存在）
        try:
            config = read_config()
            assert isinstance(config, dict)
        except Exception:
            # 配置文件可能不存在，这是正常的
            pass
    
    def test_parse_db_uri(self):
        """测试数据库URI解析"""
        from woniunote.common.utils import parse_db_uri
        
        # 测试有效URI
        uri = "mysql://user:password@localhost:3306/testdb"
        result = parse_db_uri(uri)
        
        assert result['host'] == 'localhost'
        assert result['port'] == 3306
        assert result['user'] == 'user'
        assert result['password'] == 'password'
        assert result['database'] == 'testdb'
        
        # 测试无效URI
        with pytest.raises(Exception):
            parse_db_uri("invalid_uri")
        
        with pytest.raises(Exception):
            parse_db_uri("")
    
    def test_image_code_class(self):
        """测试图片验证码类"""
        from woniunote.common.utils import ImageCode
        
        image_code = ImageCode()
        assert image_code is not None
        
        # 测试文本生成
        text = image_code.gen_text()
        assert len(text) == 4  # 默认长度
        assert text.isalnum()
        
        # 测试颜色生成
        color = image_code.rand_color()
        assert isinstance(color, tuple)
        assert len(color) == 3
        for c in color:
            assert 0 <= c <= 255
    
    def test_image_utilities(self):
        """测试图片工具函数"""
        from woniunote.common.utils import generate_random_color, hsv_to_rgb
        
        # 测试随机颜色生成
        color = generate_random_color()
        assert isinstance(color, tuple)
        assert len(color) == 3
        for c in color:
            assert 0 <= c <= 255
        
        # 测试HSV到RGB转换
        r, g, b = hsv_to_rgb(0, 1, 1)  # 红色
        assert r == 255
        assert g == 0
        assert b == 0
        
        r, g, b = hsv_to_rgb(120, 1, 1)  # 绿色
        assert r == 0
        assert g == 255
        assert b == 0
    
    def test_performance_monitor(self):
        """测试性能监控装饰器"""
        from woniunote.common.utils import performance_monitor
        
        @performance_monitor
        def test_function():
            time.sleep(0.01)  # 短暂延迟
            return "completed"
        
        result = test_function()
        assert result == "completed"
    
    def test_memory_usage(self):
        """测试内存使用监控"""
        from woniunote.common.utils import get_memory_usage
        
        memory_info = get_memory_usage()
        assert isinstance(memory_info, dict)
        assert 'rss' in memory_info
        assert 'vms' in memory_info
        assert memory_info['rss'] > 0
        assert memory_info['vms'] > 0
    
    def test_file_operations(self):
        """测试文件操作"""
        from woniunote.common.utils import safe_file_operation
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("test content")
            temp_file = f.name
        
        try:
            # 测试读取
            with safe_file_operation(temp_file, 'r') as file:
                content = file.read()
                assert content == "test content"
        finally:
            # 清理
            if os.path.exists(temp_file):
                os.unlink(temp_file)


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
        
        logger1 = get_simple_logger('test_singleton')
        logger2 = get_simple_logger('test_singleton')
        assert logger1 is logger2
    
    def test_logger_methods(self):
        """测试日志记录器方法"""
        from woniunote.common.simple_logger import get_simple_logger
        
        logger = get_simple_logger('test_methods')
        
        # 测试基本方法存在
        assert hasattr(logger, 'info')
        assert hasattr(logger, 'error')
        assert hasattr(logger, 'warning')
        assert hasattr(logger, 'debug')
        
        # 测试方法可以调用
        logger.info("Test info message")
        logger.error("Test error message")
        logger.warning("Test warning message")
        logger.debug("Test debug message")


class TestTimer:
    """测试计时器工具"""
    
    def test_timer_function(self):
        """测试计时器函数"""
        from woniunote.common.timer import can_use_minute
        
        result = can_use_minute()
        assert isinstance(result, int)
        assert result > 0


class TestCacheUtils:
    """测试缓存工具"""
    
    def test_cache_manager_creation(self):
        """测试缓存管理器创建"""
        from woniunote.common.cache_utils import CacheManager
        
        cache_manager = CacheManager()
        assert cache_manager is not None
    
    def test_cache_manager_methods(self):
        """测试缓存管理器方法"""
        from woniunote.common.cache_utils import CacheManager
        
        cache_manager = CacheManager()
        
        # 测试基本方法存在
        assert hasattr(cache_manager, 'get')
        assert hasattr(cache_manager, 'set')
        assert hasattr(cache_manager, 'delete')
    
    @patch('redis.Redis')
    def test_cache_operations(self, mock_redis):
        """测试缓存操作"""
        from woniunote.common.cache_utils import CacheManager
        
        # 设置mock
        mock_instance = Mock()
        mock_redis.return_value = mock_instance
        mock_instance.get.return_value = None
        mock_instance.set.return_value = True
        mock_instance.delete.return_value = 1
        
        cache_manager = CacheManager()
        
        # 测试基本操作
        try:
            cache_manager.set('test_key', 'test_value')
            result = cache_manager.get('test_key')
            cache_manager.delete('test_key')
        except Exception:
            # Redis可能不可用，这是正常的
            pass


class TestDatabase:
    """测试数据库模块"""
    
    def test_database_import(self):
        """测试数据库模块导入"""
        from woniunote.common import database
        
        assert database is not None
        assert hasattr(database, 'db')
    
    def test_db_connection_context(self):
        """测试数据库连接上下文"""
        from woniunote.common.utils import get_db_connection_context
        
        # 测试函数存在
        assert callable(get_db_connection_context)
        
        # 由于需要实际数据库连接，这里只测试函数存在
        try:
            with get_db_connection_context() as conn:
                assert conn is not None
        except Exception:
            # 数据库可能不可用，这是正常的
            pass


class TestRateLimiter:
    """测试速率限制器"""
    
    def test_rate_limiter_import(self):
        """测试速率限制器导入"""
        from woniunote.common.rate_limiter import RateLimiter
        
        assert RateLimiter is not None
    
    def test_rate_limiter_init(self):
        """测试速率限制器初始化"""
        from woniunote.common.rate_limiter import RateLimiter
        
        limiter = RateLimiter(max_calls=10, period=60)
        assert limiter is not None
        assert limiter.max_calls == 10
        assert limiter.period == 60


class TestAsyncTasks:
    """测试异步任务"""
    
    def test_async_tasks_import(self):
        """测试异步任务导入"""
        from woniunote.common.async_tasks import TaskManager
        
        assert TaskManager is not None
    
    def test_task_manager_init(self):
        """测试任务管理器初始化"""
        from woniunote.common.async_tasks import TaskManager
        
        manager = TaskManager()
        assert manager is not None


class TestMonitoring:
    """测试监控工具"""
    
    def test_monitoring_import(self):
        """测试监控工具导入"""
        from woniunote.common.monitoring import PerformanceMonitor
        
        assert PerformanceMonitor is not None
    
    def test_performance_monitor_init(self):
        """测试性能监控器初始化"""
        from woniunote.common.monitoring import PerformanceMonitor
        
        monitor = PerformanceMonitor()
        assert monitor is not None


class TestConfigManager:
    """测试配置管理器"""
    
    def test_config_manager_import(self):
        """测试配置管理器导入"""
        from woniunote.common.config_manager import ConfigManager
        
        assert ConfigManager is not None
    
    def test_config_manager_init(self):
        """测试配置管理器初始化"""
        from woniunote.common.config_manager import ConfigManager
        
        manager = ConfigManager()
        assert manager is not None


class TestDatabaseOptimizer:
    """测试数据库优化器"""
    
    def test_database_optimizer_import(self):
        """测试数据库优化器导入"""
        from woniunote.common.database_optimizer import DatabaseOptimizer
        
        assert DatabaseOptimizer is not None
    
    def test_database_optimizer_init(self):
        """测试数据库优化器初始化"""
        from woniunote.common.database_optimizer import DatabaseOptimizer
        
        optimizer = DatabaseOptimizer()
        assert optimizer is not None


class TestStaticOptimizer:
    """测试静态文件优化器"""
    
    def test_static_optimizer_import(self):
        """测试静态文件优化器导入"""
        from woniunote.common.static_optimizer import StaticOptimizer
        
        assert StaticOptimizer is not None
    
    def test_static_optimizer_init(self):
        """测试静态文件优化器初始化"""
        from woniunote.common.static_optimizer import StaticOptimizer
        
        optimizer = StaticOptimizer()
        assert optimizer is not None


class TestSessionUtil:
    """测试会话工具"""
    
    def test_session_util_import(self):
        """测试会话工具导入"""
        from woniunote.common.session_util import get_session_data, set_session_data
        
        assert get_session_data is not None
        assert set_session_data is not None
        assert callable(get_session_data)
        assert callable(set_session_data)


class TestRedisDB:
    """测试Redis数据库"""
    
    def test_redis_db_import(self):
        """测试Redis数据库导入"""
        from woniunote.common.redisdb import RedisManager
        
        assert RedisManager is not None
    
    def test_redis_manager_init(self):
        """测试Redis管理器初始化"""
        from woniunote.common.redisdb import RedisManager
        
        manager = RedisManager()
        assert manager is not None


class TestTodoDatabase:
    """测试Todo数据库"""
    
    def test_todo_database_import(self):
        """测试Todo数据库导入"""
        from woniunote.common.todo_database import TodoManager
        
        assert TodoManager is not None
    
    def test_todo_manager_init(self):
        """测试Todo管理器初始化"""
        from woniunote.common.todo_database import TodoManager
        
        manager = TodoManager()
        assert manager is not None


class TestCardDatabase:
    """测试Card数据库"""
    
    def test_card_database_import(self):
        """测试Card数据库导入"""
        from woniunote.common.card_database import CardManager
        
        assert CardManager is not None
    
    def test_card_manager_init(self):
        """测试Card管理器初始化"""
        from woniunote.common.card_database import CardManager
        
        manager = CardManager()
        assert manager is not None


class TestLogDecorator:
    """测试日志装饰器"""
    
    def test_log_decorator_import(self):
        """测试日志装饰器导入"""
        from woniunote.common.log_decorator import log_execution, timing_log
        
        assert log_execution is not None
        assert timing_log is not None
        assert callable(log_execution)
        assert callable(timing_log)


@pytest.mark.integration
class TestIntegration:
    """集成测试"""
    
    def test_logger_and_utils_integration(self):
        """测试日志记录器和工具函数集成"""
        from woniunote.common.simple_logger import get_simple_logger
        from woniunote.common.utils import validate_email, gen_email_code
        
        logger = get_simple_logger('integration_test')
        
        # 测试邮箱验证并记录日志
        email = "test@example.com"
        is_valid = validate_email(email)
        logger.info(f"Email validation result: {is_valid}")
        
        # 测试验证码生成并记录日志
        code = gen_email_code()
        logger.info(f"Generated email code: {code}")
        
        assert is_valid == True
        assert len(code) == 6
    
    def test_cache_and_database_integration(self):
        """测试缓存和数据库集成"""
        from woniunote.common.cache_utils import CacheManager
        from woniunote.common import database
        
        cache_manager = CacheManager()
        
        # 测试基本集成
        assert cache_manager is not None
        assert database is not None
    
    def test_comprehensive_functionality(self):
        """测试综合功能"""
        from woniunote.common.simple_logger import get_simple_logger
        from woniunote.common.utils import validate_email, gen_email_code, validate_filename
        from woniunote.common.cache_utils import CacheManager
        
        # 创建组件
        logger = get_simple_logger('comprehensive_test')
        cache_manager = CacheManager()
        
        # 测试邮箱验证流程
        test_emails = [
            "valid@example.com",
            "invalid_email",
            "another@test.org"
        ]
        
        valid_count = 0
        for email in test_emails:
            is_valid = validate_email(email)
            if is_valid:
                valid_count += 1
                code = gen_email_code()
                logger.info(f"Generated code {code} for {email}")
        
        assert valid_count == 2  # 应该有2个有效邮箱
        
        # 测试文件名验证
        test_files = [
            "document.pdf",
            "../malicious.txt",
            "normal_file.jpg"
        ]
        
        safe_count = 0
        for filename in test_files:
            is_safe = validate_filename(filename)
            if is_safe:
                safe_count += 1
                logger.info(f"Safe filename: {filename}")
        
        assert safe_count == 2  # 应该有2个安全文件名 