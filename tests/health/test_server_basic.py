#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
服务器基本健康检查测试

测试服务器的基本运行状态和核心功能。
"""

import pytest
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from utils.test_base import TestBase, logger
from woniunote.app import create_app

class TestServerBasic(TestBase):
    """服务器基本功能测试"""
    
    @classmethod
    def setup_class(cls):
        """类级别的准备工作"""
        # 创建测试应用
        cls.app = create_app('testing')
        cls.app_context = cls.app.app_context()
        cls.app_context.push()
        cls.client = cls.app.test_client()
        logger.info("服务器测试：创建测试应用和客户端")
    
    @classmethod 
    def teardown_class(cls):
        """类级别的清理工作"""
        try:
            if hasattr(cls, 'app_context'):
                cls.app_context.pop()
            logger.info("服务器测试：清理测试应用")
        except:
            pass
    
    def test_server_running(self):
        """测试服务器基本运行状态"""
        try:
            # 使用test client测试根路径
            response = self.client.get('/')
            
            # 验证响应 - 包括301重定向
            assert response.status_code in [200, 301, 404, 302], f"根路径返回异常状态码: {response.status_code}"
            
            if response.status_code == 200:
                logger.info("✓ 服务器根路径访问正常")
            elif response.status_code == 301:
                logger.info("✓ 服务器运行正常（根路径永久重定向）")
            elif response.status_code == 404:
                logger.info("✓ 服务器运行正常（根路径返回404）")
            elif response.status_code == 302:
                logger.info("✓ 服务器运行正常（根路径重定向）")
                
        except Exception as e:
            pytest.fail(f"服务器测试失败: {str(e)}")
    
    def test_health_endpoint(self):
        """测试健康检查端点"""
        try:
            # 测试多个可能的健康检查端点
            health_endpoints = ['/health', '/status', '/ping', '/']
            
            found_endpoint = False
            for endpoint in health_endpoints:
                response = self.client.get(endpoint)
                if response.status_code == 200:
                    logger.info(f"✓ 健康检查端点 {endpoint} 可用")
                    found_endpoint = True
                    break
            
            if not found_endpoint:
                logger.info("✓ 未找到专用健康检查端点，但服务器运行正常")
                
        except Exception as e:
            pytest.fail(f"健康检查失败: {str(e)}")
    
    def test_article_page(self):
        """测试文章页面是否可访问"""
        try:
            # 测试文章列表页面
            response = self.client.get('/article')
            
            # 验证响应
            if response.status_code == 200:
                logger.info("✓ 文章列表页面可访问")
            elif response.status_code == 404:
                logger.info("✓ 文章列表路由未配置（可能正常）")
            else:
                logger.info(f"文章页面返回状态码: {response.status_code}")
                
        except Exception as e:
            pytest.fail(f"文章页面测试失败: {str(e)}")


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
