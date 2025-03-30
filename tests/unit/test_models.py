"""
WoniuNote Models Unit Tests

Tests all database models to ensure they function correctly.
"""
from datetime import datetime, timedelta
import sys
import os

# 添加项目根目录到Python路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# 使用绝对导入，避免相对导入带来的测试发现问题
from tests.test_helpers import (
    User, Article, Comment, Favorite, Credit, Category, Item, Card, CardCategory,
    create_test_user, create_test_article, create_test_comment, create_test_favorite,
    create_test_credit, create_test_category, create_test_item, create_test_card_category, create_test_card
)


class TestUserModel:
    """Tests for the User model"""
    
    def test_create_user(self, db_session):
        """Test creating a new user"""
        username = "testuser"
        password = "testpassword"
        nickname = "Test User"
        avatar = "testuser.jpg"
        qq = "123456789"
        role = "user"
        credit = 50
        
        user = User(
            username=username,
            password=password,
            nickname=nickname,
            avatar=avatar,
            qq=qq,
            role=role,
            credit=credit,
            createtime=datetime.now(),
            updatetime=datetime.now()
        )
        db_session.add(user)
        db_session.commit()
        
        # Fetch the user
        saved_user = db_session.query(User).filter_by(username=username).first()
        
        assert saved_user is not None
        assert saved_user.username == username
        assert saved_user.password == password
        assert saved_user.nickname == nickname
        assert saved_user.avatar == avatar
        assert saved_user.qq == qq
        assert saved_user.role == role
        assert saved_user.credit == credit
    
    def test_user_relationships(self, db_session):
        """Test user relationships with other models"""
        # Create user with related data
        user = create_test_user(db_session)
        article = create_test_article(db_session, user=user)
        comment = create_test_comment(db_session, user=user, article=article)
        favorite = create_test_favorite(db_session, user=user, article=article)
        
        # Fetch the user with their related data
        db_session.refresh(user)
        
        # Test relationships through queries
        user_articles = db_session.query(Article).filter_by(userid=user.userid).all()
        user_comments = db_session.query(Comment).filter_by(userid=user.userid).all()
        user_favorites = db_session.query(Favorite).filter_by(userid=user.userid).all()
        
        assert len(user_articles) > 0
        assert len(user_comments) > 0
        assert len(user_favorites) > 0
        
        # Verify the relationship data
        assert user_articles[0].userid == user.userid
        assert user_comments[0].userid == user.userid
        assert user_favorites[0].userid == user.userid


class TestArticleModel:
    """Tests for the Article model"""
    
    def test_create_article(self, db_session):
        """Test creating a new article"""
        user = create_test_user(db_session)
        
        headline = "Test Article"
        content = "This is a test article content."
        article_type = "blog"  
        thumbnail = "test.jpg"
        
        article = Article(
            userid=user.userid,
            type=article_type,
            title=headline,  
            content=content,
            thumbnail=thumbnail,
            credit=5,
            readcount=0,
            replycount=0,
            recommended=0,
            hidden=0,
            drafted=0,
            checked=1,
            createtime=datetime.now(),
            updatetime=datetime.now()
        )
        db_session.add(article)
        db_session.commit()
        
        # Fetch the article - 
        saved_article = db_session.query(Article).filter_by(title=headline).first()
        
        assert saved_article is not None
        assert saved_article.headline == headline  
        assert saved_article.title == headline     
        assert saved_article.content == content
        assert saved_article.type == article_type
        assert saved_article.thumbnail == thumbnail
        assert saved_article.userid == user.userid
    
    def test_article_relationships(self, db_session):
        """Test article relationships with other models"""
        # Create article with related data
        user = create_test_user(db_session)
        article = create_test_article(db_session, user=user)
        comment = create_test_comment(db_session, user=user, article=article)
        favorite = create_test_favorite(db_session, user=user, article=article)
        
        # Test relationships through queries
        article_comments = db_session.query(Comment).filter_by(articleid=article.articleid).all()
        article_favorites = db_session.query(Favorite).filter_by(articleid=article.articleid).all()
        
        assert len(article_comments) > 0
        assert len(article_favorites) > 0
        
        # Verify the relationship data
        assert article_comments[0].articleid == article.articleid
        assert article_favorites[0].articleid == article.articleid


