import uuid
import datetime
from woniunote.common.database import dbconnect
from woniunote.common.create_database import Favorite
from woniunote.common.unified_logging import get_simple_logger

# 创建收藏模块的日志记录器
favorites_logger = get_simple_logger('favorites')

# 生成收藏模块的跟踪ID
def get_favorites_trace_id():
    return str(uuid.uuid4())

class Favorites:
    """收藏管理类 - 所有方法都是静态方法"""

    @staticmethod
    def check_favorite(articleid):
        """检查是否已收藏"""
        trace_id = get_favorites_trace_id()
        try:
            userid = None
            from flask import session
            try:
                userid = session.get('userid')
            except RuntimeError:
                # 没有应用上下文
                pass
            
            if not userid:
                favorites_logger.info("用户未登录，跳过收藏检查", {
                    'trace_id': trace_id,
                    'articleid': articleid
                })
                return False

            # 动态获取数据库连接
            dbsession, md, DBase = dbconnect()
            if dbsession is None:
                favorites_logger.error("无法获取数据库连接", {
                    'trace_id': trace_id,
                    'articleid': articleid
                })
                return False

            # 查询收藏记录
            favorite_record = dbsession.query(Favorite).filter_by(
                userid=userid,
                articleid=articleid
            ).first()

            if favorite_record:
                favorites_logger.info("找到收藏记录", {
                    'trace_id': trace_id,
                    'articleid': articleid,
                    'userid': userid
                })
                return True
            else:
                favorites_logger.info("未找到收藏记录", {
                    'trace_id': trace_id,
                    'articleid': articleid,
                    'userid': userid
                })
                return False

        except Exception as e:
            favorites_logger.error("检查收藏异常", {
                'trace_id': trace_id,
                'articleid': articleid,
                'error': str(e)
            })
            return False

    @staticmethod
    def find_by_userid(userid):
        """根据用户ID查找收藏"""
        trace_id = get_favorites_trace_id()
        favorites_logger.info("开始根据用户ID查询收藏", {
            'trace_id': trace_id,
            'userid': userid
        })

        try:
            # 动态获取数据库连接
            dbsession, md, DBase = dbconnect()
            if dbsession is None:
                favorites_logger.error("无法获取数据库连接", {
                    'trace_id': trace_id,
                    'userid': userid
                })
                return []

            # 查询收藏记录
            favorites = dbsession.query(Favorite).filter_by(userid=userid).order_by(Favorite.createtime.desc()).all()

            favorites_logger.info("根据用户ID查询收藏成功", {
                'trace_id': trace_id,
                'userid': userid,
                'favorites_count': len(favorites)
            })

            return favorites

        except Exception as e:
            favorites_logger.error("根据用户ID查询收藏异常", {
                'trace_id': trace_id,
                'userid': userid,
                'error': str(e)
            })
            return []
