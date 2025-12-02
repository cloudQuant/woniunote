"""
积分API
"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from app.core.database import get_db
from app.models.credit import Credit
from app.models.user import User
from app.schemas.credit import CreditResponse, CreditSummary
from app.schemas.common import ResponseModel, PaginatedResponse
from app.api.deps import get_current_user_required

router = APIRouter()


# 积分类型常量
class CreditType:
    REGISTER = "用户注册"
    LOGIN = "每日登录"
    POST_ARTICLE = "发布文章"
    POST_COMMENT = "发表评论"
    REPLY_COMMENT = "回复评论"
    READ_ARTICLE = "阅读文章"
    RECEIVE_COMMENT = "收到评论"
    
# 积分值配置
CREDIT_VALUES = {
    CreditType.REGISTER: 50,
    CreditType.LOGIN: 1,
    CreditType.POST_ARTICLE: 10,
    CreditType.POST_COMMENT: 2,
    CreditType.REPLY_COMMENT: 2,
    CreditType.READ_ARTICLE: -1,  # 消耗积分
    CreditType.RECEIVE_COMMENT: 1,
}


async def add_credit(
    db: AsyncSession,
    userid: int,
    category: str,
    target: int = None,
    credit: int = None
) -> Credit:
    """添加积分记录并更新用户积分"""
    # 如果未指定积分值，从配置中获取
    if credit is None:
        credit = CREDIT_VALUES.get(category, 0)
    
    # 创建积分记录
    new_credit = Credit(
        userid=userid,
        category=category,
        target=target,
        credit=credit,
        createtime=datetime.now(),
        updatetime=datetime.now()
    )
    db.add(new_credit)
    
    # 更新用户积分
    result = await db.execute(select(User).where(User.userid == userid))
    user = result.scalar_one_or_none()
    if user:
        user.credit = (user.credit or 0) + credit
    
    await db.commit()
    await db.refresh(new_credit)
    return new_credit


async def check_payed_article(
    db: AsyncSession,
    userid: int,
    articleid: int
) -> bool:
    """检查用户是否已支付阅读该文章"""
    result = await db.execute(
        select(Credit).where(
            Credit.userid == userid,
            Credit.category == CreditType.READ_ARTICLE,
            Credit.target == articleid
        )
    )
    return result.scalar_one_or_none() is not None


@router.get("/", response_model=PaginatedResponse[dict])
async def get_my_credits(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db)
):
    """获取我的积分记录"""
    # 获取总数
    count_query = select(func.count()).select_from(Credit).where(Credit.userid == current_user.userid)
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # 分页查询
    offset = (page - 1) * page_size
    query = select(Credit).where(
        Credit.userid == current_user.userid
    ).order_by(desc(Credit.createtime)).offset(offset).limit(page_size)
    
    result = await db.execute(query)
    credits = result.scalars().all()
    
    return PaginatedResponse(
        code=200,
        message="success",
        data=[CreditResponse.model_validate(c).model_dump() for c in credits],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size if total > 0 else 0
    )


@router.get("/summary", response_model=ResponseModel[dict])
async def get_credit_summary(
    current_user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db)
):
    """获取积分汇总"""
    # 获取当前积分
    total_credit = current_user.credit or 0
    
    # 获取最近10条记录
    query = select(Credit).where(
        Credit.userid == current_user.userid
    ).order_by(desc(Credit.createtime)).limit(10)
    
    result = await db.execute(query)
    recent_credits = result.scalars().all()
    
    # 按类型统计
    type_stats_query = select(
        Credit.category,
        func.sum(Credit.credit).label("total"),
        func.count().label("count")
    ).where(
        Credit.userid == current_user.userid
    ).group_by(Credit.category)
    
    type_result = await db.execute(type_stats_query)
    type_stats = {row[0]: {"total": row[1], "count": row[2]} for row in type_result.all()}
    
    return ResponseModel(
        code=200,
        message="success",
        data={
            "total_credit": total_credit,
            "recent_credits": [CreditResponse.model_validate(c).model_dump() for c in recent_credits],
            "type_stats": type_stats
        }
    )


@router.post("/pay-article/{articleid}", response_model=ResponseModel[dict])
async def pay_for_article(
    articleid: int,
    current_user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db)
):
    """支付积分阅读文章"""
    from app.models.article import Article
    
    # 检查文章是否存在
    article_result = await db.execute(
        select(Article).where(Article.articleid == articleid)
    )
    article = article_result.scalar_one_or_none()
    
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")
    
    # 检查文章是否需要积分
    if article.credit <= 0:
        return ResponseModel(
            code=200,
            message="该文章免费阅读",
            data={"paid": False, "required_credit": 0}
        )
    
    # 检查是否已支付
    if await check_payed_article(db, current_user.userid, articleid):
        return ResponseModel(
            code=200,
            message="已支付过",
            data={"paid": True, "required_credit": article.credit}
        )
    
    # 检查积分是否足够
    if current_user.credit < article.credit:
        raise HTTPException(
            status_code=400,
            detail=f"积分不足，需要{article.credit}积分，当前只有{current_user.credit}积分"
        )
    
    # 扣除积分
    remaining = (current_user.credit or 0) - article.credit
    await add_credit(
        db=db,
        userid=current_user.userid,
        category=CreditType.READ_ARTICLE,
        target=articleid,
        credit=-article.credit
    )
    
    return ResponseModel(
        code=200,
        message="支付成功",
        data={
            "paid": True,
            "required_credit": article.credit,
            "remaining_credit": remaining
        }
    )


@router.get("/check-article/{articleid}", response_model=ResponseModel[dict])
async def check_article_payment(
    articleid: int,
    current_user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db)
):
    """检查是否已支付文章"""
    from app.models.article import Article
    
    # 检查文章
    article_result = await db.execute(
        select(Article).where(Article.articleid == articleid)
    )
    article = article_result.scalar_one_or_none()
    
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")
    
    # 文章作者无需支付
    if article.userid == current_user.userid:
        return ResponseModel(
            code=200,
            message="success",
            data={"paid": True, "is_owner": True, "required_credit": 0}
        )
    
    # 免费文章
    if article.credit <= 0:
        return ResponseModel(
            code=200,
            message="success",
            data={"paid": True, "is_free": True, "required_credit": 0}
        )
    
    # 检查支付状态
    paid = await check_payed_article(db, current_user.userid, articleid)
    
    return ResponseModel(
        code=200,
        message="success",
        data={
            "paid": paid,
            "required_credit": article.credit,
            "user_credit": current_user.credit
        }
    )
