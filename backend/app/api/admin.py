"""
管理员API
"""
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.core.database import get_db
from app.models.article import Article
from app.models.user import User
from app.models.comment import Comment
from app.schemas.common import ResponseModel
from app.api.deps import get_admin_user

router = APIRouter()


@router.get("/stats", response_model=ResponseModel[dict])
async def get_admin_stats(
    admin_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """获取管理统计数据"""
    # 文章总数
    articles_count = await db.execute(select(func.count()).select_from(Article))
    total_articles = articles_count.scalar() or 0
    
    # 用户总数
    users_count = await db.execute(select(func.count()).select_from(User))
    total_users = users_count.scalar() or 0
    
    # 评论总数
    comments_count = await db.execute(select(func.count()).select_from(Comment))
    total_comments = comments_count.scalar() or 0
    
    # 总阅读量
    readcount_sum = await db.execute(select(func.sum(Article.readcount)))
    total_views = readcount_sum.scalar() or 0
    
    # 今日新增文章
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_articles = await db.execute(
        select(func.count()).select_from(Article).where(Article.createtime >= today)
    )
    articles_today = today_articles.scalar() or 0
    
    # 今日新增用户
    today_users = await db.execute(
        select(func.count()).select_from(User).where(User.createtime >= today)
    )
    users_today = today_users.scalar() or 0
    
    # 推荐文章数
    recommended_count = await db.execute(
        select(func.count()).select_from(Article).where(Article.recommended == 1)
    )
    total_recommended = recommended_count.scalar() or 0
    
    return ResponseModel(
        code=200,
        message="success",
        data={
            "total_articles": total_articles,
            "total_users": total_users,
            "total_comments": total_comments,
            "total_views": total_views,
            "articles_today": articles_today,
            "users_today": users_today,
            "total_recommended": total_recommended
        }
    )


@router.get("/users", response_model=ResponseModel[dict])
async def get_all_users(
    page: int = 1,
    page_size: int = 20,
    admin_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """获取所有用户列表"""
    import math
    
    # 获取总数
    count_query = select(func.count()).select_from(User)
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # 分页查询
    offset = (page - 1) * page_size
    query = select(User).order_by(User.createtime.desc()).offset(offset).limit(page_size)
    result = await db.execute(query)
    users = result.scalars().all()
    
    # 构建响应
    user_list = []
    for user in users:
        user_list.append({
            "userid": user.userid,
            "username": user.username,
            "nickname": user.nickname,
            "role": user.role,
            "credit": user.credit,
            "createtime": user.createtime.isoformat() if user.createtime else None
        })
    
    return ResponseModel(
        code=200,
        message="success",
        data={
            "users": user_list,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": math.ceil(total / page_size) if total > 0 else 0
        }
    )
