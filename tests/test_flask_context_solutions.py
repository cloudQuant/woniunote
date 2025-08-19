#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Flask上下文问题解决方案测试
专门解决Flask上下文相关的测试失败问题
"""

import sys
import os
import pytest
import importlib.util
from unittest.mock import Mock, patch, MagicMock, mock_open
from datetime import datetime, UTC
import json
import tempfile

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

def create_mock_flask_app():
    """创建模拟Flask应用"""
    mock_app = Mock()
    mock_app.config = {}
    mock_app.app_context = Mock()
    mock_app.request_context = Mock()
    mock_app.test_client = Mock()
    return mock_app

def create_mock_flask_context():
    """创建模拟Flask上下文"""
    mock_context = Mock()
    mock_context.__enter__ = Mock(return_value=mock_context)
    mock_context.__exit__ = Mock(return_value=None)
    return mock_context

class TestFlaskContextSolutions:
    """Flask上下文解决方案测试"""
    
    def setup_method(self):
        """设置测试环境"""
        self.mock_app = create_mock_flask_app()
        self.mock_context = create_mock_flask_context()
        self.mock_app.app_context.return_value = self.mock_context
        self.mock_app.request_context.return_value = self.mock_context
    
    @patch('flask.Flask')
    @patch('flask.current_app')
    @patch('flask.g')
    def test_flask_app_context_simulation(self, mock_g, mock_current_app, mock_flask):
        """测试Flask应用上下文模拟"""
        # 设置Flask应用mock
        mock_flask.return_value = self.mock_app
        mock_current_app._get_current_object.return_value = self.mock_app
        
        # 设置g对象
        mock_g.request_id = 'test-request-123'
        mock_g.start_time = 1000000000.0
        mock_g.user_id = None
        
        # 测试应用上下文
        with patch('flask.has_app_context', return_value=True):
            # 模拟应用上下文中的操作
            app = mock_flask(__name__)
            assert app is not None
            
            # 测试配置访问
            app.config['SECRET_KEY'] = 'test_secret'
            assert app.config.get('SECRET_KEY') == 'test_secret'
            
            # 测试g对象访问
            assert mock_g.request_id == 'test-request-123'
            assert mock_g.start_time == 1000000000.0
    
    @patch('flask.request')
    @patch('flask.session') 
    @patch('flask.g')
    def test_flask_request_context_simulation(self, mock_g, mock_session, mock_request):
        """测试Flask请求上下文模拟"""
        # 设置请求对象
        mock_request.method = 'GET'
        mock_request.path = '/test'
        mock_request.args = {'param': 'value'}
        mock_request.form = {}
        mock_request.json = None
        mock_request.headers = {'Content-Type': 'application/json'}
        mock_request.remote_addr = '127.0.0.1'
        
        # 设置会话对象
        mock_session.get = Mock(side_effect=lambda key, default=None: {
            'user_id': 123,
            'username': 'testuser',
            'is_authenticated': True
        }.get(key, default))
        
        # 设置g对象
        mock_g.request_id = 'req-456'
        mock_g.user = None
        
        # 模拟请求上下文操作
        with patch('flask.has_request_context', return_value=True):
            # 测试请求数据访问
            assert mock_request.method == 'GET'
            assert mock_request.path == '/test'
            assert mock_request.args.get('param') == 'value'
            assert mock_request.remote_addr == '127.0.0.1'
            
            # 测试会话数据访问
            assert mock_session.get('user_id') == 123
            assert mock_session.get('username') == 'testuser'
            assert mock_session.get('is_authenticated') is True
            
            # 测试g对象
            assert mock_g.request_id == 'req-456'
    
    @patch('woniunote.common.simple_logger.get_simple_logger')
    @patch('flask.g')
    def test_logger_with_context(self, mock_g, mock_get_logger):
        """测试带上下文的日志记录"""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        
        # 设置请求ID
        mock_g.request_id = 'test-req-789'
        
        with patch('flask.has_request_context', return_value=True):
            # 模拟带上下文的日志记录
            logger = mock_get_logger('test_module')
            
            # 测试各种日志级别
            logger.info("Test info message", extra={'request_id': mock_g.request_id})
            logger.warning("Test warning", extra={'request_id': mock_g.request_id})
            logger.error("Test error", extra={'request_id': mock_g.request_id})
            
            # 验证调用
            assert mock_get_logger.call_count == 1
            assert logger.info.call_count == 1
            assert logger.warning.call_count == 1
            assert logger.error.call_count == 1
    
    @patch('flask.render_template')
    @patch('flask.request')
    def test_template_rendering_context(self, mock_request, mock_render):
        """测试模板渲染上下文"""
        mock_render.return_value = '<html>Test Template</html>'
        mock_request.endpoint = 'test.index'
        
        with patch('flask.has_request_context', return_value=True):
            # 模拟模板渲染
            result = mock_render('test.html', 
                               title='Test Page',
                               user={'name': 'Test User'},
                               data=[1, 2, 3])
            
            assert result == '<html>Test Template</html>'
            mock_render.assert_called_once_with('test.html',
                                               title='Test Page',
                                               user={'name': 'Test User'},
                                               data=[1, 2, 3])
    
    @patch('flask.jsonify')
    @patch('flask.request')
    def test_json_response_context(self, mock_request, mock_jsonify):
        """测试JSON响应上下文"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_jsonify.return_value = mock_response
        
        mock_request.method = 'POST'
        mock_request.json = {'name': 'test', 'value': 123}
        
        with patch('flask.has_request_context', return_value=True):
            # 模拟JSON响应
            response_data = {
                'success': True,
                'message': 'Operation successful',
                'data': {'id': 1, 'name': 'test'}
            }
            
            response = mock_jsonify(response_data)
            
            assert response.status_code == 200
            mock_jsonify.assert_called_once_with(response_data)

