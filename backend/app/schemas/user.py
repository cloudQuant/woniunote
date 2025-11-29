"""
用户Schema
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, EmailStr


class UserBase(BaseModel):
    """用户基础Schema"""
    username: str = Field(..., min_length=3, max_length=50)
    nickname: Optional[str] = Field(None, max_length=30)
    qq: Optional[str] = Field(None, max_length=15)


class UserCreate(UserBase):
    """用户注册Schema"""
    password: str = Field(..., min_length=6, max_length=32)


class UserLogin(BaseModel):
    """用户登录Schema"""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=32)
    captcha_id: Optional[str] = Field(None, description="验证码ID")
    captcha_code: Optional[str] = Field(None, description="验证码")


class UserUpdate(BaseModel):
    """用户更新Schema"""
    nickname: Optional[str] = Field(None, max_length=30)
    avatar: Optional[str] = None
    qq: Optional[str] = Field(None, max_length=15)


class UserPasswordUpdate(BaseModel):
    """修改密码Schema"""
    old_password: str = Field(..., min_length=6, max_length=32)
    new_password: str = Field(..., min_length=6, max_length=32)


class UserResponse(BaseModel):
    """用户响应Schema"""
    userid: int
    username: str
    nickname: Optional[str] = None
    avatar: Optional[str] = None
    qq: Optional[str] = None
    role: str
    credit: int
    createtime: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class UserBrief(BaseModel):
    """用户简要信息"""
    userid: int
    username: str
    nickname: Optional[str] = None
    avatar: Optional[str] = None
    
    class Config:
        from_attributes = True
