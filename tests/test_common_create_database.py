# tests/test_common_create_database.py
import pytest
import datetime
import hashlib
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from woniunote.common.create_database import (
    User, Article, Comment, Favorite, Credit,
    Item, Category, Card, CardCategory, db
)
from woniunote.common.utils import read_config
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

def test_create_database():
    @pytest.fixture(scope="session")
    def app():
        """测试 Flask app 配置"""
        app = Flask(__name__)
        app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://testuser:testpass@localhost/test_woniunote'
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        db.init_app(app)
        return app


    @pytest.fixture(scope="session")
    def client(app):
        """测试客户端"""
        return app.test_client()


    @pytest.fixture(scope="session")
    def init_db(app):
        """初始化数据库"""
        # 在创建表之前，确保删除现有的表
        with app.app_context():
            try:
                db.drop_all()  # 删除现有的表
                db.create_all()  # 创建新表
            except Exception as e:
                print(f"Error during table creation: {e}")

        # 之后执行测试代码
        yield db

        # 清理数据库，测试完成后删除所有表
        with app.app_context():
            try:
                db.session.remove()  # 清理会话
                db.drop_all()  # 删除所有表
            except Exception as e:
                print(f"Error during cleanup: {e}")


    @pytest.mark.run(order=1)
    def test_user_creation(init_db):
        """测试用户的创建"""
        user = User(username='testuser', password='password', role='admin', nickname='Test User')
        db.session.add(user)
        db.session.commit()

        # 验证用户是否被添加
        fetched_user = User.query.filter_by(username='testuser').first()
        assert fetched_user is not None
        assert fetched_user.username == 'testuser'
        assert fetched_user.role == 'admin'

    @pytest.mark.run(order=2)
    def test_article_creation(init_db):
        """测试文章的创建"""
        user = User(username='testuser', password='password', role='admin', nickname='Test User')
        db.session.add(user)
        db.session.commit()

        article = Article(userid=user.userid, type=1, headline="Test Article", content="This is a test article.")
        db.session.add(article)
        db.session.commit()

        # 验证文章是否被添加
        fetched_article = Article.query.filter_by(headline="Test Article").first()
        assert fetched_article is not None
        assert fetched_article.headline == "Test Article"
        assert fetched_article.content == "This is a test article."

    @pytest.mark.run(order=3)
    def test_comment_creation(init_db):
        """测试评论的创建"""
        user = User(username='testuser', password='password', role='admin', nickname='Test User')
        db.session.add(user)
        db.session.commit()

        article = Article(userid=user.userid, type=1, headline="Test Article", content="This is a test article.")
        db.session.add(article)
        db.session.commit()

        comment = Comment(userid=user.userid, articleid=article.articleid, content="This is a comment.")
        db.session.add(comment)
        db.session.commit()

        # 验证评论是否被添加
        fetched_comment = Comment.query.filter_by(content="This is a comment.").first()
        assert fetched_comment is not None
        assert fetched_comment.content == "This is a comment."

    @pytest.mark.run(order=4)
    def test_favorite_creation(init_db):
        """测试收藏的创建"""
        user = User(username='testuser', password='password', role='admin', nickname='Test User')
        db.session.add(user)
        db.session.commit()

        article = Article(userid=user.userid, type=1, headline="Test Article", content="This is a test article.")
        db.session.add(article)
        db.session.commit()

        favorite = Favorite(userid=user.userid, articleid=article.articleid)
        db.session.add(favorite)
        db.session.commit()

        # 验证收藏是否被添加
        fetched_favorite = Favorite.query.filter_by(userid=user.userid, articleid=article.articleid).first()
        assert fetched_favorite is not None
        assert fetched_favorite.userid == user.userid
        assert fetched_favorite.articleid == article.articleid

    @pytest.mark.run(order=5)
    def test_credit_creation(init_db):
        """测试信用记录的创建"""
        user = User(username='testuser', password='password', role='admin', nickname='Test User')
        db.session.add(user)
        db.session.commit()

        credit = Credit(userid=user.userid, category="bonus", target=10, credit=100)
        db.session.add(credit)
        db.session.commit()

        # 验证信用记录是否被添加
        fetched_credit = Credit.query.filter_by(userid=user.userid, category="bonus").first()
        assert fetched_credit is not None
        assert fetched_credit.credit == 100
        assert fetched_credit.target == 10

    @pytest.mark.run(order=6)
    def test_category_creation(init_db):
        """测试分类的创建"""
        category = Category(name="Technology")
        db.session.add(category)
        db.session.commit()

        # 验证分类是否被添加
        fetched_category = Category.query.filter_by(name="Technology").first()
        assert fetched_category is not None
        assert fetched_category.name == "Technology"
