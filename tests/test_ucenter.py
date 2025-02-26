import pytest
from woniunote.module.favorites import Favorites
from woniunote.module.credits import Credits

def test_user_center_access(auth_client):
    """Test user center access control."""
    client = auth_client['client']

    # Try accessing without login
    response = client.get('/ucenter')
    assert response.status_code == 302  # Should redirect to login

    # Login and try again
    auth_client['login']()
    response = client.get('/ucenter')
    assert response.status_code == 200

def test_user_articles(auth_client, test_article_data):
    """Test user's article management."""
    # Login and create article
    auth_client['login']()
    client = auth_client['client']
    client.post('/article/add', data=test_article_data)

    # Check user's articles page
    response = client.get('/user/article')
    assert response.status_code == 200
    assert b'Test Article' in response.data

def test_user_comments(auth_client, test_article_data):
    """Test user's comment management."""
    # Login and create article
    auth_client['login']()
    client = auth_client['client']
    response = client.post('/article/add', data=test_article_data)
    article_id = int(response.data)

    # Add comment
    comment_data = {
        'articleid': article_id,
        'content': 'Test comment',
        'ipaddr': '127.0.0.1'
    }
    client.post('/comment', data=comment_data)

    # Check user's comments page
    response = client.get('/user/comment')
    assert response.status_code == 200
    assert b'Test Article' in response.data

def test_user_favorites(auth_client, test_article_data):
    """Test user's favorites management."""
    # Login and create article
    auth_client['login']()
    client = auth_client['client']
    response = client.post('/article/add', data=test_article_data)
    article_id = int(response.data)

    # Add to favorites
    response = client.get(f'/favorite/{article_id}')
    assert response.status_code == 200

    # Verify in favorites
    response = client.get('/ucenter')
    assert response.status_code == 200
    assert b'Test Article' in response.data

    # Remove from favorites
    response = client.get(f'/favorite/{article_id}')
    assert response.status_code == 200

    # Verify removed from favorites
    response = client.get('/ucenter')
    assert response.status_code == 200
    assert b'Test Article' not in response.data

def test_user_credits(auth_client, test_article_data):
    """Test user credit system."""
    # Login
    auth_client['login']()
    client = auth_client['client']

    # Create article (should earn credits)
    client.post('/article/add', data=test_article_data)

    # Check credits
    credits = Credits().get_user_credits()
    assert credits > 0

def test_user_profile(auth_client):
    """Test user profile management."""
    # Login
    auth_client['login']()
    client = auth_client['client']

    # Access profile page
    response = client.get('/user/post')
    assert response.status_code == 200

def test_user_draft_articles(auth_client, test_article_data):
    """Test draft article functionality."""
    # Login
    auth_client['login']()
    client = auth_client['client']

    # Create draft article
    draft_article = test_article_data.copy()
    draft_article['drafted'] = 1
    response = client.post('/article/add', data=draft_article)
    assert response.status_code == 200

    # Check drafts in user articles
    response = client.get('/user/article')
    assert response.status_code == 200
    assert b'Test Article' in response.data

def test_user_article_workflow(auth_client, test_article_data):
    """Test complete article workflow."""
    # Login
    auth_client['login']()
    client = auth_client['client']

    # 1. Create draft
    draft_article = test_article_data.copy()
    draft_article['drafted'] = 1
    response = client.post('/article/add', data=draft_article)
    article_id = int(response.data)

    # 2. Update draft
    draft_article['articleid'] = article_id
    draft_article['headline'] = 'Updated Draft'
    response = client.post('/article/add', data=draft_article)
    assert response.status_code == 200

    # 3. Publish article
    draft_article['drafted'] = 0
    response = client.post('/article/add', data=draft_article)
    assert response.status_code == 200

    # 4. Verify published
    response = client.get('/user/article')
    assert response.status_code == 200
    assert b'Updated Draft' in response.data
