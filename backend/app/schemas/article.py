"""
文章Schema
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from app.schemas.user import UserBrief


class ArticleBase(BaseModel):
    """文章基础Schema"""
    headline: str = Field(..., min_length=1, max_length=100)
    type: int = Field(..., ge=1)
    content: Optional[str] = None
    thumbnail: Optional[str] = None
    credit: int = Field(default=0, ge=0)


class ArticleCreate(ArticleBase):
    """创建文章Schema"""
    drafted: int = Field(default=0, ge=0, le=1)


class ArticleUpdate(BaseModel):
    """更新文章Schema"""
    headline: Optional[str] = Field(None, min_length=1, max_length=100)
    type: Optional[int] = Field(None, ge=1)
    content: Optional[str] = None
    thumbnail: Optional[str] = None
    credit: Optional[int] = Field(None, ge=0)
    drafted: Optional[int] = Field(None, ge=0, le=1)


class ArticleResponse(BaseModel):
    """文章响应Schema"""
    articleid: int
    userid: int
    type: int
    headline: str
    content: Optional[str] = None
    thumbnail: Optional[str] = None
    credit: int
    readcount: int
    replycount: int
    recommended: int
    hidden: int
    drafted: int
    checked: int
    createtime: Optional[datetime] = None
    updatetime: Optional[datetime] = None
    author: Optional[UserBrief] = None
    
    class Config:
        from_attributes = True


class ArticleListItem(BaseModel):
    """文章列表项Schema"""
    articleid: int
    userid: int
    type: int
    headline: str
    content: Optional[str] = None  # 用于生成摘要
    thumbnail: Optional[str] = None
    credit: int
    readcount: int
    replycount: int
    recommended: int
    createtime: Optional[datetime] = None
    author: Optional[UserBrief] = None
    
    class Config:
        from_attributes = True


class ArticleTypeConfig(BaseModel):
    """文章类型配置"""
    types: dict
