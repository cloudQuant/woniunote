#!/usr/bin/env python3
"""
WoniuNote 统一响应系统测试
"""

import pytest
from unittest.mock import patch, MagicMock
import time
from woniunote.common.unified_response import (
    PageInfo, ApiResponse, PaginatedResponse, ResponseBuilder,
    FlaskResponseHelper, standardize_response, paginate_query_result,
    format_article_response, format_user_response, success_response,
    error_response, paginated_response
)


class TestPageInfo:
    """测试分页信息类"""

    def test_page_info_creation(self):
        """测试PageInfo创建"""
        page_info = PageInfo(
            page=1,
            page_size=20,
            total=100,
            total_pages=5,
            has_next=True,
            has_prev=False
        )

        assert page_info.page == 1
        assert page_info.page_size == 20
        assert page_info.total == 100
        assert page_info.total_pages == 5
        assert page_info.has_next is True
        assert page_info.has_prev is False

    def test_page_info_asdict(self):
        """测试PageInfo转换为字典"""
        from dataclasses import asdict
        page_info = PageInfo(page=1, page_size=20, total=100, total_pages=5, has_next=True, has_prev=False)
        result = asdict(page_info)

        expected = {
            'page': 1,
            'page_size': 20,
            'total': 100,
            'total_pages': 5,
            'has_next': True,
            'has_prev': False
        }
        assert result == expected


class TestApiResponse:
    """测试API响应类"""

    def test_api_response_creation(self):
        """测试ApiResponse创建"""
        response = ApiResponse(
            success=True,
            data={"test": "data"},
            message="操作成功",
            error_code=None,
            request_id="req-123"
        )

        assert response.success is True
        assert response.data == {"test": "data"}
        assert response.message == "操作成功"
        assert response.error_code is None
        assert response.request_id == "req-123"
        assert isinstance(response.timestamp, int)

    def test_api_response_auto_timestamp(self):
        """测试ApiResponse自动设置时间戳"""
        response = ApiResponse(success=True)
        assert isinstance(response.timestamp, int)
        assert response.timestamp > 0

    def test_api_response_asdict(self):
        """测试ApiResponse转换为字典"""
        from dataclasses import asdict
        response = ApiResponse(success=True, message="测试", request_id="req-123")
        result = asdict(response)

        assert result['success'] is True
        assert result['message'] == "测试"
        assert result['request_id'] == "req-123"
        assert 'timestamp' in result


class TestPaginatedResponse:
    """测试分页响应类"""

    def test_paginated_response_creation(self):
        """测试PaginatedResponse创建"""
        page_info = PageInfo(page=1, page_size=20, total=100, total_pages=5, has_next=True, has_prev=False)
        response = PaginatedResponse(
            success=True,
            data=[1, 2, 3],
            message="查询成功",
            pagination=page_info
        )

        assert response.success is True
        assert response.data == [1, 2, 3]
        assert response.message == "查询成功"
        assert response.pagination == page_info


