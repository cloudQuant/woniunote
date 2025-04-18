#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WoniuNote 数据库信息显示工具

显示数据库中所有表的结构和内容概览
"""
import os
import sys
import yaml
import pymysql
from datetime import datetime
import io

# 获取项目根目录
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(project_root)

# 确保输出正确显示中文
sys.stdout.reconfigure(encoding='utf-8')

print("=" * 50)
print(f"WoniuNote数据库分析工具 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 50)

# 读取配置文件
config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'test_config.yaml')
with open(config_path, 'r', encoding='utf-8') as file:
    config = yaml.safe_load(file)

# 获取数据库连接URI
db_uri = config['database']['SQLALCHEMY_DATABASE_URI']
print(f"数据库连接URI: {db_uri}")

# 解析数据库连接字符串，提取主机、端口、用户名、密码和数据库名
def parse_db_uri(uri):
    """解析数据库连接URI，处理特殊格式和字符"""
    try:
        # 简化URI解析
        parts = uri.split('://', 1)[1]
        auth, rest = parts.split('@', 1) if '@' in parts else ('', parts)
        user, password = auth.split(':', 1) if ':' in auth else (auth, '')
        
        if '/' not in rest:
            host_port = rest
            db_name = ''
        else:
            host_port, db_name = rest.split('/', 1)
            if '?' in db_name:
                db_name = db_name.split('?', 1)[0]
            
        host, port = host_port.split(':', 1) if ':' in host_port else (host_port, '3306')
        port = int(port)
        
        return {
            'user': user,
            'password': password,
            'host': host,
            'port': port,
            'database': db_name
        }
    except Exception as e:
        print(f"解析URI时出错: {e}")
        return {
            'user': 'woniunote_user',
            'password': 'Woniunote_password1!',
            'host': '127.0.0.1',
            'port': 3306,
            'database': 'woniunote'
        }

# 解析数据库连接信息
db_info = parse_db_uri(db_uri)
print(f"数据库连接信息: 主机={db_info['host']}, 端口={db_info['port']}, 数据库名={db_info['database']}")

# 使用pymysql连接数据库
try:
    print("\n正在连接数据库...")
    connection = pymysql.connect(
        host=db_info['host'],
        user=db_info['user'],
        password=db_info['password'],
        database=db_info['database'],
        port=db_info['port'],
        charset='utf8mb4'
    )
    
    with connection.cursor() as cursor:
        # 获取所有表
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        
        print(f"\n数据库中共有 {len(tables)} 个表:")
        
        # 列出所有表名
        for i, table_info in enumerate(tables):
            print(f"{i+1}. {table_info[0]}")
        
        # 对每个表分析结构和内容
        for table_info in tables:
            table_name = table_info[0]
            
            # 显示表名
            print("\n" + "=" * 30)
            print(f"表名: {table_name}")
            print("=" * 30)
            
            # 获取表结构
            cursor.execute(f"DESCRIBE `{table_name}`")
            columns = cursor.fetchall()
            
            # 显示表结构概要
            print("\n表结构概要:")
            print("-" * 40)
            for col in columns:
                col_name = col[0]
                col_type = col[1]
                is_pk = "√" if col[3] == "PRI" else ""
                print(f"{col_name:<15} {col_type:<15} {is_pk}")
            
            # 获取记录数量
            cursor.execute(f"SELECT COUNT(*) FROM `{table_name}`")
            record_count = cursor.fetchone()[0]
            print(f"\n记录数量: {record_count}")
            
            # 根据记录数量决定显示方式
            if record_count > 0:
                print("\n数据预览:")
                print("-" * 40)
                
                # 获取记录
                display_count = record_count if record_count < 10 else 3
                cursor.execute(f"SELECT * FROM `{table_name}` LIMIT {display_count}")
                rows = cursor.fetchall()
                
                # 显示前几条记录
                for i, row in enumerate(rows):
                    print(f"记录 {i+1}:")
                    for j, col in enumerate(columns):
                        col_name = col[0]
                        value = row[j]
                        if value is None:
                            value = "NULL"
                        elif isinstance(value, str) and len(value) > 50:
                            value = value[:47] + "..."
                        print(f"  {col_name}: {value}")
                    print("-" * 20)
                
                # 如果只显示了部分记录，显示提示
                if record_count > 10:
                    print(f"...共{record_count}条记录，只显示前3条...")
    
    print("\n数据库分析完成!")
    
except Exception as e:
    print(f"分析数据库时出错: {str(e)}")
finally:
    if 'connection' in locals() and connection:
        connection.close()