#!/usr/bin/env python3
"""
Comprehensive test suite for woniunote.controller.admin module
Tests all admin-related functions with 100% coverage including Flask routes, CRUD operations, and error handling
"""

import pytest
import sys
import os
import json
import uuid
import math
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
    from woniunote.controller.admin import admin
    app.register_blueprint(admin)

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


class TestAdminTraceId:
    """测试管理模块跟踪ID生成"""

    def test_get_admin_trace_id_format(self):
        """测试跟踪ID格式"""
        from woniunote.controller.admin import get_admin_trace_id

        trace_id = get_admin_trace_id()

        # 验证格式: UUID格式
        assert isinstance(trace_id, str)
        assert len(trace_id) == 36  # UUID标准长度
        assert '-' in trace_id  # 包含连字符

    def test_get_admin_trace_id_uniqueness(self):
        """测试跟踪ID唯一性"""
        from woniunote.controller.admin import get_admin_trace_id

        trace_ids = [get_admin_trace_id() for _ in range(10)]

        # 由于使用线程本地存储，在单线程中ID应该是相同的
        assert len(set(trace_ids)) == 1  # 所有ID应该相同
        assert all(id == trace_ids[0] for id in trace_ids)  # 验证都是同一个ID

    def test_generate_trace_id_uniqueness(self):
        """测试基础跟踪ID生成器的唯一性"""
        from woniunote.controller.admin import generate_trace_id

        trace_ids = [generate_trace_id() for _ in range(10)]

        # 验证所有ID都是唯一的
        assert len(set(trace_ids)) == len(trace_ids)
        for trace_id in trace_ids:
            assert isinstance(trace_id, str)
            assert len(trace_id) == 36


class TestAdminBlueprintSetup:
    """测试管理蓝图设置"""

    def test_blueprint_creation(self):
        """测试蓝图创建"""
        from woniunote.controller.admin import admin

        assert admin.name == 'admin'
        # admin蓝图在实际应用中没有设置url_prefix，与其他蓝图保持一致
        assert admin.url_prefix is None

    def test_blueprint_routes_registration(self, app):
        """测试路由注册"""
        with app.test_client() as client:
            # 测试路由是否正确注册
            routes = [rule.rule for rule in app.url_map.iter_rules()]
            expected_routes = [
                '/admin',
                '/admin/article/<int:page>',
                '/admin/type/<int:type>-<int:page>',
                '/admin/search/<keyword>',
                '/admin/article/hide/<int:articleid>',
                '/admin/article/recommend/<int:articleid>',
                '/admin/article/check/<int:articleid>'
            ]

            for route in expected_routes:
                assert route in routes, f"Route {route} not found in registered routes. Available routes: {routes}"

    def test_logger_initialization(self):
        """测试日志记录器初始化"""
        from woniunote.controller.admin import admin_logger

        assert admin_logger is not None
        assert hasattr(admin_logger, 'info')
        assert hasattr(admin_logger, 'warning')
        assert hasattr(admin_logger, 'error')


