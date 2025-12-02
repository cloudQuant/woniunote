"""
待办事项API
"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_

from app.core.database import get_db
from app.models.todo import TodoCategory, TodoItem
from app.models.user import User
from app.schemas.todo import (
    TodoCategoryCreate, TodoCategoryUpdate, TodoCategoryResponse,
    TodoItemCreate, TodoItemUpdate, TodoItemResponse, TodoItemWithCategory
)
from app.schemas.common import ResponseModel, PaginatedResponse
from app.api.deps import get_current_user_required

router = APIRouter()


# ==================== 分类管理 ====================

@router.get("/categories", response_model=ResponseModel[list])
async def get_categories(
    current_user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db)
):
    """获取所有分类"""
    query = select(TodoCategory).where(
        TodoCategory.userid == current_user.userid
    ).order_by(TodoCategory.sort_order, TodoCategory.id)
    
    result = await db.execute(query)
    categories = result.scalars().all()
    
    return ResponseModel(
        code=200,
        message="success",
        data=[TodoCategoryResponse.model_validate(c).model_dump() for c in categories]
    )


@router.post("/categories", response_model=ResponseModel[dict])
async def create_category(
    data: TodoCategoryCreate,
    current_user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db)
):
    """创建分类"""
    new_category = TodoCategory(
        userid=current_user.userid,
        name=data.name,
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
        data=TodoCategoryResponse.model_validate(new_category).model_dump()
    )


@router.put("/categories/{category_id}", response_model=ResponseModel[dict])
async def update_category(
    category_id: int,
    data: TodoCategoryUpdate,
    current_user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db)
):
    """更新分类"""
    result = await db.execute(
        select(TodoCategory).where(
            TodoCategory.id == category_id,
            TodoCategory.userid == current_user.userid
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
        data=TodoCategoryResponse.model_validate(category).model_dump()
    )


@router.delete("/categories/{category_id}")
async def delete_category(
    category_id: int,
    current_user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db)
):
    """删除分类（同时删除该分类下的所有待办事项）"""
    result = await db.execute(
        select(TodoCategory).where(
            TodoCategory.id == category_id,
            TodoCategory.userid == current_user.userid
        )
    )
    category = result.scalar_one_or_none()
    
    if not category:
        raise HTTPException(status_code=404, detail="分类不存在")
    
    await db.delete(category)
    await db.commit()
    
    return ResponseModel(code=200, message="删除成功")


# ==================== 待办事项管理 ====================

@router.get("/items", response_model=PaginatedResponse[dict])
async def get_items(
    category_id: int = Query(None),
    done: int = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db)
):
    """获取待办事项列表"""
    # 构建查询
    conditions = [TodoItem.userid == current_user.userid]
    
    if category_id is not None:
        conditions.append(TodoItem.category_id == category_id)
    if done is not None:
        conditions.append(TodoItem.done == done)
    
    query = select(TodoItem).where(and_(*conditions))
    
    # 获取总数
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # 分页并排序
    offset = (page - 1) * page_size
    query = query.order_by(
        TodoItem.done,  # 未完成的在前
        desc(TodoItem.priority),  # 高优先级在前
        desc(TodoItem.createtime)
    ).offset(offset).limit(page_size)
    
    result = await db.execute(query)
    items = result.scalars().all()
    
    return PaginatedResponse(
        code=200,
        message="success",
        data=[TodoItemResponse.model_validate(i).model_dump() for i in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size if total > 0 else 0
    )


@router.post("/items", response_model=ResponseModel[dict])
async def create_item(
    data: TodoItemCreate,
    current_user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db)
):
    """创建待办事项"""
    # 验证分类归属
    category_result = await db.execute(
        select(TodoCategory).where(
            TodoCategory.id == data.category_id,
            TodoCategory.userid == current_user.userid
        )
    )
    if not category_result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="分类不存在或无权访问")
    
    new_item = TodoItem(
        userid=current_user.userid,
        category_id=data.category_id,
        body=data.body,
        priority=data.priority or 0,
        due_date=data.due_date,
        createtime=datetime.now(),
        updatetime=datetime.now()
    )
    db.add(new_item)
    await db.commit()
    await db.refresh(new_item)
    
    return ResponseModel(
        code=200,
        message="创建成功",
        data=TodoItemResponse.model_validate(new_item).model_dump()
    )


@router.put("/items/{item_id}", response_model=ResponseModel[dict])
async def update_item(
    item_id: int,
    data: TodoItemUpdate,
    current_user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db)
):
    """更新待办事项"""
    result = await db.execute(
        select(TodoItem).where(
            TodoItem.id == item_id,
            TodoItem.userid == current_user.userid
        )
    )
    item = result.scalar_one_or_none()
    
    if not item:
        raise HTTPException(status_code=404, detail="待办事项不存在")
    
    # 如果更新分类，验证新分类归属
    if data.category_id is not None and data.category_id != item.category_id:
        category_result = await db.execute(
            select(TodoCategory).where(
                TodoCategory.id == data.category_id,
                TodoCategory.userid == current_user.userid
            )
        )
        if not category_result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="目标分类不存在或无权访问")
    
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(item, field, value)
    
    item.updatetime = datetime.now()
    await db.commit()
    await db.refresh(item)
    
    return ResponseModel(
        code=200,
        message="更新成功",
        data=TodoItemResponse.model_validate(item).model_dump()
    )


@router.post("/items/{item_id}/toggle")
async def toggle_item(
    item_id: int,
    current_user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db)
):
    """切换待办事项完成状态"""
    result = await db.execute(
        select(TodoItem).where(
            TodoItem.id == item_id,
            TodoItem.userid == current_user.userid
        )
    )
    item = result.scalar_one_or_none()
    
    if not item:
        raise HTTPException(status_code=404, detail="待办事项不存在")
    
    item.done = 1 if item.done == 0 else 0
    item.donetime = datetime.now() if item.done == 1 else None
    item.updatetime = datetime.now()
    await db.commit()
    
    return ResponseModel(
        code=200,
        message="已完成" if item.done else "已恢复",
        data={"done": item.done, "donetime": item.donetime.isoformat() if item.donetime else None}
    )


@router.delete("/items/{item_id}")
async def delete_item(
    item_id: int,
    current_user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db)
):
    """删除待办事项"""
    result = await db.execute(
        select(TodoItem).where(
            TodoItem.id == item_id,
            TodoItem.userid == current_user.userid
        )
    )
    item = result.scalar_one_or_none()
    
    if not item:
        raise HTTPException(status_code=404, detail="待办事项不存在")
    
    await db.delete(item)
    await db.commit()
    
    return ResponseModel(code=200, message="删除成功")


@router.get("/stats", response_model=ResponseModel[dict])
async def get_stats(
    current_user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db)
):
    """获取待办事项统计"""
    base_filter = TodoItem.userid == current_user.userid
    
    # 总数
    total_result = await db.execute(
        select(func.count()).select_from(TodoItem).where(base_filter)
    )
    total = total_result.scalar() or 0
    
    # 已完成
    done_result = await db.execute(
        select(func.count()).select_from(TodoItem).where(and_(base_filter, TodoItem.done == 1))
    )
    done = done_result.scalar() or 0
    
    # 未完成
    pending = total - done
    
    # 按分类统计
    category_stats = []
    categories_result = await db.execute(
        select(TodoCategory).where(TodoCategory.userid == current_user.userid)
    )
    categories = categories_result.scalars().all()
    
    for cat in categories:
        cat_total = await db.execute(
            select(func.count()).select_from(TodoItem).where(
                and_(base_filter, TodoItem.category_id == cat.id)
            )
        )
        cat_done = await db.execute(
            select(func.count()).select_from(TodoItem).where(
                and_(base_filter, TodoItem.category_id == cat.id, TodoItem.done == 1)
            )
        )
        category_stats.append({
            "id": cat.id,
            "name": cat.name,
            "total": cat_total.scalar() or 0,
            "done": cat_done.scalar() or 0
        })
    
    return ResponseModel(
        code=200,
        message="success",
        data={
            "total": total,
            "done": done,
            "pending": pending,
            "categories": category_stats
        }
    )
