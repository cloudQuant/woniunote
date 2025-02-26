import pytest
from woniunote.module.articles import Articles
from woniunote.module.comments import Comments

def test_article_creation(auth_client, test_article_data):
    """Test article creation."""
    # Login first
    auth_client['login']()

    # Create article
    response = auth_client['client'].post('/article/add', data=test_article_data)
    assert response.status_code == 200
    article_id = int(response.data)
    assert article_id > 0

    # Verify article exists
    article = Articles().find_by_id(article_id)
    assert article is not None
    assert article.headline == test_article_data['headline']

def test_article_update(auth_client, test_article_data):
    """Test article update."""
    # Login first
    auth_client['login']()

    # Create initial article
    response = auth_client['client'].post('/article/add', data=test_article_data)
    article_id = int(response.data)

    # Update article
    updated_data = test_article_data.copy()
    updated_data['articleid'] = article_id
    updated_data['headline'] = 'Updated Test Article'
    response = auth_client['client'].post('/article/add', data=updated_data)
    assert response.status_code == 200

    # Verify update
    article = Articles().find_by_id(article_id)
    assert article.headline == 'Updated Test Article'

def test_article_permissions(auth_client, test_article_data):
    """Test article creation permissions."""
    # Try creating article without login
    response = auth_client['client'].post('/article/add', data=test_article_data)
    assert response.data == b'not-login'

    # Login as regular user
    auth_client['login']()

    # Try creating checked article as regular user
    test_article_data['checked'] = 1
    response = auth_client['client'].post('/article/add', data=test_article_data)
    assert response.data == b'perm-denied'

def test_article_listing(auth_client, test_article_data):
    """Test article listing functionality."""
    # Login and create an article
    auth_client['login']()
    auth_client['client'].post('/article/add', data=test_article_data)

    # Test article listing
    response = auth_client['client'].get('/')
    assert response.status_code == 200
    assert b'Test Article' in response.data

def test_article_search(auth_client, test_article_data):
    """Test article search functionality."""
    # Login and create an article
    auth_client['login']()
    auth_client['client'].post('/article/add', data=test_article_data)

    # Test search
    response = auth_client['client'].get('/search/1/Test')
    assert response.status_code == 200
    assert b'Test Article' in response.data

def test_article_comments(auth_client, test_article_data):
    """Test article commenting functionality."""
    # Login and create an article
    auth_client['login']()
    response = auth_client['client'].post('/article/add', data=test_article_data)
    article_id = int(response.data)

    # Add comment
    comment_data = {
        'articleid': article_id,
        'content': 'Test comment',
        'ipaddr': '127.0.0.1'
    }
    response = auth_client['client'].post('/comment', data=comment_data)
    assert response.status_code == 200

    # Verify comment exists
    comments = Comments().find_by_articleid(article_id)
    assert len(comments) > 0
    assert comments[0].content == 'Test comment'

def test_article_favorites(auth_client, test_article_data):
    """Test article favoriting functionality."""
    # Login and create an article
    auth_client['login']()
    response = auth_client['client'].post('/article/add', data=test_article_data)
    article_id = int(response.data)

    # Add to favorites
    response = auth_client['client'].get(f'/favorite/{article_id}')
    assert response.status_code == 200

    # Check favorites list
    response = auth_client['client'].get('/ucenter')
    assert response.status_code == 200
    assert b'Test Article' in response.data

def test_article_type_filter(auth_client, test_article_data):
    """Test article filtering by type."""
    # Login and create articles of different types
    auth_client['login']()
    
    # Create article of type 1
    auth_client['client'].post('/article/add', data=test_article_data)
    
    # Create article of type 2
    test_article_data['article_type'] = 2
    test_article_data['headline'] = 'Type 2 Article'
    auth_client['client'].post('/article/add', data=test_article_data)

    # Test filtering by type
    response = auth_client['client'].get('/type/1')
    assert response.status_code == 200
    assert b'Test Article' in response.data
    assert b'Type 2 Article' not in response.data
