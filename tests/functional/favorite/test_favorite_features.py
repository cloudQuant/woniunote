import pytest
from playwright.sync_api import expect
import time
import sys
import os

# 添加项目根目录到Python路径
project_root = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
sys.path.insert(0, project_root)

# 导入Flask应用上下文提供者
from tests.utils.test_base import FlaskAppContextProvider

# 创建app_context fixture
app_context = FlaskAppContextProvider.with_app_context_fixture()

"""
收藏功能测试
测试用户对文章的收藏和取消收藏功能
"""

# 确保在Flask应用上下文中运行
@pytest.mark.browser
def test_favorite_article(app_context, authenticated_page, base_url, browser_name):
    """测试收藏文章功能"""
    page = authenticated_page
    
    # 访问一篇文章
    page.goto(f"{base_url}/article/1")
    
    # 检查当前收藏状态
    favorite_button = page.locator(".favorite-button")
    
    # 如果已经收藏，先取消收藏
    if "已收藏" in favorite_button.inner_text():
        favorite_button.click()
        page.wait_for_load_state("networkidle")
    
    # 现在点击收藏按钮
    favorite_button.click()
    
    # 等待请求完成
    page.wait_for_load_state("networkidle")
    
    # 验证按钮文本变为"已收藏"
    expect(favorite_button).to_contain_text("已收藏")

# 确保在Flask应用上下文中运行
@pytest.mark.browser
def test_unfavorite_article(app_context, authenticated_page, base_url, browser_name):
    """测试取消收藏文章功能"""
    page = authenticated_page
    
    # 访问一篇文章
    page.goto(f"{base_url}/article/1")
    
    # 检查当前收藏状态
    favorite_button = page.locator(".favorite-button")
    
    # 如果未收藏，先收藏
    if "收藏" in favorite_button.inner_text() and "已收藏" not in favorite_button.inner_text():
        favorite_button.click()
        page.wait_for_load_state("networkidle")
    
    # 现在点击取消收藏
    favorite_button.click()
    
    # 等待请求完成
    page.wait_for_load_state("networkidle")
    
    # 验证按钮文本变为"收藏"
    expect(favorite_button).to_contain_text("收藏")
    expect(favorite_button).not_to_contain_text("已收藏")

# 确保在Flask应用上下文中运行
@pytest.mark.browser
def test_view_favorite_list(app_context, authenticated_page, base_url, browser_name):
    """测试查看收藏列表"""
    page = authenticated_page
    
    # 访问收藏列表页面
    page.goto(f"{base_url}/favorite")
    
    # 验证收藏列表页面加载
    expect(page.locator(".favorite-list")).to_be_visible()
    
    # 验证页面标题包含"我的收藏"
    expect(page.locator("h1, h2, h3")).to_contain_text("收藏")
    
    # 如果列表为空，检查是否有提示
    if page.locator(".favorite-item").count() == 0:
        expect(page.locator(".empty-message")).to_be_visible()
    else:
        # 否则检查收藏项目显示
        expect(page.locator(".favorite-item")).to_be_visible()

# 确保在Flask应用上下文中运行
@pytest.mark.browser
def test_favorite_from_list_to_detail(app_context, authenticated_page, base_url, browser_name):
    """测试从收藏列表访问文章详情"""
    page = authenticated_page
    
    # 访问收藏列表
    page.goto(f"{base_url}/favorite")
    
    # 如果有收藏项目，点击第一个
    if page.locator(".favorite-item").count() > 0:
        first_item_title = page.locator(".favorite-item .article-title").first.inner_text()
        page.locator(".favorite-item .article-title a").first.click()
        
        # 验证跳转到文章详情页
        expect(page.url).to_match(r"/article/\d+")
        
        # 验证文章标题与收藏列表中的标题一致
        expect(page.locator("h1.article-title")).to_contain_text(first_item_title)
    else:
        # 如果没有收藏项目，直接通过
        print("No favorites found, skipping test")
        pytest.skip("No favorites found to test navigation")
