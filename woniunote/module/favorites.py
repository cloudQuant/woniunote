import time
import traceback
import uuid
from flask import session
from sqlalchemy import Table, Column, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from woniunote.common.database import dbconnect
from woniunote.module.articles import Article
from woniunote.common.create_database import Favorite
from woniunote.common.simple_logger import get_simple_logger

dbsession, md, DBase = dbconnect()

# 创建收藏模块的日志记录器
favorites_logger = get_simple_logger('favorites')

# 生成收藏模块的跟踪ID
def get_favorites_trace_id():
    return str(uuid.uuid4())


class Favorites(DBase):
    __table__ = Table(
        'favorite', md,
        Column('favoriteid', Integer, primary_key=True, nullable=False, autoincrement=True),
        Column('userid', Integer, ForeignKey('users.userid'), nullable=False),
        Column('articleid', Integer, ForeignKey('article.articleid'), nullable=False),
        Column('canceled', Integer, default=0),
        Column('createtime', DateTime),
        Column('updatetime', DateTime)
    )

    def __init__(self):
        from woniunote.module.users import Users
        self.user = relationship("Users", back_populates="Favorites")
        self.article = relationship("Articles", back_populates="Favorites")

    # 定义外键关系
    # user = relationship("Users", foreign_keys=[__table__.c.userid],
    #                     primaryjoin="Favorite.userid == Users.userid")
    # article = relationship("Article", foreign_keys=[__table__.c.articleid],
    #                        primaryjoin="Favorite.articleid == Article.articleid")

    # 添加文章收藏数据
    @staticmethod
    def insert_favorite(articleid):
        # 生成跟踪ID
        trace_id = get_favorites_trace_id()
        
        # 获取当前用户ID
        userid = session.get('main_userid')
        
        # 记录收藏操作开始
        favorites_logger.info("开始添加文章收藏", {
            'trace_id': trace_id,
            'userid': userid,
            'articleid': articleid
        })
        
        try:
            # 检查用户ID是否存在
            if not userid:
                # 记录用户ID不存在
                favorites_logger.warning("添加文章收藏失败，用户ID不存在", {
                    'trace_id': trace_id,
                    'articleid': articleid
                })
                return False
            
            # 查询是否已收藏
            query_start_time = time.time()
            row = dbsession.query(Favorite).filter_by(articleid=articleid, userid=userid).first()
            query_end_time = time.time()
            
            # 如果已经收藏过，只需要设置状态为未取消
            if row is not None:
                favorites_logger.info("文章已收藏过，更新状态", {
                    'trace_id': trace_id,
                    'userid': userid,
                    'articleid': articleid,
                    'favoriteid': row.favoriteid,
                    'old_canceled': row.canceled
                })
                row.canceled = 0
            else:
                # 新增收藏记录
                now = time.strftime('%Y-%m-%d %H:%M:%S')
                favorite = Favorite(articleid=articleid, userid=userid, canceled=0, createtime=now,
                                    updatetime=now)
                dbsession.add(favorite)
                
                favorites_logger.info("创建新的收藏记录", {
                    'trace_id': trace_id,
                    'userid': userid,
                    'articleid': articleid,
                    'createtime': now
                })
                
            # 提交事务
            dbsession.commit()
            
            # 记录收藏成功
            favorites_logger.info("添加文章收藏成功", {
                'trace_id': trace_id,
                'userid': userid,
                'articleid': articleid,
                'query_time_ms': round((query_end_time - query_start_time) * 1000, 2)
            })
            
            return True
        except Exception as e:
            # 记录异常
            favorites_logger.error("添加文章收藏异常", {
                'trace_id': trace_id,
                'userid': userid,
                'articleid': articleid,
                'error': str(e),
                'error_type': type(e).__name__
            })
            traceback.print_exc()
            return False

    @staticmethod
    def find_by_userid(userid):
        # 生成跟踪ID
        trace_id = get_favorites_trace_id()
        
        # 记录查询开始
        favorites_logger.info("开始查询用户收藏", {
            'trace_id': trace_id,
            'userid': userid
        })
        
        try:
            # 执行查询
            query_start_time = time.time()
            result = dbsession.query(Favorite).filter_by(userid=userid, canceled=0).all()
            query_end_time = time.time()
            
            # 记录查询结果
            favorites_logger.info("查询用户收藏成功", {
                'trace_id': trace_id,
                'userid': userid,
                'result_count': len(result) if result else 0,
                'query_time_ms': round((query_end_time - query_start_time) * 1000, 2)
            })
            
            return result
        except Exception as e:
            # 记录异常
            favorites_logger.error("查询用户收藏异常", {
                'trace_id': trace_id,
                'userid': userid,
                'error': str(e),
                'error_type': type(e).__name__
            })
            traceback.print_exc()
            return []

    # 取消收藏
    @staticmethod
    def cancel_favorite(articleid):
        # 生成跟踪ID
        trace_id = get_favorites_trace_id()
        
        # 获取当前用户ID
        userid = session.get('main_userid')
        
        # 记录取消收藏操作开始
        favorites_logger.info("开始取消文章收藏", {
            'trace_id': trace_id,
            'userid': userid,
            'articleid': articleid
        })
        
        try:
            # 检查用户ID是否存在
            if not userid:
                # 记录用户ID不存在
                favorites_logger.warning("取消文章收藏失败，用户ID不存在", {
                    'trace_id': trace_id,
                    'articleid': articleid
                })
                return False
            
            # 查询收藏记录
            query_start_time = time.time()
            row = dbsession.query(Favorite).filter_by(articleid=articleid, userid=userid).first()
            query_end_time = time.time()
            
            if row:
                # 记录原始状态
                old_canceled = row.canceled
                
                # 更新状态
                row.canceled = 1
                dbsession.commit()
                
                # 记录取消收藏成功
                favorites_logger.info("取消文章收藏成功", {
                    'trace_id': trace_id,
                    'userid': userid,
                    'articleid': articleid,
                    'favoriteid': row.favoriteid,
                    'old_canceled': old_canceled,
                    'query_time_ms': round((query_end_time - query_start_time) * 1000, 2)
                })
                
                return True
            else:
                # 记录收藏记录不存在
                favorites_logger.warning("取消文章收藏失败，收藏记录不存在", {
                    'trace_id': trace_id,
                    'userid': userid,
                    'articleid': articleid,
                    'query_time_ms': round((query_end_time - query_start_time) * 1000, 2)
                })
                
                return False
        except Exception as e:
            # 记录异常
            favorites_logger.error("取消文章收藏异常", {
                'trace_id': trace_id,
                'userid': userid,
                'articleid': articleid,
                'error': str(e),
                'error_type': type(e).__name__
            })
            traceback.print_exc()
            return False

    # 判断是否已经被收藏
    @staticmethod
    def check_favorite(articleid):
        # 生成跟踪ID
        trace_id = get_favorites_trace_id()
        
        # 获取当前用户ID
        userid = session.get('main_userid')
        
        # 记录检查收藏状态开始
        favorites_logger.info("开始检查文章收藏状态", {
            'trace_id': trace_id,
            'userid': userid,
            'articleid': articleid
        })
        
        try:
            # 检查用户ID是否存在
            if not userid:
                # 记录用户ID不存在
                favorites_logger.warning("检查文章收藏状态失败，用户ID不存在", {
                    'trace_id': trace_id,
                    'articleid': articleid
                })
                return False
            
            # 查询收藏记录
            query_start_time = time.time()
            row = dbsession.query(Favorite).filter_by(articleid=articleid, userid=userid).first()
            query_end_time = time.time()
            
            # 判断收藏状态
            is_favorited = False
            status = "not_favorited"
            
            if row is None:
                is_favorited = False
                status = "not_found"
            elif row.canceled == 1:
                is_favorited = False
                status = "canceled"
            else:
                is_favorited = True
                status = "favorited"
            
            # 记录检查结果
            favorites_logger.info("检查文章收藏状态成功", {
                'trace_id': trace_id,
                'userid': userid,
                'articleid': articleid,
                'is_favorited': is_favorited,
                'status': status,
                'favoriteid': row.favoriteid if row else None,
                'query_time_ms': round((query_end_time - query_start_time) * 1000, 2)
            })
            
            return is_favorited
        except Exception as e:
            # 记录异常
            favorites_logger.error("检查文章收藏状态异常", {
                'trace_id': trace_id,
                'userid': userid,
                'articleid': articleid,
                'error': str(e),
                'error_type': type(e).__name__
            })
            traceback.print_exc()
            return False

    # 为用户中心查询我的收藏添加数据操作方法
    @staticmethod
    def find_my_favorite():
        # 生成跟踪ID
        trace_id = get_favorites_trace_id()
        
        # 获取当前用户ID
        userid = session.get('main_userid')
        
        # 记录查询开始
        favorites_logger.info("开始查询我的收藏", {
            'trace_id': trace_id,
            'userid': userid
        })
        
        try:
            # 检查用户ID是否存在
            if not userid:
                # 记录用户ID不存在
                favorites_logger.warning("查询我的收藏失败，用户ID不存在", {
                    'trace_id': trace_id
                })
                return []
            
            # 执行查询
            query_start_time = time.time()
            result = dbsession.query(Favorite, Article).join(Article, Favorite.articleid == Article.articleid).filter(
                Favorite.userid == userid).all()
            query_end_time = time.time()
            
            # 记录查询结果
            favorites_logger.info("查询我的收藏成功", {
                'trace_id': trace_id,
                'userid': userid,
                'result_count': len(result) if result else 0,
                'query_time_ms': round((query_end_time - query_start_time) * 1000, 2)
            })
            
            return result
        except Exception as e:
            # 记录异常
            favorites_logger.error("查询我的收藏异常", {
                'trace_id': trace_id,
                'userid': userid,
                'error': str(e),
                'error_type': type(e).__name__
            })
            traceback.print_exc()
            return []

    # 切换收藏和取消收藏的状态
    @staticmethod
    def switch_favorite(favoriteid):
        # 生成跟踪ID
        trace_id = get_favorites_trace_id()
        
        # 记录切换收藏状态开始
        favorites_logger.info("开始切换收藏状态", {
            'trace_id': trace_id,
            'favoriteid': favoriteid
        })
        
        try:
            # 查询收藏记录
            query_start_time = time.time()
            row = dbsession.query(Favorite).filter_by(favoriteid=favoriteid).first()
            query_end_time = time.time()
            
            if not row:
                # 记录收藏记录不存在
                favorites_logger.warning("切换收藏状态失败，收藏记录不存在", {
                    'trace_id': trace_id,
                    'favoriteid': favoriteid
                })
                return None
            
            # 记录原始状态
            old_canceled = row.canceled
            
            # 切换状态
            if row.canceled == 1:
                row.canceled = 0
                new_status = "收藏"
            else:
                row.canceled = 1
                new_status = "取消收藏"
                
            # 提交事务
            dbsession.commit()
            
            # 记录切换收藏状态成功
            favorites_logger.info("切换收藏状态成功", {
                'trace_id': trace_id,
                'favoriteid': favoriteid,
                'articleid': row.articleid,
                'userid': row.userid,
                'old_canceled': old_canceled,
                'new_canceled': row.canceled,
                'new_status': new_status,
                'query_time_ms': round((query_end_time - query_start_time) * 1000, 2)
            })
            
            return row.canceled
        except Exception as e:
            # 记录异常
            favorites_logger.error("切换收藏状态异常", {
                'trace_id': trace_id,
                'favoriteid': favoriteid,
                'error': str(e),
                'error_type': type(e).__name__
            })
            traceback.print_exc()
            return None


if __name__ == '__main__':
    favorite_instance = Favorite()
