import pytest
from flask import session
from woniunote.module.users import Users

def test_register(client):
    """Test user registration."""
    # Test successful registration
    response = client.post('/user', data={
        'username': 'newuser@example.com',
        'password': 'password123',
        'ecode': '123456'
    })
    assert response.data == b'reg-pass'
    
    # Test duplicate registration
    response = client.post('/user', data={
        'username': 'newuser@example.com',
        'password': 'password123',
        'ecode': '123456'
    })
    assert response.data == b'user-repeated'

def test_login_logout(auth_client):
    """Test login and logout functionality."""
    client = auth_client['client']
    login = auth_client['login']
    logout = auth_client['logout']

    # Test successful login
    response = login()
    assert response.data == b'login-pass'

    # Test invalid credentials
    response = client.post('/login', data={
        'username': 'wrong@example.com',
        'password': 'wrongpass',
        'vcode': '0000'
    })
    assert response.data == b'login-fail'

    # Test logout
    response = logout()
    assert response.status_code == 302
    assert b'\u6ce8\u9500\u5e76\u8fdb\u884c\u91cd\u5b9a\u5411' in response.data  # "注销并进行重定向"

def test_multiple_sessions(auth_client, app):
    """Test multiple session handling."""
    client1 = auth_client['client']
    client2 = app.test_client()

    # Login with first client
    response1 = client1.post('/login', data={
        'username': 'test@example.com',
        'password': 'password123',
        'vcode': '0000'
    })
    assert response1.data == b'login-pass'

    # Login with second client
    response2 = client2.post('/login', data={
        'username': 'test2@example.com',
        'password': 'password123',
        'vcode': '0000'
    })
    assert response2.data == b'login-pass'

    # Verify both sessions are active
    with client1.session_transaction() as sess1:
        assert sess1.get('active_sessions') is not None
        
    with client2.session_transaction() as sess2:
        assert sess2.get('active_sessions') is not None

def test_session_data_isolation(auth_client, test_user, app):
    """Test that session data is properly isolated between users."""
    client1 = auth_client['client']
    client2 = app.test_client()

    # Login both users
    response1 = client1.post('/login', data={
        'username': test_user['username'],
        'password': test_user['password'],
        'vcode': '0000'
    })
    assert response1.data == b'login-pass'

    response2 = client2.post('/login', data={
        'username': 'other@example.com',
        'password': 'password123',
        'vcode': '0000'
    })
    assert response2.data == b'login-pass'

    # Verify session data isolation
    with client1.session_transaction() as sess1:
        user1_id = sess1.get('userid')
    
    with client2.session_transaction() as sess2:
        user2_id = sess2.get('userid')
    
    assert user1_id != user2_id

def test_invalid_session(client):
    """Test accessing protected routes without valid session."""
    # Try to access protected route without login
    response = client.get('/ucenter')
    assert response.status_code == 302  # Should redirect to login

def test_session_expiry(auth_client, app):
    """Test session expiry handling."""
    client = auth_client['client']
    login = auth_client['login']

    # Login and verify success
    response = login()
    assert response.data == b'login-pass'

    # Simulate session expiry
    with client.session_transaction() as sess:
        sess.clear()

    # Try to access protected route
    response = client.get('/ucenter')
    assert response.status_code == 302  # Should redirect to login
