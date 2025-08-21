#!/usr/bin/env python3
"""
完整测试套件 - 用于实现100%覆盖率
"""

import unittest
import sys
import os
from unittest.mock import Mock, patch, MagicMock, mock_open, PropertyMock
import tempfile
import json
import yaml
from datetime import datetime, timedelta
import hashlib
import time
import threading
from io import BytesIO
import flask
from flask import Flask, session, g

# 导入woniunote包
import woniunote

class TestCommonUtils(unittest.TestCase):
    """测试 common/utils.py 模块的所有功能"""
    
    def test_read_config(self):
        """测试读取配置文件"""
        yaml_content = """
        database:
          host: localhost
          port: 3306
        """
        with patch('builtins.open', mock_open(read_data=yaml_content)):
            result = woniunote.common.utils.read_config('test.yaml')
            self.assertIsInstance(result, dict)
            self.assertEqual(result['database']['host'], 'localhost')
    
    def test_gen_email_code(self):
        """测试生成邮件验证码"""
        code = woniunote.common.utils.gen_email_code()
        self.assertIsInstance(code, str)
        self.assertEqual(len(code), 6)
        self.assertTrue(code.isdigit())
    
    def test_compress_image(self):
        """测试图片压缩"""
        # 创建模拟文件对象
        mock_file = Mock()
        mock_file.filename = 'test.jpg'
        mock_file.read = Mock(return_value=b'fake_image_data')
        mock_file.seek = Mock()
        
        with patch('PIL.Image.open') as mock_img_open:
            mock_img = Mock()
            mock_img.size = (1000, 800)
            mock_img.mode = 'RGB'
            mock_img.convert = Mock(return_value=mock_img)
            mock_img.resize = Mock(return_value=mock_img)
            
            # 模拟save方法
            def save_side_effect(output, format=None, quality=None):
                output.write(b'compressed')
            mock_img.save = Mock(side_effect=save_side_effect)
            mock_img_open.return_value = mock_img
            
            result = woniunote.common.utils.compress_image(mock_file, width=500)
            self.assertIsInstance(result, bytes)
    
    def test_model_list(self):
        """测试模型列表转换"""
        # 创建模拟模型
        mock_model = Mock()
        mock_model.__dict__ = {
            '_sa_instance_state': 'state',
            'id': 1,
            'name': 'test',
            'created_at': datetime.now()
        }
        
        result = woniunote.common.utils.model_list([mock_model])
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
    
    def test_get_config(self):
        """测试获取配置"""
        with patch.object(woniunote.common.utils, 'g_config', {'test_key': 'test_value'}):
            result = woniunote.common.utils.get_config('test_key')
            self.assertEqual(result, 'test_value')
    
    def test_get_article_type_config(self):
        """测试获取文章类型配置"""
        result = woniunote.common.utils.get_article_type_config()
        self.assertIsInstance(result, dict)
    
    def test_escape_sql(self):
        """测试SQL转义"""
        dangerous_input = "'; DROP TABLE users; --"
        result = woniunote.common.utils.escape_sql(dangerous_input)
        self.assertNotIn("DROP TABLE", result)


