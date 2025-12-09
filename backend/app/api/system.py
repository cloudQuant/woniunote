"""
系统监控 API 模块

本模块提供系统资源、数据库状态、进程信息等监控功能。
"""
import os
import sys
import platform
from datetime import datetime
from typing import List, Dict, Any
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

# 尝试导入psutil
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


def get_size_format(bytes_size: int) -> str:
    """
    格式化字节大小
    
    将字节数转换为人类可读的格式（B, KB, MB, GB, TB, PB）。
    
    Args:
        bytes_size: 字节大小
        
    Returns:
        str: 格式化后的字符串
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024
    return f"{bytes_size:.2f} PB"


def get_size_bytes(bytes_size: int) -> Dict[str, Any]:
    """
    返回字节大小的详细信息
    
    Args:
        bytes_size: 字节大小
        
    Returns:
        Dict[str, Any]: 包含原始字节数和格式化字符串的字典
    """
    return {
        "bytes": bytes_size,
        "formatted": get_size_format(bytes_size)
    }


def get_time_format(seconds: int) -> str:
    """
    格式化时间
    
    将秒数转换为天、小时、分钟的格式。
    
    Args:
        seconds: 秒数
        
    Returns:
        str: 格式化后的时间字符串
    """
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
    """
    获取完整系统状态
    
    获取包括系统信息、CPU、内存、磁盘、网络、进程等在内的完整系统状态信息。
    需要管理员权限。
    
    Args:
        admin_user: 管理员用户
        db: 数据库会话
        
    Returns:
        ResponseModel[dict]: 系统状态信息
    """
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
    
    # 资源信息
    resources = {
        "has_psutil": HAS_PSUTIL
    }
    
    if HAS_PSUTIL:
        # CPU信息
        cpu_freq = psutil.cpu_freq()
        resources["cpu"] = {
            "count_physical": psutil.cpu_count(logical=False),
            "count_logical": psutil.cpu_count(logical=True),
            "percent": psutil.cpu_percent(interval=0.5),
            "percent_per_cpu": psutil.cpu_percent(interval=0.1, percpu=True),
            "freq_current": round(cpu_freq.current, 2) if cpu_freq else None,
            "freq_max": round(cpu_freq.max, 2) if cpu_freq else None,
        }
        
        # 内存信息
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()
        resources["memory"] = {
            "total": get_size_bytes(memory.total),
            "used": get_size_bytes(memory.used),
            "available": get_size_bytes(memory.available),
            "percent": memory.percent,
            "swap_total": get_size_bytes(swap.total),
            "swap_used": get_size_bytes(swap.used),
            "swap_percent": swap.percent
        }
        
        # 磁盘信息
        disk_path = 'C:\\' if platform.system() == 'Windows' else '/'
        try:
            disk = psutil.disk_usage(disk_path)
            disk_io = psutil.disk_io_counters()
            resources["disk"] = {
                "path": disk_path,
                "total": get_size_bytes(disk.total),
                "used": get_size_bytes(disk.used),
                "free": get_size_bytes(disk.free),
                "percent": disk.percent,
                "read_bytes": get_size_bytes(disk_io.read_bytes) if disk_io else None,
                "write_bytes": get_size_bytes(disk_io.write_bytes) if disk_io else None,
            }
        except Exception as e:
            resources["disk"] = {"error": str(e)}
        
        # 网络信息
        try:
            net_io = psutil.net_io_counters()
            resources["network"] = {
                "bytes_sent": get_size_bytes(net_io.bytes_sent),
                "bytes_recv": get_size_bytes(net_io.bytes_recv),
                "packets_sent": net_io.packets_sent,
                "packets_recv": net_io.packets_recv,
                "errors_in": net_io.errin,
                "errors_out": net_io.errout,
            }
        except Exception:
            resources["network"] = {"error": "无法获取网络信息"}
        
        # 系统运行时间
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        uptime_seconds = (datetime.now() - boot_time).total_seconds()
        resources["uptime"] = {
            "seconds": int(uptime_seconds),
            "formatted": get_time_format(int(uptime_seconds)),
            "boot_time": boot_time.isoformat()
        }
        
        # 当前进程信息
        current_process = psutil.Process()
        resources["process"] = {
            "pid": current_process.pid,
            "name": current_process.name(),
            "cpu_percent": current_process.cpu_percent(),
            "memory_percent": round(current_process.memory_percent(), 2),
            "memory_used": get_size_bytes(current_process.memory_info().rss),
            "threads": current_process.num_threads(),
            "create_time": datetime.fromtimestamp(current_process.create_time()).isoformat()
        }
    else:
        resources["note"] = "请安装 psutil 库以获取系统资源信息: pip install psutil"
    
    return ResponseModel(
        code=200,
        message="success",
        data={
            "system": system_info,
            "resources": resources
        }
    )


@router.get("/metrics", response_model=ResponseModel[dict])
async def get_realtime_metrics(
    admin_user: User = Depends(get_admin_user)
):
    """
    获取实时监控指标
    
    获取轻量级的实时监控数据，适用于定时刷新。
    
    Args:
        admin_user: 管理员用户
        
    Returns:
        ResponseModel[dict]: 实时监控指标
    """
    if not HAS_PSUTIL:
        return ResponseModel(
            code=200,
            message="psutil not installed",
            data={"error": "请安装 psutil 库"}
        )
    
    memory = psutil.virtual_memory()
    current_process = psutil.Process()
    
    return ResponseModel(
        code=200,
        message="success",
        data={
            "timestamp": datetime.now().isoformat(),
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_percent": memory.percent,
            "memory_used_gb": round(memory.used / (1024**3), 2),
            "memory_total_gb": round(memory.total / (1024**3), 2),
            "process_cpu": current_process.cpu_percent(),
            "process_memory_mb": round(current_process.memory_info().rss / (1024**2), 2),
        }
    )


@router.get("/processes", response_model=ResponseModel[dict])
async def get_top_processes(
    admin_user: User = Depends(get_admin_user),
    limit: int = 10
):
    """
    获取占用资源最多的进程
    
    获取 CPU 或内存占用率最高的进程列表。
    
    Args:
        admin_user: 管理员用户
        limit: 返回的进程数量限制
        
    Returns:
        ResponseModel[dict]: 进程列表
    """
    if not HAS_PSUTIL:
        return ResponseModel(
            code=200,
            message="psutil not installed",
            data={"error": "请安装 psutil 库"}
        )
    
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
        try:
            pinfo = proc.info
            processes.append({
                "pid": pinfo['pid'],
                "name": pinfo['name'],
                "cpu_percent": pinfo['cpu_percent'] or 0,
                "memory_percent": round(pinfo['memory_percent'] or 0, 2)
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    
    # 按CPU使用率排序
    top_by_cpu = sorted(processes, key=lambda x: x['cpu_percent'], reverse=True)[:limit]
    # 按内存使用率排序
    top_by_memory = sorted(processes, key=lambda x: x['memory_percent'], reverse=True)[:limit]
    
    return ResponseModel(
        code=200,
        message="success",
        data={
            "top_by_cpu": top_by_cpu,
            "top_by_memory": top_by_memory,
            "total_processes": len(processes)
        }
    )


@router.get("/database", response_model=ResponseModel[dict])
async def get_database_status(
    admin_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取数据库状态
    
    统计数据库中的表记录数及今日新增数据。
    
    Args:
        admin_user: 管理员用户
        db: 数据库会话
        
    Returns:
        ResponseModel[dict]: 数据库统计信息
    """
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
    """
    健康检查
    
    检查系统和数据库连接状态。不需要管理员权限。
    
    Args:
        db: 数据库会话
        
    Returns:
        ResponseModel[dict]: 健康状态信息
    """
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
