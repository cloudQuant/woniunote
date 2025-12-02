"""
待办事项Schema
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


# 分类相关
class TodoCategoryBase(BaseModel):
    name: str
    sort_order: Optional[int] = 0


class TodoCategoryCreate(TodoCategoryBase):
    pass


class TodoCategoryUpdate(BaseModel):
    name: Optional[str] = None
    sort_order: Optional[int] = None


class TodoCategoryResponse(TodoCategoryBase):
    id: int
    userid: int
    createtime: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# 待办事项相关
class TodoItemBase(BaseModel):
    body: str
    category_id: int
    priority: Optional[int] = 0
    due_date: Optional[datetime] = None


class TodoItemCreate(TodoItemBase):
    pass


class TodoItemUpdate(BaseModel):
    body: Optional[str] = None
    category_id: Optional[int] = None
    priority: Optional[int] = None
    due_date: Optional[datetime] = None
    done: Optional[int] = None


class TodoItemResponse(TodoItemBase):
    id: int
    userid: int
    done: int
    createtime: Optional[datetime] = None
    updatetime: Optional[datetime] = None
    donetime: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class TodoItemWithCategory(TodoItemResponse):
    category_name: Optional[str] = None
