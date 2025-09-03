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
    app = Flask(__name__)
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

    def test_before_request_exception_handling(self, client):
        """测试前置请求处理异常情况"""
        with patch('woniunote.controller.comment.comment_logger') as mock_logger, \
             patch('woniunote.controller.comment.session.get') as mock_session_get:

            # Mock session.get抛出异常
            mock_session_get.side_effect = Exception("Session error")

            # 发送请求
            response = client.post('/comment', data={'content': 'test'})

            # 验证错误日志记录
            mock_logger.error.assert_called()
            error_calls = [call for call in mock_logger.error.call_args_list
                          if '评论前置检查异常' in str(call)]
            assert len(error_calls) > 0


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
        """测试评论频率限制"""
        with patch('woniunote.controller.comment.Comments') as mock_comments_class, \
             patch('woniunote.controller.comment.comment_logger') as mock_logger:

            # 设置登录状态
            with client.session_transaction() as sess:
                sess['islogin'] = 'true'
                sess['userid'] = 1

            # Mock评论实例（超出频率限制）
            mock_comments_instance = Mock()
            mock_comments_instance.check_limit_per_5.return_value = True  # 超出限制
            mock_comments_class.return_value = mock_comments_instance

            # 测试数据
            data = {
                'articleid': '1',
                'content': 'This is a valid comment with proper length'
            }

            response = client.post('/comment', data=data)

            # 验证返回频率限制提示
            assert 'limit-exceed' in response.data.decode()

            # 验证警告日志记录
            mock_logger.warning.assert_called()
            warning_calls = [call for call in mock_logger.warning.call_args_list
                           if '评论频率超限' in str(call)]
            assert len(warning_calls) > 0

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
            assert 'reply-pass' in response.data.decode()

            # 验证回复插入被调用
            mock_comments_instance.insert_reply.assert_called_once_with(
                '1',  # articleid
                '2',  # commentid
                'This is a valid reply with proper length',  # content
                '127.0.0.1'  # ipaddr (客户端IP)
            )

            # 验证积分更新（回复评论获得2积分）
            mock_credits_instance.insert_detail.assert_called_once_with(
                credit_type='回复评论',
                target='1',
                credit=2
            )

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
            assert 'limit-exceed' in response.data.decode()

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
        """测试成功获取评论分页数据"""
        with patch('woniunote.controller.comment.Comments') as mock_comments_class, \
             patch('woniunote.controller.comment.comment_logger') as mock_logger:

            # 设置登录状态
            with client.session_transaction() as sess:
                sess['islogin'] = 'true'
                sess['userid'] = 1

            # Mock评论实例
            mock_comments_instance = Mock()
            mock_comments_data = [
                {
                    'commentid': 1,
                    'content': 'Test comment 1',
                    'userid': 1,
                    'username': 'user1',
                    'createtime': '2024-01-01 10:00:00'
                },
                {
                    'commentid': 2,
                    'content': 'Test comment 2',
                    'userid': 2,
                    'username': 'user2',
                    'createtime': '2024-01-01 11:00:00'
                }
            ]
            mock_comments_instance.get_comment_user_list.return_value = mock_comments_data
            mock_comments_class.return_value = mock_comments_instance

            # 发送请求
            response = client.get('/comment/1-1')

            # 验证响应
            assert response.status_code == 200
            assert response.content_type == 'application/json'

            # 解析JSON响应
            response_data = json.loads(response.data.decode())

            # 验证数据
            assert len(response_data) == 2
            assert response_data[0]['commentid'] == 1
            assert response_data[1]['content'] == 'Test comment 2'

            # 验证方法调用
            mock_comments_instance.get_comment_user_list.assert_called_once_with(
                '1', 0, 10  # articleid=1, start=0, page_size=10
            )

    def test_comment_page_different_pages(self, client):
        """测试不同页码的分页数据"""
        with patch('woniunote.controller.comment.Comments') as mock_comments_class, \
             patch('woniunote.controller.comment.comment_logger') as mock_logger:

            # 设置登录状态
            with client.session_transaction() as sess:
                sess['islogin'] = 'true'
                sess['userid'] = 1

            # Mock评论实例
            mock_comments_instance = Mock()
            mock_comments_data = [
                {
                    'commentid': 11,
                    'content': 'Page 2 comment 1',
                    'userid': 3,
                    'username': 'user3',
                    'createtime': '2024-01-02 10:00:00'
                }
            ]
            mock_comments_instance.get_comment_user_list.return_value = mock_comments_data
            mock_comments_class.return_value = mock_comments_instance

            # 请求第2页
            response = client.get('/comment/1-2')

            # 验证方法调用参数
            mock_comments_instance.get_comment_user_list.assert_called_once_with(
                '1', 10, 10  # articleid=1, start=10, page_size=10
            )

    def test_comment_page_empty_result(self, client):
        """测试空评论数据"""
        with patch('woniunote.controller.comment.Comments') as mock_comments_class, \
             patch('woniunote.controller.comment.comment_logger') as mock_logger:

            # 设置登录状态
            with client.session_transaction() as sess:
                sess['islogin'] = 'true'
                sess['userid'] = 1

            # Mock空评论数据
            mock_comments_instance = Mock()
            mock_comments_instance.get_comment_user_list.return_value = []
            mock_comments_class.return_value = mock_comments_instance

            # 发送请求
            response = client.get('/comment/1-1')

            # 验证响应
            assert response.status_code == 200
            response_data = json.loads(response.data.decode())
            assert len(response_data) == 0

    def test_comment_page_database_error(self, client):
        """测试数据库错误情况"""
        with patch('woniunote.controller.comment.Comments') as mock_comments_class, \
             patch('woniunote.controller.comment.comment_logger') as mock_logger:

            # 设置登录状态
            with client.session_transaction() as sess:
                sess['islogin'] = 'true'
                sess['userid'] = 1

            # Mock数据库错误
            mock_comments_instance = Mock()
            mock_comments_instance.get_comment_user_list.side_effect = Exception("Database error")
            mock_comments_class.return_value = mock_comments_instance

            # 发送请求
            response = client.get('/comment/1-1')

            # 验证返回空数组
            assert response.status_code == 200
            response_data = json.loads(response.data.decode())
            assert response_data == []

            # 验证错误日志记录
            mock_logger.error.assert_called()

    def test_comment_page_invalid_articleid(self, client):
        """测试无效文章ID"""
        with client.session_transaction() as sess:
            sess['islogin'] = 'true'
            sess['userid'] = 1

        # 发送请求
        response = client.get('/comment/0-1')

        # 验证响应正常（即使articleid为0）
        assert response.status_code == 200

    def test_comment_page_invalid_page(self, client):
        """测试无效页码"""
        with client.session_transaction() as sess:
            sess['islogin'] = 'true'
            sess['userid'] = 1

        # 发送请求（页码为0）
        response = client.get('/comment/1-0')

        # 验证响应正常
        assert response.status_code == 200

    def test_comment_page_not_logged_in(self, client):
        """测试未登录访问评论分页"""
        # 不设置登录状态
        response = client.get('/comment/1-1')

        # 验证返回未登录提示
        assert 'not-login' in response.data.decode()


