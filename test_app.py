#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试应用启动脚本
"""
import os
import sys

# 确保能找到 woniunote 包
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 在任何其他导入之前注册 pymysql
import pymysql
pymysql.install_as_MySQLdb()

# 导入应用
from woniunote import create_app

if __name__ == '__main__':
    # 使用开发模式配置启动应用
    app = create_app('development')
    
    # 打印配置信息以进行验证
    print(f"SECRET_KEY configured: {'SECRET_KEY' in app.config}")
    print(f"DATABASE_URI: {app.config.get('SQLALCHEMY_DATABASE_URI')}")
    
    # 启动开发服务器
    app.run(host='127.0.0.1', port=5000, debug=True)
