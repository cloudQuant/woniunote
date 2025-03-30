"""
WoniuNote Card API Tests

Tests for card-related API endpoints including creating, listing, updating, and deleting cards,
as well as managing card categories.
"""
import pytest
from flask import session
from ..test_helpers import (
    User, Card, CardCategory, random_string, create_test_user, create_test_card, create_test_card_category
)


class TestCardCategories:
    """Tests for card category functionality"""
    
    def test_card_category_requires_login(self, test_client):
        """Test that card category operations require login"""
        # Ensure logged out
        test_client.get('/user/logout', follow_redirects=True)
        
        # Try to access card category list
        response = test_client.get('/card/category', follow_redirects=True)
        
        assert response.status_code == 200
        assert '用户登录' in response.get_data(as_text=True)
    
    def test_card_category_list(self, authenticated_client, db_session, test_app):
        """Test card category list displays correctly"""
        # Create some card categories
        with test_app.app_context():
            # Get user ID from session
            with authenticated_client.session_transaction() as sess:
                userid = sess.get('userid')
            
            # Create unique card categories
            categories = []
            for i in range(3):
                category_name = f"Test Category {i} {random_string(8)}"
                category = create_test_card_category(db_session, name=category_name)
                categories.append(category)
        
        # Access card category list
        response = authenticated_client.get('/card/category')
        
        assert response.status_code == 200
        assert '卡片分类' in response.get_data(as_text=True)
        
        # Check if all category names are displayed
        response_text = response.get_data(as_text=True)
        for category in categories:
            assert category.name in response_text
    
    def test_create_card_category(self, authenticated_client):
        """Test creating a new card category"""
        # Generate a unique category name
        category_name = f"New Category {random_string(10)}"
        
        # Create the category
        response = authenticated_client.post('/card/category/create', data={
            'name': category_name
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert '分类添加成功' in response.get_data(as_text=True)
        
        # Check if category appears in the list
        response = authenticated_client.get('/card/category')
        assert category_name in response.get_data(as_text=True)
    
    def test_create_duplicate_category(self, authenticated_client, db_session, test_app):
        """Test creating a category with a duplicate name"""
        # Create a card category
        with test_app.app_context():
            category_name = f"Duplicate Category {random_string(8)}"
            category = create_test_card_category(db_session, name=category_name)
        
        # Try to create a category with the same name
        response = authenticated_client.post('/card/category/create', data={
            'name': category_name
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert '分类名称已存在' in response.get_data(as_text=True)
    
    def test_rename_card_category(self, authenticated_client, db_session, test_app):
        """Test renaming a card category"""
        # Create a card category
        with test_app.app_context():
            original_name = f"Original Category {random_string(8)}"
            category = create_test_card_category(db_session, name=original_name)
        
        # Rename the category
        new_name = f"Renamed Category {random_string(8)}"
        response = authenticated_client.post(f'/card/category/rename/{category.id}', data={
            'name': new_name
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert '分类已重命名' in response.get_data(as_text=True)
        
        # Check if the category was renamed in the list
        response = authenticated_client.get('/card/category')
        response_text = response.get_data(as_text=True)
        assert new_name in response_text
        assert original_name not in response_text
    
    def test_delete_card_category(self, authenticated_client, db_session, test_app):
        """Test deleting a card category"""
        # Create a card category
        with test_app.app_context():
            category_name = f"Delete Category {random_string(8)}"
            category = create_test_card_category(db_session, name=category_name)
        
        # Delete the category
        response = authenticated_client.get(f'/card/category/delete/{category.id}', follow_redirects=True)
        
        assert response.status_code == 200
        assert '分类已删除' in response.get_data(as_text=True)
        
        # Check if the category was removed from the list
        response = authenticated_client.get('/card/category')
        assert category_name not in response.get_data(as_text=True)


class TestCardOperations:
    """Tests for card operations functionality"""
    
    def test_card_list_requires_login(self, test_client):
        """Test that card list requires login"""
        # Ensure logged out
        test_client.get('/user/logout', follow_redirects=True)
        
        # Try to access card list
        response = test_client.get('/card/list', follow_redirects=True)
        
        assert response.status_code == 200
        assert '用户登录' in response.get_data(as_text=True)
    
    def test_card_list_by_category(self, authenticated_client, db_session, test_app):
        """Test card list displays correctly for a specific category"""
        # Create a card category and cards
        with test_app.app_context():
            # Get user ID from session
            with authenticated_client.session_transaction() as sess:
                userid = sess.get('userid')
            
            # Ensure we have a user object
            user = db_session.query(User).filter_by(userid=userid).first()
            if not user:
                user = create_test_user(db_session)
            
            category = create_test_card_category(db_session, name=f"Card List Category {random_string(8)}")
            cards = []
            for i in range(3):
                card = create_test_card(
                    db_session, 
                    user=user, 
                    card_category=category,
                    headline=f"Card {i} in {category.name} {random_string(8)}"
                )
                cards.append(card)
        
        # Access card list for the category
        response = authenticated_client.get(f'/card/list/{category.id}')
        
        assert response.status_code == 200
        assert category.name in response.get_data(as_text=True)
        
        # Check if all card headlines are displayed
        response_text = response.get_data(as_text=True)
        for card in cards:
            assert card.headline in response_text
    
    def test_create_card(self, authenticated_client, db_session, test_app):
        """Test creating a new card"""
        # Create a card category
        with test_app.app_context():
            category = create_test_card_category(db_session, name=f"New Card Category {random_string(8)}")
        
        # Create a card
        headline = f"New Card {random_string(10)}"
        content = f"Card content {random_string(30)}"
        priority = "3"
        
        response = authenticated_client.post('/card/create', data={
            'categoryid': category.id,
            'headline': headline,
            'content': content,
            'priority': priority
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert '卡片添加成功' in response.get_data(as_text=True)
        
        # Check if card appears in the category list
        response = authenticated_client.get(f'/card/list/{category.id}')
        assert headline in response.get_data(as_text=True)
    
    def test_create_card_with_empty_fields(self, authenticated_client, db_session, test_app):
        """Test creating a card with empty required fields"""
        # Create a card category
        with test_app.app_context():
            category = create_test_card_category(db_session, name=f"Empty Card Category {random_string(8)}")
        
        # Try to create a card with empty headline
        response = authenticated_client.post('/card/create', data={
            'categoryid': category.id,
            'headline': '',
            'content': 'Some content',
            'priority': '3'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert '标题不能为空' in response.get_data(as_text=True)
    
    def test_update_card(self, authenticated_client, db_session, test_app):
        """Test updating a card"""
        # Create a card
        with test_app.app_context():
            # Get user ID from session
            with authenticated_client.session_transaction() as sess:
                userid = sess.get('userid')
            
            # Ensure we have a user object
            user = db_session.query(User).filter_by(userid=userid).first()
            if not user:
                user = create_test_user(db_session)
            
            category = create_test_card_category(db_session)
            card = create_test_card(db_session, user=user, card_category=category)
        
        # Update the card
        new_headline = f"Updated Card {random_string(10)}"
        new_content = f"Updated content {random_string(30)}"
        new_priority = "5"
        
        response = authenticated_client.post(f'/card/edit/{card.id}', data={
            'categoryid': category.id,
            'headline': new_headline,
            'content': new_content,
            'priority': new_priority
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert '卡片已更新' in response.get_data(as_text=True)
        
        # Check if the card was updated
        updated_card = db_session.query(Card).filter_by(id=card.id).first()
        assert updated_card.headline == new_headline
        assert updated_card.content == new_content
        assert updated_card.priority == int(new_priority)
    
    def test_move_card_to_different_category(self, authenticated_client, db_session, test_app):
        """Test moving a card to a different category"""
        # Create categories and a card
        with test_app.app_context():
            # Get user ID from session
            with authenticated_client.session_transaction() as sess:
                userid = sess.get('userid')
            
            # Ensure we have a user object
            user = db_session.query(User).filter_by(userid=userid).first()
            if not user:
                user = create_test_user(db_session)
            
            source_category = create_test_card_category(db_session, name=f"Source Category {random_string(8)}")
            target_category = create_test_card_category(db_session, name=f"Target Category {random_string(8)}")
            card = create_test_card(db_session, user=user, card_category=source_category)
        
        # Move the card to the target category
        response = authenticated_client.post(f'/card/edit/{card.id}', data={
            'categoryid': target_category.id,
            'headline': card.headline,
            'content': card.content,
            'priority': card.priority
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert '卡片已更新' in response.get_data(as_text=True)
        
        # Check if the card was moved
        moved_card = db_session.query(Card).filter_by(id=card.id).first()
        assert moved_card.cardcategory_id == target_category.id
    
    def test_mark_card_as_done(self, authenticated_client, db_session, test_app):
        """Test marking a card as done"""
        # Create a card
        with test_app.app_context():
            # Get user ID from session
            with authenticated_client.session_transaction() as sess:
                userid = sess.get('userid')
            
            # Ensure we have a user object
            user = db_session.query(User).filter_by(userid=userid).first()
            if not user:
                user = create_test_user(db_session)
            
            category = create_test_card_category(db_session)
            card = create_test_card(db_session, user=user, card_category=category, done=0)
        
        # Mark the card as done
        response = authenticated_client.get(f'/card/done/{card.id}', follow_redirects=True)
        
        assert response.status_code == 200
        assert '状态已更新' in response.get_data(as_text=True)
        
        # Check if the card was marked as done
        updated_card = db_session.query(Card).filter_by(id=card.id).first()
        assert updated_card.done == 1
    
    def test_delete_card(self, authenticated_client, db_session, test_app):
        """Test deleting a card"""
        # Create a card
        with test_app.app_context():
            # Get user ID from session
            with authenticated_client.session_transaction() as sess:
                userid = sess.get('userid')
            
            # Ensure we have a user object
            user = db_session.query(User).filter_by(userid=userid).first()
            if not user:
                user = create_test_user(db_session)
            
            category = create_test_card_category(db_session)
            card = create_test_card(db_session, user=user, card_category=category)
        
        # Delete the card
        response = authenticated_client.get(f'/card/delete/{card.id}', follow_redirects=True)
        
        assert response.status_code == 200
        assert '卡片已删除' in response.get_data(as_text=True)
        
        # Check if the card was deleted
        deleted_card = db_session.query(Card).filter_by(id=card.id).first()
        assert deleted_card is None
