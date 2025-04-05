#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
最基础测试 - 检查应用程序能否启动并访问基本页面
"""

import os
import sys

# 确保能找到项目根目录
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 导入Flask应用
try:
    from app import app
    from flask import Flask
    import pytest
except ImportError as e:
    print(f"导入错误: {e}")
    app = None

def test_app_exists():
    """测试Flask应用是否存在"""
    assert app is not None

def test_app_is_flask():
    """测试app是否是Flask应用实例"""
    assert isinstance(app, Flask)

@pytest.fixture
def client():
    """创建测试客户端"""
    if app is None:
        pytest.skip("无法导入Flask应用")
    
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_home_page(client):
    """测试首页是否返回200状态码"""
    response = client.get('/')
    assert response.status_code == 200, f"首页返回意外状态码: {response.status_code}"

if __name__ == "__main__":
    print("请使用 pytest 运行这个测试文件")
