"""
文章 Schema 模块

本模块定义了文章相关的 Pydantic 模型，用于请求验证和响应序列化。
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from app.schemas.user import UserBrief


class ArticleBase(BaseModel):
    """
    文章基础 Schema
    
    定义文章共有的字段。
    """
    headline: str = Field(..., min_length=1, max_length=100, description="文章标题")
    type: int = Field(..., ge=1, description="文章分类ID")
    content: Optional[str] = Field(None, description="文章内容")
    thumbnail: Optional[str] = Field(None, description="缩略图路径")
    credit: int = Field(default=0, ge=0, description="阅读所需积分")


class ArticleCreate(ArticleBase):
    """
    创建文章 Schema
    
    用于创建文章时的请求验证。
    """
    drafted: int = Field(default=0, ge=0, le=1, description="是否草稿 (0:否, 1:是)")


class ArticleUpdate(BaseModel):
    """
    更新文章 Schema
    
    用于更新文章时的请求验证。所有字段均为可选。
    """
    headline: Optional[str] = Field(None, min_length=1, max_length=100, description="文章标题")
    type: Optional[int] = Field(None, ge=1, description="文章分类ID")
    content: Optional[str] = Field(None, description="文章内容")
    thumbnail: Optional[str] = Field(None, description="缩略图路径")
    credit: Optional[int] = Field(None, ge=0, description="阅读所需积分")
    drafted: Optional[int] = Field(None, ge=0, le=1, description="是否草稿")


class ArticleResponse(BaseModel):
    """
    文章响应 Schema
    
    用于返回文章详情。
    """
    articleid: int = Field(..., description="文章ID")
    userid: int = Field(..., description="作者ID")
    type: int = Field(..., description="文章分类ID")
    headline: str = Field(..., description="文章标题")
    content: Optional[str] = Field(None, description="文章内容")
    thumbnail: Optional[str] = Field(None, description="缩略图路径")
    credit: int = Field(..., description="阅读所需积分")
    readcount: int = Field(..., description="阅读次数")
    replycount: int = Field(..., description="回复次数")
    recommended: int = Field(..., description="是否推荐")
    hidden: int = Field(..., description="是否隐藏")
    drafted: int = Field(..., description="是否草稿")
    checked: int = Field(..., description="是否审核通过")
    createtime: Optional[datetime] = Field(None, description="创建时间")
    updatetime: Optional[datetime] = Field(None, description="更新时间")
    author: Optional[UserBrief] = Field(None, description="作者信息")
    
    class Config:
        from_attributes = True


class ArticleListItem(BaseModel):
    """
    文章列表项 Schema
    
    用于文章列表接口返回，包含文章的简要信息。
    """
    articleid: int = Field(..., description="文章ID")
    userid: int = Field(..., description="作者ID")
    type: int = Field(..., description="文章分类ID")
    headline: str = Field(..., description="文章标题")
    content: Optional[str] = Field(None, description="文章摘要")
    thumbnail: Optional[str] = Field(None, description="缩略图路径")
    credit: int = Field(..., description="阅读所需积分")
    readcount: int = Field(..., description="阅读次数")
    replycount: int = Field(..., description="回复次数")
    recommended: int = Field(..., description="是否推荐")
    createtime: Optional[datetime] = Field(None, description="创建时间")
    author: Optional[UserBrief] = Field(None, description="作者信息")
    
    class Config:
        from_attributes = True


class ArticleTypeConfig(BaseModel):
    """
    文章类型配置 Schema
    
    用于返回文章分类配置。
    """
    types: dict = Field(..., description="文章分类字典")
