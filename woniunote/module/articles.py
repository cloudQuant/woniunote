import time
import traceback
import uuid
from flask import session
from sqlalchemy import Table, Column, Integer, String, Text, DateTime, func, ForeignKey
from sqlalchemy.orm import relationship
from woniunote.common.database import dbconnect
from woniunote.module.users import Users
from woniunote.common.create_database import Article
from woniunote.common.simple_logger import get_simple_logger

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

dbsession, md, DBase = dbconnect()


class Articles(DBase):
    __table__ = Table(
        'article', md,
        Column('articleid', Integer, primary_key=True, nullable=False, autoincrement=True),
        Column('userid', Integer, ForeignKey('users.userid'), nullable=False),
        Column('type', Integer, nullable=False),
        Column('headline', String(100), nullable=False),
        Column('content', Text(16777216)),
        Column('thumbnail', String(30)),
        Column('credit', Integer, default=0),
        Column('readcount', Integer, default=0),
        Column('replycount', Integer, default=0),
        Column('recommended', Integer, default=0),
        Column('hidden', Integer, default=0),
        Column('drafted', Integer, default=0),
        Column('checked', Integer, default=1),
        Column('createtime', DateTime),
        Column('updatetime', DateTime)
    )

    def __init__(self):
        from woniunote.module.users import Users
        self.user = relationship("Users", back_populates="Articles")

    # 定义外键关系
    # user = relationship("Users", foreign_keys=[__table__.c.userid], primaryjoin="Article.userid == Users.userid")

    # 查询所有文章
    @staticmethod
    def find_all():
        # 生成跟踪ID
        trace_id = get_articles_trace_id()
        
        # 记录查询开始
        articles_logger.info("开始查询所有文章", {
            'trace_id': trace_id
        })
        
        try:
            # 执行查询
            query_start_time = time.time()
            result = dbsession.query(Article).all()
            query_end_time = time.time()
            
            # 记录查询结果
            articles_logger.info("查询所有文章成功", {
                'trace_id': trace_id,
                'result_count': len(result) if result else 0,
                'query_time_ms': round((query_end_time - query_start_time) * 1000, 2)
            })
            
            return result
        except Exception as e:
            # 记录异常
            articles_logger.error("查询所有文章异常", {
                'trace_id': trace_id,
                'error': str(e),
                'error_type': type(e).__name__
            })
            traceback.print_exc()
            return []

    # 根据id查询文章，数据格式：(Article, 'nickname')
    @staticmethod
    def find_by_id(articleid):
        # 生成跟踪ID
        trace_id = get_articles_trace_id()
        
        # 记录查询开始
        articles_logger.info("根据ID查询文章", {
            'trace_id': trace_id,
            'articleid': articleid
        })
        
        try:
            result = dbsession.query(Article).filter_by(articleid=articleid).first()
            
            # 记录查询结果
            if result:
                articles_logger.info("文章查询成功", {
                    'trace_id': trace_id,
                    'articleid': articleid,
                    'headline': result.headline,
                    'userid': result.userid
                })
            else:
                articles_logger.warning("未找到指定文章", {
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

    # 根据多个文章ID查询文章
    @staticmethod
    def find_by_ids(articleid_list):
        try:
            if not articleid_list:
                return []
            result = dbsession.query(Article).filter(Article.articleid.in_(articleid_list)).all()
            return result
        except Exception as e:
            print(e)
            traceback.print_exc()
            return []

    # 根据用户ID查询文章
    @staticmethod
    def find_by_userid(userid):
        # 生成跟踪ID
        trace_id = get_articles_trace_id()
        
        # 记录查询开始
        articles_logger.info("开始根据用户ID查询文章", {
            'trace_id': trace_id,
            'userid': userid
        })
        
        try:
            # 执行查询
            query_start_time = time.time()
            result = dbsession.query(Article).filter_by(userid=userid, drafted=0).order_by(Article.articleid.desc()).all()
            query_end_time = time.time()
            
            # 记录查询结果
            articles_logger.info("根据用户ID查询文章成功", {
                'trace_id': trace_id,
                'userid': userid,
                'result_count': len(result) if result else 0,
                'query_time_ms': round((query_end_time - query_start_time) * 1000, 2)
            })
            
            return result
        except Exception as e:
            # 记录异常
            articles_logger.error("根据用户ID查询文章异常", {
                'trace_id': trace_id,
                'userid': userid,
                'error': str(e),
                'error_type': type(e).__name__
            })
            traceback.print_exc()
            return []

    # 根据用户ID查询草稿
    @staticmethod
    def find_drafts_by_userid(userid):
        # 生成跟踪ID
        trace_id = get_articles_trace_id()
        
        # 记录查询开始
        articles_logger.info("开始根据用户ID查询草稿", {
            'trace_id': trace_id,
            'userid': userid
        })
        
        try:
            # 执行查询
            query_start_time = time.time()
            result = dbsession.query(Article).filter_by(userid=userid, drafted=1).order_by(Article.articleid.desc()).all()
            query_end_time = time.time()
            
            # 记录查询结果
            articles_logger.info("根据用户ID查询草稿成功", {
                'trace_id': trace_id,
                'userid': userid,
                'result_count': len(result) if result else 0,
                'query_time_ms': round((query_end_time - query_start_time) * 1000, 2)
            })
            
            return result
        except Exception as e:
            # 记录异常
            articles_logger.error("根据用户ID查询草稿异常", {
                'trace_id': trace_id,
                'userid': userid,
                'error': str(e),
                'error_type': type(e).__name__
            })
            traceback.print_exc()
            return []

    # 指定分页的limit和offset的参数值，同时与用户表做连接查询
    @staticmethod
    def find_limit_with_users(start, count):
        # 生成跟踪ID
        trace_id = get_articles_trace_id()
        
        # 记录查询开始
        articles_logger.info("开始分页查询文章", {
            'trace_id': trace_id,
            'start': start,
            'count': count
        })
        
        try:
            # 执行连接查询
            query_start_time = time.time()
            result = dbsession.query(Article, Users.nickname).join(Users, Users.userid == Article.userid).all()
            query_end_time = time.time()
            
            # 记录查询时间
            articles_logger.info("文章连接查询完成", {
                'trace_id': trace_id,
                'total_results': len(result) if result else 0,
                'query_time_ms': round((query_end_time - query_start_time) * 1000, 2)
            })
            
            # 排序处理
            sort_start_time = time.time()
            result = sorted(result, key=lambda row: row[0].articleid, reverse=True)
            sort_end_time = time.time()
            
            # 记录排序时间
            articles_logger.info("文章排序完成", {
                'trace_id': trace_id,
                'sort_time_ms': round((sort_end_time - sort_start_time) * 1000, 2)
            })
            
            # 分页处理
            begin = start
            end = start + count
            
            if begin == -10:
                result = result[:count]
                articles_logger.info("特殊分页处理", {
                    'trace_id': trace_id,
                    'special_start': begin,
                    'result_count': len(result) if result else 0
                })
            else:
                result = result[begin:end]
                articles_logger.info("正常分页处理", {
                    'trace_id': trace_id,
                    'begin': begin,
                    'end': end,
                    'result_count': len(result) if result else 0
                })
            
            # 记录查询结果
            articles_logger.info("分页查询文章成功", {
                'trace_id': trace_id,
                'start': start,
                'count': count,
                'result_count': len(result) if result else 0
            })
            
            return result
        except Exception as e:
            # 记录异常
            articles_logger.error("分页查询文章异常", {
                'trace_id': trace_id,
                'start': start,
                'count': count,
                'error': str(e),
                'error_type': type(e).__name__
            })
            traceback.print_exc()
            return []

    # 统计一下当前文章的总数量
    @staticmethod
    def get_total_count():
        # 生成跟踪ID
        trace_id = get_articles_trace_id()
        
        # 记录开始统计
        articles_logger.info("开始统计文章总数", {
            'trace_id': trace_id
        })
        
        try:
            # 执行统计查询
            query_start_time = time.time()
            count = dbsession.query(Article).filter(Article.hidden == 0, Article.drafted == 0, Article.checked == 1).count()
            query_end_time = time.time()
            
            # 记录统计结果
            articles_logger.info("统计文章总数成功", {
                'trace_id': trace_id,
                'count': count,
                'query_time_ms': round((query_end_time - query_start_time) * 1000, 2)
            })
            
            return count
        except Exception as e:
            # 记录异常
            articles_logger.error("统计文章总数异常", {
                'trace_id': trace_id,
                'error': str(e),
                'error_type': type(e).__name__
            })
            traceback.print_exc()
            return 0

    # 根据文章类型获取文章
    @staticmethod
    def find_by_type(article_type, start, count):
        # 生成跟踪ID
        trace_id = get_articles_trace_id()
        
        # 记录查询开始
        articles_logger.info("开始按类型查询文章", {
            'trace_id': trace_id,
            'article_type': article_type,
            'start': start,
            'count': count
        })
        
        try:
            # 执行查询
            query_start_time = time.time()
            result = dbsession.query(Article, Users.nickname).join(Users, Users.userid == Article.userid) \
                .filter(Article.hidden == 0, Article.drafted == 0, Article.checked == 1, Article.type == article_type) \
                .order_by(Article.articleid.desc()).limit(count).offset(start).all()
            query_end_time = time.time()
            
            # 记录查询结果
            articles_logger.info("按类型查询文章成功", {
                'trace_id': trace_id,
                'article_type': article_type,
                'start': start,
                'count': count,
                'result_count': len(result) if result else 0,
                'query_time_ms': round((query_end_time - query_start_time) * 1000, 2)
            })
            
            return result
        except Exception as e:
            # 记录异常
            articles_logger.error("按类型查询文章异常", {
                'trace_id': trace_id,
                'article_type': article_type,
                'start': start,
                'count': count,
                'error': str(e),
                'error_type': type(e).__name__
            })
            traceback.print_exc()
            return []

    # 根据文章类型来获取总数量
    @staticmethod
    def get_count_by_type(article_type):
        # 生成跟踪ID
        trace_id = get_articles_trace_id()
        
        # 记录开始统计
        articles_logger.info("开始按类型统计文章数量", {
            'trace_id': trace_id,
            'article_type': article_type
        })
        
        try:
            # 执行统计查询
            query_start_time = time.time()
            count = dbsession.query(Article).filter(Article.hidden == 0,
                                                    Article.drafted == 0,
                                                    Article.checked == 1,
                                                    Article.type == article_type).count()
            query_end_time = time.time()
            
            # 记录统计结果
            articles_logger.info("按类型统计文章数量成功", {
                'trace_id': trace_id,
                'article_type': article_type,
                'count': count,
                'query_time_ms': round((query_end_time - query_start_time) * 1000, 2)
            })
            
            return count
        except Exception as e:
            # 记录异常
            articles_logger.error("按类型统计文章数量异常", {
                'trace_id': trace_id,
                'article_type': article_type,
                'error': str(e),
                'error_type': type(e).__name__
            })
            traceback.print_exc()
            return 0

    # 根据文章标题进行模糊搜索
    @staticmethod
    def find_by_headline(headline, start, count):
        # 生成跟踪ID
        trace_id = get_articles_trace_id()
        
        # 记录搜索开始
        articles_logger.info("开始根据标题模糊搜索文章", {
            'trace_id': trace_id,
            'headline': headline,
            'start': start,
            'count': count
        })
        
        try:
            # 执行搜索查询
            query_start_time = time.time()
            result = dbsession.query(Article, Users.nickname).join(Users, Users.userid == Article.userid) \
                .filter(Article.hidden == 0, Article.drafted == 0, Article.checked == 1,
                        Article.headline.like('%' + headline + '%')) \
                .order_by(Article.articleid.desc()).limit(count).offset(start).all()
            query_end_time = time.time()
            
            # 记录搜索结果
            articles_logger.info("根据标题模糊搜索文章成功", {
                'trace_id': trace_id,
                'headline': headline,
                'start': start,
                'count': count,
                'result_count': len(result) if result else 0,
                'query_time_ms': round((query_end_time - query_start_time) * 1000, 2)
            })
            
            return result
        except Exception as e:
            # 记录异常
            articles_logger.error("根据标题模糊搜索文章异常", {
                'trace_id': trace_id,
                'headline': headline,
                'start': start,
                'count': count,
                'error': str(e),
                'error_type': type(e).__name__
            })
            traceback.print_exc()
            return []

    # 统计分页总数量
    @staticmethod
    def get_count_by_headline(headline):
        # 生成跟踪ID
        trace_id = get_articles_trace_id()
        
        # 记录开始统计
        articles_logger.info("开始统计标题搜索结果数量", {
            'trace_id': trace_id,
            'headline': headline
        })
        
        try:
            # 执行统计查询
            query_start_time = time.time()
            count = dbsession.query(Article).filter(Article.hidden == 0,
                                                Article.drafted == 0,
                                                Article.checked == 1,
                                                Article.headline.like('%' + headline + '%')).count()
            query_end_time = time.time()
            
            # 记录统计结果
            articles_logger.info("统计标题搜索结果数量成功", {
                'trace_id': trace_id,
                'headline': headline,
                'count': count,
                'query_time_ms': round((query_end_time - query_start_time) * 1000, 2)
            })
            
            return count
        except Exception as e:
            # 记录异常
            articles_logger.error("统计标题搜索结果数量异常", {
                'trace_id': trace_id,
                'headline': headline,
                'error': str(e),
                'error_type': type(e).__name__
            })
            traceback.print_exc()
            return 0

    # 最新文章[(id, headline),(id, headline)]
    @staticmethod
    def find_last_9():
        # 生成跟踪ID
        trace_id = get_articles_trace_id()
        
        # 记录查询开始
        articles_logger.info("开始查询最新9篇文章", {
            'trace_id': trace_id
        })
        
        try:
            # 执行查询
            query_start_time = time.time()
            result = dbsession.query(Article.articleid, Article.headline). \
                filter(Article.hidden == 0, Article.drafted == 0, Article.checked == 1) \
                .order_by(Article.articleid.desc()).limit(9).all()
            query_end_time = time.time()
            
            # 记录查询结果
            articles_logger.info("查询最新9篇文章成功", {
                'trace_id': trace_id,
                'result_count': len(result) if result else 0,
                'query_time_ms': round((query_end_time - query_start_time) * 1000, 2)
            })
            
            return result
        except Exception as e:
            # 记录异常
            articles_logger.error("查询最新9篇文章异常", {
                'trace_id': trace_id,
                'error': str(e),
                'error_type': type(e).__name__
            })
            traceback.print_exc()
            return []

    # 最多阅读
    @staticmethod
    def find_most_9():
        # 生成跟踪ID
        trace_id = get_articles_trace_id()
        
        # 记录查询开始
        articles_logger.info("开始查询阅读量最多的9篇文章", {
            'trace_id': trace_id
        })
        
        try:
            # 执行查询
            query_start_time = time.time()
            result = dbsession.query(Article.articleid, Article.headline). \
                filter(Article.hidden == 0, Article.drafted == 0, Article.checked == 1) \
                .order_by(Article.readcount.desc()).limit(9).all()
            query_end_time = time.time()
            
            # 记录查询结果
            articles_logger.info("查询阅读量最多的9篇文章成功", {
                'trace_id': trace_id,
                'result_count': len(result) if result else 0,
                'query_time_ms': round((query_end_time - query_start_time) * 1000, 2)
            })
            
            return result
        except Exception as e:
            # 记录异常
            articles_logger.error("查询阅读量最多的9篇文章异常", {
                'trace_id': trace_id,
                'error': str(e),
                'error_type': type(e).__name__
            })
            traceback.print_exc()
            return []

    # 特别推荐，如果超过9篇，可以考虑order by rand()的方式随机显示9篇
    @staticmethod
    def find_recommended_9():
        # 生成跟踪ID
        trace_id = get_articles_trace_id()
        
        # 记录查询开始
        articles_logger.info("开始查询推荐的9篇文章", {
            'trace_id': trace_id
        })
        
        try:
            # 执行查询
            query_start_time = time.time()
            result = dbsession.query(Article.articleid, Article.headline). \
                filter(Article.hidden == 0, Article.drafted == 0, Article.checked == 1, Article.recommended == 1) \
                .order_by(func.rand()).limit(9).all()
            query_end_time = time.time()
            
            # 记录查询结果
            articles_logger.info("查询推荐的9篇文章成功", {
                'trace_id': trace_id,
                'result_count': len(result) if result else 0,
                'query_time_ms': round((query_end_time - query_start_time) * 1000, 2)
            })
            
            return result
        except Exception as e:
            # 记录异常
            articles_logger.error("查询推荐的9篇文章异常", {
                'trace_id': trace_id,
                'error': str(e),
                'error_type': type(e).__name__
            })
            traceback.print_exc()
            return []

    # 一次性返回三个推荐数据
    @staticmethod
    def find_last_most_recommended():
        # 生成跟踪ID
        trace_id = get_articles_trace_id()
        
        # 记录查询开始
        articles_logger.info("开始查询三类推荐文章", {
            'trace_id': trace_id
        })
        
        try:
            # 最新文章
            query_start_time = time.time()
            last = dbsession.query(Article).filter(
                Article.hidden == 0,
                Article.drafted == 0,
                Article.checked == 1
            ).order_by(Article.articleid.desc()).limit(9).all()
            query_end_time = time.time()
            
            # 记录最新文章查询结果
            articles_logger.info("查询最新文章成功", {
                'trace_id': trace_id,
                'last_count': len(last) if last else 0,
                'query_time_ms': round((query_end_time - query_start_time) * 1000, 2)
            })

            # 最多阅读
            query_start_time = time.time()
            most = dbsession.query(Article).filter(
                Article.hidden == 0,
                Article.drafted == 0,
                Article.checked == 1
            ).order_by(Article.readcount.desc()).limit(9).all()
            query_end_time = time.time()
            
            # 记录最多阅读查询结果
            articles_logger.info("查询最多阅读文章成功", {
                'trace_id': trace_id,
                'most_count': len(most) if most else 0,
                'query_time_ms': round((query_end_time - query_start_time) * 1000, 2)
            })

            # 推荐文章
            query_start_time = time.time()
            recommended = dbsession.query(Article).filter(
                Article.hidden == 0,
                Article.drafted == 0,
                Article.checked == 1,
                Article.recommended == 1
            ).order_by(Article.articleid.desc()).limit(9).all()
            query_end_time = time.time()
            
            # 记录推荐文章查询结果
            articles_logger.info("查询推荐文章成功", {
                'trace_id': trace_id,
                'recommended_count': len(recommended) if recommended else 0,
                'query_time_ms': round((query_end_time - query_start_time) * 1000, 2)
            })
            
            # 记录总体查询结果
            articles_logger.info("查询三类推荐文章成功", {
                'trace_id': trace_id,
                'last_count': len(last) if last else 0,
                'most_count': len(most) if most else 0,
                'recommended_count': len(recommended) if recommended else 0
            })

            return last, most, recommended
        except Exception as e:
            # 记录异常
            articles_logger.error("查询三类推荐文章异常", {
                'trace_id': trace_id,
                'error': str(e),
                'error_type': type(e).__name__
            })
            traceback.print_exc()
            return [], [], []

    # 每阅读一次文章，阅读次数+1
    @staticmethod
    def update_read_count(articleid):
        # 生成跟踪ID
        trace_id = get_articles_trace_id()
        
        # 记录开始更新阅读计数
        articles_logger.info("开始更新文章阅读计数", {
            'trace_id': trace_id,
            'articleid': articleid,
            'user_id': session.get('main_userid') if session.get('main_islogin') == 'true' else None
        })
        
        try:
            article = dbsession.query(Article).filter_by(articleid=articleid).first()
            
            # 检查文章是否存在
            if not article:
                articles_logger.warning("更新阅读计数失败：文章不存在", {
                    'trace_id': trace_id,
                    'articleid': articleid
                })
                return
                
            # 记录原始阅读计数
            old_readcount = article.readcount if article.readcount is not None else 0
            
            # 更新阅读计数
            if article.readcount is None:
                article.readcount = 0
            article.readcount += 1
            dbsession.commit()
            
            # 记录更新成功
            articles_logger.info("文章阅读计数更新成功", {
                'trace_id': trace_id,
                'articleid': articleid,
                'headline': article.headline,
                'old_readcount': old_readcount,
                'new_readcount': article.readcount
            })
            
        except Exception as e:
            # 记录异常
            articles_logger.error("更新文章阅读计数异常", {
                'trace_id': trace_id,
                'articleid': articleid,
                'error': str(e),
                'error_type': type(e).__name__
            })
            traceback.print_exc()

    # 根据文章编号查询文章标题
    @staticmethod
    def find_headline_by_id(articleid):
        # 生成跟踪ID
        trace_id = get_articles_trace_id()
        
        # 记录查询开始
        articles_logger.info("开始根据ID查询文章标题", {
            'trace_id': trace_id,
            'articleid': articleid
        })
        
        try:
            # 执行查询
            query_start_time = time.time()
            row = dbsession.query(Article.headline).filter_by(articleid=articleid).first()
            query_end_time = time.time()
            
            if row:
                # 记录查询成功
                articles_logger.info("根据ID查询文章标题成功", {
                    'trace_id': trace_id,
                    'articleid': articleid,
                    'headline': row.headline,
                    'query_time_ms': round((query_end_time - query_start_time) * 1000, 2)
                })
                return row.headline
            else:
                # 记录文章不存在
                articles_logger.warning("根据ID查询文章标题失败：文章不存在", {
                    'trace_id': trace_id,
                    'articleid': articleid,
                    'query_time_ms': round((query_end_time - query_start_time) * 1000, 2)
                })
                return None
        except Exception as e:
            # 记录异常
            articles_logger.error("根据ID查询文章标题异常", {
                'trace_id': trace_id,
                'articleid': articleid,
                'error': str(e),
                'error_type': type(e).__name__
            })
            traceback.print_exc()
            return None

    # 获取当前文章的 上一篇和下一篇
    @staticmethod
    def find_prev_next_by_id(articleid):
        # 生成跟踪ID
        trace_id = get_articles_trace_id()
        
        # 记录查询开始
        articles_logger.info("开始查询文章的上一篇和下一篇", {
            'trace_id': trace_id,
            'articleid': articleid
        })
        
        try:
            query_start_time = time.time()
            m_dict = {}

            # 查询比当前编号小的当中最大的一个
            row = dbsession.query(Article).filter(Article.hidden == 0,
                                                  Article.drafted == 0,
                                                  Article.checked == 1,
                                                  Article.articleid < articleid).order_by(
                Article.articleid.desc()).limit(1).first()
            # 如果当前已经是第一篇，上一篇也是当前文章
            if row is None:
                prev_id = articleid
                prev_is_current = True
            else:
                prev_id = row.articleid
                prev_is_current = False

            m_dict['prev_id'] = prev_id
            m_dict['prev_headline'] = Articles.find_headline_by_id(prev_id)
            
            # 记录上一篇查询结果
            articles_logger.info("查询上一篇文章成功", {
                'trace_id': trace_id,
                'articleid': articleid,
                'prev_id': prev_id,
                'prev_headline': m_dict['prev_headline'],
                'is_first_article': prev_is_current
            })

            # 查询比当前编号大的当中最小的一个
            row = dbsession.query(Article).filter(Article.hidden == 0,
                                                  Article.drafted == 0,
                                                  Article.checked == 1,
                                                  Article.articleid > articleid).order_by(
                Article.articleid).limit(1).first()
            # 如果当前已经是最后一篇，下一篇也是当前文章
            if row is None:
                next_id = articleid
                next_is_current = True
            else:
                next_id = row.articleid
                next_is_current = False

            m_dict['next_id'] = next_id
            m_dict['next_headline'] = Articles.find_headline_by_id(next_id)
            
            # 记录下一篇查询结果
            articles_logger.info("查询下一篇文章成功", {
                'trace_id': trace_id,
                'articleid': articleid,
                'next_id': next_id,
                'next_headline': m_dict['next_headline'],
                'is_last_article': next_is_current
            })
            
            query_end_time = time.time()
            
            # 记录总体查询结果
            articles_logger.info("查询文章的上一篇和下一篇成功", {
                'trace_id': trace_id,
                'articleid': articleid,
                'prev_id': prev_id,
                'next_id': next_id,
                'query_time_ms': round((query_end_time - query_start_time) * 1000, 2)
            })

            return m_dict
        except Exception as e:
            # 记录异常
            articles_logger.error("查询文章的上一篇和下一篇异常", {
                'trace_id': trace_id,
                'articleid': articleid,
                'error': str(e),
                'error_type': type(e).__name__
            })
            traceback.print_exc()
            return {}

    # 当发表或者回复评论后，为文章表字段replycount加1
    @staticmethod
    def update_replycount(articleid):
        # 生成跟踪ID
        trace_id = get_articles_trace_id()
        
        # 记录开始更新评论计数
        articles_logger.info("开始更新文章评论计数", {
            'trace_id': trace_id,
            'articleid': articleid,
            'user_id': session.get('main_userid') if session.get('main_islogin') == 'true' else None
        })
        
        try:
            row = dbsession.query(Article).filter_by(articleid=articleid).first()
            
            # 检查文章是否存在
            if not row:
                articles_logger.warning("更新评论计数失败：文章不存在", {
                    'trace_id': trace_id,
                    'articleid': articleid
                })
                return
                
            # 记录原始评论计数
            old_replycount = row.replycount if row.replycount is not None else 0
            
            # 更新评论计数
            row.replycount += 1
            dbsession.commit()
            
            # 记录更新成功
            articles_logger.info("文章评论计数更新成功", {
                'trace_id': trace_id,
                'articleid': articleid,
                'headline': row.headline,
                'old_replycount': old_replycount,
                'new_replycount': row.replycount
            })
            
        except Exception as e:
            # 记录异常
            articles_logger.error("更新文章评论计数异常", {
                'trace_id': trace_id,
                'articleid': articleid,
                'error': str(e),
                'error_type': type(e).__name__
            })
            traceback.print_exc()

    # 插入一篇新的文章，草稿或投稿通过参数进行区分
    @staticmethod
    def insert_article(article_type, headline, content, thumbnail, credit, drafted=0, checked=1):
        # 生成跟踪ID
        trace_id = get_articles_trace_id()
        
        # 记录插入开始
        articles_logger.info("开始插入文章", {
            'trace_id': trace_id,
            'article_type': article_type,
            'headline': headline,
            'thumbnail': thumbnail,
            'credit': credit,
            'drafted': drafted,
            'checked': checked,
            'user_id': session.get('main_userid')
        })
        
        try:
            now = time.strftime('%Y-%m-%d %H:%M:%S')
            userid = session.get('main_userid')
            
            # 检查用户ID是否存在
            if not userid:
                articles_logger.error("插入文章失败：用户ID不存在", {
                    'trace_id': trace_id,
                    'session_data': str(session)
                })
                return None
                
            # 其他字段在数据库中均已设置好默认值，无须手工插入
            article = Article(userid=userid, type=article_type, headline=headline, content=content,
                               thumbnail=thumbnail, credit=credit, drafted=drafted, readcount=0,
                               checked=checked, createtime=now, updatetime=now)
            dbsession.add(article)
            dbsession.commit()
            
            # 记录插入成功
            articles_logger.info("文章插入成功", {
                'trace_id': trace_id,
                'articleid': article.articleid,
                'headline': headline,
                'user_id': userid,
                'drafted': drafted,
                'checked': checked
            })
            
            return article.articleid  # 将文章ID返回调用处
            
        except Exception as e:
            # 记录异常
            articles_logger.error("文章插入异常", {
                'trace_id': trace_id,
                'headline': headline,
                'user_id': session.get('main_userid'),
                'error': str(e),
                'error_type': type(e).__name__
            })
            traceback.print_exc()
            dbsession.rollback()
            return None

    # 根据文章编号更新文章的内容，可用于文章编辑或草稿修改，以及基于草稿的发布
    @staticmethod
    def update_article(articleid, article_type, headline, content, thumbnail, credit, drafted=0, checked=1):
        # 生成跟踪ID
        trace_id = get_articles_trace_id()
        
        # 记录更新开始
        articles_logger.info("开始更新文章", {
            'trace_id': trace_id,
            'articleid': articleid,
            'article_type': article_type,
            'headline': headline,
            'thumbnail': thumbnail,
            'credit': credit,
            'drafted': drafted,
            'checked': checked,
            'user_id': session.get('main_userid')
        })
        
        try:
            now = time.strftime('%Y-%m-%d %H:%M:%S')
            article = dbsession.query(Article).filter_by(articleid=articleid).first()
            
            if not article:
                # 记录文章不存在
                articles_logger.warning("更新文章失败：文章不存在", {
                    'trace_id': trace_id,
                    'articleid': articleid
                })
                return None
                
            # 记录更新前的文章信息
            articles_logger.info("文章更新前状态", {
                'trace_id': trace_id,
                'articleid': articleid,
                'old_type': article.type,
                'old_headline': article.headline,
                'old_drafted': article.drafted,
                'old_checked': article.checked
            })
            
            # 更新文章内容
            article.type = article_type
            article.headline = headline
            article.content = content
            article.thumbnail = thumbnail
            article.credit = credit
            article.drafted = drafted
            article.checked = checked
            article.updatetime = now  # 修改文章的更新时间
            
            dbsession.commit()
            
            # 记录更新成功
            articles_logger.info("文章更新成功", {
                'trace_id': trace_id,
                'articleid': articleid,
                'headline': headline,
                'user_id': session.get('main_userid'),
                'drafted': drafted,
                'checked': checked,
                'updatetime': now
            })
            
            return articleid  # 继续将文章ID返回调用处
        except Exception as e:
            # 记录异常
            articles_logger.error("文章更新异常", {
                'trace_id': trace_id,
                'articleid': articleid,
                'headline': headline,
                'user_id': session.get('main_userid'),
                'error': str(e),
                'error_type': type(e).__name__
            })
            traceback.print_exc()
            dbsession.rollback()
            return None

    # =========== 以下方法主要用于后台管理类操作 ================== #

    # 查询article表中除草稿外的所有数据并返回结果集
    @staticmethod
    def find_all_except_draft(start, count):
        # 生成跟踪ID
        trace_id = get_articles_trace_id()
        
        # 记录查询开始
        articles_logger.info("开始查询所有非草稿文章", {
            'trace_id': trace_id,
            'start': start,
            'count': count
        })
        
        try:
            # 执行查询
            query_start_time = time.time()
            result = dbsession.query(Article).filter(Article.drafted == 0).order_by(
                Article.articleid.desc()).limit(count).offset(start).all()
            query_end_time = time.time()
            
            # 记录查询结果
            articles_logger.info("查询所有非草稿文章成功", {
                'trace_id': trace_id,
                'start': start,
                'count': count,
                'result_count': len(result) if result else 0,
                'query_time_ms': round((query_end_time - query_start_time) * 1000, 2)
            })
            
            return result
        except Exception as e:
            # 记录异常
            articles_logger.error("查询所有非草稿文章异常", {
                'trace_id': trace_id,
                'start': start,
                'count': count,
                'error': str(e),
                'error_type': type(e).__name__
            })
            traceback.print_exc()
            return []

    # 查询除草稿外的所有文章的总数量
    @staticmethod
    def get_count_except_draft():
        # 生成跟踪ID
        trace_id = get_articles_trace_id()
        
        # 记录开始统计
        articles_logger.info("开始统计非草稿文章数量", {
            'trace_id': trace_id
        })
        
        try:
            # 执行统计查询
            query_start_time = time.time()
            count = dbsession.query(Article).filter(Article.drafted == 0).count()
            query_end_time = time.time()
            
            # 记录统计结果
            articles_logger.info("统计非草稿文章数量成功", {
                'trace_id': trace_id,
                'count': count,
                'query_time_ms': round((query_end_time - query_start_time) * 1000, 2)
            })
            
            return count
        except Exception as e:
            # 记录异常
            articles_logger.error("统计非草稿文章数量异常", {
                'trace_id': trace_id,
                'error': str(e),
                'error_type': type(e).__name__
            })
            traceback.print_exc()
            return 0

    # 按照文章分类进行查询（不含草稿，该方法直接返回文章总数量用于分页）
    def find_by_type_except_draft(self, start, count, article_type):
        # 生成跟踪ID
        trace_id = get_articles_trace_id()
        
        # 记录查询开始
        articles_logger.info("开始按类型查询非草稿文章", {
            'trace_id': trace_id,
            'article_type': article_type,
            'start': start,
            'count': count
        })
        
        try:
            query_start_time = time.time()
            if type == 0:
                result = self.find_all_except_draft(start, count)
                total = self.get_count_except_draft()
                
                # 记录查询结果
                articles_logger.info("查询所有非草稿文章成功", {
                    'trace_id': trace_id,
                    'start': start,
                    'count': count,
                    'result_count': len(result) if result else 0,
                    'total': total
                })
            else:
                # 执行查询
                result = dbsession.query(Article).filter(Article.drafted == 0,
                                                         Article.type == article_type).order_by(Article.articleid.desc()) \
                    .limit(count).offset(start).all()
                total = dbsession.query(Article).filter(Article.drafted == 0,
                                                        Article.type == article_type).count()
                
                # 记录查询结果
                articles_logger.info("按类型查询非草稿文章成功", {
                    'trace_id': trace_id,
                    'article_type': article_type,
                    'start': start,
                    'count': count,
                    'result_count': len(result) if result else 0,
                    'total': total
                })
            
            query_end_time = time.time()
            
            # 记录总体查询时间
            articles_logger.info("按类型查询非草稿文章完成", {
                'trace_id': trace_id,
                'query_time_ms': round((query_end_time - query_start_time) * 1000, 2)
            })
            
            return result, total  # 返回分页结果集和不分页的总数量
        except Exception as e:
            # 记录异常
            articles_logger.error("按类型查询非草稿文章异常", {
                'trace_id': trace_id,
                'article_type': article_type,
                'start': start,
                'count': count,
                'error': str(e),
                'error_type': type(e).__name__
            })
            traceback.print_exc()
            return [], 0

    # 按照标题模糊查询（不含草稿，不分页）
    @staticmethod
    def find_by_headline_except_draft(headline):
        # 生成跟踪ID
        trace_id = get_articles_trace_id()
        
        # 记录查询开始
        articles_logger.info("开始按标题模糊查询非草稿文章", {
            'trace_id': trace_id,
            'headline': headline
        })
        
        try:
            # 执行查询
            query_start_time = time.time()
            result = dbsession.query(Article).filter(Article.drafted == 0,
                                                     Article.headline.like('%' + headline + '%')) \
                .order_by(Article.articleid.desc()).all()
            query_end_time = time.time()
            
            # 记录查询结果
            articles_logger.info("按标题模糊查询非草稿文章成功", {
                'trace_id': trace_id,
                'headline': headline,
                'result_count': len(result) if result else 0,
                'query_time_ms': round((query_end_time - query_start_time) * 1000, 2)
            })
            
            return result
        except Exception as e:
            # 记录异常
            articles_logger.error("按标题模糊查询非草稿文章异常", {
                'trace_id': trace_id,
                'headline': headline,
                'error': str(e),
                'error_type': type(e).__name__
            })
            traceback.print_exc()
            return []

    # 切换文章的隐藏状态：1表示隐藏，0表示显示
    @staticmethod
    def switch_hidden(articleid):
        # 生成跟踪ID
        trace_id = get_articles_trace_id()
        
        # 记录操作开始
        articles_logger.info("开始切换文章隐藏状态", {
            'trace_id': trace_id,
            'articleid': articleid
        })
        
        try:
            # 查询文章
            query_start_time = time.time()
            row = dbsession.query(Article).filter_by(articleid=articleid).first()
            
            if not row:
                # 记录文章不存在
                articles_logger.warning("切换隐藏状态的文章不存在", {
                    'trace_id': trace_id,
                    'articleid': articleid
                })
                return None
            
            # 记录原始状态
            original_hidden = row.hidden
            
            # 切换状态
            if row.hidden == 1:
                row.hidden = 0
                new_status = "显示"
            else:
                row.hidden = 1
                new_status = "隐藏"
                
            # 提交事务
            dbsession.commit()
            query_end_time = time.time()
            
            # 记录操作结果
            articles_logger.info("切换文章隐藏状态成功", {
                'trace_id': trace_id,
                'articleid': articleid,
                'headline': row.headline if hasattr(row, 'headline') else None,
                'original_status': "隐藏" if original_hidden == 1 else "显示",
                'new_status': new_status,
                'query_time_ms': round((query_end_time - query_start_time) * 1000, 2)
            })
            
            return row.hidden  # 将当前最新状态返回给控制层
        except Exception as e:
            # 记录异常
            articles_logger.error("切换文章隐藏状态异常", {
                'trace_id': trace_id,
                'articleid': articleid,
                'error': str(e),
                'error_type': type(e).__name__
            })
            traceback.print_exc()
            return None

    # 切换文章的推荐状态：1表示推荐，0表示正常
    @staticmethod
    def switch_recommended(articleid):
        # 生成跟踪ID
        trace_id = get_articles_trace_id()
        
        # 记录操作开始
        articles_logger.info("开始切换文章推荐状态", {
            'trace_id': trace_id,
            'articleid': articleid
        })
        
        try:
            # 查询文章
            query_start_time = time.time()
            row = dbsession.query(Article).filter_by(articleid=articleid).first()
            
            if not row:
                # 记录文章不存在
                articles_logger.warning("切换推荐状态的文章不存在", {
                    'trace_id': trace_id,
                    'articleid': articleid
                })
                return None
            
            # 记录原始状态
            original_recommended = row.recommended
            
            # 切换状态
            if row.recommended == 1:
                row.recommended = 0
                new_status = "普通"
            else:
                row.recommended = 1
                new_status = "推荐"
                
            # 提交事务
            dbsession.commit()
            query_end_time = time.time()
            
            # 记录操作结果
            articles_logger.info("切换文章推荐状态成功", {
                'trace_id': trace_id,
                'articleid': articleid,
                'headline': row.headline if hasattr(row, 'headline') else None,
                'original_status': "推荐" if original_recommended == 1 else "普通",
                'new_status': new_status,
                'query_time_ms': round((query_end_time - query_start_time) * 1000, 2)
            })
            
            return row.recommended
        except Exception as e:
            # 记录异常
            articles_logger.error("切换文章推荐状态异常", {
                'trace_id': trace_id,
                'articleid': articleid,
                'error': str(e),
                'error_type': type(e).__name__
            })
            traceback.print_exc()
            return None

    # 切换文章的审核状态：1表示已审，0表示待审
    @staticmethod
    def switch_checked(articleid):
        # 生成跟踪ID
        trace_id = get_articles_trace_id()
        
        # 记录操作开始
        articles_logger.info("开始切换文章审核状态", {
            'trace_id': trace_id,
            'articleid': articleid
        })
        
        try:
            # 查询文章
            query_start_time = time.time()
            row = dbsession.query(Article).filter_by(articleid=articleid).first()
            
            if not row:
                # 记录文章不存在
                articles_logger.warning("切换审核状态的文章不存在", {
                    'trace_id': trace_id,
                    'articleid': articleid
                })
                return None
            
            # 记录原始状态
            original_checked = row.checked
            
            # 切换状态
            if row.checked == 1:
                row.checked = 0
                new_status = "待审"
            else:
                row.checked = 1
                new_status = "已审"
                
            # 提交事务
            dbsession.commit()
            query_end_time = time.time()
            
            # 记录操作结果
            articles_logger.info("切换文章审核状态成功", {
                'trace_id': trace_id,
                'articleid': articleid,
                'headline': row.headline if hasattr(row, 'headline') else None,
                'original_status': "已审" if original_checked == 1 else "待审",
                'new_status': new_status,
                'query_time_ms': round((query_end_time - query_start_time) * 1000, 2)
            })
            
            return row.checked
        except Exception as e:
            # 记录异常
            articles_logger.error("切换文章审核状态异常", {
                'trace_id': trace_id,
                'articleid': articleid,
                'error': str(e),
                'error_type': type(e).__name__
            })
            traceback.print_exc()
            return None


if __name__ == "__main__":
    article_instance = Articles()
