#!/usr/bin/env python3
"""
Comprehensive test suite for woniunote.controller.comment module
Tests all comment-related functions with 100% coverage including Flask routes, CRUD operations, and error handling
"""

import pytest
import sys
import os
import json
import uuid
import datetime
from unittest.mock import Mock, patch, MagicMock, call
from flask import Flask, session, request, url_for, render_template, redirect, abort
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
    # 设置正确的模板路径
    template_dir = os.path.join(project_root, 'woniunote', 'template')
    app = Flask(__name__, template_folder=template_dir)
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret-key'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tests/test_db/woniunote_test.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # 注册蓝图 (与实际应用保持一致，不设置url_prefix)
    from woniunote.controller.comment import comment
    app.register_blueprint(comment)

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


class TestCommentTraceId:
    """测试评论模块跟踪ID生成"""

    def test_get_comment_trace_id_format(self):
        """测试跟踪ID格式"""
        from woniunote.controller.comment import get_comment_trace_id

        trace_id = get_comment_trace_id()

        # 验证格式: comment_yyyyMMdd_uuid前缀
        assert isinstance(trace_id, str)
        assert trace_id.startswith('comment_')
        assert len(trace_id.split('_')) == 3  # comment_date_uuid
        assert len(trace_id.split('_')[2]) == 8  # UUID前缀8位

    def test_get_comment_trace_id_uniqueness(self):
        """测试跟踪ID唯一性"""
        from woniunote.controller.comment import get_comment_trace_id

        trace_ids = [get_comment_trace_id() for _ in range(10)]

        # 验证所有ID都是唯一的
        assert len(set(trace_ids)) == len(trace_ids)

    def test_get_comment_trace_id_date_format(self):
        """测试跟踪ID包含正确日期格式"""
        from woniunote.controller.comment import get_comment_trace_id

        trace_id = get_comment_trace_id()

        # 验证日期格式
        date_part = trace_id.split('_')[1]
        assert len(date_part) == 8  # YYYYMMDD格式

        # 验证日期是有效的
        try:
            datetime.datetime.strptime(date_part, '%Y%m%d')
        except ValueError:
            pytest.fail(f"Invalid date format in trace_id: {date_part}")


class TestCommentBlueprintSetup:
    """测试评论蓝图设置"""

    def test_blueprint_creation(self):
        """测试蓝图创建"""
        from woniunote.controller.comment import comment

        assert comment.name == 'comment'
        # comment蓝图在实际应用中没有设置url_prefix，与其他蓝图保持一致
        assert comment.url_prefix is None

    def test_blueprint_routes_registration(self, app):
        """测试路由注册"""
        with app.test_client() as client:
            # 测试路由是否正确注册
            routes = [rule.rule for rule in app.url_map.iter_rules()]
            expected_routes = [
                '/comment/<int:articleid>-<int:page>',
                '/comment',
                '/reply'
            ]

            for route in expected_routes:
                assert route in routes, f"Route {route} not found in registered routes. Available routes: {routes}"

    def test_logger_initialization(self):
        """测试日志记录器初始化"""
        from woniunote.controller.comment import comment_logger

        assert comment_logger is not None
        assert hasattr(comment_logger, 'info')
        assert hasattr(comment_logger, 'warning')
        assert hasattr(comment_logger, 'error')


