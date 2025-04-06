"""
查找所有路由处理函数并检查其返回值类型
这个脚本会打印出所有可能直接返回整数的路由函数
"""

import os
import re
import ast
import sys

class RouteVisitor(ast.NodeVisitor):
    """遍历AST树查找路由函数并分析其返回值"""
    
    def __init__(self, filename):
        self.filename = filename
        self.routes = []
        self.current_function = None
        self.has_integer_return = False
        self.route_decorators = []
        
    def visit_FunctionDef(self, node):
        """访问函数定义节点"""
        old_function = self.current_function
        self.current_function = node.name
        self.has_integer_return = False
        
        # 检查函数上的装饰器，是否有路由装饰器
        is_route = False
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Call):
                if isinstance(decorator.func, ast.Attribute):
                    if decorator.func.attr == 'route':
                        is_route = True
                        if isinstance(decorator.func.value, ast.Name):
                            self.route_decorators.append(decorator.func.value.id)
        
        # 普通函数，递归检查其中的返回语句
        self.generic_visit(node)
        
        # 如果是路由函数并且有直接返回整数的情况，记录下来
        if is_route and self.has_integer_return:
            self.routes.append({
                'name': node.name,
                'line': node.lineno,
                'decorator': self.route_decorators[-1] if self.route_decorators else '?'
            })
        
        self.current_function = old_function
    
    def visit_Return(self, node):
        """访问返回语句节点"""
        if self.current_function:
            # 检查是否直接返回整数
            if isinstance(node.value, ast.Num) and isinstance(node.value.n, int):
                self.has_integer_return = True
            
            # 检查是否返回变量，且该变量可能是整数
            elif isinstance(node.value, ast.Name):
                # 简单地假设某些常见的变量名可能是整数
                if node.value.id in ['id', 'count', 'status', 'code', 'result']:
                    self.has_integer_return = True
        
        self.generic_visit(node)

def analyze_file(file_path):
    """分析单个文件中的路由函数"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            code = f.read()
        
        # 解析Python代码为AST
        tree = ast.parse(code)
        
        # 访问者模式分析AST
        visitor = RouteVisitor(os.path.basename(file_path))
        visitor.visit(tree)
        
        return visitor.routes
    except Exception as e:
        print(f"分析文件 {file_path} 时出错: {str(e)}")
        return []

def find_routes_with_integer_returns(directory):
    """查找所有控制器文件并分析其中的路由函数"""
    problematic_routes = []
    
    for root, _, files in os.walk(directory):
        for filename in files:
            if filename.endswith('.py'):
                file_path = os.path.join(root, filename)
                routes = analyze_file(file_path)
                for route in routes:
                    problematic_routes.append({
                        'file': file_path,
                        'function': route['name'],
                        'line': route['line'],
                        'decorator': route['decorator']
                    })
    
    return problematic_routes

def main():
    """主函数，分析项目中的所有控制器文件"""
    project_dir = os.path.dirname(os.path.abspath(__file__))
    controller_dir = os.path.join(project_dir, 'controller')
    
    # 如果controller目录不存在，使用整个项目目录
    if not os.path.exists(controller_dir):
        controller_dir = project_dir
    
    print(f"分析目录: {controller_dir}")
    problematic_routes = find_routes_with_integer_returns(controller_dir)
    
    if problematic_routes:
        print("\n发现以下可能直接返回整数的路由函数:")
        for route in problematic_routes:
            print(f"文件: {route['file']}")
            print(f"函数: {route['function']}")
            print(f"行号: {route['line']}")
            print(f"蓝图: {route['decorator']}")
            print("-" * 50)
        
        print(f"\n共发现 {len(problematic_routes)} 个可能有问题的路由函数")
        print("建议检查这些函数，确保它们返回的是有效的Flask响应对象而不是整数")
    else:
        print("\n未发现可能直接返回整数的路由函数")
        print("问题可能出在更复杂的返回逻辑中，建议使用debug_app.py进行调试")

if __name__ == "__main__":
    main()
