"""
WoniuNote Test Helpers

Utility functions and classes to assist with testing
"""
import random
import string
from datetime import datetime, timedelta

import hashlib
import os
import sys
import yaml
from datetime import datetime

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey

# 获取项目根目录和测试配置文件的正确路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEST_CONFIG_PATH = os.path.join(BASE_DIR, 'tests', 'test_config.yaml')

# 确保项目根目录在Python路径中
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# 读取配置
with open(TEST_CONFIG_PATH, 'r', encoding='utf-8') as f:
    config_data = yaml.load(f.read(), Loader=yaml.FullLoader)

# 创建应用和数据库实例 - 避免循环导入
app = Flask(__name__, template_folder='template', static_url_path='/', static_folder='resource')
app.config['SECRET_KEY'] = os.urandom(24)

# 设置数据库URI
db_uri = config_data['database']["SQLALCHEMY_DATABASE_URI"]
app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_POOL_SIZE'] = 100

# 实例化db对象
db = SQLAlchemy(app)

# 为向后兼容保留的变量
dbsession = db.session
DBase = db.Model

# 基础模型类
class BaseModel(db.Model):
    """所有模型的基类，提供公共字段和方法"""
    __abstract__ = True

    # 公共时间戳字段
    createtime = Column(DateTime, default=datetime.now, nullable=False)
    updatetime = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)

    def to_dict(self):
        """将模型转换为字典"""
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class User(BaseModel):
    """用户模型，存储用户账号和个人信息"""
    __tablename__ = "users"

    userid = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    username = Column(String(50), nullable=False, index=True)
    password = Column(String(32), nullable=False)
    nickname = Column(String(30))
    avatar = Column(String(20))
    qq = Column(String(15))
    role = Column(String(10), nullable=False)
    credit = Column(Integer, default=50)

    # 定义关系
    articles = relationship("Article", back_populates="user", lazy="dynamic")
    comments = relationship("Comment", back_populates="user", lazy="dynamic")
    favorites = relationship("Favorite", back_populates="user", lazy="dynamic")
    credits = relationship("Credit", back_populates="user", lazy="dynamic")
    cards = relationship("Card", back_populates="user", lazy="dynamic")

    def __repr__(self):
        return f"<User(userid={self.userid}, username='{self.username}', role='{self.role}')>"


class Article(BaseModel):
    """文章模型，存储文章内容和元数据"""
    __tablename__ = "article"

    articleid = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    userid = Column(Integer, ForeignKey("users.userid"), nullable=False)
    # 修正：type应为字符串类型，而非整数
    type = Column(String(10), nullable=False)
    # 使用数据库的实际字段名 title
    title = Column(String(100), nullable=False)
    content = Column(Text(16777216))
    thumbnail = Column(String(30))
    credit = Column(Integer, default=0)
    readcount = Column(Integer, default=0)
    replycount = Column(Integer, default=0)
    recommended = Column(Integer, default=0)
    hidden = Column(Integer, default=0)
    drafted = Column(Integer, default=0)
    checked = Column(Integer, default=1)
    category = Column(String(20), default='')  # 添加可能缺失的字段
    tag = Column(String(50), default='')       # 添加可能缺失的字段
    
    # 定义关系
    user = relationship("User", back_populates="articles")
    comments = relationship("Comment", back_populates="article", cascade="all, delete-orphan")
    favorites = relationship("Favorite", back_populates="article", cascade="all, delete-orphan")

    # 为应用层提供headline属性的兼容性
    @property
    def headline(self):
        """向后兼容：返回文章标题"""
        return self.title

    @headline.setter
    def headline(self, value):
        """向后兼容：设置文章标题"""
        self.title = value

    def __repr__(self):
        return f"<Article(articleid={self.articleid}, title='{self.title[:20]}...', type='{self.type}')>"


class Comment(BaseModel):
    """评论模型，存储用户对文章的评论"""
    __tablename__ = "comment"

    commentid = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    userid = Column(Integer, ForeignKey("users.userid"), nullable=False)
    articleid = Column(Integer, ForeignKey("article.articleid"), nullable=False)
    content = Column(Text(65536), nullable=False)
    ipaddr = Column(String(30))
    replyid = Column(Integer)
    agreecount = Column(Integer, default=0)
    opposecount = Column(Integer, default=0)
    hidden = Column(Integer, default=0)

    # 定义关系
    user = relationship("User", back_populates="comments")
    article = relationship("Article", back_populates="comments")

    def __repr__(self):
        return f"<Comment(commentid={self.commentid}, articleid={self.articleid}, content='{self.content[:20]}...')>"


