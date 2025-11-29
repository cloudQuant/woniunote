"""
评论API
"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.comment import Comment
from app.models.article import Article
from app.models.user import User
from app.schemas.comment import CommentCreate, CommentUpdate, CommentResponse
from app.schemas.common import ResponseModel, PaginatedResponse
from app.api.deps import get_current_user_required, get_admin_user

router = APIRouter()


@router.get("/article/{articleid}", response_model=PaginatedResponse[dict])
async def get_article_comments(
    articleid: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """获取文章的评论列表"""
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
    count_query = select(func.count()).where(
        Comment.articleid == articleid,
        Comment.hidden == 0
    )
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
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
    """创建评论"""
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
    """更新评论"""
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
    """删除评论"""
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
    """点赞评论"""
    result = await db.execute(
        select(Comment).where(Comment.commentid == commentid)
    )
    comment = result.scalar_one_or_none()
    
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="评论不存在"
        )
    
    comment.agreecount += 1
    await db.commit()
    
    return ResponseModel(
        code=200,
        message="点赞成功",
        data={"agreecount": comment.agreecount}
    )


@router.post("/{commentid}/oppose")
async def oppose_comment(
    commentid: int,
    current_user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db)
):
    """踩评论"""
    result = await db.execute(
        select(Comment).where(Comment.commentid == commentid)
    )
    comment = result.scalar_one_or_none()
    
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="评论不存在"
        )
    
    comment.opposecount += 1
    await db.commit()
    
    return ResponseModel(
        code=200,
        message="操作成功",
        data={"opposecount": comment.opposecount}
    )
