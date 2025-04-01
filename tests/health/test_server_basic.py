#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
WoniuNote服务器基本健康测试

此文件包含测试以验证WoniuNote服务器是否正确启动和响应基本请求。
"""

import pytest
import sys
import os
import time

# 导入测试基类
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))
from utils.test_base import TestBase, logger

@pytest.mark.unit
class TestServerBasic(TestBase):
    """服务器基本功能测试"""
    
    def test_server_running(self):
        """
        测试服务器是否正在运行
        
        这个测试验证WoniuNote服务器是否正在运行，并能响应请求。
        """
        # 等待服务器启动，尝试多个健康检查端点
        health_endpoints = ['/health', '/test-health']
        server_running = False
        
        for endpoint in health_endpoints:
            try:
                response = self.make_request('get', endpoint)
                if response.status_code == 200:
                    logger.info(f"服务器健康检查通过，使用端点: {endpoint}")
                    server_running = True
                    break
            except Exception as e:
                logger.warning(f"端点 {endpoint} 检查失败: {e}")
        
        assert server_running, "所有健康检查端点均失败，服务器可能未正常运行"
        
        # 发送请求到主页
        response = self.make_request('get', '/')
        
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
    
    def test_health_endpoint(self):
        """
        测试健康检查端点 (如果存在)
        
        WoniuNote现在在app.py中添加了/health端点，此测试验证该端点是否正常工作。
        """
        # 发送请求到健康检查端点
        response = self.make_request('get', '/health')
        
        # 验证响应
        assert response.status_code == 200, f"健康检查返回错误状态码: {response.status_code}"
        
        # 检查响应内容
        try:
            data = response.json()
            logger.info(f"响应内容: {data}")
            assert "status" in data, "健康检查响应缺少状态信息"
            assert data["status"] == "ok", f"健康检查状态不正确: {data}"
            logger.info("✓ 健康检查JSON响应验证通过")
        except ValueError:
            logger.error(f"无法解析JSON响应: {response.text[:100]}...")
            pytest.fail(f"健康检查端点返回无效JSON: {response.text[:100]}...")
        
        logger.info("✓ 健康检查端点测试通过")
    
    def test_article_page(self):
        """
        测试文章页面
        
        这个测试验证服务器是否能够显示特定的文章页面。
        """
        # 特定文章ID
        article_id = 398  # 可以配置为更通用的测试ID
        
        # 发送请求到文章页面
        response = self.make_request('get', f'/article/{article_id}')
        
        # 验证响应
        assert response.status_code == 200, f"文章页面返回错误状态码: {response.status_code}"
        
        # 检查内容类型
        content_type = response.headers.get("Content-Type", "")
        logger.info(f"响应内容类型: {content_type}")
        assert "text/html" in content_type, f"响应内容类型不是HTML: {content_type}"
        
        # 检查是否包含文章相关内容
        assert "article" in response.text.lower(), "响应不包含文章相关内容"
        
        logger.info("✓ 文章页面检查通过")


if __name__ == "__main__":
    # 如果直接运行此文件，而不是通过pytest
    print(f"正在测试WoniuNote服务器基本功能...")
    
    # 创建测试实例
    test = TestServerBasic()
    test.setup_class()
    
    try:
        # 运行测试
        test.test_server_running()
        test.test_health_endpoint()
        test.test_article_page()
        print("所有测试通过！")
    except Exception as e:
        print(f"测试失败: {str(e)}")
        sys.exit(1)
    finally:
        # 清理资源
        test.teardown_class()
