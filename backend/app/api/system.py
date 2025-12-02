"""
系统监控API
"""
import os
import platform
from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text

from app.core.database import get_db
from app.models.user import User
from app.models.article import Article
from app.models.comment import Comment
from app.schemas.common import ResponseModel
from app.api.deps import get_admin_user

router = APIRouter()


def get_size_format(bytes_size: int) -> str:
    """格式化字节大小"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024
    return f"{bytes_size:.2f} PB"


def get_time_format(seconds: int) -> str:
    """格式化时间"""
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60
    
    if days > 0:
        return f"{days}天 {hours}小时 {minutes}分钟"
    elif hours > 0:
        return f"{hours}小时 {minutes}分钟"
    else:
        return f"{minutes}分钟"


@router.get("/status", response_model=ResponseModel[dict])
async def get_system_status(
    admin_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """获取系统状态"""
    try:
        import psutil
        has_psutil = True
    except ImportError:
        has_psutil = False
    
    # 基础系统信息
    system_info = {
        "platform": platform.system(),
        "platform_release": platform.release(),
        "platform_version": platform.version(),
        "architecture": platform.machine(),
        "hostname": platform.node(),
        "python_version": platform.python_version(),
        "current_time": datetime.now().isoformat()
    }
    
    # 资源信息（如果有psutil）
    resource_info = {}
    if has_psutil:
        # CPU信息
        resource_info["cpu_count"] = psutil.cpu_count()
        resource_info["cpu_percent"] = psutil.cpu_percent(interval=1)
        
        # 内存信息
        memory = psutil.virtual_memory()
        resource_info["memory_total"] = get_size_format(memory.total)
        resource_info["memory_used"] = get_size_format(memory.used)
        resource_info["memory_percent"] = memory.percent
        
        # 磁盘信息 (Windows使用C盘，Linux使用根目录)
        import platform as pf
        disk_path = 'C:\\' if pf.system() == 'Windows' else '/'
        try:
            disk = psutil.disk_usage(disk_path)
            resource_info["disk_total"] = get_size_format(disk.total)
            resource_info["disk_used"] = get_size_format(disk.used)
            resource_info["disk_percent"] = disk.percent
            resource_info["disk_path"] = disk_path
        except Exception:
            resource_info["disk_error"] = "无法获取磁盘信息"
        
        # 系统运行时间
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        uptime = (datetime.now() - boot_time).total_seconds()
        resource_info["uptime"] = get_time_format(int(uptime))
        resource_info["boot_time"] = boot_time.isoformat()
    else:
        resource_info["note"] = "安装 psutil 库以获取更详细的系统资源信息"
    
    return ResponseModel(
        code=200,
        message="success",
        data={
            "system": system_info,
            "resources": resource_info
        }
    )


@router.get("/database", response_model=ResponseModel[dict])
async def get_database_status(
    admin_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """获取数据库状态"""
    # 表统计
    tables_stats = {}
    
    # 用户数
    user_count = await db.execute(select(func.count()).select_from(User))
    tables_stats["users"] = user_count.scalar() or 0
    
    # 文章数
    article_count = await db.execute(select(func.count()).select_from(Article))
    tables_stats["articles"] = article_count.scalar() or 0
    
    # 评论数
    comment_count = await db.execute(select(func.count()).select_from(Comment))
    tables_stats["comments"] = comment_count.scalar() or 0
    
    # 今日新增
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    today_users = await db.execute(
        select(func.count()).select_from(User).where(User.createtime >= today)
    )
    today_articles = await db.execute(
        select(func.count()).select_from(Article).where(Article.createtime >= today)
    )
    today_comments = await db.execute(
        select(func.count()).select_from(Comment).where(Comment.createtime >= today)
    )
    
    today_stats = {
        "users": today_users.scalar() or 0,
        "articles": today_articles.scalar() or 0,
        "comments": today_comments.scalar() or 0
    }
    
    return ResponseModel(
        code=200,
        message="success",
        data={
            "tables": tables_stats,
            "today": today_stats
        }
    )


@router.get("/health", response_model=ResponseModel[dict])
async def health_check(
    db: AsyncSession = Depends(get_db)
):
    """健康检查（不需要管理员权限）"""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "checks": {}
    }
    
    # 数据库连接检查
    try:
        await db.execute(text("SELECT 1"))
        health_status["checks"]["database"] = {"status": "ok"}
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["checks"]["database"] = {"status": "error", "message": str(e)}
    
    return ResponseModel(
        code=200,
        message="success",
        data=health_status
    )