class TestResponseBuilder:
    """测试响应构建器"""

    def test_success_response(self):
        """测试成功响应构建"""
        result = ResponseBuilder.success(data={"id": 1}, message="创建成功", request_id="req-123")

        assert result['success'] is True
        assert result['data'] == {"id": 1}
        assert result['message'] == "创建成功"
        assert result['request_id'] == "req-123"
        assert 'timestamp' in result

    def test_success_response_default(self):
        """测试成功响应默认值"""
        result = ResponseBuilder.success()

        assert result['success'] is True
        assert result['data'] is None
        assert result['message'] == "操作成功"
        assert result['request_id'] is None

    def test_error_response(self):
        """测试错误响应构建"""
        result = ResponseBuilder.error(
            message="参数错误",
            error_code=1001,
            data={"field": "name"},
            request_id="req-456"
        )

        assert result['success'] is False
        assert result['message'] == "参数错误"
        assert result['error_code'] == 1001
        assert result['data'] == {"field": "name"}
        assert result['request_id'] == "req-456"

    def test_paginated_response(self):
        """测试分页响应构建"""
        data = [{"id": 1}, {"id": 2}]
        result = ResponseBuilder.paginated(
            data=data,
            page=1,
            page_size=20,
            total=100,
            message="查询成功",
            request_id="req-789"
        )

        assert result['success'] is True
        assert result['data'] == data
        assert result['message'] == "查询成功"
        assert result['request_id'] == "req-789"
        assert 'pagination' in result

        pagination = result['pagination']
        assert pagination['page'] == 1
        assert pagination['page_size'] == 20
        assert pagination['total'] == 100
        assert pagination['total_pages'] == 5
        assert pagination['has_next'] is True
        assert pagination['has_prev'] is False

    def test_paginated_response_edge_cases(self):
        """测试分页响应边界情况"""
        # 空数据
        result = ResponseBuilder.paginated(data=[], page=1, page_size=20, total=0)
        assert result['pagination']['total_pages'] == 0
        assert result['pagination']['has_next'] is False
        assert result['pagination']['has_prev'] is False

        # page_size为0的情况
        result = ResponseBuilder.paginated(data=[], page=1, page_size=0, total=10)
        assert result['pagination']['total_pages'] == 0

    def test_list_response(self):
        """测试列表响应构建"""
        items = [{"id": 1}, {"id": 2}, {"id": 3}]
        result = ResponseBuilder.list_response(
            items=items,
            message="获取列表成功",
            total=10,
            request_id="req-list"
        )

        assert result['success'] is True
        assert result['data']['items'] == items
        assert result['data']['count'] == 3
        assert result['data']['total'] == 10
        assert result['message'] == "获取列表成功"
        assert result['request_id'] == "req-list"

    def test_create_response(self):
        """测试创建响应构建"""
        data = {"id": 123, "name": "test"}
        result = ResponseBuilder.create_response(data, message="创建成功", request_id="req-create")

        assert result['success'] is True
        assert result['data'] == data
        assert result['message'] == "创建成功"
        assert result['request_id'] == "req-create"

    def test_update_response(self):
        """测试更新响应构建"""
        result = ResponseBuilder.update_response(message="更新成功", request_id="req-update")

        assert result['success'] is True
        assert result['data'] is None
        assert result['message'] == "更新成功"
        assert result['request_id'] == "req-update"

    def test_delete_response(self):
        """测试删除响应构建"""
        result = ResponseBuilder.delete_response(message="删除成功", request_id="req-delete")

        assert result['success'] is True
        assert result['data'] is None
        assert result['message'] == "删除成功"
        assert result['request_id'] == "req-delete"

    def test_validation_error(self):
        """测试验证错误响应构建"""
        result = ResponseBuilder.validation_error(
            field="email",
            message="邮箱格式不正确",
            request_id="req-validation"
        )

        assert result['success'] is False
        assert result['message'] == "参数验证失败: 邮箱格式不正确"
        assert result['error_code'] == 2000
        assert result['data']['field'] == "email"
        assert result['data']['validation_message'] == "邮箱格式不正确"
        assert result['request_id'] == "req-validation"

    def test_not_found_error(self):
        """测试资源未找到错误响应构建"""
        result = ResponseBuilder.not_found_error(resource="用户", request_id="req-not-found")

        assert result['success'] is False
        assert result['message'] == "用户未找到"
        assert result['error_code'] == 2003
        assert result['request_id'] == "req-not-found"

    def test_permission_error(self):
        """测试权限错误响应构建"""
        result = ResponseBuilder.permission_error(message="需要管理员权限", request_id="req-permission")

        assert result['success'] is False
        assert result['message'] == "需要管理员权限"
        assert result['error_code'] == 2002
        assert result['request_id'] == "req-permission"

    def test_server_error(self):
        """测试服务器错误响应构建"""
        result = ResponseBuilder.server_error(message="数据库连接失败", request_id="req-server")

        assert result['success'] is False
        assert result['message'] == "数据库连接失败"
        assert result['error_code'] == 1000
        assert result['request_id'] == "req-server"


