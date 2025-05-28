#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
基本应用测试

测试Flask应用的基本功能
"""

import pytest
import sys
import os

# 添加项目根目录到路径
project_root = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, project_root)

from woniunote.app import create_app

@pytest.fixture
def app():
    """创建测试应用"""
    app = create_app('testing')
    return app

@pytest.fixture 
def client(app):
    """创建测试客户端"""
    return app.test_client()

def test_app_creation(app):
    """测试应用创建"""
    assert app is not None, "应用创建失败"
    assert app.config['TESTING'] is True, "应用未设置为测试模式"
    print("✓ 应用创建测试通过")

def test_app_context(app):
    """测试应用上下文"""
    with app.app_context():
        # 在应用上下文中，应该能够访问配置
        assert app.config is not None, "无法访问应用配置"
        print("✓ 应用上下文测试通过")

def test_test_client(client):
    """测试客户端创建"""
    assert client is not None, "测试客户端创建失败"
    print("✓ 测试客户端创建测试通过")

if __name__ == "__main__":
    # 直接运行测试
    pytest.main([__file__, "-v"]) 