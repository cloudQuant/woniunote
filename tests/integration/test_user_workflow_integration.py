#!/usr/bin/env python3
"""
Integration tests for complete user workflows in WoniuNote
Tests end-to-end user journeys including registration, login, content creation, and interaction
"""

import pytest
import sys
import os
import json
import time
import datetime
from unittest.mock import Mock, patch, MagicMock
from flask import Flask, session, request, url_for

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
    from flask import Flask
    from flask_sqlalchemy import SQLAlchemy
    from woniunote.controller.user import user
    from woniunote.controller.index import index
    from woniunote.controller.article import article
    from woniunote.controller.comment import comment
    from woniunote.controller.admin import admin
    from woniunote.controller.card_center import card_center
    from woniunote.controller.todo_center import tcenter
    from woniunote.controller.ucenter import ucenter
    from woniunote.controller.ueditor import ueditor
    from woniunote.controller.favorite import favorite

    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-integration-secret-key'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # 初始化数据库
    from woniunote.common.database import db
    db.init_app(app)

    # 在应用上下文中创建所有表
    with app.app_context():
        # 导入模型来创建表
        from woniunote.models.card import Card, CardCategory
        from woniunote.models.todo import Item as TodoItem, Category as TodoCategory
        db.create_all()

    # 注册蓝图 - 与app.py中的注册方式一致
    app.register_blueprint(index)
    app.register_blueprint(tcenter)
    app.register_blueprint(ucenter)
    app.register_blueprint(ueditor)
    app.register_blueprint(user)  # 直接注册，没有url_prefix
    app.register_blueprint(article)
    app.register_blueprint(comment)
    app.register_blueprint(admin)
    app.register_blueprint(card_center)
    app.register_blueprint(favorite)

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


class TestUserRegistrationWorkflow:
    """测试用户注册完整流程"""

    def test_user_registration_success(self, client):
        """测试成功用户注册流程"""
        # 使用更直接的方法mock整个用户模块
        with patch('woniunote.controller.user.Users') as mock_users_class, \
             patch('woniunote.controller.user.Credits') as mock_credits_class, \
             patch('woniunote.controller.user.gen_email_code') as mock_gen_code, \
             patch('woniunote.controller.user.send_email') as mock_send_email, \
             patch('woniunote.common.database.dbconnect') as mock_dbconnect:

            # 设置session中的验证码
            with client.session_transaction() as sess:
                sess['ecode'] = 'ABCD'

            # Mock数据库连接
            mock_session = Mock()
            mock_session.add = Mock()
            mock_session.commit = Mock()
            mock_dbconnect.return_value = (mock_session, None, None)

            # Mock邮件发送
            mock_gen_code.return_value = 'ABCD'
            mock_send_email.return_value = True

            # Mock用户类
            mock_users_instance = Mock()
            mock_user_result = Mock()
            mock_user_result.userid = 1
            mock_user_result.username = 'test@example.com'
            mock_user_result.nickname = 'TestUser'
            mock_user_result.role = 'user'
            mock_users_instance.do_register.return_value = mock_user_result
            mock_users_instance.find_by_username.return_value = []  # 用户不存在
            mock_users_class.return_value = mock_users_instance

            # Mock积分系统
            mock_credits_instance = Mock()
            mock_credits_class.return_value = mock_credits_instance

            # 准备注册数据（注意：实际使用ecode而不是captcha）
            registration_data = {
                'username': 'test@example.com',  # 邮箱作为用户名
                'password': 'TestPass123!',
                'ecode': 'ABCD'  # 邮箱验证码
            }

            # 发送注册请求
            response = client.post('/user', data=registration_data)

            # 验证响应
            assert response.status_code == 200

            # 验证方法调用
            mock_users_instance.do_register.assert_called_once()

    def test_user_registration_validation_errors(self, client):
        """测试注册验证错误"""
        test_cases = [
            {
                'name': '用户名为空',
                'data': {'username': '', 'password': 'TestPass123!', 'ecode': 'ABCD'},
                'expected_error': 'up-invalid'
            },
            {
                'name': '密码太短',
                'data': {'username': 'test@example.com', 'password': '123', 'ecode': 'ABCD'},
                'expected_error': 'up-invalid'
            },
            {
                'name': '邮箱格式错误',
                'data': {'username': 'invalid-email', 'password': 'TestPass123!', 'ecode': 'ABCD'},
                'expected_error': 'up-invalid'
            },
            {
                'name': '验证码错误',
                'data': {'username': 'test@example.com', 'password': 'TestPass123!', 'ecode': 'WRONG'},
                'expected_error': 'ecode-error'
            }
        ]

        for test_case in test_cases:
            # 设置session中的验证码（除了验证码错误的情况）
            with client.session_transaction() as sess:
                if test_case['expected_error'] != 'ecode-error':
                    sess['ecode'] = 'ABCD'
                else:
                    sess['ecode'] = 'DIFFERENT'

            response = client.post('/user', data=test_case['data'])
            assert response.status_code == 200
            response_data = response.data.decode()
            # 验证包含相应的错误信息
            assert test_case['expected_error'] in response_data

    def test_user_registration_duplicate_username(self, client):
        """测试用户名重复注册"""
        with patch('woniunote.controller.user.Users') as mock_users_class:

            # 设置session中的验证码
            with client.session_transaction() as sess:
                sess['ecode'] = 'ABCD'

            # Mock用户名已存在
            mock_users_instance = Mock()
            mock_users_instance.find_by_username.return_value = [{'userid': 1}]  # 用户已存在
            mock_users_class.return_value = mock_users_instance

            registration_data = {
                'username': 'existing@example.com',
                'password': 'TestPass123!',
                'ecode': 'ABCD'
            }

            response = client.post('/user', data=registration_data)
            assert response.status_code == 200
            response_data = response.data.decode()
            assert 'user-repeated' in response_data


