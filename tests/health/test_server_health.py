#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
WoniuNote简单服务器测试

此文件包含一个极简的测试，用于验证Flask服务器是否正确启动和响应。
仅测试服务器是否在响应基本请求，不涉及特定功能。
"""

import os
import sys
import pytest
import requests
import logging
import urllib3
import time
import socket

# 添加项目根目录到Python路径
project_root = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
sys.path.insert(0, project_root)

# 导入测试配置
from tests.utils.test_config import SERVER_CONFIG

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("server_test")

# 禁用不安全连接警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 从配置获取端口和主机
SERVER_HOST = SERVER_CONFIG['host']
SERVER_PORT = SERVER_CONFIG['port']

# 定义可能的基础URL (先尝试HTTP，再尝试HTTPS)
HTTP_URL = f"http://{SERVER_HOST}:{SERVER_PORT}"
HTTPS_URL = f"https://{SERVER_HOST}:{SERVER_PORT}"

logger.info(f"测试服务器主机: {SERVER_HOST}")
logger.info(f"测试服务器端口: {SERVER_PORT}")

@pytest.mark.unit
def test_server_running():
    """
    测试服务器是否正在运行
    
    这个测试验证WoniuNote服务器是否正在运行，并能响应请求。
    使用更加宽松的验证方式，只要能检测到服务器在指定端口运行就通过。
    """
    # 首先尝试使用socket检查端口是否打开
    socket_check_passed = check_port_open(SERVER_HOST, SERVER_PORT)
    if socket_check_passed:
        logger.info(f"✓ 检测到服务器在 {SERVER_HOST}:{SERVER_PORT} 上运行")
        return
    
    # 如果端口检查失败，尝试HTTP请求
    if try_http_request():
        return
    
    # 所有尝试都失败，测试不通过
    pytest.fail(f"无法检测到服务器在 {SERVER_HOST}:{SERVER_PORT} 上运行")

def check_port_open(host, port, timeout=2):
    """使用socket检查端口是否开放"""
    try:
        logger.info(f"使用socket检查端口 {host}:{port} 是否开放...")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        
        if result == 0:
            logger.info(f"✓ 端口 {port} 已开放")
            return True
        else:
            logger.warning(f"端口 {port} 未开放，错误码: {result}")
            return False
    except Exception as e:
        logger.error(f"检查端口时出错: {e}")
        return False

def try_http_request():
    """尝试HTTP/HTTPS请求"""
    # 增加最大重试次数和延迟，但设置较大的间隔
    max_retries = 3
    delay_seconds = 5
    
    # 构建请求头
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Connection': 'keep-alive',
    }
    
    # 按协议优先级依次尝试
    urls_to_try = [(HTTP_URL, "HTTP"), (HTTPS_URL, "HTTPS")]
    
    for base_url, protocol in urls_to_try:
        for attempt in range(max_retries):
            try:
                logger.info(f"尝试通过{protocol}连接服务器 (尝试 {attempt+1}/{max_retries})...")
                
                # 等待一段时间再重试
                if attempt > 0:
                    logger.info(f"等待 {delay_seconds} 秒后重试...")
                    time.sleep(delay_seconds)
                
                # 创建会话并设置较长的超时
                session = requests.Session()
                session.verify = False  # 禁用HTTPS验证
                
                # 尝试连接服务器根路径
                logger.info(f"发送请求到: {base_url}")
                response = session.get(
                    base_url, 
                    timeout=10,
                    headers=headers,
                    verify=False
                )
                
                # 记录状态码
                status_code = response.status_code
                logger.info(f"服务器响应: 状态码={status_code}")
                
                # 任何返回都视为成功
                logger.info(f"✓ 服务器通过{protocol}健康检查通过 (状态码: {status_code})")
                return True
                
            except requests.exceptions.SSLError as e:
                logger.warning(f"{protocol}连接失败 (SSL错误): {e}")
                # SSL错误时，如果是HTTPS，尝试HTTP；如果是HTTP，可能服务器真的需要HTTPS
                break  # 跳出当前协议的尝试，尝试下一个协议
                
            except requests.exceptions.ConnectionError as e:
                logger.warning(f"{protocol}连接失败 (连接错误): {e}")
                # 连接错误，服务器可能未就绪，继续下一次尝试
                
            except requests.exceptions.RequestException as e:
                logger.warning(f"{protocol}连接失败 (请求错误): {e}")
                
    # 所有尝试都失败
    logger.error("所有HTTP/HTTPS连接尝试均失败")
    return False

# 如果直接运行此文件，而不是通过pytest
if __name__ == "__main__":
    print(f"正在测试WoniuNote服务器: {SERVER_HOST}:{SERVER_PORT}")
    try:
        test_server_running()
        print("服务器健康检查通过！")
    except Exception as e:
        print(f"测试失败: {str(e)}")
        sys.exit(1)
