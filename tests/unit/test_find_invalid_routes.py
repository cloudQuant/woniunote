#!/usr/bin/env python3
"""
WoniuNote 无效路由查找工具测试
"""

import pytest
import tempfile
import os
import ast
from unittest.mock import patch, MagicMock
from woniunote.find_invalid_routes import RouteVisitor, analyze_file, find_routes_with_integer_returns, main


class TestFindInvalidRoutes:
    """测试无效路由查找工具"""

    def test_route_visitor_class_exists(self):
        """测试RouteVisitor类存在"""
        assert RouteVisitor is not None

    def test_analyze_file_function_exists(self):
        """测试analyze_file函数存在"""
        assert callable(analyze_file)

    def test_find_routes_with_integer_returns_exists(self):
        """测试find_routes_with_integer_returns函数存在"""
        assert callable(find_routes_with_integer_returns)

    def test_main_function_exists(self):
        """测试main函数存在"""
        assert callable(main)

    def test_route_visitor_initialization(self):
        """测试RouteVisitor初始化"""
        visitor = RouteVisitor("test.py")
        assert visitor.filename == "test.py"
        assert visitor.routes == []
        assert visitor.current_function is None
        assert visitor.has_integer_return is False
        assert visitor.route_decorators == []

    def test_route_visitor_visit_function_def_route(self):
        """测试RouteVisitor访问路由函数定义"""
        code = """
@app.route('/test')
def test_function():
    return 404
"""
        tree = ast.parse(code)
        visitor = RouteVisitor("test.py")

        # 手动设置装饰器信息来模拟路由函数
        visitor.route_decorators = ['app']

        # 访问函数定义
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                visitor.visit_FunctionDef(node)

        # 验证结果
        assert len(visitor.routes) > 0

    def test_route_visitor_visit_function_def_non_route(self):
        """测试RouteVisitor访问非路由函数定义"""
        code = """
def normal_function():
    return 404
"""
        tree = ast.parse(code)
        visitor = RouteVisitor("test.py")

        # 访问函数定义
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                visitor.visit_FunctionDef(node)

        # 验证结果 - 非路由函数不应该被记录
        assert len(visitor.routes) == 0

    def test_route_visitor_visit_return_integer(self):
        """测试RouteVisitor访问返回整数的语句"""
        code = """
@app.route('/test')
def test_function():
    return 404
"""
        tree = ast.parse(code)
        visitor = RouteVisitor("test.py")
        visitor.current_function = "test_function"
        visitor.route_decorators = ['app']

        # 访问返回语句
        for node in ast.walk(tree):
            if isinstance(node, ast.Return):
                visitor.visit_Return(node)

        # 验证检测到整数返回
        assert visitor.has_integer_return is True

    def test_route_visitor_visit_return_string(self):
        """测试RouteVisitor访问返回字符串的语句"""
        code = """
@app.route('/test')
def test_function():
    return "response"
"""
        tree = ast.parse(code)
        visitor = RouteVisitor("test.py")
        visitor.current_function = "test_function"
        visitor.route_decorators = ['app']

        # 访问返回语句
        for node in ast.walk(tree):
            if isinstance(node, ast.Return):
                visitor.visit_Return(node)

        # 验证没有检测到整数返回
        assert visitor.has_integer_return is False

    def test_analyze_file_basic(self):
        """测试analyze_file基本功能"""
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("""
@app.route('/test')
def test_function():
    return 404
""")
            temp_file = f.name

        try:
            # 分析文件
            routes = analyze_file(temp_file)

            # 验证结果
            assert isinstance(routes, list)
            assert len(routes) > 0
            assert 'name' in routes[0]
            assert 'line' in routes[0]

        finally:
            # 清理临时文件
            os.unlink(temp_file)

    def test_analyze_file_no_route(self):
        """测试analyze_file处理没有路由的文件"""
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("""
def normal_function():
    return 404
""")
            temp_file = f.name

        try:
            # 分析文件
            routes = analyze_file(temp_file)

            # 验证结果
            assert isinstance(routes, list)
            assert len(routes) == 0

        finally:
            # 清理临时文件
            os.unlink(temp_file)

    def test_analyze_file_invalid_syntax(self):
        """测试analyze_file处理语法错误的文件"""
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("""
def invalid_syntax(
    return 404
""")
            temp_file = f.name

        try:
            # 分析文件
            routes = analyze_file(temp_file)

            # 验证结果 - 应该返回空列表
            assert isinstance(routes, list)
            assert len(routes) == 0

        finally:
            # 清理临时文件
            os.unlink(temp_file)

    def test_find_routes_with_integer_returns_basic(self):
        """测试find_routes_with_integer_returns基本功能"""
        # 创建临时目录和文件
        with tempfile.TemporaryDirectory() as temp_dir:
            # 创建测试文件
            test_file = os.path.join(temp_dir, 'test_controller.py')
            with open(test_file, 'w') as f:
                f.write("""
@app.route('/test')
def test_function():
    return 404
""")

            # 查找路由
            routes = find_routes_with_integer_returns(temp_dir)

            # 验证结果
            assert isinstance(routes, list)
            assert len(routes) > 0
            assert 'file' in routes[0]
            assert 'function' in routes[0]
            assert 'line' in routes[0]

    @patch('builtins.print')
    def test_main_function_execution(self, mock_print):
        """测试main函数执行"""
        # 执行main函数
        main()

        # 验证输出
        mock_print.assert_called()

    def test_route_visitor_complex_case(self):
        """测试RouteVisitor处理复杂情况"""
        code = """
@app.route('/test1')
def test_function1():
    return 404

@app.route('/test2')
def test_function2():
    return "normal"

def normal_function():
    return 500
"""
        tree = ast.parse(code)
        visitor = RouteVisitor("test.py")

        # 访问所有节点
        visitor.visit(tree)

        # 验证只检测到路由函数中的整数返回
        assert len(visitor.routes) == 1
        assert visitor.routes[0]['name'] == 'test_function1'
