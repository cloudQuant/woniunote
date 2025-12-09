"""
文章模型模块

本模块定义了文章相关的数据模型。
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class Article(Base):
    """
    文章表
    
    存储文章的基本信息，包括标题、内容、作者、分类等。
    
    Attributes:
        articleid (int): 文章 ID，主键
        userid (int): 作者 ID，外键关联 users 表
        type (int): 文章分类 ID
        headline (str): 文章标题
        content (str): 文章内容
        thumbnail (str): 缩略图路径
        credit (int): 阅读所需积分
        readcount (int): 阅读次数
        replycount (int): 回复次数
        recommended (int): 是否推荐 (0: 否, 1: 是)
        hidden (int): 是否隐藏 (0: 否, 1: 是)
        drafted (int): 是否草稿 (0: 否, 1: 是)
        checked (int): 是否审核通过 (0: 待审核, 1: 通过)
        createtime (datetime): 创建时间
        updatetime (datetime): 更新时间
    """
    __tablename__ = "article"
    
    articleid = Column(Integer, primary_key=True, autoincrement=True)
    userid = Column(Integer, ForeignKey("users.userid"), nullable=False, index=True)
    type = Column(Integer, nullable=False, index=True)
    headline = Column(String(100), nullable=False)
    content = Column(Text(16777216))
    thumbnail = Column(String(200))
    credit = Column(Integer, default=0)
    readcount = Column(Integer, default=0)
    replycount = Column(Integer, default=0)
    recommended = Column(Integer, default=0, index=True)
    hidden = Column(Integer, default=0)
    drafted = Column(Integer, default=0)
    checked = Column(Integer, default=1)
    createtime = Column(DateTime, default=datetime.now, index=True)
    updatetime = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 关系
    author = relationship("User", back_populates="articles")
    comments = relationship(
        "Comment",
        back_populates="article",
        lazy="dynamic",
        cascade="all, delete-orphan"
    )
    favorites = relationship(
        "Favorite",
        back_populates="article",
        lazy="dynamic",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self):
        return f"<Article {self.articleid}: {self.headline[:20]}>"
