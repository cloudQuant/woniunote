import uuid
from woniunote.common.database import dbconnect
from woniunote.common.create_database import User
from woniunote.common.unified_logging import get_simple_logger

# 创建用户模块的日志记录器
users_logger = get_simple_logger('users')

# 生成用户模块的跟踪ID
def get_users_trace_id():
    return str(uuid.uuid4())

class Users:
    """用户管理类 - 所有方法都是静态方法"""

    @staticmethod
    def find_by_userid(userid):
        """根据用户ID查询用户"""
        trace_id = get_users_trace_id()
        users_logger.info("开始根据用户ID查询用户", {
            'trace_id': trace_id,
            'userid': userid
        })

        try:
            # 动态获取数据库连接
            dbsession, md, DBase = dbconnect()
            if dbsession is None:
                users_logger.error("无法获取数据库连接", {'trace_id': trace_id})
                return None

            user_model = dbsession.query(User).filter_by(userid=userid).first()

            if user_model:
                users_logger.info("根据用户ID查询用户成功", {
                    'trace_id': trace_id,
                    'userid': userid,
                    'username': user_model.username
                })
                return user_model
            else:
                users_logger.warning("用户不存在", {
                    'trace_id': trace_id,
                    'userid': userid
                })
                return None

        except Exception as e:
            users_logger.error("根据用户ID查询用户异常", {
                'trace_id': trace_id,
                'userid': userid,
                'error': str(e)
            })
            return None

    @staticmethod
    def find_by_username(username):
        """根据用户名查询用户"""
        trace_id = get_users_trace_id()
        users_logger.info("开始根据用户名查询用户", {
            'trace_id': trace_id,
            'username': username
        })

        try:
            # 动态获取数据库连接
            dbsession, md, DBase = dbconnect()
            if dbsession is None:
                users_logger.error("无法获取数据库连接", {'trace_id': trace_id})
                return None

            user_model = dbsession.query(User).filter_by(username=username).first()

            if user_model:
                users_logger.info("根据用户名查询用户成功", {
                    'trace_id': trace_id,
                    'username': username,
                    'userid': user_model.userid
                })
                return user_model
            else:
                users_logger.warning("用户不存在", {
                    'trace_id': trace_id,
                    'username': username
                })
                return None

        except Exception as e:
            users_logger.error("根据用户名查询用户异常", {
                'trace_id': trace_id,
                'username': username,
                'error': str(e)
            })
            return None
