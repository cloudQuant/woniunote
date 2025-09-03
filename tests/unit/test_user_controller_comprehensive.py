#!/usr/bin/env python3
"""
Comprehensive test suite for woniunote.controller.user module
Tests all user-related functions with 100% coverage including Flask routes, authentication, and error handling
"""

import pytest
import sys
import os
import json
import uuid
from unittest.mock import Mock, patch, MagicMock, call
from flask import Flask, session, request, url_for, jsonify
from io import BytesIO

# 确保项目根目录在Python路径中
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 设置测试环境
os.environ['TESTING'] = 'True'
os.environ['FLASK_ENV'] = 'testing'


@pytest.fixture
def app():
    """创建测试Flask应用"""
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret-key'
    app.config['SESSION_TYPE'] = 'filesystem'

    # 注册用户蓝图
    from woniunote.controller.user import user
    app.register_blueprint(user, url_prefix='/user')

    return app


@pytest.fixture
def client(app):
    """创建测试客户端"""
    return app.test_client()


@pytest.fixture
def app_context(app):
    """创建应用上下文"""
    with app.app_context():
        yield app


class TestUserTraceId:
    """测试用户模块跟踪ID生成"""

    def test_generate_user_trace_id_format(self):
        """测试跟踪ID格式"""
        from woniunote.controller.user import generate_user_trace_id

        trace_id = generate_user_trace_id()

        # 验证格式: UUID格式
        assert isinstance(trace_id, str)
        assert len(trace_id) == 36  # UUID标准长度
        assert '-' in trace_id  # 包含连字符

    def test_generate_user_trace_id_uniqueness(self):
        """测试跟踪ID唯一性"""
        from woniunote.controller.user import generate_user_trace_id

        trace_ids = [generate_user_trace_id() for _ in range(10)]

        # 验证所有ID都是唯一的
        assert len(set(trace_ids)) == len(trace_ids)

    def test_get_user_trace_id_thread_safety(self):
        """测试跟踪ID线程安全性"""
        from woniunote.controller.user import get_user_trace_id

        trace_id1 = get_user_trace_id()
        trace_id2 = get_user_trace_id()

        # 在同一线程中应该返回相同的ID
        assert trace_id1 == trace_id2
        assert isinstance(trace_id1, str)


class TestUserBlueprintSetup:
    """测试用户蓝图设置"""

    def test_blueprint_creation(self):
        """测试蓝图创建"""
        from woniunote.controller.user import user

        assert user.name == 'user'
        assert user.url_prefix == '/user'

    def test_blueprint_routes_registration(self, app):
        """测试路由注册"""
        with app.test_client() as client:
            # 测试路由是否正确注册
            routes = [rule.rule for rule in app.url_map.iter_rules() if rule.rule.startswith('/user')]
            expected_routes = [
                '/user/vcode',
                '/user/ecode',
                '/user/user',
                '/user/login',
                '/user/logout',
                '/user/loginfo',
                '/user/redis/code',
                '/user/redis/reg',
                '/user/redis/login'
            ]

            for route in expected_routes:
                assert route in routes, f"Route {route} not found in registered routes"


class TestVcodeRoute:
    """测试图形验证码路由"""

    def test_vcode_get_success(self, client):
        """测试获取图形验证码成功"""
        with patch('woniunote.controller.user.ImageCode') as mock_image_code:
            # Mock验证码生成
            mock_code_instance = Mock()
            mock_code_instance.get_code.return_value = ('ABCD', b'fake_image_data')
            mock_image_code.return_value = mock_code_instance

            response = client.get('/user/vcode')

            assert response.status_code == 200
            assert response.content_type == 'image/jpeg'
            assert response.data == b'fake_image_data'

            # 验证session中保存了验证码
            with client.session_transaction() as sess:
                assert sess['vcode'] == 'abcd'  # 应该转换为小写

    def test_vcode_get_with_exception(self, client):
        """测试获取图形验证码异常处理"""
        with patch('woniunote.controller.user.ImageCode') as mock_image_code:
            # Mock异常
            mock_image_code.side_effect = Exception("Image generation failed")

            response = client.get('/user/vcode')

            assert response.status_code == 500
            data = json.loads(response.data)
            assert 'error' in data
            assert data['error'] == '生成验证码失败'

    def test_vcode_get_logging(self, client, caplog):
        """测试图形验证码的日志记录"""
        with patch('woniunote.controller.user.ImageCode') as mock_image_code:
            mock_code_instance = Mock()
            mock_code_instance.get_code.return_value = ('ABCD', b'fake_image_data')
            mock_image_code.return_value = mock_code_instance

            with caplog.at_level('INFO'):
                client.get('/user/vcode')

            # 验证日志记录
            assert '请求图形验证码' in caplog.text
            assert '生成图形验证码成功' in caplog.text