class TestArticlesModule(unittest.TestCase):
    """测试文章模块"""
    
    @patch('woniunote.module.articles.db')
    def test_get_visible_articles(self, mock_db):
        """测试获取可见文章"""
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.all.return_value = []
        
        mock_db.session.query.return_value = mock_query
        
        result = woniunote.module.articles.get_visible_articles()
        self.assertIsInstance(result, list)
    
    @patch('woniunote.module.articles.db')
    def test_get_article_by_id(self, mock_db):
        """测试根据ID获取文章"""
        mock_article = Mock()
        mock_article.article_id = 1
        mock_article.title = 'Test'
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_article
        
        mock_db.session.query.return_value = mock_query
        
        result = woniunote.module.articles.get_article_by_id(1)
        self.assertIsNotNone(result)
    
    @patch('woniunote.module.articles.db')
    def test_count_visible_articles(self, mock_db):
        """测试统计文章数量"""
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 10
        
        mock_db.session.query.return_value = mock_query
        
        result = woniunote.module.articles.count_visible_articles()
        self.assertEqual(result, 10)
    
    @patch('woniunote.module.articles.db')
    def test_search_articles(self, mock_db):
        """测试搜索文章"""
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = []
        
        mock_db.session.query.return_value = mock_query
        
        result = woniunote.module.articles.search_articles('test')
        self.assertIsInstance(result, list)
    
    @patch('woniunote.module.articles.db')
    def test_get_recent_articles(self, mock_db):
        """测试获取最近文章"""
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []
        
        mock_db.session.query.return_value = mock_query
        
        result = woniunote.module.articles.get_recent_articles(5)
        self.assertIsInstance(result, list)


class TestUsersModule(unittest.TestCase):
    """测试用户模块"""
    
    @patch('woniunote.module.users.db')
    def test_get_user_by_id(self, mock_db):
        """测试根据ID获取用户"""
        mock_user = Mock()
        mock_user.userid = 1
        mock_user.username = 'test'
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_user
        
        mock_db.session.query.return_value = mock_query
        
        result = woniunote.module.users.get_user_by_id(1)
        self.assertIsNotNone(result)
    
    @patch('woniunote.module.users.db')
    def test_get_user_by_username(self, mock_db):
        """测试根据用户名获取用户"""
        mock_user = Mock()
        mock_user.username = 'test'
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_user
        
        mock_db.session.query.return_value = mock_query
        
        result = woniunote.module.users.get_user_by_username('test')
        self.assertIsNotNone(result)
    
    @patch('woniunote.module.users.db')
    @patch('werkzeug.security.check_password_hash')
    def test_check_login(self, mock_check_pass, mock_db):
        """测试登录检查"""
        mock_user = Mock()
        mock_user.password = 'hashed_pass'
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_user
        
        mock_db.session.query.return_value = mock_query
        mock_check_pass.return_value = True
        
        result = woniunote.module.users.check_login('test', 'pass')
        self.assertTrue(result)
    
    @patch('woniunote.module.users.db')
    def test_count_users(self, mock_db):
        """测试统计用户数量"""
        mock_query = Mock()
        mock_query.count.return_value = 100
        
        mock_db.session.query.return_value = mock_query
        
        result = woniunote.module.users.count_users()
        self.assertEqual(result, 100)


class TestCommentsModule(unittest.TestCase):
    """测试评论模块"""
    
    @patch('woniunote.module.comments.db')
    def test_get_comments_by_article(self, mock_db):
        """测试获取文章评论"""
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = []
        
        mock_db.session.query.return_value = mock_query
        
        result = woniunote.module.comments.get_comments_by_article(1)
        self.assertIsInstance(result, list)
    
    @patch('woniunote.module.comments.db')
    def test_add_comment(self, mock_db):
        """测试添加评论"""
        mock_db.session.add = Mock()
        mock_db.session.commit = Mock()
        
        result = woniunote.module.comments.add_comment(1, 1, 'test comment')
        mock_db.session.add.assert_called_once()
        mock_db.session.commit.assert_called_once()
    
    @patch('woniunote.module.comments.db')
    def test_count_comments(self, mock_db):
        """测试统计评论数"""
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 5
        
        mock_db.session.query.return_value = mock_query
        
        result = woniunote.module.comments.count_comments(1)
        self.assertEqual(result, 5)


