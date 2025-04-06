import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath('.'))

from flask import Flask
from woniunote.app import create_app
from woniunote.controller.todo_center import tcenter

def test_todo_routes():
    """测试todo相关的路由是否正确注册"""
    # 创建应用实例
    app = create_app()
    
    print("\n=== ToDo 路由测试 ===")
    # 检查蓝图是否正确注册
    if 'tcenter' in [bp.name for bp in app.blueprints.values()]:
        print("✓ tcenter 蓝图已正确注册")
    else:
        print("✗ tcenter 蓝图未正确注册")
    
    # 打印所有注册的路由
    print("\n所有注册的路由:")
    routes = []
    for rule in app.url_map.iter_rules():
        if 'todo' in rule.rule:
            routes.append((rule.rule, rule.endpoint))
    
    # 按路径排序并打印
    for route, endpoint in sorted(routes):
        print(f"  {route:30} -> {endpoint}")
    
    # 检查是否存在特定的todo路由
    key_routes = ['/todo', '/todo/', '/todo/category/<int:id>']
    for route in key_routes:
        found = False
        for rule in app.url_map.iter_rules():
            if rule.rule == route:
                found = True
                break
        print(f"{'✓' if found else '✗'} 路由 {route} {'已注册' if found else '未注册'}")
        
    print("\n建议解决方案:")
    print("1. 确保 flask.redirect() 使用的是正确的完整URL")
    print("2. 检查 todo_center.py 中的导入语句")
    print("3. 确保用户已登录时再访问todo功能")

if __name__ == "__main__":
    test_todo_routes()
