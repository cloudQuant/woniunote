"""
积分模型模块

本模块定义了用户积分相关的数据模型。
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class Credit(Base):
    """
    积分表
    
    记录用户的积分变动历史。
    
    Attributes:
        creditid (int): 积分记录 ID，主键
        userid (int): 用户 ID，外键关联 users 表
        category (str): 积分类型 (如: login, post, comment)
        target (int): 关联目标 ID (如文章 ID)
        credit (int): 变动积分数 (正数增加，负数减少)
        createtime (datetime): 创建时间
        updatetime (datetime): 更新时间
    """
    __tablename__ = "credit"
    
    creditid = Column(Integer, primary_key=True, autoincrement=True)
    userid = Column(Integer, ForeignKey("users.userid"), nullable=False, index=True)
    category = Column(String(10))
    target = Column(Integer)
    credit = Column(Integer)
    createtime = Column(DateTime, default=datetime.now)
    updatetime = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 关系
    user = relationship("User", back_populates="credits")
    
    def __repr__(self):
        return f"<Credit {self.creditid}: {self.credit}>"
