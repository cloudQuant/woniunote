"""
WoniuNote FastAPI 后端主入口
"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.database import engine, Base
from app.core.logger import log_info, log_error
from app.core.middleware import LoggingMiddleware
from app.api import auth, articles, comments, favorites, users, upload, captcha, thumb, ueditor


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    log_info("WoniuNote API 启动中...")
    # 启动时创建数据库表
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    log_info("WoniuNote API 启动完成")
    yield
    # 关闭时清理资源
    log_info("WoniuNote API 关闭中...")
    await engine.dispose()
    log_info("WoniuNote API 已关闭")


app = FastAPI(
    title="WoniuNote API",
    description="WoniuNote 博客系统 API",
    version="2.0.0",
    lifespan=lifespan
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 日志中间件
app.add_middleware(LoggingMiddleware)

# 注册路由
app.include_router(auth.router, prefix="/api/auth", tags=["认证"])
app.include_router(users.router, prefix="/api/users", tags=["用户"])
app.include_router(articles.router, prefix="/api/articles", tags=["文章"])
app.include_router(comments.router, prefix="/api/comments", tags=["评论"])
app.include_router(favorites.router, prefix="/api/favorites", tags=["收藏"])
app.include_router(upload.router, prefix="/api/upload", tags=["上传"])
app.include_router(captcha.router, prefix="/api/captcha", tags=["验证码"])
app.include_router(thumb.router, prefix="/api", tags=["缩略图"])
app.include_router(ueditor.router, prefix="/api", tags=["UEditor"])


@app.get("/")
async def root():
    return {"message": "WoniuNote API v2.0.0", "status": "running"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