class TestEcodeRoute:
    """测试邮箱验证码路由"""

    def test_ecode_post_success(self, client):
        """测试发送邮箱验证码成功"""
        with patch('woniunote.controller.user.gen_email_code') as mock_gen_code, \
             patch('woniunote.controller.user.send_email') as mock_send_email:

            mock_gen_code.return_value = '123456'
            mock_send_email.return_value = True

            data = {'email': 'test@example.com'}
            response = client.post('/user/ecode', data=data)

            assert response.status_code == 200
            assert b'success' in response.data

            # 验证session中保存了验证码
            with client.session_transaction() as sess:
                assert sess['ecode'] == '123456'

    def test_ecode_post_invalid_email(self, client):
        """测试发送邮箱验证码 - 无效邮箱格式"""
        data = {'email': 'invalid-email'}
        response = client.post('/user/ecode', data=data)

        assert response.status_code == 200
        assert response.data == b'email-invalid'

    def test_ecode_post_missing_email(self, client):
        """测试发送邮箱验证码 - 缺少邮箱参数"""
        data = {}
        response = client.post('/user/ecode', data=data)

        assert response.status_code == 200
        assert response.data == b'email-invalid'

    def test_ecode_post_email_send_failure(self, client):
        """测试发送邮箱验证码 - 邮件发送失败"""
        with patch('woniunote.controller.user.gen_email_code') as mock_gen_code, \
             patch('woniunote.controller.user.send_email') as mock_send_email:

            mock_gen_code.return_value = '123456'
            mock_send_email.side_effect = Exception("Email send failed")

            data = {'email': 'test@example.com'}
            response = client.post('/user/ecode', data=data)

            assert response.status_code == 200
            assert response.data == b'email-send-error'

    def test_ecode_post_logging(self, client, caplog):
        """测试邮箱验证码的日志记录"""
        with patch('woniunote.controller.user.gen_email_code') as mock_gen_code, \
             patch('woniunote.controller.user.send_email') as mock_send_email:

            mock_gen_code.return_value = '123456'
            mock_send_email.return_value = True

            data = {'email': 'test@example.com'}

            with caplog.at_level('INFO'):
                client.post('/user/ecode', data=data)

            # 验证日志记录
            assert '请求邮箱验证码' in caplog.text
            assert '发送邮箱验证码成功' in caplog.text