class TestCommentModel:
    """Tests for the Comment model"""
    
    def test_create_comment(self, db_session):
        """Test creating a new comment"""
        user = create_test_user(db_session)
        article = create_test_article(db_session, user=user)
        
        content = "This is a test comment."
        ipaddr = "127.0.0.1"
        
        comment = Comment(
            userid=user.userid,
            articleid=article.articleid,
            content=content,
            ipaddr=ipaddr,
            replyid=0,
            agreecount=0,
            opposecount=0,
            hidden=0,
            createtime=datetime.now(),
            updatetime=datetime.now()
        )
        db_session.add(comment)
        db_session.commit()
        
        # Fetch the comment
        saved_comment = db_session.query(Comment).filter_by(
            userid=user.userid, 
            articleid=article.articleid
        ).first()
        
        assert saved_comment is not None
        assert saved_comment.content == content
        assert saved_comment.ipaddr == ipaddr
        assert saved_comment.userid == user.userid
        assert saved_comment.articleid == article.articleid
    
    def test_comment_reply(self, db_session):
        """Test comment reply functionality"""
        user = create_test_user(db_session)
        article = create_test_article(db_session, user=user)
        
        # Create parent comment
        parent_comment = Comment(
            userid=user.userid,
            articleid=article.articleid,
            content="Parent comment",
            ipaddr="127.0.0.1",
            replyid=0,
            agreecount=0,
            opposecount=0,
            hidden=0,
            createtime=datetime.now(),
            updatetime=datetime.now()
        )
        db_session.add(parent_comment)
        db_session.commit()
        
        # Create reply comment
        reply_comment = Comment(
            userid=user.userid,
            articleid=article.articleid,
            content="Reply comment",
            ipaddr="127.0.0.1",
            replyid=parent_comment.commentid,
            agreecount=0,
            opposecount=0,
            hidden=0,
            createtime=datetime.now(),
            updatetime=datetime.now()
        )
        db_session.add(reply_comment)
        db_session.commit()
        
        # Fetch the reply comment
        saved_reply = db_session.query(Comment).filter_by(replyid=parent_comment.commentid).first()
        
        assert saved_reply is not None
        assert saved_reply.replyid == parent_comment.commentid
        assert saved_reply.content == "Reply comment"


class TestFavoriteModel:
    """Tests for the Favorite model"""
    
    def test_create_favorite(self, db_session):
        """Test creating a new favorite"""
        user = create_test_user(db_session)
        article = create_test_article(db_session, user=user)
        
        favorite = Favorite(
            userid=user.userid,
            articleid=article.articleid,
            canceled=0,
            createtime=datetime.now(),
            updatetime=datetime.now()
        )
        db_session.add(favorite)
        db_session.commit()
        
        # Fetch the favorite
        saved_favorite = db_session.query(Favorite).filter_by(
            userid=user.userid, 
            articleid=article.articleid
        ).first()
        
        assert saved_favorite is not None
        assert saved_favorite.userid == user.userid
        assert saved_favorite.articleid == article.articleid
        assert saved_favorite.canceled == 0
    
    def test_favorite_cancel(self, db_session):
        """Test canceling a favorite"""
        user = create_test_user(db_session)
        article = create_test_article(db_session, user=user)
        
        # Create favorite
        favorite = Favorite(
            userid=user.userid,
            articleid=article.articleid,
            canceled=0,
            createtime=datetime.now(),
            updatetime=datetime.now()
        )
        db_session.add(favorite)
        db_session.commit()
        
        # Cancel favorite
        favorite.canceled = 1
        favorite.updatetime = datetime.now()
        db_session.commit()
        
        # Fetch the favorite
        saved_favorite = db_session.query(Favorite).filter_by(
            userid=user.userid, 
            articleid=article.articleid
        ).first()
        
        assert saved_favorite is not None
        assert saved_favorite.canceled == 1


class TestCreditModel:
    """Tests for the Credit model"""
    
    def test_create_credit(self, db_session):
        """Test creating a new credit record"""
        user = create_test_user(db_session)
        article = create_test_article(db_session, user=user)
        
        category = 1  # Assuming 1 is a valid category
        credit_amount = 10
        description = "Test credit"
        
        credit = Credit(
            userid=user.userid,
            category=category,
            target=article.articleid,
            credit=credit_amount,
            description=description,
            createtime=datetime.now()
        )
        db_session.add(credit)
        db_session.commit()
        
        # Fetch the credit record
        saved_credit = db_session.query(Credit).filter_by(
            userid=user.userid, 
            target=article.articleid
        ).first()
        
        assert saved_credit is not None
        assert saved_credit.userid == user.userid
        assert saved_credit.category == category
        assert saved_credit.target == article.articleid
        assert saved_credit.credit == credit_amount
        assert saved_credit.description == description


