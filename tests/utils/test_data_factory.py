#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试数据工厂

提供创建测试数据的工具类，解决模型定义与数据库结构不匹配的问题
"""

import random
import time
import datetime
from sqlalchemy import text
from flask import current_app
from woniunote.common.database import dbconnect

class TestDataFactory:
    """测试数据工厂类，用于创建与数据库兼容的测试数据"""
    
    @staticmethod
    def create_article(user_id=1, article_type="1", headline="测试文章", content="这是一篇测试文章的内容"):
        """
        创建测试文章
        
        注意：
        - type 字段在数据库中是 varchar(10)，但在模型中定义为 Integer
        - 我们在这里确保它以字符串形式存入
        - 数据库可能使用 'title' 而不是 'headline'，这里根据实际情况调整
        """
        now = datetime.datetime.now()
        
        # 获取数据库会话
        session, _, _ = dbconnect()
        
        try:
            # 检查article表结构，确定是使用headline还是title
            field_check = text("SHOW COLUMNS FROM article LIKE 'headline'")
            has_headline = session.execute(field_check).fetchone() is not None
            
            title_field = "headline" if has_headline else "title"
            
            # 使用原始 SQL 插入，避免 SQLAlchemy 模型验证的问题
            sql = text(f"""
                INSERT INTO article 
                (userid, type, {title_field}, content, createtime, updatetime, readcount, replycount, credit, recommended, hidden, drafted, checked)
                VALUES
                (:userid, :type, :title_value, :content, :createtime, :updatetime, 0, 0, 0, 0, 0, 0, 1)
            """)
            
            params = {
                'userid': user_id,
                'type': article_type,  # 确保使用字符串类型
                'title_value': headline,  # 使用headline的值作为title或headline字段的值
                'content': content,
                'createtime': now,
                'updatetime': now
            }
            
            result = session.execute(sql, params)
            session.commit()
            
            # 获取最新插入的文章 ID
            get_id_sql = text("SELECT LAST_INSERT_ID()")
            article_id = session.execute(get_id_sql).scalar()
        except Exception as e:
            session.rollback()
            raise e
        
        return article_id
    
    @staticmethod
    def create_comment(article_id, user_id=1, content="这是一条测试评论"):
        """创建测试评论"""
        now = datetime.datetime.now()
        
        # 获取数据库会话
        session, _, _ = dbconnect()
        
        try:
            # 检查comment表结构，确定是否有ipaddress字段
            field_check = text("SHOW COLUMNS FROM comment LIKE 'ipaddress'")
            has_ipaddress = session.execute(field_check).fetchone() is not None
            
            if has_ipaddress:
                sql = text("""
                    INSERT INTO comment
                    (articleid, userid, content, ipaddress, createtime, hidden)
                    VALUES
                    (:articleid, :userid, :content, '127.0.0.1', :createtime, 0)
                """)
            else:
                # 如果没有ipaddress字段，则不包含该字段
                sql = text("""
                    INSERT INTO comment
                    (articleid, userid, content, createtime, hidden)
                    VALUES
                    (:articleid, :userid, :content, :createtime, 0)
                """)
            
            params = {
                'articleid': article_id,
                'userid': user_id,
                'content': content,
                'createtime': now
            }
            
            result = session.execute(sql, params)
            session.commit()
            
            # 获取最新插入的评论 ID
            get_id_sql = text("SELECT LAST_INSERT_ID()")
            comment_id = session.execute(get_id_sql).scalar()
        except Exception as e:
            session.rollback()
            raise e
        
        return comment_id
    
    @staticmethod
    def create_articles_batch(count=5, user_id=1):
        """批量创建测试文章"""
        article_ids = []
        
        for i in range(count):
            try:
                article_type = str(random.randint(1, 4))
                headline = f"测试文章 {int(time.time())}-{i}"
                content = f"这是第 {i+1} 篇测试文章的内容，创建于 {datetime.datetime.now()}"
                
                article_id = TestDataFactory.create_article(
                    user_id=user_id,
                    article_type=article_type,
                    headline=headline,
                    content=content
                )
                
                article_ids.append(article_id)
            except Exception as e:
                print(f"创建第 {i+1} 篇文章时出错: {e}")
        
        return article_ids
    
    @staticmethod
    def ensure_test_data_exists():
        """确保测试数据存在"""
        # 获取数据库会话
        session, _, _ = dbconnect()
        
        try:
            # 检查是否已有足够的文章
            sql = text("SELECT COUNT(*) FROM article")
            count = session.execute(sql).scalar()
            
            if count < 10:
                # 创建一些测试文章
                TestDataFactory.create_articles_batch(10)
                
                # 为第一篇文章添加一些评论
                first_article_sql = text("SELECT articleid FROM article ORDER BY articleid LIMIT 1")
                first_article_id = session.execute(first_article_sql).scalar()
                
                if first_article_id:
                    for i in range(3):
                        try:
                            TestDataFactory.create_comment(
                                article_id=first_article_id,
                                content=f"测试评论 {i+1} 于文章 {first_article_id}"
                            )
                        except Exception as e:
                            print(f"创建第 {i+1} 条评论时出错: {e}")
        except Exception as e:
            session.rollback()
            raise e