class TestRegisterRoute:
    """测试用户注册路由"""

    def test_register_post_success(self, client):
        """测试用户注册成功"""
        with patch('woniunote.controller.user.Users') as mock_users_class, \
             patch('woniunote.controller.user.Credits') as mock_credits_class:

            # Mock用户实例
            mock_user_instance = Mock()
            mock_user_instance.find_by_username.return_value = []
            mock_users_class.return_value = mock_user_instance

            # Mock注册结果
            mock_result = Mock()
            mock_result.userid = 1
            mock_result.nickname = 'TestUser'
            mock_result.role = 'user'
            mock_user_instance.do_register.return_value = mock_result

            # Mock积分实例
            mock_credits_instance = Mock()
            mock_credits_class.return_value = mock_credits_instance

            # 设置session中的验证码
            with client.session_transaction() as sess:
                sess['ecode'] = '123456'

            data = {
                'username': 'test@example.com',
                'password': 'password123',
                'ecode': '123456'
            }

            response = client.post('/user/user', data=data)

            assert response.status_code == 200
            assert response.data == b'reg-pass'

            # 验证session设置
            with client.session_transaction() as sess:
                assert sess['islogin'] == 'true'
                assert sess['userid'] == 1
                assert sess['username'] == 'test@example.com'
                assert sess['nickname'] == 'TestUser'
                assert sess['role'] == 'user'

    def test_register_post_invalid_ecode(self, client):
        """测试用户注册 - 验证码错误"""
        with client.session_transaction() as sess:
            sess['ecode'] = '123456'

        data = {
            'username': 'test@example.com',
            'password': 'password123',
            'ecode': 'wrong_code'
        }

        response = client.post('/user/user', data=data)

        assert response.status_code == 200
        assert response.data == b'ecode-error'

    def test_register_post_invalid_email(self, client):
        """测试用户注册 - 无效邮箱格式"""
        with client.session_transaction() as sess:
            sess['ecode'] = '123456'

        data = {
            'username': 'invalid-email',
            'password': 'password123',
            'ecode': '123456'
        }

        response = client.post('/user/user', data=data)

        assert response.status_code == 200
        assert response.data == b'up-invalid'

    def test_register_post_short_password(self, client):
        """测试用户注册 - 密码太短"""
        with client.session_transaction() as sess:
            sess['ecode'] = '123456'

        data = {
            'username': 'test@example.com',
            'password': '123',
            'ecode': '123456'
        }

        response = client.post('/user/user', data=data)

        assert response.status_code == 200
        assert response.data == b'up-invalid'

    def test_register_post_user_exists(self, client):
        """测试用户注册 - 用户已存在"""
        with patch('woniunote.controller.user.Users') as mock_users_class:
            mock_user_instance = Mock()
            mock_user_instance.find_by_username.return_value = [{'id': 1}]  # 用户已存在
            mock_users_class.return_value = mock_user_instance

            with client.session_transaction() as sess:
                sess['ecode'] = '123456'

            data = {
                'username': 'test@example.com',
                'password': 'password123',
                'ecode': '123456'
            }

            response = client.post('/user/user', data=data)

            assert response.status_code == 200
            assert response.data == b'user-repeated'

    def test_register_post_exception_handling(self, client):
        """测试用户注册异常处理"""
        with patch('woniunote.controller.user.Users') as mock_users_class:
            mock_user_instance = Mock()
            mock_user_instance.find_by_username.side_effect = Exception("Database error")
            mock_users_class.return_value = mock_user_instance

            with client.session_transaction() as sess:
                sess['ecode'] = '123456'

            data = {
                'username': 'test@example.com',
                'password': 'password123',
                'ecode': '123456'
            }

            response = client.post('/user/user', data=data)

            assert response.status_code == 200
            assert response.data == b'reg-error'


class TestLoginRoute:
    """测试用户登录路由"""

    def test_login_post_success(self, client):
        """测试用户登录成功"""
        with patch('woniunote.controller.user.Users') as mock_users_class:
            # Mock用户实例
            mock_user_instance = Mock()

            # Mock登录结果
            mock_result = Mock()
            mock_result.userid = 1
            mock_result.nickname = 'TestUser'
            mock_result.role = 'user'
            mock_user_instance.do_login.return_value = mock_result
            mock_users_class.return_value = mock_user_instance

            # 设置session中的验证码
            with client.session_transaction() as sess:
                sess['vcode'] = 'abcd'

            data = {
                'username': 'test@example.com',
                'password': 'password123',
                'vcode': 'ABCD'  # 大写字母
            }

            response = client.post('/user/login', data=data)

            assert response.status_code == 200
            assert response.data == b'login-pass'

            # 验证session设置
            with client.session_transaction() as sess:
                assert sess['islogin'] == 'true'
                assert sess['userid'] == 1
                assert sess['username'] == 'test@example.com'
                assert sess['nickname'] == 'TestUser'
                assert sess['role'] == 'user'

    def test_login_post_invalid_vcode(self, client):
        """测试用户登录 - 验证码错误"""
        with client.session_transaction() as sess:
            sess['vcode'] = 'abcd'

        data = {
            'username': 'test@example.com',
            'password': 'password123',
            'vcode': 'wrong_code'
        }

        response = client.post('/user/login', data=data)

        assert response.status_code == 200
        assert response.data == b'vcode-error'

    def test_login_post_invalid_credentials(self, client):
        """测试用户登录 - 无效凭据"""
        with patch('woniunote.controller.user.Users') as mock_users_class:
            mock_user_instance = Mock()
            mock_user_instance.do_login.return_value = None  # 登录失败
            mock_users_class.return_value = mock_user_instance

            with client.session_transaction() as sess:
                sess['vcode'] = 'abcd'

            data = {
                'username': 'test@example.com',
                'password': 'wrong_password',
                'vcode': 'ABCD'
            }

            response = client.post('/user/login', data=data)

            assert response.status_code == 200
            assert response.data == b'login-fail'

    def test_login_post_exception_handling(self, client):
        """测试用户登录异常处理"""
        with patch('woniunote.controller.user.Users') as mock_users_class:
            mock_user_instance = Mock()
            mock_user_instance.do_login.side_effect = Exception("Database error")
            mock_users_class.return_value = mock_user_instance

            with client.session_transaction() as sess:
                sess['vcode'] = 'abcd'

            data = {
                'username': 'test@example.com',
                'password': 'password123',
                'vcode': 'ABCD'
            }

            response = client.post('/user/login', data=data)

            assert response.status_code == 200
            assert response.data == b'login-error'


