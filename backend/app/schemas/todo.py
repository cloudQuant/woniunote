"""
待办事项 Schema 模块

本模块定义了待办事项相关的 Pydantic 模型，包括分类和具体事项。
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


# 分类相关
class TodoCategoryBase(BaseModel):
    """
    待办事项分类基础 Schema
    
    定义分类共有的字段。
    """
    name: str = Field(..., description="分类名称")
    sort_order: Optional[int] = Field(0, description="排序权重")


class TodoCategoryCreate(TodoCategoryBase):
    """
    创建待办事项分类 Schema
    
    用于创建分类时的请求验证。
    """
    pass


class TodoCategoryUpdate(BaseModel):
    """
    更新待办事项分类 Schema
    
    用于更新分类时的请求验证。
    """
    name: Optional[str] = Field(None, description="分类名称")
    sort_order: Optional[int] = Field(None, description="排序权重")


class TodoCategoryResponse(TodoCategoryBase):
    """
    待办事项分类响应 Schema
    
    用于返回分类详情。
    """
    id: int = Field(..., description="分类ID")
    userid: int = Field(..., description="用户ID")
    createtime: Optional[datetime] = Field(None, description="创建时间")
    
    class Config:
        from_attributes = True


# 待办事项相关
class TodoItemBase(BaseModel):
    """
    待办事项基础 Schema
    
    定义事项共有的字段。
    """
    body: str = Field(..., description="事项内容")
    category_id: int = Field(..., description="分类ID")
    priority: Optional[int] = Field(0, description="优先级 (0:普通, 1:重要, 2:紧急)")
    due_date: Optional[datetime] = Field(None, description="截止日期")


class TodoItemCreate(TodoItemBase):
    """
    创建待办事项 Schema
    
    用于创建事项时的请求验证。
    """
    pass


class TodoItemUpdate(BaseModel):
    """
    更新待办事项 Schema
    
    用于更新事项时的请求验证。所有字段均为可选。
    """
    body: Optional[str] = Field(None, description="事项内容")
    category_id: Optional[int] = Field(None, description="分类ID")
    priority: Optional[int] = Field(None, description="优先级")
    due_date: Optional[datetime] = Field(None, description="截止日期")
    done: Optional[int] = Field(None, description="是否完成 (0:未完成, 1:已完成)")


class TodoItemResponse(TodoItemBase):
    """
    待办事项响应 Schema
    
    用于返回事项详情。
    """
    id: int = Field(..., description="事项ID")
    userid: int = Field(..., description="用户ID")
    done: int = Field(..., description="是否完成")
    createtime: Optional[datetime] = Field(None, description="创建时间")
    updatetime: Optional[datetime] = Field(None, description="更新时间")
    donetime: Optional[datetime] = Field(None, description="完成时间")
    
    class Config:
        from_attributes = True


class TodoItemWithCategory(TodoItemResponse):
    """
    带分类名称的待办事项 Schema
    
    用于列表展示，包含分类名称。
    """
    category_name: Optional[str] = Field(None, description="分类名称")
