import time
import traceback
import uuid
from woniunote.common.utils import model_join_list
from flask import session
from sqlalchemy import Table, Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from woniunote.common.database import dbconnect
from woniunote.module.users import Users
from woniunote.common.create_database import Comment
from woniunote.common.simple_logger import get_simple_logger

dbsession, md, DBase = dbconnect()

# 创建评论模块的日志记录器
comments_logger = get_simple_logger('comments')

# 生成评论模块的跟踪ID
def get_comments_trace_id():
    return str(uuid.uuid4())


class Comments(DBase):
    __table__ = Table(
        'comment', md,
        Column('commentid', Integer, primary_key=True, nullable=False, autoincrement=True),
        Column('userid', Integer, ForeignKey('users.userid'), nullable=False),
        Column('articleid', Integer, ForeignKey('article.articleid'), nullable=False),
        Column('content', Text(65536), nullable=False),
        Column('ipaddr', String(30)),
        Column('replyid', Integer),
        Column('agreecount', Integer, default=0),
        Column('opposecount', Integer, default=0),
        Column('hidden', Integer, default=0),
        Column('createtime', DateTime),
        Column('updatetime', DateTime)
    )

    def __init__(self):
        self.user = relationship("Users", back_populates="Comments")
        self.article = relationship("Articles", back_populates="Comments")

    # # 定义外键关系
    # user = relationship("Users",
    #                     foreign_keys=[__table__.c.userid],
    #                     primaryjoin="Comment.userid == Users.userid")
    # article = relationship("Article",
    #                        foreign_keys=[__table__.c.articleid],
    #                        primaryjoin="Comment.articleid == Article.articleid")

    # 新增一条评论
    @staticmethod
    def insert_comment(articleid, content, ipaddr):
        # 生成跟踪ID
        trace_id = get_comments_trace_id()
        
        # 记录评论插入开始
        comments_logger.info("开始插入评论", {
            'trace_id': trace_id,
            'articleid': articleid,
            'ipaddr': ipaddr,
            'user_id': session.get('main_userid') if session.get('main_islogin') == 'true' else None
        })
        
        try:
            userid = session.get('main_userid')
            if not userid:
                # 记录用户ID不存在
                comments_logger.warning("插入评论失败，用户ID不存在", {
                    'trace_id': trace_id,
                    'articleid': articleid
                })
                return None
                
            now = time.strftime('%Y-%m-%d %H:%M:%S')
            comment = Comment(userid=userid, articleid=articleid,
                            content=content, ipaddr=ipaddr,
                            createtime=now, updatetime=now)
            dbsession.add(comment)
            dbsession.commit()
            
            # 记录评论插入成功
            comments_logger.info("插入评论成功", {
                'trace_id': trace_id,
                'articleid': articleid,
                'commentid': comment.commentid,
                'userid': userid,
                'ipaddr': ipaddr
            })
            
            return comment
        except Exception as e:
            # 记录异常
            comments_logger.error("插入评论异常", {
                'trace_id': trace_id,
                'articleid': articleid,
                'userid': session.get('main_userid'),
                'error': str(e),
                'error_type': type(e).__name__
            })
            traceback.print_exc()
            return None

    # 根据用户编号查询所有评论
    @staticmethod
    def find_by_userid(userid):
        # 生成跟踪ID
        trace_id = get_comments_trace_id()
        
        # 记录查询开始
        comments_logger.info("开始根据用户ID查询评论", {
            'trace_id': trace_id,
            'userid': userid
        })
        
        try:
            # 执行查询
            query_start_time = time.time()
            # 查询用户的所有评论，并关联文章信息
            results = dbsession.query(Comment, Article)\
                .join(Article, Comment.articleid == Article.articleid)\
                .filter(Comment.userid == userid)\
                .filter(Comment.hidden == 0)\
                .order_by(Comment.commentid.desc())\
                .all()
            query_end_time = time.time()
            
            # 记录查询结果
            comments_logger.info("根据用户ID查询评论成功", {
                'trace_id': trace_id,
                'userid': userid,
                'result_count': len(results) if results else 0,
                'query_time_ms': round((query_end_time - query_start_time) * 1000, 2)
            })
            
            return results
        except Exception as e:
            # 记录异常
            comments_logger.error("根据用户ID查询评论异常", {
                'trace_id': trace_id,
                'userid': userid,
                'error': str(e),
                'error_type': type(e).__name__
            })
            traceback.print_exc()
            return []

    # 根据文章编号查询所有评论
    @staticmethod
    def find_by_articleid(articleid):
        # 生成跟踪ID
        trace_id = get_comments_trace_id()
        
        # 记录查询开始
        comments_logger.info("开始根据文章ID查询评论", {
            'trace_id': trace_id,
            'articleid': articleid
        })
        
        try:
            # 执行查询
            query_start_time = time.time()
            result = dbsession.query(Comment).filter_by(articleid=articleid, hidden=0, replyid=0).all()
            query_end_time = time.time()
            
            # 记录查询结果
            comments_logger.info("根据文章ID查询评论成功", {
                'trace_id': trace_id,
                'articleid': articleid,
                'result_count': len(result) if result else 0,
                'query_time_ms': round((query_end_time - query_start_time) * 1000, 2)
            })
            
            return result
        except Exception as e:
            # 记录异常
            comments_logger.error("根据文章ID查询评论异常", {
                'trace_id': trace_id,
                'articleid': articleid,
                'error': str(e),
                'error_type': type(e).__name__
            })
            traceback.print_exc()
            return []

    # 根据用户编号和日期进行查询是否已经超过每天5条限制
    @staticmethod
    def check_limit_per_5():
        # 生成跟踪ID
        trace_id = get_comments_trace_id()
        
        # 获取当前用户ID
        userid = session.get('userid')
        
        # 记录查询开始
        comments_logger.info("开始检查用户评论数量限制", {
            'trace_id': trace_id,
            'userid': userid
        })
        
        try:
            # 执行查询
            query_start_time = time.time()
            start = time.strftime("%Y-%m-%d 00:00:00")  # 当天的起始时间
            end = time.strftime("%Y-%m-%d 23:59:59")  # 当天的结束时间
            result = dbsession.query(Comment).filter(Comment.userid == userid,
                                                     Comment.createtime.between(start, end)).all()
            query_end_time = time.time()
            
            comment_count = len(result) if result else 0
            is_limited = comment_count >= 5
            
            # 记录查询结果
            comments_logger.info("检查用户评论数量限制成功", {
                'trace_id': trace_id,
                'userid': userid,
                'comment_count': comment_count,
                'is_limited': is_limited,
                'date': time.strftime("%Y-%m-%d"),
                'query_time_ms': round((query_end_time - query_start_time) * 1000, 2)
            })
            
            return is_limited  # 返回True表示今天已经不能再发表评论
        except Exception as e:
            # 记录异常
            comments_logger.error("检查用户评论数量限制异常", {
                'trace_id': trace_id,
                'userid': userid,
                'error': str(e),
                'error_type': type(e).__name__
            })
            traceback.print_exc()
            return False  # 出错时默认不限制

    # 查询评论与用户信息，注意评论也需要分页 [(Comment, Users), (Comment, Users)]
    @staticmethod
    def find_limit_with_user(articleid, start, count):
        # 生成跟踪ID
        trace_id = get_comments_trace_id()
        
        # 记录查询开始
        comments_logger.info("开始查询带用户信息的评论", {
            'trace_id': trace_id,
            'articleid': articleid,
            'start': start,
            'count': count
        })
        
        try:
            # 执行查询
            query_start_time = time.time()
            result = dbsession.query(Comment, Users).join(Users, Users.userid == Comment.userid).filter(
                Comment.articleid == articleid, Comment.hidden == 0).order_by(
                Comment.commentid.desc()).limit(count).offset(start).all()
            query_end_time = time.time()
            
            # 记录查询结果
            comments_logger.info("查询带用户信息的评论成功", {
                'trace_id': trace_id,
                'articleid': articleid,
                'start': start,
                'count': count,
                'result_count': len(result) if result else 0,
                'query_time_ms': round((query_end_time - query_start_time) * 1000, 2)
            })
            
            return result
        except Exception as e:
            # 记录异常
            comments_logger.error("查询带用户信息的评论异常", {
                'trace_id': trace_id,
                'articleid': articleid,
                'start': start,
                'count': count,
                'error': str(e),
                'error_type': type(e).__name__
            })
            traceback.print_exc()
            return []

    @staticmethod
    def find_all():
        # 生成跟踪ID
        trace_id = get_comments_trace_id()
        
        # 记录查询开始
        comments_logger.info("开始查询所有评论", {
            'trace_id': trace_id
        })
        
        try:
            # 执行查询
            query_start_time = time.time()
            result = dbsession.query(Comment).all()
            query_end_time = time.time()
            
            # 记录查询结果
            comments_logger.info("查询所有评论成功", {
                'trace_id': trace_id,
                'result_count': len(result) if result else 0,
                'query_time_ms': round((query_end_time - query_start_time) * 1000, 2)
            })
            
            return result
        except Exception as e:
            # 记录异常
            comments_logger.error("查询所有评论异常", {
                'trace_id': trace_id,
                'error': str(e),
                'error_type': type(e).__name__
            })
            traceback.print_exc()
            return []

    # 新增一条回复，将原始评论的ID作为新评论的replyid字段来进行关联
    @staticmethod
    def insert_reply(articleid, commentid, content, ipaddr):
        # 生成跟踪ID
        trace_id = get_comments_trace_id()
        
        # 获取当前用户ID
        userid = session.get('userid')
        
        # 记录回复插入开始
        comments_logger.info("开始插入评论回复", {
            'trace_id': trace_id,
            'articleid': articleid,
            'commentid': commentid,
            'ipaddr': ipaddr,
            'userid': userid
        })
        
        try:
            # 检查用户ID是否存在
            if not userid:
                # 记录用户ID不存在
                comments_logger.warning("插入评论回复失败，用户ID不存在", {
                    'trace_id': trace_id,
                    'articleid': articleid,
                    'commentid': commentid
                })
                return None
                
            # 执行插入
            now = time.strftime('%Y-%m-%d %H:%M:%S')
            comment = Comment(userid=userid, articleid=articleid,
                              content=content, ipaddr=ipaddr, replyid=commentid,
                              createtime=now, updatetime=now)
            dbsession.add(comment)
            dbsession.commit()
            
            # 记录回复插入成功
            comments_logger.info("插入评论回复成功", {
                'trace_id': trace_id,
                'articleid': articleid,
                'commentid': commentid,
                'reply_commentid': comment.commentid,
                'userid': userid,
                'ipaddr': ipaddr
            })
            
            return comment
        except Exception as e:
            # 记录异常
            comments_logger.error("插入评论回复异常", {
                'trace_id': trace_id,
                'articleid': articleid,
                'commentid': commentid,
                'userid': userid,
                'error': str(e),
                'error_type': type(e).__name__
            })
            traceback.print_exc()
            return None

    # 查询原始评论与对应的用户信息，带分页参数
    @staticmethod
    def find_comment_with_user(articleid, start, count):
        # 生成跟踪ID
        trace_id = get_comments_trace_id()
        
        # 记录查询开始
        comments_logger.info("开始查询原始评论及用户信息", {
            'trace_id': trace_id,
            'articleid': articleid,
            'start': start,
            'count': count
        })
        
        try:
            # 执行查询
            query_start_time = time.time()
            result = dbsession.query(Comment, Users).join(
                Users, Users.userid == Comment.userid).filter(
                Comment.articleid == articleid,
                Comment.hidden == 0,
                Comment.replyid == 0).order_by(
                Comment.commentid.desc()).limit(count).offset(start).all()
            query_end_time = time.time()
            
            # 记录查询结果
            comments_logger.info("查询原始评论及用户信息成功", {
                'trace_id': trace_id,
                'articleid': articleid,
                'start': start,
                'count': count,
                'result_count': len(result) if result else 0,
                'query_time_ms': round((query_end_time - query_start_time) * 1000, 2)
            })
            
            return result
        except Exception as e:
            # 记录异常
            comments_logger.error("查询原始评论及用户信息异常", {
                'trace_id': trace_id,
                'articleid': articleid,
                'start': start,
                'count': count,
                'error': str(e),
                'error_type': type(e).__name__
            })
            traceback.print_exc()
            return []

    # 查询回复评论，回复评论不需要分页
    @staticmethod
    def find_reply_with_user(replyid):
        # 生成跟踪ID
        trace_id = get_comments_trace_id()
        
        # 记录查询开始
        comments_logger.info("开始查询回复评论及用户信息", {
            'trace_id': trace_id,
            'replyid': replyid
        })
        
        try:
            # 执行查询
            query_start_time = time.time()
            result = dbsession.query(Comment, Users).join(Users, Users.userid ==
                                                          Comment.userid).filter(Comment.replyid == replyid,
                                                                                 Comment.hidden == 0).all()
            query_end_time = time.time()
            
            # 记录查询结果
            comments_logger.info("查询回复评论及用户信息成功", {
                'trace_id': trace_id,
                'replyid': replyid,
                'result_count': len(result) if result else 0,
                'query_time_ms': round((query_end_time - query_start_time) * 1000, 2)
            })
            
            return result
        except Exception as e:
            # 记录异常
            comments_logger.error("查询回复评论及用户信息异常", {
                'trace_id': trace_id,
                'replyid': replyid,
                'error': str(e),
                'error_type': type(e).__name__
            })
            traceback.print_exc()
            return []

    # 根据原始评论和回复评论生成一个关联列表
    def get_comment_user_list(self, articleid, start, count):
        # 生成跟踪ID
        trace_id = get_comments_trace_id()
        
        # 记录查询开始
        comments_logger.info("开始生成评论及回复关联列表", {
            'trace_id': trace_id,
            'articleid': articleid,
            'start': start,
            'count': count
        })
        
        try:
            # 执行查询
            query_start_time = time.time()
            
            # 查询原始评论
            result = self.find_comment_with_user(articleid, start, count)
            comment_list = model_join_list(result)  # 原始评论的连接结果
            
            # 记录原始评论查询结果
            comments_logger.info("查询原始评论成功", {
                'trace_id': trace_id,
                'articleid': articleid,
                'comment_count': len(comment_list) if comment_list else 0
            })
            
            # 查询每个原始评论的回复
            reply_count = 0
            for comment in comment_list:
                # 查询原始评论对应的回复评论,并转换为列表保存到comment_list中
                result = self.find_reply_with_user(comment['commentid'])
                # 为comment_list列表中的原始评论字典对象添加一个新Key叫reply_list
                # 用于存储当前这条原始评论的所有回复评论,如果无回复评论则列表值为空
                replies = model_join_list(result)
                comment['reply_list'] = replies
                reply_count += len(replies) if replies else 0
                
            query_end_time = time.time()
            
            # 记录总体查询结果
            comments_logger.info("生成评论及回复关联列表成功", {
                'trace_id': trace_id,
                'articleid': articleid,
                'start': start,
                'count': count,
                'comment_count': len(comment_list) if comment_list else 0,
                'reply_count': reply_count,
                'query_time_ms': round((query_end_time - query_start_time) * 1000, 2)
            })
            
            return comment_list  # 将新的数据结构返回给控制器接口
        except Exception as e:
            # 记录异常
            comments_logger.error("生成评论及回复关联列表异常", {
                'trace_id': trace_id,
                'articleid': articleid,
                'start': start,
                'count': count,
                'error': str(e),
                'error_type': type(e).__name__
            })
            traceback.print_exc()
            return []

    # 查询某篇文章的原始评论总数量
    @staticmethod
    def get_count_by_article(articleid):
        # 生成跟踪ID
        trace_id = get_comments_trace_id()
        
        # 记录统计开始
        comments_logger.info("开始统计文章评论数量", {
            'trace_id': trace_id,
            'articleid': articleid
        })
        
        try:
            # 执行统计查询
            query_start_time = time.time()
            count = dbsession.query(Comment).filter_by(articleid=articleid, hidden=0, replyid=0).count()
            query_end_time = time.time()
            
            # 记录统计结果
            comments_logger.info("统计文章评论数量成功", {
                'trace_id': trace_id,
                'articleid': articleid,
                'count': count,
                'query_time_ms': round((query_end_time - query_start_time) * 1000, 2)
            })
            
            return count
        except Exception as e:
            # 记录异常
            comments_logger.error("统计文章评论数量异常", {
                'trace_id': trace_id,
                'articleid': articleid,
                'error': str(e),
                'error_type': type(e).__name__
            })
            traceback.print_exc()
            return 0


if __name__ == '__main__':
    comment_instance = Comment()