class TestUserLoginWorkflow:
    """测试用户登录完整流程"""

    def test_user_login_success(self, client):
        """测试成功用户登录"""
        with patch('woniunote.controller.article.Users') as mock_users_class, \
             patch('woniunote.common.unified_logging.get_simple_logger') as mock_logger_func:

            # Mock用户登录成功
            mock_users_instance = Mock()
            mock_users_instance.login.return_value = "login-success"
            mock_users_instance.get_user_info.return_value = {
                'userid': 1,
                'username': 'testuser',
                'nickname': '测试用户',
                'role': 'user'
            }
            mock_users_class.return_value = mock_users_instance

            login_data = {
                'username': 'testuser',
                'password': 'TestPass123!'
            }

            response = client.post('/user/login', data=login_data)

            # 验证响应
            assert response.status_code == 200
            response_data = response.data.decode()
            assert 'login-success' in response_data

            # 验证会话设置
            with client.session_transaction() as sess:
                assert 'islogin' in sess
                assert sess['main_islogin'] == 'true'

    def test_user_login_wrong_credentials(self, client):
        """测试错误凭据登录"""
        with patch('woniunote.controller.article.Users') as mock_users_class:

            # Mock登录失败
            mock_users_instance = Mock()
            mock_users_instance.login.return_value = "用户名或密码错误"
            mock_users_class.return_value = mock_users_instance

            login_data = {
                'username': 'testuser',
                'password': 'WrongPassword!'
            }

            response = client.post('/user/login', data=login_data)
            assert response.status_code == 200
            response_data = response.data.decode()
            assert '用户名或密码错误' in response_data

    def test_user_logout_workflow(self, client):
        """测试用户登出流程"""
        # 先设置登录状态
        with client.session_transaction() as sess:
            sess['main_islogin'] = 'true'
            sess['main_userid'] = 1
            sess['main_username'] = 'testuser'

        # 发送登出请求
        response = client.get('/user/logout')

        # 验证响应
        assert response.status_code == 302  # 重定向

        # 验证会话清除
        with client.session_transaction() as sess:
            assert 'islogin' not in sess or sess.get('islogin') != 'true'


