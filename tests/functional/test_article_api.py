"""
WoniuNote Article API Tests

Tests for article-related API endpoints including creating, reading, updating and deleting articles.
"""
import pytest
from ..test_helpers import (
    Article, random_string, ResponseParser, create_test_user, create_test_article
)


class TestArticleCreation:
    """Tests for article creation functionality"""
    
    def test_article_creation_requires_login(self, test_client):
        """Test that article creation requires login"""
        # Ensure logged out
        test_client.get('/user/logout', follow_redirects=True)
        
        # Try to access article creation page
        response = test_client.get('/article/create', follow_redirects=True)
        
        assert response.status_code == 200
        assert '用户登录' in response.get_data(as_text=True)
    
    def test_article_creation_page_loads(self, authenticated_client):
        """Test that article creation page loads correctly"""
        response = authenticated_client.get('/article/create')
        
        assert response.status_code == 200
        assert '发布文章' in response.get_data(as_text=True)
    
    def test_successful_article_creation(self, authenticated_client):
        """Test successful article creation"""
        headline = f"Test Article {random_string(10)}"
        content = f"This is a test article content. {random_string(50)}"
        article_type = "blog"
        
        response = authenticated_client.post('/article/create', data={
            'headline': headline,
            'content': content,
            'type': article_type
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert '文章发布成功' in response.get_data(as_text=True)
        assert headline in response.get_data(as_text=True)
    
    def test_article_creation_with_empty_fields(self, authenticated_client):
        """Test article creation with empty required fields"""
        # Empty headline
        response = authenticated_client.post('/article/create', data={
            'headline': '',
            'content': 'Some content',
            'type': 'blog'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert '标题不能为空' in response.get_data(as_text=True)
        
        # Empty content
        response = authenticated_client.post('/article/create', data={
            'headline': 'Test Headline',
            'content': '',
            'type': 'blog'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert '内容不能为空' in response.get_data(as_text=True)
    
    def test_saving_article_as_draft(self, authenticated_client):
        """Test saving article as draft"""
        headline = f"Draft Article {random_string(10)}"
        content = f"This is a draft article content. {random_string(50)}"
        article_type = "blog"
        
        response = authenticated_client.post('/article/create', data={
            'headline': headline,
            'content': content,
            'type': article_type,
            'drafted': '1'  # Save as draft
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert '草稿保存成功' in response.get_data(as_text=True)


class TestArticleReading:
    """Tests for article reading functionality"""
    
    def test_article_list_page(self, test_client, db_session):
        """Test article list page loads correctly"""
        response = test_client.get('/')
        
        assert response.status_code == 200
        assert '最新文章' in response.get_data(as_text=True)
    
    def test_article_detail_page(self, test_client, db_session):
        """Test article detail page loads correctly"""
        # Create a test user and article
        user = create_test_user(db_session)
        article = create_test_article(db_session, user=user)
        
        # Access article detail page
        response = test_client.get(f'/article/detail/{article.articleid}')
        
        assert response.status_code == 200
        assert article.headline in response.get_data(as_text=True)
        assert article.content in response.get_data(as_text=True)
    
    def test_article_by_type(self, test_client, db_session):
        """Test viewing articles by type"""
        # Create test articles with different types
        user = create_test_user(db_session)
        article_type = "blog"
        for i in range(3):
            create_test_article(db_session, user=user, type_id=article_type)
        
        # Access articles by type
        response = test_client.get(f'/article/type/{article_type}')
        
        assert response.status_code == 200
        response_text = response.get_data(as_text=True)
        
        # Check if we can find multiple article headlines in the response
        articles = db_session.query(Article).filter_by(type=article_type).all()
        for article in articles[:3]:  # Check first 3 articles
            assert article.headline in response_text
    
    def test_article_not_found(self, test_client):
        """Test accessing a non-existent article"""
        # Use a very large ID that likely doesn't exist
        large_id = 999999
        response = test_client.get(f'/article/detail/{large_id}', follow_redirects=True)
        
        assert response.status_code == 200
        assert '文章不存在' in response.get_data(as_text=True)


class TestArticleUpdate:
    """Tests for article update functionality"""
    
    def test_article_update_requires_login(self, test_client, db_session):
        """Test that article update requires login"""
        # Create a test user and article
        user = create_test_user(db_session)
        article = create_test_article(db_session, user=user)
        
        # Ensure logged out
        test_client.get('/user/logout', follow_redirects=True)
        
        # Try to access article update page
        response = test_client.get(f'/article/edit/{article.articleid}', follow_redirects=True)
        
        assert response.status_code == 200
        assert '用户登录' in response.get_data(as_text=True)
    
    def test_article_update_requires_ownership(self, authenticated_client, db_session):
        """Test that article update requires article ownership"""
        # Create a different user and their article
        other_user = create_test_user(db_session, username="otheruser", password="password123")
        article = create_test_article(db_session, user=other_user)
        
        # Try to edit another user's article
        response = authenticated_client.get(f'/article/edit/{article.articleid}', follow_redirects=True)
        
        assert response.status_code == 200
        assert '只能编辑自己的文章' in response.get_data(as_text=True)
    
    def test_article_update_page_loads(self, authenticated_client, db_session, test_app):
        """Test that article update page loads correctly"""
        # Get current user ID
        with authenticated_client.session_transaction() as sess:
            userid = sess.get('userid')
        
        # Create an article for the authenticated user
        with test_app.app_context():
            article = create_test_article(db_session, user_id=userid)
        
        # Access article update page
        response = authenticated_client.get(f'/article/edit/{article.articleid}')
        
        assert response.status_code == 200
        assert '编辑文章' in response.get_data(as_text=True)
        assert article.headline in response.get_data(as_text=True)
    
    def test_successful_article_update(self, authenticated_client, db_session, test_app):
        """Test successful article update"""
        # Get current user ID
        with authenticated_client.session_transaction() as sess:
            userid = sess.get('userid')
        
        # Create an article for the authenticated user
        with test_app.app_context():
            article = create_test_article(db_session, user_id=userid)
        
        # Update article
        new_headline = f"Updated Article {random_string(10)}"
        new_content = f"This is updated content. {random_string(50)}"
        
        response = authenticated_client.post(f'/article/edit/{article.articleid}', data={
            'headline': new_headline,
            'content': new_content,
            'type': article.type
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert '文章更新成功' in response.get_data(as_text=True)
        
        # Check if the article was actually updated in the database
        updated_article = db_session.query(Article).filter_by(articleid=article.articleid).first()
        assert updated_article.headline == new_headline
        assert updated_article.content == new_content


class TestArticleDelete:
    """Tests for article deletion functionality"""
    
    def test_article_delete_requires_login(self, test_client, db_session):
        """Test that article deletion requires login"""
        # Create a test user and article
        user = create_test_user(db_session)
        article = create_test_article(db_session, user=user)
        
        # Ensure logged out
        test_client.get('/user/logout', follow_redirects=True)
        
        # Try to delete the article
        response = test_client.get(f'/article/delete/{article.articleid}', follow_redirects=True)
        
        assert response.status_code == 200
        assert '用户登录' in response.get_data(as_text=True)
    
    def test_article_delete_requires_ownership(self, authenticated_client, db_session):
        """Test that article deletion requires article ownership"""
        # Create a different user and their article
        other_user = create_test_user(db_session, username="otheruser", password="password123")
        article = create_test_article(db_session, user=other_user)
        
        # Try to delete another user's article
        response = authenticated_client.get(f'/article/delete/{article.articleid}', follow_redirects=True)
        
        assert response.status_code == 200
        assert '只能删除自己的文章' in response.get_data(as_text=True)
    
    def test_successful_article_deletion(self, authenticated_client, db_session, test_app):
        """Test successful article deletion"""
        # Get current user ID
        with authenticated_client.session_transaction() as sess:
            userid = sess.get('userid')
        
        # Create an article for the authenticated user
        with test_app.app_context():
            article = create_test_article(db_session, user_id=userid)
        
        # Delete the article
        response = authenticated_client.get(f'/article/delete/{article.articleid}', follow_redirects=True)
        
        assert response.status_code == 200
        assert '文章已删除' in response.get_data(as_text=True)
        
        # Check if the article was actually deleted or marked as hidden in the database
        deleted_article = db_session.query(Article).filter_by(articleid=article.articleid).first()
        if deleted_article:
            assert deleted_article.hidden == 1  # Article might be soft-deleted (hidden)
        else:
            # Article was hard-deleted
            pass


class TestArticleSearch:
    """Tests for article search functionality"""
    
    def test_article_search(self, test_client, db_session):
        """Test article search functionality"""
        # Create a test user and articles with distinctive headlines
        user = create_test_user(db_session)
        unique_word = random_string(10)
        for i in range(3):
            create_test_article(db_session, user=user, headline=f"Test {unique_word} Article {i+1}")
        
        # Search for articles
        response = test_client.get(f'/article/search?keyword={unique_word}')
        
        assert response.status_code == 200
        response_text = response.get_data(as_text=True)
        
        # Check if all articles with the unique word are found
        for i in range(3):
            assert f"Test {unique_word} Article {i+1}" in response_text
    
    def test_article_search_no_results(self, test_client):
        """Test article search with no results"""
        # Use a random string that likely doesn't exist in any article
        random_keyword = random_string(20)
        response = test_client.get(f'/article/search?keyword={random_keyword}')
        
        assert response.status_code == 200
        assert '没有找到相关文章' in response.get_data(as_text=True)
