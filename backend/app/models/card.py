"""
卡片管理模型 - 用于任务追踪和时间管理
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class CardCategory(Base):
    """卡片分类表"""
    __tablename__ = "card_category"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    userid = Column(Integer, ForeignKey("users.userid"), nullable=False, index=True)
    name = Column(String(64), nullable=False)
    type = Column(Integer, default=0)  # 0: 普通, 1: 时间类(日/周/月/年), 2: 优先级类
    sort_order = Column(Integer, default=0)
    createtime = Column(DateTime, default=datetime.now)
    updatetime = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 关系
    user = relationship("User", backref="card_categories")
    cards = relationship("Card", back_populates="category", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<CardCategory {self.name}>"


class Card(Base):
    """卡片表 - 任务追踪"""
    __tablename__ = "card"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    userid = Column(Integer, ForeignKey("users.userid"), nullable=False, index=True)
    category_id = Column(Integer, ForeignKey("card_category.id"), nullable=False, index=True)
    headline = Column(String(200), nullable=False)
    content = Column(Text, default="")
    type = Column(Integer, default=1)  # 优先级: 1-重要紧急, 2-重要不紧急, 3-紧急不重要, 4-不重要不紧急
    is_repeat = Column(Integer, default=0)  # 是否重复任务
    
    # 时间追踪
    createtime = Column(DateTime, default=datetime.now)
    updatetime = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    begintime = Column(DateTime, nullable=True)  # 开始时间
    endtime = Column(DateTime, nullable=True)  # 结束时间
    donetime = Column(DateTime, nullable=True)  # 完成时间
    usedtime = Column(Integer, default=0)  # 累计使用时间(秒)
    
    # 关系
    user = relationship("User", backref="cards")
    category = relationship("CardCategory", back_populates="cards")
    
    def __repr__(self):
        return f"<Card {self.id}: {self.headline[:20]}>"