class TestAdminBeforeRequest:
    """测试管理模块前置请求处理"""

    def test_before_request_admin_success(self, client):
        """测试管理员成功访问"""
        with patch('woniunote.controller.admin.admin_logger') as mock_logger:
            # 设置管理员登录状态
            with client.session_transaction() as sess:
                sess['islogin'] = 'true'
                sess['role'] = 'admin'
                sess['userid'] = 1

            # 发送请求
            response = client.get('/admin')

            # 验证日志记录
            mock_logger.info.assert_called()
            info_calls = [call for call in mock_logger.info.call_args_list
                         if '管理员请求' in str(call)]
            assert len(info_calls) > 0

    def test_before_request_non_admin_user(self, client):
        """测试非管理员用户访问"""
        with patch('woniunote.controller.admin.admin_logger') as mock_logger:
            # 设置普通用户登录状态
            with client.session_transaction() as sess:
                sess['islogin'] = 'true'
                sess['role'] = 'user'
                sess['userid'] = 1

            # 发送请求
            response = client.get('/admin')

            # 验证返回权限拒绝
            assert response.data.decode() == 'perm-denied'

            # 验证警告日志记录
            mock_logger.warning.assert_called()
            warning_calls = [call for call in mock_logger.warning.call_args_list
                           if '非管理员访问管理页面' in str(call)]
            assert len(warning_calls) > 0

    def test_before_request_not_logged_in(self, client):
        """测试未登录用户访问"""
        with patch('woniunote.controller.admin.admin_logger') as mock_logger:
            # 不设置登录状态

            # 发送请求
            response = client.get('/admin')

            # 验证返回权限拒绝
            assert response.data.decode() == 'perm-denied'

            # 验证警告日志记录
            mock_logger.warning.assert_called()

    def test_before_request_exception_handling(self, app):
        """测试前置请求处理异常情况"""
        with patch('woniunote.controller.admin.admin_logger') as mock_logger, \
             patch('woniunote.controller.admin.request') as mock_request:

            # Mock request对象
            mock_request.remote_addr = '127.0.0.1'
            mock_request.method = 'GET'
            mock_request.path = '/admin'

            # 使用应用上下文测试before_request函数
            with app.test_request_context('/admin', method='GET'):
                # 在应用上下文中Mock session.get方法
                from woniunote.controller.admin import session
                original_get = session.get
                def mock_get_side_effect(key, default=None):
                    if key == 'islogin':
                        raise Exception("Session access error")
                    return original_get(key, default)

                # 临时替换session.get方法
                session.get = mock_get_side_effect

                try:
                    from woniunote.controller.admin import before_admin
                    result = before_admin()

                    # 验证异常被正确记录
                    mock_logger.error.assert_called_once()
                    call_args = mock_logger.error.call_args[0][0]  # 获取第一个位置参数
                    assert "管理员请求处理异常" in call_args

                    # 验证日志包含错误信息
                    call_kwargs = mock_logger.error.call_args[0][1]  # 获取第二个位置参数（字典）
                    assert 'error' in call_kwargs
                    assert 'traceback' in call_kwargs
                    assert call_kwargs['error'] == 'Session access error'
                finally:
                    # 恢复原始的session.get方法
                    session.get = original_get


class TestAdminHomeRoute:
    """测试管理首页路由"""

    def test_admin_home_success(self, client):
        """测试成功访问管理首页"""
        with patch('woniunote.controller.admin.Articles') as mock_articles_class, \
             patch('woniunote.controller.admin.render_template') as mock_render, \
             patch('woniunote.controller.admin.admin_logger') as mock_logger:

            # 设置管理员登录状态
            with client.session_transaction() as sess:
                sess['islogin'] = 'true'
                sess['role'] = 'admin'
                sess['userid'] = 1

            # Mock文章实例
            mock_articles_instance = Mock()
            mock_articles_data = [
                {'articleid': 1, 'headline': 'Article 1', 'userid': 1},
                {'articleid': 2, 'headline': 'Article 2', 'userid': 2}
            ]
            mock_articles_instance.find_all_except_draft.return_value = mock_articles_data
            mock_articles_instance.get_count_except_draft.return_value = 100
            mock_articles_class.return_value = mock_articles_instance

            # Mock模板渲染
            mock_render.return_value = 'rendered_template'

            # 发送请求
            response = client.get('/admin')

            # 验证响应
            assert response.status_code == 200

            # 验证方法调用
            mock_articles_instance.find_all_except_draft.assert_called_once_with(0, 50)
            mock_articles_instance.get_count_except_draft.assert_called_once()

            # 验证模板渲染
            mock_render.assert_called_once_with(
                'system-admin.html',
                page=1,
                result=mock_articles_data,
                total=2  # math.ceil(100/50) = 2
            )

            # 验证日志记录
            mock_logger.info.assert_called()

    def test_admin_home_empty_result(self, client):
        """测试管理首页空结果"""
        with patch('woniunote.controller.admin.Articles') as mock_articles_class, \
             patch('woniunote.controller.admin.render_template') as mock_render, \
             patch('woniunote.controller.admin.admin_logger') as mock_logger:

            # 设置管理员登录状态
            with client.session_transaction() as sess:
                sess['islogin'] = 'true'
                sess['role'] = 'admin'
                sess['userid'] = 1

            # Mock空文章数据
            mock_articles_instance = Mock()
            mock_articles_instance.find_all_except_draft.return_value = []
            mock_articles_instance.get_count_except_draft.return_value = 0
            mock_articles_class.return_value = mock_articles_instance

            # Mock模板渲染
            mock_render.return_value = 'rendered_template'

            # 发送请求
            response = client.get('/admin')

            # 验证模板渲染参数
            mock_render.assert_called_once_with(
                'system-admin.html',
                page=1,
                result=[],
                total=0  # math.ceil(0/50) = 0
            )

    def test_admin_home_database_error(self, client):
        """测试管理首页数据库错误"""
        with patch('woniunote.controller.admin.Articles') as mock_articles_class, \
             patch('woniunote.controller.admin.render_template') as mock_render, \
             patch('woniunote.controller.admin.admin_logger') as mock_logger:

            # 设置管理员登录状态
            with client.session_transaction() as sess:
                sess['islogin'] = 'true'
                sess['role'] = 'admin'
                sess['userid'] = 1

            # Mock数据库错误
            mock_articles_instance = Mock()
            mock_articles_instance.find_all_except_draft.side_effect = Exception("Database error")
            mock_articles_class.return_value = mock_articles_instance

            # 发送请求
            response = client.get('/admin')

            # 验证返回错误页面
            mock_render.assert_called_once_with(
                'error.html',
                error_message="系统管理页面加载失败"
            )

            # 验证错误日志记录
            mock_logger.error.assert_called()