class TestCategoryAndItemModels:
    """Tests for the Category and Item models"""
    
    def test_create_category(self, db_session):
        """Test creating a new category"""
        name = "Test Category"
        
        category = Category(
            name=name,
            parent_id=None,
            createtime=datetime.now(),
            updatetime=datetime.now()
        )
        db_session.add(category)
        db_session.commit()
        
        # Fetch the category
        saved_category = db_session.query(Category).filter_by(name=name).first()
        
        assert saved_category is not None
        assert saved_category.name == name
        assert saved_category.parent_id is None
    
    def test_create_nested_categories(self, db_session):
        """Test creating nested categories"""
        parent_name = "Parent Category"
        child_name = "Child Category"
        
        # Create parent category
        parent = Category(
            name=parent_name,
            parent_id=None,
            createtime=datetime.now(),
            updatetime=datetime.now()
        )
        db_session.add(parent)
        db_session.commit()
        
        # Create child category
        child = Category(
            name=child_name,
            parent_id=parent.id,
            createtime=datetime.now(),
            updatetime=datetime.now()
        )
        db_session.add(child)
        db_session.commit()
        
        # Fetch the child category
        saved_child = db_session.query(Category).filter_by(name=child_name).first()
        
        assert saved_child is not None
        assert saved_child.name == child_name
        assert saved_child.parent_id == parent.id
    
    def test_create_item(self, db_session):
        """Test creating a new item"""
        category = create_test_category(db_session)
        name = "Test Item"
        
        item = Item(
            category_id=category.id,
            name=name,
            createtime=datetime.now(),
            updatetime=datetime.now()
        )
        db_session.add(item)
        db_session.commit()
        
        # Fetch the item
        saved_item = db_session.query(Item).filter_by(name=name).first()
        
        assert saved_item is not None
        assert saved_item.name == name
        assert saved_item.category_id == category.id
    
    def test_category_item_relationship(self, db_session):
        """Test relationship between category and items"""
        category = create_test_category(db_session)
        
        # Create multiple items for the category
        for i in range(3):
            item = Item(
                category_id=category.id,
                name=f"Test Item {i+1}",
                createtime=datetime.now(),
                updatetime=datetime.now()
            )
            db_session.add(item)
        db_session.commit()
        
        # Fetch items for the category
        category_items = db_session.query(Item).filter_by(category_id=category.id).all()
        
        assert len(category_items) == 3
        for item in category_items:
            assert item.category_id == category.id


class TestCardModels:
    """Tests for the Card and CardCategory models"""
    
    def test_create_card_category(self, db_session):
        """Test creating a new card category"""
        name = "Test Card Category"
        
        card_category = CardCategory(
            name=name,
            createtime=datetime.now(),
            updatetime=datetime.now()
        )
        db_session.add(card_category)
        db_session.commit()
        
        # Fetch the card category
        saved_category = db_session.query(CardCategory).filter_by(name=name).first()
        
        assert saved_category is not None
        assert saved_category.name == name
    
    def test_create_card(self, db_session):
        """Test creating a new card with direct SQL queries rather than ORM relationships"""
        # 首先创建一个卡片分类
        card_category = CardCategory(name="Test Category")
        db_session.add(card_category)
        db_session.flush()  # 获取ID但不提交事务
        
        # 创建卡片时只使用基本的字段，避免复杂的关系
        headline = "Test Card"
        content = "This is a test card content."
        now = datetime.now()
        
        # 使用字符串类型的 type (根据数据库实际结构)
        card = Card(
            type='1',  # 确保使用字符串类型
            headline=headline,
            content=content,
            cardcategory_id=card_category.id,
            begintime=now,
            endtime=now + timedelta(days=3),
            createtime=now,
            updatetime=now
        )
        
        db_session.add(card)
        db_session.commit()
        
        # 直接使用SQL查询获取卡片，而不是通过关系
        saved_card = db_session.query(Card).filter_by(headline=headline).first()
        
        assert saved_card is not None
        assert saved_card.headline == headline
        assert saved_card.content == content
        assert saved_card.type == '1'  # 字符串类型
        assert saved_card.cardcategory_id == card_category.id
    
    def test_card_status_update(self, db_session):
        """Test updating card status"""
        card_category = create_test_card_category(db_session)
        
        # Create card
        now = datetime.now()
        card = Card(
            type='1',  # 使用字符串类型
            headline="Test Card for Status Update",
            content="This is a test card content.",
            cardcategory_id=card_category.id,
            begintime=now,
            endtime=now + timedelta(days=3),
            createtime=now,
            updatetime=now
        )
        db_session.add(card)
        db_session.commit()
        
        # Update card status to done
        card.donetime = datetime.now()
        card.updatetime = datetime.now()
        db_session.commit()
        
        # Fetch the card
        updated_card = db_session.query(Card).filter_by(id=card.id).first()
        
        assert updated_card is not None
        assert updated_card.donetime is not None
    
    def test_card_category_relationship(self, db_session):
        """Test relationship between card category and cards"""
        card_category = create_test_card_category(db_session)
        
        # Create multiple cards for the category
        now = datetime.now()
        for i in range(3):
            card = Card(
                type='1',  # 使用字符串类型
                headline=f"Test Card {i+1}",
                content=f"This is test card {i+1} content.",
                cardcategory_id=card_category.id,
                begintime=now,
                endtime=now + timedelta(days=3),
                createtime=now,
                updatetime=now
            )
            db_session.add(card)
        db_session.commit()
        
        # Fetch cards for the category
        category_cards = db_session.query(Card).filter_by(cardcategory_id=card_category.id).all()
        
        assert len(category_cards) == 3
        for card in category_cards:
            assert card.cardcategory_id == card_category.id


if __name__ == "__main__":
    pass