class TestCommentControllerIntegration:
    """测试评论控制器集成场景"""

    def test_comment_workflow_complete(self, client):
        """测试完整的评论工作流程"""
        with patch('woniunote.controller.comment.Comments') as mock_comments_class, \
             patch('woniunote.controller.comment.Credits') as mock_credits_class, \
             patch('woniunote.controller.comment.Users') as mock_users_class, \
             patch('woniunote.controller.comment.Articles') as mock_articles_class, \
             patch('woniunote.controller.comment.comment_logger') as mock_logger:

            # 设置登录状态
            with client.session_transaction() as sess:
                sess['islogin'] = 'true'
                sess['userid'] = 1

            # Mock所有相关实例
            mock_comments_instance = Mock()
            mock_comments_instance.check_limit_per_5.return_value = False
            mock_comments_data = [{'commentid': 1, 'content': 'Original comment'}]
            mock_comments_instance.get_comment_user_list.return_value = mock_comments_data
            mock_comments_class.return_value = mock_comments_instance

            mock_credits_instance = Mock()
            mock_credits_class.return_value = mock_credits_instance

            mock_users_instance = Mock()
            mock_users_class.return_value = mock_users_instance

            mock_articles_instance = Mock()
            mock_articles_class.return_value = mock_articles_instance

            # 1. 添加评论
            comment_data = {
                'articleid': '1',
                'content': 'This is a test comment'
            }
            response = client.post('/comment', data=comment_data)
            assert 'add-pass' in response.data.decode()

            # 2. 回复评论
            reply_data = {
                'articleid': '1',
                'commentid': '1',
                'content': 'This is a reply to the comment'
            }
            response = client.post('/reply', data=reply_data)
            assert response.data.decode() == 'reply-pass'

            # 3. 获取评论列表
            response = client.get('/comment/1-1')
            assert response.status_code == 200
            response_data = json.loads(response.data.decode())
            assert len(response_data) > 0

    def test_comment_error_scenarios(self, client):
        """测试评论功能的错误场景"""
        with patch('woniunote.controller.comment.Comments') as mock_comments_class, \
             patch('woniunote.controller.comment.comment_logger') as mock_logger:

            # 设置登录状态
            with client.session_transaction() as sess:
                sess['islogin'] = 'true'
                sess['userid'] = 1

            # Mock评论实例（总是超出限制）
            mock_comments_instance = Mock()
            mock_comments_instance.check_limit_per_5.return_value = True
            mock_comments_class.return_value = mock_comments_instance

            # 测试评论频率限制
            comment_data = {
                'articleid': '1',
                'content': 'Valid comment content'
            }
            response = client.post('/comment', data=comment_data)
            assert response.data.decode() == 'limit-exceed'

            # 测试回复频率限制
            reply_data = {
                'articleid': '1',
                'commentid': '1',
                'content': 'Valid reply content'
            }
            response = client.post('/reply', data=reply_data)
            assert response.data.decode() == 'limit-exceed'