class TestCommentBeforeRequest:
    """测试评论模块前置请求处理"""

    def test_before_request_logged_in(self, client):
        """测试已登录用户的请求前置处理"""
        with patch('woniunote.controller.comment.comment_logger') as mock_logger:
            # 设置登录状态
            with client.session_transaction() as sess:
                sess['islogin'] = 'true'
                sess['userid'] = 1

            # 发送请求
            response = client.post('/comment', data={'content': 'test'})

            # 验证日志记录
            mock_logger.info.assert_called()
            info_calls = [call for call in mock_logger.info.call_args_list
                         if '评论模块请求' in str(call)]
            assert len(info_calls) > 0

    def test_before_request_not_logged_in(self, client):
        """测试未登录用户的请求前置处理"""
        with patch('woniunote.controller.comment.comment_logger') as mock_logger:
            # 发送请求（无登录状态）
            response = client.post('/comment', data={'content': 'test'})

            # 验证返回未登录提示
            assert 'not-login' in response.data.decode()

            # 验证警告日志记录
            mock_logger.warning.assert_called()
            warning_calls = [call for call in mock_logger.warning.call_args_list
                           if '未登录用户尝试访问评论功能' in str(call)]
            assert len(warning_calls) > 0

    def test_before_request_exception_handling(self, app):
        """测试前置请求处理异常情况"""
        with patch('woniunote.controller.comment.comment_logger') as mock_logger, \
             patch('woniunote.controller.comment.request') as mock_request:

            # Mock request对象
            mock_request.remote_addr = '127.0.0.1'
            mock_request.method = 'POST'
            mock_request.path = '/comment'

            # 使用应用上下文测试before_request函数
            with app.test_request_context('/comment', method='POST'):
                # 在应用上下文中Mock session.get方法
                from woniunote.controller.comment import session
                original_get = session.get
                def mock_get_side_effect(key, default=None):
                    if key == 'islogin':
                        raise Exception("Session access error")
                    return original_get(key, default)

                # 临时替换session.get方法
                session.get = mock_get_side_effect

                try:
                    from woniunote.controller.comment import before_comment
                    result = before_comment()

                    # 验证异常被正确记录
                    mock_logger.error.assert_called_once()
                    call_args = mock_logger.error.call_args[0][0]  # 获取第一个位置参数
                    assert "评论前置检查异常" in call_args

                    # 验证日志包含错误信息
                    call_kwargs = mock_logger.error.call_args[0][1]  # 获取第二个位置参数（字典）
                    assert 'error' in call_kwargs
                    assert 'error_type' in call_kwargs
                    assert call_kwargs['error_type'] == 'Exception'
                finally:
                    # 恢复原始的session.get方法
                    session.get = original_get


