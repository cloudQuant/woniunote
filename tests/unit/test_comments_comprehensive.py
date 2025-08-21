#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comments模块综合测试 - 100%覆盖率
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

class TestCommentsComprehensive(unittest.TestCase):
    """Comments模块100%覆盖率综合测试"""
    
    @patch('woniunote.module.comments.dbconnect')
    @patch('woniunote.module.comments.get_simple_logger')
    def test_comments_init(self, mock_logger, mock_dbconnect):
        """测试Comments类初始化"""
        mock_logger.return_value = Mock()
        mock_session = Mock()
        mock_metadata = Mock()
        mock_base = Mock()
        mock_dbconnect.return_value = (mock_session, mock_metadata, mock_base)
        
        from woniunote.module.comments import Comments
        
        comments = Comments()
        self.assertIsNotNone(comments)
        mock_logger.assert_called_once_with('comments')
    
    @patch('woniunote.module.comments.dbconnect')
    @patch('woniunote.module.comments.get_simple_logger')
    def test_find_by_article_success(self, mock_logger, mock_dbconnect):
        """测试按文章ID查找评论 - 成功路径"""
        mock_logger.return_value = Mock()
        mock_session = Mock()
        mock_metadata = Mock()
        mock_base = Mock()
        mock_dbconnect.return_value = (mock_session, mock_metadata, mock_base)
        
        from woniunote.module.comments import Comments
        
        comments = Comments()
        
        # Mock数据
        mock_comment = Mock()
        mock_comment.articleid = 1
        mock_comment.content = 'Test comment'
        
        mock_query = Mock()
        mock_query.filter_by.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.all.return_value = [mock_comment]
        mock_query.count.return_value = 1
        
        mock_session.query.return_value = mock_query
        
        # 执行测试
        result = comments.find_by_article(1, 1, 10)
        
        # 验证结果
        self.assertIsNotNone(result)
        self.assertEqual(len(result[0]), 1)
        self.assertEqual(result[1], 1)
        self.assertEqual(result[2], 1)
    
    @patch('woniunote.module.comments.dbconnect')
    @patch('woniunote.module.comments.get_simple_logger')
    def test_find_by_article_exception(self, mock_logger, mock_dbconnect):
        """测试按文章ID查找评论 - 异常处理"""
        mock_logger_instance = Mock()
        mock_logger.return_value = mock_logger_instance
        mock_session = Mock()
        mock_metadata = Mock()
        mock_base = Mock()
        mock_dbconnect.return_value = (mock_session, mock_metadata, mock_base)
        
        from woniunote.module.comments import Comments
        
        comments = Comments()
        
        # 模拟数据库异常
        mock_session.query.side_effect = Exception("Database error")
        
        # 执行测试
        result = comments.find_by_article(1, 1, 10)
        
        # 验证结果
        self.assertEqual(result, ([], 0, 0))
        mock_logger_instance.error.assert_called()
    
    @patch('woniunote.module.comments.dbconnect')
    @patch('woniunote.module.comments.get_simple_logger')
    def test_insert_comment_success(self, mock_logger, mock_dbconnect):
        """测试插入评论 - 成功路径"""
        mock_logger.return_value = Mock()
        mock_session = Mock()
        mock_metadata = Mock()
        mock_base = Mock()
        mock_dbconnect.return_value = (mock_session, mock_metadata, mock_base)
        
        from woniunote.module.comments import Comments
        
        comments = Comments()
        
        # Mock execute
        mock_session.execute.return_value = Mock()
        mock_session.commit.return_value = None
        
        # 执行测试
        comments.insert_comment(1, 1, 'Test comment', '2024-01-01', 0)
        
        # 验证调用
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()
    
    @patch('woniunote.module.comments.dbconnect')
    @patch('woniunote.module.comments.get_simple_logger')
    def test_insert_comment_exception(self, mock_logger, mock_dbconnect):
        """测试插入评论 - 异常处理"""
        mock_logger_instance = Mock()
        mock_logger.return_value = mock_logger_instance
        mock_session = Mock()
        mock_metadata = Mock()
        mock_base = Mock()
        mock_dbconnect.return_value = (mock_session, mock_metadata, mock_base)
        
        from woniunote.module.comments import Comments
        
        comments = Comments()
        
        # 模拟数据库异常
        mock_session.execute.side_effect = Exception("Insert error")
        
        # 执行测试
        comments.insert_comment(1, 1, 'Test comment', '2024-01-01', 0)
        
        # 验证错误处理
        mock_session.rollback.assert_called_once()
        mock_logger_instance.error.assert_called()
    
    @patch('woniunote.module.comments.dbconnect')
    @patch('woniunote.module.comments.get_simple_logger')
    def test_find_by_id(self, mock_logger, mock_dbconnect):
        """测试按ID查找评论"""
        mock_logger.return_value = Mock()
        mock_session = Mock()
        mock_metadata = Mock()
        mock_base = Mock()
        mock_dbconnect.return_value = (mock_session, mock_metadata, mock_base)
        
        from woniunote.module.comments import Comments
        
        comments = Comments()
        
        # Mock数据
        mock_comment = Mock()
        mock_comment.id = 1
        mock_comment.username = 'testuser'
        
        mock_query = Mock()
        mock_query.filter_by.return_value = mock_query
        mock_query.first.return_value = mock_comment
        
        mock_session.query.return_value = mock_query
        
        # 执行测试
        result = comments.find_by_id(1)
        
        # 验证结果
        self.assertEqual(result, mock_comment)
        self.assertEqual(result.username, 'testuser')
    
    @patch('woniunote.module.comments.dbconnect')
    @patch('woniunote.module.comments.get_simple_logger')
    def test_last_reply(self, mock_logger, mock_dbconnect):
        """测试获取最后回复"""
        mock_logger.return_value = Mock()
        mock_session = Mock()
        mock_metadata = Mock()
        mock_base = Mock()
        mock_dbconnect.return_value = (mock_session, mock_metadata, mock_base)
        
        from woniunote.module.comments import Comments
        
        comments = Comments()
        
        # Mock数据
        mock_comment = Mock()
        mock_comment.replyid = 1
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [mock_comment]
        
        mock_session.query.return_value = mock_query
        
        # 执行测试
        result = comments.last_reply(1)
        
        # 验证结果
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 1)
    
    @patch('woniunote.module.comments.dbconnect')
    @patch('woniunote.module.comments.get_simple_logger')
    def test_edge_cases(self, mock_logger, mock_dbconnect):
        """测试边界条件"""
        mock_logger.return_value = Mock()
        mock_session = Mock()
        mock_metadata = Mock()
        mock_base = Mock()
        mock_dbconnect.return_value = (mock_session, mock_metadata, mock_base)
        
        from woniunote.module.comments import Comments
        
        comments = Comments()
        
        # 测试空结果
        mock_query = Mock()
        mock_query.filter_by.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.all.return_value = []
        mock_query.count.return_value = 0
        mock_query.first.return_value = None
        
        mock_session.query.return_value = mock_query
        
        # 测试空文章评论
        result = comments.find_by_article(999, 1, 10)
        self.assertEqual(result[0], [])
        self.assertEqual(result[1], 0)
        
        # 测试不存在的评论ID
        result = comments.find_by_id(999)
        self.assertIsNone(result)
        
        # 测试没有回复的评论
        mock_query.all.return_value = []
        result = comments.last_reply(999)
        self.assertEqual(result, [])


if __name__ == '__main__':
    unittest.main()