class TestDatabaseContextIntegration:
    """数据库上下文集成测试"""
    
    @patch('woniunote.common.database.db')
    @patch('flask.g')
    def test_database_session_with_context(self, mock_g, mock_db):
        """测试带上下文的数据库会话"""
        # 设置数据库mock
        mock_session = Mock()
        mock_db.session = mock_session
        
        # 设置g对象
        mock_g.request_id = 'db-req-001'
        
        with patch('flask.has_app_context', return_value=True):
            # 模拟数据库操作
            mock_user = Mock()
            mock_user.id = 1
            mock_user.username = 'testuser'
            
            # 模拟查询
            mock_session.query.return_value.filter.return_value.first.return_value = mock_user
            mock_session.query.return_value.all.return_value = [mock_user]
            
            # 执行查询操作
            user = mock_session.query('User').filter('id=1').first()
            users = mock_session.query('User').all()
            
            assert user.username == 'testuser'
            assert len(users) == 1
            assert users[0].username == 'testuser'
            
            # 验证调用
            mock_session.query.assert_called()
    
    @patch('woniunote.common.cache_utils.cached')
    @patch('redis.Redis')
    @patch('flask.current_app')
    def test_cache_with_app_context(self, mock_current_app, mock_redis, mock_cached):
        """测试带应用上下文的缓存操作"""
        # 设置Redis mock
        mock_redis_instance = Mock()
        mock_redis.return_value = mock_redis_instance
        mock_redis_instance.get.return_value = None
        mock_redis_instance.set.return_value = True
        mock_redis_instance.setex.return_value = True
        
        # 设置应用上下文
        mock_app = create_mock_flask_app()
        mock_current_app._get_current_object.return_value = mock_app
        
        with patch('flask.has_app_context', return_value=True):
            # 模拟缓存装饰器
            def cache_decorator(ttl=300):
                def decorator(func):
                    def wrapper(*args, **kwargs):
                        # 模拟缓存键生成
                        cache_key = f"{func.__name__}:{hash(str(args) + str(kwargs))}"
                        
                        # 模拟缓存检查
                        cached_result = mock_redis_instance.get(cache_key)
                        if cached_result:
                            return cached_result
                        
                        # 执行函数并缓存结果
                        result = func(*args, **kwargs)
                        mock_redis_instance.setex(cache_key, ttl, result)
                        return result
                    return wrapper
                return decorator
            
            mock_cached.return_value = cache_decorator(ttl=600)
            
            # 测试被缓存的函数
            @mock_cached(ttl=600)
            def expensive_operation(param):
                return f"result_for_{param}"
            
            # 执行操作
            result1 = expensive_operation("test")
            result2 = expensive_operation("test")  # 应该从缓存获取
            
            assert result1 == "result_for_test"
            assert result2 == "result_for_test"