class Favorite(BaseModel):
    """收藏模型，存储用户对文章的收藏记录"""
    __tablename__ = "favorite"

    favoriteid = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    userid = Column(Integer, ForeignKey("users.userid"), nullable=False)
    articleid = Column(Integer, ForeignKey("article.articleid"), nullable=False)
    canceled = Column(Integer, default=0)

    # 定义关系
    user = relationship("User", back_populates="favorites")
    article = relationship("Article", back_populates="favorites")

    def __repr__(self):
        return f"<Favorite(favoriteid={self.favoriteid}, userid={self.userid}, articleid={self.articleid})>"


class Credit(BaseModel):
    """积分模型，存储用户积分变动记录"""
    __tablename__ = "credit"

    creditid = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    userid = Column(Integer, ForeignKey("users.userid"), nullable=False)
    category = Column(String(10))
    target = Column(Integer)
    credit = Column(Integer)

    # 定义关系
    user = relationship("User", back_populates="credits")

    def __repr__(self):
        return f"<Credit(creditid={self.creditid}, userid={self.userid}, category='{self.category}', credit={self.credit})>"


class Category(BaseModel):
    """分类模型，提供条目分类"""
    __tablename__ = "category"

    id = Column(Integer, primary_key=True)
    name = Column(String(64))
    parent_id = Column(Integer, default=None)

    # 定义关系
    items = relationship('Item', back_populates='category', cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Category(id={self.id}, name='{self.name}')>"


class Item(BaseModel):
    """条目模型，与分类相关联"""
    __tablename__ = "item"

    id = Column(Integer, primary_key=True)
    body = Column(Text)
    category_id = Column(Integer, ForeignKey('category.id'), default=1)

    # 定义关系
    category = relationship('Category', back_populates='items')

    def __repr__(self):
        return f"<Item(id={self.id}, category_id={self.category_id})>"


class CardCategory(BaseModel):
    """卡片分类模型"""
    __tablename__ = "cardcategory"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(64))

    def __repr__(self):
        return f"<CardCategory(id={self.id}, name='{self.name}')>"


class Card(BaseModel):
    """卡片模型，用于用户卡片管理"""
    __tablename__ = "card"

    id = Column(Integer, primary_key=True, autoincrement=True)
    type = Column(String(10), default='1')  # 修改为字符串类型，与数据库匹配
    headline = Column(Text)
    content = Column(Text)
    createtime = Column(DateTime, default=datetime.now)
    updatetime = Column(DateTime, default=datetime.now)
    donetime = Column(DateTime, nullable=True)
    usedtime = Column(Integer, default=0)
    begintime = Column(DateTime, nullable=True)
    endtime = Column(DateTime, nullable=True)
    cardcategory_id = Column(Integer)  # 简单使用整数字段，不设置外键约束

    # 兼容性属性
    @property
    def done(self):
        """向后兼容：检查卡片是否完成"""
        return 1 if self.donetime is not None else 0

    @done.setter
    def done(self, value):
        """向后兼容：设置卡片完成状态"""
        self.donetime = datetime.now() if value else None

    @property
    def priority(self):
        """向后兼容：返回卡片优先级（默认使用type字段）"""
        return int(self.type) if self.type.isdigit() else 1

    @priority.setter
    def priority(self, value):
        """向后兼容：设置卡片优先级"""
        self.type = str(value)  # 确保存储为字符串

    @property
    def userid(self):
        """向后兼容：尝试获取用户ID"""
        # 由于数据库中实际没有userid字段，我们返回一个默认值
        return 1

    @userid.setter
    def userid(self, value):
        """向后兼容：忽略用户ID的设置"""
        # 实际数据库中没有此字段，所以我们只是忽略这个操作
        pass

    def __repr__(self):
        return f"<Card(id={self.id}, headline='{self.headline[:20]}...', type={self.type})>"


# ======== 辅助函数 ========

def random_string(length=10):
    """生成指定长度的随机字符串"""
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for _ in range(length))

def random_email():
    """生成随机Email地址"""
    return f"{random_string(8)}@{random_string(6)}.com"

def random_qq():
    """生成随机QQ号码"""
    return ''.join(random.choice(string.digits) for _ in range(9))

def random_date(start_date=None, end_date=None):
    """生成两个日期之间的随机日期"""
    if start_date is None:
        start_date = datetime.now() - timedelta(days=365)
    if end_date is None:
        end_date = datetime.now()
    
    time_between_dates = end_date - start_date
    days_between_dates = time_between_dates.days
    random_number_of_days = random.randrange(days_between_dates)
    return start_date + timedelta(days=random_number_of_days)


