#!/usr/bin/env python3
"""
数据库配置修复脚本
检查并修复数据库连接问题
"""

import os
import sys
import yaml
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def check_database_connection():
    """检查数据库连接"""
    try:
        from woniunote.common.database import get_connection
        
        print("正在测试数据库连接...")
        
        with get_connection() as conn:
            result = conn.execute("SELECT 1 as test").fetchone()
            if result and result[0] == 1:
                print("✅ 数据库连接成功!")
                return True
            else:
                print("❌ 数据库连接测试失败")
                return False
                
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        return False

def create_database_user():
    """创建数据库用户"""
    try:
        import pymysql
        
        print("正在尝试创建数据库用户...")
        
        # 使用root用户连接
        root_conn = pymysql.connect(
            host='localhost',
            user='root',
            password='123456',
            charset='utf8mb4'
        )
        
        cursor = root_conn.cursor()
        
        # 创建数据库
        cursor.execute("CREATE DATABASE IF NOT EXISTS woniunote CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        cursor.execute("CREATE DATABASE IF NOT EXISTS woniunote_dev CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        
        # 创建用户
        cursor.execute("CREATE USER IF NOT EXISTS 'woniunote_user'@'localhost' IDENTIFIED BY 'woniunote_pass'")
        
        # 授予权限
        cursor.execute("GRANT ALL PRIVILEGES ON woniunote.* TO 'woniunote_user'@'localhost'")
        cursor.execute("GRANT ALL PRIVILEGES ON woniunote_dev.* TO 'woniunote_user'@'localhost'")
        cursor.execute("FLUSH PRIVILEGES")
        
        cursor.close()
        root_conn.close()
        
        print("✅ 数据库用户创建成功!")
        return True
        
    except Exception as e:
        print(f"❌ 数据库用户创建失败: {e}")
        print("请手动执行以下SQL命令:")
        print("CREATE DATABASE IF NOT EXISTS woniunote CHARACTER SET utf8mb4;")
        print("CREATE DATABASE IF NOT EXISTS woniunote_dev CHARACTER SET utf8mb4;")
        print("CREATE USER IF NOT EXISTS 'woniunote_user'@'localhost' IDENTIFIED BY 'woniunote_pass';")
        print("GRANT ALL PRIVILEGES ON woniunote.* TO 'woniunote_user'@'localhost';")
        print("GRANT ALL PRIVILEGES ON woniunote_dev.* TO 'woniunote_user'@'localhost';")
        print("FLUSH PRIVILEGES;")
        return False

def create_config_file():
    """创建配置文件"""
    config_file = project_root / 'configs' / 'user_password_config.yaml'
    
    if config_file.exists():
        print("配置文件已存在")
        return True
    
    config_data = {
        'database': {
            'host': 'localhost',
            'port': 3306,
            'name': 'woniunote',
            'username': 'woniunote_user',
            'password': 'woniunote_pass'
        },
        'redis': {
            'host': 'localhost',
            'port': 6379,
            'db': 0,
            'password': None
        },
        'mail': {
            'smtp_server': 'smtp.163.com',
            'smtp_port': 587,
            'use_tls': True,
            'username': 'your_email@163.com',
            'password': 'your_email_password'
        },
        'security': {
            'secret_key': 'dev-secret-key-change-in-production'
        }
    }
    
    try:
        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True)
        
        # 设置文件权限
        os.chmod(config_file, 0o600)
        
        print(f"✅ 配置文件创建成功: {config_file}")
        return True
        
    except Exception as e:
        print(f"❌ 配置文件创建失败: {e}")
        return False

def main():
    """主函数"""
    print("=== WoniuNote 数据库配置修复工具 ===\n")
    
    # 1. 检查当前数据库连接
    if not check_database_connection():
        print("\n正在尝试修复数据库配置...")
        
        # 2. 创建数据库用户
        if create_database_user():
            # 3. 创建配置文件
            create_config_file()
            
            # 4. 再次测试连接
            print("\n重新测试数据库连接...")
            if check_database_connection():
                print("✅ 数据库配置修复成功!")
            else:
                print("❌ 数据库配置修复失败，请检查配置")
        else:
            print("❌ 无法自动修复，请手动配置数据库")
    else:
        print("数据库连接正常，无需修复")
    
    print("\n=== 修复完成 ===")

if __name__ == '__main__':
    main()