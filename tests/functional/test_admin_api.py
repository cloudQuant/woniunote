"""
WoniuNote Admin API Tests

Tests for admin-related API endpoints including admin login, user management,
article management, and system settings.
"""
import pytest
from ..test_helpers import (
    User, Article, Comment, random_string, create_test_user, create_test_article, create_test_comment
)

class TestAdminLogin:
    """Tests for admin login functionality"""
    
    def test_admin_login_page(self, test_client):
        """Test that admin login page loads correctly"""
        response = test_client.get('/admin/login')
        
        assert response.status_code == 200
        assert '管理员登录' in response.get_data(as_text=True)
    
    def test_successful_admin_login(self, test_client, db_session):
        """Test successful admin login"""
        # Create admin user if it doesn't exist
        admin = db_session.query(User).filter_by(username="admin").first()
        if not admin:
            admin = create_test_user(
                db_session, 
                username="admin", 
                password="admin123", 
                role="admin"
            )
        
        # Ensure logged out
        test_client.get('/user/logout', follow_redirects=True)
        
        # Login as admin
        response = test_client.post('/admin/login', data={
            'username': admin.username,
            'password': "admin123"  # Use the known password
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert '管理员控制台' in response.get_data(as_text=True)
    
    def test_admin_login_with_non_admin_account(self, test_client, db_session):
        """Test admin login with non-admin account"""
        # Create regular user
        user = create_test_user(
            db_session, 
            username=f"regular_{random_string(8)}", 
            password="Test@123", 
            role="user"
        )
        
        # Try to login to admin with regular user
        response = test_client.post('/admin/login', data={
            'username': user.username,
            'password': "Test@123"
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert '您不是管理员' in response.get_data(as_text=True)


class TestAdminDashboard:
    """Tests for admin dashboard functionality"""
    
    @pytest.fixture
    def admin_client(self, test_client, db_session):
        """Create an authenticated admin client"""
        # Create admin user if it doesn't exist
        admin = db_session.query(User).filter_by(username="admin").first()
        if not admin:
            admin = create_test_user(
                db_session, 
                username="admin", 
                password="admin123", 
                role="admin"
            )
        
        # Ensure logged out
        test_client.get('/user/logout', follow_redirects=True)
        
        # Login as admin
        test_client.post('/admin/login', data={
            'username': admin.username,
            'password': "admin123"  # Use the known password
        }, follow_redirects=True)
        
        return test_client
    
    def test_admin_dashboard_requires_admin_login(self, test_client):
        """Test that admin dashboard requires admin login"""
        # Ensure logged out
        test_client.get('/user/logout', follow_redirects=True)
        
        # Try to access admin dashboard
        response = test_client.get('/admin', follow_redirects=True)
        
        assert response.status_code == 200
        assert '管理员登录' in response.get_data(as_text=True)
    
    def test_admin_dashboard_loads(self, admin_client):
        """Test that admin dashboard loads correctly"""
        response = admin_client.get('/admin')
        
        assert response.status_code == 200
        assert '管理员控制台' in response.get_data(as_text=True)
        assert '系统概况' in response.get_data(as_text=True)


class TestUserManagement:
    """Tests for user management functionality"""
    
    @pytest.fixture
    def admin_client(self, test_client, db_session):
        """Create an authenticated admin client"""
        # Create admin user if it doesn't exist
        admin = db_session.query(User).filter_by(username="admin").first()
        if not admin:
            admin = create_test_user(
                db_session, 
                username="admin", 
                password="admin123", 
                role="admin"
            )
        
        # Ensure logged out
        test_client.get('/user/logout', follow_redirects=True)
        
        # Login as admin
        test_client.post('/admin/login', data={
            'username': admin.username,
            'password': "admin123"  # Use the known password
        }, follow_redirects=True)
        
        return test_client
    
    def test_user_list(self, admin_client, db_session):
        """Test user list displays correctly"""
        # Create some test users
        for i in range(3):
            create_test_user(
                db_session, 
                username=f"userlist_{random_string(6)}_{i}", 
                password="Test@123"
            )
        
        # Access user list
        response = admin_client.get('/admin/user')
        
        assert response.status_code == 200
        assert '用户管理' in response.get_data(as_text=True)
        
        # Check for user table
        assert '<table' in response.get_data(as_text=True)
        assert 'admin' in response.get_data(as_text=True)  # Admin user should be listed
    
    def test_user_details(self, admin_client, db_session):
        """Test user details display correctly"""
        # Create a test user
        user = create_test_user(
            db_session, 
            username=f"userdetail_{random_string(8)}", 
            password="Test@123",
            nickname=f"User Detail {random_string(6)}"
        )
        
        # Access user details
        response = admin_client.get(f'/admin/user/detail/{user.userid}')
        
        assert response.status_code == 200
        assert '用户详情' in response.get_data(as_text=True)
        assert user.username in response.get_data(as_text=True)
        assert user.nickname in response.get_data(as_text=True)
    
    def test_update_user_status(self, admin_client, db_session):
        """Test updating user status (e.g., locking/unlocking)"""
        # Create a test user
        user = create_test_user(
            db_session, 
            username=f"lockuser_{random_string(8)}", 
            password="Test@123"
        )
        
        # Lock the user (implementation depends on how locking is handled in your app)
        # This might be setting a "status" field, or might be a separate endpoint
        response = admin_client.get(f'/admin/user/lock/{user.userid}', follow_redirects=True)
        
        # Check for appropriate response (status change confirmation)
        assert response.status_code == 200
        
        # Note: Since we don't know the exact implementation of locking, 
        # we can't make specific assertions about the response content or database state
        # Modify these assertions based on your actual implementation
        
        # Example if there's a "locked" or "status" field:
        # updated_user = db_session.query(User).filter_by(userid=user.userid).first()
        # assert updated_user.locked == 1  # or assert updated_user.status == 'locked'
    
    def test_update_user_role(self, admin_client, db_session):
        """Test updating user role"""
        # Create a test user
        user = create_test_user(
            db_session, 
            username=f"roleuser_{random_string(8)}", 
            password="Test@123",
            role="user"
        )
        
        # Change the user's role to admin
        response = admin_client.post(f'/admin/user/role/{user.userid}', data={
            'role': 'admin'
        }, follow_redirects=True)
        
        # Check for appropriate response
        assert response.status_code == 200
        
        # Check if role was updated in the database
        updated_user = db_session.query(User).filter_by(userid=user.userid).first()
        assert updated_user.role == 'admin'


class TestArticleManagement:
    """Tests for article management functionality"""
    
    @pytest.fixture
    def admin_client(self, test_client, db_session):
        """Create an authenticated admin client"""
        # Create admin user if it doesn't exist
        admin = db_session.query(User).filter_by(username="admin").first()
        if not admin:
            admin = create_test_user(
                db_session, 
                username="admin", 
                password="admin123", 
                role="admin"
            )
        
        # Ensure logged out
        test_client.get('/user/logout', follow_redirects=True)
        
        # Login as admin
        test_client.post('/admin/login', data={
            'username': admin.username,
            'password': "admin123"  # Use the known password
        }, follow_redirects=True)
        
        return test_client
    
    def test_article_list(self, admin_client, db_session):
        """Test article list displays correctly"""
        # Create a test user and articles
        user = create_test_user(db_session)
        for i in range(3):
            create_test_article(
                db_session, 
                user=user, 
                headline=f"Admin Article Test {i} {random_string(8)}"
            )
        
        # Access article list
        response = admin_client.get('/admin/article')
        
        assert response.status_code == 200
        assert '文章管理' in response.get_data(as_text=True)
        
        # Check for article table
        assert '<table' in response.get_data(as_text=True)
    
    def test_article_details(self, admin_client, db_session):
        """Test article details display correctly"""
        # Create a test user and article
        user = create_test_user(db_session)
        article = create_test_article(
            db_session, 
            user=user, 
            headline=f"Admin Article Detail {random_string(8)}"
        )
        
        # Access article details
        response = admin_client.get(f'/admin/article/detail/{article.articleid}')
        
        assert response.status_code == 200
        assert '文章详情' in response.get_data(as_text=True)
        assert article.headline in response.get_data(as_text=True)
        assert article.content in response.get_data(as_text=True)
    
    def test_check_article(self, admin_client, db_session):
        """Test checking/approving an article"""
        # Create a test user and unchecked article
        user = create_test_user(db_session)
        article = create_test_article(db_session, user=user)
        
        # Set article as unchecked
        article.checked = 0
        db_session.commit()
        
        # Check/approve the article
        response = admin_client.get(f'/admin/article/check/{article.articleid}', follow_redirects=True)
        
        # Verify response
        assert response.status_code == 200
        
        # Verify article is now checked
        checked_article = db_session.query(Article).filter_by(articleid=article.articleid).first()
        assert checked_article.checked == 1
    
    def test_hide_article(self, admin_client, db_session):
        """Test hiding an article"""
        # Create a test user and visible article
        user = create_test_user(db_session)
        article = create_test_article(db_session, user=user)
        
        # Set article as visible
        article.hidden = 0
        db_session.commit()
        
        # Hide the article
        response = admin_client.get(f'/admin/article/hide/{article.articleid}', follow_redirects=True)
        
        # Verify response
        assert response.status_code == 200
        
        # Verify article is now hidden
        hidden_article = db_session.query(Article).filter_by(articleid=article.articleid).first()
        assert hidden_article.hidden == 1
    
    def test_recommend_article(self, admin_client, db_session):
        """Test recommending an article"""
        # Create a test user and non-recommended article
        user = create_test_user(db_session)
        article = create_test_article(db_session, user=user)
        
        # Set article as not recommended
        article.recommended = 0
        db_session.commit()
        
        # Recommend the article
        response = admin_client.get(f'/admin/article/recommend/{article.articleid}', follow_redirects=True)
        
        # Verify response
        assert response.status_code == 200
        
        # Verify article is now recommended
        recommended_article = db_session.query(Article).filter_by(articleid=article.articleid).first()
        assert recommended_article.recommended == 1


class TestCommentManagement:
    """Tests for comment management functionality"""
    
    @pytest.fixture
    def admin_client(self, test_client, db_session):
        """Create an authenticated admin client"""
        # Create admin user if it doesn't exist
        admin = db_session.query(User).filter_by(username="admin").first()
        if not admin:
            admin = create_test_user(
                db_session, 
                username="admin", 
                password="admin123", 
                role="admin"
            )
        
        # Ensure logged out
        test_client.get('/user/logout', follow_redirects=True)
        
        # Login as admin
        test_client.post('/admin/login', data={
            'username': admin.username,
            'password': "admin123"  # Use the known password
        }, follow_redirects=True)
        
        return test_client
    
    def test_comment_list(self, admin_client, db_session):
        """Test comment list displays correctly"""
        # Create test users, articles and comments
        user = create_test_user(db_session)
        article = create_test_article(db_session, user=user)
        for i in range(3):
            create_test_comment(
                db_session, 
                user=user, 
                article=article, 
                content=f"Admin Comment Test {i} {random_string(10)}"
            )
        
        # Access comment list
        response = admin_client.get('/admin/comment')
        
        assert response.status_code == 200
        assert '评论管理' in response.get_data(as_text=True)
        
        # Check for comment table
        assert '<table' in response.get_data(as_text=True)
    
    def test_hide_comment(self, admin_client, db_session):
        """Test hiding a comment"""
        # Create a test user, article and visible comment
        user = create_test_user(db_session)
        article = create_test_article(db_session, user=user)
        comment = create_test_comment(db_session, user=user, article=article)
        
        # Set comment as visible
        comment.hidden = 0
        db_session.commit()
        
        # Hide the comment
        response = admin_client.get(f'/admin/comment/hide/{comment.commentid}', follow_redirects=True)
        
        # Verify response
        assert response.status_code == 200
        
        # Verify comment is now hidden
        hidden_comment = db_session.query(Comment).filter_by(commentid=comment.commentid).first()
        assert hidden_comment.hidden == 1


class TestSystemSettings:
    """Tests for system settings functionality"""
    
    @pytest.fixture
    def admin_client(self, test_client, db_session):
        """Create an authenticated admin client"""
        # Create admin user if it doesn't exist
        admin = db_session.query(User).filter_by(username="admin").first()
        if not admin:
            admin = create_test_user(
                db_session, 
                username="admin", 
                password="admin123", 
                role="admin"
            )
        
        # Ensure logged out
        test_client.get('/user/logout', follow_redirects=True)
        
        # Login as admin
        test_client.post('/admin/login', data={
            'username': admin.username,
            'password': "admin123"  # Use the known password
        }, follow_redirects=True)
        
        return test_client
    
    def test_system_settings_page(self, admin_client):
        """Test system settings page loads correctly"""
        response = admin_client.get('/admin/settings')
        
        assert response.status_code == 200
        assert '系统设置' in response.get_data(as_text=True)
    
    def test_update_system_settings(self, admin_client):
        """Test updating system settings"""
        # Update system settings
        site_name = f"WoniuNote Test {random_string(8)}"
        site_description = f"Test Description {random_string(20)}"
        
        response = admin_client.post('/admin/settings/update', data={
            'site_name': site_name,
            'site_description': site_description,
            # Add other settings as needed
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert '设置已更新' in response.get_data(as_text=True)
        
        # Check if settings were applied
        response = admin_client.get('/')
        assert site_name in response.get_data(as_text=True)
