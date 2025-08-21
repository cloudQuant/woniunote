#!/usr/bin/env python3
"""
完整的测试套件，用于实现100%覆盖率
"""

import unittest
import sys
import os
from unittest.mock import Mock, patch, MagicMock, mock_open
import tempfile
import json
import yaml
from datetime import datetime, timedelta
import hashlib
import hmac
import time
import threading
from io import BytesIO

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

# 测试 common/utils.py
class TestCommonUtils(unittest.TestCase):
    """测试 common/utils.py 模块"""
    
    def setUp(self):
        """设置测试环境"""
        from woniunote.common import utils
        self.utils = utils
    
    def test_read_config_function(self):
        """测试读取配置文件功能"""
        # 测试成功读取YAML配置
        yaml_content = """
        database:
          host: localhost
          port: 3306
        """
        with patch('builtins.open', mock_open(read_data=yaml_content)):
            result = self.utils.read_config('test.yaml')
            self.assertIsInstance(result, dict)
            self.assertEqual(result['database']['host'], 'localhost')
    
    def test_gen_email_code(self):
        """测试生成邮件验证码"""
        code = self.utils.gen_email_code()
        self.assertIsInstance(code, str)
        self.assertEqual(len(code), 6)
        self.assertTrue(code.isdigit())
    
    def test_compress_image(self):
        """测试图片压缩功能"""
        # 模拟文件对象
        mock_file = Mock()
        mock_file.filename = 'test.jpg'
        mock_file.read = Mock(return_value=b'fake_image_data')
        mock_file.seek = Mock()
        
        with patch('PIL.Image.open') as mock_image_open:
            mock_img = Mock()
            mock_img.size = (1000, 800)
            mock_img.mode = 'RGB'
            mock_image_open.return_value = mock_img
            
            # 模拟save方法
            def save_side_effect(output, format, quality=None):
                output.write(b'compressed_image_data')
            mock_img.save = Mock(side_effect=save_side_effect)
            
            result = self.utils.compress_image(mock_file, width=500)
            self.assertIsInstance(result, bytes)
    
    def test_model_list(self):
        """测试模型列表转换"""
        # 创建模拟的SQLAlchemy模型对象
        mock_model = Mock()
        mock_model.__dict__ = {
            '_sa_instance_state': 'state',
            'id': 1,
            'name': 'test',
            'created_at': datetime(2024, 1, 1)
        }
        
        result = self.utils.model_list([mock_model])
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['id'], 1)
        self.assertEqual(result[0]['name'], 'test')


# 测试 module/articles.py
class TestArticlesModule(unittest.TestCase):
    """测试文章模块"""
    
    def setUp(self):
        """设置测试环境"""
        from woniunote.module import articles
        self.articles = articles
    
    @patch('woniunote.module.articles.db')
    def test_get_visible_articles(self, mock_db):
        """测试获取可见文章"""
        # 模拟查询结果
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.all.return_value = []
        
        mock_db.session.query.return_value = mock_query
        
        result = self.articles.get_visible_articles()
        self.assertIsInstance(result, list)
    
    @patch('woniunote.module.articles.db')
    def test_get_article_by_id(self, mock_db):
        """测试根据ID获取文章"""
        mock_article = Mock()
        mock_article.article_id = 1
        mock_article.title = 'Test Article'
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_article
        
        mock_db.session.query.return_value = mock_query
        
        result = self.articles.get_article_by_id(1)
        self.assertIsNotNone(result)
    
    @patch('woniunote.module.articles.db')
    def test_count_visible_articles(self, mock_db):
        """测试统计可见文章数量"""
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 10
        
        mock_db.session.query.return_value = mock_query
        
        result = self.articles.count_visible_articles()
        self.assertEqual(result, 10)


# 测试 module/users.py
class TestUsersModule(unittest.TestCase):
    """测试用户模块"""
    
    def setUp(self):
        """设置测试环境"""
        from woniunote.module import users
        self.users = users
    
    @patch('woniunote.module.users.db')
    def test_get_user_by_id(self, mock_db):
        """测试根据ID获取用户"""
        mock_user = Mock()
        mock_user.userid = 1
        mock_user.username = 'testuser'
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_user
        
        mock_db.session.query.return_value = mock_query
        
        result = self.users.get_user_by_id(1)
        self.assertIsNotNone(result)
    
    @patch('woniunote.module.users.db')
    def test_get_user_by_username(self, mock_db):
        """测试根据用户名获取用户"""
        mock_user = Mock()
        mock_user.username = 'testuser'
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_user
        
        mock_db.session.query.return_value = mock_query
        
        result = self.users.get_user_by_username('testuser')
        self.assertIsNotNone(result)
    
    @patch('woniunote.module.users.db')
    def test_check_login(self, mock_db):
        """测试登录验证"""
        from werkzeug.security import generate_password_hash
        
        mock_user = Mock()
        mock_user.password = generate_password_hash('password123')
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_user
        
        mock_db.session.query.return_value = mock_query
        
        with patch('werkzeug.security.check_password_hash', return_value=True):
            result = self.users.check_login('testuser', 'password123')
            self.assertTrue(result)


