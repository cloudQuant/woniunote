"""
API 依赖项模块

本模块定义了 FastAPI 路由所需的依赖项，如获取当前用户、数据库会话等。
"""
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import decode_token
from app.models.user import User

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """
    获取当前用户（可选）
    
    尝试从请求头的 Bearer Token 中解析用户信息。如果未提供 Token 或 Token 无效，返回 None。
    
    Args:
        credentials: 认证凭据 (Bearer Token)
        db: 数据库会话
        
    Returns:
        Optional[User]: 用户对象，如果认证失败则返回 None
    """
    if not credentials:
        return None
    
    payload = decode_token(credentials.credentials)
    if not payload:
        return None
    
    userid = payload.get("sub")
    if not userid:
        return None
    
    result = await db.execute(select(User).where(User.userid == int(userid)))
    user = result.scalar_one_or_none()
    return user


async def get_current_user_required(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    获取当前用户（必需）
    
    从请求头的 Bearer Token 中解析用户信息。如果认证失败，抛出 HTTP 401 异常。
    
    Args:
        credentials: 认证凭据 (Bearer Token)
        db: 数据库会话
        
    Returns:
        User: 用户对象
        
    Raises:
        HTTPException(401): 未提供认证信息、Token 无效或用户不存在
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供认证信息",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    payload = decode_token(credentials.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    userid = payload.get("sub")
    if not userid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    result = await db.execute(select(User).where(User.userid == int(userid)))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


async def get_admin_user(
    current_user: User = Depends(get_current_user_required)
) -> User:
    """
    获取管理员用户
    
    依赖于 `get_current_user_required`，并额外检查用户角色是否为管理员或编辑。
    
    Args:
        current_user: 当前已认证用户
        
    Returns:
        User: 管理员用户对象
        
    Raises:
        HTTPException(403): 用户权限不足
    """
    if current_user.role not in ["admin", "editor"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )
    return current_user