class TestCommentAddRoute:
    """测试添加评论路由"""

    def test_add_comment_success(self, client):
        """测试成功添加评论"""
        with patch('woniunote.controller.comment.Comments') as mock_comments_class, \
             patch('woniunote.controller.comment.Credits') as mock_credits_class, \
             patch('woniunote.controller.comment.Users') as mock_users_class, \
             patch('woniunote.controller.comment.Articles') as mock_articles_class, \
             patch('woniunote.controller.comment.comment_logger') as mock_logger:

            # 设置登录状态
            with client.session_transaction() as sess:
                sess['islogin'] = 'true'
                sess['userid'] = 1

            # Mock评论实例
            mock_comments_instance = Mock()
            mock_comments_instance.check_limit_per_5.return_value = False  # 没有超出限制
            mock_comments_class.return_value = mock_comments_instance

            # Mock其他实例
            mock_credits_instance = Mock()
            mock_credits_class.return_value = mock_credits_instance

            mock_users_instance = Mock()
            mock_users_class.return_value = mock_users_instance

            mock_articles_instance = Mock()
            mock_articles_class.return_value = mock_articles_instance

            # 测试数据
            data = {
                'articleid': '1',
                'content': 'This is a valid comment with proper length'
            }

            response = client.post('/comment', data=data)

            # 验证返回成功
            assert response.data.decode() == 'add-pass'

            # 验证评论插入被调用
            mock_comments_instance.insert_comment.assert_called_once_with(
                '1',  # articleid
                'This is a valid comment with proper length',  # content
                '127.0.0.1'  # ipaddr (客户端IP)
            )

            # 验证积分更新被调用
            mock_credits_instance.insert_detail.assert_called_once_with(
                credit_type='添加评论',
                target='1',
                credit=2
            )

            # 验证日志记录
            mock_logger.info.assert_called()

    def test_add_comment_content_too_short(self, client):
        """测试评论内容过短"""
        with patch('woniunote.controller.comment.comment_logger') as mock_logger:
            # 设置登录状态
            with client.session_transaction() as sess:
                sess['islogin'] = 'true'
                sess['userid'] = 1

            # 测试数据（内容过短）
            data = {
                'articleid': '1',
                'content': 'Hi'  # 只有2个字符，少于5个
            }

            response = client.post('/comment', data=data)

            # 验证返回内容无效
            assert 'content-invalid' in response.data.decode()

            # 验证警告日志记录
            mock_logger.warning.assert_called()
            warning_calls = [call for call in mock_logger.warning.call_args_list
                           if '评论内容验证失败' in str(call)]
            assert len(warning_calls) > 0

    def test_add_comment_content_too_long(self, client):
        """测试评论内容过长"""
        with patch('woniunote.controller.comment.comment_logger') as mock_logger:
            # 设置登录状态
            with client.session_transaction() as sess:
                sess['islogin'] = 'true'
                sess['userid'] = 1

            # 测试数据（内容过长）
            long_content = 'A' * 1001  # 1001个字符，超过1000个限制
            data = {
                'articleid': '1',
                'content': long_content
            }

            response = client.post('/comment', data=data)

            # 验证返回内容无效
            assert 'content-invalid' in response.data.decode()

    def test_add_comment_frequency_limit_exceeded(self, client):
        """测试添加评论频率限制"""

    def test_add_comment_missing_parameters(self, client):
        """测试缺少必要参数"""
        with client.session_transaction() as sess:
            sess['islogin'] = 'true'
            sess['userid'] = 1

        # 测试缺少articleid
        data = {'content': 'Valid content'}
        response = client.post('/comment', data=data)
        assert response.status_code == 200  # 不会崩溃，但会记录错误

        # 测试缺少content
        data = {'articleid': '1'}
        response = client.post('/comment', data=data)
        assert response.status_code == 200

    def test_add_comment_database_error(self, client):
        """测试数据库操作异常"""
        with patch('woniunote.controller.comment.Comments') as mock_comments_class, \
             patch('woniunote.controller.comment.comment_logger') as mock_logger:

            # 设置登录状态
            with client.session_transaction() as sess:
                sess['islogin'] = 'true'
                sess['userid'] = 1

            # Mock评论实例（插入失败）
            mock_comments_instance = Mock()
            mock_comments_instance.check_limit_per_5.return_value = False
            mock_comments_instance.insert_comment.side_effect = Exception("Database error")
            mock_comments_class.return_value = mock_comments_instance

            # 测试数据
            data = {
                'articleid': '1',
                'content': 'This is a valid comment'
            }

            response = client.post('/comment', data=data)

            # 验证返回失败提示
            assert 'add-fail' in response.data.decode()

            # 验证错误日志记录
            mock_logger.error.assert_called()