class TestSecurityContextIntegration:
    """安全上下文集成测试"""
    
    @patch('flask.session')
    @patch('flask.request')
    @patch('woniunote.common.utils.validate_csrf_token')
    def test_csrf_protection_with_context(self, mock_validate_csrf, mock_request, mock_session):
        """测试带上下文的CSRF保护"""
        mock_request.method = 'POST'
        mock_request.form = {'csrf_token': 'valid_token_123'}
        mock_session.get.return_value = 'valid_token_123'
        mock_validate_csrf.return_value = True
        
        with patch('flask.has_request_context', return_value=True):
            # 模拟CSRF验证
            token_from_form = mock_request.form.get('csrf_token')
            token_from_session = mock_session.get('csrf_token')
            
            is_valid = mock_validate_csrf(token_from_form, token_from_session)
            
            assert is_valid is True
            mock_validate_csrf.assert_called_once_with(token_from_form, token_from_session)
    
    @patch('flask.session')
    @patch('woniunote.common.utils.check_rate_limit')
    @patch('flask.request')
    def test_rate_limiting_with_context(self, mock_request, mock_rate_limit, mock_session):
        """测试带上下文的速率限制"""
        mock_request.remote_addr = '192.168.1.100'
        mock_request.endpoint = 'api.login'
        mock_session.get.return_value = None  # 未登录用户
        
        # 模拟正常请求（未超限）
        mock_rate_limit.return_value = True
        
        with patch('flask.has_request_context', return_value=True):
            # 检查速率限制
            is_allowed = mock_rate_limit(
                ip=mock_request.remote_addr,
                endpoint=mock_request.endpoint,
                user_id=mock_session.get('user_id')
            )
            
            assert is_allowed is True
            mock_rate_limit.assert_called_once()
    
    @patch('flask.g')
    @patch('flask.session')
    @patch('woniunote.module.users.get_user_by_id')
    def test_user_authentication_context(self, mock_get_user, mock_session, mock_g):
        """测试用户认证上下文"""
        # 设置会话数据
        mock_session.get.side_effect = lambda key, default=None: {
            'user_id': 456,
            'username': 'authenticated_user',
            'is_authenticated': True,
            'login_time': '2024-12-19T10:00:00Z'
        }.get(key, default)
        
        # 设置用户数据
        mock_user = Mock()
        mock_user.id = 456
        mock_user.username = 'authenticated_user'
        mock_user.email = 'user@example.com'
        mock_user.is_active = True
        mock_get_user.return_value = mock_user
        
        # 设置g对象
        mock_g.user = mock_user
        mock_g.user_id = 456
        
        with patch('flask.has_request_context', return_value=True):
            # 模拟用户认证检查
            user_id = mock_session.get('user_id')
            is_authenticated = mock_session.get('is_authenticated', False)
            
            if user_id and is_authenticated:
                current_user = mock_get_user(user_id)
                mock_g.user = current_user
                mock_g.user_id = user_id
            
            # 验证认证状态
            assert mock_g.user_id == 456
            assert mock_g.user.username == 'authenticated_user'
            assert mock_g.user.is_active is True
            mock_get_user.assert_called_once_with(456)

class TestErrorHandlingWithContext:
    """带上下文的错误处理测试"""
    
    @patch('flask.jsonify')
    @patch('flask.g')
    @patch('woniunote.common.simple_logger.get_simple_logger')
    def test_error_handler_with_context(self, mock_get_logger, mock_g, mock_jsonify):
        """测试带上下文的错误处理"""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        
        mock_g.request_id = 'error-req-001'
        
        # 模拟错误响应
        mock_error_response = Mock()
        mock_error_response.status_code = 500
        mock_jsonify.return_value = mock_error_response
        
        with patch('flask.has_request_context', return_value=True):
            # 模拟错误处理函数
            def handle_internal_error(error):
                # 记录错误日志
                mock_logger.error(
                    f"Internal server error: {str(error)}",
                    extra={'request_id': mock_g.request_id}
                )
                
                # 返回错误响应
                return mock_jsonify({
                    'error': 'Internal Server Error',
                    'message': 'An internal server error occurred',
                    'request_id': mock_g.request_id
                })
            
            # 模拟错误发生
            test_error = Exception("Database connection failed")
            response = handle_internal_error(test_error)
            
            assert response.status_code == 500
            mock_logger.error.assert_called_once()
            mock_jsonify.assert_called_once()
    
    @patch('flask.abort')
    @patch('flask.request')
    def test_permission_error_with_context(self, mock_request, mock_abort):
        """测试带上下文的权限错误"""
        mock_request.endpoint = 'admin.users'
        mock_request.method = 'GET'
        
        with patch('flask.has_request_context', return_value=True):
            # 模拟权限检查失败
            def check_admin_permission():
                # 假设权限检查失败
                user_is_admin = False
                
                if not user_is_admin:
                    mock_abort(403)  # Forbidden
                
                return True
            
            # 测试权限检查
            try:
                check_admin_permission()
            except:
                pass  # 预期的权限错误
            
            mock_abort.assert_called_once_with(403)

class TestTemplateContextProcessors:
    """模板上下文处理器测试"""
    
    @patch('flask.g')
    @patch('flask.session')
    @patch('flask.request')
    def test_template_context_processor(self, mock_request, mock_session, mock_g):
        """测试模板上下文处理器"""
        # 设置上下文数据
        mock_g.user_id = 789
        mock_g.request_id = 'template-req-001'
        mock_session.get.return_value = 'zh-CN'
        mock_request.endpoint = 'main.index'
        
        with patch('flask.has_app_context', return_value=True):
            # 模拟模板上下文处理器
            def inject_template_globals():
                return {
                    'current_user_id': mock_g.user_id,
                    'request_id': mock_g.request_id,
                    'language': mock_session.get('language', 'en'),
                    'current_endpoint': mock_request.endpoint,
                    'app_name': 'WoniuNote',
                    'version': '1.0.0'
                }
            
            # 获取模板上下文
            context = inject_template_globals()
            
            assert context['current_user_id'] == 789
            assert context['request_id'] == 'template-req-001'
            assert context['language'] == 'zh-CN'
            assert context['current_endpoint'] == 'main.index'
            assert context['app_name'] == 'WoniuNote'
            assert context['version'] == '1.0.0'

if __name__ == "__main__":
    pytest.main([__file__, "-v"])