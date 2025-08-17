#!/usr/bin/env python3
"""
WoniuNote 统一测试配置
提供全局测试fixtures和配置
"""
import os
import sys
import pytest
import tempfile
import shutil
from unittest.mock import Mock, patch

# 添加项目根目录到Python路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 测试环境配置
TEST_ENV_CONFIG = {
    'FLASK_ENV': 'testing',
    'TESTING': 'True',
    'SECRET_KEY': 'TestSecret123KEY456ForTestingOnly',
    'DATABASE_URL': 'sqlite:///:memory:',
    'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
    'WTF_CSRF_ENABLED': 'False',
    'SQLALCHEMY_TRACK_MODIFICATIONS': 'False',
    'DISABLE_DATABASE_POOL_OPTIMIZER': 'True',
    'DISABLE_PERFORMANCE_MONITOR': 'True',
    'DISABLE_REDIS': 'True',
    'DISABLE_CONFIG_VALIDATION': 'True',
    'DISABLE_ENVIRONMENT_VALIDATION': 'True',
    'SKIP_APP_INIT': 'True',
}


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """设置全局测试环境"""
    # 保存原始环境变量
    original_env = {}
    for key, value in TEST_ENV_CONFIG.items():
        original_env[key] = os.environ.get(key)
        os.environ[key] = value
    
    # 阻止Flask应用初始化
    try:
        import woniunote.app
        woniunote.app.app = None
    except ImportError:
        pass
    
    yield
    
    # 恢复原始环境变量
    for key, original_value in original_env.items():
        if original_value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = original_value


@pytest.fixture
def temp_directory():
    """创建临时目录"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def mock_redis():
    """模拟Redis连接"""
    with patch('woniunote.common.cache_utils.redis') as mock:
        mock_redis_instance = Mock()
        mock_redis_instance.get.return_value = None
        mock_redis_instance.set.return_value = True
        mock_redis_instance.delete.return_value = True
        mock_redis_instance.ping.return_value = True
        mock.Redis.return_value = mock_redis_instance
        yield mock_redis_instance


@pytest.fixture
def mock_database():
    """模拟数据库连接"""
    with patch('woniunote.common.database.db') as mock_db:
        mock_db.session = Mock()
        mock_db.create_all = Mock()
        mock_db.drop_all = Mock()
        yield mock_db


@pytest.fixture
def sample_user_data():
    """测试用户数据"""
    return {
        'username': 'testuser',
        'email': 'test@example.com',
        'password': 'TestPass123!',
        'display_name': 'Test User'
    }


@pytest.fixture
def sample_article_data():
    """测试文章数据"""
    return {
        'title': 'Test Article',
        'content': 'This is a test article content.',
        'summary': 'Test article summary',
        'category': 'test',
        'tags': 'test,article'
    }


@pytest.fixture
def sample_comment_data():
    """测试评论数据"""
    return {
        'content': 'This is a test comment.',
        'author': 'testuser',
        'article_id': 1
    }


class TestHelper:
    """测试辅助类"""
    
    @staticmethod
    def assert_valid_email(email):
        """断言邮箱格式有效"""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        assert re.match(pattern, email), f"Invalid email format: {email}"
    
    @staticmethod
    def assert_secure_password(password):
        """断言密码安全性"""
        assert len(password) >= 8, "Password too short"
        assert any(c.isupper() for c in password), "Password needs uppercase"
        assert any(c.islower() for c in password), "Password needs lowercase"
        assert any(c.isdigit() for c in password), "Password needs digit"
    
    @staticmethod
    def create_mock_request(method='GET', path='/', **kwargs):
        """创建模拟请求对象"""
        from werkzeug.test import EnvironBuilder
        from werkzeug.wrappers import Request
        
        builder = EnvironBuilder(method=method, path=path, **kwargs)
        env = builder.get_environ()
        return Request(env)


@pytest.fixture
def test_helper():
    """测试辅助工具"""
    return TestHelper


def pytest_configure(config):
    """pytest配置"""
    # 添加自定义标记
    config.addinivalue_line(
        "markers", "unit: mark test as unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "performance: mark test as performance test"
    )
    config.addinivalue_line(
        "markers", "security: mark test as security test"
    )


def pytest_collection_modifyitems(config, items):
    """修改测试收集"""
    for item in items:
        # 为所有测试添加默认标记
        if "unit" not in item.keywords:
            item.add_marker(pytest.mark.unit)


# 全局测试常量
TEST_CONSTANTS = {
    'VALID_EMAILS': [
        'test@example.com',
        'user.name@domain.co.uk',
        'firstname.lastname@company.com'
    ],
    'INVALID_EMAILS': [
        '',
        'invalid_email',
        '@domain.com',
        'user@',
        'user@@domain.com'
    ],
    'VALID_PASSWORDS': [
        'TestPass123!',
        'SecureP@ssw0rd',
        'MyStr0ng#Password'
    ],
    'WEAK_PASSWORDS': [
        '123',
        'password',
        'abc123'
    ],
    'XSS_PAYLOADS': [
        '<script>alert("xss")</script>',
        '<img src=x onerror=alert("xss")>',
        'javascript:alert("xss")',
        '<svg onload=alert("xss")>'
    ]
}