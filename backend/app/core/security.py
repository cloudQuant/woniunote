"""
安全相关工具
"""
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional, Union

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码

    - 兼容旧的 MD5 密码（32 位十六进制）
    - 其余情况使用 bcrypt 库直接验证，避免 passlib 与 bcrypt 版本不兼容问题
    """
    if not hashed_password:
        return False

    # 兼容旧的 MD5 密码
    if len(hashed_password) == 32 and all(c in "0123456789abcdef" for c in hashed_password.lower()):
        return hashlib.md5(plain_password.encode("utf-8")).hexdigest() == hashed_password

    # 其余使用 bcrypt 校验
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except ValueError:
        # 哈希格式不正确时，直接返回 False
        return False


def is_md5_password(hashed_password: str) -> bool:
    """检查是否是MD5密码（需要升级）"""
    return len(hashed_password) == 32


def get_password_hash(password: str) -> str:
    """获取 bcrypt 密码哈希（推荐用于新用户）"""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def get_md5_hash(password: str) -> str:
    """获取MD5哈希（仅用于兼容旧系统，不推荐新用户使用）"""
    return hashlib.md5(password.encode()).hexdigest()


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """创建访问令牌"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    """创建刷新令牌"""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Optional[dict]:
    """解码令牌"""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError:
        return None
