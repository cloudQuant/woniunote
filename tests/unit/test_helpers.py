#!/usr/bin/env python3
"""
测试辅助工具模块
提供测试常用的工具函数和类
"""

# 确保项目根目录在Python路径中
import sys
import os
import subprocess

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 设置测试环境
os.environ['TESTING'] = 'True'
os.environ['FLASK_ENV'] = 'testing'

import os
import sys
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import Mock, patch

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from woniunote.common.unified_logging import get_simple_logger
except ImportError:
    # Fallback for test environment
    import logging
    def get_simple_logger(name):
        return logging.getLogger(name)

logger = get_simple_logger('test_helpers')

class TestDatabaseHelper:
    """测试数据库辅助类"""
    
    @staticmethod
    def create_test_database_uri():
        """创建测试数据库URI"""
        return 'sqlite:///:memory:'
    
    @staticmethod
    def setup_test_tables():
        """设置测试表"""
        from woniunote.common.database import db
        db.create_all()
    
    @staticmethod
    def cleanup_test_data():
        """清理测试数据"""
        from woniunote.common.database import db
        db.drop_all()

class TestUserHelper:
    """测试用户辅助类"""
    
    @staticmethod
    def create_test_user(username: str = None, password: str = "test123", 
                        nickname: str = None, role: str = "user"):
        """创建测试用户"""
        username = username or f"test_user_{uuid.uuid4().hex[:8]}"
        nickname = nickname or f"Test User {username}"
        
        return {
            'username': username,
            'password': password,
            'nickname': nickname,
            'role': role,
            'userid': None  # 将在注册后设置
        }
    
    @staticmethod
    def create_admin_user():
        """创建管理员用户"""
        return TestUserHelper.create_test_user(
            username="test_admin",
            password="admin123",
            nickname="Test Admin",
            role="admin"
        )

class TestSessionHelper:
    """测试会话辅助类"""
    
    @staticmethod
    def create_mock_session(user_data: Dict[str, Any] = None):
        """创建模拟会话"""
        session_mock = Mock()
        
        if user_data:
            session_mock.get.side_effect = lambda key, default=None: {
                'islogin': 'true',
                'userid': user_data.get('userid', 1),
                'username': user_data.get('username', 'test_user'),
                'nickname': user_data.get('nickname', 'Test User'),
                'role': user_data.get('role', 'user')
            }.get(key, default)
        else:
            session_mock.get.return_value = None
        
        return session_mock
    
    @staticmethod
    def login_user(client, username: str, password: str):
        """模拟用户登录"""
        return client.post('/user/login', data={
            'username': username,
            'password': password,
            'vcode': 'test'  # 测试验证码
        })

class TestArticleHelper:
    """测试文章辅助类"""
    
    @staticmethod
    def create_test_article(title: str = None, content: str = None, 
                           userid: int = 1, article_type: int = 1):
        """创建测试文章"""
        title = title or f"Test Article {uuid.uuid4().hex[:8]}"
        content = content or f"This is test content for {title}"
        
        return {
            'title': title,
            'content': content,
            'userid': userid,
            'article_type': article_type,
            'readcount': 0,
            'replycount': 0,
            'createtime': time.time()
        }

class TestConfigHelper:
    """测试配置辅助类"""
    
    @staticmethod
    def create_test_config():
        """创建测试配置"""
        return {
            'TESTING': True,
            'WTF_CSRF_ENABLED': False,
            'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
            'SQLALCHEMY_TRACK_MODIFICATIONS': False,
            'SECRET_KEY': 'test-secret-key'
        }
    
    @staticmethod
    def setup_test_environment():
        """设置测试环境变量"""
        os.environ['FLASK_ENV'] = 'testing'
        os.environ['DATABASE_URL'] = 'sqlite:///:memory:'

class TestFileHelper:
    """测试文件辅助类"""
    
    @staticmethod
    def create_temp_file(content: str = "test content", suffix: str = ".txt"):
        """创建临时文件"""
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix=suffix, delete=False)
        temp_file.write(content)
        temp_file.close()
        return temp_file.name
    
    @staticmethod
    def create_test_image():
        """创建测试图片文件"""
        try:
            from PIL import Image
            import io
            
            # 创建一个简单的测试图片
            img = Image.new('RGB', (100, 100), color='red')
            img_bytes = io.BytesIO()
            img.save(img_bytes, format='JPEG')
            img_bytes.seek(0)
            return img_bytes
        except ImportError:
            # 如果没有PIL，创建一个假的图片字节流
            return io.BytesIO(b'fake image data')

