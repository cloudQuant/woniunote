"""
卡片管理API - 任务追踪和时间管理
"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_

from app.core.database import get_db
from app.models.card import CardCategory, Card
from app.models.user import User
from app.schemas.card import (
    CardCategoryCreate, CardCategoryUpdate, CardCategoryResponse,
    CardCreate, CardUpdate, CardResponse, CardWithCategory, CardStats
)
from app.schemas.common import ResponseModel, PaginatedResponse
from app.api.deps import get_current_user_required

router = APIRouter()


# 优先级类型名称映射
PRIORITY_NAMES = {
    1: "重要紧急",
    2: "重要不紧急",
    3: "紧急不重要",
    4: "不重要不紧急"
}


# ==================== 分类管理 ====================

@router.get("/categories", response_model=ResponseModel[list])
async def get_categories(
    current_user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db)
):
    """获取所有卡片分类"""
    query = select(CardCategory).where(
        CardCategory.userid == current_user.userid
    ).order_by(CardCategory.sort_order, CardCategory.id)
    
    result = await db.execute(query)
    categories = result.scalars().all()
    
    return ResponseModel(
        code=200,
        message="success",
        data=[CardCategoryResponse.model_validate(c).model_dump() for c in categories]
    )


@router.post("/categories", response_model=ResponseModel[dict])
async def create_category(
    data: CardCategoryCreate,
    current_user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db)
):
    """创建卡片分类"""
    new_category = CardCategory(
        userid=current_user.userid,
        name=data.name,
        type=data.type,
        sort_order=data.sort_order,
        createtime=datetime.now(),
        updatetime=datetime.now()
    )
    db.add(new_category)
    await db.commit()
    await db.refresh(new_category)
    
    return ResponseModel(
        code=200,
        message="创建成功",
        data=CardCategoryResponse.model_validate(new_category).model_dump()
    )


@router.put("/categories/{category_id}", response_model=ResponseModel[dict])
async def update_category(
    category_id: int,
    data: CardCategoryUpdate,
    current_user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db)
):
    """更新卡片分类"""
    result = await db.execute(
        select(CardCategory).where(
            CardCategory.id == category_id,
            CardCategory.userid == current_user.userid
        )
    )
    category = result.scalar_one_or_none()
    
    if not category:
        raise HTTPException(status_code=404, detail="分类不存在")
    
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(category, field, value)
    
    category.updatetime = datetime.now()
    await db.commit()
    await db.refresh(category)
    
    return ResponseModel(
        code=200,
        message="更新成功",
        data=CardCategoryResponse.model_validate(category).model_dump()
    )


@router.delete("/categories/{category_id}")
async def delete_category(
    category_id: int,
    current_user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db)
):
    """删除卡片分类"""
    result = await db.execute(
        select(CardCategory).where(
            CardCategory.id == category_id,
            CardCategory.userid == current_user.userid
        )
    )
    category = result.scalar_one_or_none()
    
    if not category:
        raise HTTPException(status_code=404, detail="分类不存在")
    
    await db.delete(category)
    await db.commit()
    
    return ResponseModel(code=200, message="删除成功")


# ==================== 统计（放在动态路由之前） ====================

@router.get("/stats/summary", response_model=ResponseModel[dict])
async def get_stats(
    current_user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db)
):
    """获取卡片统计"""
    base_filter = Card.userid == current_user.userid
    
    # 总数
    total_result = await db.execute(
        select(func.count()).select_from(Card).where(base_filter)
    )
    total = total_result.scalar() or 0
    
    # 已完成
    done_result = await db.execute(
        select(func.count()).select_from(Card).where(and_(base_filter, Card.donetime.isnot(None)))
    )
    done = done_result.scalar() or 0
    
    # 进行中
    in_progress_result = await db.execute(
        select(func.count()).select_from(Card).where(
            and_(base_filter, Card.begintime.isnot(None), Card.donetime.is_(None))
        )
    )
    in_progress = in_progress_result.scalar() or 0
    
    # 总用时
    time_result = await db.execute(
        select(func.sum(Card.usedtime)).where(base_filter)
    )
    total_time = time_result.scalar() or 0
    
    # 按优先级统计
    priority_stats = {}
    for priority, name in PRIORITY_NAMES.items():
        count_result = await db.execute(
            select(func.count()).select_from(Card).where(
                and_(base_filter, Card.type == priority, Card.donetime.is_(None))
            )
        )
        priority_stats[name] = count_result.scalar() or 0
    
    return ResponseModel(
        code=200,
        message="success",
        data={
            "total": total,
            "done": done,
            "pending": total - done,
            "in_progress": in_progress,
            "total_time": total_time,
            "priority_stats": priority_stats
        }
    )


# ==================== 卡片管理 ====================

@router.get("/", response_model=PaginatedResponse[dict])
async def get_cards(
    category_id: int = Query(None),
    type: int = Query(None),
    done: int = Query(None),  # 0: 未完成, 1: 已完成
    in_progress: int = Query(None),  # 1: 进行中的卡片
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db)
):
    """获取卡片列表"""
    conditions = [Card.userid == current_user.userid]
    
    if category_id is not None:
        conditions.append(Card.category_id == category_id)
    if type is not None:
        conditions.append(Card.type == type)
    if done is not None:
        if done == 1:
            conditions.append(Card.donetime.isnot(None))
        else:
            conditions.append(Card.donetime.is_(None))
    if in_progress == 1:
        conditions.append(Card.begintime.isnot(None))
        conditions.append(Card.donetime.is_(None))
    
    query = select(Card).where(and_(*conditions))
    
    # 获取总数
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # 分页并排序
    offset = (page - 1) * page_size
    query = query.order_by(
        Card.type,  # 按优先级排序
        desc(Card.updatetime)
    ).offset(offset).limit(page_size)
    
    result = await db.execute(query)
    cards = result.scalars().all()
    
    return PaginatedResponse(
        code=200,
        message="success",
        data=[CardResponse.model_validate(c).model_dump() for c in cards],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size if total > 0 else 0
    )


@router.post("/", response_model=ResponseModel[dict])
async def create_card(
    data: CardCreate,
    current_user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db)
):
    """创建卡片"""
    # 验证分类归属
    category_result = await db.execute(
        select(CardCategory).where(
            CardCategory.id == data.category_id,
            CardCategory.userid == current_user.userid
        )
    )
    if not category_result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="分类不存在或无权访问")
    
    new_card = Card(
        userid=current_user.userid,
        category_id=data.category_id,
        headline=data.headline,
        content=data.content or "",
        type=data.type or 1,
        is_repeat=data.is_repeat or 0,
        createtime=datetime.now(),
        updatetime=datetime.now()
    )
    db.add(new_card)
    await db.commit()
    await db.refresh(new_card)
    
    return ResponseModel(
        code=200,
        message="创建成功",
        data=CardResponse.model_validate(new_card).model_dump()
    )


@router.get("/{card_id}", response_model=ResponseModel[dict])
async def get_card(
    card_id: int,
    current_user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db)
):
    """获取卡片详情"""
    result = await db.execute(
        select(Card).where(
            Card.id == card_id,
            Card.userid == current_user.userid
        )
    )
    card = result.scalar_one_or_none()
    
    if not card:
        raise HTTPException(status_code=404, detail="卡片不存在")
    
    return ResponseModel(
        code=200,
        message="success",
        data=CardResponse.model_validate(card).model_dump()
    )


@router.put("/{card_id}", response_model=ResponseModel[dict])
async def update_card(
    card_id: int,
    data: CardUpdate,
    current_user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db)
):
    """更新卡片"""
    result = await db.execute(
        select(Card).where(
            Card.id == card_id,
            Card.userid == current_user.userid
        )
    )
    card = result.scalar_one_or_none()
    
    if not card:
        raise HTTPException(status_code=404, detail="卡片不存在")
    
    # 如果更新分类，验证新分类归属
    if data.category_id is not None and data.category_id != card.category_id:
        category_result = await db.execute(
            select(CardCategory).where(
                CardCategory.id == data.category_id,
                CardCategory.userid == current_user.userid
            )
        )
        if not category_result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="目标分类不存在或无权访问")
    
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(card, field, value)
    
    card.updatetime = datetime.now()
    await db.commit()
    await db.refresh(card)
    
    return ResponseModel(
        code=200,
        message="更新成功",
        data=CardResponse.model_validate(card).model_dump()
    )


@router.delete("/{card_id}")
async def delete_card(
    card_id: int,
    current_user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db)
):
    """删除卡片"""
    result = await db.execute(
        select(Card).where(
            Card.id == card_id,
            Card.userid == current_user.userid
        )
    )
    card = result.scalar_one_or_none()
    
    if not card:
        raise HTTPException(status_code=404, detail="卡片不存在")
    
    await db.delete(card)
    await db.commit()
    
    return ResponseModel(code=200, message="删除成功")


# ==================== 时间追踪 ====================

@router.post("/{card_id}/start")
async def start_card(
    card_id: int,
    current_user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db)
):
    """开始卡片任务（记录开始时间）"""
    result = await db.execute(
        select(Card).where(
            Card.id == card_id,
            Card.userid == current_user.userid
        )
    )
    card = result.scalar_one_or_none()
    
    if not card:
        raise HTTPException(status_code=404, detail="卡片不存在")
    
    if card.begintime:
        raise HTTPException(status_code=400, detail="任务已在进行中")
    
    card.begintime = datetime.now()
    card.updatetime = datetime.now()
    await db.commit()
    
    return ResponseModel(
        code=200,
        message="任务已开始",
        data={"begintime": card.begintime.isoformat()}
    )


@router.post("/{card_id}/stop")
async def stop_card(
    card_id: int,
    current_user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db)
):
    """暂停卡片任务（记录用时但不完成）"""
    result = await db.execute(
        select(Card).where(
            Card.id == card_id,
            Card.userid == current_user.userid
        )
    )
    card = result.scalar_one_or_none()
    
    if not card:
        raise HTTPException(status_code=404, detail="卡片不存在")
    
    if not card.begintime:
        raise HTTPException(status_code=400, detail="任务尚未开始")
    
    # 计算本次用时并累加
    elapsed = int((datetime.now() - card.begintime).total_seconds())
    card.usedtime = (card.usedtime or 0) + elapsed
    card.endtime = datetime.now()
    card.begintime = None  # 重置开始时间，允许再次开始
    card.updatetime = datetime.now()
    await db.commit()
    
    return ResponseModel(
        code=200,
        message="任务已暂停",
        data={
            "elapsed": elapsed,
            "total_time": card.usedtime
        }
    )


@router.post("/{card_id}/complete")
async def complete_card(
    card_id: int,
    current_user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db)
):
    """完成卡片任务"""
    result = await db.execute(
        select(Card).where(
            Card.id == card_id,
            Card.userid == current_user.userid
        )
    )
    card = result.scalar_one_or_none()
    
    if not card:
        raise HTTPException(status_code=404, detail="卡片不存在")
    
    now = datetime.now()
    
    # 如果任务正在进行，先计算用时
    if card.begintime:
        elapsed = int((now - card.begintime).total_seconds())
        card.usedtime = (card.usedtime or 0) + elapsed
        card.endtime = now
        card.begintime = None
    
    card.donetime = now
    card.updatetime = now
    
    # 如果是重复任务，创建一个新的副本
    if card.is_repeat:
        new_card = Card(
            userid=current_user.userid,
            category_id=card.category_id,
            headline=card.headline,
            content=card.content,
            type=card.type,
            is_repeat=1,
            createtime=now,
            updatetime=now
        )
        db.add(new_card)
    
    await db.commit()
    
    return ResponseModel(
        code=200,
        message="任务已完成",
        data={
            "donetime": card.donetime.isoformat(),
            "total_time": card.usedtime
        }
    )


@router.post("/{card_id}/reopen")
async def reopen_card(
    card_id: int,
    current_user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db)
):
    """重新打开已完成的卡片"""
    result = await db.execute(
        select(Card).where(
            Card.id == card_id,
            Card.userid == current_user.userid
        )
    )
    card = result.scalar_one_or_none()
    
    if not card:
        raise HTTPException(status_code=404, detail="卡片不存在")
    
    if not card.donetime:
        raise HTTPException(status_code=400, detail="任务尚未完成")
    
    card.donetime = None
    card.updatetime = datetime.now()
    await db.commit()
    
    return ResponseModel(code=200, message="任务已重新打开")


# 统计路由已移动到文件顶部（动态路由之前）
