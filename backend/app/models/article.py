"""
文章模型
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class Article(Base):
    """文章表"""
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