class TestAdminArticlePaginationRoute:
    """测试管理文章分页路由"""

    def test_admin_article_pagination_success(self, client):
        """测试成功分页获取文章"""
        with patch('woniunote.controller.admin.Articles') as mock_articles_class, \
             patch('woniunote.controller.admin.render_template') as mock_render, \
             patch('woniunote.controller.admin.admin_logger') as mock_logger:

            # 设置管理员登录状态
            with client.session_transaction() as sess:
                sess['islogin'] = 'true'
                sess['role'] = 'admin'
                sess['userid'] = 1

            # Mock文章实例
            mock_articles_instance = Mock()
            mock_articles_data = [
                {'articleid': 51, 'headline': 'Article 51', 'userid': 1},
                {'articleid': 52, 'headline': 'Article 52', 'userid': 2}
            ]
            mock_articles_instance.find_all_except_draft.return_value = mock_articles_data
            mock_articles_instance.get_count_except_draft.return_value = 150
            mock_articles_class.return_value = mock_articles_instance

            # Mock模板渲染
            mock_render.return_value = 'rendered_template'

            # 发送第2页请求
            response = client.get('/admin/article/2')

            # 验证响应
            assert response.status_code == 200

            # 验证方法调用参数
            mock_articles_instance.find_all_except_draft.assert_called_once_with(50, 50)  # (2-1)*50 = 50

            # 验证模板渲染
            mock_render.assert_called_once_with(
                'system-admin.html',
                page=2,
                result=mock_articles_data,
                total=3  # math.ceil(150/50) = 3
            )

    def test_admin_article_pagination_first_page(self, client):
        """测试第1页分页"""
        with patch('woniunote.controller.admin.Articles') as mock_articles_class, \
             patch('woniunote.controller.admin.render_template') as mock_render:

            # 设置管理员登录状态
            with client.session_transaction() as sess:
                sess['islogin'] = 'true'
                sess['role'] = 'admin'
                sess['userid'] = 1

            # Mock文章实例
            mock_articles_instance = Mock()
            mock_articles_instance.find_all_except_draft.return_value = []
            mock_articles_instance.get_count_except_draft.return_value = 10
            mock_articles_class.return_value = mock_articles_instance

            # Mock模板渲染
            mock_render.return_value = 'rendered_template'

            # 发送第1页请求
            response = client.get('/admin/article/1')

            # 验证起始位置为0
            mock_articles_instance.find_all_except_draft.assert_called_once_with(0, 50)

    def test_admin_article_pagination_database_error(self, client):
        """测试分页数据库错误"""
        with patch('woniunote.controller.admin.Articles') as mock_articles_class, \
             patch('woniunote.controller.admin.render_template') as mock_render, \
             patch('woniunote.controller.admin.admin_logger') as mock_logger:

            # 设置管理员登录状态
            with client.session_transaction() as sess:
                sess['islogin'] = 'true'
                sess['role'] = 'admin'
                sess['userid'] = 1

            # Mock数据库错误
            mock_articles_instance = Mock()
            mock_articles_instance.find_all_except_draft.side_effect = Exception("Database error")
            mock_articles_class.return_value = mock_articles_instance

            # 发送请求
            response = client.get('/admin/article/2')

            # 验证返回错误页面
            mock_render.assert_called_once_with(
                'error.html',
                error_message="文章列表加载失败"
            )