class TestFlaskResponseHelper:
    """测试Flask响应助手"""

    @patch('woniunote.common.unified_response.jsonify')
    def test_json_response(self, mock_jsonify):
        """测试JSON响应创建"""
        mock_response = MagicMock()
        mock_jsonify.return_value = mock_response

        data = {"test": "data"}
        result = FlaskResponseHelper.json_response(data, 201)

        mock_jsonify.assert_called_once_with(data)
        assert mock_response.status_code == 201
        assert result == mock_response

    @patch('woniunote.common.unified_response.FlaskResponseHelper.json_response')
    def test_success_json(self, mock_json_response):
        """测试成功JSON响应创建"""
        mock_response = MagicMock()
        mock_json_response.return_value = mock_response

        result = FlaskResponseHelper.success_json(
            data={"id": 1},
            message="创建成功",
            request_id="req-success",
            status_code=201
        )

        mock_json_response.assert_called_once()
        assert result == mock_response

    @patch('woniunote.common.unified_response.FlaskResponseHelper.json_response')
    def test_error_json(self, mock_json_response):
        """测试错误JSON响应创建"""
        mock_response = MagicMock()
        mock_json_response.return_value = mock_response

        result = FlaskResponseHelper.error_json(
            message="参数错误",
            error_code=1001,
            status_code=400
        )

        mock_json_response.assert_called_once()
        assert result == mock_response

    @patch('woniunote.common.unified_response.FlaskResponseHelper.json_response')
    def test_paginated_json(self, mock_json_response):
        """测试分页JSON响应创建"""
        mock_response = MagicMock()
        mock_json_response.return_value = mock_response

        data = [{"id": 1}, {"id": 2}]
        result = FlaskResponseHelper.paginated_json(
            data=data,
            page=1,
            page_size=20,
            total=100,
            message="查询成功"
        )

        mock_json_response.assert_called_once()
        assert result == mock_response

    @patch('woniunote.common.unified_response.FlaskResponseHelper.json_response')
    def test_created_json(self, mock_json_response):
        """测试创建JSON响应创建"""
        mock_response = MagicMock()
        mock_json_response.return_value = mock_response

        result = FlaskResponseHelper.created_json(
            data={"id": 123},
            message="创建成功"
        )

        mock_json_response.assert_called_once()
        assert result == mock_response

    @patch('woniunote.common.unified_response.jsonify')
    def test_no_content(self, mock_jsonify):
        """测试无内容响应创建"""
        mock_response = MagicMock()
        mock_jsonify.return_value = mock_response

        result = FlaskResponseHelper.no_content()

        mock_jsonify.assert_called_once_with({})
        assert mock_response.status_code == 204
        assert result == mock_response


