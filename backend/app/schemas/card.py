"""
卡片管理Schema
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


# 分类相关
class CardCategoryBase(BaseModel):
    name: str
    type: Optional[int] = 0
    sort_order: Optional[int] = 0


class CardCategoryCreate(CardCategoryBase):
    pass


class CardCategoryUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[int] = None
    sort_order: Optional[int] = None


class CardCategoryResponse(CardCategoryBase):
    id: int
    userid: int
    createtime: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# 卡片相关
class CardBase(BaseModel):
    headline: str
    category_id: int
    content: Optional[str] = ""
    type: Optional[int] = 1
    is_repeat: Optional[int] = 0


class CardCreate(CardBase):
    pass


class CardUpdate(BaseModel):
    headline: Optional[str] = None
    category_id: Optional[int] = None
    content: Optional[str] = None
    type: Optional[int] = None
    is_repeat: Optional[int] = None


class CardResponse(CardBase):
    id: int
    userid: int
    createtime: Optional[datetime] = None
    updatetime: Optional[datetime] = None
    begintime: Optional[datetime] = None
    endtime: Optional[datetime] = None
    donetime: Optional[datetime] = None
    usedtime: int = 0
    
    class Config:
        from_attributes = True


class CardWithCategory(CardResponse):
    category_name: Optional[str] = None


class CardStats(BaseModel):
    """卡片统计"""
    total: int = 0
    done: int = 0
    in_progress: int = 0
    total_time: int = 0  # 总计用时(秒)