class ResponseParser:
    """辅助类，用于解析和验证Flask测试客户端的响应"""
    
    @staticmethod
    def parse_json_response(response):
        """
        解析JSON响应并返回结果
        
        Args:
            response: Flask测试客户端的响应对象
        
        Returns:
            dict: 解析后的JSON数据
        """
        try:
            return response.json
        except Exception as e:
            print(f"解析JSON响应失败: {e}")
            return None
    
    @staticmethod
    def check_success_response(response, check_data=True):
        """
        检查API响应是否成功
        
        Args:
            response: Flask测试客户端的响应对象
            check_data: 是否检查data字段存在
        
        Returns:
            tuple: (是否成功, 响应数据, 错误消息)
        """
        json_data = ResponseParser.parse_json_response(response)
        if not json_data:
            return False, None, "返回数据不是有效的JSON"
        
        if "code" not in json_data:
            return False, None, "返回数据缺少code字段"
        
        if json_data["code"] != 0:
            return False, None, json_data.get("message", "未知错误")
        
        if check_data and "data" not in json_data:
            return False, None, "返回数据缺少data字段"
        
        return True, json_data.get("data"), None
    
    @staticmethod
    def extract_message(response):
        """从响应中提取消息"""
        json_data = ResponseParser.parse_json_response(response)
        if not json_data:
            return None
        
        return json_data.get("message")


# ======== 测试数据创建函数 ========

def create_test_user(session=None, username=None, password=None, role='user', **kwargs):
    """创建测试用户"""
    session = session or dbsession
    
    defaults = {
        'username': username or random_string(8),
        'password': password or random_string(8),
        'nickname': kwargs.get('nickname', f"Test User {random_string(4)}"),
        'avatar': kwargs.get('avatar', f"{random_string(8)}.jpg"),
        'qq': kwargs.get('qq', random_qq()),
        'role': role,
        'credit': kwargs.get('credit', 50),
        'createtime': kwargs.get('createtime', datetime.now()),
        'updatetime': kwargs.get('updatetime', datetime.now())
    }
    
    # 创建用户实例
    user = User(**defaults)
    
    if session:
        session.add(user)
        session.commit()
    
    return user

def create_test_article(session=None, user=None, type_id=None, headline=None, **kwargs):
    """创建测试文章
    注意：type必须是字符串类型，而非整数
    """
    session = session or dbsession
    
    # 如果没有提供用户，创建一个
    if user is None:
        user = create_test_user(session)
    
    defaults = {
        'userid': getattr(user, 'userid', 1),
        'type': str(type_id or 'blog'),  # 确保type是字符串类型
        'title': headline or f"Test Article {random_string(8)}",  # 使用title而非headline
        'content': kwargs.get('content', f"Test content {random_string(50)}"),
        'thumbnail': kwargs.get('thumbnail', f"{random_string(8)}.jpg"),
        'credit': kwargs.get('credit', 0),
        'readcount': kwargs.get('readcount', 0),
        'replycount': kwargs.get('replycount', 0),
        'recommended': kwargs.get('recommended', 0),
        'hidden': kwargs.get('hidden', 0),
        'drafted': kwargs.get('drafted', 0),
        'checked': kwargs.get('checked', 1),
        'createtime': kwargs.get('createtime', datetime.now()),
        'updatetime': kwargs.get('updatetime', datetime.now())
    }
    
    # 创建文章实例
    article = Article(**defaults)
    
    if session:
        session.add(article)
        session.commit()
    
    return article

def create_test_comment(session=None, user=None, article=None, **kwargs):
    """创建测试评论"""
    session = session or dbsession
    
    # 如果没有提供用户或文章，创建它们
    if user is None:
        user = create_test_user(session)
    
    if article is None:
        article = create_test_article(session, user)
    
    defaults = {
        'userid': getattr(user, 'userid', 1),
        'articleid': getattr(article, 'articleid', 1),
        'content': kwargs.get('content', f"Test comment {random_string(20)}"),
        'ipaddr': kwargs.get('ipaddr', f"192.168.1.{random.randint(1, 254)}"),
        'replyid': kwargs.get('replyid', 0),
        'agreecount': kwargs.get('agreecount', 0),
        'opposecount': kwargs.get('opposecount', 0),
        'hidden': kwargs.get('hidden', 0),
        'createtime': kwargs.get('createtime', datetime.now()),
        'updatetime': kwargs.get('updatetime', datetime.now())
    }
    
    # 创建评论实例
    comment = Comment(**defaults)
    
    if session:
        session.add(comment)
        session.commit()
    
    return comment

