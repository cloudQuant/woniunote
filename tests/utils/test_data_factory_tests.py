#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试数据工厂测试

测试 TestDataFactory 类的功能
"""

import pytest
import os
import sys
import logging
from sqlalchemy import text

# 添加项目根目录到Python路径
project_root = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
sys.path.insert(0, project_root)

# 添加测试目录到Python路径
test_root = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, test_root)

# 导入测试基础设施
from tests.utils.test_base import logger, flask_app
from tests.utils.test_data_factory import TestDataFactory
from woniunote.common.database import dbconnect

@pytest.fixture(scope="module")
def app_context():
    """创建应用上下文"""
    with flask_app.app_context():
        yield

@pytest.mark.unit
def test_create_article(app_context):
    """测试创建文章功能"""
    try:
        # 创建一篇测试文章
        article_id = TestDataFactory.create_article(
            user_id=1,
            article_type="2",  # 使用字符串类型
            headline="测试文章标题",
            content="这是测试文章的内容"
        )
        
        # 验证文章已创建
        assert article_id is not None and article_id > 0, "文章创建失败，未返回有效ID"
        
        # 验证数据库中确实有这篇文章
        session, _, _ = dbconnect()
        result = session.execute(
            text("SELECT * FROM article WHERE articleid = :id"),
            {"id": article_id}
        )
        article = result.fetchone()
        session.close()
        
        assert article is not None, f"未找到ID为{article_id}的文章"
        
        # 检查标题字段（可能是headline或title）
        if hasattr(article, 'headline'):
            assert article.headline == "测试文章标题", "文章标题不匹配"
        elif hasattr(article, 'title'):
            assert article.title == "测试文章标题", "文章标题不匹配"
        
        # 类型字段始终用字符串比较，因为数据库中type是varchar
        assert str(article.type) == "2", f"文章类型不匹配，期望'2'，实际是'{article.type}'"
        
        logger.info(f"✓ 成功创建并验证文章，ID: {article_id}")
        
    except Exception as e:
        logger.error(f"测试创建文章时出错: {e}")
        pytest.fail(f"测试失败: {e}")

@pytest.mark.unit
def test_create_comment(app_context):
    """测试创建评论功能"""
    try:
        # 先创建一篇文章
        article_id = TestDataFactory.create_article()
        assert article_id is not None, "创建测试文章失败"
        
        # 为该文章创建评论
        comment_id = TestDataFactory.create_comment(
            article_id=article_id,
            user_id=1,
            content="这是一条测试评论内容"
        )
        
        # 验证评论已创建
        assert comment_id is not None and comment_id > 0, "评论创建失败，未返回有效ID"
        
        # 验证数据库中确实有这条评论
        session, _, _ = dbconnect()
        result = session.execute(
            text("SELECT * FROM comment WHERE commentid = :id"),
            {"id": comment_id}
        )
        comment = result.fetchone()
        session.close()
        
        assert comment is not None, f"未找到ID为{comment_id}的评论"
        assert comment.content == "这是一条测试评论内容", "评论内容不匹配"
        assert comment.articleid == article_id, "评论关联的文章ID不匹配"
        
        logger.info(f"✓ 成功创建并验证评论，ID: {comment_id}，关联文章ID: {article_id}")
        
    except Exception as e:
        logger.error(f"测试创建评论时出错: {e}")
        pytest.fail(f"测试失败: {e}")

@pytest.mark.unit
def test_ensure_test_data_exists(app_context):
    """测试确保测试数据存在功能"""
    try:
        # 执行确保测试数据存在的方法
        TestDataFactory.ensure_test_data_exists()
        
        # 验证数据库中确实有足够的文章
        session, _, _ = dbconnect()
        result = session.execute(text("SELECT COUNT(*) FROM article"))
        count = result.scalar()
        session.close()
        
        # 验证至少有10篇文章
        assert count >= 10, f"确保测试数据后，文章数量不足10篇，实际为{count}篇"
        
        logger.info(f"✓ 成功确保测试数据存在，当前文章数量: {count}")
        
    except Exception as e:
        logger.error(f"测试确保测试数据存在功能时出错: {e}")
        pytest.fail(f"测试失败: {e}")
