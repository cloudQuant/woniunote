"""
待办事项模型模块

本模块定义了待办事项相关的数据模型，包含分类和事项两个模型。
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class TodoCategory(Base):
    """
    待办事项分类表
    
    用于对待办事项进行分类管理。
    
    Attributes:
        id (int): 分类 ID，主键
        userid (int): 用户 ID，外键关联 users 表
        name (str): 分类名称
        sort_order (int): 排序权重
        createtime (datetime): 创建时间
        updatetime (datetime): 更新时间
    """
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
    """
    待办事项表
    
    记录具体的待办事项信息。
    
    Attributes:
        id (int): 事项 ID，主键
        userid (int): 用户 ID，外键关联 users 表
        category_id (int): 分类 ID，外键关联 todo_category 表
        body (str): 事项内容
        done (int): 是否完成 (0: 未完成, 1: 已完成)
        priority (int): 优先级 (0: 普通, 1: 重要, 2: 紧急)
        due_date (datetime): 截止日期
        createtime (datetime): 创建时间
        updatetime (datetime): 更新时间
        donetime (datetime): 完成时间
    """
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