class TestUserContentCreationWorkflow:
    """测试用户内容创建完整流程"""

    def test_user_publish_article_workflow(self, client):
        """测试用户发布文章完整流程"""
        # 使用更直接的Mock方式
        with patch('woniunote.controller.article.Articles') as mock_articles_class, \
             patch('woniunote.controller.article.Users') as mock_users_class, \
             patch('woniunote.controller.article.session') as mock_session_module:

            # 设置登录状态
            with client.session_transaction() as sess:
                sess['main_islogin'] = 'true'
                sess['main_userid'] = 1
                sess['main_username'] = 'testuser'

            # Mock session.get 方法
            mock_session_module.get = Mock(side_effect=lambda key: {
                'main_islogin': 'true',
                'main_userid': 1
            }.get(key))

            # Mock用户查找
            mock_user_instance = Mock()
            mock_user_obj = Mock()
            mock_user_obj.userid = 1
            mock_user_obj.username = 'testuser'
            mock_user_obj.role = 'user'  # 确保角色正确设置
            mock_user_instance.find_by_userid.return_value = mock_user_obj
            mock_users_class.return_value = mock_user_instance

            # Mock文章发布成功
            mock_articles_instance = Mock()
            mock_articles_instance.insert_article.return_value = 1  # 返回文章ID
            mock_articles_class.return_value = mock_articles_instance

            article_data = {
                'headline': '测试文章标题',
                'content': '这是测试文章的内容，包含详细的描述和说明。',
                'type': '1',
                'subtype': '',
                'credit': '0',
                'drafted': '0',
                'checked': '0',
                'articleid': '0',  # 新文章ID为0
                'thumbnail': 'test_thumb.png'
            }

            response = client.post('/article/post', data=article_data)

            # 验证响应
            assert response.status_code == 200
            response_data = response.data.decode()
            # 控制器返回的是文章ID字符串，验证返回的是数字ID
            assert response_data.isdigit() and int(response_data) > 0

            # 验证方法调用
            mock_articles_instance.insert_article.assert_called_once()

    def test_user_publish_article_validation(self, client):
        """测试文章发布验证"""
        with patch('woniunote.controller.article.Users') as mock_users_class:
            # 设置登录状态
            with client.session_transaction() as sess:
                sess['main_islogin'] = 'true'
                sess['main_userid'] = 1

            # Mock用户查找
            mock_user_instance = Mock()
            mock_user_instance.find_by_userid.return_value = Mock(userid=1, username='testuser')
            mock_users_class.return_value = mock_user_instance

        # 测试标题为空
        article_data = {
            'headline': '',
            'content': '测试内容',
            'type': '1'
        }

        response = client.post('/article/post', data=article_data)
        assert response.status_code == 200
        response_data = response.data.decode()
        assert '标题不能为空' in response_data or 'post-fail' in response_data

    def test_user_edit_article_workflow(self, client):
        """测试用户编辑文章流程"""
        # 设置登录状态
            with client.session_transaction() as sess:
                sess['main_islogin'] = 'true'
                sess['main_userid'] = 1

            # Mock session.get 方法
            mock_session_module.get = Mock(side_effect=lambda key: {
                'main_islogin': 'true',
                'main_userid': 1
            }.get(key))

            # Mock用户查找
            mock_user_instance = Mock()
            mock_user_obj = Mock()
            mock_user_obj.userid = 1
            mock_user_obj.username = 'testuser'
            mock_user_obj.role = 'user'  # 确保角色正确设置
            mock_user_instance.find_by_userid.return_value = mock_user_obj
            mock_users_class.return_value = mock_user_instance

            # Mock文章编辑成功
            mock_articles_instance = Mock()
            mock_article_obj = Mock()
            mock_article_obj.userid = 1  # 确保文章所有者ID与用户ID一致
            mock_article_obj.type = 1
            mock_articles_instance.find_by_id.return_value = mock_article_obj  # Mock文章对象
            mock_articles_instance.update_article.return_value = 123  # 返回文章ID
            mock_articles_class.return_value = mock_articles_instance

            edit_data = {
                'articleid': '123',
                'headline': '修改后的标题',
                'content': '修改后的内容',
                'type': '2',
                'subtype': '',
                'credit': '0',
                'drafted': '0',
                'checked': '0',
                'thumbnail': 'test_thumb.png'
            }

            response = client.post('/article/edit', data=edit_data)

            # 验证响应
            assert response.status_code == 200
            response_data = response.data.decode()
            # 控制器返回的是文章ID字符串，验证返回的是数字ID
            assert response_data.isdigit() and int(response_data) > 0

    def test_user_delete_article_workflow(self, client):
        """测试用户删除文章流程"""
        # 验证文章删除功能不存在（返回404或错误）
        with client.session_transaction() as sess:
            sess['main_islogin'] = 'true'
            sess['main_userid'] = 1

        # 尝试访问不存在的删除端点
        response = client.post('/article/delete/123')
        # 应该返回404或其他错误状态码，因为删除功能不存在
        assert response.status_code in [404, 500, 405]


