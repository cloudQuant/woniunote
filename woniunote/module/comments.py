import uuid
import datetime
from woniunote.common.database import dbconnect
from woniunote.common.create_database import Comment
from woniunote.common.unified_logging import get_simple_logger

# 创建评论模块的日志记录器
comments_logger = get_simple_logger('comments')

# 生成评论模块的跟踪ID
def get_comments_trace_id():
    return str(uuid.uuid4())

class Comments:
    """评论管理类 - 所有方法都是静态方法"""

    @staticmethod
    def find_by_articleid(articleid):
        """根据文章ID查找评论"""
        trace_id = get_comments_trace_id()
        comments_logger.info("开始根据文章ID查询评论", {
            'trace_id': trace_id,
            'articleid': articleid
        })

        try:
            # 动态获取数据库连接
            dbsession, md, DBase = dbconnect()
            if dbsession is None:
                comments_logger.error("无法获取数据库连接", {
                    'trace_id': trace_id,
                    'articleid': articleid
                })
                return []

            # 查询评论
            comments = dbsession.query(Comment).filter_by(
                articleid=articleid
            ).order_by(Comment.createtime.desc()).all()

            comments_logger.info("根据文章ID查询评论成功", {
                'trace_id': trace_id,
                'articleid': articleid,
                'comment_count': len(comments)
            })

            return comments

        except Exception as e:
            comments_logger.error("根据文章ID查询评论异常", {
                'trace_id': trace_id,
                'articleid': articleid,
                'error': str(e)
            })
            return []

    @staticmethod
    def find_by_userid(userid):
        """根据用户ID查找评论"""
        trace_id = get_comments_trace_id()
        comments_logger.info("开始根据用户ID查询评论", {
            'trace_id': trace_id,
            'userid': userid
        })

        try:
            # 动态获取数据库连接
            dbsession, md, DBase = dbconnect()
            if dbsession is None:
                comments_logger.error("无法获取数据库连接", {
                    'trace_id': trace_id,
                    'userid': userid
                })
                return []

            # 查询评论
            comments = dbsession.query(Comment).filter_by(userid=userid).order_by(Comment.createtime.desc()).all()

            comments_logger.info("根据用户ID查询评论成功", {
                'trace_id': trace_id,
                'userid': userid,
                'comment_count': len(comments)
            })

            return comments

        except Exception as e:
            comments_logger.error("根据用户ID查询评论异常", {
                'trace_id': trace_id,
                'userid': userid,
                'error': str(e)
            })
            return []
