#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
直接使用SQL语句重置Card和Todo模块的数据库表，避开循环导入和模型重复定义问题
"""
import os
import sys
import datetime
import pymysql
import yaml

# 直接读取配置文件，避免导入应用模块
def direct_read_config():
    """直接从配置文件读取数据库信息，避免导入应用模块"""
    config_path = os.path.join('woniunote', 'configs', 'config.py')
    try:
        # 读取Python配置文件内容
        config_content = {}
        with open(config_path, 'r', encoding='utf-8') as f:
            # 提取数据库连接字符串
            for line in f:
                if 'SQLALCHEMY_DATABASE_URI' in line:
                    # 提取引号内的内容
                    import re
                    match = re.search(r'["\'](.+?)["\']', line)
                    if match:
                        db_uri = match.group(1)
                        return {'database': {'SQLALCHEMY_DATABASE_URI': db_uri}}
        
        # 如果没有找到连接字符串，返回None
        print("在配置文件中未找到数据库连接字符串")
        return None
    except Exception as e:
        print(f"读取配置文件出错: {str(e)}")
        return None

# 解析数据库URI
def direct_parse_db_uri(uri):
    """解析数据库URI获取连接信息"""
    # mysql://username:password@host:port/database
    if not uri.startswith('mysql://'):
        raise ValueError("仅支持MySQL数据库")
    
    # 去除协议前缀
    uri = uri.replace('mysql://', '')
    
    # 提取用户名和密码
    auth, rest = uri.split('@', 1)
    user, password = auth.split(':', 1)
    
    # 提取主机、端口和数据库名
    host_port, database = rest.split('/', 1)
    
    if ':' in host_port:
        host, port = host_port.split(':', 1)
    else:
        host = host_port
        port = 3306  # 默认MySQL端口
    
    return {
        'host': host,
        'port': port,
        'user': user,
        'password': password,
        'database': database
    }

# 直接创建数据库连接
def get_connection():
    """直接创建数据库连接"""
    config = direct_read_config()
    if not config:
        print("无法读取配置")
        sys.exit(1)
    
    db_uri = config.get('database', {}).get('SQLALCHEMY_DATABASE_URI')
    if not db_uri:
        print("无法找到数据库URI")
        sys.exit(1)
    
    db_info = direct_parse_db_uri(db_uri)
    print(f"数据库连接信息: {db_info}")
    
    try:
        return pymysql.connect(
            host=db_info['host'],
            port=int(db_info['port']),
            user=db_info['user'],
            password=db_info['password'],
            database=db_info['database'],
            charset='utf8mb4'
        )
    except Exception as e:
        print(f"连接数据库失败: {str(e)}")
        sys.exit(1)

def reset_card_tables():
    """重置Card模块的数据库表"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # 删除表（如果存在）
        cursor.execute("DROP TABLE IF EXISTS card")
        cursor.execute("DROP TABLE IF EXISTS cardcategory")
        print("已删除Card相关表")
        
        # 创建cardcategory表
        cursor.execute("""
        CREATE TABLE cardcategory (
            id INT PRIMARY KEY,
            name VARCHAR(64) NOT NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)
        print("成功创建cardcategory表")
        
        # 创建card表
        cursor.execute("""
        CREATE TABLE card (
            id INT AUTO_INCREMENT PRIMARY KEY,
            type INT DEFAULT 1,
            headline TEXT NOT NULL,
            content TEXT,
            createtime DATETIME,
            updatetime DATETIME,
            donetime DATETIME,
            usedtime INT DEFAULT 0,
            begintime DATETIME,
            endtime DATETIME,
            cardcategory_id INT DEFAULT 1,
            FOREIGN KEY (cardcategory_id) REFERENCES cardcategory(id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)
        print("成功创建card表")
        
        # 添加默认分类
        cursor.execute("INSERT INTO cardcategory (id, name) VALUES (1, '待办卡片')")
        cursor.execute("INSERT INTO cardcategory (id, name) VALUES (2, '已完成')")
        conn.commit()
        print("成功添加默认分类")
        
        # 添加示例卡片
        now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute(f"""
        INSERT INTO card (headline, type, createtime, cardcategory_id) 
        VALUES ('这是一个示例卡片', 1, '{now}', 1)
        """)
        conn.commit()
        print("成功添加示例卡片")
    except Exception as e:
        print(f"重置Card表出错: {str(e)}")
        conn.rollback()
    
    cursor.close()
    conn.close()

def reset_todo_tables():
    """重置Todo模块的数据库表"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # 删除表（如果存在）
        cursor.execute("DROP TABLE IF EXISTS todo_item")
        cursor.execute("DROP TABLE IF EXISTS todo_category")
        print("已删除Todo相关表")
        
        # 创建todo_category表
        cursor.execute("""
        CREATE TABLE todo_category (
            id INT PRIMARY KEY,
            name VARCHAR(64) NOT NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)
        print("成功创建todo_category表")
        
        # 创建todo_item表
        cursor.execute("""
        CREATE TABLE todo_item (
            id INT AUTO_INCREMENT PRIMARY KEY,
            body TEXT NOT NULL,
            category_id INT DEFAULT 1,
            FOREIGN KEY (category_id) REFERENCES todo_category(id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)
        print("成功创建todo_item表")
        
        # 添加默认分类
        cursor.execute("INSERT INTO todo_category (id, name) VALUES (1, '待办事项')")
        cursor.execute("INSERT INTO todo_category (id, name) VALUES (2, '已完成')")
        conn.commit()
        print("成功添加默认分类")
        
        # 添加示例待办事项
        cursor.execute("""
        INSERT INTO todo_item (body, category_id) 
        VALUES ('这是一个示例待办事项', 1)
        """)
        conn.commit()
        print("成功添加示例待办事项")
    except Exception as e:
        print(f"重置Todo表出错: {str(e)}")
        conn.rollback()
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    # 询问用户要重置哪些表
    print("请选择要重置的表：")
    print("1. 重置Card相关表")
    print("2. 重置Todo相关表")
    print("3. 重置所有表")
    
    choice = input("请输入选项(1/2/3): ")
    
    if choice == '1':
        reset_card_tables()
        print("Card表重置完成")
    elif choice == '2':
        reset_todo_tables()
        print("Todo表重置完成")
    elif choice == '3':
        reset_card_tables()
        reset_todo_tables()
        print("所有表重置完成")
    else:
        print("无效选项")
