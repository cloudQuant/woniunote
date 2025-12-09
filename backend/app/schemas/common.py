"""
通用 Schema 模块

本模块定义了通用的响应模型和基础 Schema。
"""
from typing import Generic, TypeVar, Optional, List
from pydantic import BaseModel, Field

T = TypeVar("T")


class ResponseBase(BaseModel):
    """
    响应基类
    
    定义所有 API 响应共有的字段。
    """
    code: int = Field(200, description="状态码")
    message: str = Field("success", description="消息提示")


class ResponseModel(ResponseBase, Generic[T]):
    """
    通用响应模型
    
    用于包装单个数据对象的响应。
    """
    data: Optional[T] = Field(None, description="数据内容")


class PaginatedResponse(ResponseBase, Generic[T]):
    """
    分页响应模型
    
    用于包装分页数据的响应。
    """
    data: List[T] = Field([], description="数据列表")
    total: int = Field(0, description="总记录数")
    page: int = Field(1, description="当前页码")
    page_size: int = Field(10, description="每页数量")
    total_pages: int = Field(0, description="总页数")


class TokenResponse(BaseModel):
    """
    令牌响应 Schema
    
    用于返回 JWT 令牌。
    """
    access_token: str = Field(..., description="访问令牌")
    refresh_token: str = Field(..., description="刷新令牌")
    token_type: str = Field("bearer", description="令牌类型")