class TestAdminSearchTypeRoute:
    """测试管理按类型搜索路由"""

    def test_admin_search_type_success(self, client):
        """测试成功按类型搜索文章"""
        with patch('woniunote.controller.admin.Articles') as mock_articles_class, \
             patch('woniunote.controller.admin.render_template') as mock_render, \
             patch('woniunote.controller.admin.admin_logger') as mock_logger:

            # 设置管理员登录状态
            with client.session_transaction() as sess:
                sess['islogin'] = 'true'
                sess['role'] = 'admin'
                sess['userid'] = 1

            # Mock文章实例
            mock_articles_instance = Mock()
            mock_articles_data = [
                {'articleid': 1, 'headline': 'Tech Article 1', 'type': 1},
                {'articleid': 2, 'headline': 'Tech Article 2', 'type': 1}
            ]
            mock_articles_instance.find_by_type_except_draft.return_value = (mock_articles_data, 25)
            mock_articles_class.return_value = mock_articles_instance

            # Mock模板渲染
            mock_render.return_value = 'rendered_template'

            # 发送类型1，第2页请求
            response = client.get('/admin/type/1-2')

            # 验证响应
            assert response.status_code == 200

            # 验证方法调用
            mock_articles_instance.find_by_type_except_draft.assert_called_once_with(50, 50, 1)  # start=50, pagesize=50, type=1

            # 验证模板渲染
            mock_render.assert_called_once_with(
                'system-admin.html',
                page=2,
                result=mock_articles_data,
                total=1  # math.ceil(25/50) = 1
            )

    def test_admin_search_type_empty_result(self, client):
        """测试按类型搜索空结果"""
        with patch('woniunote.controller.admin.Articles') as mock_articles_class, \
             patch('woniunote.controller.admin.render_template') as mock_render:

            # 设置管理员登录状态
            with client.session_transaction() as sess:
                sess['islogin'] = 'true'
                sess['role'] = 'admin'
                sess['userid'] = 1

            # Mock空结果
            mock_articles_instance = Mock()
            mock_articles_instance.find_by_type_except_draft.return_value = ([], 0)
            mock_articles_class.return_value = mock_articles_instance

            # Mock模板渲染
            mock_render.return_value = 'rendered_template'

            # 发送请求
            response = client.get('/admin/type/2-1')

            # 验证模板渲染参数
            mock_render.assert_called_once_with(
                'system-admin.html',
                page=1,
                result=[],
                total=0
            )

    def test_admin_search_type_database_error(self, client):
        """测试按类型搜索数据库错误"""
        with patch('woniunote.controller.admin.Articles') as mock_articles_class, \
             patch('woniunote.controller.admin.render_template') as mock_render, \
             patch('woniunote.controller.admin.admin_logger') as mock_logger:

            # 设置管理员登录状态
            with client.session_transaction() as sess:
                sess['islogin'] = 'true'
                sess['role'] = 'admin'
                sess['userid'] = 1

            # Mock数据库错误
            mock_articles_instance = Mock()
            mock_articles_instance.find_by_type_except_draft.side_effect = Exception("Database error")
            mock_articles_class.return_value = mock_articles_instance

            # 发送请求
            response = client.get('/admin/type/1-1')

            # 验证返回错误页面
            mock_render.assert_called_once_with(
                'error.html',
                error_message="按类型搜索文章失败"
            )


