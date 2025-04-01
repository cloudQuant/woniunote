#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
WoniuNote简单服务器测试

此文件包含一个极简的测试，用于验证Flask服务器是否正确启动和响应。
不依赖于Flask应用的/health端点，而是直接测试主页。
"""

import os
import sys
import pytest
import requests
import logging
import urllib3
import time

# 添加项目根目录到Python路径
project_root = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, project_root)

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("server_test")

# 禁用不安全连接警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 硬编码URL，不依赖fixture
BASE_URL = "https://127.0.0.1:5000"  # 使用HTTPS而不是HTTP
ARTICLE_URL = f"{BASE_URL}/article/398"  # 用户提供的测试文章URL

def test_server_running():
    """
    测试服务器是否正在运行
    
    这个测试验证WoniuNote服务器是否正在运行，并能响应请求。
    """
    logger.info(f"测试服务器主页: {BASE_URL}")
    
    # 等待服务器启动
    time.sleep(1)
    
    try:
        # 创建会话，禁用证书验证
        session = requests.Session()
        session.verify = False
        
        # 发送请求到主页
        logger.info(f"发送请求到: {BASE_URL}")
        response = session.get(BASE_URL, timeout=5, verify=False)
        logger.info(f"主页响应: 状态码={response.status_code}")
        
        # 验证响应
        assert response.status_code == 200, f"主页返回错误状态码: {response.status_code}"
        
        # 检查内容类型
        content_type = response.headers.get("Content-Type", "")
        logger.info(f"响应内容类型: {content_type}")
        assert "text/html" in content_type, f"响应内容类型不是HTML: {content_type}"
        
        # 检查响应正文长度
        content_length = len(response.text)
        logger.info(f"响应内容长度: {content_length} 字节")
        assert content_length > 0, "响应内容为空"
        
        logger.info("✓ 服务器运行检查通过")
    except requests.exceptions.RequestException as e:
        logger.error(f"请求主页时出错: {str(e)}")
        logger.error(f"尝试检查服务器是否在端口5000上运行")
        pytest.fail(f"请求主页时出错: {str(e)}")

def test_article_page():
    """
    测试文章页面
    
    这个测试验证服务器是否能够显示特定的文章页面。
    """
    logger.info(f"测试文章URL: {ARTICLE_URL}")
    
    try:
        # 创建会话，禁用证书验证
        session = requests.Session()
        session.verify = False
        
        # 发送请求到文章页面
        logger.info(f"发送请求到: {ARTICLE_URL}")
        response = session.get(ARTICLE_URL, timeout=5, verify=False)
        logger.info(f"文章页面响应: 状态码={response.status_code}")
        
        # 验证响应
        assert response.status_code == 200, f"文章页面返回错误状态码: {response.status_code}"
        
        # 检查内容类型
        content_type = response.headers.get("Content-Type", "")
        logger.info(f"响应内容类型: {content_type}")
        assert "text/html" in content_type, f"响应内容类型不是HTML: {content_type}"
        
        # 检查是否包含文章内容的标记
        assert "article" in response.text.lower(), "响应不包含文章相关内容"
        
        logger.info("✓ 文章页面检查通过")
    except requests.exceptions.RequestException as e:
        logger.error(f"请求文章页面时出错: {str(e)}")
        pytest.fail(f"请求文章页面时出错: {str(e)}")

# 如果直接运行此文件，而不是通过pytest
if __name__ == "__main__":
    print(f"正在测试WoniuNote服务器: {BASE_URL}")
    try:
        test_server_running()
        test_article_page()
        print("所有测试通过！")
    except Exception as e:
        print(f"测试失败: {str(e)}")
        sys.exit(1)
