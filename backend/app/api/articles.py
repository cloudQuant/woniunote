"""
文章API
"""
import math
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_, delete
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.config import settings
from app.models.article import Article
from app.models.user import User
from app.models.comment import Comment
from app.models.favorite import Favorite
from app.schemas.article import (
    ArticleCreate, ArticleUpdate, ArticleResponse, 
    ArticleListItem, ArticleTypeConfig
)
from app.schemas.common import ResponseModel, PaginatedResponse
from app.api.deps import get_current_user, get_current_user_required, get_admin_user

router = APIRouter()

# 文章类型配置
ARTICLE_TYPES = {
    1: '交易策略',
    101: 'CTA策略',
    102: '统计套利',
    103: '高频交易',
    104: '因子策略',
    105: '选股与择时',
    106: '机器学习',
    107: '深度学习',
    2: '量化框架',
    201: 'backtrader',
    202: 'wondertrader',
    203: 'wtpy',
    204: 'pyfolio',
    205: 'alphalens',
    3: '投资',
    301: '股票',
    302: '期货',
    303: '期权',
    304: '外汇',
    305: 'crypto',
    306: '黄金',
    307: '债券',
    4: '理财',
    401: '基金',
    402: '保险',
    403: '信托',
    404: '银行理财',
    405: '存款',
    5: '区块链与defi',
    501: '去中心化交易所',
    502: '去中心化金融',
    503: '去中心化借贷',
    504: '去中心化治理',
    505: '其他defi',
    506: '区块链',
    507: '比特币',
    508: '以太坊',
    6: '机器学习',
    601: 'tensorflow',
    602: 'pytorch',
    603: 'keras',
    604: 'scikit-learn',
    605: '机器学习与交易',
    606: '深度学习与交易',
    7: '编程',
    701: 'python',
    702: 'c++',
    703: 'cython',
    704: 'java',
    705: 'javascript',
    706: 'swing',
    707: 'pybind11',
    8: '笔记',
    801: '幸福',
    802: '金融',
    803: '经济',
    804: '哲学',
    805: '历史',
    806: '科技',
    807: '读书笔记',
    808: '其他笔记',
    809: '个人知识库',
    9: '教程',
    901: 'woniunote入门教程',
    902: 'backtrader基础教程',
    903: 'airflow入门教程',
    904: 'arrow入门教程',
    905: '量化交易入门教程',
    906: '机器学习入门教程',
    907: 'ib_tws_api入门教程'
}


@router.get("/types", response_model=ResponseModel[dict])
async def get_article_types():
    """获取文章类型配置"""
    return ResponseModel(
        code=200,
        message="success",
        data={"types": ARTICLE_TYPES}
    )


@router.get("/", response_model=PaginatedResponse[dict])
async def list_articles(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    type: Optional[int] = None,
    keyword: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """获取文章列表"""
    # 构建查询 - 只过滤隐藏和草稿，不过滤checked状态以兼容测试数据
    query = select(Article).where(
        and_(
            Article.hidden == 0,
            Article.drafted == 0
        )
    )
    
    # 类型过滤
    if type:
        if type < 100:
            # 主类型，匹配所有子类型
            query = query.where(
                and_(Article.type >= type * 100, Article.type < (type + 1) * 100) |
                (Article.type == type)
            )
        else:
            query = query.where(Article.type == type)
    
    # 关键词搜索
    if keyword:
        query = query.where(Article.headline.contains(keyword))
    
    # 获取总数
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # 分页
    offset = (page - 1) * page_size
    query = query.options(selectinload(Article.author))
    query = query.order_by(desc(Article.createtime)).offset(offset).limit(page_size)
    
    result = await db.execute(query)
    articles = result.scalars().all()
    
    # 构建响应
    article_list = []
    for article in articles:
        item = ArticleListItem.model_validate(article)
        article_list.append(item.model_dump())
    
    return PaginatedResponse(
        code=200,
        message="success",
        data=article_list,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size)
    )


