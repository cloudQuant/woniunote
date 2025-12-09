"""
评论 API 模块

本模块提供评论的发布、删除、列表获取以及点赞/踩等接口。
"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.comment import Comment
from app.models.article import Article
from app.models.user import User
from app.models.credit import Credit
from app.models.comment_vote import CommentVote
from app.schemas.comment import CommentCreate, CommentUpdate, CommentResponse
from app.schemas.common import ResponseModel, PaginatedResponse
from app.api.deps import get_current_user_required, get_admin_user

router = APIRouter()


@router.get("/article/{articleid}", response_model=PaginatedResponse[dict])
async def get_article_comments(
    articleid: int,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: AsyncSession = Depends(get_db)
):
    """
    获取文章的评论列表
    
    分页获取指定文章的评论列表。
    
    Args:
        articleid: 文章 ID
        page: 页码
        page_size: 每页数量
        db: 数据库会话
        
    Returns:
        PaginatedResponse[dict]: 分页的评论列表
        
    Raises:
        HTTPException(404): 文章不存在
    """
    # 检查文章是否存在
    article_result = await db.execute(
        select(Article).where(Article.articleid == articleid)
    )
    if not article_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文章不存在"
        )
    
    # 获取评论总数
    count_query = select(func.count()).select_from(Comment).where(
        Comment.articleid == articleid,
        Comment.hidden == 0
    )
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # 分页获取评论
    offset = (page - 1) * page_size
    query = select(Comment).where(
        Comment.articleid == articleid,
        Comment.hidden == 0
    ).options(
        selectinload(Comment.user)
    ).order_by(desc(Comment.createtime)).offset(offset).limit(page_size)
    
    result = await db.execute(query)
    comments = result.scalars().all()
    
    return PaginatedResponse(
        code=200,
        message="success",
        data=[CommentResponse.model_validate(c).model_dump() for c in comments],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size
    )


@router.post("/", response_model=ResponseModel[dict])
async def create_comment(
    comment_data: CommentCreate,
    request: Request,
    current_user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db)
):
    """
    创建评论
    
    发布新评论，并给予用户积分奖励。
    
    Args:
        comment_data: 评论创建数据
        request: 请求对象 (用于记录 IP)
        current_user: 当前已认证用户
        db: 数据库会话
        
    Returns:
        ResponseModel[dict]: 创建成功的评论信息
        
    Raises:
        HTTPException(404): 文章不存在
    """
    # 检查文章是否存在
    article_result = await db.execute(
        select(Article).where(Article.articleid == comment_data.articleid)
    )
    article = article_result.scalar_one_or_none()
    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文章不存在"
        )
    
    # 获取客户端IP
    client_ip = request.client.host if request.client else None
    
    # 创建评论
    new_comment = Comment(
        userid=current_user.userid,
        articleid=comment_data.articleid,
        content=comment_data.content,
        replyid=comment_data.replyid,
        ipaddr=client_ip,
        createtime=datetime.now(),
        updatetime=datetime.now()
    )
    
    db.add(new_comment)
    
    # 更新文章评论数
    article.replycount += 1
    
    await db.commit()
    await db.refresh(new_comment)
    
    # 添加积分记录 - 发表评论+2积分
    credit_category = "回复评论" if comment_data.replyid else "发表评论"
    credit_record = Credit(
        userid=current_user.userid,
        category=credit_category,
        target=comment_data.articleid,
        credit=2,
        createtime=datetime.now(),
        updatetime=datetime.now()
    )
    db.add(credit_record)
    
    # 更新用户积分
    current_user.credit = (current_user.credit or 0) + 2
    
    await db.commit()
    
    return ResponseModel(
        code=200,
        message="评论成功",
        data=CommentResponse.model_validate(new_comment).model_dump()
    )


@router.put("/{commentid}", response_model=ResponseModel[dict])
async def update_comment(
    commentid: int,
    comment_data: CommentUpdate,
    current_user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db)
):
    """
    更新评论
    
    Args:
        commentid: 评论 ID
        comment_data: 评论更新数据
        current_user: 当前已认证用户
        db: 数据库会话
        
    Returns:
        ResponseModel[dict]: 更新后的评论信息
        
    Raises:
        HTTPException(404): 评论不存在
        HTTPException(403): 没有权限修改此评论
    """
    result = await db.execute(
        select(Comment).where(Comment.commentid == commentid)
    )
    comment = result.scalar_one_or_none()
    
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="评论不存在"
        )
    
    # 检查权限
    if comment.userid != current_user.userid and current_user.role not in ["admin", "editor"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有权限修改此评论"
        )
    
    if comment_data.content:
        comment.content = comment_data.content
        comment.updatetime = datetime.now()
    
    await db.commit()
    await db.refresh(comment)
    
    return ResponseModel(
        code=200,
        message="更新成功",
        data=CommentResponse.model_validate(comment).model_dump()
    )


@router.delete("/{commentid}")
async def delete_comment(
    commentid: int,
    current_user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db)
):
    """
    删除评论
    
    同时减少文章的评论数。
    
    Args:
        commentid: 评论 ID
        current_user: 当前已认证用户
        db: 数据库会话
        
    Returns:
        ResponseModel: 成功消息
        
    Raises:
        HTTPException(404): 评论不存在
        HTTPException(403): 没有权限删除此评论
    """
    result = await db.execute(
        select(Comment).where(Comment.commentid == commentid)
    )
    comment = result.scalar_one_or_none()
    
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="评论不存在"
        )
    
    # 检查权限
    if comment.userid != current_user.userid and current_user.role not in ["admin", "editor"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有权限删除此评论"
        )
    
    # 更新文章评论数
    article_result = await db.execute(
        select(Article).where(Article.articleid == comment.articleid)
    )
    article = article_result.scalar_one_or_none()
    if article and article.replycount > 0:
        article.replycount -= 1
    
    await db.delete(comment)
    await db.commit()
    
    return ResponseModel(code=200, message="删除成功")


@router.post("/{commentid}/agree")
async def agree_comment(
    commentid: int,
    current_user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db)
):
    """
    点赞评论
    
    如果已经点过赞，则报错；如果之前是踩，则改为赞。
    
    Args:
        commentid: 评论 ID
        current_user: 当前已认证用户
        db: 数据库会话
        
    Returns:
        ResponseModel: 包含新的点赞/踩数
        
    Raises:
        HTTPException(404): 评论不存在
        HTTPException(400): 已经点过赞了
    """
    result = await db.execute(
        select(Comment).where(Comment.commentid == commentid)
    )
    comment = result.scalar_one_or_none()
    
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="评论不存在"
        )
    
    # 检查是否已投票
    vote_result = await db.execute(
        select(CommentVote).where(
            and_(
                CommentVote.userid == current_user.userid,
                CommentVote.commentid == commentid
            )
        )
    )
    existing_vote = vote_result.scalar_one_or_none()
    
    if existing_vote:
        if existing_vote.vote_type == 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="您已经点过赞了"
            )
        else:
            # 之前是踩，现在改为赞
            existing_vote.vote_type = 1
            comment.opposecount = max(0, comment.opposecount - 1)
            comment.agreecount += 1
    else:
        # 新投票
        new_vote = CommentVote(
            userid=current_user.userid,
            commentid=commentid,
            vote_type=1
        )
        db.add(new_vote)
        comment.agreecount += 1
    
    await db.commit()
    
    return ResponseModel(
        code=200,
        message="点赞成功",
        data={"agreecount": comment.agreecount, "opposecount": comment.opposecount}
    )


@router.post("/{commentid}/oppose")
async def oppose_comment(
    commentid: int,
    current_user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db)
):
    """
    踩评论
    
    如果已经踩过，则报错；如果之前是赞，则改为踩。
    
    Args:
        commentid: 评论 ID
        current_user: 当前已认证用户
        db: 数据库会话
        
    Returns:
        ResponseModel: 包含新的点赞/踩数
        
    Raises:
        HTTPException(404): 评论不存在
        HTTPException(400): 已经踩过了
    """
    result = await db.execute(
        select(Comment).where(Comment.commentid == commentid)
    )
    comment = result.scalar_one_or_none()
    
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="评论不存在"
        )
    
    # 检查是否已投票
    vote_result = await db.execute(
        select(CommentVote).where(
            and_(
                CommentVote.userid == current_user.userid,
                CommentVote.commentid == commentid
            )
        )
    )
    existing_vote = vote_result.scalar_one_or_none()
    
    if existing_vote:
        if existing_vote.vote_type == -1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="您已经踩过了"
            )
        else:
            # 之前是赞，现在改为踩
            existing_vote.vote_type = -1
            comment.agreecount = max(0, comment.agreecount - 1)
            comment.opposecount += 1
    else:
        # 新投票
        new_vote = CommentVote(
            userid=current_user.userid,
            commentid=commentid,
            vote_type=-1
        )
        db.add(new_vote)
        comment.opposecount += 1
    
    await db.commit()
    
    return ResponseModel(
        code=200,
        message="操作成功",
        data={"agreecount": comment.agreecount, "opposecount": comment.opposecount}
    )


@router.get("/{commentid}/vote-status")
async def get_vote_status(
    commentid: int,
    current_user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db)
):
    """
    获取当前用户对评论的投票状态
    
    Args:
        commentid: 评论 ID
        current_user: 当前已认证用户
        db: 数据库会话
        
    Returns:
        ResponseModel[dict]: 投票状态 (是否已投, 投票类型)
    """
    vote_result = await db.execute(
        select(CommentVote).where(
            and_(
                CommentVote.userid == current_user.userid,
                CommentVote.commentid == commentid
            )
        )
    )
    vote = vote_result.scalar_one_or_none()
    
    return ResponseModel(
        code=200,
        message="success",
        data={
            "voted": vote is not None,
            "vote_type": vote.vote_type if vote else None
        }
    )


@router.get("/my", response_model=PaginatedResponse[dict])
async def get_my_comments(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    current_user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db)
):
    """
    获取我的评论列表
    
    Args:
        page: 页码
        page_size: 每页数量
        current_user: 当前已认证用户
        db: 数据库会话
        
    Returns:
        PaginatedResponse[dict]: 分页的评论列表 (包含文章标题)
    """
    # 获取评论总数
    count_query = select(func.count()).select_from(Comment).where(Comment.userid == current_user.userid)
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # 分页获取评论，同时加载文章信息
    offset = (page - 1) * page_size
    query = select(Comment).where(
        Comment.userid == current_user.userid
    ).options(
        selectinload(Comment.article)
    ).order_by(desc(Comment.createtime)).offset(offset).limit(page_size)
    
    result = await db.execute(query)
    comments = result.scalars().all()
    
    # 构建响应，包含文章标题
    comment_list = []
    for c in comments:
        comment_data = CommentResponse.model_validate(c).model_dump()
        if c.article:
            comment_data["article_headline"] = c.article.headline
            comment_data["article_id"] = c.article.articleid
        comment_list.append(comment_data)
    
    return PaginatedResponse(
        code=200,
        message="success",
        data=comment_list,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size if total > 0 else 0
    )
