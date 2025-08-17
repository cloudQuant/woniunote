"""
文章服务模块
优化数据库查询性能，消除 N+1 查询问题
"""
import time
import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy import desc, asc, and_, or_
from woniunote.common.database import dbconnect
from woniunote.common.create_database import Article, User
from woniunote.common.cache_utils import cached
from woniunote.common.simple_logger import get_simple_logger

# 获取数据库连接
dbsession, md, DBase = dbconnect()

# 创建日志记录器
logger = get_simple_logger('article_service')

class ArticleService:
    """优化的文章服务类"""
    
    def __init__(self):
        self.dbsession = dbsession
    
    @cached(ttl=300)  # 缓存5分钟
    def get_articles_with_users(self, limit: int = 10, offset: int = 0, 
                               include_hidden: bool = False) -> List[Dict[str, Any]]:
        """
        获取文章列表，包含用户信息，使用预加载避免 N+1 查询
        
        Args:
            limit: 限制数量
            offset: 偏移量
            include_hidden: 是否包含隐藏文章
            
        Returns:
            文章列表，包含用户信息
        """
        try:
            start_time = time.time()
            
            # 构建查询，使用 joinedload 预加载用户信息
            query = (
                self.dbsession.query(Article, User)
                .join(User, Article.userid == User.userid)
                .order_by(desc(Article.createtime))
            )
            
            # 过滤条件
            if not include_hidden:
                query = query.filter(Article.hidden == 0)
            
            # 应用分页
            articles = query.offset(offset).limit(limit).all()
            
            # 转换为字典格式
            result = []
            for article, user in articles:
                article_dict = {
                    'articleid': article.articleid,
                    'userid': article.userid,
                    'type': article.type,
                    'headline': article.headline,
                    'content': article.content[:200] + '...' if article.content and len(article.content) > 200 else (article.content or ''),
                    'thumbnail': article.thumbnail,
                    'credit': article.credit,
                    'readcount': article.readcount,
                    'replycount': article.replycount,
                    'recommended': article.recommended,
                    'hidden': article.hidden,
                    'drafted': article.drafted,
                    'checked': article.checked,
                    'createtime': article.createtime,
                    'updatetime': article.updatetime,
                    # 用户信息（已预加载，不会产生额外查询）
                    'author': {
                        'userid': user.userid,
                        'username': user.username,
                        'nickname': user.nickname,
                        'avatar': getattr(user, 'avatar', None),
                        'role': getattr(user, 'role', None)
                    } if user else None
                }
                result.append(article_dict)
            
            query_time = time.time() - start_time
            logger.info(f"获取文章列表成功: {len(result)}篇文章, 查询时间: {query_time:.3f}秒")
            
            return result
            
        except Exception as e:
            logger.error(f"获取文章列表失败: {str(e)}")
            return []
    
    @cached(ttl=600)  # 缓存10分钟
    def get_homepage_articles(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        获取首页文章数据，包括最新、最多阅读、推荐文章
        使用单次查询获取所有数据，避免多次数据库访问
        """
        try:
            start_time = time.time()
            
            # 单次查询获取所有需要的文章
            articles = (
                self.dbsession.query(Article, User)
                .join(User, Article.userid == User.userid)
                .filter(and_(Article.hidden == 0, Article.checked == 1))
                .order_by(desc(Article.createtime))
                .limit(50)  # 获取最近50篇文章用于分类
                .all()
            )
            
            # 在内存中分类，避免多次数据库查询
            latest_articles = []
            most_read_articles = []
            recommended_articles = []
            
            # 按创建时间排序的最新文章
            sorted_by_time = sorted(articles, key=lambda x: x[0].createtime, reverse=True)
            latest_articles = self._format_articles_with_users(sorted_by_time[:10])
            
            # 按阅读量排序的热门文章
            sorted_by_reads = sorted(articles, key=lambda x: x[0].readcount, reverse=True)
            most_read_articles = self._format_articles_with_users(sorted_by_reads[:10])
            
            # 推荐文章
            recommended = [(a, u) for a, u in articles if a.recommended == 1]
            recommended_articles = self._format_articles_with_users(recommended[:10])
            
            result = {
                'latest': latest_articles,
                'most_read': most_read_articles,
                'recommended': recommended_articles
            }
            
            query_time = time.time() - start_time
            logger.info(f"获取首页文章成功, 查询时间: {query_time:.3f}秒")
            
            return result
            
        except Exception as e:
            logger.error(f"获取首页文章失败: {str(e)}")
            return {'latest': [], 'most_read': [], 'recommended': []}
    
    def _format_articles_with_users(self, articles_with_users: List[tuple]) -> List[Dict[str, Any]]:
        """格式化文章数据（包含用户信息）"""
        result = []
        for article, user in articles_with_users:
            article_dict = {
                'articleid': article.articleid,
                'userid': article.userid,
                'type': article.type,
                'headline': article.headline,
                'content': article.content[:100] + '...' if article.content and len(article.content) > 100 else (article.content or ''),
                'thumbnail': article.thumbnail,
                'credit': article.credit,
                'readcount': article.readcount,
                'replycount': article.replycount,
                'recommended': article.recommended,
                'createtime': article.createtime,
                'author': {
                    'userid': user.userid,
                    'username': user.username,
                    'nickname': user.nickname,
                    'avatar': getattr(user, 'avatar', None)
                } if user else {}
            }
            result.append(article_dict)
        return result
        
    def _format_articles(self, articles: List[Article]) -> List[Dict[str, Any]]:
        """格式化文章数据（不包含用户信息）"""
        result = []
        for article in articles:
            article_dict = {
                'articleid': article.articleid,
                'userid': article.userid,
                'type': article.type,
                'headline': article.headline,
                'content': article.content[:100] + '...' if article.content and len(article.content) > 100 else (article.content or ''),
                'thumbnail': article.thumbnail,
                'credit': article.credit,
                'readcount': article.readcount,
                'replycount': article.replycount,
                'recommended': article.recommended,
                'createtime': article.createtime
            }
            result.append(article_dict)
        return result
    
    def get_article_by_id(self, article_id: int, include_user: bool = True) -> Optional[Dict[str, Any]]:
        """
        根据ID获取文章详情
        
        Args:
            article_id: 文章ID
            include_user: 是否包含用户信息
            
        Returns:
            文章详情或None
        """
        try:
            if include_user:
                # 查询文章和用户信息
                result_tuple = (
                    self.dbsession.query(Article, User)
                    .join(User, Article.userid == User.userid)
                    .filter(Article.articleid == article_id)
                    .first()
                )
                
                if not result_tuple:
                    return None
                    
                article, user = result_tuple
                
                result = {
                    'articleid': article.articleid,
                    'userid': article.userid,
                    'type': article.type,
                    'headline': article.headline,
                    'content': article.content,
                    'thumbnail': article.thumbnail,
                    'credit': article.credit,
                    'readcount': article.readcount,
                    'replycount': article.replycount,
                    'recommended': article.recommended,
                    'hidden': article.hidden,
                    'drafted': article.drafted,
                    'checked': article.checked,
                    'createtime': article.createtime,
                    'updatetime': article.updatetime,
                    'author': {
                        'userid': user.userid,
                        'username': user.username,
                        'nickname': user.nickname,
                        'avatar': getattr(user, 'avatar', None),
                        'role': getattr(user, 'role', None)
                    } if user else {}
                }
            else:
                # 只查询文章信息
                article = self.dbsession.query(Article).filter(Article.articleid == article_id).first()
                
                if not article:
                    return None
                
                result = {
                    'articleid': article.articleid,
                    'userid': article.userid,
                    'type': article.type,
                    'headline': article.headline,
                    'content': article.content,
                    'thumbnail': article.thumbnail,
                    'credit': article.credit,
                    'readcount': article.readcount,
                    'replycount': article.replycount,
                    'recommended': article.recommended,
                    'hidden': article.hidden,
                    'drafted': article.drafted,
                    'checked': article.checked,
                    'createtime': article.createtime,
                    'updatetime': article.updatetime
                }
            
            return result
            
        except Exception as e:
            logger.error(f"获取文章详情失败 (ID: {article_id}): {str(e)}")
            return None
    
    @cached(ttl=1800)  # 缓存30分钟
    def get_articles_by_type(self, article_type: int, limit: int = 20) -> List[Dict[str, Any]]:
        """
        根据类型获取文章列表
        
        Args:
            article_type: 文章类型
            limit: 限制数量
            
        Returns:
            文章列表
        """
        try:
            articles_with_users = (
                self.dbsession.query(Article, User)
                .join(User, Article.userid == User.userid)
                .filter(and_(
                    Article.type == article_type,
                    Article.hidden == 0,
                    Article.checked == 1
                ))
                .order_by(desc(Article.createtime))
                .limit(limit)
                .all()
            )
            
            return self._format_articles_with_users(articles_with_users)
            
        except Exception as e:
            logger.error(f"根据类型获取文章失败 (type: {article_type}): {str(e)}")
            return []
    
    def search_articles(self, keyword: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        搜索文章
        
        Args:
            keyword: 搜索关键词
            limit: 限制数量
            
        Returns:
            搜索结果
        """
        try:
            articles_with_users = (
                self.dbsession.query(Article, User)
                .join(User, Article.userid == User.userid)
                .filter(and_(
                    or_(
                        Article.headline.contains(keyword),
                        Article.content.contains(keyword)
                    ),
                    Article.hidden == 0,
                    Article.checked == 1
                ))
                .order_by(desc(Article.createtime))
                .limit(limit)
                .all()
            )
            
            return self._format_articles_with_users(articles_with_users)
            
        except Exception as e:
            logger.error(f"搜索文章失败 (keyword: {keyword}): {str(e)}")
            return []
    
    def increment_read_count(self, article_id: int) -> bool:
        """
        原子性增加文章阅读数
        
        Args:
            article_id: 文章ID
            
        Returns:
            是否成功
        """
        try:
            from sqlalchemy import text
            
            # 使用原子更新避免竞态条件
            result = self.dbsession.execute(
                text("UPDATE article SET readcount = readcount + 1 WHERE articleid = :article_id"),
                {'article_id': article_id}
            )
            
            if result.rowcount == 1:
                self.dbsession.commit()
                logger.debug(f"文章阅读数增加成功 (ID: {article_id})")
                return True
            else:
                logger.warning(f"文章不存在，无法增加阅读数 (ID: {article_id})")
                return False
                
        except Exception as e:
            self.dbsession.rollback()
            logger.error(f"增加文章阅读数失败 (ID: {article_id}): {str(e)}")
            return False

# 全局服务实例
article_service = ArticleService()

# 便捷函数
def get_articles_with_users(limit=10, offset=0, include_hidden=False):
    return article_service.get_articles_with_users(limit, offset, include_hidden)

def get_homepage_articles():
    return article_service.get_homepage_articles()

def get_article_by_id(article_id, include_user=True):
    return article_service.get_article_by_id(article_id, include_user)

def get_articles_by_type(article_type, limit=20):
    return article_service.get_articles_by_type(article_type, limit)

def search_articles(keyword, limit=20):
    return article_service.search_articles(keyword, limit)

def increment_read_count(article_id):
    return article_service.increment_read_count(article_id)