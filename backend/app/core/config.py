"""
应用配置
"""
import os
from typing import List
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """应用配置类"""
    # 应用设置
    APP_NAME: str = "WoniuNote"
    # 开发环境下默认开启 DEBUG，方便定位错误
    DEBUG: bool = True
    SECRET_KEY: str = "your-secret-key-change-in-production"
    
    # 数据库设置
    # 默认使用专用的 woniunote_user 账户，避免使用 root 帐号导致权限或安全问题
    # 注意：MySQL 用户通常创建为 'woniunote_user'@'localhost'，因此这里使用 localhost 而不是 127.0.0.1
    # 如需本地覆盖，可在 .env 中设置 DATABASE_URL
    DATABASE_URL: str = "mysql+asyncmy://woniunote_user:Woniunote_password1!@localhost:3306/woniunote"
    
    # Redis设置
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # JWT设置
    JWT_SECRET_KEY: str = "jwt-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24小时
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # CORS设置
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:5173"]
    
    # 上传设置
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE: int = 16 * 1024 * 1024  # 16MB
    ALLOWED_EXTENSIONS: List[str] = ["jpg", "jpeg", "png", "gif", "pdf", "doc", "docx", "txt", "zip", "rar"]
    
    # 资源目录设置 (缩略图等静态资源)
    RESOURCE_DIR: str = ""  # 默认自动检测
    
    # 分页设置
    DEFAULT_PAGE_SIZE: int = 10
    MAX_PAGE_SIZE: int = 100
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()


settings = get_settings()