class TestLogoutRoute:
    """测试用户登出路由"""

    def test_logout_get_success(self, client):
        """测试用户登出成功 (GET请求)"""
        # 设置登录状态
        with client.session_transaction() as sess:
            sess['islogin'] = 'true'
            sess['userid'] = 1
            sess['username'] = 'test@example.com'
            sess['nickname'] = 'TestUser'
            sess['role'] = 'user'

        response = client.get('/user/logout')

        assert response.status_code == 200
        assert response.data == b'logout-success'

        # 验证session清除
        with client.session_transaction() as sess:
            assert 'islogin' not in sess
            assert 'userid' not in sess
            assert 'username' not in sess
            assert 'nickname' not in sess
            assert 'role' not in sess

    def test_logout_post_success(self, client):
        """测试用户登出成功 (POST请求)"""
        # 设置登录状态
        with client.session_transaction() as sess:
            sess['islogin'] = 'true'
            sess['userid'] = 1
            sess['username'] = 'test@example.com'

        response = client.post('/user/logout')

        assert response.status_code == 200
        assert response.data == b'logout-success'

        # 验证session清除
        with client.session_transaction() as sess:
            assert 'islogin' not in sess
            assert 'userid' not in sess

    def test_logout_without_login(self, client):
        """测试用户登出 - 未登录状态"""
        response = client.get('/user/logout')

        assert response.status_code == 200
        assert response.data == b'logout-success'


class TestLoginfoRoute:
    """测试登录信息路由"""

    def test_loginfo_get_logged_in(self, client):
        """测试获取登录信息 - 已登录状态"""
        # 设置登录状态
        with client.session_transaction() as sess:
            sess['islogin'] = 'true'
            sess['userid'] = 1
            sess['username'] = 'test@example.com'
            sess['nickname'] = 'TestUser'
            sess['role'] = 'user'

        response = client.get('/user/loginfo')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['islogin'] == 'true'
        assert data['userid'] == 1
        assert data['username'] == 'test@example.com'
        assert data['nickname'] == 'TestUser'
        assert data['role'] == 'user'

    def test_loginfo_get_not_logged_in(self, client):
        """测试获取登录信息 - 未登录状态"""
        response = client.get('/user/loginfo')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['islogin'] == 'false'
        assert data['userid'] == 0
        assert data['username'] == ''
        assert data['nickname'] == ''
        assert data['role'] == 'guest'


class TestRedisCodeRoute:
    """测试Redis验证码路由"""

    def test_redis_code_post_success(self, client):
        """测试Redis验证码成功"""
        with patch('woniunote.controller.user.redis_connect') as mock_redis:
            mock_redis_instance = Mock()
            mock_redis_instance.set.return_value = True
            mock_redis.return_value = mock_redis_instance

            data = {'code': '123456', 'email': 'test@example.com'}
            response = client.post('/user/redis/code', data=data)

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['status'] == 'success'

    def test_redis_code_post_redis_error(self, client):
        """测试Redis验证码 - Redis连接错误"""
        with patch('woniunote.controller.user.redis_connect') as mock_redis:
            mock_redis.side_effect = Exception("Redis connection failed")

            data = {'code': '123456', 'email': 'test@example.com'}
            response = client.post('/user/redis/code', data=data)

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['status'] == 'error'