class TestUtilityFunctions:
    """测试工具函数"""

    def test_success_response_function(self):
        """测试success_response便捷函数"""
        result = success_response(data={"id": 1}, message="操作成功")

        assert result['success'] is True
        assert result['data'] == {"id": 1}
        assert result['message'] == "操作成功"

    def test_error_response_function(self):
        """测试error_response便捷函数"""
        result = error_response(message="参数错误", error_code=1001)

        assert result['success'] is False
        assert result['message'] == "参数错误"
        assert result['error_code'] == 1001

    def test_paginated_response_function(self):
        """测试paginated_response便捷函数"""
        data = [{"id": 1}, {"id": 2}]
        result = paginated_response(data=data, page=1, page_size=20, total=100)

        assert result['success'] is True
        assert result['data'] == data
        assert 'pagination' in result

    def test_paginate_query_result(self):
        """测试查询结果分页处理"""
        query_result = list(range(1, 101))  # 1-100的列表

        result = paginate_query_result(query_result, page=1, page_size=20)
        assert result['success'] is True
        assert len(result['data']) == 20
        assert result['data'] == list(range(1, 21))

        pagination = result['pagination']
        assert pagination['page'] == 1
        assert pagination['page_size'] == 20
        assert pagination['total'] == 100
        assert pagination['total_pages'] == 5
        assert pagination['has_next'] is True
        assert pagination['has_prev'] is False

        # 测试第2页
        result = paginate_query_result(query_result, page=2, page_size=20)
        assert len(result['data']) == 20
        assert result['data'] == list(range(21, 41))

        pagination = result['pagination']
        assert pagination['page'] == 2
        assert pagination['has_next'] is True
        assert pagination['has_prev'] is True

        # 测试最后一页
        result = paginate_query_result(query_result, page=5, page_size=20)
        assert len(result['data']) == 20
        assert result['data'] == list(range(81, 101))

        pagination = result['pagination']
        assert pagination['page'] == 5
        assert pagination['has_next'] is False
        assert pagination['has_prev'] is True

    def test_format_article_response(self):
        """测试文章响应格式化"""
        # 创建模拟文章对象
        class MockArticle:
            def __init__(self):
                self.articleid = 123
                self.userid = 456
                self.headline = "测试文章"
                self.type = 1
                self.thumbnail = "/images/test.jpg"
                self.credit = 10
                self.readcount = 100
                self.replycount = 5
                self.recommended = 1
                self.hidden = 0
                self.drafted = 0
                self.checked = 1
                self.createtime = MagicMock()
                self.updatetime = MagicMock()
                self.content = "文章内容"

        article = MockArticle()
        result = format_article_response(article, include_content=True)

        assert result['articleid'] == 123
        assert result['userid'] == 456
        assert result['headline'] == "测试文章"
        assert result['content'] == "文章内容"

        # 测试不包含内容
        result_no_content = format_article_response(article, include_content=False)
        assert 'content' not in result_no_content

        # 测试None输入
        assert format_article_response(None) is None

    def test_format_user_response(self):
        """测试用户响应格式化"""
        # 创建模拟用户对象
        class MockUser:
            def __init__(self):
                self.userid = 789
                self.username = "testuser"
                self.nickname = "测试用户"
                self.avatar = "/avatars/test.jpg"
                self.role = "admin"
                self.credit = 500
                self.createtime = MagicMock()
                self.updatetime = MagicMock()
                self.qq = "123456789"

        user = MockUser()
        result = format_user_response(user, include_sensitive=True)

        assert result['userid'] == 789
        assert result['username'] == "testuser"
        assert result['nickname'] == "测试用户"
        assert result['qq'] == "123456789"

        # 测试不包含敏感信息
        result_no_sensitive = format_user_response(user, include_sensitive=False)
        assert 'qq' not in result_no_sensitive

        # 测试None输入
        assert format_user_response(None) is None

    def test_standardize_response_decorator_success(self):
        """测试标准化响应装饰器 - 成功情况"""
        @standardize_response
        def test_function():
            return {"result": "success"}

        result = test_function()

        assert result['success'] is True
        assert result['data'] == {"result": "success"}

    def test_standardize_response_decorator_none_result(self):
        """测试标准化响应装饰器 - None结果"""
        @standardize_response
        def test_function():
            return None

        result = test_function()

        assert result['success'] is True
        assert result['data'] is None
        assert result['message'] == "操作成功"

    @patch('woniunote.common.unified_response.logger')
    def test_standardize_response_decorator_exception(self, mock_logger):
        """测试标准化响应装饰器 - 异常情况"""
        @standardize_response
        def test_function():
            raise ValueError("测试异常")

        result = test_function()

        assert result['success'] is False
        assert "测试异常" in result['message']
        mock_logger.error.assert_called_once()

    def test_standardize_response_decorator_existing_response(self):
        """测试标准化响应装饰器 - 已有标准响应"""
        @standardize_response
        def test_function():
            return {"success": True, "data": "test", "message": "自定义消息"}

        result = test_function()

        # 应该直接返回，不会被重新包装
        assert result == {"success": True, "data": "test", "message": "自定义消息"}
