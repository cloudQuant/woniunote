"""
积分Schema
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class CreditBase(BaseModel):
    """积分基础模型"""
    category: str
    target: Optional[int] = None
    credit: int


class CreditCreate(CreditBase):
    """创建积分记录"""
    pass


class CreditResponse(CreditBase):
    """积分响应模型"""
    creditid: int
    userid: int
    createtime: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class CreditSummary(BaseModel):
    """积分汇总"""
    total_credit: int
    credit_history: list[CreditResponse]