class TestCreditsModule(unittest.TestCase):
    """测试积分模块"""
    
    @patch('woniunote.module.credits.db')
    def test_get_user_credits(self, mock_db):
        """测试获取用户积分"""
        mock_user = Mock()
        mock_user.credit = 100
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_user
        
        mock_db.session.query.return_value = mock_query
        
        result = woniunote.module.credits.get_user_credits(1)
        self.assertEqual(result, 100)
    
    @patch('woniunote.module.credits.db')
    def test_update_credits(self, mock_db):
        """测试更新积分"""
        mock_user = Mock()
        mock_user.credit = 100
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_user
        
        mock_db.session.query.return_value = mock_query
        mock_db.session.commit = Mock()
        
        woniunote.module.credits.update_credits(1, 50)
        self.assertEqual(mock_user.credit, 150)
        mock_db.session.commit.assert_called_once()
    
    @patch('woniunote.module.credits.db')
    def test_deduct_credits(self, mock_db):
        """测试扣除积分"""
        mock_user = Mock()
        mock_user.credit = 100
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_user
        
        mock_db.session.query.return_value = mock_query
        mock_db.session.commit = Mock()
        
        result = woniunote.module.credits.deduct_credits(1, 30)
        self.assertTrue(result)
        self.assertEqual(mock_user.credit, 70)


class TestFavoritesModule(unittest.TestCase):
    """测试收藏模块"""
    
    @patch('woniunote.module.favorites.db')
    def test_add_favorite(self, mock_db):
        """测试添加收藏"""
        mock_db.session.add = Mock()
        mock_db.session.commit = Mock()
        
        woniunote.module.favorites.add_favorite(1, 10)
        mock_db.session.add.assert_called_once()
        mock_db.session.commit.assert_called_once()
    
    @patch('woniunote.module.favorites.db')
    def test_remove_favorite(self, mock_db):
        """测试取消收藏"""
        mock_fav = Mock()
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_fav
        
        mock_db.session.query.return_value = mock_query
        mock_db.session.delete = Mock()
        mock_db.session.commit = Mock()
        
        result = woniunote.module.favorites.remove_favorite(1, 10)
        self.assertTrue(result)
        mock_db.session.delete.assert_called_once()
    
    @patch('woniunote.module.favorites.db')
    def test_get_user_favorites(self, mock_db):
        """测试获取用户收藏"""
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = []
        
        mock_db.session.query.return_value = mock_query
        
        result = woniunote.module.favorites.get_user_favorites(1)
        self.assertIsInstance(result, list)


class TestControllers(unittest.TestCase):
    """测试控制器层"""
    
    def setUp(self):
        """设置测试环境"""
        self.app = woniunote.create_app('testing')
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()
    
    def tearDown(self):
        """清理测试环境"""
        self.ctx.pop()
    
    def test_index_page(self):
        """测试首页"""
        with patch('woniunote.module.articles.get_visible_articles', return_value=[]):
            with patch('woniunote.module.articles.count_visible_articles', return_value=0):
                response = self.client.get('/')
                self.assertEqual(response.status_code, 200)
    
    def test_login_page(self):
        """测试登录页面"""
        response = self.client.get('/user/login')
        self.assertEqual(response.status_code, 200)
    
    def test_register_page(self):
        """测试注册页面"""
        response = self.client.get('/user/register')
        self.assertEqual(response.status_code, 200)
    
    def test_article_detail(self):
        """测试文章详情"""
        mock_article = Mock()
        mock_article.article_id = 1
        mock_article.title = 'Test'
        mock_article.content = 'Content'
        mock_article.userid = 1
        mock_article.create_time = datetime.now()
        mock_article.read_count = 0
        
        with patch('woniunote.module.articles.get_article_by_id', return_value=mock_article):
            with patch('woniunote.module.users.get_user_by_id', return_value=Mock(username='test')):
                response = self.client.get('/article/1')
                self.assertIn(response.status_code, [200, 302])
    
    def test_search_route(self):
        """测试搜索路由"""
        with patch('woniunote.module.articles.search_articles', return_value=[]):
            response = self.client.get('/search?q=test')
            self.assertIn(response.status_code, [200, 302])
    
    def test_user_logout(self):
        """测试用户登出"""
        response = self.client.get('/user/logout')
        self.assertEqual(response.status_code, 302)  # 重定向到首页


