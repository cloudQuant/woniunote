"""
收藏模型
"""
from datetime import datetime
from sqlalchemy import Column, Integer, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.core.database import Base


class Favorite(Base):
    """收藏表"""
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
