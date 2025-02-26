import os
import pytest
from playwright.sync_api import sync_playwright
from woniunote import app

@pytest.fixture(scope="session")
def app_client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

@pytest.fixture(scope="session")
def browser_context():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        yield page
        context.close()
        browser.close()

@pytest.fixture
def test_user():
    return {
        'username': 'testuser',
        'password': 'testpass123',
        'email': 'test@example.com'
    }

@pytest.fixture
def authenticated_client(app_client, test_user):
    # 登录用户
    response = app_client.post('/login', data={
        'username': test_user['username'],
        'password': test_user['password'],
        'vcode': '0000'  # 测试环境验证码
    })
    assert response.status_code == 200
    return app_client
