"""
认证API
"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import (
    verify_password,
    get_password_hash,
    get_md5_hash,
    is_md5_password,
    create_access_token,
    create_refresh_token,
    decode_token
)
from app.models.user import User
from app.schemas.user import UserCreate, UserLogin, UserResponse
from app.schemas.common import ResponseModel, TokenResponse
from app.api.deps import get_current_user_required
from app.api.captcha import validate_captcha
from app.models.credit import Credit

router = APIRouter()


@router.post("/register", response_model=ResponseModel[UserResponse])
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """用户注册"""
    # 检查用户名是否已存在
    result = await db.execute(
        select(User).where(User.username == user_data.username)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已存在"
        )
    
    # 创建用户（新用户使用bcrypt加密密码）
    new_user = User(
        username=user_data.username,
        password=get_password_hash(user_data.password),  # 使用bcrypt加密
        nickname=user_data.nickname or user_data.username,
        qq=user_data.qq,
        role="user",
        credit=50,
        createtime=datetime.now(),
        updatetime=datetime.now()
    )
    
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    # 添加注册积分记录
    credit_record = Credit(
        userid=new_user.userid,
        category="用户注册",
        target=new_user.userid,
        credit=50,
        createtime=datetime.now(),
        updatetime=datetime.now()
    )
    db.add(credit_record)
    await db.commit()
    
    return ResponseModel(
        code=200,
        message="注册成功",
        data=UserResponse.model_validate(new_user)
    )


@router.post("/login", response_model=ResponseModel[dict])
async def login(
    login_data: UserLogin,
    db: AsyncSession = Depends(get_db)
):
    """用户登录"""
    # 验证验证码
    captcha_valid, captcha_error = validate_captcha(
        login_data.captcha_id, 
        login_data.captcha_code
    )
    if not captcha_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=captcha_error
        )
    
    # 查找用户
    result = await db.execute(
        select(User).where(User.username == login_data.username)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )
    
    # 验证密码
    if not verify_password(login_data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )
    
    # 自动升级MD5密码为bcrypt（增强安全性）
    if is_md5_password(user.password):
        user.password = get_password_hash(login_data.password)
        user.updatetime = datetime.now()
        await db.commit()
    
    # 生成令牌
    access_token = create_access_token(data={"sub": str(user.userid)})
    refresh_token = create_refresh_token(data={"sub": str(user.userid)})
    
    return ResponseModel(
        code=200,
        message="登录成功",
        data={
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user": UserResponse.model_validate(user).model_dump()
        }
    )


@router.post("/refresh", response_model=ResponseModel[TokenResponse])
async def refresh_token(
    refresh_token: str,
    db: AsyncSession = Depends(get_db)
):
    """刷新访问令牌"""
    payload = decode_token(refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的刷新令牌"
        )
    
    userid = payload.get("sub")
    result = await db.execute(select(User).where(User.userid == int(userid)))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在"
        )
    
    # 生成新令牌
    new_access_token = create_access_token(data={"sub": str(user.userid)})
    new_refresh_token = create_refresh_token(data={"sub": str(user.userid)})
    
    return ResponseModel(
        code=200,
        message="刷新成功",
        data=TokenResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token
        )
    )


@router.get("/me", response_model=ResponseModel[UserResponse])
async def get_me(
    current_user: User = Depends(get_current_user_required)
):
    """获取当前用户信息"""
    return ResponseModel(
        code=200,
        message="success",
        data=UserResponse.model_validate(current_user)
    )


@router.post("/logout")
async def logout():
    """用户登出"""
    return ResponseModel(code=200, message="登出成功")