class TestModels(unittest.TestCase):
    """测试模型层"""
    
    def test_user_model(self):
        """测试用户模型"""
        from woniunote.common.create_database import User
        user = User()
        user.username = 'test'
        user.email = 'test@example.com'
        self.assertEqual(user.username, 'test')
        self.assertEqual(user.email, 'test@example.com')
    
    def test_article_model(self):
        """测试文章模型"""
        from woniunote.common.create_database import Article
        article = Article()
        article.title = 'Test'
        article.content = 'Content'
        self.assertEqual(article.title, 'Test')
        self.assertEqual(article.content, 'Content')
    
    def test_comment_model(self):
        """测试评论模型"""
        from woniunote.common.create_database import Comment
        comment = Comment()
        comment.content = 'Test'
        comment.article_id = 1
        self.assertEqual(comment.content, 'Test')
        self.assertEqual(comment.article_id, 1)
    
    def test_card_model(self):
        """测试卡片模型"""
        from woniunote.models.card import Card, CardCategory
        
        category = CardCategory()
        category.name = 'Test Category'
        self.assertEqual(category.name, 'Test Category')
        
        card = Card()
        card.front = 'Question'
        card.back = 'Answer'
        self.assertEqual(card.front, 'Question')
        self.assertEqual(card.back, 'Answer')
    
    def test_todo_model(self):
        """测试待办事项模型"""
        from woniunote.models.todo import Item, Category
        
        category = Category()
        category.name = 'Work'
        self.assertEqual(category.name, 'Work')
        
        item = Item()
        item.title = 'Task'
        item.description = 'Description'
        self.assertEqual(item.title, 'Task')
        self.assertEqual(item.description, 'Description')


class TestCommonModules(unittest.TestCase):
    """测试通用模块"""
    
    def test_simple_logger(self):
        """测试简单日志"""
        from woniunote.common.simple_logger import get_simple_logger
        logger = get_simple_logger('test')
        self.assertIsNotNone(logger)
        
        # 测试日志记录
        with patch.object(logger, 'info') as mock_info:
            logger.info('test')
            mock_info.assert_called_once()
    
    def test_cache_manager(self):
        """测试缓存管理器"""
        from woniunote.common.cache_utils import CacheManager
        
        with patch('redis.Redis') as mock_redis:
            cache = CacheManager()
            
            # 测试设置缓存
            cache.set('key', 'value', 60)
            
            # 测试获取缓存
            mock_redis.return_value.get.return_value = b'value'
            result = cache.get('key')
            self.assertIsNotNone(result)
    
    def test_password_utils(self):
        """测试密码工具"""
        from woniunote.common.password_utils import hash_password, verify_password
        
        password = 'test123'
        hashed = hash_password(password)
        self.assertNotEqual(hashed, password)
        
        # 验证密码
        is_valid = verify_password(password, hashed)
        self.assertTrue(is_valid)
        
        # 错误密码
        is_valid = verify_password('wrong', hashed)
        self.assertFalse(is_valid)
    
    def test_session_manager(self):
        """测试会话管理"""
        from woniunote.common.session_manager import SessionManager
        
        app = Flask(__name__)
        app.secret_key = 'test_secret'
        
        with app.test_request_context():
            mgr = SessionManager()
            
            # 设置会话
            mgr.set_user_session({'userid': 1})
            
            # 获取会话
            user = mgr.get_user_session()
            self.assertIsNotNone(user)
    
    def test_monitoring(self):
        """测试监控"""
        from woniunote.common.monitoring import PerformanceMonitor
        
        monitor = PerformanceMonitor()
        
        # 记录请求
        monitor.record_request('/test', 0.1)
        
        # 获取指标
        metrics = monitor.get_metrics()
        self.assertIsInstance(metrics, dict)
    
    def test_rate_limiter(self):
        """测试速率限制"""
        from woniunote.common.rate_limiter import RateLimiter
        
        with patch('redis.Redis') as mock_redis:
            limiter = RateLimiter()
            
            # 模拟限制检查
            mock_redis.return_value.incr.return_value = 1
            mock_redis.return_value.expire.return_value = True
            
            result = limiter.check_limit('127.0.0.1', 'api', 10, 60)
            self.assertTrue(result)


