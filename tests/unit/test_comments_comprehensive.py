#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comments模块综合测试 - 100%覆盖率 (Pytest版本)
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

class TestCommentsComprehensive:
    """Comments模块100%覆盖率综合测试 (Pytest版本)"""
    
    @patch('woniunote.module.comments.dbconnect')
    def test_comments_init(self, mock_dbconnect):
        """测试Comments类初始化"""
        mock_session = Mock()
        mock_metadata = Mock()
        mock_base = Mock()
        mock_dbconnect.return_value = (mock_session, mock_metadata, mock_base)
        
        from woniunote.module.comments import Comments
        
        comments = Comments()
        assert comments is not None
        # 验证Comments类有预期的属性
        assert hasattr(comments, 'user')
        assert hasattr(comments, 'article')
    
    @patch('woniunote.module.comments.dbsession')
    def test_find_by_article_success(self, mock_dbsession):
        """测试按文章ID查找评论 - 成功路径"""
        # Mock查询结果
        mock_result = [Mock(), Mock()]
        mock_dbsession.query.return_value.filter_by.return_value.all.return_value = mock_result
        
        from woniunote.module.comments import Comments
        
        result = Comments.find_by_articleid(1)
        assert result == mock_result
    
    @patch('woniunote.module.comments.dbsession')
    def test_find_by_article_exception(self, mock_dbsession):
        """测试按文章ID查找评论 - 异常处理"""
        # Mock异常
        mock_dbsession.query.side_effect = Exception("Database error")
        
        from woniunote.module.comments import Comments
        
        result = Comments.find_by_articleid(1)
        assert result == []
    
    @patch('woniunote.module.comments.dbsession')
    @patch('woniunote.module.comments.session')
    def test_insert_comment_success(self, mock_session, mock_dbsession):
        """测试插入评论 - 成功路径"""
        # Mock session
        mock_session.get.return_value = 1
        
        # Mock数据库操作
        mock_comment = Mock()
        mock_comment.commentid = 123
        mock_dbsession.add.return_value = None
        mock_dbsession.commit.return_value = None
        
        from woniunote.module.comments import Comments
        
        result = Comments.insert_comment(1, "Test comment", "127.0.0.1")
        assert result is not None
    
    @patch('woniunote.module.comments.dbsession')
    @patch('woniunote.module.comments.session')
    def test_insert_comment_exception(self, mock_session, mock_dbsession):
        """测试插入评论 - 异常处理"""
        # Mock session with proper structure
        mock_session.get.side_effect = lambda key: None if key == 'main_userid' else None
        
        from woniunote.module.comments import Comments
        
        result = Comments.insert_comment(1, "Test comment", "127.0.0.1")
        assert result is None
    
    @patch('woniunote.module.comments.dbsession')
    def test_find_by_id(self, mock_dbsession):
        """测试按ID查找评论"""
        # Mock查询结果
        mock_result = Mock()
        mock_dbsession.query.return_value.filter_by.return_value.first.return_value = mock_result
        
        from woniunote.module.comments import Comments
        
        result = Comments.find_by_id(1)
        assert result == mock_result
    
    @patch('woniunote.module.comments.dbsession')
    def test_last_reply(self, mock_dbsession):
        """测试获取最后回复"""
        # Mock查询结果
        mock_result = Mock()
        mock_dbsession.query.return_value.filter_by.return_value.order_by.return_value.first.return_value = mock_result
        
        from woniunote.module.comments import Comments
        
        result = Comments.last_reply(1)
        assert result == mock_result
    
    @patch('woniunote.module.comments.dbsession')
    def test_edge_cases(self, mock_dbsession):
        """测试边界条件"""
        # Mock空结果
        mock_dbsession.query.return_value.filter_by.return_value.all.return_value = []
        
        from woniunote.module.comments import Comments
        
        result = Comments.find_by_articleid(999)
        assert result == []


if __name__ == '__main__':
    pytest.main([__file__, "-v"])