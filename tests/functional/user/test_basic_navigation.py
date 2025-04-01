import pytest
from playwright.sync_api import expect
import os
import sys

# 添加项目根目录到Python路径
project_root = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
sys.path.insert(0, project_root)

# 导入Flask应用上下文提供者
from tests.utils.test_base import FlaskAppContextProvider

"""
基本导航测试
测试网站的主要页面是否可以正常访问
"""

@FlaskAppContextProvider.with_app_context
@pytest.mark.parametrize("browser_name", ["chromium"])
@pytest.mark.browser
def test_home_page_loads(page, base_url, browser_name):
    """测试首页是否能正常加载"""
    # 访问首页
    page.goto(base_url)
    
    # 验证页面标题
    expect(page).to_have_title("蜗牛笔记")
    
    # 验证关键元素存在
    expect(page.locator(".navbar")).to_be_visible()
    expect(page.locator("footer")).to_be_visible()

@FlaskAppContextProvider.with_app_context
@pytest.mark.parametrize("browser_name", ["chromium"])
@pytest.mark.browser
def test_login_page_loads(page, base_url, browser_name):
    """测试登录页是否能正常加载"""
    # 访问登录页
    page.goto(f"{base_url}/login")
    
    # 验证页面包含登录表单
    expect(page.locator("form")).to_be_visible()
    expect(page.locator("input[name='username']")).to_be_visible()
    expect(page.locator("input[name='password']")).to_be_visible()
    expect(page.locator("input[name='vcode']")).to_be_visible()

@FlaskAppContextProvider.with_app_context
@pytest.mark.parametrize("browser_name", ["chromium"])
@pytest.mark.browser
def test_register_page_loads(page, base_url, browser_name):
    """测试注册页是否能正常加载"""
    # 访问注册页
    page.goto(f"{base_url}/register")
    
    # 验证页面包含注册表单
    expect(page.locator("form")).to_be_visible()
    expect(page.locator("input[name='username']")).to_be_visible()
    expect(page.locator("input[name='password']")).to_be_visible()
    expect(page.locator("input[name='ecode']")).to_be_visible()

@FlaskAppContextProvider.with_app_context
@pytest.mark.parametrize("browser_name", ["chromium"])
@pytest.mark.browser
def test_article_list_loads(page, base_url, browser_name):
    """测试文章列表页是否能正常加载"""
    # 访问文章列表页
    page.goto(f"{base_url}/article")
    
    # 验证页面包含文章列表
    expect(page.locator(".article-list")).to_be_visible()

@FlaskAppContextProvider.with_app_context
@pytest.mark.parametrize("browser_name", ["chromium"])
@pytest.mark.browser
def test_article_detail_loads(page, base_url, browser_name):
    """测试文章详情页是否能正常加载"""
    # 访问文章详情页 - 假设ID为1的文章存在
    page.goto(f"{base_url}/article/1")
    
    # 验证页面包含文章内容
    expect(page.locator(".article-content")).to_be_visible()
    
    # 验证页面包含评论区
    expect(page.locator(".comment-area")).to_be_visible()
