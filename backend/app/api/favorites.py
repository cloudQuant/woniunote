"""
收藏API
"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.favorite import Favorite
from app.models.article import Article
from app.models.user import User
from app.schemas.favorite import FavoriteCreate, FavoriteResponse
from app.schemas.common import ResponseModel, PaginatedResponse
from app.api.deps import get_current_user_required

router = APIRouter()


@router.get("/", response_model=PaginatedResponse[dict])
async def get_my_favorites(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db)
):
    """获取我的收藏列表"""
    # 获取总数
    count_query = select(func.count()).select_from(Favorite).where(
        and_(
            Favorite.userid == current_user.userid,
            Favorite.canceled == 0
        )
    )
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # 分页获取收藏
    offset = (page - 1) * page_size
    query = select(Favorite).where(
        and_(
            Favorite.userid == current_user.userid,
            Favorite.canceled == 0
        )
    ).options(
        selectinload(Favorite.article)
    ).order_by(Favorite.createtime.desc()).offset(offset).limit(page_size)
    
    result = await db.execute(query)
    favorites = result.scalars().all()
    
    return PaginatedResponse(
        code=200,
        message="success",
        data=[FavoriteResponse.model_validate(f).model_dump() for f in favorites],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size
    )


@router.post("/", response_model=ResponseModel[dict])
async def add_favorite(
    favorite_data: FavoriteCreate,
    current_user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db)
):
    """添加收藏"""
    # 检查文章是否存在
    article_result = await db.execute(
        select(Article).where(Article.articleid == favorite_data.articleid)
    )
    if not article_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文章不存在"
        )
    
    # 检查是否已收藏
    existing_result = await db.execute(
        select(Favorite).where(
            and_(
                Favorite.userid == current_user.userid,
                Favorite.articleid == favorite_data.articleid
            )
        )
    )
    existing = existing_result.scalar_one_or_none()
    
    if existing:
        if existing.canceled == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="已经收藏过了"
            )
        else:
            # 恢复收藏
            existing.canceled = 0
            existing.updatetime = datetime.now()
            await db.commit()
            await db.refresh(existing)
            return ResponseModel(
                code=200,
                message="收藏成功",
                data=FavoriteResponse.model_validate(existing).model_dump()
            )
    
    # 创建新收藏
    new_favorite = Favorite(
        userid=current_user.userid,
        articleid=favorite_data.articleid,
        createtime=datetime.now(),
        updatetime=datetime.now()
    )
    
    db.add(new_favorite)
    await db.commit()
    await db.refresh(new_favorite)
    
    return ResponseModel(
        code=200,
        message="收藏成功",
        data=FavoriteResponse.model_validate(new_favorite).model_dump()
    )


@router.delete("/{articleid}")
async def remove_favorite(
    articleid: int,
    current_user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db)
):
    """取消收藏"""
    result = await db.execute(
        select(Favorite).where(
            and_(
                Favorite.userid == current_user.userid,
                Favorite.articleid == articleid
            )
        )
    )
    favorite = result.scalar_one_or_none()
    
    if not favorite or favorite.canceled == 1:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="未收藏此文章"
        )
    
    favorite.canceled = 1
    favorite.updatetime = datetime.now()
    await db.commit()
    
    return ResponseModel(code=200, message="取消收藏成功")


@router.get("/check/{articleid}", response_model=ResponseModel[dict])
async def check_favorite(
    articleid: int,
    current_user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db)
):
    """检查是否已收藏"""
    result = await db.execute(
        select(Favorite).where(
            and_(
                Favorite.userid == current_user.userid,
                Favorite.articleid == articleid,
                Favorite.canceled == 0
            )
        )
    )
    favorite = result.scalar_one_or_none()
    
    return ResponseModel(
        code=200,
        message="success",
        data={"is_favorited": favorite is not None}
    )
