#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
文章模型测试辅助工具

提供与数据库直接交互的函数，规避模型字段定义问题
"""

import logging
from sqlalchemy import text
from woniunote.common.database import dbconnect

# 配置日志
logger = logging.getLogger(__name__)

def get_db_session():
    """获取数据库会话"""
    dbsession, _, _ = dbconnect()
    return dbsession

def get_article_types():
    """直接从数据库获取所有文章类型"""
    try:
        session = get_db_session()
        result = session.execute(text("SELECT DISTINCT type FROM article"))
        types = [str(row[0]) for row in result.fetchall()]
        
        # 如果没有找到类型，返回默认类型
        if not types:
            types = ['1', '2', 'tech', 'share']
        
        return types
    except Exception as e:
        logger.error(f"获取文章类型时出错: {e}")
        return ['1', '2', 'tech', 'share']  # 返回默认值

def get_article_by_id(article_id):
    """使用原生SQL查询获取文章，避免模型映射问题"""
    try:
        session = get_db_session()
        result = session.execute(
            text("SELECT * FROM article WHERE articleid = :id"),
            {"id": article_id}
        )
        article = result.fetchone()
        return article
    except Exception as e:
        logger.error(f"通过ID获取文章时出错: {e}")
        return None
        
def get_articles_by_type(article_type, limit=10):
    """使用原生SQL查询按类型获取文章"""
    try:
        session = get_db_session()
        result = session.execute(
            text("SELECT * FROM article WHERE type = :type LIMIT :limit"),
            {"type": article_type, "limit": limit}
        )
        articles = result.fetchall()
        return articles
    except Exception as e:
        logger.error(f"按类型获取文章时出错: {e}")
        return []

def get_articles_by_headline(headline_keyword, limit=10):
    """使用原生SQL查询按标题关键词搜索文章"""
    try:
        session = get_db_session()
        result = session.execute(
            text("SELECT * FROM article WHERE headline LIKE :keyword LIMIT :limit"),
            {"keyword": f"%{headline_keyword}%", "limit": limit}
        )
        articles = result.fetchall()
        return articles
    except Exception as e:
        logger.error(f"按标题搜索文章时出错: {e}")
        return []
