#!/usr/bin/env python3
"""
MySQL测试数据库设置脚本
用于创建和初始化WoniuNote测试数据库
"""

import sys
import os
import yaml
import pymysql
from urllib.parse import urlparse
from sqlalchemy import create_engine, text

def load_test_config():
    """加载测试配置"""
    config_file = os.path.join(os.path.dirname(__file__), 'user_password_config.yaml')
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            return config
    except FileNotFoundError:
        print(f"❌ 配置文件不存在: {config_file}")
        return None
    except Exception as e:
        print(f"❌ 读取配置文件失败: {e}")
        return None

def parse_mysql_url(database_url):
    """解析MySQL连接URL"""
    try:
        # 替换mysql://为mysql+pymysql://以便sqlalchemy使用
        sqlalchemy_url = database_url.replace('mysql://', 'mysql+pymysql://')
        parsed = urlparse(sqlalchemy_url)
        
        return {
            'host': parsed.hostname or 'localhost',
            'port': parsed.port or 3306,
            'username': parsed.username,
            'password': parsed.password,
            'database': parsed.path[1:] if parsed.path else None,  # 移除开头的/
            'sqlalchemy_url': sqlalchemy_url,
            'admin_url': f"mysql+pymysql://{parsed.username}:{parsed.password}@{parsed.hostname}:{parsed.port}/"
        }
    except Exception as e:
        print(f"❌ 解析数据库URL失败: {e}")
        return None

def test_mysql_connection(db_info):
    """测试MySQL连接"""
    try:
        print(f"🔍 测试MySQL连接 {db_info['host']}:{db_info['port']}...")
        
        # 测试基础连接（不指定数据库）
        engine = create_engine(db_info['admin_url'])
        with engine.connect() as conn:
            result = conn.execute(text('SELECT VERSION()'))
            version = result.fetchone()[0]
            print(f"✅ MySQL连接成功 - 版本: {version}")
            return True
    except Exception as e:
        print(f"❌ MySQL连接失败: {e}")
        return False

def create_database(db_info):
    """创建测试数据库"""
    try:
        print(f"🏗️  创建数据库: {db_info['database']}")
        
        engine = create_engine(db_info['admin_url'])
        with engine.connect() as conn:
            # 检查数据库是否存在
            result = conn.execute(
                text('SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME = :db_name'),
                {'db_name': db_info['database']}
            )
            
            if result.fetchone():
                print(f"✅ 数据库 {db_info['database']} 已存在")
            else:
                # 创建数据库
                conn.execute(text(f"CREATE DATABASE `{db_info['database']}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
                conn.commit()
                print(f"✅ 数据库 {db_info['database']} 创建成功")
        
        return True
    except Exception as e:
        print(f"❌ 创建数据库失败: {e}")
        return False

def test_database_access(db_info):
    """测试数据库访问权限"""
    try:
        print(f"🔐 测试数据库访问权限...")
        
        engine = create_engine(db_info['sqlalchemy_url'])
        with engine.connect() as conn:
            # 测试基本操作
            conn.execute(text('SELECT 1'))
            print(f"✅ 数据库 {db_info['database']} 访问正常")
            return True
    except Exception as e:
        print(f"❌ 数据库访问测试失败: {e}")
        return False

def initialize_test_tables(db_info):
    """初始化测试表"""
    try:
        print("📋 初始化测试表...")
        
        # 设置环境变量让WoniuNote使用正确的数据库
        os.environ['DATABASE_URL'] = db_info['sqlalchemy_url'].replace('mysql+pymysql://', 'mysql://')
        os.environ['TESTING'] = 'True'
        os.environ['FLASK_ENV'] = 'testing'
        
        # 导入WoniuNote数据库模型
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
        
        from woniunote.common.database import db
        from woniunote.configs.config import config
        from flask import Flask
        
        # 创建Flask应用用于初始化数据库
        app = Flask(__name__)
        app.config.from_object(config['testing'])
        app.config['SQLALCHEMY_DATABASE_URI'] = db_info['sqlalchemy_url'].replace('mysql+pymysql://', 'mysql://')
        
        db.init_app(app)
        
        with app.app_context():
            # 创建所有表
            db.create_all()
            print("✅ 测试表创建成功")
            
            # 检查表是否创建成功
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            print(f"📊 创建的表: {', '.join(tables)}")
        
        return True
    except Exception as e:
        print(f"❌ 初始化测试表失败: {e}")
        print(f"详细错误: {str(e)}")
        return False

def main():
    """主函数"""
    print("🚀 MySQL测试数据库设置工具")
    print("=" * 50)
    
    # 加载配置
    config = load_test_config()
    if not config:
        return 1
    
    database_url = config.get('database', {}).get('SQLALCHEMY_DATABASE_URI')
    if not database_url or not database_url.startswith('mysql://'):
        print("❌ 配置文件中未找到MySQL配置")
        print("💡 请检查 tests/configs/user_password_config.yaml")
        return 1
    
    # 解析数据库配置
    db_info = parse_mysql_url(database_url)
    if not db_info:
        return 1
    
    print(f"📋 数据库配置:")
    print(f"   主机: {db_info['host']}:{db_info['port']}")
    print(f"   用户: {db_info['username']}")
    print(f"   数据库: {db_info['database']}")
    print()
    
    # 1. 测试MySQL连接
    if not test_mysql_connection(db_info):
        print("\n💡 解决建议:")
        print("   1. 启动MySQL服务: brew services start mysql")
        print("   2. 检查用户名密码是否正确")
        print("   3. 安装Python MySQL驱动: pip install pymysql mysqlclient")
        return 1
    
    # 2. 创建数据库
    if not create_database(db_info):
        print("\n💡 解决建议:")
        print(f"   1. 手动创建数据库: CREATE DATABASE {db_info['database']};")
        print(f"   2. 授予权限: GRANT ALL ON {db_info['database']}.* TO '{db_info['username']}'@'localhost';")
        return 1
    
    # 3. 测试数据库访问
    if not test_database_access(db_info):
        return 1
    
    # 4. 初始化测试表
    if not initialize_test_tables(db_info):
        print("\n💡 可以稍后通过运行测试来创建表")
    
    print("\n🎉 MySQL测试数据库设置完成！")
    print("\n🧪 现在可以运行测试:")
    print("   source tests/setup_test_env.sh")
    print("   python -m pytest tests/test_simple_working.py -v")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
