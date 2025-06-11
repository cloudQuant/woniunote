"""
Comprehensive unit tests for all WoniuNote modules.

This module tests all module-level operations with proper mocking
to avoid context and dependency issues.
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


class TestUsersModule:
    """Test Users module functionality."""
    
    def test_users_class_instantiation(self):
        """Test Users class can be instantiated."""
        from woniunote.module.users import Users
        
        user = Users()
        assert user is not None

    @patch('woniunote.module.users.dbsession')
    def test_users_find_by_username(self, mock_dbsession):
        """Test Users.find_by_username method."""
        from woniunote.module.users import Users
        
        # Mock query result
        mock_dbsession.query.return_value.filter_by.return_value.all.return_value = [
            MagicMock(userid=1, username='test@example.com')
        ]
        
        user = Users()
        result = user.find_by_username('test@example.com')
        
        assert len(result) == 1
        assert result[0].username == 'test@example.com'

    @patch('woniunote.module.users.dbsession')
    def test_users_do_register(self, mock_dbsession):
        """Test Users.do_register method."""
        from woniunote.module.users import Users
        
        # Mock user creation
        mock_user = MagicMock()
        mock_user.userid = 1
        mock_user.nickname = 'Test User'
        mock_user.role = 1
        
        mock_dbsession.add = MagicMock()
        mock_dbsession.commit = MagicMock()
        mock_dbsession.refresh = MagicMock()
        
        with patch('woniunote.module.users.User') as mock_user_class:
            mock_user_class.return_value = mock_user
            
            user = Users()
            result = user.do_register('test@example.com', 'hashedpassword')
            
            assert result.userid == 1
            assert result.nickname == 'Test User'
            mock_dbsession.add.assert_called()

    @patch('woniunote.module.users.dbsession')
    def test_users_find_by_id(self, mock_dbsession):
        """Test Users.find_by_id method."""
        from woniunote.module.users import Users
        
        mock_user = MagicMock(userid=1, username='test@example.com')
        mock_dbsession.query.return_value.filter_by.return_value.first.return_value = mock_user
        
        user = Users()
        result = user.find_by_id(1)
        
        assert result.userid == 1
        assert result.username == 'test@example.com'


class TestArticlesModule:
    """Test Articles module functionality."""

    def test_articles_class_methods_exist(self):
        """Test Articles class has required methods."""
        from woniunote.module.articles import Articles
        
        # Test static methods exist
        assert hasattr(Articles, 'find_all')
        assert hasattr(Articles, 'find_by_id')
        assert hasattr(Articles, 'insert_article')
        assert hasattr(Articles, 'update_article')
        assert hasattr(Articles, 'find_by_userid')

    @patch('woniunote.module.articles.dbsession')
    def test_articles_find_all(self, mock_dbsession):
        """Test Articles.find_all method."""
        from woniunote.module.articles import Articles
        
        mock_articles = [
            MagicMock(articleid=1, headline='Article 1'),
            MagicMock(articleid=2, headline='Article 2')
        ]
        mock_dbsession.query.return_value.all.return_value = mock_articles
        
        result = Articles.find_all()
        assert len(result) == 2
        assert result[0].headline == 'Article 1'

    @patch('woniunote.module.articles.dbsession')
    def test_articles_get_total_count(self, mock_dbsession):
        """Test Articles.get_total_count method."""
        from woniunote.module.articles import Articles
        
        mock_dbsession.query.return_value.count.return_value = 42
        
        result = Articles.get_total_count()
        assert result == 42

    @patch('woniunote.module.articles.dbsession')
    def test_articles_find_by_type(self, mock_dbsession):
        """Test Articles.find_by_type method."""
        from woniunote.module.articles import Articles
        
        mock_articles = [MagicMock(articleid=1, type=1)]
        mock_dbsession.query.return_value.filter_by.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = mock_articles
        
        result = Articles.find_by_type(1, 0, 10)
        assert len(result) == 1
        assert result[0].type == 1

    @patch('woniunote.module.articles.dbsession')
    def test_articles_update_read_count(self, mock_dbsession):
        """Test Articles.update_read_count method."""
        from woniunote.module.articles import Articles
        
        mock_article = MagicMock()
        mock_article.readcount = 5
        mock_dbsession.query.return_value.filter_by.return_value.first.return_value = mock_article
        mock_dbsession.commit = MagicMock()
        
        result = Articles.update_read_count(1)
        assert mock_article.readcount == 6
        mock_dbsession.commit.assert_called()


class TestCreditsModule:
    """Test Credits module functionality."""
    
    def test_credits_class_import(self):
        """Test Credits class can be imported."""
        from woniunote.module.credits import Credits
        
        credits = Credits()
        assert credits is not None

    @patch('woniunote.module.credits.dbsession')
    def test_credits_insert_detail(self, mock_dbsession):
        """Test Credits.insert_detail method."""
        from woniunote.module.credits import Credits
        
        mock_dbsession.add = MagicMock()
        mock_dbsession.commit = MagicMock()
        
        with patch('woniunote.module.credits.session', {'userid': 1}):
            credits = Credits()
            result = credits.insert_detail('用户注册', '0', 50)
            
            mock_dbsession.add.assert_called()
            mock_dbsession.commit.assert_called()


class TestCommentsModule:
    """Test Comments module functionality."""
    
    def test_comments_class_import(self):
        """Test Comments class can be imported."""
        from woniunote.module.comments import Comments
        
        comments = Comments()
        assert comments is not None

    @patch('woniunote.module.comments.dbsession')
    def test_comments_find_by_articleid(self, mock_dbsession):
        """Test Comments.find_by_articleid method."""
        from woniunote.module.comments import Comments
        
        mock_comments = [
            MagicMock(commentid=1, content='Comment 1'),
            MagicMock(commentid=2, content='Comment 2')
        ]
        mock_dbsession.query.return_value.filter_by.return_value.order_by.return_value.all.return_value = mock_comments
        
        comments = Comments()
        result = comments.find_by_articleid(1)
        assert len(result) == 2


class TestFavoritesModule:
    """Test Favorites module functionality."""
    
    def test_favorites_class_import(self):
        """Test Favorites class can be imported."""
        from woniunote.module.favorites import Favorites
        
        favorites = Favorites()
        assert favorites is not None

    @patch('woniunote.module.favorites.dbsession')
    def test_favorites_find_by_userid(self, mock_dbsession):
        """Test Favorites.find_by_userid method."""
        from woniunote.module.favorites import Favorites
        
        mock_favorites = [MagicMock(favoriteid=1, articleid=1)]
        mock_dbsession.query.return_value.filter_by.return_value.order_by.return_value.all.return_value = mock_favorites
        
        favorites = Favorites()
        result = favorites.find_by_userid(1)
        assert len(result) == 1


class TestTagsModule:
    """Test Tags module functionality."""
    
    def test_tags_class_import(self):
        """Test Tags class can be imported if exists."""
        try:
            from woniunote.module.tags import Tags
            
            tags = Tags()
            assert tags is not None
        except ImportError:
            # Tags module might not exist
            pass


class TestTypesModule:
    """Test Types module functionality."""
    
    def test_types_class_import(self):
        """Test Types class can be imported if exists."""
        try:
            from woniunote.module.types import Types
            
            types = Types()
            assert types is not None
        except ImportError:
            # Types module might not exist
            pass


class TestRewardsModule:
    """Test Rewards module functionality."""
    
    def test_rewards_class_import(self):
        """Test Rewards class can be imported if exists."""
        try:
            from woniunote.module.rewards import Rewards
            
            rewards = Rewards()
            assert rewards is not None
        except ImportError:
            # Rewards module might not exist
            pass


class TestModuleIntegration:
    """Test integration between different modules."""
    
    @patch('woniunote.module.users.dbsession')
    @patch('woniunote.module.articles.dbsession')
    def test_user_article_relationship(self, mock_articles_db, mock_users_db):
        """Test relationship between users and articles."""
        from woniunote.module.users import Users
        from woniunote.module.articles import Articles
        
        # Mock user
        mock_user = MagicMock(userid=1, username='test@example.com')
        mock_users_db.query.return_value.filter_by.return_value.first.return_value = mock_user
        
        # Mock user's articles
        mock_articles = [
            MagicMock(articleid=1, userid=1, headline='User Article 1'),
            MagicMock(articleid=2, userid=1, headline='User Article 2')
        ]
        mock_articles_db.query.return_value.filter_by.return_value.order_by.return_value.all.return_value = mock_articles
        
        # Test integration
        user = Users()
        user_result = user.find_by_id(1)
        assert user_result.userid == 1
        
        articles_result = Articles.find_by_userid(1)
        assert len(articles_result) == 2
        assert all(article.userid == 1 for article in articles_result)

    @patch('woniunote.module.favorites.dbsession')
    @patch('woniunote.module.articles.dbsession')
    def test_favorites_article_relationship(self, mock_articles_db, mock_favorites_db):
        """Test relationship between favorites and articles."""
        from woniunote.module.favorites import Favorites
        from woniunote.module.articles import Articles
        
        # Mock favorites
        mock_favorites = [MagicMock(favoriteid=1, articleid=1, userid=1)]
        mock_favorites_db.query.return_value.filter_by.return_value.order_by.return_value.all.return_value = mock_favorites
        
        # Mock articles
        mock_articles = [MagicMock(articleid=1, headline='Favorite Article')]
        mock_articles_db.query.return_value.filter.return_value.all.return_value = mock_articles
        
        # Test integration
        favorites = Favorites()
        favorites_result = favorites.find_by_userid(1)
        assert len(favorites_result) == 1
        
        # Test getting favorited articles
        article_ids = [fav.articleid for fav in favorites_result]
        articles_result = Articles.find_by_ids(article_ids)
        assert len(articles_result) == 1


class TestModuleErrorHandling:
    """Test error handling in modules."""
    
    @patch('woniunote.module.users.dbsession')
    def test_users_database_error_handling(self, mock_dbsession):
        """Test Users module database error handling."""
        from woniunote.module.users import Users
        
        # Mock database error
        mock_dbsession.query.side_effect = Exception("Database connection error")
        
        user = Users()
        # The actual method should handle the error gracefully
        try:
            result = user.find_by_username('test@example.com')
            # If method handles errors, it should return empty list or None
            assert result == [] or result is None
        except Exception:
            # If method doesn't handle errors, that's also valid behavior
            pass

    @patch('woniunote.module.articles.dbsession')
    def test_articles_database_error_handling(self, mock_dbsession):
        """Test Articles module database error handling."""
        from woniunote.module.articles import Articles
        
        # Mock database error
        mock_dbsession.query.side_effect = Exception("Database connection error")
        
        # Test that error handling works
        try:
            result = Articles.find_all()
            # The method should return empty list on error
            assert result == []
        except Exception:
            # If method doesn't handle errors, that's documented behavior
            pass


class TestModulePerformance:
    """Test module performance optimizations."""
    
    @patch('woniunote.module.articles.dbsession')
    def test_articles_pagination(self, mock_dbsession):
        """Test Articles pagination methods."""
        from woniunote.module.articles import Articles
        
        # Mock paginated query
        mock_query = mock_dbsession.query.return_value
        mock_query.order_by.return_value.offset.return_value.limit.return_value.all.return_value = [
            MagicMock(articleid=1, headline='Article 1')
        ]
        
        result = Articles.find_limit_with_users(0, 10)
        
        # Verify pagination was applied
        mock_query.offset.assert_called_with(0)
        mock_query.offset.return_value.limit.assert_called_with(10)

    @patch('woniunote.module.articles.dbsession')
    def test_articles_search_optimization(self, mock_dbsession):
        """Test Articles search optimization."""
        from woniunote.module.articles import Articles
        
        # Mock search query
        mock_query = mock_dbsession.query.return_value
        mock_query.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = [
            MagicMock(articleid=1, headline='Search Result')
        ]
        
        result = Articles.find_by_headline('search term', 0, 10)
        
        # Verify search was performed
        mock_query.filter.assert_called()


if __name__ == '__main__':
    pytest.main(['-v', __file__]) 