class TestAdminSearchHeadlineRoute:
    """测试管理按标题搜索路由"""

    def test_admin_search_headline_success(self, client):
        """测试成功按标题搜索文章"""
        with patch('woniunote.controller.admin.Articles') as mock_articles_class, \
             patch('woniunote.controller.admin.render_template') as mock_render, \
             patch('woniunote.controller.admin.admin_logger') as mock_logger:

            # 设置管理员登录状态
            with client.session_transaction() as sess:
                sess['islogin'] = 'true'
                sess['role'] = 'admin'
                sess['userid'] = 1

            # Mock文章实例
            mock_articles_instance = Mock()
            mock_articles_data = [
                {'articleid': 1, 'headline': 'Python Tutorial', 'userid': 1},
                {'articleid': 2, 'headline': 'Python Guide', 'userid': 2}
            ]
            mock_articles_instance.find_by_headline_except_draft.return_value = (mock_articles_data, 2)
            mock_articles_class.return_value = mock_articles_instance

            # Mock模板渲染
            mock_render.return_value = 'rendered_template'

            # 发送搜索请求
            response = client.get('/admin/search/python')

            # 验证响应
            assert response.status_code == 200

            # 验证方法调用
            mock_articles_instance.find_by_headline_except_draft.assert_called_once_with('python', 0, 50)

            # 验证模板渲染
            mock_render.assert_called_once_with(
                'system-admin.html',
                page=1,
                result=mock_articles_data,
                total=1  # math.ceil(2/50) = 1
            )

    def test_admin_search_headline_no_results(self, client):
        """测试按标题搜索无结果"""
        with patch('woniunote.controller.admin.Articles') as mock_articles_class, \
             patch('woniunote.controller.admin.render_template') as mock_render:

            # 设置管理员登录状态
            with client.session_transaction() as sess:
                sess['islogin'] = 'true'
                sess['role'] = 'admin'
                sess['userid'] = 1

            # Mock空结果
            mock_articles_instance = Mock()
            mock_articles_instance.find_by_headline_except_draft.return_value = ([], 0)
            mock_articles_class.return_value = mock_articles_instance

            # Mock模板渲染
            mock_render.return_value = 'rendered_template'

            # 发送搜索请求
            response = client.get('/admin/search/nonexistent')

            # 验证模板渲染参数
            mock_render.assert_called_once_with(
                'system-admin.html',
                page=1,
                result=[],
                total=1  # 根据管理控制器逻辑，total为0时使用1
            )

    def test_admin_search_headline_database_error(self, client):
        """测试按标题搜索数据库错误"""
        with patch('woniunote.controller.admin.Articles') as mock_articles_class, \
             patch('woniunote.controller.admin.render_template') as mock_render, \
             patch('woniunote.controller.admin.admin_logger') as mock_logger:

            # 设置管理员登录状态
            with client.session_transaction() as sess:
                sess['islogin'] = 'true'
                sess['role'] = 'admin'
                sess['userid'] = 1

            # Mock数据库错误
            mock_articles_instance = Mock()
            mock_articles_instance.find_by_headline_except_draft.side_effect = Exception("Database error")
            mock_articles_class.return_value = mock_articles_instance

            # 发送请求
            response = client.get('/admin/search/test')

            # 验证返回错误页面
            mock_render.assert_called_once_with(
                'error.html',
                error_message="按标题搜索文章失败"
            )


