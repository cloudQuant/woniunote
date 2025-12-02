"""
文章服务层 - 处理文章相关业务逻辑
"""
from typing import Optional, List, Tuple
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_, delete
from sqlalchemy.orm import selectinload

from app.models.article import Article
from app.models.user import User
from app.models.comment import Comment
from app.models.favorite import Favorite
from app.core.logger import log_user_action, log_db_operation
from app.core.exceptions import (
    NotFoundException,
    ForbiddenException,
    BadRequestException
)


class ArticleService:
    """文章服务类"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_article_by_id(
        self, 
        article_id: int,
        include_author: bool = True
    ) -> Optional[Article]:
        """
        根据ID获取文章
        
        Args:
            article_id: 文章ID
            include_author: 是否包含作者信息
        """
        query = select(Article).where(Article.articleid == article_id)
        if include_author:
            query = query.options(selectinload(Article.author))
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def list_articles(
        self,
        page: int = 1,
        page_size: int = 10,
        article_type: int = None,
        keyword: str = None,
        user_id: int = None,
        include_hidden: bool = False,
        include_drafted: bool = False
    ) -> Tuple[List[Article], int]:
        """
        获取文章列表
        
        Args:
            page: 页码
            page_size: 每页数量
            article_type: 文章类型
            keyword: 搜索关键词
            user_id: 指定用户ID
            include_hidden: 是否包含隐藏文章
            include_drafted: 是否包含草稿
            
        Returns:
            (文章列表, 总数)
        """
        conditions = []
        
        if not include_hidden:
            conditions.append(Article.hidden == 0)
        if not include_drafted:
            conditions.append(Article.drafted == 0)
        if user_id:
            conditions.append(Article.userid == user_id)
        
        # 类型筛选
        if article_type:
            if article_type < 100:
                # 主类型，匹配所有子类型
                conditions.append(
                    (Article.type >= article_type * 100) & 
                    (Article.type < (article_type + 1) * 100) |
                    (Article.type == article_type)
                )
            else:
                conditions.append(Article.type == article_type)
        
        # 关键词搜索
        if keyword:
            conditions.append(Article.headline.contains(keyword))
        
        query = select(Article)
        if conditions:
            query = query.where(and_(*conditions))
        
        # 获取总数
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0
        
        # 分页
        offset = (page - 1) * page_size
        query = query.options(selectinload(Article.author))
        query = query.order_by(desc(Article.createtime)).offset(offset).limit(page_size)
        
        result = await self.db.execute(query)
        articles = result.scalars().all()
        
        return list(articles), total
    
    async def create_article(
        self,
        user: User,
        headline: str,
        content: str,
        article_type: int,
        thumbnail: str = None,
        credit: int = 0,
        drafted: int = 0
    ) -> Article:
        """
        创建文章
        
        Args:
            user: 作者
            headline: 标题
            content: 内容
            article_type: 类型
            thumbnail: 缩略图
            credit: 阅读所需积分
            drafted: 是否草稿
            
        Returns:
            新创建的文章
        """
        new_article = Article(
            userid=user.userid,
            type=article_type,
            headline=headline,
            content=content,
            thumbnail=thumbnail,
            credit=credit,
            drafted=drafted,
            createtime=datetime.now(),
            updatetime=datetime.now()
        )
        
        self.db.add(new_article)
        await self.db.commit()
        await self.db.refresh(new_article)
        
        log_user_action(user.userid, "create_article", str(new_article.articleid))
        log_db_operation("INSERT", "articles", record_id=new_article.articleid, user_id=user.userid)
        
        return new_article
    
    async def update_article(
        self,
        article_id: int,
        user: User,
        **kwargs
    ) -> Article:
        """
        更新文章
        
        Args:
            article_id: 文章ID
            user: 当前用户
            **kwargs: 要更新的字段
            
        Returns:
            更新后的文章
            
        Raises:
            NotFoundException: 文章不存在
            ForbiddenException: 没有权限
        """
        article = await self.get_article_by_id(article_id, include_author=False)
        
        if not article:
            raise NotFoundException("文章不存在")
        
        # 权限检查
        if article.userid != user.userid and user.role not in ["admin", "editor"]:
            raise ForbiddenException("没有权限修改此文章")
        
        # 更新字段
        allowed_fields = ['headline', 'content', 'type', 'thumbnail', 'credit', 'drafted']
        for field, value in kwargs.items():
            if field in allowed_fields:
                setattr(article, field, value)
        
        article.updatetime = datetime.now()
        await self.db.commit()
        await self.db.refresh(article)
        
        log_user_action(user.userid, "update_article", str(article_id))
        log_db_operation("UPDATE", "articles", record_id=article_id, user_id=user.userid)
        
        return article
    
    async def delete_article(
        self,
        article_id: int,
        user: User
    ) -> bool:
        """
        删除文章
        
        Args:
            article_id: 文章ID
            user: 当前用户
            
        Returns:
            是否成功
            
        Raises:
            NotFoundException: 文章不存在
            ForbiddenException: 没有权限
        """
        # 检查文章存在性和权限
        result = await self.db.execute(
            select(Article.userid).where(Article.articleid == article_id)
        )
        row = result.first()
        
        if not row:
            raise NotFoundException("文章不存在")
        
        owner_id = row[0]
        if owner_id != user.userid and user.role not in ["admin", "editor"]:
            raise ForbiddenException("没有权限删除此文章")
        
        # 删除关联数据
        await self.db.execute(delete(Comment).where(Comment.articleid == article_id))
        await self.db.execute(delete(Favorite).where(Favorite.articleid == article_id))
        await self.db.execute(delete(Article).where(Article.articleid == article_id))
        await self.db.commit()
        
        log_user_action(user.userid, "delete_article", str(article_id))
        log_db_operation("DELETE", "articles", record_id=article_id, user_id=user.userid)
        
        return True
    
    async def increment_read_count(self, article_id: int) -> None:
        """增加文章阅读次数"""
        article = await self.get_article_by_id(article_id, include_author=False)
        if article:
            article.readcount += 1
            await self.db.commit()
    
    async def toggle_recommend(self, article_id: int) -> int:
        """切换推荐状态"""
        article = await self.get_article_by_id(article_id, include_author=False)
        if not article:
            raise NotFoundException("文章不存在")
        
        article.recommended = 1 if article.recommended == 0 else 0
        article.updatetime = datetime.now()
        await self.db.commit()
        
        return article.recommended
    
    async def toggle_hidden(self, article_id: int) -> int:
        """切换隐藏状态"""
        article = await self.get_article_by_id(article_id, include_author=False)
        if not article:
            raise NotFoundException("文章不存在")
        
        article.hidden = 1 if article.hidden == 0 else 0
        article.updatetime = datetime.now()
        await self.db.commit()
        
        return article.hidden
