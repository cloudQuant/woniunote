"""
WoniuNote Favorite API Tests

Tests for favorite-related API endpoints including adding, listing, and removing favorites.
"""
import os
import sys
import pytest
from flask import session
from ..test_helpers import (
    User, Article, Favorite, random_string, create_test_user, create_test_article, create_test_favorite
)

class TestFavoriteOperations:
    """Tests for favorite operations functionality"""
    
    def test_favorite_requires_login(self, test_client, db_session):
        """Test that favoriting an article requires login"""
        # Create a test user and article
        user = create_test_user(db_session)
        article = create_test_article(db_session, user=user)
        
        # Ensure logged out
        test_client.get('/user/logout', follow_redirects=True)
        
        # Try to favorite the article
        response = test_client.get(f'/favorite/add/{article.articleid}', follow_redirects=True)
        
        assert response.status_code == 200
        assert '用户登录' in response.get_data(as_text=True)
    
    def test_successful_favorite_add(self, authenticated_client, db_session, test_app):
        """Test successfully adding an article to favorites"""
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
        
        # Add article to favorites
        response = authenticated_client.get(f'/favorite/add/{article.articleid}', follow_redirects=True)
        
        assert response.status_code == 200
        assert '收藏成功' in response.get_data(as_text=True)
        
        # Check if the favorite entry was created in the database
        favorite = db_session.query(Favorite).filter_by(
            userid=userid, 
            articleid=article.articleid,
            canceled=0
        ).first()
        
        assert favorite is not None
    
    def test_favorite_nonexistent_article(self, authenticated_client):
        """Test favoriting a non-existent article"""
        # Use a very large ID that likely doesn't exist
        large_id = 999999
        
        # Try to favorite a non-existent article
        response = authenticated_client.get(f'/favorite/add/{large_id}', follow_redirects=True)
        
        assert response.status_code == 200
        assert '文章不存在' in response.get_data(as_text=True)
    
    def test_duplicate_favorite(self, authenticated_client, db_session, test_app):
        """Test favoriting an article that is already favorited"""
        # Create a test article and favorite it
        with test_app.app_context():
            # Get user ID from session
            with authenticated_client.session_transaction() as sess:
                userid = sess.get('userid')
            
            # Ensure we have a user object
            user = db_session.query(User).filter_by(userid=userid).first()
            if not user:
                user = create_test_user(db_session)
                
            article = create_test_article(db_session, user=user)
            
            # Create a favorite
            favorite = create_test_favorite(db_session, user=user, article=article)
        
        # Try to favorite the same article again
        response = authenticated_client.get(f'/favorite/add/{article.articleid}', follow_redirects=True)
        
        assert response.status_code == 200
        assert '已经收藏过了' in response.get_data(as_text=True)


class TestFavoriteList:
    """Tests for favorite listing functionality"""
    
    def test_favorite_list_requires_login(self, test_client):
        """Test that viewing favorites list requires login"""
        # Ensure logged out
        test_client.get('/user/logout', follow_redirects=True)
        
        # Try to access favorites list
        response = test_client.get('/favorite/list', follow_redirects=True)
        
        assert response.status_code == 200
        assert '用户登录' in response.get_data(as_text=True)
    
    def test_favorite_list_displays_correctly(self, authenticated_client, db_session, test_app):
        """Test that favorites list displays correctly"""
        # Create test articles and favorites
        with test_app.app_context():
            # Get user ID from session
            with authenticated_client.session_transaction() as sess:
                userid = sess.get('userid')
            
            # Ensure we have a user object
            user = db_session.query(User).filter_by(userid=userid).first()
            if not user:
                user = create_test_user(db_session)
            
            # Create unique articles and favorites
            for i in range(3):
                article = create_test_article(
                    db_session, 
                    user=user, 
                    headline=f"Favorite Test Article {i} {random_string(8)}"
                )
                create_test_favorite(db_session, user=user, article=article)
        
        # Access favorites list
        response = authenticated_client.get('/favorite/list')
        
        assert response.status_code == 200
        assert '我的收藏' in response.get_data(as_text=True)
        
        # Check if all favorite article headlines are displayed
        response_text = response.get_data(as_text=True)
        
        favorites = db_session.query(Favorite).filter_by(userid=userid, canceled=0).all()
        for favorite in favorites:
            article = db_session.query(Article).filter_by(articleid=favorite.articleid).first()
            if article and "Favorite Test Article" in article.headline:
                assert article.headline in response_text
    
    def test_empty_favorite_list(self, authenticated_client, db_session, test_app):
        """Test that empty favorites list displays correctly"""
        # First, make sure the user has no favorites or cancel all existing ones
        with test_app.app_context():
            # Get user ID from session
            with authenticated_client.session_transaction() as sess:
                userid = sess.get('userid')
            
            # Cancel all favorites for this user
            favorites = db_session.query(Favorite).filter_by(userid=userid, canceled=0).all()
            for favorite in favorites:
                favorite.canceled = 1
            db_session.commit()
        
        # Access favorites list
        response = authenticated_client.get('/favorite/list')
        
        assert response.status_code == 200
        assert '我的收藏' in response.get_data(as_text=True)
        assert '暂无收藏文章' in response.get_data(as_text=True)


