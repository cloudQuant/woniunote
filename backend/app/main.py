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
from app.core.rate_limit import rate_limit_middleware
from app.core.exceptions import register_exception_handlers
from app.api import auth, articles, comments, favorites, users, upload, captcha, thumb, ueditor, credits, admin, todos, cards, system


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


API_DESCRIPTION = """
# WoniuNote API 文档

WoniuNote 是一个功能完整的量化交易知识分享平台，提供文章管理、用户认证、评论互动等功能。

## 功能模块

### 🔐 认证模块
- 用户注册、登录、登出
- JWT Token 认证机制
- 密码安全（bcrypt加密）

### 📝 文章模块
- 文章的CRUD操作
- 分类、搜索、分页
- 推荐、热门文章

### 💬 评论模块
- 评论的增删改查
- 点赞/踩功能
- 回复评论

### ⭐ 收藏模块
- 收藏/取消收藏文章
- 收藏列表管理

### 💰 积分系统
- 积分获取（注册、评论等）
- 积分消费（阅读付费文章）

### ✅ 待办事项
- 分类管理
- 事项CRUD
- 完成状态切换

### 📋 任务卡片
- 优先级管理
- 时间追踪
- 重复任务

## 认证方式

除公开接口外，大部分接口需要在请求头中携带 JWT Token：

```
Authorization: Bearer <your_token>
```

## 响应格式

所有接口返回统一的JSON格式：

```json
{
    "code": 200,
    "message": "success",
    "data": { ... }
}
```

分页接口额外包含：

```json
{
    "code": 200,
    "message": "success",
    "data": [...],
    "total": 100,
    "page": 1,
    "page_size": 10,
    "total_pages": 10
}
```
"""

app = FastAPI(
    title="WoniuNote API",
    description=API_DESCRIPTION,
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    openapi_tags=[
        {"name": "认证", "description": "用户注册、登录、Token管理"},
        {"name": "用户", "description": "用户信息管理"},
        {"name": "文章", "description": "文章的增删改查、分类、搜索"},
        {"name": "评论", "description": "评论管理、点赞/踩"},
        {"name": "收藏", "description": "文章收藏管理"},
        {"name": "积分", "description": "积分系统"},
        {"name": "上传", "description": "文件上传"},
        {"name": "验证码", "description": "验证码生成和验证"},
        {"name": "缩略图", "description": "文章缩略图"},
        {"name": "UEditor", "description": "富文本编辑器接口"},
        {"name": "管理员", "description": "管理员专用接口"},
        {"name": "待办事项", "description": "待办事项管理"},
        {"name": "卡片管理", "description": "任务卡片和时间追踪"},
        {"name": "系统监控", "description": "系统状态监控"},
    ]
)

# 注册全局异常处理器
register_exception_handlers(app)

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

# 限流中间件
@app.middleware("http")
async def add_rate_limit(request, call_next):
    return await rate_limit_middleware(request, call_next)

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
app.include_router(credits.router, prefix="/api/credits", tags=["积分"])
app.include_router(admin.router, prefix="/api/admin", tags=["管理员"])
app.include_router(todos.router, prefix="/api/todos", tags=["待办事项"])
app.include_router(cards.router, prefix="/api/cards", tags=["卡片管理"])
app.include_router(system.router, prefix="/api/system", tags=["系统监控"])


@app.get("/")
async def root():
    return {"message": "WoniuNote API v2.0.0", "status": "running"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
