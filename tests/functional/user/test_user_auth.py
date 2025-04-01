#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
WoniuNote用户认证测试

测试用户登录、注册等功能。
"""

import pytest
import time
import re
import os
import sys
from playwright.sync_api import expect

# 添加项目根目录到Python路径
project_root = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
sys.path.insert(0, project_root)

# 导入Flask应用上下文提供者
from tests.utils.test_base import FlaskAppContextProvider, logger

# 使用装饰器确保在Flask应用上下文中运行
@FlaskAppContextProvider.with_app_context
@pytest.mark.parametrize("browser_name", ["chromium"])
@pytest.mark.browser
def test_login_page_access(page, base_url, browser_name):
    """测试登录页面访问"""
    logger.info("===== 测试登录页面访问 =====")
    
    # 访问登录页
    page.goto(f"{base_url}/login")
    
    # 验证页面标题
    expect(page).to_have_title("蜗牛笔记 - 登录")
    
    # 验证表单元素存在
    expect(page.locator("form")).to_be_visible()
    expect(page.locator("input[name='username']")).to_be_visible()
    expect(page.locator("input[name='password']")).to_be_visible()
    
    logger.info("✓ 登录页面访问测试通过")

@FlaskAppContextProvider.with_app_context
@pytest.mark.parametrize("browser_name", ["chromium"])
@pytest.mark.browser
def test_login_with_valid_credentials(page, base_url, browser_name):
    """测试使用有效凭据登录"""
    logger.info("===== 测试使用有效凭据登录 =====")
    
    try:
        # 访问登录页
        page.goto(f"{base_url}/login")
        
        # 获取验证码
        page.goto(f"{base_url}/vcode")
        
        # 返回登录页
        page.goto(f"{base_url}/login")
        
        # 填写表单
        page.fill('input[name="username"]', "administrator")
        page.fill('input[name="password"]', "admin123")
        page.fill('input[name="vcode"]', "1234")  # 假设的验证码
        
        # 提交表单
        page.click('button[type="submit"]')
        
        # 验证登录成功
        page.wait_for_url(f"{base_url}/")
        
        # 检查用户信息元素
        user_info = page.locator(".user-info")
        if user_info.count() > 0:
            expect(user_info).to_contain_text("administrator")
            logger.info("✓ 使用有效凭据登录测试通过")
        else:
            logger.warning("⚠ 找不到用户信息元素，但重定向到首页成功")
    
    except Exception as e:
        logger.error(f"登录测试失败: {e}")
        raise

@FlaskAppContextProvider.with_app_context
@pytest.mark.parametrize("browser_name", ["chromium"])
@pytest.mark.browser
def test_register_page_access(page, base_url, browser_name):
    """测试注册页面访问"""
    logger.info("===== 测试注册页面访问 =====")
    
    # 访问注册页
    page.goto(f"{base_url}/register")
    
    # 验证页面标题
    expect(page).to_have_title("蜗牛笔记 - 注册")
    
    # 验证表单元素存在
    expect(page.locator("form")).to_be_visible()
    expect(page.locator("input[name='email']")).to_be_visible()
    expect(page.locator("input[name='username']")).to_be_visible()
    expect(page.locator("input[name='password']")).to_be_visible()
    
    logger.info("✓ 注册页面访问测试通过")

# 只在需要执行测试时取消注释这些测试
"""
@FlaskAppContextProvider.with_app_context
@pytest.mark.parametrize("browser_name", ["chromium"])
def test_login_with_invalid_credentials(page, base_url, browser_name):
    # 测试使用无效凭据登录
    pass

@FlaskAppContextProvider.with_app_context
@pytest.mark.parametrize("browser_name", ["chromium"])
def test_registration_with_valid_data(page, base_url, browser_name):
    # 测试使用有效数据注册
    pass

@FlaskAppContextProvider.with_app_context
@pytest.mark.parametrize("browser_name", ["chromium"])
def test_logout(page, base_url, browser_name):
    # 测试登出功能
    pass

@FlaskAppContextProvider.with_app_context
@pytest.mark.parametrize("browser_name", ["chromium"])
def test_invalid_verification_code(page, base_url, browser_name):
    # 测试使用无效验证码登录
    pass
"""

if __name__ == "__main__":
    print("手动运行用户认证测试...")