class TestFavoriteCancel:
    """Tests for favorite cancellation functionality"""
    
    def test_favorite_cancel_requires_login(self, test_client, db_session):
        """Test that canceling a favorite requires login"""
        # Create a test user, article, and favorite
        user = create_test_user(db_session)
        article = create_test_article(db_session, user=user)
        favorite = create_test_favorite(db_session, user=user, article=article)
        
        # Ensure logged out
        test_client.get('/user/logout', follow_redirects=True)
        
        # Try to cancel the favorite
        response = test_client.get(f'/favorite/cancel/{favorite.favoriteid}', follow_redirects=True)
        
        assert response.status_code == 200
        assert '用户登录' in response.get_data(as_text=True)
    
    def test_successful_favorite_cancel(self, authenticated_client, db_session, test_app):
        """Test successfully canceling a favorite"""
        # Create a test favorite
        with test_app.app_context():
            # Get user ID from session
            with authenticated_client.session_transaction() as sess:
                userid = sess.get('userid')
            
            # Ensure we have a user object
            user = db_session.query(User).filter_by(userid=userid).first()
            if not user:
                user = create_test_user(db_session)
                
            article = create_test_article(db_session, user=user)
            favorite = create_test_favorite(db_session, user=user, article=article)
        
        # Cancel the favorite
        response = authenticated_client.get(f'/favorite/cancel/{favorite.favoriteid}', follow_redirects=True)
        
        assert response.status_code == 200
        assert '已取消收藏' in response.get_data(as_text=True)
        
        # Check if the favorite was actually canceled in the database
        canceled_favorite = db_session.query(Favorite).filter_by(favoriteid=favorite.favoriteid).first()
        assert canceled_favorite.canceled == 1
    
    def test_cancel_nonexistent_favorite(self, authenticated_client):
        """Test canceling a non-existent favorite"""
        # Use a very large ID that likely doesn't exist
        large_id = 999999
        
        # Try to cancel a non-existent favorite
        response = authenticated_client.get(f'/favorite/cancel/{large_id}', follow_redirects=True)
        
        assert response.status_code == 200
        assert '收藏不存在' in response.get_data(as_text=True)
    
    def test_cancel_another_users_favorite(self, authenticated_client, db_session):
        """Test canceling another user's favorite"""
        # Create another user with a favorite
        other_user = create_test_user(db_session, username="otherfavuser", password="password123")
        article = create_test_article(db_session, user=other_user)
        favorite = create_test_favorite(db_session, user=other_user, article=article)
        
        # Try to cancel another user's favorite
        response = authenticated_client.get(f'/favorite/cancel/{favorite.favoriteid}', follow_redirects=True)
        
        assert response.status_code == 200
        assert '只能取消自己的收藏' in response.get_data(as_text=True)