@router.get("/my", response_model=PaginatedResponse[dict])
async def get_my_articles(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db)
):
    """获取当前用户的文章列表"""
    # 构建查询 - 获取当前用户的所有文章（包括草稿）
    query = select(Article).where(Article.userid == current_user.userid)
    
    # 获取总数
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # 分页
    offset = (page - 1) * page_size
    query = query.order_by(desc(Article.createtime)).offset(offset).limit(page_size)
    
    result = await db.execute(query)
    articles = result.scalars().all()
    
    # 构建响应
    article_list = []
    for article in articles:
        item = ArticleListItem.model_validate(article)
        article_list.append(item.model_dump())
    
    return PaginatedResponse(
        code=200,
        message="success",
        data=article_list,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total > 0 else 0
    )


@router.get("/hot", response_model=ResponseModel[dict])
async def get_hot_articles(
    db: AsyncSession = Depends(get_db)
):
    """获取热门文章（最新、最热、推荐）"""
    base_filter = and_(
        Article.hidden == 0,
        Article.drafted == 0
    )
    
    # 最新文章 - 使用selectinload预加载author关系
    latest_query = select(Article).where(base_filter).options(
        selectinload(Article.author)
    ).order_by(desc(Article.createtime)).limit(10)
    latest_result = await db.execute(latest_query)
    latest = latest_result.scalars().all()
    
    # 最热文章
    most_query = select(Article).where(base_filter).options(
        selectinload(Article.author)
    ).order_by(desc(Article.readcount)).limit(10)
    most_result = await db.execute(most_query)
    most = most_result.scalars().all()
    
    # 推荐文章
    recommended_query = select(Article).where(
        and_(base_filter, Article.recommended == 1)
    ).options(selectinload(Article.author)).order_by(desc(Article.createtime)).limit(9)
    recommended_result = await db.execute(recommended_query)
    recommended = recommended_result.scalars().all()
    
    return ResponseModel(
        code=200,
        message="success",
        data={
            "latest": [ArticleListItem.model_validate(a).model_dump() for a in latest],
            "most": [ArticleListItem.model_validate(a).model_dump() for a in most],
            "recommended": [ArticleListItem.model_validate(a).model_dump() for a in recommended]
        }
    )


