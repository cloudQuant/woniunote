#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
直接使用SQLAlchemy API创建数据库表，避免循环导入问题
"""
import sys
import os
import datetime
from sqlalchemy import create_engine, Table, Column, Integer, String, Text, DateTime, ForeignKey, MetaData
from sqlalchemy.ext.declarative import declarative_base

# 直接指定数据库连接字符串
# 请根据实际情况修改
DB_USER = 'root'
DB_PASSWORD = 'root'
DB_HOST = 'localhost'
DB_PORT = '3306'
DB_NAME = 'woniunote'

# 创建数据库连接字符串
DB_URI = f"mysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# 创建引擎
engine = create_engine(DB_URI)
metadata = MetaData()
Base = declarative_base(metadata=metadata)

# 定义模型
class Card(Base):
    __tablename__ = "card"
    id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    type = Column(Integer, default=1)
    headline = Column(Text, nullable=False)
    content = Column(Text, default="")
    createtime = Column(DateTime)
    updatetime = Column(DateTime)
    donetime = Column(DateTime)
    usedtime = Column(Integer, default=0)
    begintime = Column(DateTime)
    endtime = Column(DateTime)
    cardcategory_id = Column(Integer, ForeignKey("cardcategory.id"), default=1)

class CardCategory(Base):
    __tablename__ = "cardcategory"
    id = Column(Integer, primary_key=True)
    name = Column(String(64))

class TodoItem(Base):
    __tablename__ = "todo_item"
    id = Column(Integer, primary_key=True, autoincrement=True)
    body = Column(Text, nullable=False)
    category_id = Column(Integer, ForeignKey("todo_category.id"), default=1)

class TodoCategory(Base):
    __tablename__ = "todo_category"
    id = Column(Integer, primary_key=True)
    name = Column(String(64))

def init_tables():
    """初始化数据库表"""
    try:
        # 连接数据库
        conn = engine.connect()
        
        # 删除已存在的表（如果存在）
        metadata.drop_all(engine)
        print("已删除旧表")
        
        # 创建表
        metadata.create_all(engine)
        print("成功创建新表")
        
        # 添加默认分类
        conn.execute(CardCategory.__table__.insert(), [
            {"id": 1, "name": "待办卡片"},
            {"id": 2, "name": "已完成"}
        ])
        
        conn.execute(TodoCategory.__table__.insert(), [
            {"id": 1, "name": "待办事项"},
            {"id": 2, "name": "已完成"}
        ])
        
        # 添加示例数据
        now = datetime.datetime.now()
        conn.execute(Card.__table__.insert(), [
            {"headline": "这是一个示例卡片", "type": 1, "createtime": now, "updatetime": now, "cardcategory_id": 1}
        ])
        
        conn.execute(TodoItem.__table__.insert(), [
            {"body": "这是一个示例待办事项", "category_id": 1}
        ])
        
        conn.close()
        print("数据库初始化完成")
        return True
    except Exception as e:
        print(f"初始化数据库失败: {str(e)}")
        return False

if __name__ == "__main__":
    print("开始初始化数据库...")
    init_tables()
