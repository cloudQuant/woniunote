"""
用户API
"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import verify_password, get_md5_hash
from app.models.user import User
from app.schemas.user import UserUpdate, UserPasswordUpdate, UserResponse
from app.schemas.common import ResponseModel
from app.api.deps import get_current_user_required, get_admin_user

router = APIRouter()


@router.get("/{userid}", response_model=ResponseModel[UserResponse])
async def get_user(
    userid: int,
    db: AsyncSession = Depends(get_db)
):
    """获取用户信息"""
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
    """更新当前用户信息"""
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
    """修改密码"""
    # 验证旧密码
    if not verify_password(password_data.old_password, current_user.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="旧密码错误"
        )
    
    # 更新密码
    current_user.password = get_md5_hash(password_data.new_password)
    current_user.updatetime = datetime.now()
    await db.commit()
    
    return ResponseModel(code=200, message="密码修改成功")


@router.get("/", response_model=ResponseModel[list])
async def list_users(
    page: int = 1,
    page_size: int = 10,
    admin_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """获取用户列表（管理员）"""
    offset = (page - 1) * page_size
    
    result = await db.execute(
        select(User)
        .order_by(User.userid.desc())
        .offset(offset)
        .limit(page_size)
    )
    users = result.scalars().all()
    
    return ResponseModel(
        code=200,
        message="success",
        data=[UserResponse.model_validate(u).model_dump() for u in users]
    )
