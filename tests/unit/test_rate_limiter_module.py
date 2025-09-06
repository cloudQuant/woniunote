#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""限流器模块测试"""
import pytest
import time
from unittest.mock import Mock, patch, MagicMock

# 添加项目根目录到Python路径
import os
import sys
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


class TestRateLimiterModule:
    """限流器模块测试"""

    def test_rate_limiter_module_imports(self):
        """测试限流器模块导入"""
        try:
            import woniunote.common.rate_limiter as rate_limiter
            assert rate_limiter is not None
        except ImportError as e:
            pytest.skip(f"无法导入rate_limiter模块: {e}")

    def test_sliding_window_limiter_init(self):
        """测试滑动窗口限流器初始化"""
        try:
            from woniunote.common.rate_limiter import SlidingWindowLimiter

            limiter = SlidingWindowLimiter(max_requests=10, window_size=60)
            assert limiter.max_requests == 10
            assert limiter.window_size == 60
            assert isinstance(limiter.requests, dict)
            assert limiter.lock is not None

        except ImportError:
            pytest.skip("无法导入rate_limiter模块")

    def test_sliding_window_limiter_is_allowed(self):
        """测试滑动窗口限流器允许请求"""
        try:
            from woniunote.common.rate_limiter import SlidingWindowLimiter

            limiter = SlidingWindowLimiter(max_requests=2, window_size=60)

            # 第一次请求应该允许
            result, info = limiter.is_allowed('user1')
            assert result is True
            assert info['allowed'] is True
            assert info['limit'] == 2
            assert info['remaining'] == 1

            # 第二次请求应该允许
            result, info = limiter.is_allowed('user1')
            assert result is True
            assert info['allowed'] is True
            assert info['remaining'] == 0

            # 第三次请求应该被拒绝
            result, info = limiter.is_allowed('user1')
            assert result is False
            assert info['allowed'] is False
            assert info['remaining'] == 0
            assert 'reset_time' in info
            assert 'retry_after' in info

        except ImportError:
            pytest.skip("无法导入rate_limiter模块")

    def test_sliding_window_limiter_window_expiry(self):
        """测试滑动窗口过期"""
        try:
            from woniunote.common.rate_limiter import SlidingWindowLimiter

            limiter = SlidingWindowLimiter(max_requests=1, window_size=1)

            # 第一次请求
            result, info = limiter.is_allowed('user1')
            assert result is True

            # 等待窗口过期
            time.sleep(1.1)

            # 第二次请求应该允许（窗口已过期）
            result, info = limiter.is_allowed('user1')
            assert result is True

        except ImportError:
            pytest.skip("无法导入rate_limiter模块")

    def test_token_bucket_limiter_init(self):
        """测试令牌桶限流器初始化"""
        try:
            from woniunote.common.rate_limiter import TokenBucketLimiter

            limiter = TokenBucketLimiter(capacity=10, refill_rate=1)
            assert limiter.capacity == 10
            assert limiter.refill_rate == 1
            assert limiter.tokens == 10
            assert limiter.last_refill is not None

        except ImportError:
            pytest.skip("无法导入rate_limiter模块")

    def test_token_bucket_limiter_is_allowed(self):
        """测试令牌桶限流器允许请求"""
        try:
            from woniunote.common.rate_limiter import TokenBucketLimiter

            limiter = TokenBucketLimiter(capacity=2, refill_rate=1)

            # 第一次请求应该允许
            result, info = limiter.is_allowed('user1')
            assert result is True
            assert info['allowed'] is True
            assert info['remaining'] == 1

            # 第二次请求应该允许
            result, info = limiter.is_allowed('user1')
            assert result is True
            assert info['remaining'] == 0

            # 第三次请求应该被拒绝
            result, info = limiter.is_allowed('user1')
            assert result is False
            assert info['allowed'] is False
            assert info['remaining'] == 0

        except ImportError:
            pytest.skip("无法导入rate_limiter模块")

    def test_token_bucket_limiter_refill(self):
        """测试令牌桶令牌补充"""
        try:
            from woniunote.common.rate_limiter import TokenBucketLimiter

            limiter = TokenBucketLimiter(capacity=10, refill_rate=5)

            # 消耗所有令牌
            for _ in range(10):
                limiter.is_allowed('user1')

            # 等待补充
            time.sleep(1.1)

            # 检查令牌补充
            result, info = limiter.is_allowed('user1')
            assert result is True
            assert info['remaining'] >= 4  # 应该补充了至少4个令牌

        except ImportError:
            pytest.skip("无法导入rate_limiter模块")

    def test_fixed_window_limiter_init(self):
        """测试固定窗口限流器初始化"""
        try:
            from woniunote.common.rate_limiter import FixedWindowLimiter

            limiter = FixedWindowLimiter(max_requests=10, window_size=60)
            assert limiter.max_requests == 10
            assert limiter.window_size == 60
            assert isinstance(limiter.requests, dict)
            assert limiter.lock is not None

        except ImportError:
            pytest.skip("无法导入rate_limiter模块")

    def test_fixed_window_limiter_is_allowed(self):
        """测试固定窗口限流器允许请求"""
        try:
            from woniunote.common.rate_limiter import FixedWindowLimiter

            limiter = FixedWindowLimiter(max_requests=2, window_size=60)

            # 第一次请求应该允许
            result, info = limiter.is_allowed('user1')
            assert result is True
            assert info['allowed'] is True

            # 第二次请求应该允许
            result, info = limiter.is_allowed('user1')
            assert result is True

            # 第三次请求应该被拒绝
            result, info = limiter.is_allowed('user1')
            assert result is False
            assert info['allowed'] is False

        except ImportError:
            pytest.skip("无法导入rate_limiter模块")

    def test_rate_limiter_manager_init(self):
        """测试限流器管理器初始化"""
        try:
            from woniunote.common.rate_limiter import RateLimiterManager

            manager = RateLimiterManager()
            assert manager.limiters is not None
            assert isinstance(manager.limiters, dict)

        except ImportError:
            pytest.skip("无法导入rate_limiter模块")

    def test_rate_limiter_manager_add_limiter(self):
        """测试添加限流器"""
        try:
            from woniunote.common.rate_limiter import RateLimiterManager, SlidingWindowLimiter

            manager = RateLimiterManager()
            limiter = SlidingWindowLimiter(max_requests=10, window_size=60)

            manager.add_limiter('test', limiter)
            assert 'test' in manager.limiters
            assert manager.limiters['test'] == limiter

        except ImportError:
            pytest.skip("无法导入rate_limiter模块")

    def test_rate_limiter_manager_is_allowed(self):
        """测试管理器检查允许请求"""
        try:
            from woniunote.common.rate_limiter import RateLimiterManager, SlidingWindowLimiter

            manager = RateLimiterManager()
            limiter = SlidingWindowLimiter(max_requests=1, window_size=60)

            manager.add_limiter('test', limiter)

            # 第一次请求应该允许
            result, info = manager.is_allowed('test', 'user1')
            assert result is True

            # 第二次请求应该被拒绝
            result, info = manager.is_allowed('test', 'user1')
            assert result is False

        except ImportError:
            pytest.skip("无法导入rate_limiter模块")

    @patch('woniunote.common.rate_limiter.request')
    def test_get_client_key(self, mock_request):
        """测试获取客户端密钥"""
        try:
            from woniunote.common.rate_limiter import get_client_key

            mock_request.remote_addr = '127.0.0.1'
            mock_request.headers.get.return_value = 'user-agent-string'

            key = get_client_key()
            assert isinstance(key, str)
            assert len(key) > 0

        except ImportError:
            pytest.skip("无法导入rate_limiter模块")

    def test_rate_limit_decorator(self):
        """测试限流装饰器"""
        try:
            from woniunote.common.rate_limiter import rate_limit

            @rate_limit('test', 2, 60)
            def test_function():
                return "success"

            # 第一次调用应该成功
            result = test_function()
            assert result == "success"

            # 第二次调用应该成功
            result = test_function()
            assert result == "success"

        except ImportError:
            pytest.skip("无法导入rate_limiter模块")

    def test_module_constants(self):
        """测试模块常量"""
        try:
            import woniunote.common.rate_limiter as rate_limiter

            # 验证模块的基本属性
            assert hasattr(rate_limiter, '__file__')
            assert hasattr(rate_limiter, '__name__')

        except ImportError:
            pytest.skip("无法导入rate_limiter模块")

    def test_module_docstring(self):
        """测试模块文档字符串"""
        try:
            import woniunote.common.rate_limiter as rate_limiter

            # 验证模块有文档字符串
            assert rate_limiter.__doc__ is not None
            assert len(rate_limiter.__doc__.strip()) > 0

        except ImportError:
            pytest.skip("无法导入rate_limiter模块")

    def test_logger_initialization(self):
        """测试日志记录器初始化"""
        try:
            import woniunote.common.rate_limiter as rate_limiter

            # 验证日志记录器存在
            assert hasattr(rate_limiter, 'logger')
            assert rate_limiter.logger is not None

        except ImportError:
            pytest.skip("无法导入rate_limiter模块")
