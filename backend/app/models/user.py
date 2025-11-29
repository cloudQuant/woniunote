"""
用户模型
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from app.core.database import Base


class User(Base):
    """用户表"""
    __tablename__ = "users"
    
    userid = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), nullable=False, unique=True, index=True)
    password = Column(String(128), nullable=False)
    nickname = Column(String(30))
    avatar = Column(String(200))
    qq = Column(String(15))
    role = Column(String(10), nullable=False, default="user")
    credit = Column(Integer, default=50)
    createtime = Column(DateTime, default=datetime.now)
    updatetime = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 关系
    articles = relationship("Article", back_populates="author", lazy="dynamic")
    comments = relationship("Comment", back_populates="user", lazy="dynamic")
    favorites = relationship("Favorite", back_populates="user", lazy="dynamic")
    credits = relationship("Credit", back_populates="user", lazy="dynamic")
    
    def __repr__(self):
        return f"<User {self.username}>"