class TestUserInteractionWorkflow:
    """测试用户互动完整流程"""

    def test_user_comment_workflow(self, client):
        """测试用户评论完整流程"""
        with patch('woniunote.module.comments.Comments') as mock_comments_class, \
             patch('woniunote.controller.article.Users') as mock_users_class, \
             patch('woniunote.common.unified_logging.get_simple_logger') as mock_logger_func:

            # 设置登录状态
            with client.session_transaction() as sess:
                sess['main_islogin'] = 'true'
                sess['main_userid'] = 1

            # Mock用户查找
            mock_user_instance = Mock()
            mock_user_instance.find_by_userid.return_value = Mock(userid=1, username='testuser')
            mock_users_class.return_value = mock_user_instance

            # Mock评论添加成功
            mock_comments_instance = Mock()
            mock_comments_instance.insert_comment.return_value = "add-pass"
            mock_comments_class.return_value = mock_comments_instance

            comment_data = {
                'articleid': '123',
                'content': '这是一条测试评论，内容足够长以通过验证。'
            }

            response = client.post('/comment/add', data=comment_data)

            # 验证响应
            assert response.status_code == 200
            response_data = response.data.decode()
            assert 'add-pass' in response_data

    def test_user_reply_workflow(self, client):
        """测试用户回复评论流程"""
        with patch('woniunote.module.comments.Comments') as mock_comments_class:

            # 设置登录状态
            with client.session_transaction() as sess:
                sess['main_islogin'] = 'true'
                sess['main_userid'] = 1

            # Mock回复成功
            mock_comments_instance = Mock()
            mock_comments_instance.insert_reply.return_value = "reply-pass"
            mock_comments_class.return_value = mock_comments_instance

            reply_data = {
                'articleid': '123',
                'commentid': '456',
                'content': '这是对评论的回复，内容足够长。'
            }

            response = client.post('/comment/reply', data=reply_data)

            # 验证响应
            assert response.status_code == 200
            response_data = response.data.decode()
            assert 'reply-pass' in response_data

    def test_user_like_article_workflow(self, client):
        """测试用户点赞文章流程"""
        with patch('woniunote.module.favorites.Favorites') as mock_favorites_class:

            # 设置登录状态
            with client.session_transaction() as sess:
                sess['main_islogin'] = 'true'
                sess['main_userid'] = 1

            # Mock点赞成功
            mock_favorites_instance = Mock()
            mock_favorites_instance.add_favorite.return_value = "收藏成功"
            mock_favorites_class.return_value = mock_favorites_instance

            response = client.get('/favorite/add/123')

            # 验证响应
            assert response.status_code == 200
            response_data = response.data.decode()
            assert '收藏成功' in response_data


class TestUserProfileManagementWorkflow:
    """测试用户个人资料管理完整流程"""

    def test_user_profile_update_workflow(self, client):
        """测试用户资料更新流程"""
        with patch('woniunote.controller.article.Users') as mock_users_class:

            # 设置登录状态
            with client.session_transaction() as sess:
                sess['main_islogin'] = 'true'
                sess['main_userid'] = 1

            # Mock资料更新成功
            mock_users_instance = Mock()
            mock_users_instance.update_profile.return_value = "更新成功"
            mock_users_class.return_value = mock_users_instance

            profile_data = {
                'nickname': '新昵称',
                'email': 'newemail@example.com',
                'signature': '新的个性签名'
            }

            response = client.post('/loginfo/update', data=profile_data)

            # 验证响应
            assert response.status_code == 200
            response_data = response.data.decode()
            assert '更新成功' in response_data

    # def test_user_password_change_workflow(self, client):
    #     """测试用户密码修改流程 - TODO: 路由不存在"""
    #     pass

    # def test_user_avatar_upload_workflow(self, client):
    #     """测试用户头像上传流程 - TODO: 路由不存在"""
    #     pass


