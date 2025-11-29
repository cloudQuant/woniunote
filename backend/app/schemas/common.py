"""
通用Schema
"""
from typing import Generic, TypeVar, Optional, List
from pydantic import BaseModel

T = TypeVar("T")


class ResponseBase(BaseModel):
    """响应基类"""
    code: int = 200
    message: str = "success"


class ResponseModel(ResponseBase, Generic[T]):
    """通用响应模型"""
    data: Optional[T] = None


class PaginatedResponse(ResponseBase, Generic[T]):
    """分页响应模型"""
    data: List[T] = []
    total: int = 0
    page: int = 1
    page_size: int = 10
    total_pages: int = 0


class TokenResponse(BaseModel):
    """令牌响应"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
