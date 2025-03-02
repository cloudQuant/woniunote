import pytest
from datetime import datetime
from unittest.mock import patch
from woniunote.common.timer import can_use_minute

def test_can_use_minute_basic():
    """测试基本的分钟计算功能"""
    # 使用一个固定的当前时间进行测试
    with patch('datetime.datetime') as mock_datetime:
        # 模拟当前时间为 2024-01-01 00:00:00
        mock_now = datetime(2024, 1, 1, 0, 0, 0)
        mock_datetime.now.return_value = mock_now
        mock_datetime.strptime = datetime.strptime
        
        # 计算预期分钟数
        target_time = datetime(2078, 5, 7, 23, 59, 59)
        total_seconds = (target_time - mock_now).total_seconds()
        expected_minutes = int(total_seconds / 60)
        
        result = can_use_minute()
        assert abs(result - expected_minutes) < 1  # 允许1分钟的误差

def test_can_use_minute_near_target():
    """测试接近目标时间的情况"""
    with patch('datetime.datetime') as mock_datetime:
        # 模拟当前时间为目标时间前一小时
        mock_now = datetime(2078, 5, 7, 22, 59, 59)
        mock_datetime.now.return_value = mock_now
        mock_datetime.strptime = datetime.strptime
        
        result = can_use_minute()
        expected_minutes = 60  # 一小时等于60分钟
        assert abs(result - expected_minutes) < 1  # 允许1分钟的误差

def test_can_use_minute_at_target():
    """测试在目标时间的情况"""
    with patch('datetime.datetime') as mock_datetime:
        # 模拟当前时间为目标时间
        mock_now = datetime(2078, 5, 7, 23, 59, 59)
        mock_datetime.now.return_value = mock_now
        mock_datetime.strptime = datetime.strptime
        
        result = can_use_minute()
        assert result == 0  # 在目标时间时应该返回0

def test_can_use_minute_past_target():
    """测试超过目标时间的情况"""
    with patch('datetime.datetime') as mock_datetime:
        # 模拟当前时间已经超过目标时间一小时
        mock_now = datetime(2078, 5, 8, 0, 59, 59)
        mock_datetime.now.return_value = mock_now
        mock_datetime.strptime = datetime.strptime
        
        result = can_use_minute()
        expected_minutes = -60  # 超过一小时应该返回-60
        assert abs(result - expected_minutes) < 1  # 允许1分钟的误差

def test_can_use_minute_type():
    """测试返回值类型"""
    with patch('datetime.datetime') as mock_datetime:
        # 模拟当前时间
        mock_now = datetime(2024, 1, 1, 0, 0, 0)
        mock_datetime.now.return_value = mock_now
        mock_datetime.strptime = datetime.strptime
        
        result = can_use_minute()
        assert isinstance(result, int)  # 确保返回值是整数类型
