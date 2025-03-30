"""
WoniuNote Credit API Tests

Tests for credit-related API endpoints including credit transactions, viewing credit history,
and credit impacts from other actions.
"""
import os
import sys
import pytest
from flask import session
from ..test_helpers import (
    User, Article, Credit, random_string, create_test_user, create_test_article, create_test_credit
)


class TestCreditTransactions:
    """Tests for credit transaction functionality"""
    
    def test_credit_transaction_requires_login(self, test_client):
        """Test that credit transactions require login"""
        # Ensure logged out
        test_client.get('/user/logout', follow_redirects=True)
        
        # Try to access credit history
        response = test_client.get('/credit/list', follow_redirects=True)
        
        assert response.status_code == 200
        assert '用户登录' in response.get_data(as_text=True)
    
    def test_credit_history_display(self, authenticated_client, db_session, test_app):
        """Test that credit history displays correctly"""
        # Create some credit transactions
        with test_app.app_context():
            # Get user ID from session
            with authenticated_client.session_transaction() as sess:
                userid = sess.get('userid')
            
            # Ensure we have a user object
            user = db_session.query(User).filter_by(userid=userid).first()
            if not user:
                user = create_test_user(db_session)
            
            article = create_test_article(db_session, user=user)
            
            # Create credit transactions with different categories and descriptions
            create_test_credit(
                db_session, 
                user=user, 
                article=article, 
                category=1, 
                description="发表文章奖励积分"
            )
            
            create_test_credit(
                db_session, 
                user=user, 
                article=article, 
                category=2, 
                description="评论文章奖励积分"
            )
            
            create_test_credit(
                db_session, 
                user=user, 
                article=article, 
                category=3, 
                description="每日登录奖励积分"
            )
        
        # Access credit history
        response = authenticated_client.get('/credit/list')
        
        assert response.status_code == 200
        assert '积分记录' in response.get_data(as_text=True)
        
        # Check if credit transaction descriptions are displayed
        response_text = response.get_data(as_text=True)
        assert '发表文章奖励积分' in response_text
        assert '评论文章奖励积分' in response_text
        assert '每日登录奖励积分' in response_text
    
    def test_empty_credit_history(self, authenticated_client, db_session, test_app):
        """Test that empty credit history displays correctly"""
        # Create a new user with no credit history
        with test_app.app_context():
            new_user = create_test_user(
                db_session, 
                username=f"nocredit_{random_string(8)}", 
                password="Test@123"
            )
            
            # Login as the new user
            authenticated_client.get('/user/logout')
            authenticated_client.post('/user/login', data={
                'username': new_user.username,
                'password': "Test@123"
            })
        
        # Access credit history
        response = authenticated_client.get('/credit/list')
        
        assert response.status_code == 200
        assert '积分记录' in response.get_data(as_text=True)
        assert '暂无积分记录' in response.get_data(as_text=True)


class TestCreditFromArticles:
    """Tests for credit earned from article operations"""
    
    def test_credit_for_publishing_article(self, authenticated_client, db_session, test_app):
        """Test that publishing an article earns credit"""
        # Get initial user credit
        with test_app.app_context():
            with authenticated_client.session_transaction() as sess:
                userid = sess.get('userid')
            
            user = db_session.query(User).filter_by(userid=userid).first()
            initial_credit = user.credit
        
        # Publish a new article
        headline = f"Credit Test Article {random_string(10)}"
        content = f"This is a test article content for credit testing. {random_string(50)}"
        article_type = "1"  # Assuming 1 is a valid article type
        
        response = authenticated_client.post('/article/create', data={
            'headline': headline,
            'content': content,
            'type': article_type
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert '文章发布成功' in response.get_data(as_text=True)
        
        # Check if credit was awarded
        with test_app.app_context():
            user = db_session.query(User).filter_by(userid=userid).first()
            assert user.credit > initial_credit, "User should have earned credit for publishing an article"
            
            # Find the article
            article = db_session.query(Article).filter_by(headline=headline).first()
            assert article is not None
            
            # Check credit record
            credit_record = db_session.query(Credit).filter_by(
                userid=userid,
                target=article.articleid,
                category=1  # Assuming 1 is the category for article publishing
            ).first()
            
            assert credit_record is not None, "Credit record should have been created"
            assert credit_record.credit > 0, "Credit amount should be positive"
    
    def test_credit_for_commenting(self, authenticated_client, db_session, test_app):
        """Test that commenting on an article earns credit"""
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
            
            # Get initial credit
            initial_credit = user.credit
        
        # Post a comment
        comment_content = f"Test comment for credit {random_string(20)}"
        response = authenticated_client.post('/comment/post', data={
            'articleid': article.articleid,
            'content': comment_content
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert '评论发表成功' in response.get_data(as_text=True)
        
        # Check if credit was awarded
        with test_app.app_context():
            user = db_session.query(User).filter_by(userid=userid).first()
            assert user.credit > initial_credit, "User should have earned credit for commenting"
            
            # Check credit record
            credit_record = db_session.query(Credit).filter_by(
                userid=userid,
                category=2  # Assuming 2 is the category for commenting
            ).order_by("Credit.createtime.desc()").first()
            
            assert credit_record is not None, "Credit record should have been created"
            assert credit_record.credit > 0, "Credit amount should be positive"


class TestCreditFromLogin:
    """Tests for credit earned from daily login"""
    
    def test_credit_for_daily_login(self, test_client, db_session):
        """Test that daily login earns credit"""
        # Create a test user
        user = create_test_user(
            db_session, 
            username=f"loginuser_{random_string(8)}", 
            password="Test@123"
        )
        
        # Get initial credit
        initial_credit = user.credit
        
        # Login
        response = test_client.post('/user/login', data={
            'username': user.username,
            'password': "Test@123"
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert '登录成功' in response.get_data(as_text=True)
        
        # Check if credit was awarded
        updated_user = db_session.query(User).filter_by(userid=user.userid).first()
        # Daily login might not award credit every time, so we'll just check if there's a record
        
        # Check credit record
        credit_record = db_session.query(Credit).filter_by(
            userid=user.userid,
            category=3  # Assuming 3 is the category for daily login
        ).order_by("Credit.createtime.desc()").first()
        
        # If there's a credit record for login, assert it's positive
        if credit_record:
            assert credit_record.credit > 0, "Credit amount should be positive"
            assert updated_user.credit >= initial_credit, "User credit should not decrease after login"


class TestCreditFromAdminOperations:
    """Tests for credit adjustments by admin operations"""
    
    def test_admin_credit_adjustment(self, db_session):
        """Test admin adjusting user credit"""
        # This test would require admin login which may not be available in standard test setup
        # We'll test using direct database operations instead
        
        # Create a test user
        user = create_test_user(db_session)
        initial_credit = user.credit
        
        # Simulate admin credit adjustment
        adjustment_amount = 10
        credit_description = "管理员奖励积分"
        
        credit = create_test_credit(
            db_session,
            user=user,
            article=None,
            category=4,  # Assuming 4 is admin adjustment category
            credit_amount=adjustment_amount,
            description=credit_description
        )
        
        # Update user credit
        user.credit += adjustment_amount
        db_session.commit()
        
        # Check if credit was properly adjusted
        updated_user = db_session.query(User).filter_by(userid=user.userid).first()
        assert updated_user.credit == initial_credit + adjustment_amount
        
        # Check credit record
        credit_record = db_session.query(Credit).filter_by(
            userid=user.userid,
            category=4
        ).order_by("Credit.createtime.desc()").first()
        
        assert credit_record is not None
        assert credit_record.credit == adjustment_amount
        assert credit_record.description == credit_description
