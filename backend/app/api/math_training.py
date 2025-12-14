"""
Math Training API - 数学训练相关接口
"""
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.api.deps import get_current_user_required
from app.models.user import User
from app.models.math_training import MathTrainingRecord, MathTrainingWrongAnswer
from app.schemas.math_training import (
    MathTrainingRecordCreate,
    MathTrainingRecordResponse,
    MathTrainingRecordListItem,
    WrongAnswerResponse,
    MathTrainingSummary,
)
from app.schemas.common import ResponseModel, PaginatedResponse

router = APIRouter(prefix="/math-training", tags=["math-training"])


@router.post("/records", response_model=ResponseModel[MathTrainingRecordResponse])
async def create_training_record(
    data: MathTrainingRecordCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_required),
):
    """创建训练记录（含错题）"""
    # 创建训练记录
    record = MathTrainingRecord(
        user_id=current_user.userid,
        difficulty=data.difficulty,
        total_questions=data.total_questions,
        correct_count=data.correct_count,
        wrong_count=data.wrong_count,
        accuracy=data.accuracy,
        start_time=data.start_time,
        end_time=data.end_time,
        duration_seconds=data.duration_seconds,
    )
    db.add(record)
    await db.flush()  # 获取 record.id

    # 创建错题记录
    for wrong in data.wrong_answers:
        wrong_answer = MathTrainingWrongAnswer(
            record_id=record.id,
            user_id=current_user.userid,
            question=wrong.question,
            correct_answer=wrong.correct_answer,
            user_answer=wrong.user_answer,
            operation=wrong.operation,
            difficulty=data.difficulty,
        )
        db.add(wrong_answer)

    await db.commit()
    await db.refresh(record)

    # 重新查询以获取关联的错题
    result = await db.execute(
        select(MathTrainingRecord)
        .options(selectinload(MathTrainingRecord.wrong_answers))
        .where(MathTrainingRecord.id == record.id)
    )
    record = result.scalar_one()

    return ResponseModel(data=MathTrainingRecordResponse.model_validate(record))


@router.get("/records", response_model=PaginatedResponse[MathTrainingRecordListItem])
async def get_training_records(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量"),
    difficulty: Optional[int] = Query(None, ge=1, le=3, description="筛选难度级别"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_required),
):
    """获取用户训练记录列表（分页）"""
    # 构建查询
    query = select(MathTrainingRecord).where(
        MathTrainingRecord.user_id == current_user.userid
    )
    count_query = select(func.count()).select_from(MathTrainingRecord).where(
        MathTrainingRecord.user_id == current_user.userid
    )

    if difficulty is not None:
        query = query.where(MathTrainingRecord.difficulty == difficulty)
        count_query = count_query.where(MathTrainingRecord.difficulty == difficulty)

    # 获取总数
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # 分页查询
    query = query.order_by(desc(MathTrainingRecord.created_at))
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    records = result.scalars().all()

    items = [MathTrainingRecordListItem.model_validate(r) for r in records]

    return PaginatedResponse(
        data=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/records/{record_id}", response_model=ResponseModel[MathTrainingRecordResponse])
async def get_training_record_detail(
    record_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_required),
):
    """获取单个训练记录详情（含错题）"""
    result = await db.execute(
        select(MathTrainingRecord)
        .options(selectinload(MathTrainingRecord.wrong_answers))
        .where(
            MathTrainingRecord.id == record_id,
            MathTrainingRecord.user_id == current_user.userid,
        )
    )
    record = result.scalar_one_or_none()

    if not record:
        return ResponseModel(code=404, message="训练记录不存在")

    return ResponseModel(data=MathTrainingRecordResponse.model_validate(record))


@router.get("/wrong-answers", response_model=PaginatedResponse[WrongAnswerResponse])
async def get_wrong_answers(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    difficulty: Optional[int] = Query(None, ge=1, le=3, description="筛选难度级别"),
    operation: Optional[str] = Query(None, description="筛选运算类型: +, -, *, /"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_required),
):
    """获取用户所有错题（分页）"""
    query = select(MathTrainingWrongAnswer).where(
        MathTrainingWrongAnswer.user_id == current_user.userid
    )
    count_query = select(func.count()).select_from(MathTrainingWrongAnswer).where(
        MathTrainingWrongAnswer.user_id == current_user.userid
    )

    if difficulty is not None:
        query = query.where(MathTrainingWrongAnswer.difficulty == difficulty)
        count_query = count_query.where(MathTrainingWrongAnswer.difficulty == difficulty)

    if operation is not None:
        query = query.where(MathTrainingWrongAnswer.operation == operation)
        count_query = count_query.where(MathTrainingWrongAnswer.operation == operation)

    # 获取总数
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # 分页查询
    query = query.order_by(desc(MathTrainingWrongAnswer.created_at))
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    wrong_answers = result.scalars().all()

    items = [WrongAnswerResponse.model_validate(w) for w in wrong_answers]

    return PaginatedResponse(
        data=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/summary", response_model=ResponseModel[MathTrainingSummary])
async def get_training_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_required),
):
    """获取用户训练统计摘要"""
    result = await db.execute(
        select(
            func.count(MathTrainingRecord.id).label("total_sessions"),
            func.coalesce(func.sum(MathTrainingRecord.total_questions), 0).label("total_questions"),
            func.coalesce(func.sum(MathTrainingRecord.correct_count), 0).label("total_correct"),
            func.coalesce(func.sum(MathTrainingRecord.wrong_count), 0).label("total_wrong"),
            func.coalesce(func.sum(MathTrainingRecord.duration_seconds), 0).label("total_duration"),
        ).where(MathTrainingRecord.user_id == current_user.userid)
    )
    row = result.one()

    total_sessions = row.total_sessions or 0
    total_questions = row.total_questions or 0
    total_correct = row.total_correct or 0
    total_wrong = row.total_wrong or 0
    total_duration = row.total_duration or 0

    average_accuracy = (total_correct / total_questions * 100) if total_questions > 0 else 0.0

    return ResponseModel(
        data=MathTrainingSummary(
            total_sessions=total_sessions,
            total_questions=total_questions,
            total_correct=total_correct,
            total_wrong=total_wrong,
            average_accuracy=round(average_accuracy, 2),
            total_duration_seconds=total_duration,
        )
    )
