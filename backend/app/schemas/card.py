"""
卡片管理 Schema 模块

本模块定义了卡片管理相关的 Pydantic 模型，包括卡片分类和卡片任务。
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


# 分类相关
class CardCategoryBase(BaseModel):
    """
    卡片分类基础 Schema
    
    定义卡片分类共有的字段。
    """
    name: str = Field(..., description="分类名称")
    type: Optional[int] = Field(0, description="分类类型 (0:普通, 1:时间类, 2:优先级类)")
    sort_order: Optional[int] = Field(0, description="排序权重")


class CardCategoryCreate(CardCategoryBase):
    """
    创建卡片分类 Schema
    
    用于创建卡片分类时的请求验证。
    """
    pass


class CardCategoryUpdate(BaseModel):
    """
    更新卡片分类 Schema
    
    用于更新卡片分类时的请求验证。所有字段均为可选。
    """
    name: Optional[str] = Field(None, description="分类名称")
    type: Optional[int] = Field(None, description="分类类型")
    sort_order: Optional[int] = Field(None, description="排序权重")


class CardCategoryResponse(CardCategoryBase):
    """
    卡片分类响应 Schema
    
    用于返回卡片分类详情。
    """
    id: int = Field(..., description="分类ID")
    userid: int = Field(..., description="用户ID")
    createtime: Optional[datetime] = Field(None, description="创建时间")
    
    class Config:
        from_attributes = True


# 卡片相关
class CardBase(BaseModel):
    """
    卡片基础 Schema
    
    定义卡片共有的字段。
    """
    headline: str = Field(..., description="任务标题")
    category_id: int = Field(..., description="分类ID")
    content: Optional[str] = Field("", description="任务详情")
    type: Optional[int] = Field(1, description="优先级 (1-4)")
    is_repeat: Optional[int] = Field(0, description="是否重复任务")


class CardCreate(CardBase):
    """
    创建卡片 Schema
    
    用于创建卡片时的请求验证。
    """
    pass


class CardUpdate(BaseModel):
    """
    更新卡片 Schema
    
    用于更新卡片时的请求验证。所有字段均为可选。
    """
    headline: Optional[str] = Field(None, description="任务标题")
    category_id: Optional[int] = Field(None, description="分类ID")
    content: Optional[str] = Field(None, description="任务详情")
    type: Optional[int] = Field(None, description="优先级")
    is_repeat: Optional[int] = Field(None, description="是否重复任务")


class CardResponse(CardBase):
    """
    卡片响应 Schema
    
    用于返回卡片详情。
    """
    id: int = Field(..., description="卡片ID")
    userid: int = Field(..., description="用户ID")
    createtime: Optional[datetime] = Field(None, description="创建时间")
    updatetime: Optional[datetime] = Field(None, description="更新时间")
    begintime: Optional[datetime] = Field(None, description="开始时间")
    endtime: Optional[datetime] = Field(None, description="结束时间")
    donetime: Optional[datetime] = Field(None, description="完成时间")
    usedtime: int = Field(0, description="累计使用时间(秒)")
    
    class Config:
        from_attributes = True


class CardWithCategory(CardResponse):
    """
    带分类名称的卡片 Schema
    
    用于列表展示，包含分类名称。
    """
    category_name: Optional[str] = Field(None, description="分类名称")


class CardStats(BaseModel):
    """
    卡片统计 Schema
    
    用于返回卡片统计信息。
    """
    total: int = Field(0, description="总任务数")
    done: int = Field(0, description="已完成任务数")
    in_progress: int = Field(0, description="进行中任务数")
    total_time: int = Field(0, description="总计用时(秒)")
