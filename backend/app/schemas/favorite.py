"""
收藏 Schema 模块

本模块定义了收藏相关的 Pydantic 模型，用于请求验证和响应序列化。
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from app.schemas.article import ArticleListItem


class FavoriteCreate(BaseModel):
    """
    创建收藏 Schema
    
    用于创建收藏时的请求验证。
    """
    articleid: int = Field(..., description="文章ID")


class FavoriteResponse(BaseModel):
    """
    收藏响应 Schema
    
    用于返回收藏详情。
    """
    favoriteid: int = Field(..., description="收藏ID")
    userid: int = Field(..., description="用户ID")
    articleid: int = Field(..., description="文章ID")
    canceled: int = Field(..., description="是否取消收藏")
    createtime: Optional[datetime] = Field(None, description="创建时间")
    article: Optional[ArticleListItem] = Field(None, description="文章信息")
    
    class Config:
        from_attributes = True
