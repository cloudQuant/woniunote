"""
评论服务层模块

本模块处理评论相关的业务逻辑，包括评论的发布、删除、列表获取、点赞/踩等操作。
"""
from typing import Optional, List, Tuple
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_
from sqlalchemy.orm import selectinload

from app.models.comment import Comment
from app.models.article import Article
from app.models.user import User
from app.models.credit import Credit
from app.models.comment_vote import CommentVote
from app.core.logger import log_user_action, log_db_operation
from app.core.exceptions import (
    NotFoundException,
    ForbiddenException,
    BadRequestException
)


class CommentService:
    """
    评论服务类
    
    提供评论管理的业务逻辑接口。
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_comment_by_id(self, comment_id: int) -> Optional[Comment]:
        """
        根据 ID 获取评论
        
        Args:
            comment_id: 评论 ID
            
        Returns:
            Optional[Comment]: 评论对象，如果不存在则返回 None
        """
        result = await self.db.execute(
            select(Comment).where(Comment.commentid == comment_id)
        )
        return result.scalar_one_or_none()
    
    async def get_article_comments(
        self,
        article_id: int,
        page: int = 1,
        page_size: int = 20,
        include_hidden: bool = False
    ) -> Tuple[List[Comment], int]:
        """
        获取文章评论列表
        
        Args:
            article_id: 文章 ID
            page: 页码，从 1 开始
            page_size: 每页数量
            include_hidden: 是否包含隐藏评论
            
        Returns:
            Tuple[List[Comment], int]: (评论列表, 总记录数)
        """
        conditions = [Comment.articleid == article_id]
        if not include_hidden:
            conditions.append(Comment.hidden == 0)
        
        # 获取总数
        count_query = select(func.count()).select_from(Comment).where(and_(*conditions))
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0
        
        # 分页查询
        offset = (page - 1) * page_size
        query = select(Comment).where(and_(*conditions)).options(
            selectinload(Comment.user)
        ).order_by(desc(Comment.createtime)).offset(offset).limit(page_size)
        
        result = await self.db.execute(query)
        comments = result.scalars().all()
        
        return list(comments), total
    
    async def create_comment(
        self,
        user: User,
        article_id: int,
        content: str,
        reply_id: int = 0,
        ip_addr: str = None
    ) -> Comment:
        """
        创建评论
        
        同时会更新文章的回复数，并给予用户积分奖励。
        
        Args:
            user: 评论用户对象
            article_id: 文章 ID
            content: 评论内容
            reply_id: 回复的评论 ID（0 表示不是回复）
            ip_addr: 客户端 IP 地址
            
        Returns:
            Comment: 新创建的评论对象
            
        Raises:
            NotFoundException: 文章不存在
        """
        # 检查文章是否存在
        article_result = await self.db.execute(
            select(Article).where(Article.articleid == article_id)
        )
        article = article_result.scalar_one_or_none()
        
        if not article:
            raise NotFoundException("文章不存在")
        
        # 创建评论
        new_comment = Comment(
            userid=user.userid,
            articleid=article_id,
            content=content,
            replyid=reply_id,
            ipaddr=ip_addr,
            createtime=datetime.now(),
            updatetime=datetime.now()
        )
        
        self.db.add(new_comment)
        
        # 更新文章评论数
        article.replycount += 1
        
        await self.db.commit()
        await self.db.refresh(new_comment)
        
        # 添加积分记录
        credit_category = "回复评论" if reply_id else "发表评论"
        credit_record = Credit(
            userid=user.userid,
            category=credit_category,
            target=article_id,
            credit=2,
            createtime=datetime.now(),
            updatetime=datetime.now()
        )
        self.db.add(credit_record)
        
        # 更新用户积分
        user.credit = (user.credit or 0) + 2
        
        await self.db.commit()
        
        log_user_action(user.userid, "create_comment", str(article_id), {"comment_id": new_comment.commentid})
        log_db_operation("INSERT", "comments", record_id=new_comment.commentid, user_id=user.userid)
        
        return new_comment
    
    async def delete_comment(
        self,
        comment_id: int,
        user: User
    ) -> bool:
        """
        删除评论
        
        同时会减少文章的回复数。
        
        Args:
            comment_id: 评论 ID
            user: 当前用户对象 (用于权限检查)
            
        Returns:
            bool: 是否删除成功
            
        Raises:
            NotFoundException: 评论不存在
            ForbiddenException: 没有权限删除此评论
        """
        comment = await self.get_comment_by_id(comment_id)
        
        if not comment:
            raise NotFoundException("评论不存在")
        
        if comment.userid != user.userid and user.role not in ["admin", "editor"]:
            raise ForbiddenException("没有权限删除此评论")
        
        # 更新文章评论数
        article_result = await self.db.execute(
            select(Article).where(Article.articleid == comment.articleid)
        )
        article = article_result.scalar_one_or_none()
        if article and article.replycount > 0:
            article.replycount -= 1
        
        await self.db.delete(comment)
        await self.db.commit()
        
        log_user_action(user.userid, "delete_comment", str(comment_id))
        log_db_operation("DELETE", "comments", record_id=comment_id, user_id=user.userid)
        
        return True
    
    async def vote_comment(
        self,
        comment_id: int,
        user: User,
        vote_type: int  # 1: 赞, -1: 踩
    ) -> Tuple[int, int]:
        """
        对评论投票（点赞/踩）
        
        Args:
            comment_id: 评论 ID
            user: 投票用户对象
            vote_type: 投票类型 (1: 赞, -1: 踩)
            
        Returns:
            Tuple[int, int]: (新的点赞数, 新的反对数)
            
        Raises:
            NotFoundException: 评论不存在
            BadRequestException: 已经投过相同的票
        """
        comment = await self.get_comment_by_id(comment_id)
        
        if not comment:
            raise NotFoundException("评论不存在")
        
        # 检查是否已投票
        vote_result = await self.db.execute(
            select(CommentVote).where(
                and_(
                    CommentVote.userid == user.userid,
                    CommentVote.commentid == comment_id
                )
            )
        )
        existing_vote = vote_result.scalar_one_or_none()
        
        if existing_vote:
            if existing_vote.vote_type == vote_type:
                action = "点赞" if vote_type == 1 else "踩"
                raise BadRequestException(f"您已经{action}过了")
            else:
                # 改变投票
                existing_vote.vote_type = vote_type
                if vote_type == 1:
                    comment.opposecount = max(0, comment.opposecount - 1)
                    comment.agreecount += 1
                else:
                    comment.agreecount = max(0, comment.agreecount - 1)
                    comment.opposecount += 1
        else:
            # 新投票
            new_vote = CommentVote(
                userid=user.userid,
                commentid=comment_id,
                vote_type=vote_type
            )
            self.db.add(new_vote)
            
            if vote_type == 1:
                comment.agreecount += 1
            else:
                comment.opposecount += 1
        
        await self.db.commit()
        
        action = "agree" if vote_type == 1 else "oppose"
        log_user_action(user.userid, f"vote_comment_{action}", str(comment_id))
        
        return comment.agreecount, comment.opposecount
