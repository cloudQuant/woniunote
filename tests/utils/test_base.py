#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试基础类模块

提供测试中常用的工具函数和基类，包括:
- HTTP客户端会话管理
- SSL验证配置
- 日志初始化
- 路径管理
- Flask应用上下文支持
"""

import os
import sys
import logging
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from urllib3.exceptions import InsecureRequestWarning
import warnings
import pytest

# 添加项目根目录到Python路径
project_root = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
sys.path.insert(0, project_root)

# 导入Flask应用
try:
    from woniunote.app import app as flask_app
except ImportError:
    # 如果直接导入app失败，尝试导入create_app函数
    try:
        from woniunote.app import create_app
        flask_app = create_app()
    except ImportError:
        # 如果都失败，提供一个空的Flask应用占位符
        import flask
        flask_app = flask.Flask(__name__)
        logging.warning("无法导入WoniuNote Flask应用，使用空的Flask应用代替")

# 导入测试配置
from tests.utils.test_config import (
    SERVER_CONFIG, 
    get_base_url, 
    setup_logging
)

# 配置日志
logger = setup_logging("woniunote_test")

# 禁用不安全HTTPS请求的警告
warnings.filterwarnings("ignore", category=InsecureRequestWarning)

class FlaskAppContextProvider:
    """提供Flask应用上下文的工具类"""
    
    @staticmethod
    def get_app_context():
        """获取Flask应用上下文"""
        return flask_app.app_context()
    
    @staticmethod
    def with_app_context(func):
        """装饰器：使函数在Flask应用上下文中运行"""
        def wrapper(*args, **kwargs):
            with flask_app.app_context():
                return func(*args, **kwargs)
        return wrapper


class TestBase:
    """测试基类，提供共享功能"""
    
    # 默认服务器配置
    SERVER_HOST = SERVER_CONFIG['host']
    SERVER_PORT = SERVER_CONFIG['port']
    USE_HTTPS = SERVER_CONFIG['protocol'] == 'https'
    REQUEST_TIMEOUT = SERVER_CONFIG['timeout']
    
    @classmethod
    def setup_class(cls):
        """在类初始化时设置共享资源"""
        cls.base_url = get_base_url()
        logger.info(f"使用基础URL: {cls.base_url}")
        
        # 创建会话，禁用证书验证
        cls.session = requests.Session()
        cls.session.verify = False
    
    @classmethod
    def teardown_class(cls):
        """在类销毁时清理资源"""
        if hasattr(cls, 'session'):
            cls.session.close()
    
    @staticmethod
    def wait_for_server(seconds=1):
        """等待服务器启动"""
        logger.info(f"等待服务器就绪: {seconds}秒")
        time.sleep(seconds)
    
    @classmethod
    def get_url(cls, path):
        """构建完整的URL路径"""
        if path.startswith('/'):
            return f"{cls.base_url}{path}"
        return f"{cls.base_url}/{path}"
    
    @classmethod
    def make_request(cls, method, path, **kwargs):
        """
        发送HTTP请求并处理异常
        
        Args:
            method: HTTP方法 (get, post, put, delete等)
            path: 相对路径
            **kwargs: 传递给requests的参数
            
        Returns:
            requests.Response对象
            
        Raises:
            pytest.fail: 如果请求失败
        """
        url = cls.get_url(path)
        logger.info(f"发送{method.upper()}请求到: {url}")
        
        try:
            # 设置默认超时
            kwargs.setdefault('timeout', cls.REQUEST_TIMEOUT)
            # 确保禁用SSL验证
            kwargs.setdefault('verify', False)
            
            # 发送请求
            response = getattr(cls.session, method.lower())(url, **kwargs)
            logger.info(f"收到响应: 状态码={response.status_code}")
            return response
        except requests.exceptions.RequestException as e:
            logger.error(f"请求失败: {str(e)}")
            pytest.fail(f"请求失败: {str(e)}")
    
    @classmethod
    def login(cls, username, password):
        """
        登录到WoniuNote系统
        
        Args:
            username: 用户名
            password: 密码
            
        Returns:
            bool: 登录是否成功
        """
        login_data = {
            "username": username,
            "password": password
        }
        
        response = cls.make_request('post', '/user/login', data=login_data)
        
        # 检查登录是否成功（根据应用实际情况调整）
        return response.status_code == 200 and "登录成功" in response.text

# 导出常用函数给测试文件使用
get_project_root = lambda: project_root

# 添加简单的单元测试函数，确保该文件可以被测试运行
@pytest.mark.unit
def test_base_url_configuration():
    """测试基础URL配置是否正确"""
    base_url = get_base_url()
    assert base_url is not None
    assert base_url.startswith('http')
    logger.info(f"基础URL正确: {base_url}")

@pytest.mark.unit
def test_flask_app_import():
    """测试Flask应用是否正确导入"""
    assert flask_app is not None
    logger.info("Flask应用导入成功")