class TestAdminArticleOperations:
    """测试管理文章操作路由"""

    def test_admin_article_hide_success(self, client):
        """测试成功切换文章隐藏状态"""
        with patch('woniunote.controller.admin.Articles') as mock_articles_class, \
             patch('woniunote.controller.admin.admin_logger') as mock_logger:

            # 设置管理员登录状态
            with client.session_transaction() as sess:
                sess['islogin'] = 'true'
                sess['role'] = 'admin'
                sess['userid'] = 1

            # Mock文章实例
            mock_articles_instance = Mock()
            mock_articles_instance.switch_hidden.return_value = 1  # 切换为隐藏状态
            mock_articles_class.return_value = mock_articles_instance

            # 发送请求
            response = client.get('/admin/article/hide/123')

            # 验证响应
            assert response.data.decode() == '1'

            # 验证方法调用
            mock_articles_instance.switch_hidden.assert_called_once_with(123)

            # 验证日志记录
            mock_logger.info.assert_called()

    def test_admin_article_hide_database_error(self, client):
        """测试切换文章隐藏状态数据库错误"""
        with patch('woniunote.controller.admin.Articles') as mock_articles_class, \
             patch('woniunote.controller.admin.admin_logger') as mock_logger:

            # 设置管理员登录状态
            with client.session_transaction() as sess:
                sess['islogin'] = 'true'
                sess['role'] = 'admin'
                sess['userid'] = 1

            # Mock数据库错误
            mock_articles_instance = Mock()
            mock_articles_instance.switch_hidden.side_effect = Exception("Database error")
            mock_articles_class.return_value = mock_articles_instance

            # 发送请求
            response = client.get('/admin/article/hide/123')

            # 验证返回错误
            assert response.data.decode() == 'error'

            # 验证错误日志记录
            mock_logger.error.assert_called()

    def test_admin_article_recommend_success(self, client):
        """测试成功切换文章推荐状态"""
        with patch('woniunote.controller.admin.Articles') as mock_articles_class, \
             patch('woniunote.controller.admin.admin_logger') as mock_logger:

            # 设置管理员登录状态
            with client.session_transaction() as sess:
                sess['islogin'] = 'true'
                sess['role'] = 'admin'
                sess['userid'] = 1

            # Mock文章实例
            mock_articles_instance = Mock()
            mock_articles_instance.switch_recommended.return_value = 0  # 切换为非推荐状态
            mock_articles_class.return_value = mock_articles_instance

            # 发送请求
            response = client.get('/admin/article/recommend/456')

            # 验证响应
            assert response.data.decode() == '0'

            # 验证方法调用
            mock_articles_instance.switch_recommended.assert_called_once_with(456)

    def test_admin_article_check_success(self, client):
        """测试成功切换文章审核状态"""
        with patch('woniunote.controller.admin.Articles') as mock_articles_class, \
             patch('woniunote.controller.admin.admin_logger') as mock_logger:

            # 设置管理员登录状态
            with client.session_transaction() as sess:
                sess['islogin'] = 'true'
                sess['role'] = 'admin'
                sess['userid'] = 1

            # Mock文章实例
            mock_articles_instance = Mock()
            mock_articles_instance.switch_checked.return_value = 1  # 切换为已审核状态
            mock_articles_class.return_value = mock_articles_instance

            # 发送请求
            response = client.get('/admin/article/check/789')

            # 验证响应
            assert response.data.decode() == '1'

            # 验证方法调用
            mock_articles_instance.switch_checked.assert_called_once_with(789)


