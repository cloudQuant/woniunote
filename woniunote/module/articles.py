import time
import traceback
import uuid
import datetime
from flask import session
from sqlalchemy import Table, Column, Integer, String, Text, DateTime, func, ForeignKey
from sqlalchemy.orm import relationship
from woniunote.common.database import dbconnect
from woniunote.module.users import Users
# 从模型定义中导入 Article 类
from woniunote.common.create_database import Article, User
from woniunote.common.unified_logging import get_simple_logger

# 初始化日志记录器
articles_logger = get_simple_logger('articles')

# 生成唯一的跟踪ID
def get_articles_trace_id():
    """
    生成唯一的跟踪ID用于日志关联
    
    Returns:
        str: 唯一的跟踪ID
    """
    return f"articles_{uuid.uuid4().hex}"

class Articles:
    """文章管理类 - 所有方法都是静态方法"""

    @staticmethod
    def find_by_id(articleid):
        """根据ID查询文章"""
        # 生成跟踪ID
        trace_id = get_articles_trace_id()
        
        # 记录查询开始
        articles_logger.info("根据ID查询文章", {
            'trace_id': trace_id,
            'articleid': articleid
        })
        
        try:
            # 动态获取数据库连接
            try:
                dbsession, md, DBase = dbconnect()
                if dbsession is None:
                    articles_logger.error("无法获取数据库连接", {'trace_id': trace_id})
                    return None
            except Exception as db_error:
                articles_logger.error("数据库连接失败", {
                    'trace_id': trace_id,
                    'error': str(db_error)
                })
                return None

            result = dbsession.query(Article).filter_by(articleid=articleid).first()

            # 记录查询结果
            if result:
                articles_logger.info("文章查询成功", {
                    'trace_id': trace_id,
                    'articleid': articleid,
                    'headline': result.headline[:30] + '...' if len(result.headline) > 30 else result.headline,
                    'type': result.type
                })
            else:
                articles_logger.warning("文章不存在", {
                    'trace_id': trace_id,
                    'articleid': articleid
                })

            return result
        except Exception as e:
            # 记录异常
            articles_logger.error("文章查询异常", {
                'trace_id': trace_id,
                'articleid': articleid,
                'error': str(e),
                'error_type': type(e).__name__
            })
            traceback.print_exc()
            return None

    @staticmethod
    def update_read_count(articleid):
        """更新文章阅读次数"""
        try:
            # 动态获取数据库连接
            dbsession, md, DBase = dbconnect()
            if dbsession is None:
                return
            
            # 更新阅读次数
            dbsession.query(Article).filter_by(articleid=articleid).update({
                'readcount': Article.readcount + 1,
                'updatetime': datetime.datetime.now()
            })
            dbsession.commit()
        except Exception as e:
            articles_logger.error(f"更新阅读次数失败: {e}")

    @staticmethod
    def find_prev_next_by_id(articleid):
        """获取上一篇和下一篇文章"""
        try:
            # 动态获取数据库连接
            dbsession, md, DBase = dbconnect()
            if dbsession is None:
                return None, None

            # 查找上一篇文章
            prev_article = dbsession.query(Article).filter(
                Article.articleid < articleid,
                Article.drafted == 0,
                Article.checked == 1
            ).order_by(Article.articleid.desc()).first()

            # 查找下一篇文章
            next_article = dbsession.query(Article).filter(
                Article.articleid > articleid,
                Article.drafted == 0,
                Article.checked == 1
            ).order_by(Article.articleid.asc()).first()

            return prev_article, next_article
        except Exception as e:
            articles_logger.error(f"查找前后文章失败: {e}")
            return None, None

    @staticmethod
    def find_limit_with_users(start, count):
        """获取文章列表（带用户信息）"""
        try:
            # 动态获取数据库连接
            dbsession, md, DBase = dbconnect()
            if dbsession is None:
                return []

            # 查询文章和用户信息 - 先获取文章，再获取用户信息
            articles = dbsession.query(Article).filter(
                Article.drafted == 0,
                Article.checked == 1
            ).order_by(Article.articleid.desc()).offset(start).limit(count).all()

            # 转换为(文章对象, 作者昵称)的元组格式，符合首页模板要求
            articles_list = []
            for article in articles:
                # 获取作者信息 - 直接使用User模型
                try:
                    user = dbsession.query(User).filter(User.userid == article.userid).first()
                except Exception:
                    user = None

                nickname = user.nickname if user else "Unknown"
                articles_list.append((article, nickname))

            return articles_list
        except Exception as e:
            articles_logger.error(f"获取文章列表失败: {e}")
            import traceback
            traceback.print_exc()
            return []

    @staticmethod
    def get_total_count():
        """获取文章总数"""
        try:
            # 动态获取数据库连接
            dbsession, md, DBase = dbconnect()
            if dbsession is None:
                return 0

            count = dbsession.query(Article).filter(
                Article.drafted == 0,
                Article.checked == 1
            ).count()

            return count
        except Exception as e:
            articles_logger.error(f"获取文章总数失败: {e}")
            return 0

    @staticmethod
    def find_last_most_recommended():
        """获取最新、最热、推荐文章"""
        try:
            # 动态获取数据库连接
            dbsession, md, DBase = dbconnect()
            if dbsession is None:
                return [], [], []

            # 最新文章
            last_articles = dbsession.query(Article).filter(
                Article.drafted == 0,
                Article.checked == 1
            ).order_by(Article.createtime.desc()).limit(9).all()

            # 最热文章（按阅读次数）
            most_articles = dbsession.query(Article).filter(
                Article.drafted == 0,
                Article.checked == 1
            ).order_by(Article.readcount.desc()).limit(9).all()

            # 推荐文章（按推荐标志）
            recommended_articles = dbsession.query(Article).filter(
                Article.drafted == 0,
                Article.checked == 1,
                Article.recommended == 1
            ).order_by(Article.createtime.desc()).limit(9).all()

            return last_articles, most_articles, recommended_articles
        except Exception as e:
            articles_logger.error(f"获取最新最热推荐文章失败: {e}")
            return [], [], []

    @staticmethod
    def find_by_ids(article_ids):
        """根据文章ID列表查找文章"""
        trace_id = get_articles_trace_id()
        articles_logger.info("开始根据ID列表查询文章", {
            'trace_id': trace_id,
            'article_ids': article_ids
        })

        try:
            # 动态获取数据库连接
            dbsession, md, DBase = dbconnect()
            if dbsession is None:
                articles_logger.error("无法获取数据库连接", {'trace_id': trace_id})
                return []

            # 查询文章
            articles = dbsession.query(Article).filter(
                Article.articleid.in_(article_ids),
                Article.drafted == 0,
                Article.checked == 1
            ).all()

            articles_logger.info("根据ID列表查询文章成功", {
                'trace_id': trace_id,
                'article_ids': article_ids,
                'articles_count': len(articles)
            })

            return articles

        except Exception as e:
            articles_logger.error("根据ID列表查询文章异常", {
                'trace_id': trace_id,
                'article_ids': article_ids,
                'error': str(e)
            })
            return []

# 为了兼容性，提供一些基本的别名方法
def find_by_id(articleid):
    return Articles.find_by_id(articleid)

def find_limit_with_users(start, count):
    return Articles.find_limit_with_users(start, count)

def get_total_count():
    return Articles.get_total_count()

def find_last_most_recommended():
    return Articles.find_last_most_recommended()

def update_read_count(articleid):
    return Articles.update_read_count(articleid)

def find_prev_next_by_id(articleid):
    return Articles.find_prev_next_by_id(articleid)

def find_by_ids(article_ids):
    return Articles.find_by_ids(article_ids)
