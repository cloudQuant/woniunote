"""
WoniuNote User API Tests

Tests for user-related API endpoints including registration, login, profile management.
"""
import os
import sys
import pytest
from flask import session
from ..test_helpers import (
    User, random_string, ResponseParser, create_test_user, create_test_article
)

class TestUserRegistration:
    """Tests for user registration functionality"""
    
    def test_register_page_loads(self, test_client):
        """Test that the registration page loads correctly"""
        response = test_client.get('/user/register')
        assert response.status_code == 200
        assert '用户注册' in response.get_data(as_text=True)
    
    def test_successful_registration(self, test_client):
        """Test successful user registration"""
        username = f"testuser_{random_string(8)}"
        password = "Test@123"
        confirm = "Test@123"
        nickname = f"Test User {random_string(6)}"
        qq = random_qq()
        
        response = test_client.post('/user/register', data={
            'username': username,
            'password': password,
            'confirm': confirm,
            'nickname': nickname,
            'qq': qq
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert '注册成功' in response.get_data(as_text=True)
    
    def test_registration_with_existing_username(self, test_client, db_session):
        """Test registration with already existing username"""
        # First registration
        username = f"duplicate_{random_string(8)}"
        password = "Test@123"
        confirm = "Test@123"
        nickname = f"Test User {random_string(6)}"
        qq = random_qq()
        
        response = test_client.post('/user/register', data={
            'username': username,
            'password': password,
            'confirm': confirm,
            'nickname': nickname,
            'qq': qq
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert '注册成功' in response.get_data(as_text=True)
        
        # Second registration with same username
        response = test_client.post('/user/register', data={
            'username': username,
            'password': password,
            'confirm': confirm,
            'nickname': f"Another {nickname}",
            'qq': random_qq()
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert '用户名已被注册' in response.get_data(as_text=True)
    
    def test_registration_with_password_mismatch(self, test_client):
        """Test registration with password and confirm password not matching"""
        username = f"testuser_{random_string(8)}"
        password = "Test@123"
        confirm = "DifferentPassword"
        nickname = f"Test User {random_string(6)}"
        qq = random_qq()
        
        response = test_client.post('/user/register', data={
            'username': username,
            'password': password,
            'confirm': confirm,
            'nickname': nickname,
            'qq': qq
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert '两次密码不一致' in response.get_data(as_text=True)
    
    def test_registration_with_missing_fields(self, test_client):
        """Test registration with missing required fields"""
        # Missing username
        response = test_client.post('/user/register', data={
            'password': "Test@123",
            'confirm': "Test@123",
            'nickname': f"Test User {random_string(6)}",
            'qq': random_qq()
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert '请输入用户名' in response.get_data(as_text=True)
        
        # Missing password
        username = f"testuser_{random_string(8)}"
        response = test_client.post('/user/register', data={
            'username': username,
            'confirm': "Test@123",
            'nickname': f"Test User {random_string(6)}",
            'qq': random_qq()
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert '请输入密码' in response.get_data(as_text=True)


class TestUserLogin:
    """Tests for user login functionality"""
    
    def test_login_page_loads(self, test_client):
        """Test that the login page loads correctly"""
        response = test_client.get('/user/login')
        assert response.status_code == 200
        assert '用户登录' in response.get_data(as_text=True)
    
    def test_successful_login(self, test_client):
        """Test successful user login"""
        # Register a user first
        username = f"logintest_{random_string(8)}"
        password = "Test@123"
        nickname = f"Login Test {random_string(6)}"
        qq = random_qq()
        
        # Register
        test_client.post('/user/register', data={
            'username': username,
            'password': password,
            'confirm': password,
            'nickname': nickname,
            'qq': qq
        }, follow_redirects=True)
        
        # Logout to ensure clean session
        test_client.get('/user/logout', follow_redirects=True)
        
        # Login
        response = test_client.post('/user/login', data={
            'username': username,
            'password': password
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert '登录成功' in response.get_data(as_text=True)
        assert nickname in response.get_data(as_text=True)
    
    def test_login_with_incorrect_password(self, test_client):
        """Test login with incorrect password"""
        # Register a user first
        username = f"wrongpass_{random_string(8)}"
        password = "Test@123"
        nickname = f"Wrong Pass Test {random_string(6)}"
        qq = random_qq()
        
        # Register
        test_client.post('/user/register', data={
            'username': username,
            'password': password,
            'confirm': password,
            'nickname': nickname,
            'qq': qq
        }, follow_redirects=True)
        
        # Logout to ensure clean session
        test_client.get('/user/logout', follow_redirects=True)
        
        # Login with wrong password
        response = test_client.post('/user/login', data={
            'username': username,
            'password': 'WrongPassword'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert '用户名或密码错误' in response.get_data(as_text=True)
    
    def test_login_with_nonexistent_user(self, test_client):
        """Test login with non-existent username"""
        response = test_client.post('/user/login', data={
            'username': f"nonexistent_{random_string(10)}",
            'password': 'SomePassword'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert '用户名或密码错误' in response.get_data(as_text=True)


class TestUserProfile:
    """Tests for user profile functionality"""
    
    def test_profile_page_requires_login(self, test_client):
        """Test that profile page requires login"""
        # Ensure logged out
        test_client.get('/user/logout', follow_redirects=True)
        
        # Try to access profile page
        response = test_client.get('/user/profile', follow_redirects=True)
        
        assert response.status_code == 200
        assert '用户登录' in response.get_data(as_text=True)
    
    def test_profile_page_loads_for_logged_in_user(self, test_client):
        """Test that profile page loads for logged in user"""
        # Register and login
        username = f"profile_{random_string(8)}"
        password = "Test@123"
        nickname = f"Profile Test {random_string(6)}"
        qq = random_qq()
        
        # Register
        test_client.post('/user/register', data={
            'username': username,
            'password': password,
            'confirm': password,
            'nickname': nickname,
            'qq': qq
        }, follow_redirects=True)
        
        # Access profile page
        response = test_client.get('/user/profile', follow_redirects=True)
        
        assert response.status_code == 200
        assert nickname in response.get_data(as_text=True)
        assert username in response.get_data(as_text=True)
    
    def test_update_profile(self, test_client):
        """Test updating user profile"""
        # Register and login
        username = f"updateprofile_{random_string(8)}"
        password = "Test@123"
        nickname = f"Update Profile {random_string(6)}"
        qq = random_qq()
        
        # Register
        test_client.post('/user/register', data={
            'username': username,
            'password': password,
            'confirm': password,
            'nickname': nickname,
            'qq': qq
        }, follow_redirects=True)
        
        # Update profile
        new_nickname = f"Updated {nickname}"
        new_qq = random_qq()
        
        response = test_client.post('/user/profile', data={
            'nickname': new_nickname,
            'qq': new_qq
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert '个人资料已更新' in response.get_data(as_text=True)
        assert new_nickname in response.get_data(as_text=True)
    
    def test_change_password(self, test_client):
        """Test changing user password"""
        # Register and login
        username = f"changepwd_{random_string(8)}"
        password = "Test@123"
        nickname = f"Change Password {random_string(6)}"
        qq = random_qq()
        
        # Register
        test_client.post('/user/register', data={
            'username': username,
            'password': password,
            'confirm': password,
            'nickname': nickname,
            'qq': qq
        }, follow_redirects=True)
        
        # Change password
        new_password = "NewTest@456"
        
        response = test_client.post('/user/password', data={
            'oldpassword': password,
            'newpassword': new_password,
            'confirm': new_password
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert '密码已修改' in response.get_data(as_text=True)
        
        # Logout
        test_client.get('/user/logout', follow_redirects=True)
        
        # Login with new password
        response = test_client.post('/user/login', data={
            'username': username,
            'password': new_password
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert '登录成功' in response.get_data(as_text=True)
    
    def test_password_change_with_incorrect_old_password(self, test_client):
        """Test changing password with incorrect old password"""
        # Register and login
        username = f"wrongoldpwd_{random_string(8)}"
        password = "Test@123"
        nickname = f"Wrong Old Password {random_string(6)}"
        qq = random_qq()
        
        # Register
        test_client.post('/user/register', data={
            'username': username,
            'password': password,
            'confirm': password,
            'nickname': nickname,
            'qq': qq
        }, follow_redirects=True)
        
        # Try to change password with wrong old password
        new_password = "NewTest@456"
        
        response = test_client.post('/user/password', data={
            'oldpassword': 'WrongPassword',
            'newpassword': new_password,
            'confirm': new_password
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert '原密码错误' in response.get_data(as_text=True)


class TestUserLogout:
    """Tests for user logout functionality"""
    
    def test_logout(self, test_client):
        """Test user logout"""
        # Register and login
        username = f"logout_{random_string(8)}"
        password = "Test@123"
        nickname = f"Logout Test {random_string(6)}"
        qq = random_qq()
        
        # Register
        test_client.post('/user/register', data={
            'username': username,
            'password': password,
            'confirm': password,
            'nickname': nickname,
            'qq': qq
        }, follow_redirects=True)
        
        # Logout
        response = test_client.get('/user/logout', follow_redirects=True)
        
        assert response.status_code == 200
        assert '已退出登录' in response.get_data(as_text=True)
        
        # Try to access profile page (should redirect to login)
        response = test_client.get('/user/profile', follow_redirects=True)
        
        assert response.status_code == 200
        assert '用户登录' in response.get_data(as_text=True)
