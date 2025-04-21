#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重置Card模块的数据库表，解决循环导入和模型重复定义问题
"""
import os
import sys
import datetime
import pymysql
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from woniunote.common.utils import read_config, parse_db_uri

# 读取数据库配置
config_result = read_config()
SQLALCHEMY_DATABASE_URI = config_result['database']["SQLALCHEMY_DATABASE_URI"]
DATABASE_INFO = parse_db_uri(SQLALCHEMY_DATABASE_URI)

# 创建数据库连接
def get_connection():
    return pymysql.connect(
        host=DATABASE_INFO['host'],
        port=int(DATABASE_INFO['port']),
        user=DATABASE_INFO['user'],
        password=DATABASE_INFO['password'],
        database=DATABASE_INFO['database'],
        charset='utf8mb4'
    )

def drop_and_create_tables():
    """删除并重新创建Card相关表"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # 删除表（如果存在）
    try:
        cursor.execute("DROP TABLE IF EXISTS card")
        cursor.execute("DROP TABLE IF EXISTS cardcategory")
        print("已删除旧表")
    except Exception as e:
        print(f"删除旧表出错: {str(e)}")
    
    # 创建cardcategory表
    try:
        cursor.execute("""
        CREATE TABLE cardcategory (
            id INT PRIMARY KEY,
            name VARCHAR(64) NOT NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)
        print("成功创建cardcategory表")
    except Exception as e:
        print(f"创建cardcategory表出错: {str(e)}")
    
    # 创建card表
    try:
        cursor.execute("""
        CREATE TABLE card (
            id INT AUTO_INCREMENT PRIMARY KEY,
            type INT DEFAULT 1,
            headline TEXT(200) NOT NULL,
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
    except Exception as e:
        print(f"创建card表出错: {str(e)}")
    
    # 添加默认分类
    try:
        cursor.execute("INSERT INTO cardcategory (id, name) VALUES (1, '待办卡片')")
        cursor.execute("INSERT INTO cardcategory (id, name) VALUES (2, '已完成')")
        conn.commit()
        print("成功添加默认分类")
    except Exception as e:
        print(f"添加默认分类出错: {str(e)}")
    
    # 添加示例卡片
    try:
        now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute(f"""
        INSERT INTO card (headline, type, createtime, cardcategory_id) 
        VALUES ('这是一个示例卡片', 1, '{now}', 1)
        """)
        conn.commit()
        print("成功添加示例卡片")
    except Exception as e:
        print(f"添加示例卡片出错: {str(e)}")
    
    cursor.close()
    conn.close()
    print("Card模块数据库表初始化完成")

if __name__ == "__main__":
    drop_and_create_tables()