def create_test_favorite(session=None, user=None, article=None, **kwargs):
    """创建测试收藏"""
    session = session or dbsession
    
    # 如果没有提供用户或文章，创建它们
    if user is None:
        user = create_test_user(session)
    
    if article is None:
        article = create_test_article(session, user)
    
    defaults = {
        'userid': getattr(user, 'userid', 1),
        'articleid': getattr(article, 'articleid', 1),
        'canceled': kwargs.get('canceled', 0),
        'createtime': kwargs.get('createtime', datetime.now()),
        'updatetime': kwargs.get('updatetime', datetime.now())
    }
    
    # 创建收藏实例
    favorite = Favorite(**defaults)
    
    if session:
        session.add(favorite)
        session.commit()
    
    return favorite

def create_test_credit(session=None, user=None, **kwargs):
    """创建测试积分记录"""
    session = session or dbsession
    
    # 如果没有提供用户，创建一个
    if user is None:
        user = create_test_user(session)
    
    defaults = {
        'userid': getattr(user, 'userid', 1),
        'category': kwargs.get('category', random.choice(['article', 'comment', 'login'])),
        'target': kwargs.get('target', random.randint(1, 1000)),
        'credit': kwargs.get('credit', random.randint(1, 10)),
        'createtime': kwargs.get('createtime', datetime.now()),
        'updatetime': kwargs.get('updatetime', datetime.now())
    }
    
    # 创建积分实例
    credit = Credit(**defaults)
    
    if session:
        session.add(credit)
        session.commit()
    
    return credit

def create_test_category(session=None, parent=None, **kwargs):
    """创建测试分类"""
    session = session or dbsession
    
    defaults = {
        'name': kwargs.get('name', f"Category {random_string(8)}"),
        'parent_id': getattr(parent, 'id', None) if parent else kwargs.get('parent_id', None),
        'createtime': kwargs.get('createtime', datetime.now()),
        'updatetime': kwargs.get('updatetime', datetime.now())
    }
    
    # 创建分类实例
    category = Category(**defaults)
    
    if session:
        session.add(category)
        session.commit()
    
    return category

def create_test_item(session=None, category=None, **kwargs):
    """创建测试条目"""
    session = session or dbsession
    
    # 如果没有提供分类，创建一个
    if category is None:
        category = create_test_category(session)
    
    defaults = {
        'category_id': getattr(category, 'id', 1),
        'name': kwargs.get('name', f"Item {random_string(8)}"),
        'createtime': kwargs.get('createtime', datetime.now()),
        'updatetime': kwargs.get('updatetime', datetime.now())
    }
    
    # 创建条目实例
    item = Item(**defaults)
    
    if session:
        session.add(item)
        session.commit()
    
    return item

def create_test_card_category(session=None, **kwargs):
    """创建测试卡片分类"""
    session = session or dbsession
    
    defaults = {
        'name': kwargs.get('name', f"Card Category {random_string(8)}"),
        'createtime': kwargs.get('createtime', datetime.now()),
        'updatetime': kwargs.get('updatetime', datetime.now())
    }
    
    # 创建卡片分类实例
    card_category = CardCategory(**defaults)
    
    if session:
        session.add(card_category)
        session.commit()
    
    return card_category

def create_test_card(session=None, card_category=None, **kwargs):
    """创建测试卡片"""
    session = session or dbsession
    
    # 如果没有提供卡片分类，创建一个
    if card_category is None:
        card_category = create_test_card_category(session)
    
    defaults = {
        'type': str(kwargs.get('type', '1')),  # 确保存储为字符串
        'headline': kwargs.get('headline', f"Card {random_string(8)}"),
        'content': kwargs.get('content', f"Card content {random_string(20)}"),
        'cardcategory_id': getattr(card_category, 'id', 1),
        'donetime': kwargs.get('donetime', None),
        'usedtime': kwargs.get('usedtime', 0),
        'begintime': kwargs.get('begintime', datetime.now()),
        'endtime': kwargs.get('endtime', datetime.now() + timedelta(days=7)),
        'createtime': kwargs.get('createtime', datetime.now()),
        'updatetime': kwargs.get('updatetime', datetime.now())
    }
    
    # 创建卡片实例
    card = Card(**defaults)
    
    if session:
        session.add(card)
        session.commit()
    
    return card