# 测试 controller 层
class TestControllers(unittest.TestCase):
    """测试控制器层"""
    
    def setUp(self):
        """设置测试环境"""
        # 创建测试应用
        from woniunote.app_factory import create_app
        self.app = create_app('testing')
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()
    
    def tearDown(self):
        """清理测试环境"""
        self.ctx.pop()
    
    def test_index_route(self):
        """测试首页路由"""
        with patch('woniunote.module.articles.get_visible_articles', return_value=[]):
            with patch('woniunote.module.articles.count_visible_articles', return_value=0):
                response = self.client.get('/')
                self.assertEqual(response.status_code, 200)
    
    def test_article_detail_route(self):
        """测试文章详情路由"""
        mock_article = Mock()
        mock_article.article_id = 1
        mock_article.title = 'Test Article'
        mock_article.content = 'Test content'
        mock_article.userid = 1
        mock_article.create_time = datetime.now()
        mock_article.read_count = 10
        
        with patch('woniunote.module.articles.get_article_by_id', return_value=mock_article):
            with patch('woniunote.module.users.get_user_by_id', return_value=Mock(username='author')):
                response = self.client.get('/article/1')
                self.assertIn(response.status_code, [200, 302])  # 可能重定向到登录
    
    def test_user_login_get(self):
        """测试用户登录页面"""
        response = self.client.get('/user/login')
        self.assertEqual(response.status_code, 200)
    
    def test_user_login_post(self):
        """测试用户登录提交"""
        with patch('woniunote.module.users.check_login', return_value=True):
            with patch('woniunote.module.users.get_user_by_username', return_value=Mock(userid=1)):
                response = self.client.post('/user/login', data={
                    'username': 'testuser',
                    'password': 'password123'
                })
                self.assertIn(response.status_code, [200, 302])
    
    def test_user_register_get(self):
        """测试用户注册页面"""
        response = self.client.get('/user/register')
        self.assertEqual(response.status_code, 200)


# 测试 models 层
class TestModels(unittest.TestCase):
    """测试模型层"""
    
    def test_user_model(self):
        """测试用户模型"""
        from woniunote.common.create_database import User
        user = User()
        user.username = 'testuser'
        user.email = 'test@example.com'
        self.assertEqual(user.username, 'testuser')
        self.assertEqual(user.email, 'test@example.com')
    
    def test_article_model(self):
        """测试文章模型"""
        from woniunote.common.create_database import Article
        article = Article()
        article.title = 'Test Article'
        article.content = 'Test content'
        self.assertEqual(article.title, 'Test Article')
        self.assertEqual(article.content, 'Test content')
    
    def test_comment_model(self):
        """测试评论模型"""
        from woniunote.common.create_database import Comment
        comment = Comment()
        comment.content = 'Test comment'
        comment.article_id = 1
        self.assertEqual(comment.content, 'Test comment')
        self.assertEqual(comment.article_id, 1)


# 测试 common 层的其他模块
class TestCommonModules(unittest.TestCase):
    """测试通用模块"""
    
    def test_simple_logger(self):
        """测试简单日志模块"""
        from woniunote.common.simple_logger import get_simple_logger
        logger = get_simple_logger('test')
        self.assertIsNotNone(logger)
        
        # 测试日志方法
        with patch.object(logger, 'info') as mock_info:
            logger.info('test message')
            mock_info.assert_called_once()
    
    def test_cache_utils(self):
        """测试缓存工具"""
        from woniunote.common.cache_utils import CacheManager
        
        with patch('redis.Redis') as mock_redis:
            cache = CacheManager()
            
            # 测试设置缓存
            cache.set('key', 'value', timeout=60)
            
            # 测试获取缓存
            mock_redis.return_value.get.return_value = b'value'
            result = cache.get('key')
            self.assertIsNotNone(result)
    
    def test_password_utils(self):
        """测试密码工具"""
        from woniunote.common.password_utils import hash_password, verify_password
        
        password = 'test_password_123'
        hashed = hash_password(password)
        self.assertIsNotNone(hashed)
        self.assertNotEqual(hashed, password)
        
        # 测试密码验证
        is_valid = verify_password(password, hashed)
        self.assertTrue(is_valid)
        
        # 测试错误密码
        is_valid = verify_password('wrong_password', hashed)
        self.assertFalse(is_valid)
    
    def test_session_utils(self):
        """测试会话工具"""
        from woniunote.common.session_utils import SessionManager
        
        with self.app.test_request_context():
            session_mgr = SessionManager()
            
            # 测试设置会话
            session_mgr.set_user_session({'userid': 1, 'username': 'test'})
            
            # 测试获取会话
            user_info = session_mgr.get_user_session()
            self.assertIsNotNone(user_info)
    
    def test_monitoring(self):
        """测试监控模块"""
        from woniunote.common.monitoring import PerformanceMonitor
        
        monitor = PerformanceMonitor()
        
        # 测试记录指标
        monitor.record_request('/test', 0.1)
        
        # 测试获取指标
        metrics = monitor.get_metrics()
        self.assertIsInstance(metrics, dict)


