import pytest

def test_utils_basic():
    """基础工具测试"""
    # 简单的断言测试，确保测试框架正常工作
    assert True

def test_string_operations():
    """字符串操作测试"""
    test_str = "Hello World"
    assert len(test_str) == 11
    assert test_str.startswith("Hello")

def test_list_operations():
    """列表操作测试"""
    test_list = [1, 2, 3, 4, 5]
    assert len(test_list) == 5
    assert sum(test_list) == 15
