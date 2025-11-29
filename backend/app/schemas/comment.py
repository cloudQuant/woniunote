"""
评论Schema
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from app.schemas.user import UserBrief


class CommentBase(BaseModel):
    """评论基础Schema"""
    content: str = Field(..., min_length=1, max_length=65536)
    replyid: Optional[int] = None


class CommentCreate(CommentBase):
    """创建评论Schema"""
    articleid: int


class CommentUpdate(BaseModel):
    """更新评论Schema"""
    content: Optional[str] = Field(None, min_length=1, max_length=65536)


class CommentResponse(BaseModel):
    """评论响应Schema"""
    commentid: int
    userid: int
    articleid: int
    content: str
    replyid: Optional[int] = None
    agreecount: Optional[int] = 0
    opposecount: Optional[int] = 0
    hidden: int
    createtime: Optional[datetime] = None
    user: Optional[UserBrief] = None
    
    class Config:
        from_attributes = True