class TestRedisRegRoute:
    """测试Redis注册路由"""

    def test_redis_reg_post_success(self, client):
        """测试Redis注册成功"""
        with patch('woniunote.controller.user.redis_connect') as mock_redis, \
             patch('woniunote.controller.user.Users') as mock_users_class:

            # Mock Redis
            mock_redis_instance = Mock()
            mock_redis_instance.get.return_value = b'123456'
            mock_redis.return_value = mock_redis_instance

            # Mock用户实例
            mock_user_instance = Mock()
            mock_user_instance.find_by_username.return_value = []
            mock_users_class.return_value = mock_user_instance

            # Mock注册结果
            mock_result = Mock()
            mock_result.userid = 1
            mock_result.nickname = 'TestUser'
            mock_result.role = 'user'
            mock_user_instance.do_register.return_value = mock_result

            data = {
                'username': 'test@example.com',
                'password': 'password123',
                'code': '123456'
            }

            response = client.post('/user/redis/reg', data=data)

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['status'] == 'success'

    def test_redis_reg_post_invalid_code(self, client):
        """测试Redis注册 - 验证码错误"""
        with patch('woniunote.controller.user.redis_connect') as mock_redis:
            mock_redis_instance = Mock()
            mock_redis_instance.get.return_value = b'654321'  # 不同的验证码
            mock_redis.return_value = mock_redis_instance

            data = {
                'username': 'test@example.com',
                'password': 'password123',
                'code': '123456'
            }

            response = client.post('/user/redis/reg', data=data)

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['status'] == 'code_error'


class TestRedisLoginRoute:
    """测试Redis登录路由"""

    def test_redis_login_post_success(self, client):
        """测试Redis登录成功"""
        with patch('woniunote.controller.user.redis_connect') as mock_redis, \
             patch('woniunote.controller.user.Users') as mock_users_class:

            # Mock Redis
            mock_redis_instance = Mock()
            mock_redis_instance.get.return_value = b'abcd'
            mock_redis.return_value = mock_redis_instance

            # Mock用户实例
            mock_user_instance = Mock()
            mock_result = Mock()
            mock_result.userid = 1
            mock_result.nickname = 'TestUser'
            mock_result.role = 'user'
            mock_user_instance.do_login.return_value = mock_result
            mock_users_class.return_value = mock_user_instance

            data = {
                'username': 'test@example.com',
                'password': 'password123',
                'code': 'ABCD'  # 大写字母
            }

            response = client.post('/user/redis/login', data=data)

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['status'] == 'success'

    def test_redis_login_post_invalid_code(self, client):
        """测试Redis登录 - 验证码错误"""
        with patch('woniunote.controller.user.redis_connect') as mock_redis:
            mock_redis_instance = Mock()
            mock_redis_instance.get.return_value = b'wrong_code'
            mock_redis.return_value = mock_redis_instance

            data = {
                'username': 'test@example.com',
                'password': 'password123',
                'code': 'ABCD'
            }

            response = client.post('/user/redis/login', data=data)

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['status'] == 'code_error'


class TestUserControllerIntegration:
    """测试用户控制器集成场景"""

    def test_complete_registration_flow(self, client):
        """测试完整的注册流程"""
        # 1. 获取图形验证码
        with patch('woniunote.controller.user.ImageCode') as mock_image_code:
            mock_code_instance = Mock()
            mock_code_instance.get_code.return_value = ('ABCD', b'fake_image_data')
            mock_image_code.return_value = mock_code_instance

            client.get('/user/vcode')

        # 2. 发送邮箱验证码
        with patch('woniunote.controller.user.gen_email_code') as mock_gen_code, \
             patch('woniunote.controller.user.send_email') as mock_send_email:

            mock_gen_code.return_value = '123456'
            mock_send_email.return_value = True

            data = {'email': 'test@example.com'}
            client.post('/user/ecode', data=data)

        # 3. 用户注册
        with patch('woniunote.controller.user.Users') as mock_users_class, \
             patch('woniunote.controller.user.Credits') as mock_credits_class:

            mock_user_instance = Mock()
            mock_user_instance.find_by_username.return_value = []

            mock_result = Mock()
            mock_result.userid = 1
            mock_result.nickname = 'TestUser'
            mock_result.role = 'user'
            mock_user_instance.do_register.return_value = mock_result
            mock_users_class.return_value = mock_user_instance

            mock_credits_instance = Mock()
            mock_credits_class.return_value = mock_credits_instance

            data = {
                'username': 'test@example.com',
                'password': 'password123',
                'ecode': '123456'
            }

            response = client.post('/user/user', data=data)
            assert response.data == b'reg-pass'

        # 4. 验证登录状态
        response = client.get('/user/loginfo')
        data = json.loads(response.data)
        assert data['islogin'] == 'true'
        assert data['username'] == 'test@example.com'

    def test_complete_login_logout_flow(self, client):
        """测试完整的登录登出流程"""
        # 1. 获取图形验证码
        with patch('woniunote.controller.user.ImageCode') as mock_image_code:
            mock_code_instance = Mock()
            mock_code_instance.get_code.return_value = ('ABCD', b'fake_image_data')
            mock_image_code.return_value = mock_code_instance

            client.get('/user/vcode')

        # 2. 用户登录
        with patch('woniunote.controller.user.Users') as mock_users_class:
            mock_user_instance = Mock()
            mock_result = Mock()
            mock_result.userid = 1
            mock_result.nickname = 'TestUser'
            mock_result.role = 'user'
            mock_user_instance.do_login.return_value = mock_result
            mock_users_class.return_value = mock_user_instance

            data = {
                'username': 'test@example.com',
                'password': 'password123',
                'vcode': 'ABCD'
            }

            response = client.post('/user/login', data=data)
            assert response.data == b'login-pass'

        # 3. 验证登录状态
        response = client.get('/user/loginfo')
        data = json.loads(response.data)
        assert data['islogin'] == 'true'

        # 4. 用户登出
        response = client.get('/user/logout')
        assert response.data == b'logout-success'

        # 5. 验证登出状态
        response = client.get('/user/loginfo')
        data = json.loads(response.data)
        assert data['islogin'] == 'false'


