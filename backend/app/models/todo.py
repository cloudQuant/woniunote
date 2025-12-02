"""
待办事项模型
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class TodoCategory(Base):
    """待办事项分类表"""
    __tablename__ = "todo_category"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    userid = Column(Integer, ForeignKey("users.userid"), nullable=False, index=True)
    name = Column(String(64), nullable=False)
    sort_order = Column(Integer, default=0)
    createtime = Column(DateTime, default=datetime.now)
    updatetime = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 关系
    user = relationship("User", backref="todo_categories")
    items = relationship("TodoItem", back_populates="category", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<TodoCategory {self.name}>"


class TodoItem(Base):
    """待办事项表"""
    __tablename__ = "todo_item"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    userid = Column(Integer, ForeignKey("users.userid"), nullable=False, index=True)
    category_id = Column(Integer, ForeignKey("todo_category.id"), nullable=False, index=True)
    body = Column(Text, nullable=False)
    done = Column(Integer, default=0)  # 0: 未完成, 1: 已完成
    priority = Column(Integer, default=0)  # 优先级: 0-普通, 1-重要, 2-紧急
    due_date = Column(DateTime, nullable=True)  # 截止日期
    createtime = Column(DateTime, default=datetime.now)
    updatetime = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    donetime = Column(DateTime, nullable=True)  # 完成时间
    
    # 关系
    user = relationship("User", backref="todo_items")
    category = relationship("TodoCategory", back_populates="items")
    
    def __repr__(self):
        return f"<TodoItem {self.id}: {self.body[:20]}>"
