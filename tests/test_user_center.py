import pytest
from playwright.sync_api import expect

def test_user_center_access(browser_context, authenticated_client):
    """测试用户中心访问权限"""
    page = browser_context
    page.goto("http://localhost:5000/ucenter")
    
    # 检查用户中心菜单是否显示
    menu = page.locator(".admin-side")
    expect(menu).to_be_visible()
    
    # 检查各个菜单项
    expect(page.locator("text=我的收藏")).to_be_visible()
    expect(page.locator("text=我的文章")).to_be_visible()
    expect(page.locator("text=我的评论")).to_be_visible()

def test_favorite_article(authenticated_client):
    """测试收藏文章功能"""
    # 收藏一篇文章
    response = authenticated_client.get('/user/favorite/1')
    assert response.status_code == 200
    
    # 检查收藏列表
    response = authenticated_client.get('/ucenter')
    assert response.status_code == 200
    assert b'取消收藏' in response.data

def test_user_profile(browser_context, authenticated_client):
    """测试用户资料页面"""
    page = browser_context
    page.goto("http://localhost:5000/user/info")
    
    # 检查个人资料表单
    expect(page.locator("#nickname")).to_be_visible()
    expect(page.locator("#email")).to_be_visible()
    
    # 测试更新资料
    page.locator("#nickname").fill("新昵称")
    page.locator("#email").fill("new@example.com")
    page.locator("text=保存修改").click()
    
    # 检查更新后的提示
    expect(page.locator("text=修改成功")).to_be_visible()

def test_user_comments(authenticated_client):
    """测试用户评论功能"""
    # 发表评论
    response = authenticated_client.post('/comment/create', data={
        'articleid': 1,
        'content': '测试评论'
    })
    assert response.status_code == 200
    
    # 检查评论列表
    response = authenticated_client.get('/user/comment')
    assert response.status_code == 200
    assert b'测试评论' in response.data