class TestUserControllerErrorHandling:
    """测试用户控制器错误处理"""

    def test_unexpected_exceptions(self, client):
        """测试意外异常处理"""
        with patch('woniunote.controller.user.get_user_trace_id') as mock_trace:
            mock_trace.side_effect = Exception("Unexpected error")

            response = client.get('/user/vcode')
            assert response.status_code == 500

    def test_database_connection_errors(self, client):
        """测试数据库连接错误"""
        with patch('woniunote.controller.user.Users') as mock_users_class:
            mock_user_instance = Mock()
            mock_user_instance.find_by_username.side_effect = Exception("Database connection failed")
            mock_users_class.return_value = mock_user_instance

            with client.session_transaction() as sess:
                sess['ecode'] = '123456'

            data = {
                'username': 'test@example.com',
                'password': 'password123',
                'ecode': '123456'
            }

            response = client.post('/user/user', data=data)
            assert response.data == b'reg-error'

    def test_redis_connection_errors(self, client):
        """测试Redis连接错误"""
        with patch('woniunote.controller.user.redis_connect') as mock_redis:
            mock_redis.side_effect = Exception("Redis connection failed")

            data = {'code': '123456', 'email': 'test@example.com'}
            response = client.post('/user/redis/code', data=data)

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['status'] == 'error'


class TestUserControllerLogging:
    """测试用户控制器日志记录"""

    def test_all_routes_have_logging(self, client, caplog):
        """测试所有路由都有适当的日志记录"""
        # 测试各个路由的日志记录
        routes_to_test = [
            ('/user/vcode', 'GET', {}),
            ('/user/loginfo', 'GET', {}),
            ('/user/logout', 'GET', {})
        ]

        for route, method, data in routes_to_test:
            with caplog.at_level('INFO'):
                if method == 'GET':
                    client.get(route)
                else:
                    client.post(route, data=data)

                # 验证有相应的日志记录
                assert len(caplog.records) > 0

    def test_error_logging(self, client, caplog):
        """测试错误日志记录"""
        with patch('woniunote.controller.user.ImageCode') as mock_image_code:
            mock_image_code.side_effect = Exception("Test error")

            with caplog.at_level('ERROR'):
                client.get('/user/vcode')

            # 验证错误日志记录
            assert any('生成图形验证码失败' in record.message for record in caplog.records)

    def test_security_logging(self, client, caplog):
        """测试安全相关日志记录"""
        with patch('woniunote.controller.user.Users') as mock_users_class:
            mock_user_instance = Mock()
            mock_user_instance.do_login.return_value = None  # 登录失败
            mock_users_class.return_value = mock_user_instance

            with client.session_transaction() as sess:
                sess['vcode'] = 'abcd'

            data = {
                'username': 'test@example.com',
                'password': 'wrong_password',
                'vcode': 'ABCD'
            }

            with caplog.at_level('WARNING'):
                client.post('/user/login', data=data)

            # 验证安全日志记录
            assert any('登录失败' in record.message or 'login-fail' in str(record)
                      for record in caplog.records)