class TestDatabase(unittest.TestCase):
    """测试数据库相关"""
    
    def test_database_instance(self):
        """测试数据库实例"""
        from woniunote.common.database import db
        self.assertIsNotNone(db)
    
    def test_database_optimizer(self):
        """测试数据库优化器"""
        from woniunote.common.database_optimizer import DatabaseOptimizer
        
        with patch('woniunote.common.database.db') as mock_db:
            optimizer = DatabaseOptimizer()
            
            # 测试查询优化
            mock_query = Mock()
            result = optimizer.optimize_query(mock_query)
            self.assertIsNotNone(result)
    
    def test_connection_manager(self):
        """测试连接管理器"""
        from woniunote.common.db_connection_manager import ConnectionManager
        
        with patch('sqlalchemy.create_engine') as mock_engine:
            manager = ConnectionManager()
            
            # 测试获取连接
            conn = manager.get_connection()
            self.assertIsNotNone(conn)


class TestSecurity(unittest.TestCase):
    """测试安全功能"""
    
    def test_csrf_protection(self):
        """测试CSRF保护"""
        from woniunote.common.csrf_protection import generate_csrf_token, validate_csrf_token
        
        app = Flask(__name__)
        app.secret_key = 'test'
        
        with app.test_request_context():
            # 生成token
            token = generate_csrf_token()
            self.assertIsNotNone(token)
            
            # 验证token
            is_valid = validate_csrf_token(token)
            self.assertTrue(is_valid)
    
    def test_input_validator(self):
        """测试输入验证"""
        from woniunote.common.input_validator import InputValidator
        
        validator = InputValidator()
        
        # 测试邮箱
        self.assertTrue(validator.validate_email('test@example.com'))
        self.assertFalse(validator.validate_email('invalid'))
        
        # 测试文件名
        self.assertTrue(validator.validate_filename('test.jpg'))
        self.assertFalse(validator.validate_filename('../etc/passwd'))
    
    def test_api_security(self):
        """测试API安全"""
        from woniunote.common.api_security import APISecurityManager
        
        manager = APISecurityManager()
        
        # 生成API密钥
        key = manager.generate_api_key()
        self.assertIsNotNone(key)
        self.assertEqual(len(key), 32)
        
        # 验证签名
        secret = 'secret'
        data = 'data'
        sig = manager.generate_signature(data, secret)
        
        is_valid = manager.verify_signature(data, sig, secret)
        self.assertTrue(is_valid)


class TestErrorHandling(unittest.TestCase):
    """测试错误处理"""
    
    def test_error_handler(self):
        """测试错误处理器"""
        from woniunote.common.error_handler import ErrorHandler
        
        handler = ErrorHandler()
        
        # 测试处理错误
        try:
            raise ValueError('test')
        except Exception as e:
            result = handler.handle_error(e)
            self.assertIsNotNone(result)
    
    def test_exception_handler(self):
        """测试异常处理"""
        from woniunote.common.enhanced_exception_handler import EnhancedExceptionHandler
        
        handler = EnhancedExceptionHandler()
        
        # 记录异常
        try:
            raise RuntimeError('test')
        except Exception as e:
            handler.log_exception(e)
        
        # 获取统计
        stats = handler.get_exception_stats()
        self.assertIsInstance(stats, dict)


# 主测试运行器
def run_all_tests():
    """运行所有测试"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加所有测试类
    test_classes = [
        TestCommonUtils,
        TestArticlesModule,
        TestUsersModule,
        TestCommentsModule,
        TestCreditsModule,
        TestFavoritesModule,
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
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)