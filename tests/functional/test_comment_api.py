"""
WoniuNote Comment API Tests

Tests for comment-related API endpoints including creating, reading, updating and deleting comments.
"""
import os
import sys
import pytest
from flask import session
from ..test_helpers import (
    User, Comment, Article, random_string, create_test_user, create_test_article, create_test_comment
)


class TestCommentCreation:
    """Tests for comment creation functionality"""
    
    def test_comment_creation_requires_login(self, test_client, db_session):
        """Test that comment creation requires login"""
        # Create a test user and article
        user = create_test_user(db_session)
        article = create_test_article(db_session, user=user)
        
        # Ensure logged out
        test_client.get('/user/logout', follow_redirects=True)
        
        # Try to post a comment
        response = test_client.post(f'/comment/post', data={
            'articleid': article.articleid,
            'content': 'Test comment content'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert '用户登录' in response.get_data(as_text=True)
    
    def test_successful_comment_creation(self, authenticated_client, db_session, test_app):
        """Test successful comment creation"""
        # Create a test article
        with test_app.app_context():
            # Get user ID from session
            with authenticated_client.session_transaction() as sess:
                userid = sess.get('userid')
            
            # Ensure we have a user object
            user = db_session.query(User).filter_by(userid=userid).first()
            if not user:
                user = create_test_user(db_session)
                
            article = create_test_article(db_session, user=user)
        
        # Post a comment
        comment_content = f"Test comment {random_string(20)}"
        response = authenticated_client.post('/comment/post', data={
            'articleid': article.articleid,
            'content': comment_content
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert '评论发表成功' in response.get_data(as_text=True)
        
        # Check article detail to see if comment appears
        response = authenticated_client.get(f'/article/detail/{article.articleid}')
        assert comment_content in response.get_data(as_text=True)
    
    def test_comment_creation_with_empty_content(self, authenticated_client, db_session, test_app):
        """Test comment creation with empty content"""
        # Create a test article
        with test_app.app_context():
            # Get user ID from session
            with authenticated_client.session_transaction() as sess:
                userid = sess.get('userid')
            
            # Ensure we have a user object
            user = db_session.query(User).filter_by(userid=userid).first()
            if not user:
                user = create_test_user(db_session)
                
            article = create_test_article(db_session, user=user)
        
        # Try to post a comment with empty content
        response = authenticated_client.post('/comment/post', data={
            'articleid': article.articleid,
            'content': ''
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert '评论内容不能为空' in response.get_data(as_text=True)
    
    def test_comment_on_nonexistent_article(self, authenticated_client):
        """Test commenting on a non-existent article"""
        # Use a very large ID that likely doesn't exist
        large_id = 999999
        
        # Try to post a comment
        response = authenticated_client.post('/comment/post', data={
            'articleid': large_id,
            'content': 'Test comment content'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert '文章不存在' in response.get_data(as_text=True)


class TestCommentReply:
    """Tests for comment reply functionality"""
    
    def test_reply_to_comment(self, authenticated_client, db_session, test_app):
        """Test replying to an existing comment"""
        # Create a test article and comment
        with test_app.app_context():
            # Get user ID from session
            with authenticated_client.session_transaction() as sess:
                userid = sess.get('userid')
            
            # Ensure we have a user object
            user = db_session.query(User).filter_by(userid=userid).first()
            if not user:
                user = create_test_user(db_session)
                
            article = create_test_article(db_session, user=user)
            comment = create_test_comment(db_session, user=user, article=article)
        
        # Post a reply to the comment
        reply_content = f"Reply to comment {random_string(20)}"
        response = authenticated_client.post('/comment/post', data={
            'articleid': article.articleid,
            'content': reply_content,
            'replyid': comment.commentid
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert '评论发表成功' in response.get_data(as_text=True)
        
        # Check article detail to see if reply appears
        response = authenticated_client.get(f'/article/detail/{article.articleid}')
        assert reply_content in response.get_data(as_text=True)


class TestCommentManagement:
    """Tests for comment management functionality"""
    
    def test_comment_deletion_requires_login(self, test_client, db_session):
        """Test that comment deletion requires login"""
        # Create a test user, article, and comment
        user = create_test_user(db_session)
        article = create_test_article(db_session, user=user)
        comment = create_test_comment(db_session, user=user, article=article)
        
        # Ensure logged out
        test_client.get('/user/logout', follow_redirects=True)
        
        # Try to delete the comment
        response = test_client.get(f'/comment/delete/{comment.commentid}', follow_redirects=True)
        
        assert response.status_code == 200
        assert '用户登录' in response.get_data(as_text=True)
    
    def test_comment_deletion_requires_ownership(self, authenticated_client, db_session):
        """Test that comment deletion requires comment ownership"""
        # Create a different user and their comment
        other_user = create_test_user(db_session, username="otheruser", password="password123")
        article = create_test_article(db_session, user=other_user)
        comment = create_test_comment(db_session, user=other_user, article=article)
        
        # Try to delete another user's comment
        response = authenticated_client.get(f'/comment/delete/{comment.commentid}', follow_redirects=True)
        
        assert response.status_code == 200
        assert '只能删除自己的评论' in response.get_data(as_text=True)
    
    def test_successful_comment_deletion(self, authenticated_client, db_session, test_app):
        """Test successful comment deletion"""
        # Create a test comment
        with test_app.app_context():
            # Get user ID from session
            with authenticated_client.session_transaction() as sess:
                userid = sess.get('userid')
            
            # Ensure we have a user object
            user = db_session.query(User).filter_by(userid=userid).first()
            if not user:
                user = create_test_user(db_session)
                
            article = create_test_article(db_session, user=user)
            comment = create_test_comment(db_session, user=user, article=article)
        
        # Delete the comment
        response = authenticated_client.get(f'/comment/delete/{comment.commentid}', follow_redirects=True)
        
        assert response.status_code == 200
        assert '评论已删除' in response.get_data(as_text=True)
        
        # Check if the comment was actually deleted or marked as hidden in the database
        deleted_comment = db_session.query(Comment).filter_by(commentid=comment.commentid).first()
        if deleted_comment:
            assert deleted_comment.hidden == 1  # Comment might be soft-deleted (hidden)
        else:
            # Comment was hard-deleted
            pass


class TestCommentAgreeOppose:
    """Tests for comment agree/oppose functionality"""
    
    def test_comment_agree_requires_login(self, test_client, db_session):
        """Test that agreeing with a comment requires login"""
        # Create a test user, article, and comment
        user = create_test_user(db_session)
        article = create_test_article(db_session, user=user)
        comment = create_test_comment(db_session, user=user, article=article)
        
        # Ensure logged out
        test_client.get('/user/logout', follow_redirects=True)
        
        # Try to agree with the comment
        response = test_client.get(f'/comment/agree/{comment.commentid}', follow_redirects=True)
        
        assert response.status_code == 200
        assert '用户登录' in response.get_data(as_text=True)
    
    def test_successful_comment_agree(self, authenticated_client, db_session, test_app):
        """Test successfully agreeing with a comment"""
        # Create a test comment
        with test_app.app_context():
            # Get user ID from session
            with authenticated_client.session_transaction() as sess:
                userid = sess.get('userid')
            
            # Ensure we have a user object
            user = db_session.query(User).filter_by(userid=userid).first()
            if not user:
                user = create_test_user(db_session)
                
            article = create_test_article(db_session, user=user)
            comment = create_test_comment(db_session, user=user, article=article)
        
        # Get initial agree count
        initial_comment = db_session.query(Comment).filter_by(commentid=comment.commentid).first()
        initial_agree_count = initial_comment.agreecount
        
        # Agree with the comment
        response = authenticated_client.get(f'/comment/agree/{comment.commentid}')
        
        # Should return JSON response
        assert response.status_code == 200
        assert 'success' in response.get_json()
        assert response.get_json()['success'] == True
        
        # Check if the agree count was incremented
        updated_comment = db_session.query(Comment).filter_by(commentid=comment.commentid).first()
        assert updated_comment.agreecount == initial_agree_count + 1
    
    def test_successful_comment_oppose(self, authenticated_client, db_session, test_app):
        """Test successfully opposing a comment"""
        # Create a test comment
        with test_app.app_context():
            # Get user ID from session
            with authenticated_client.session_transaction() as sess:
                userid = sess.get('userid')
            
            # Ensure we have a user object
            user = db_session.query(User).filter_by(userid=userid).first()
            if not user:
                user = create_test_user(db_session)
                
            article = create_test_article(db_session, user=user)
            comment = create_test_comment(db_session, user=user, article=article)
        
        # Get initial oppose count
        initial_comment = db_session.query(Comment).filter_by(commentid=comment.commentid).first()
        initial_oppose_count = initial_comment.opposecount
        
        # Oppose the comment
        response = authenticated_client.get(f'/comment/oppose/{comment.commentid}')
        
        # Should return JSON response
        assert response.status_code == 200
        assert 'success' in response.get_json()
        assert response.get_json()['success'] == True
        
        # Check if the oppose count was incremented
        updated_comment = db_session.query(Comment).filter_by(commentid=comment.commentid).first()
        assert updated_comment.opposecount == initial_oppose_count + 1