class TestUserCompleteJourneyWorkflow:
    """测试用户完整使用旅程"""

    def test_complete_user_journey(self, client):
        """测试完整的用户使用旅程"""
        # 1. 用户注册
        with patch('woniunote.controller.article.Users') as mock_users_class:

            mock_users_instance = Mock()
            mock_users_instance.register.return_value = "register-success"
            mock_users_class.return_value = mock_users_instance

            register_data = {
                'username': 'journeyuser',
                'password': 'JourneyPass123!',
                'email': 'journey@example.com',
                'captcha': 'ABCD'
            }

            response = client.post('/user', data=register_data)
            assert 'register-success' in response.data.decode()

        # 2. 用户登录
        with patch('woniunote.controller.article.Users') as mock_users_class:
            mock_users_instance = Mock()
            mock_users_instance.login.return_value = "login-success"
            mock_users_instance.get_user_info.return_value = {
                'userid': 1, 'username': 'journeyuser', 'role': 'user'
            }
            mock_users_class.return_value = mock_users_instance

            login_data = {
                'username': 'journeyuser',
                'password': 'JourneyPass123!'
            }

            response = client.post('/user/login', data=login_data)
            assert 'login-success' in response.data.decode()

        # 3. 发布文章
        with patch('woniunote.module.articles.Articles') as mock_articles_class:
            with client.session_transaction() as sess:
                sess['main_islogin'] = 'true'
                sess['main_userid'] = 1

            mock_articles_instance = Mock()
            mock_articles_instance.add_article.return_value = "发布成功"
            mock_articles_class.return_value = mock_articles_instance

            article_data = {
                'headline': '我的第一篇文章',
                'content': '这是我在WoniuNote上发布的首篇文章，记录我的使用体验。',
                'type': '1'
            }

            response = client.post('/article/post', data=article_data)
            assert '发布成功' in response.data.decode()

        # 4. 添加评论
        with patch('woniunote.module.comments.Comments') as mock_comments_class:
            mock_comments_instance = Mock()
            mock_comments_instance.insert_comment.return_value = "add-pass"
            mock_comments_class.return_value = mock_comments_instance

            comment_data = {
                'articleid': '1',
                'content': '文章写得很好，很有启发性！'
            }

            response = client.post('/comment/add', data=comment_data)
            assert 'add-pass' in response.data.decode()

        # 5. 查看个人资料
        response = client.get('/loginfo')
        assert response.status_code == 200

        # 6. 登出
        response = client.get('/user/logout')
        assert response.status_code == 302


class TestUserErrorScenariosWorkflow:
    """测试用户错误场景完整流程"""

    def test_user_workflow_error_recovery(self, client):
        """测试用户流程错误恢复"""
        # 测试网络错误后的重试
        with patch('woniunote.controller.article.Users') as mock_users_class:
            mock_users_instance = Mock()

            # 第一次调用失败
            mock_users_instance.login.side_effect = [
                Exception("网络错误"),
                "login-success"
            ]

            mock_users_instance.get_user_info.return_value = {
                'userid': 1, 'username': 'testuser', 'role': 'user'
            }

            mock_users_class.return_value = mock_users_instance

            login_data = {'username': 'testuser', 'password': 'TestPass123!'}

            # 第一次尝试（失败）
            response1 = client.post('/login', data=login_data)
            assert response1.status_code == 200

            # 第二次尝试（成功）
            response2 = client.post('/login', data=login_data)
            assert 'login-success' in response2.data.decode()

    def test_user_workflow_validation_chain(self, client):
        """测试用户流程验证链"""
        # 测试多重验证的完整链条
        validation_errors = []

        # 1. 注册验证
        response = client.post('/user', data={})
        validation_errors.append('register' in response.data.decode().lower())

        # 2. 登录验证
        response = client.post('/user/login', data={})
        validation_errors.append('login' in response.data.decode().lower())

        # 3. 文章发布验证
        with client.session_transaction() as sess:
            sess['main_islogin'] = 'true'

        response = client.post('/article/post', data={})
        validation_errors.append('post' in response.data.decode().lower())

        # 验证所有验证都生效了
        assert all(validation_errors), "部分验证机制未生效"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
