"""
积分 Schema 模块

本模块定义了积分相关的 Pydantic 模型，用于请求验证和响应序列化。
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class CreditBase(BaseModel):
    """
    积分基础 Schema
    
    定义积分共有的字段。
    """
    category: str = Field(..., description="积分类型")
    target: Optional[int] = Field(None, description="关联目标ID")
    credit: int = Field(..., description="变动积分数")


class CreditCreate(CreditBase):
    """
    创建积分记录 Schema
    
    用于创建积分记录时的请求验证。
    """
    pass


class CreditResponse(CreditBase):
    """
    积分响应 Schema
    
    用于返回积分记录详情。
    """
    creditid: int = Field(..., description="积分记录ID")
    userid: int = Field(..., description="用户ID")
    createtime: Optional[datetime] = Field(None, description="创建时间")
    
    class Config:
        from_attributes = True


class CreditSummary(BaseModel):
    """
    积分汇总 Schema
    
    用于返回用户的积分汇总信息。
    """
    total_credit: int = Field(..., description="总积分")
    credit_history: List[CreditResponse] = Field(..., description="积分历史记录")