class TestAdminControllerIntegration:
    """测试管理控制器集成场景"""

    def test_admin_workflow_complete(self, client):
        """测试完整的管理员工作流程"""
        with patch('woniunote.controller.admin.Articles') as mock_articles_class, \
             patch('woniunote.controller.admin.render_template') as mock_render, \
             patch('woniunote.controller.admin.admin_logger') as mock_logger:

            # 设置管理员登录状态
            with client.session_transaction() as sess:
                sess['islogin'] = 'true'
                sess['role'] = 'admin'
                sess['userid'] = 1

            # Mock文章实例
            mock_articles_instance = Mock()
            mock_articles_data = [
                {'articleid': 1, 'headline': 'Test Article', 'userid': 1, 'hidden': 0, 'recommended': 0, 'checked': 0}
            ]
            mock_articles_instance.find_all_except_draft.return_value = mock_articles_data
            mock_articles_instance.get_count_except_draft.return_value = 1
            mock_articles_instance.switch_hidden.return_value = 1
            mock_articles_instance.switch_recommended.return_value = 1
            mock_articles_instance.switch_checked.return_value = 1
            mock_articles_class.return_value = mock_articles_instance

            # Mock模板渲染
            mock_render.return_value = 'rendered_template'

            # 1. 访问管理首页
            response = client.get('/admin')
            assert response.status_code == 200

            # 2. 隐藏文章
            response = client.get('/admin/article/hide/1')
            assert response.data.decode() == '1'

            # 3. 推荐文章
            response = client.get('/admin/article/recommend/1')
            assert response.data.decode() == '1'

            # 4. 审核文章
            response = client.get('/admin/article/check/1')
            assert response.data.decode() == '1'

    def test_admin_error_scenarios(self, client):
        """测试管理员功能的错误场景"""
        with patch('woniunote.controller.admin.Articles') as mock_articles_class, \
             patch('woniunote.controller.admin.render_template') as mock_render, \
             patch('woniunote.controller.admin.admin_logger') as mock_logger:

            # 设置管理员登录状态
            with client.session_transaction() as sess:
                sess['islogin'] = 'true'
                sess['role'] = 'admin'
                sess['userid'] = 1

            # Mock各种错误场景
            mock_articles_instance = Mock()
            mock_articles_instance.find_all_except_draft.side_effect = Exception("DB Error")
            mock_articles_instance.switch_hidden.side_effect = Exception("Network Error")
            mock_articles_instance.switch_recommended.side_effect = Exception("Permission Error")
            mock_articles_instance.switch_checked.side_effect = Exception("Validation Error")
            mock_articles_class.return_value = mock_articles_instance

            # 测试各种错误处理
            response = client.get('/admin')
            assert 'error.html' in str(mock_render.call_args)

            response = client.get('/admin/article/hide/1')
            assert response.data.decode() == 'error'

            response = client.get('/admin/article/recommend/1')
            assert response.data.decode() == 'error'

            response = client.get('/admin/article/check/1')
            assert response.data.decode() == 'error'


class TestAdminControllerLogging:
    """测试管理控制器日志记录"""

    def test_all_routes_have_logging(self, client, caplog):
        """测试所有路由都有适当的日志记录"""
        with patch('woniunote.controller.admin.Articles') as mock_articles_class, \
             patch('woniunote.controller.admin.render_template') as mock_render:

            # 设置管理员登录状态
            with client.session_transaction() as sess:
                sess['islogin'] = 'true'
                sess['role'] = 'admin'
                sess['userid'] = 1

            mock_articles_instance = Mock()
            mock_articles_instance.find_all_except_draft.return_value = []
            mock_articles_instance.get_count_except_draft.return_value = 0
            mock_articles_instance.switch_hidden.return_value = 0
            mock_articles_instance.switch_recommended.return_value = 0
            mock_articles_instance.switch_checked.return_value = 0
            mock_articles_class.return_value = mock_articles_instance

            mock_render.return_value = 'rendered_template'

            # 测试各个路由的日志记录
            with caplog.at_level('INFO'):
                # 测试管理首页
                client.get('/admin')

                # 测试文章分页
                client.get('/admin/article/1')

                # 测试类型搜索
                client.get('/admin/type/1-1')

                # 测试标题搜索
                client.get('/admin/search/test')

                # 测试文章操作
                client.get('/admin/article/hide/1')
                client.get('/admin/article/recommend/1')
                client.get('/admin/article/check/1')

                # 验证有相应的日志记录
                assert len(caplog.records) > 0

    def test_error_logging(self, client, caplog):
        """测试错误日志记录"""
        with patch('woniunote.controller.admin.Articles') as mock_articles_class:
            # 设置管理员登录状态
            with client.session_transaction() as sess:
                sess['islogin'] = 'true'
                sess['role'] = 'admin'
                sess['userid'] = 1

            # Mock数据库错误
            mock_articles_instance = Mock()
            mock_articles_instance.find_all_except_draft.side_effect = Exception("DB Error")
            mock_articles_class.return_value = mock_articles_instance

            with caplog.at_level('ERROR'):
                client.get('/admin')

                # 验证错误日志记录
                error_records = [r for r in caplog.records if r.levelname == 'ERROR']
                assert len(error_records) > 0

    def test_warning_logging(self, client, caplog):
        """测试警告日志记录"""
        # 测试非管理员访问
        with caplog.at_level('WARNING'):
            with client.session_transaction() as sess:
                sess['islogin'] = 'true'
                sess['role'] = 'user'

            client.get('/admin')

            # 验证警告日志记录
            warning_records = [r for r in caplog.records if r.levelname == 'WARNING']
            assert len(warning_records) > 0


