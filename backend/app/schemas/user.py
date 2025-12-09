"""
用户 Schema 模块

本模块定义了用户相关的 Pydantic 模型，用于请求验证和响应序列化。
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, EmailStr


class UserBase(BaseModel):
    """
    用户基础 Schema
    
    定义用户共有的字段。
    """
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    nickname: Optional[str] = Field(None, max_length=30, description="昵称")
    qq: Optional[str] = Field(None, max_length=15, description="QQ号")


class UserCreate(UserBase):
    """
    用户注册 Schema
    
    用于用户注册时的请求验证。
    """
    password: str = Field(..., min_length=6, max_length=32, description="密码")


class UserLogin(BaseModel):
    """
    用户登录 Schema
    
    用于用户登录时的请求验证。
    """
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    password: str = Field(..., min_length=6, max_length=32, description="密码")
    captcha_id: Optional[str] = Field(None, description="验证码ID")
    captcha_code: Optional[str] = Field(None, description="验证码")


class UserUpdate(BaseModel):
    """
    用户更新 Schema
    
    用于更新用户信息时的请求验证。
    """
    nickname: Optional[str] = Field(None, max_length=30, description="昵称")
    avatar: Optional[str] = Field(None, description="头像路径")
    qq: Optional[str] = Field(None, max_length=15, description="QQ号")


class UserPasswordUpdate(BaseModel):
    """
    修改密码 Schema
    
    用于修改密码时的请求验证。
    """
    old_password: str = Field(..., min_length=6, max_length=32, description="旧密码")
    new_password: str = Field(..., min_length=6, max_length=32, description="新密码")


class UserResponse(BaseModel):
    """
    用户响应 Schema
    
    用于返回用户详情。
    """
    userid: int = Field(..., description="用户ID")
    username: str = Field(..., description="用户名")
    nickname: Optional[str] = Field(None, description="昵称")
    avatar: Optional[str] = Field(None, description="头像路径")
    qq: Optional[str] = Field(None, description="QQ号")
    role: str = Field(..., description="角色")
    credit: int = Field(..., description="积分")
    createtime: Optional[datetime] = Field(None, description="创建时间")
    
    class Config:
        from_attributes = True


class UserBrief(BaseModel):
    """
    用户简要信息 Schema
    
    用于在其他对象（如文章、评论）中嵌入作者信息。
    """
    userid: int = Field(..., description="用户ID")
    username: str = Field(..., description="用户名")
    nickname: Optional[str] = Field(None, description="昵称")
    avatar: Optional[str] = Field(None, description="头像路径")
    
    class Config:
        from_attributes = True