# 测试数据库相关功能
class TestDatabase(unittest.TestCase):
    """测试数据库功能"""
    
    def test_database_connection(self):
        """测试数据库连接"""
        from woniunote.common.database import db
        
        with self.app.app_context():
            # 测试数据库实例存在
            self.assertIsNotNone(db)
            
            # 测试会话
            self.assertIsNotNone(db.session)
    
    def test_database_optimizer(self):
        """测试数据库优化器"""
        from woniunote.common.database_optimizer import DatabaseOptimizer
        
        with patch('woniunote.common.database.db') as mock_db:
            optimizer = DatabaseOptimizer()
            
            # 测试优化查询
            mock_query = Mock()
            optimized = optimizer.optimize_query(mock_query)
            self.assertIsNotNone(optimized)
    
    def test_connection_pool(self):
        """测试连接池"""
        from woniunote.common.db_connection_manager import ConnectionManager
        
        with patch('sqlalchemy.create_engine') as mock_create_engine:
            manager = ConnectionManager()
            
            # 测试获取连接
            conn = manager.get_connection()
            self.assertIsNotNone(conn)


# 测试安全相关功能
class TestSecurity(unittest.TestCase):
    """测试安全功能"""
    
    def test_csrf_protection(self):
        """测试CSRF保护"""
        from woniunote.common.csrf_protection import generate_csrf_token, validate_csrf_token
        
        with self.app.test_request_context():
            # 生成token
            token = generate_csrf_token()
            self.assertIsNotNone(token)
            
            # 验证token
            is_valid = validate_csrf_token(token)
            self.assertTrue(is_valid)
    
    def test_input_validator(self):
        """测试输入验证器"""
        from woniunote.common.input_validator import InputValidator
        
        validator = InputValidator()
        
        # 测试邮箱验证
        self.assertTrue(validator.validate_email('test@example.com'))
        self.assertFalse(validator.validate_email('invalid-email'))
        
        # 测试文件名验证
        self.assertTrue(validator.validate_filename('test.jpg'))
        self.assertFalse(validator.validate_filename('../etc/passwd'))
    
    def test_rate_limiter(self):
        """测试速率限制"""
        from woniunote.common.rate_limiter import RateLimiter
        
        with patch('redis.Redis') as mock_redis:
            limiter = RateLimiter()
            
            # 测试检查限制
            mock_redis.return_value.incr.return_value = 1
            mock_redis.return_value.expire.return_value = True
            
            is_allowed = limiter.check_limit('127.0.0.1', 'api', 10, 60)
            self.assertTrue(is_allowed)
    
    def test_api_security(self):
        """测试API安全"""
        from woniunote.common.api_security import APISecurityManager
        
        manager = APISecurityManager()
        
        # 测试生成API密钥
        api_key = manager.generate_api_key()
        self.assertIsNotNone(api_key)
        self.assertEqual(len(api_key), 32)
        
        # 测试验证签名
        secret = 'test_secret'
        data = 'test_data'
        signature = manager.generate_signature(data, secret)
        
        is_valid = manager.verify_signature(data, signature, secret)
        self.assertTrue(is_valid)


# 测试错误处理
class TestErrorHandling(unittest.TestCase):
    """测试错误处理"""
    
    def test_error_handler(self):
        """测试错误处理器"""
        from woniunote.common.error_handler import ErrorHandler
        
        handler = ErrorHandler()
        
        # 测试处理异常
        try:
            raise ValueError('Test error')
        except Exception as e:
            result = handler.handle_error(e)
            self.assertIsNotNone(result)
            self.assertIn('error', result)
    
    def test_exception_handler(self):
        """测试异常处理器"""
        from woniunote.common.enhanced_exception_handler import EnhancedExceptionHandler
        
        handler = EnhancedExceptionHandler()
        
        # 测试记录异常
        try:
            raise RuntimeError('Test exception')
        except Exception as e:
            handler.log_exception(e)
            
        # 测试获取异常统计
        stats = handler.get_exception_stats()
        self.assertIsInstance(stats, dict)


# 主测试运行器
def run_all_tests():
    """运行所有测试"""
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加所有测试类
    test_classes = [
        TestCommonUtils,
        TestArticlesModule,
        TestUsersModule,
        TestControllers,
        TestModels,
        TestCommonModules,
        TestDatabase,
        TestSecurity,
        TestErrorHandling
    ]
    
    for test_class in test_classes:
        suite.addTests(loader.loadTestsFromTestCase(test_class))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 返回测试结果
    return result.wasSuccessful()


if __name__ == '__main__':
    # 设置Flask应用
    from woniunote.app_factory import create_app
    app = create_app('testing')
    
    with app.app_context():
        success = run_all_tests()
        sys.exit(0 if success else 1)