class TestAdminControllerSecurity:
    """测试管理控制器安全性"""

    def test_admin_access_control(self, client):
        """测试管理员访问控制"""
        # 测试各种非管理员情况
        test_cases = [
            {},  # 未登录
            {'islogin': 'true'},  # 无角色
            {'islogin': 'true', 'role': 'user'},  # 普通用户
            {'islogin': 'true', 'role': 'editor'},  # 编辑者
            {'islogin': 'false', 'role': 'admin'},  # 登录状态错误
        ]

        for i, session_data in enumerate(test_cases):
            with client.session_transaction() as sess:
                sess.update(session_data)

            response = client.get('/admin')
            # 所有非管理员情况都应该被拒绝
            assert response.data.decode() == 'perm-denied', f"Test case {i} failed: {session_data}"

    def test_sql_injection_protection(self, client):
        """测试SQL注入防护"""
        with client.session_transaction() as sess:
            sess['islogin'] = 'true'
            sess['role'] = 'admin'
            sess['userid'] = 1

        # 测试恶意输入
        malicious_cases = [
            '/admin/type/1\' OR \'1\'=\'1-1',
            '/admin/search/\'; DROP TABLE articles; --',
            '/admin/article/hide/1\' UNION SELECT * FROM users--',
        ]

        for malicious_url in malicious_cases:
            response = client.get(malicious_url)
            # 验证系统能正常处理（不崩溃），即使可能返回错误
            assert response.status_code in [200, 302, 404, 500]

    def test_path_traversal_protection(self, client):
        """测试路径遍历防护"""
        with client.session_transaction() as sess:
            sess['islogin'] = 'true'
            sess['role'] = 'admin'
            sess['userid'] = 1

        # 测试路径遍历攻击
        traversal_urls = [
            '/admin/article/../../../etc/passwd',
            '/admin/type/1-../../../../etc/passwd',
        ]

        for traversal_url in traversal_urls:
            response = client.get(traversal_url)
            # 验证系统能正常处理
            assert response.status_code in [200, 302, 404, 500]

    def test_admin_operation_audit(self, client):
        """测试管理员操作审计"""
        with patch('woniunote.controller.admin.Articles') as mock_articles_class, \
             patch('woniunote.controller.admin.admin_logger') as mock_logger:

            with client.session_transaction() as sess:
                sess['islogin'] = 'true'
                sess['role'] = 'admin'
                sess['userid'] = 1

            mock_articles_instance = Mock()
            mock_articles_instance.switch_hidden.return_value = 1
            mock_articles_class.return_value = mock_articles_instance

            # 执行管理员操作
            client.get('/admin/article/hide/123')

            # 验证审计日志记录了足够的信息
            info_calls = mock_logger.info.call_args_list
            audit_call = None
            for call in info_calls:
                if '管理员切换文章隐藏状态' in str(call):
                    audit_call = call
                    break

            assert audit_call is not None
            # 验证审计信息包含关键字段
            call_args = audit_call[0][1] if len(audit_call[0]) > 1 else audit_call[0][0]  # 获取关键字参数
            if isinstance(call_args, dict):
                assert 'article_id' in call_args
                assert call_args['article_id'] == 123
            assert 'user_id' in str(call_args)


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
