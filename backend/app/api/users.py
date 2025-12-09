"""
用户 API 模块

本模块提供用户信息的获取、更新、密码修改以及管理员获取用户列表等接口。
"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.core.security import verify_password, get_password_hash
from app.models.user import User
from app.schemas.user import UserUpdate, UserPasswordUpdate, UserResponse
from app.schemas.common import ResponseModel, PaginatedResponse
from app.api.deps import get_current_user_required, get_admin_user

router = APIRouter()


@router.get("/{userid}", response_model=ResponseModel[UserResponse])
async def get_user(
    userid: int,
    db: AsyncSession = Depends(get_db)
):
    """
    获取用户信息
    
    根据用户 ID 获取用户的公开信息。
    
    Args:
        userid: 用户 ID
        db: 数据库会话
        
    Returns:
        ResponseModel[UserResponse]: 用户信息
        
    Raises:
        HTTPException(404): 用户不存在
    """
    result = await db.execute(select(User).where(User.userid == userid))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    return ResponseModel(
        code=200,
        message="success",
        data=UserResponse.model_validate(user)
    )


@router.put("/me", response_model=ResponseModel[UserResponse])
async def update_me(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db)
):
    """
    更新当前用户信息
    
    更新当前登录用户的昵称、头像、QQ 等信息。
    
    Args:
        user_data: 要更新的用户数据
        current_user: 当前已认证用户
        db: 数据库会话
        
    Returns:
        ResponseModel[UserResponse]: 更新后的用户信息
    """
    update_data = user_data.model_dump(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(current_user, field, value)
    
    current_user.updatetime = datetime.now()
    await db.commit()
    await db.refresh(current_user)
    
    return ResponseModel(
        code=200,
        message="更新成功",
        data=UserResponse.model_validate(current_user)
    )


@router.put("/me/password")
async def update_password(
    password_data: UserPasswordUpdate,
    current_user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db)
):
    """
    修改密码
    
    验证旧密码并更新为新密码。
    
    Args:
        password_data: 密码修改数据 (旧密码, 新密码)
        current_user: 当前已认证用户
        db: 数据库会话
        
    Returns:
        ResponseModel: 成功消息
        
    Raises:
        HTTPException(400): 旧密码错误
    """
    # 验证旧密码
    if not verify_password(password_data.old_password, current_user.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="旧密码错误"
        )
    
    # 更新密码（使用bcrypt加密）
    current_user.password = get_password_hash(password_data.new_password)
    current_user.updatetime = datetime.now()
    await db.commit()
    
    return ResponseModel(code=200, message="密码修改成功")


@router.get("/", response_model=PaginatedResponse[dict])
async def list_users(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量"),
    keyword: str = Query(None, description="搜索用户名或昵称"),
    admin_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取用户列表（管理员）
    
    分页获取用户列表，支持按用户名或昵称搜索。需要管理员权限。
    
    Args:
        page: 页码
        page_size: 每页数量
        keyword: 搜索关键词
        admin_user: 管理员用户 (依赖注入验证权限)
        db: 数据库会话
        
    Returns:
        PaginatedResponse[dict]: 分页的用户列表
    """
    # 构建查询
    query = select(User)
    
    # 关键词搜索
    if keyword:
        query = query.where(
            User.username.contains(keyword) | User.nickname.contains(keyword)
        )
    
    # 获取总数
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # 分页
    offset = (page - 1) * page_size
    query = query.order_by(User.userid.desc()).offset(offset).limit(page_size)
    
    result = await db.execute(query)
    users = result.scalars().all()
    
    return PaginatedResponse(
        code=200,
        message="success",
        data=[UserResponse.model_validate(u).model_dump() for u in users],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size if total > 0 else 0
    )
