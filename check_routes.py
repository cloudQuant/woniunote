#!/usr/bin/env python3
"""检查WoniuNote的路由映射"""

import sys
import os

# 确保项目根目录在Python路径中
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from woniunote.app import create_app

def check_routes():
    """检查路由映射"""
    app = create_app()

    print("=== WoniuNote 路由映射 ===")
    print()

    # 按规则分组显示路由
    routes_by_blueprint = {}

    for rule in app.url_map.iter_rules():
        if rule.endpoint != 'static':
            blueprint = rule.endpoint.split('.')[0] if '.' in rule.endpoint else 'app'
            if blueprint not in routes_by_blueprint:
                routes_by_blueprint[blueprint] = []
            routes_by_blueprint[blueprint].append((rule.rule, rule.methods, rule.endpoint))

    for blueprint, routes in routes_by_blueprint.items():
        print(f"🔹 {blueprint.upper()} 蓝图路由:")
        for rule, methods, endpoint in sorted(routes):
            print(f"  {rule} -> {endpoint} [{', '.join(methods)}]")
        print()

if __name__ == '__main__':
    check_routes()
