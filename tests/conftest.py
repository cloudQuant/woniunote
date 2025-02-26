import os
import tempfile
import pytest
from woniunote import create_app
from woniunote.module.users import Users
from woniunote.module.articles import Articles
from woniunote.configs.config import config
from sqlalchemy import text

class TestConfig:
    TESTING = True
    SECRET_KEY = 'test_secret_key'
    DATABASE = None  # 将在fixture中设置
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = None  # 将在fixture中设置
    SESSION_COOKIE_SECURE = False  # 测试环境不需要安全cookie
    APPLICATION_ROOT = '/'  # 设置应用根路径
    PREFERRED_URL_SCHEME = 'http'  # 设置URL方案
    SERVER_NAME = None  # 确保不会重定向到其他域名
    FORCE_HTTPS = False  # 禁用HTTPS强制重定向
    
@pytest.fixture
def app():
    """Create and configure a new app instance for each test."""
    # Create a temporary file to isolate the database for each test
    db_fd, db_path = tempfile.mkstemp()
    
    # 设置测试配置
    TestConfig.DATABASE = db_path
    TestConfig.SQLALCHEMY_DATABASE_URI = f'sqlite:///{db_path}'
    
    app = create_app('testing')
    app.config.from_object(TestConfig)
    
    # 禁用 CSRF 保护，方便测试
    app.config['WTF_CSRF_ENABLED'] = False
    
    # 确保使用测试模式
    app.config['TESTING'] = True

    # Initialize the database
    with app.app_context():
        # 创建测试用户
        user = Users()
        test_user = user.do_register('yunjinqi@qq.com', 'yunjinqi2015')
        
        # 将用户角色更新为editor
        from woniunote.common.database import dbconnect
        dbsession, _, _ = dbconnect()
        dbsession.execute(text("UPDATE users SET role = 'editor' WHERE userid = :userid"), {'userid': test_user.userid})
        dbsession.commit()

    yield app

    # Clean up the temporary files
    os.close(db_fd)
    os.unlink(db_path)

@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()

@pytest.fixture
def runner(app):
    """A test CLI runner for the app's Click commands."""
    return app.test_cli_runner()

@pytest.fixture
def test_article_data():
    """Create test article data."""
    return {
        'headline': 'Test Article',
        'content': 'This is a test article content.',
        'type': 1,  # original
        'credit': 10,
        'drafted': 0,
        'checked': 1,
        'articleid': 0
    }

@pytest.fixture
def auth_client(app):
    """A test client with authentication helpers."""
    client = app.test_client()
    
    # Create a test user
    test_user = {
        'username': 'yunjinqi@qq.com',
        'password': 'yunjinqi2015',
        'nickname': 'yunjinqi'
    }

    def login(username='yunjinqi@qq.com', password='yunjinqi2015'):
        # 先获取验证码
        client.get('/vcode')
        with client.session_transaction() as sess:
            sess['vcode'] = '0000'
            
        return client.post('/login', data={
            'username': username,
            'password': password,
            'vcode': '0000'
        }, follow_redirects=True)

    def logout():
        return client.get('/logout', follow_redirects=True)

    # 自动登录
    login()

    # Store the helpers and test user data
    return {
        'client': client,
        'login': login,
        'logout': logout,
        'test_user': test_user
    }

@pytest.fixture
def test_user():
    """Create a test user for authentication tests."""
    return {
        'username': 'yunjinqi@qq.com',
        'password': 'yunjinqi2015',
        'nickname': 'yunjinqi'
    }
