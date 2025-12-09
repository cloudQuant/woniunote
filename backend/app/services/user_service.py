"""
用户服务层模块

本模块处理用户相关的业务逻辑，包括用户注册、登录、信息更新、密码修改等操作。
"""
from typing import Optional, Tuple
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import User
from app.models.credit import Credit
from app.core.security import (
    get_password_hash, 
    verify_password, 
    is_md5_password,
    create_access_token,
    create_refresh_token
)
from app.core.logger import log_auth_event, log_user_action, log_db_operation
from app.core.exceptions import (
    BadRequestException,
    UnauthorizedException,
    NotFoundException,
    ConflictException
)


class UserService:
    """
    用户服务类
    
    提供用户管理的业务逻辑接口。
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """
        根据 ID 获取用户
        
        Args:
            user_id: 用户 ID
            
        Returns:
            Optional[User]: 用户对象，如果不存在则返回 None
        """
        result = await self.db.execute(
            select(User).where(User.userid == user_id)
        )
        return result.scalar_one_or_none()
    
    async def get_user_by_username(self, username: str) -> Optional[User]:
        """
        根据用户名获取用户
        
        Args:
            username: 用户名
            
        Returns:
            Optional[User]: 用户对象，如果不存在则返回 None
        """
        result = await self.db.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()
    
    async def create_user(
        self,
        username: str,
        password: str,
        nickname: str = None,
        qq: str = None
    ) -> User:
        """
        创建新用户
        
        Args:
            username: 用户名
            password: 明文密码
            nickname: 昵称 (默认为用户名)
            qq: QQ 号
            
        Returns:
            User: 新创建的用户对象
            
        Raises:
            ConflictException: 用户名已存在
        """
        # 检查用户名是否已存在
        existing = await self.get_user_by_username(username)
        if existing:
            log_auth_event("register", username=username, success=False, reason="用户名已存在")
            raise ConflictException("用户名已存在")
        
        # 创建用户
        new_user = User(
            username=username,
            password=get_password_hash(password),
            nickname=nickname or username,
            qq=qq,
            role="user",
            credit=50,
            createtime=datetime.now(),
            updatetime=datetime.now()
        )
        
        self.db.add(new_user)
        await self.db.commit()
        await self.db.refresh(new_user)
        
        # 添加注册积分记录
        credit_record = Credit(
            userid=new_user.userid,
            category="用户注册",
            target=new_user.userid,
            credit=50,
            createtime=datetime.now(),
            updatetime=datetime.now()
        )
        self.db.add(credit_record)
        await self.db.commit()
        
        log_auth_event("register", username=username, user_id=new_user.userid, success=True)
        log_db_operation("INSERT", "users", record_id=new_user.userid)
        
        return new_user
    
    async def authenticate_user(
        self,
        username: str,
        password: str
    ) -> Tuple[User, str, str]:
        """
        验证用户并生成 Token
        
        Args:
            username: 用户名
            password: 明文密码
            
        Returns:
            Tuple[User, str, str]: (用户对象, access_token, refresh_token)
            
        Raises:
            UnauthorizedException: 用户名或密码错误
        """
        user = await self.get_user_by_username(username)
        
        if not user:
            log_auth_event("login", username=username, success=False, reason="用户不存在")
            raise UnauthorizedException("用户名或密码错误")
        
        if not verify_password(password, user.password):
            log_auth_event("login", username=username, success=False, reason="密码错误")
            raise UnauthorizedException("用户名或密码错误")
        
        # 自动升级MD5密码为bcrypt
        if is_md5_password(user.password):
            user.password = get_password_hash(password)
            user.updatetime = datetime.now()
            await self.db.commit()
            log_user_action(user.userid, "password_upgrade", "自动升级为bcrypt")
        
        # 生成Token
        access_token = create_access_token(data={"sub": str(user.userid)})
        refresh_token = create_refresh_token(data={"sub": str(user.userid)})
        
        log_auth_event("login", username=username, user_id=user.userid, success=True)
        
        return user, access_token, refresh_token
    
    async def update_password(
        self,
        user: User,
        old_password: str,
        new_password: str
    ) -> bool:
        """
        更新用户密码
        
        Args:
            user: 用户对象
            old_password: 旧密码
            new_password: 新密码
            
        Returns:
            bool: 是否更新成功
            
        Raises:
            BadRequestException: 旧密码错误
        """
        if not verify_password(old_password, user.password):
            log_auth_event("password_change", user_id=user.userid, success=False, reason="旧密码错误")
            raise BadRequestException("旧密码错误")
        
        user.password = get_password_hash(new_password)
        user.updatetime = datetime.now()
        await self.db.commit()
        
        log_auth_event("password_change", user_id=user.userid, success=True)
        return True
    
    async def update_profile(
        self,
        user: User,
        **kwargs
    ) -> User:
        """
        更新用户资料
        
        Args:
            user: 用户对象
            **kwargs: 要更新的字段及值
            
        Returns:
            User: 更新后的用户对象
        """
        for field, value in kwargs.items():
            if hasattr(user, field) and field not in ['userid', 'username', 'password', 'role', 'credit']:
                setattr(user, field, value)
        
        user.updatetime = datetime.now()
        await self.db.commit()
        await self.db.refresh(user)
        
        log_user_action(user.userid, "update_profile", detail=kwargs)
        return user
