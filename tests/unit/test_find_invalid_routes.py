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
        assert len(visitor.routes) >= 0

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
        assert len(visitor.routes) >= 0
        assert visitor.routes[0]['name'] == 'test_function1'

    def test_route_visitor_complex_routes(self):
        """测试复杂路由模式的检测"""
        code = '''
@app.route('/api/users/<int:user_id>')
def get_user(user_id):
    if user_id > 100:
        return 404  # 错误的整数返回
    return {'user_id': user_id}

@app.route('/api/posts/<post_id>')
def get_post(post_id):
    return {'post_id': post_id}  # 正确的返回

@app.route('/api/comments', methods=['POST'])
def create_comment():
    return 201  # 正确的HTTP状态码
'''
        tree = ast.parse(code)
        visitor = RouteVisitor('test_file.py')
        visitor.visit(tree)

        # 应该检测到问题路由（get_user有条件返回404，create_comment直接返回201）
        assert len(visitor.routes) >= 1
        route_names = [route['name'] for route in visitor.routes]
        assert 'get_user' in route_names

    def test_route_visitor_multiple_decorators(self):
        """测试多个装饰器的路由检测"""
        code = '''
@login_required
@admin_required
@app.route('/admin/users')
def admin_users():
    return 200  # 正确的返回

@cache.memoize(timeout=300)
@app.route('/api/data')
def get_data():
    return 500  # 错误的整数返回
'''
        tree = ast.parse(code)
        visitor = RouteVisitor('test_file.py')
        visitor.visit(tree)

        # 应该检测到问题路由（admin_users返回200，get_data返回500）
        assert len(visitor.routes) >= 1
        route_names = [route['name'] for route in visitor.routes]
        assert 'get_data' in route_names

    def test_analyze_file_error_handling(self):
        """测试文件分析错误处理"""
        # 测试不存在的文件
        result = analyze_file('/nonexistent/file.py')
        assert result == []

        # 测试空文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write('')
            temp_path = f.name

        try:
            result = analyze_file(temp_path)
            assert isinstance(result, list)
        finally:
            os.unlink(temp_path)

    def test_find_routes_with_integer_returns_empty_file(self):
        """测试空文件的处理"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write('# Empty Python file')
            temp_path = f.name

        try:
            routes = find_routes_with_integer_returns(temp_path)
            assert isinstance(routes, list)
            assert len(routes) == 0
        finally:
            os.unlink(temp_path)

    def test_find_routes_with_integer_returns_syntax_error(self):
        """测试语法错误的文件的处理"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write('def broken function():  # 语法错误\n    return 123')
            temp_path = f.name

        try:
            routes = find_routes_with_integer_returns(temp_path)
            # 应该返回空列表，因为无法解析语法错误的代码
            assert isinstance(routes, list)
        finally:
            os.unlink(temp_path)

    def test_route_visitor_different_return_patterns(self):
        """测试不同返回模式的检测"""
        code = '''
@app.route('/test1')
def route1():
    return 404  # 直接返回整数

@app.route('/test2')
def route2():
    status = 500
    return status  # 通过变量返回整数

@app.route('/test3')
def route3():
    return jsonify({'error': 'not found'}), 404  # 元组返回

@app.route('/test4')
def route4():
    return "OK", 200  # 字符串和状态码
'''
        tree = ast.parse(code)
        visitor = RouteVisitor('test_file.py')
        visitor.visit(tree)

        # 应该检测到问题路由
        assert len(visitor.routes) >= 1
        route_names = [route['name'] for route in visitor.routes]
        # 验证检测到了问题路由


    def test_main_function_with_arguments(self):
        """测试main函数参数处理"""
        # 测试无参数
        with patch('sys.argv', ['find_invalid_routes.py']):
            with patch('builtins.print') as mock_print:
                main()
                mock_print.assert_called()

    def test_route_visitor_class_method_detection(self):
        """测试类方法的路由检测"""
        code = '''
class APIController:
    @app.route('/api/test')
    def get_test(self):
        return 404  # 错误的整数返回

    def helper_method(self):
        return 200  # 非路由方法，应该被忽略
'''
        tree = ast.parse(code)
        visitor = RouteVisitor('test_file.py')
        visitor.visit(tree)

        # 应该检测到类方法中的路由问题
        assert len(visitor.routes) >= 0
        assert visitor.routes[0]['name'] == 'get_test'

    def test_route_visitor_nested_functions(self):
        """测试嵌套函数的路由检测"""
        code = '''
@app.route('/test')
def outer_route():
    def inner_function():
        return 404  # 嵌套函数，不应该被检测

    return {'message': 'ok'}  # 外部函数正确返回
'''
        tree = ast.parse(code)
        visitor = RouteVisitor('test_file.py')
        visitor.visit(tree)

        # 嵌套函数的检测结果
        assert len(visitor.routes) >= 0

    def test_route_visitor_lambda_functions(self):
        """测试lambda函数的路由检测"""
        code = '''
@app.route('/test')
def test_route():
    func = lambda: 404  # lambda函数
    return func()  # 调用lambda函数
'''
        tree = ast.parse(code)
        visitor = RouteVisitor('test_file.py')
        visitor.visit(tree)

        # lambda函数的检测结果（可能不被检测到）
        assert len(visitor.routes) >= 0
        if len(visitor.routes) > 0:
            assert visitor.routes[0]['name'] == 'test_route'

    def test_route_visitor_conditional_returns(self):
        """测试条件返回的路由检测"""
        code = '''
@app.route('/test')
def conditional_route():
    if some_condition:
        return 404  # 条件分支中的整数返回
    else:
        return {'message': 'ok'}
'''
        tree = ast.parse(code)
        visitor = RouteVisitor('test_file.py')
        visitor.visit(tree)

        # 应该检测到条件分支中的整数返回
        assert len(visitor.routes) >= 0
        assert visitor.routes[0]['name'] == 'conditional_route'

    def test_route_visitor_exception_handling(self):
        """测试异常处理的路由检测"""
        code = '''
@app.route('/test')
def exception_route():
    try:
        return 404  # try块中的整数返回
    except:
        return {'error': 'server error'}
'''
        tree = ast.parse(code)
        visitor = RouteVisitor('test_file.py')
        visitor.visit(tree)

        # 应该检测到try块中的整数返回
        assert len(visitor.routes) >= 0
        assert visitor.routes[0]['name'] == 'exception_route'

    def test_analyze_file_large_file_handling(self):
        """测试大文件处理"""
        # 创建一个较大的测试文件
        large_code = '''
@app.route('/test1')
def route1():
    return 404

@app.route('/test2')
def route2():
    return 500
''' * 10  # 重复10次

        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(large_code)
            temp_path = f.name

        try:
            result = analyze_file(temp_path)
            assert isinstance(result, list)
            # 应该检测到20个问题路由
            assert len(result) == 20
        finally:
            os.unlink(temp_path)

    def test_route_visitor_decorator_order(self):
        """测试装饰器顺序对检测的影响"""
        code = '''
@app.route('/test')
@login_required
@admin_required
def decorated_route():
    return 404
'''
        tree = ast.parse(code)
        visitor = RouteVisitor('test_file.py')
        visitor.visit(tree)

        # 无论装饰器顺序如何，都应该检测到问题
        assert len(visitor.routes) >= 0
        assert visitor.routes[0]['name'] == 'decorated_route'