class TestDataValidator:
    """测试数据验证助手"""
    
    @staticmethod
    def validate_user_data(user_data: Dict[str, Any]) -> bool:
        """验证用户数据格式"""
        required_fields = ['username', 'password']
        return all(field in user_data for field in required_fields)
    
    @staticmethod
    def validate_article_data(article_data: Dict[str, Any]) -> bool:
        """验证文章数据格式"""
        required_fields = ['title', 'content', 'userid']
        return all(field in article_data for field in required_fields)

class TestResponseHelper:
    """测试响应辅助类"""
    
    @staticmethod
    def assert_json_response(response, expected_data: Dict[str, Any] = None):
        """断言JSON响应"""
        assert response.content_type == 'application/json'
        
        if expected_data:
            json_data = response.get_json()
            for key, value in expected_data.items():
                assert json_data.get(key) == value
    
    @staticmethod
    def assert_success_response(response):
        """断言成功响应"""
        assert response.status_code == 200
    
    @staticmethod
    def assert_error_response(response, status_code: int = 400):
        """断言错误响应"""
        assert response.status_code == status_code

class TestMockHelper:
    """测试模拟辅助类"""
    
    @staticmethod
    def mock_redis():
        """模拟Redis连接"""
        redis_mock = Mock()
        redis_mock.get.return_value = None
        redis_mock.set.return_value = True
        redis_mock.delete.return_value = 1
        redis_mock.exists.return_value = False
        return redis_mock
    
    @staticmethod
    def mock_email_service():
        """模拟邮件服务"""
        with patch('woniunote.common.utils.send_email') as mock_send:
            mock_send.return_value = True
            yield mock_send
    
    @staticmethod
    def mock_database_error():
        """模拟数据库错误"""
        from sqlalchemy.exc import SQLAlchemyError
        return SQLAlchemyError("Mock database error")

class TestCleanupHelper:
    """测试清理辅助类"""
    
    def __init__(self):
        self.temp_files = []
        self.temp_dirs = []
    
    def add_temp_file(self, filepath: str):
        """添加临时文件到清理列表"""
        self.temp_files.append(filepath)
    
    def add_temp_dir(self, dirpath: str):
        """添加临时目录到清理列表"""
        self.temp_dirs.append(dirpath)
    
    def cleanup(self):
        """清理所有临时文件和目录"""
        import shutil
        
        for temp_file in self.temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                    logger.debug(f"已删除临时文件: {temp_file}")
            except Exception as e:
                logger.warning(f"删除临时文件失败: {temp_file}, 错误: {e}")
        
        for temp_dir in self.temp_dirs:
            try:
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
                    logger.debug(f"已删除临时目录: {temp_dir}")
            except Exception as e:
                logger.warning(f"删除临时目录失败: {temp_dir}, 错误: {e}")
        
        self.temp_files.clear()
        self.temp_dirs.clear()

# 常用的测试数据
TEST_USER_DATA = {
    'username': 'test@example.com',
    'password': 'test123456',
    'nickname': 'Test User',
    'role': 'user'
}

TEST_ADMIN_DATA = {
    'username': 'admin@example.com',
    'password': 'admin123456',
    'nickname': 'Test Admin',
    'role': 'admin'
}

TEST_ARTICLE_DATA = {
    'title': 'Test Article Title',
    'content': 'This is a test article content.',
    'article_type': 1,
    'userid': 1
}

# 常用的测试装饰器
def with_test_db(f):
    """测试数据库装饰器"""
    def wrapper(*args, **kwargs):
        helper = TestDatabaseHelper()
        helper.setup_test_tables()
        try:
            return f(*args, **kwargs)
        finally:
            helper.cleanup_test_data()
    return wrapper

def with_cleanup(f):
    """自动清理装饰器"""
    def wrapper(*args, **kwargs):
        cleanup_helper = TestCleanupHelper()
        try:
            return f(cleanup_helper, *args, **kwargs)
        finally:
            cleanup_helper.cleanup()
    return wrapper

# 导出常用的工具
__all__ = [
    'TestDatabaseHelper',
    'TestUserHelper', 
    'TestSessionHelper',
    'TestArticleHelper',
    'TestConfigHelper',
    'TestFileHelper',
    'TestDataValidator',
    'TestResponseHelper',
    'TestMockHelper',
    'TestCleanupHelper',
    'TEST_USER_DATA',
    'TEST_ADMIN_DATA', 
    'TEST_ARTICLE_DATA',
    'with_test_db',
    'with_cleanup'
]
def test_basic_import_via_subprocess():
    """Test basic woniunote import via subprocess"""
    import subprocess
    import sys
    
    cmd = [
        sys.executable, '-c',
        'import sys; sys.path.insert(0, "."); import woniunote; print("SUCCESS")'
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=project_root)
    assert result.returncode == 0
    assert "SUCCESS" in result.stdout
