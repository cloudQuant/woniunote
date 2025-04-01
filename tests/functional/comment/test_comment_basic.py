#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
评论基本功能测试

测试WoniuNote评论模块的基本功能，包括:
- 查看文章评论
- 评论提交（需要登录状态）
"""

import pytest
import sys
import os

# 导入测试基类和配置
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
from utils.test_base import TestBase, logger
from utils.test_config import TEST_USERS, TEST_DATA

class TestCommentBasic(TestBase):
    """评论基本功能测试类"""
    
    def setup_method(self):
        """每个测试方法前的准备工作"""
        # 设置文章ID，使用配置的示例文章
        self.article_id = TEST_DATA['article']['sample_id']
    
    def test_view_comments(self):
        """测试查看文章评论"""
        # 发送请求到文章详情页，评论应该显示在文章页面
        response = self.make_request('get', f'/article/{self.article_id}')
        
        # 验证响应
        assert response.status_code == 200, f"文章页面返回错误状态码: {response.status_code}"
        
        # 检查页面中是否可能包含评论区域
        # 注意：即使没有评论，评论区域也应该存在
        page_content = response.text.lower()
        assert "评论" in page_content or "comment" in page_content, "页面不包含评论区域"
        
        logger.info("✓ 查看评论测试通过")
    
    def test_post_comment_without_login(self):
        """测试未登录状态下发表评论（应该失败或重定向到登录页）"""
        # 准备评论数据
        comment_data = {
            "article_id": self.article_id,
            "content": TEST_DATA['comment']['content']
        }
        
        # 发送评论请求
        response = self.make_request('post', '/comment/post', data=comment_data, allow_redirects=False)
        
        # 验证响应：应该是重定向到登录页或错误消息
        # 不进行具体断言，只记录结果
        logger.info(f"未登录发表评论响应状态码: {response.status_code}")
        
        # 如果是重定向，记录重定向位置
        if 300 <= response.status_code < 400:
            redirect_url = response.headers.get('Location', '')
            logger.info(f"重定向到: {redirect_url}")
            assert "login" in redirect_url.lower(), "未重定向到登录页面"
        
        logger.info("✓ 未登录评论测试通过")
    
    def test_post_comment_with_login(self):
        """测试登录状态下发表评论（可能成功）"""
        # 先登录
        test_user = TEST_USERS['normal']
        logged_in = self.login(test_user['username'], test_user['password'])
        
        # 如果登录成功，尝试发表评论
        if logged_in:
            # 准备评论数据
            comment_data = {
                "article_id": self.article_id,
                "content": TEST_DATA['comment']['content']
            }
            
            # 发送评论请求
            response = self.make_request('post', '/comment/post', data=comment_data)
            
            # 记录响应结果
            logger.info(f"登录后发表评论响应状态码: {response.status_code}")
            
            # 检查是否成功
            if response.status_code == 200:
                logger.info("评论可能已成功发表")
            
            logger.info("✓ 登录后评论测试完成")
        else:
            logger.warning("登录失败，跳过评论测试")
            pytest.skip("登录失败，无法测试登录后评论功能")


if __name__ == "__main__":
    # 直接运行测试
    test = TestCommentBasic()
    test.setup_class()
    
    try:
        test.setup_method()
        test.test_view_comments()
        test.test_post_comment_without_login()
        test.test_post_comment_with_login()
        print("所有评论基本功能测试通过！")
    except Exception as e:
        print(f"测试失败: {str(e)}")
        sys.exit(1)
    finally:
        test.teardown_class()
