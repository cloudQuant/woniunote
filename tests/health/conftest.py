"""
专门为简单健康检查测试设计的conftest文件
避免与主conftest.py中的fixture冲突
"""

import pytest
import time
import logging
import socket

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("simple_test")

@pytest.fixture(scope="session")
def server_port():
    """
    服务器端口固定为5001
    5001是测试框架使用的标准端口
    """
    return 5001  # 使用测试框架标准端口

@pytest.fixture(scope="session")
def server_host():
    """服务器主机名固定为localhost"""
    return "127.0.0.1"  # 使用127.0.0.1代替localhost，避免潜在的DNS解析问题

@pytest.fixture(scope="session")
def base_url(server_host, server_port):
    """提供完整的服务器基础URL"""
    url = f"http://{server_host}:{server_port}"
    logger.info(f"测试使用基础URL: {url}")
    return url

@pytest.fixture(scope="session", autouse=True)
def ensure_server_ready():
    """确保测试环境已准备好的辅助fixture
    
    对于health测试，我们不需要真实的服务器，而是使用Flask test client
    """
    logger.info("健康测试使用Flask test client，无需外部服务器")
    yield
    logger.info("健康测试环境清理完成")
