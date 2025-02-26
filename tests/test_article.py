import pytest
from playwright.sync_api import expect

def test_article_list(browser_context):
    """测试文章列表页面"""
    page = browser_context
    page.goto("http://localhost:5000")
    
    # 检查文章列表是否显示
    article_list = page.locator(".article-list")
    expect(article_list).to_be_visible()
    
    # 检查是否有文章标题
    article_titles = page.locator(".article-title")
    expect(article_titles).to_have_count(True)

def test_article_detail(browser_context):
    """测试文章详情页面"""
    page = browser_context
    # 假设有一个ID为1的文章
    page.goto("http://localhost:5000/article/1")
    
    # 检查文章标题和内容是否显示
    expect(page.locator(".article-title")).to_be_visible()
    expect(page.locator(".article-content")).to_be_visible()
    
    # 检查评论区是否存在
    expect(page.locator("#comment-section")).to_be_visible()

@pytest.mark.asyncio
async def test_article_api(app_client):
    """测试文章相关的API"""
    # 获取文章列表
    response = await app_client.get('/api/articles')
    assert response.status_code == 200
    
    # 获取单个文章
    response = await app_client.get('/api/article/1')
    assert response.status_code == 200

def test_article_search(browser_context):
    """测试文章搜索功能"""
    page = browser_context
    page.goto("http://localhost:5000")
    
    # 输入搜索关键词
    search_input = page.locator("#search-input")
    search_input.fill("测试")
    page.keyboard.press("Enter")
    
    # 检查搜索结果
    search_results = page.locator(".search-results")
    expect(search_results).to_be_visible()