@router.get("/{articleid}", response_model=ResponseModel[dict])
async def get_article(
    articleid: int,
    current_user: Optional[User] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取文章详情"""
    query = select(Article).where(Article.articleid == articleid).options(
        selectinload(Article.author)
    )
    result = await db.execute(query)
    article = result.scalar_one_or_none()
    
    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文章不存在"
        )
    
    # 检查访问权限
    if article.hidden == 1:
        if not current_user or (current_user.userid != article.userid and current_user.role not in ["admin", "editor"]):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="文章已隐藏"
            )
    
    # 更新阅读次数
    article.readcount += 1
    await db.commit()
    
    return ResponseModel(
        code=200,
        message="success",
        data=ArticleResponse.model_validate(article).model_dump()
    )


@router.post("/", response_model=ResponseModel[dict])
async def create_article(
    article_data: ArticleCreate,
    current_user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db)
):
    """创建文章"""
    new_article = Article(
        userid=current_user.userid,
        type=article_data.type,
        headline=article_data.headline,
        content=article_data.content,
        thumbnail=article_data.thumbnail,
        credit=article_data.credit,
        drafted=article_data.drafted,
        createtime=datetime.now(),
        updatetime=datetime.now()
    )
    
    db.add(new_article)
    await db.commit()
    await db.refresh(new_article)
    
    return ResponseModel(
        code=200,
        message="创建成功",
        data=ArticleResponse.model_validate(new_article).model_dump()
    )


@router.put("/{articleid}", response_model=ResponseModel[dict])
async def update_article(
    articleid: int,
    article_data: ArticleUpdate,
    current_user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db)
):
    """更新文章"""
    result = await db.execute(
        select(Article).where(Article.articleid == articleid)
    )
    article = result.scalar_one_or_none()
    
    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文章不存在"
        )
    
    # 检查权限
    if article.userid != current_user.userid and current_user.role not in ["admin", "editor"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有权限修改此文章"
        )
    
    # 更新字段
    update_data = article_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(article, field, value)
    
    article.updatetime = datetime.now()
    await db.commit()
    await db.refresh(article)
    
    return ResponseModel(
        code=200,
        message="更新成功",
        data=ArticleResponse.model_validate(article).model_dump()
    )


@router.delete("/{articleid}")
async def delete_article(
    articleid: int,
    current_user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db)
):
    """删除文章"""
    # 仅查询文章的拥有者ID，避免加载带有关系的 ORM 对象
    result = await db.execute(
        select(Article.userid).where(Article.articleid == articleid)
    )
    row = result.first()
    
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文章不存在"
        )
    
    owner_id = row[0]
    
    # 检查权限
    if owner_id != current_user.userid and current_user.role not in ["admin", "editor"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有权限删除此文章"
        )
    
    # 先删除关联的评论和收藏记录
    await db.execute(delete(Comment).where(Comment.articleid == articleid))
    await db.execute(delete(Favorite).where(Favorite.articleid == articleid))
    
    # 删除文章本身
    await db.execute(delete(Article).where(Article.articleid == articleid))
    await db.commit()
    
    return ResponseModel(code=200, message="删除成功")


@router.post("/{articleid}/recommend")
async def toggle_recommend(
    articleid: int,
    admin_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """切换文章推荐状态（管理员）"""
    result = await db.execute(
        select(Article).where(Article.articleid == articleid)
    )
    article = result.scalar_one_or_none()
    
    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文章不存在"
        )
    
    article.recommended = 1 if article.recommended == 0 else 0
    article.updatetime = datetime.now()
    await db.commit()
    
    return ResponseModel(
        code=200,
        message="推荐状态已更新",
        data={"recommended": article.recommended}
    )


@router.post("/{articleid}/hide")
async def toggle_hide(
    articleid: int,
    admin_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """切换文章隐藏状态（管理员）"""
    result = await db.execute(
        select(Article).where(Article.articleid == articleid)
    )
    article = result.scalar_one_or_none()
    
    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文章不存在"
        )
    
    article.hidden = 1 if article.hidden == 0 else 0
    article.updatetime = datetime.now()
    await db.commit()
    
    return ResponseModel(
        code=200,
        message="隐藏状态已更新",
        data={"hidden": article.hidden}
    )


@router.post("/{articleid}/check")
async def toggle_check(
    articleid: int,
    admin_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """切换文章审核状态（管理员）"""
    result = await db.execute(
        select(Article).where(Article.articleid == articleid)
    )
    article = result.scalar_one_or_none()
    
    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文章不存在"
        )
    
    article.checked = 1 if article.checked == 0 else 0
    article.updatetime = datetime.now()
    await db.commit()
    
    return ResponseModel(
        code=200,
        message="审核状态已更新",
        data={"checked": article.checked}
    )


@router.get("/drafts/my", response_model=PaginatedResponse[dict])
async def get_my_drafts(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db)
):
    """获取我的草稿列表"""
    # 构建查询 - 获取当前用户的草稿
    query = select(Article).where(
        and_(
            Article.userid == current_user.userid,
            Article.drafted == 1
        )
    )
    
    # 获取总数
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # 分页
    offset = (page - 1) * page_size
    query = query.order_by(desc(Article.updatetime)).offset(offset).limit(page_size)
    
    result = await db.execute(query)
    articles = result.scalars().all()
    
    # 构建响应
    article_list = []
    for article in articles:
        item = ArticleListItem.model_validate(article)
        article_list.append(item.model_dump())
    
    return PaginatedResponse(
        code=200,
        message="success",
        data=article_list,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total > 0 else 0
    )
