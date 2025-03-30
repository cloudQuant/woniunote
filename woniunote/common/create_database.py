#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WoniuNote 数据库模型定义

定义应用程序使用的所有数据库模型和它们之间的关系
"""
import hashlib
import os
import yaml
from datetime import datetime

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey

from .utils import get_package_path, read_config

# 读取配置
config_data = read_config()

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
    
    id = Column(Integer, primary_key=True)
    name = Column(String(64))
    
    # 定义关系
    cards = relationship('Card', back_populates='cardcategory', cascade="all, delete-orphan")

    def __repr__(self):
        return f"<CardCategory(id={self.id}, name='{self.name}')>"


class Card(BaseModel):
    """卡片模型，用于用户卡片管理"""
    __tablename__ = "card"
    
    id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    userid = Column(Integer, ForeignKey("users.userid"), nullable=False)
    type = Column(Integer, default=1)
    headline = Column(Text(200), nullable=False)
    content = Column(Text(16777216), default="")
    donetime = Column(DateTime)
    usedtime = Column(Integer, default=0)
    begintime = Column(DateTime)
    endtime = Column(DateTime)
    cardcategory_id = Column(Integer, ForeignKey('cardcategory.id'), default=1)
    
    # 定义关系
    cardcategory = relationship('CardCategory', back_populates='cards')

    def __repr__(self):
        return f"<Card(id={self.id}, headline='{self.headline[:20]}...', type={self.type})>"


# 获取配置项的辅助函数
def get_config(key, default=None):
    """
    获取配置项
    
    Args:
        key: 配置键，支持层级访问，如'database.development'
        default: 如果键不存在，返回的默认值
            
    Returns:
        配置值或默认值
    """
    value = config_data
    for part in key.split('.'):
        if isinstance(value, dict) and part in value:
            value = value[part]
        else:
            return default
    return value


# 为向后兼容提供的初始化函数
def init_database():
    """初始化数据库，创建所有表并添加默认管理员用户"""
    try:
        with app.app_context():
            # 创建所有表
            db.create_all()
            
            # 检查是否已有用户，避免重复创建
            if User.query.filter_by(role='admin').first() is None:
                # 创建默认管理员用户
                admin_user = User(
                    username=get_config('admin.username', 'admin'),
                    nickname=get_config('admin.nickname', '管理员'),
                    password=hashlib.md5(get_config('admin.password', 'admin123').encode()).hexdigest(),
                    role="admin",
                    createtime=datetime.now(),
                    updatetime=datetime.now()
                )
                db.session.add(admin_user)
                
                # 创建编辑用户
                editor_user = User(
                    username=get_config('editor.username', 'editor'),
                    nickname=get_config('editor.nickname', '编辑'),
                    password=hashlib.md5(get_config('editor.password', 'editor123').encode()).hexdigest(),
                    role="editor",
                    createtime=datetime.now(),
                    updatetime=datetime.now()
                )
                db.session.add(editor_user)
                
                # 创建普通用户
                common_user = User(
                    username=get_config('user.username', 'user'),
                    nickname=get_config('user.nickname', '普通用户'),
                    password=hashlib.md5(get_config('user.password', 'user123').encode()).hexdigest(),
                    role="user",
                    createtime=datetime.now(),
                    updatetime=datetime.now()
                )
                db.session.add(common_user)
                
                # 提交会话
                db.session.commit()
                print("初始化数据库成功，默认用户已创建")
            else:
                print("数据库已初始化，跳过默认用户创建")
    except Exception as e:
        print(f"初始化数据库时出错: {e}")
        db.session.rollback()


# 应用启动入口
if __name__ == '__main__':
    init_database()
