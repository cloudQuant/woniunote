"""
收藏模型模块

本模块定义了用户收藏文章的数据模型。
"""
from datetime import datetime
from sqlalchemy import Column, Integer, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.core.database import Base


class Favorite(Base):
    """
    收藏表
    
    记录用户收藏的文章。
    
    Attributes:
        favoriteid (int): 收藏 ID，主键
        userid (int): 用户 ID，外键关联 users 表
        articleid (int): 文章 ID，外键关联 article 表
        canceled (int): 是否取消收藏 (0: 否, 1: 是)
        createtime (datetime): 创建时间
        updatetime (datetime): 更新时间
    """
    __tablename__ = "favorite"
    
    favoriteid = Column(Integer, primary_key=True, autoincrement=True)
    userid = Column(Integer, ForeignKey("users.userid"), nullable=False, index=True)
    articleid = Column(Integer, ForeignKey("article.articleid"), nullable=False, index=True)
    canceled = Column(Integer, default=0)
    createtime = Column(DateTime, default=datetime.now)
    updatetime = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 唯一约束
    __table_args__ = (
        UniqueConstraint('userid', 'articleid', name='uix_user_article'),
    )
    
    # 关系
    user = relationship("User", back_populates="favorites")
    article = relationship("Article", back_populates="favorites")
    
    def __repr__(self):
        return f"<Favorite user={self.userid} article={self.articleid}>"