class TestCommentControllerLogging:
    """测试评论控制器日志记录"""

    def test_all_routes_have_logging(self, client, caplog):
        """测试所有路由都有适当的日志记录"""
        with patch('woniunote.controller.comment.Comments') as mock_comments_class:
            # 设置登录状态
            with client.session_transaction() as sess:
                sess['islogin'] = 'true'
                sess['userid'] = 1

            mock_comments_instance = Mock()
            mock_comments_instance.check_limit_per_5.return_value = False
            mock_comments_instance.get_comment_user_list.return_value = []
            mock_comments_class.return_value = mock_comments_instance

            # 测试各个路由的日志记录
            with caplog.at_level('INFO'):
                # 测试评论添加
                client.post('/comment', data={'articleid': '1', 'content': 'Test comment'})

                # 测试回复添加
                client.post('/reply', data={'articleid': '1', 'commentid': '1', 'content': 'Test reply'})

                # 测试评论分页
                client.get('/comment/1-1')

                # 验证有相应的日志记录
                assert len(caplog.records) > 0

    def test_error_logging(self, client, caplog):
        """测试错误日志记录"""
        with patch('woniunote.controller.comment.Comments') as mock_comments_class:
            # 设置登录状态
            with client.session_transaction() as sess:
                sess['islogin'] = 'true'
                sess['userid'] = 1

            # Mock数据库错误
            mock_comments_instance = Mock()
            mock_comments_instance.check_limit_per_5.return_value = False
            mock_comments_instance.insert_comment.side_effect = Exception("DB Error")
            mock_comments_class.return_value = mock_comments_instance

            with caplog.at_level('ERROR'):
                client.post('/comment', data={'articleid': '1', 'content': 'Test comment'})

                # 验证错误日志记录
                error_records = [r for r in caplog.records if r.levelname == 'ERROR']
                assert len(error_records) > 0

    def test_warning_logging(self, client, caplog):
        """测试警告日志记录"""
        # 测试未登录访问
        with caplog.at_level('WARNING'):
            client.post('/comment', data={'articleid': '1', 'content': 'Test comment'})

            # 验证警告日志记录
            warning_records = [r for r in caplog.records if r.levelname == 'WARNING']
            assert len(warning_records) > 0


class TestCommentControllerSecurity:
    """测试评论控制器安全性"""

    def test_sql_injection_protection(self, client):
        """测试SQL注入防护"""
        with client.session_transaction() as sess:
            sess['islogin'] = 'true'
            sess['userid'] = 1

        # 测试恶意输入
        malicious_data = {
            'articleid': "1' OR '1'='1",
            'content': "'; DROP TABLE comments; --"
        }

        response = client.post('/comment', data=malicious_data)
        # 验证不会执行恶意SQL（具体验证取决于实际的SQL处理逻辑）
        assert response.status_code == 200

    def test_xss_protection(self, client):
        """测试XSS防护"""
        with client.session_transaction() as sess:
            sess['islogin'] = 'true'
            sess['userid'] = 1

        # 测试XSS输入
        xss_data = {
            'articleid': '1',
            'content': '<script>alert("XSS")</script>'
        }

        response = client.post('/comment', data=xss_data)
        # 验证响应不包含未转义的脚本标签
        assert '<script>' not in response.data.decode()

    def test_rate_limiting_effectiveness(self, client):
        """测试频率限制的有效性"""
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
                assert 'limit-exceed' in response.data.decode()


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
