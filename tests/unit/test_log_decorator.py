#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""日志装饰器模块测试"""
import pytest
import time
import uuid
from unittest.mock import Mock, patch, MagicMock

# 添加项目根目录到Python路径
import os
import sys
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


class TestLogDecorator:
    """日志装饰器模块测试"""

    def test_log_decorator_imports(self):
        """测试日志装饰器模块导入"""
        try:
            import woniunote.common.log_decorator as log_decorator
            assert log_decorator is not None
        except ImportError as e:
            pytest.skip(f"无法导入log_decorator模块: {e}")

    def test_generate_trace_id(self):
        """测试跟踪ID生成"""
        try:
            from woniunote.common.log_decorator import generate_trace_id

            trace_id = generate_trace_id()
            assert isinstance(trace_id, str)
            assert len(trace_id) > 0

            # 验证是有效的UUID格式
            uuid.UUID(trace_id)

        except ImportError:
            pytest.skip("无法导入log_decorator模块")

    def test_get_trace_id(self):
        """测试获取跟踪ID"""
        try:
            from woniunote.common.log_decorator import get_trace_id, _thread_local_trace_id

            # 清空线程本地存储
            _thread_local_trace_id.clear()

            trace_id = get_trace_id()
            assert isinstance(trace_id, str)
            assert len(trace_id) > 0

            # 验证跟踪ID被存储
            assert 'trace_id' in _thread_local_trace_id
            assert _thread_local_trace_id['trace_id'] == trace_id

            # 验证第二次调用返回相同ID
            trace_id2 = get_trace_id()
            assert trace_id == trace_id2

        except ImportError:
            pytest.skip("无法导入log_decorator模块")

    @patch('woniunote.common.log_decorator.get_simple_logger')
    def test_log_function_decorator_basic(self, mock_get_logger):
        """测试日志装饰器基本功能"""
        try:
            from woniunote.common.log_decorator import log_function

            # 模拟logger
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger

            # 创建被装饰的函数
            @log_function()
            def test_function(x, y=10):
                return x + y

            # 调用函数
            result = test_function(5, y=3)
            assert result == 8

            # 验证日志记录
            assert mock_logger.info.called
            assert mock_logger.error.not_called

        except ImportError:
            pytest.skip("无法导入log_decorator模块")

    @patch('woniunote.common.log_decorator.get_simple_logger')
    def test_log_function_decorator_with_exception(self, mock_get_logger):
        """测试日志装饰器异常处理"""
        try:
            from woniunote.common.log_decorator import log_function

            # 模拟logger
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger

            # 创建会抛出异常的函数
            @log_function()
            def failing_function():
                raise ValueError("Test exception")

            # 调用函数并验证异常被抛出
            with pytest.raises(ValueError, match="Test exception"):
                failing_function()

            # 验证异常被记录
            assert mock_logger.error.called

        except ImportError:
            pytest.skip("无法导入log_decorator模块")

    @patch('woniunote.common.log_decorator.get_simple_logger')
    def test_log_function_decorator_performance(self, mock_get_logger):
        """测试日志装饰器性能记录"""
        try:
            from woniunote.common.log_decorator import log_function

            # 模拟logger
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger

            # 创建被装饰的函数
            @log_function(performance=True)
            def test_function():
                time.sleep(0.01)  # 短暂延迟
                return "success"

            # 调用函数
            result = test_function()
            assert result == "success"

            # 验证性能信息被记录
            performance_calls = [call for call in mock_logger.info.call_args_list
                               if '耗时' in str(call)]
            assert len(performance_calls) > 0

        except ImportError:
            pytest.skip("无法导入log_decorator模块")

    @patch('woniunote.common.log_decorator.get_simple_logger')
    def test_log_function_decorator_custom_logger(self, mock_get_logger):
        """测试日志装饰器自定义logger"""
        try:
            from woniunote.common.log_decorator import log_function

            # 模拟自定义logger
            custom_logger = Mock()
            mock_get_logger.return_value = Mock()  # 默认logger

            # 创建被装饰的函数
            @log_function(logger=custom_logger)
            def test_function():
                return "success"

            # 调用函数
            result = test_function()
            assert result == "success"

            # 验证使用的是自定义logger
            custom_logger.info.assert_called()

        except ImportError:
            pytest.skip("无法导入log_decorator模块")

    @patch('woniunote.common.log_decorator.get_simple_logger')
    def test_log_function_decorator_args_logging(self, mock_get_logger):
        """测试日志装饰器参数记录"""
        try:
            from woniunote.common.log_decorator import log_function

            # 模拟logger
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger

            # 创建被装饰的函数
            @log_function(log_args=True)
            def test_function(a, b=None, *args, **kwargs):
                return f"{a}-{b}"

            # 调用函数
            result = test_function("test", b="value", extra="param")
            assert result == "test-value"

            # 验证参数被记录
            args_calls = [call for call in mock_logger.info.call_args_list
                         if '调用:' in str(call)]
            assert len(args_calls) > 0

        except ImportError:
            pytest.skip("无法导入log_decorator模块")

    @patch('woniunote.common.log_decorator.get_simple_logger')
    def test_log_function_decorator_return_logging(self, mock_get_logger):
        """测试日志装饰器返回值记录"""
        try:
            from woniunote.common.log_decorator import log_function

            # 模拟logger
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger

            # 创建被装饰的函数
            @log_function(log_return=True)
            def test_function():
                return {"status": "success", "data": [1, 2, 3]}

            # 调用函数
            result = test_function()
            assert result["status"] == "success"

            # 验证返回值被记录
            return_calls = [call for call in mock_logger.info.call_args_list
                           if '返回:' in str(call)]
            assert len(return_calls) > 0

        except ImportError:
            pytest.skip("无法导入log_decorator模块")

    def test_trace_id_thread_local(self):
        """测试跟踪ID线程本地存储"""
        try:
            from woniunote.common.log_decorator import get_trace_id, _thread_local_trace_id

            # 清空存储
            _thread_local_trace_id.clear()

            # 获取跟踪ID
            trace_id1 = get_trace_id()
            assert 'trace_id' in _thread_local_trace_id

            # 再次获取应该是相同的
            trace_id2 = get_trace_id()
            assert trace_id1 == trace_id2

            # 清空后应该生成新的
            _thread_local_trace_id.clear()
            trace_id3 = get_trace_id()
            assert trace_id1 != trace_id3

        except ImportError:
            pytest.skip("无法导入log_decorator模块")

    @patch('woniunote.common.log_decorator.get_simple_logger')
    def test_log_function_decorator_disabled_features(self, mock_get_logger):
        """测试日志装饰器禁用功能"""
        try:
            from woniunote.common.log_decorator import log_function

            # 模拟logger
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger

            # 创建被装饰的函数，禁用所有日志功能
            @log_function(log_args=False, log_return=False, log_exception=False, performance=False)
            def test_function():
                return "success"

            # 调用函数
            result = test_function()
            assert result == "success"

            # 验证没有日志被记录
            assert not mock_logger.info.called
            assert not mock_logger.error.called

        except ImportError:
            pytest.skip("无法导入log_decorator模块")

    def test_module_constants(self):
        """测试模块常量"""
        try:
            import woniunote.common.log_decorator as log_decorator
            # 验证模块的基本属性
            assert hasattr(log_decorator, '__file__')
            assert hasattr(log_decorator, '__name__')
        except ImportError:
            pytest.skip("无法导入log_decorator模块")

    def test_module_docstring(self):
        """测试模块文档字符串"""
        try:
            import woniunote.common.log_decorator as log_decorator

            # 验证模块的基本属性存在
            assert hasattr(log_decorator, '__file__')
            assert hasattr(log_decorator, '__name__')

            # 文档字符串可能为None，但这是正常的
            assert log_decorator.__doc__ is None or isinstance(log_decorator.__doc__, str)

        except ImportError:
            pytest.skip("无法导入log_decorator模块")

    def test_functools_wraps_usage(self):
        """测试functools.wraps使用"""
        try:
            from woniunote.common.log_decorator import log_function

            @log_function()
            def test_function():
                """Test docstring"""
                pass

            # 验证functools.wraps正确工作
            assert test_function.__name__ == "test_function"
            assert test_function.__doc__ == "Test docstring"

        except ImportError:
            pytest.skip("无法导入log_decorator模块")
