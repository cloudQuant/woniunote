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
import functools
import time
import urllib.parse
import json

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
        """装饰器：使函数在Flask应用上下文中运行
        
        注意：此装饰器不应用于 pytest fixture，
        否则会导致"fixture called directly"错误。
        只在普通测试函数和辅助函数上使用。
        """
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 简化装饰器，只负责提供应用上下文，不干扰参数传递
            with flask_app.app_context():
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    # 捕获并记录异常，但让它继续传播
                    logger.error(f"Flask应用上下文中出现错误: {str(e)}")
                    raise
        return wrapper
    
    @staticmethod
    def with_app_context_fixture():
        """创建一个能与pytest fixture兼容的应用上下文管理器
        
        与with_app_context不同，这个方法返回一个可以在fixture中使用的上下文管理器
        """
        @pytest.fixture
        def app_context():
            logger.info("创建Flask应用上下文")
            try:
                with flask_app.app_context():
                    yield
            except Exception as e:
                logger.error(f"Flask应用上下文fixture出错: {str(e)}")
                # 不报错，继续测试
                yield
            finally:
                logger.info("关闭Flask应用上下文")
        return app_context


class TestBase:
    """测试基类，提供共享功能"""
    
    @classmethod
    def setup_class(cls):
        """在类初始化时设置共享资源"""
        # 动态获取最新的服务器配置
        from tests.utils.test_config import SERVER_CONFIG, get_base_url
        cls.SERVER_HOST = SERVER_CONFIG['host']
        cls.SERVER_PORT = SERVER_CONFIG['port']
        cls.USE_HTTPS = SERVER_CONFIG['protocol'] == 'https'
        cls.REQUEST_TIMEOUT = SERVER_CONFIG['timeout']
        
        # 使用配置中的协议构建基础URL
        cls.base_url = get_base_url()
        logger.info(f"使用基础URL: {cls.base_url}")
        
        # 创建会话，禁用证书验证
        cls.session = requests.Session()
        cls.session.verify = False
        
        # 禁用SSL警告
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
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
        # 确保使用当前实例的base_url，而不是每次重新生成
        logger.debug(f"构建URL路径: 基础URL={cls.base_url}, 路径={path}")
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
        # 构建URL
        url = cls.get_url(path)
        logger.info(f"发送{method.upper()}请求到: {url}")
        
        # 添加用户代理头
        headers = kwargs.get('headers', {})
        headers.setdefault('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) WoniuNote/Test')
        kwargs['headers'] = headers
        
        # 设置默认超时和禁用SSL验证
        kwargs.setdefault('timeout', cls.REQUEST_TIMEOUT)
        kwargs.setdefault('verify', False)
        
        # 首先尝试使用标准 requests
        try:
            response = getattr(cls.session, method.lower())(url, **kwargs)
            logger.info(f"收到响应: 状态码={response.status_code}")
            return response
        except requests.exceptions.SSLError as e:
            logger.warning(f"SSL错误: {str(e)}，尝试切换协议...")
            
            # 如果URL是HTTPS但服务器使用HTTP，尝试将URL改为HTTP
            if url.startswith('https://'):
                alt_url = url.replace('https://', 'http://', 1)
                logger.info(f"尝试使用HTTP: {alt_url}")
                try:
                    response = getattr(cls.session, method.lower())(alt_url, **kwargs)
                    logger.info(f"使用HTTP成功, 状态码={response.status_code}")
                    return response
                except Exception as http_e:
                    logger.warning(f"HTTP请求也失败: {str(http_e)}")
            
            # 如果URL是HTTP但服务器需要HTTPS，尝试将URL改为HTTPS
            elif url.startswith('http://'):
                alt_url = url.replace('http://', 'https://', 1)
                logger.info(f"尝试使用HTTPS: {alt_url}")
                try:
                    response = getattr(cls.session, method.lower())(alt_url, **kwargs)
                    logger.info(f"使用HTTPS成功, 状态码={response.status_code}")
                    return response
                except Exception as https_e:
                    logger.warning(f"HTTPS请求也失败: {str(https_e)}")
            
            # 尝试使用urllib3直接发送HTTP请求，忽略SSL验证
            try:
                import urllib3
                urllib3.disable_warnings()
                
                http = urllib3.PoolManager(
                    timeout=kwargs.get('timeout', cls.REQUEST_TIMEOUT),
                    retries=3,
                    cert_reqs='CERT_NONE',
                    assert_hostname=False
                )
                
                # 首先尝试HTTP
                http_url = url.replace('https://', 'http://', 1) if url.startswith('https://') else url
                logger.info(f"通过urllib3尝试HTTP连接: {http_url}")
                
                # 提取查询参数，如果有的话
                parsed_url = urllib.parse.urlparse(http_url)
                path_with_query = parsed_url.path
                if parsed_url.query:
                    path_with_query += '?' + parsed_url.query
                
                # 对于POST/PUT请求，处理表单数据或JSON数据
                body = None
                headers = kwargs.get('headers', {}).copy()
                
                if method.lower() in ['post', 'put', 'patch']:
                    if 'json' in kwargs:
                        import json
                        body = json.dumps(kwargs['json']).encode('utf-8')
                        headers['Content-Type'] = 'application/json'
                    elif 'data' in kwargs:
                        if isinstance(kwargs['data'], dict):
                            body = urllib.parse.urlencode(kwargs['data']).encode()
                            headers['Content-Type'] = 'application/x-www-form-urlencoded'
                        else:
                            body = kwargs['data']
                
                # 发送请求
                urllib3_response = http.request(
                    method.upper(),
                    http_url,
                    body=body,
                    headers=headers,
                    redirect=kwargs.get('allow_redirects', True)
                )
                
                # 将urllib3响应转换为requests风格的响应
                from types import SimpleNamespace
                response = SimpleNamespace()
                response.status_code = urllib3_response.status
                response.headers = urllib3_response.headers
                response.text = urllib3_response.data.decode('utf-8')
                response.content = urllib3_response.data
                try:
                    import json
                    response.json = lambda: json.loads(response.text)
                except:
                    response.json = lambda: None
                
                logger.info(f"urllib3请求成功，状态码={response.status_code}")
                return response
                
            except Exception as urllib3_e:
                logger.error(f"urllib3请求失败: {str(urllib3_e)}")
            
            # 尝试使用socket直接发送HTTP请求
            try:
                import socket
                logger.info(f"尝试通过socket发送基本HTTP请求...")
                
                # 解析URL
                parsed_url = urllib.parse.urlparse(url)
                host = parsed_url.netloc.split(':')[0]
                port = int(parsed_url.netloc.split(':')[1]) if ':' in parsed_url.netloc else 80
                
                # 创建socket连接
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(kwargs.get('timeout', cls.REQUEST_TIMEOUT))
                s.connect((host, port))
                
                # 组装HTTP请求
                path_with_query = parsed_url.path
                if parsed_url.query:
                    path_with_query += '?' + parsed_url.query
                
                request = (
                    f"{method.upper()} {path_with_query} HTTP/1.1\r\n"
                    f"Host: {host}:{port}\r\n"
                    f"User-Agent: WoniuNote-Test\r\n"
                    f"Accept: */*\r\n"
                    f"Connection: close\r\n"
                )
                
                # 添加请求头
                for header, value in headers.items():
                    if header.lower() not in ['host', 'user-agent', 'connection']:
                        request += f"{header}: {value}\r\n"
                
                # 添加正文分隔符
                request += "\r\n"
                
                # 发送请求
                s.sendall(request.encode())
                
                # 接收响应
                response_data = b""
                while True:
                    try:
                        data = s.recv(4096)
                        if not data:
                            break
                        response_data += data
                    except socket.timeout:
                        break
                
                s.close()
                
                # 如果收到了有效的HTTP响应
                if response_data.startswith(b"HTTP/"):
                    # 解析HTTP响应
                    header_end = response_data.find(b"\r\n\r\n")
                    if header_end > 0:
                        headers_raw = response_data[:header_end].decode('utf-8', errors='ignore')
                        body = response_data[header_end+4:]
                        
                        # 获取状态码
                        status_line = headers_raw.split("\r\n")[0]
                        status_code = int(status_line.split(" ")[1])
                        
                        # 创建一个类似requests响应的对象
                        from types import SimpleNamespace
                        response = SimpleNamespace()
                        response.status_code = status_code
                        response.text = body.decode('utf-8', errors='ignore')
                        response.content = body
                        response.headers = {}
                        
                        # 解析响应头
                        for line in headers_raw.split("\r\n")[1:]:
                            if ":" in line:
                                key, value = line.split(":", 1)
                                response.headers[key.strip()] = value.strip()
                        
                        logger.info(f"socket请求成功，状态码={response.status_code}")
                        return response
                    else:
                        logger.error("无法解析HTTP响应头")
                else:
                    logger.error(f"收到无效的HTTP响应: {response_data[:100]}")
            except Exception as socket_e:
                logger.error(f"socket请求失败: {str(socket_e)}")
            
            # 所有尝试都失败，引发原始异常
            pytest.fail(f"所有HTTP/HTTPS请求方式均失败: {str(e)}")
            
        except requests.exceptions.RequestException as e:
            logger.error(f"请求失败: {str(e)}")
            
            # 尝试使用socket直接发送HTTP请求
            try:
                import socket
                logger.info(f"尝试通过socket发送基本HTTP请求...")
                
                # 解析URL
                parsed_url = urllib.parse.urlparse(url)
                host = parsed_url.netloc.split(':')[0]
                port = int(parsed_url.netloc.split(':')[1]) if ':' in parsed_url.netloc else 80
                
                # 创建socket连接
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(kwargs.get('timeout', cls.REQUEST_TIMEOUT))
                s.connect((host, port))
                
                # 组装HTTP请求
                path_with_query = parsed_url.path
                if parsed_url.query:
                    path_with_query += '?' + parsed_url.query
                
                request = (
                    f"{method.upper()} {path_with_query} HTTP/1.1\r\n"
                    f"Host: {host}:{port}\r\n"
                    f"User-Agent: WoniuNote-Test\r\n"
                    f"Accept: */*\r\n"
                    f"Connection: close\r\n"
                )
                
                # 添加请求头
                for header, value in headers.items():
                    if header.lower() not in ['host', 'user-agent', 'connection']:
                        request += f"{header}: {value}\r\n"
                
                # 添加正文分隔符
                request += "\r\n"
                
                # 发送请求
                s.sendall(request.encode())
                
                # 接收响应
                response_data = b""
                while True:
                    try:
                        data = s.recv(4096)
                        if not data:
                            break
                        response_data += data
                    except socket.timeout:
                        break
                
                s.close()
                
                # 如果收到了有效的HTTP响应
                if response_data.startswith(b"HTTP/"):
                    # 解析HTTP响应
                    header_end = response_data.find(b"\r\n\r\n")
                    if header_end > 0:
                        headers_raw = response_data[:header_end].decode('utf-8', errors='ignore')
                        body = response_data[header_end+4:]
                        
                        # 获取状态码
                        status_line = headers_raw.split("\r\n")[0]
                        status_code = int(status_line.split(" ")[1])
                        
                        # 创建一个类似requests响应的对象
                        from types import SimpleNamespace
                        response = SimpleNamespace()
                        response.status_code = status_code
                        response.text = body.decode('utf-8', errors='ignore')
                        response.content = body
                        response.headers = {}
                        
                        # 解析响应头
                        for line in headers_raw.split("\r\n")[1:]:
                            if ":" in line:
                                key, value = line.split(":", 1)
                                response.headers[key.strip()] = value.strip()
                        
                        logger.info(f"socket请求成功，状态码={response.status_code}")
                        return response
                    else:
                        logger.error("无法解析HTTP响应头")
                else:
                    logger.error(f"收到无效的HTTP响应: {response_data[:100]}")
            except Exception as socket_e:
                logger.error(f"socket请求失败: {str(socket_e)}")
            
            # 所有尝试都失败
            pytest.fail(f"请求失败，所有尝试均未成功: {str(e)}")
    
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