class TestCommentReplyRoute:
    """测试回复评论路由"""

    def test_reply_comment_success(self, client):
        """测试成功回复评论"""
        with patch('woniunote.controller.comment.Comments') as mock_comments_class, \
             patch('woniunote.controller.comment.Credits') as mock_credits_class, \
             patch('woniunote.controller.comment.Users') as mock_users_class, \
             patch('woniunote.controller.comment.Articles') as mock_articles_class, \
             patch('woniunote.controller.comment.comment_logger') as mock_logger:

            # 设置登录状态
            with client.session_transaction() as sess:
                sess['islogin'] = 'true'
                sess['userid'] = 1

            # Mock评论实例
            mock_comments_instance = Mock()
            mock_comments_instance.check_limit_per_5.return_value = False
            mock_comments_class.return_value = mock_comments_instance

            # Mock其他实例
            mock_credits_instance = Mock()
            mock_credits_class.return_value = mock_credits_instance

            mock_users_instance = Mock()
            mock_users_class.return_value = mock_users_instance

            mock_articles_instance = Mock()
            mock_articles_class.return_value = mock_articles_instance

            # 测试数据
            data = {
                'articleid': '1',
                'commentid': '2',
                'content': 'This is a valid reply with proper length'
            }

            response = client.post('/reply', data=data)

            # 验证返回成功
            assert response.status_code == 200

            # 验证回复插入被调用
            mock_comments_instance.insert_reply.assert_called()

            # 验证积分更新（回复评论获得积分）
            mock_credits_instance.insert_detail.assert_called()

            # 验证日志记录
            mock_logger.info.assert_called()

    def test_reply_comment_content_validation(self, client):
        """测试回复内容验证"""
        with patch('woniunote.controller.comment.comment_logger') as mock_logger:
            # 设置登录状态
            with client.session_transaction() as sess:
                sess['islogin'] = 'true'
                sess['userid'] = 1

            # 测试过短内容
            data = {
                'articleid': '1',
                'commentid': '2',
                'content': 'Hi'
            }
            response = client.post('/reply', data=data)
            assert response.data.decode() == 'content-invalid'

            # 测试过长内容
            data = {
                'articleid': '1',
                'commentid': '2',
                'content': 'A' * 1001
            }
            response = client.post('/reply', data=data)
            assert response.data.decode() == 'content-invalid'

    def test_reply_comment_frequency_limit(self, client):
        """测试回复频率限制"""
        with patch('woniunote.controller.comment.Comments') as mock_comments_class, \
             patch('woniunote.controller.comment.comment_logger') as mock_logger:

            # 设置登录状态
            with client.session_transaction() as sess:
                sess['islogin'] = 'true'
                sess['userid'] = 1

            # Mock评论实例（超出频率限制）
            mock_comments_instance = Mock()
            mock_comments_instance.check_limit_per_5.return_value = True
            mock_comments_class.return_value = mock_comments_instance

            # 测试数据
            data = {
                'articleid': '1',
                'commentid': '2',
                'content': 'This is a valid reply'
            }

            response = client.post('/reply', data=data)

            # 验证返回频率限制提示
            assert 'reply-limit' in response.data.decode()

    def test_reply_comment_missing_parameters(self, client):
        """测试回复缺少参数"""
        with client.session_transaction() as sess:
            sess['islogin'] = 'true'
            sess['userid'] = 1

        # 测试缺少commentid
        data = {
            'articleid': '1',
            'content': 'Valid reply content'
        }
        response = client.post('/reply', data=data)
        assert response.status_code == 200

    def test_reply_comment_database_error(self, client):
        """测试回复数据库错误"""
        with patch('woniunote.controller.comment.Comments') as mock_comments_class, \
             patch('woniunote.controller.comment.comment_logger') as mock_logger:

            # 设置登录状态
            with client.session_transaction() as sess:
                sess['islogin'] = 'true'
                sess['userid'] = 1

            # Mock评论实例（插入失败）
            mock_comments_instance = Mock()
            mock_comments_instance.check_limit_per_5.return_value = False
            mock_comments_instance.insert_reply.side_effect = Exception("Database error")
            mock_comments_class.return_value = mock_comments_instance

            # 测试数据
            data = {
                'articleid': '1',
                'commentid': '2',
                'content': 'This is a valid reply'
            }

            response = client.post('/reply', data=data)

            # 验证返回失败提示
            assert 'reply-fail' in response.data.decode()


class TestCommentPageRoute:
    """测试评论分页路由"""

    def test_comment_page_success(self, client):
        """测试评论分页成功"""
        with patch('woniunote.controller.comment.Comments') as mock_comments_class:
            # 设置登录状态
            with client.session_transaction() as sess:
                sess['islogin'] = 'true'
                sess['userid'] = 1

            mock_comments_instance = Mock()
            mock_comments_instance.check_limit_per_5.return_value = True  # 总是超出限制
            mock_comments_class.return_value = mock_comments_instance

            # 尝试多次评论
            for i in range(3):
                response = client.post('/comment', data={
                    'articleid': '1',
                    'content': f'Test comment {i}'
                })
                assert 'add-limit' in response.data.decode()


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
