"""
评论 Schema 模块

本模块定义了评论相关的 Pydantic 模型，用于请求验证和响应序列化。
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from app.schemas.user import UserBrief


class CommentBase(BaseModel):
    """
    评论基础 Schema
    
    定义评论共有的字段。
    """
    content: str = Field(..., min_length=1, max_length=65536, description="评论内容")
    replyid: Optional[int] = Field(None, description="回复的评论ID")


class CommentCreate(CommentBase):
    """
    创建评论 Schema
    
    用于创建评论时的请求验证。
    """
    articleid: int = Field(..., description="文章ID")


class CommentUpdate(BaseModel):
    """
    更新评论 Schema
    
    用于更新评论时的请求验证。
    """
    content: Optional[str] = Field(None, min_length=1, max_length=65536, description="评论内容")


class CommentResponse(BaseModel):
    """
    评论响应 Schema
    
    用于返回评论详情。
    """
    commentid: int = Field(..., description="评论ID")
    userid: int = Field(..., description="用户ID")
    articleid: int = Field(..., description="文章ID")
    content: str = Field(..., description="评论内容")
    replyid: Optional[int] = Field(None, description="回复的评论ID")
    agreecount: Optional[int] = Field(0, description="点赞数")
    opposecount: Optional[int] = Field(0, description="反对数")
    hidden: int = Field(..., description="是否隐藏")
    createtime: Optional[datetime] = Field(None, description="创建时间")
    user: Optional[UserBrief] = Field(None, description="评论者信息")
    
    class Config:
        from_attributes = True
