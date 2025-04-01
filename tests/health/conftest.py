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
    服务器端口可能是5000或5001
    5000: 直接运行app.py时使用的端口
    5001: 测试框架使用的端口
    """
    return 5000  # 默认使用主应用端口

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
def ensure_server_ready(server_port):
    """确保服务器已准备好接受连接的辅助fixture"""
    max_retries = 10
    retry_delay = 1
    
    logger.info(f"等待服务器在端口 {server_port} 启动...")
    
    # 首先使用socket确认端口开放
    for i in range(max_retries):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('127.0.0.1', server_port))
            sock.close()
            
            if result == 0:
                logger.info(f"✓ 端口 {server_port} 已开放 (尝试 {i+1}/{max_retries})")
                time.sleep(1)  # 给一点额外时间让服务器完全初始化
                return
            else:
                logger.warning(f"✗ 端口 {server_port} 未开放 (尝试 {i+1}/{max_retries})")
        except Exception as e:
            logger.warning(f"检查端口时出错: {e}")
        
        # 如果未成功，等待后重试
        time.sleep(retry_delay)
    
    # 如果所有尝试都失败
    pytest.fail(f"服务器未在端口 {server_port} 启动")
