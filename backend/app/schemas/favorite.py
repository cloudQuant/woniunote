"""
收藏Schema
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from app.schemas.article import ArticleListItem


class FavoriteCreate(BaseModel):
    """创建收藏Schema"""
    articleid: int


class FavoriteResponse(BaseModel):
    """收藏响应Schema"""
    favoriteid: int
    userid: int
    articleid: int
    canceled: int
    createtime: Optional[datetime] = None
    article: Optional[ArticleListItem] = None
    
    class Config:
        from_attributes = True
