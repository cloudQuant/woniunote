import pytest
from playwright.sync_api import expect

def test_login_page_elements(browser_context):
    """测试登录页面的基本元素是否存在"""
    page = browser_context
    page.goto("http://localhost:5000")
    
    # 检查登录按钮是否存在
    login_button = page.locator("text=登录")
    expect(login_button).to_be_visible()
    
    # 点击登录按钮，检查登录表单
    login_button.click()
    expect(page.locator("#username")).to_be_visible()
    expect(page.locator("#password")).to_be_visible()
    expect(page.locator("#vcode")).to_be_visible()

def test_login_success(app_client, test_user):
    """测试登录功能"""
    response = app_client.post('/login', data={
        'username': test_user['username'],
        'password': test_user['password'],
        'vcode': '0000'
    })
    assert response.status_code == 200
    assert response.data == b'login-pass'

def test_login_wrong_password(app_client, test_user):
    """测试错误密码登录"""
    response = app_client.post('/login', data={
        'username': test_user['username'],
        'password': 'wrongpass',
        'vcode': '0000'
    })
    assert response.status_code == 200
    assert response.data == b'login-fail'

def test_logout(authenticated_client):
    """测试登出功能"""
    response = authenticated_client.get('/logout')
    assert response.status_code == 302  # 重定向状态码
