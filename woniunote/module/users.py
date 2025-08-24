import random
import time
import traceback
import uuid
from flask import session
from sqlalchemy import Table, Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from woniunote.common.database import dbconnect
# 从模型定义中导入 User 类
from woniunote.common.create_database import User  # 暂时保留此导入以兼容现有代码
from woniunote.common.unified_logging import get_simple_logger

# global dbsession, md, DBase
dbsession, md, DBase = dbconnect()

# 创建用户模块的日志记录器
users_logger = get_simple_logger('users')


# 生成用户模块的跟踪ID
def get_users_trace_id():
    return str(uuid.uuid4())


class Users:
    def __init__(self, **kwargs):
        # 动态创建表结构（只在第一次创建时）
        if not hasattr(Users, '_table_created'):
            try:
                self.__table__ = Table(
                    'users', md,
                    Column('userid', Integer, primary_key=True, nullable=False, autoincrement=True),
                    Column('username', String(50), nullable=False),
                    Column('password', String(32), nullable=False),
                    Column('nickname', String(30)),
                    Column('avatar', String(20)),
                    Column('qq', String(15)),
                    Column('role', String(10), nullable=False),
                    Column('credit', Integer, default=50),
                    Column('createtime', DateTime),
                    Column('updatetime', DateTime),
                    extend_existing=True  # 允许表已存在
                )
                Users._table_created = True
            except Exception as e:
                # 如果表创建失败，尝试使用现有的表定义
                try:
                    print(e)
                    self.__table__ = User.__table__
                    Users._table_created = True
                except Exception as e:
                    print(e)
                    pass

        # 设置属性
        for key, value in kwargs.items():
            setattr(self, key, value)

    # 查询用户名，可用于注册时判断用户名是否已注册，也可用于登录校验
    @staticmethod
    def find_by_username(username):
        # 生成跟踪ID
        trace_id = get_users_trace_id()

        # 记录查询开始
        users_logger.info("开始根据用户名查询用户", {
            'trace_id': trace_id,
            'username': username
        })

        try:
            # 尝试使用主数据库实例
            from woniunote.common.database import db
            if hasattr(db, 'session'):
                # 执行查询
                query_start_time = time.time()
                result = db.session.query(User).filter_by(username=username).all()
                query_end_time = time.time()

                # 记录查询结果
                users_logger.info("根据用户名查询用户成功", {
                    'trace_id': trace_id,
                    'username': username,
                    'result_count': len(result) if result else 0,
                    'query_time_ms': round((query_end_time - query_start_time) * 1000, 2)
                })

                return result
            else:
                # 执行查询
                query_start_time = time.time()
                result = dbsession.query(User).filter_by(username=username).all()
                query_end_time = time.time()

                # 记录查询结果
                users_logger.info("根据用户名查询用户成功", {
                    'trace_id': trace_id,
                    'username': username,
                    'result_count': len(result) if result else 0,
                    'query_time_ms': round((query_end_time - query_start_time) * 1000, 2)
                })

                return result
        except Exception as e:
            # 记录异常
            users_logger.error("根据用户名查询用户异常", {
                'trace_id': trace_id,
                'username': username,
                'error': str(e),
                'error_type': type(e).__name__
            })
            traceback.print_exc()
            return []

    # 实现注册，首次注册时用户只需要输入用户名和密码，所以只需要两个参数
    # 注册时，在模型类中为其他字段尽力生成一些可用的值，虽不全面，但可用
    # 通常用户注册时不建议填写太多资料，影响体验，可待用户后续逐步完善
    @staticmethod
    def do_register(username, password):
        # 生成跟踪ID
        trace_id = get_users_trace_id()

        # 记录注册开始
        users_logger.info("开始用户注册操作", {
            'trace_id': trace_id,
            'username': username
        })

        try:
            # 生成用户信息
            now = time.strftime('%Y-%m-%d %H:%M:%S')
            nickname = username.split('@')[0]  # 默认将邮箱账号前缀作为昵称
            avatar = str(random.randint(1, 15))  # 从15张头像图片中随机选择一张

            # 记录用户信息生成
            users_logger.info("生成用户初始信息", {
                'trace_id': trace_id,
                'username': username,
                'nickname': nickname,
                'avatar': avatar + '.png',
                'role': 'user',
                'credit': 50
            })

            # 创建用户对象
            user = Users(username=username, password=password, role='user', credit=50,
                         nickname=nickname, avatar=avatar + '.png', createtime=now, updatetime=now)
            # 执行数据库操作
            query_start_time = time.time()
            dbsession.add(user)
            dbsession.commit()
            query_end_time = time.time()

            # 记录注册成功
            users_logger.info("用户注册成功", {
                'trace_id': trace_id,
                'username': username,
                'userid': user.userid,
                'createtime': now,
                'query_time_ms': round((query_end_time - query_start_time) * 1000, 2)
            })

            return user
        except Exception as e:
            # 记录异常
            users_logger.error("用户注册异常", {
                'trace_id': trace_id,
                'username': username,
                'error': str(e),
                'error_type': type(e).__name__
            })
            traceback.print_exc()
            return None

    # 修改用户剩余积分，积分为正数表示增加积分，为负数表示减少积分
    @staticmethod
    def update_credit(credit):
        # 生成跟踪ID
        trace_id = get_users_trace_id()

        # 获取当前用户ID
        userid = session.get('userid')

        # 记录更新积分开始
        users_logger.info("开始更新用户积分", {
            'trace_id': trace_id,
            'userid': userid,
            'credit_change': credit
        })

        try:
            # 检查用户ID是否存在
            if not userid:
                # 记录用户ID不存在
                users_logger.warning("更新用户积分失败，用户ID不存在", {
                    'trace_id': trace_id,
                    'credit_change': credit
                })
                return False
            # 查询用户信息
            query_start_time = time.time()
            user = dbsession.query(User).filter_by(userid=userid).one()

            # 记录原始积分
            old_credit = int(user.credit)

            # 更新积分
            user.credit = old_credit + credit

            # 提交事务
            dbsession.commit()
            query_end_time = time.time()

            # 记录更新积分成功
            users_logger.info("更新用户积分成功", {
                'trace_id': trace_id,
                'userid': userid,
                'old_credit': old_credit,
                'credit_change': credit,
                'new_credit': user.credit,
                'query_time_ms': round((query_end_time - query_start_time) * 1000, 2)
            })

            return True
        except Exception as e:
            # 记录异常
            users_logger.error("更新用户积分异常", {
                'trace_id': trace_id,
                'userid': userid,
                'credit_change': credit,
                'error': str(e),
                'error_type': type(e).__name__
            })
            traceback.print_exc()
            return False

    @staticmethod
    def find_by_userid(userid):
        # 生成跟踪ID
        trace_id = get_users_trace_id()

        # 记录查询开始
        users_logger.info("开始根据用户ID查询用户", {
            'trace_id': trace_id,
            'userid': userid
        })

        try:
            # 执行查询
            query_start_time = time.time()
            user_model = dbsession.query(User).filter_by(userid=userid).one()
            query_end_time = time.time()

            # 记录查询结果
            users_logger.info("根据用户ID查询用户成功", {
                'trace_id': trace_id,
                'userid': userid,
                'username': user_model.username if user_model else None,
                'query_time_ms': round((query_end_time - query_start_time) * 1000, 2)
            })

            # 将User模型对象转换为Users管理类对象，保持向后兼容
            if user_model:
                user_instance = Users()
                user_instance.userid = user_model.userid
                user_instance.username = user_model.username
                user_instance.password = user_model.password
                user_instance.nickname = user_model.nickname
                user_instance.avatar = user_model.avatar
                user_instance.qq = user_model.qq
                user_instance.role = user_model.role
                user_instance.credit = user_model.credit
                user_instance.createtime = user_model.createtime
                user_instance.updatetime = user_model.updatetime
                return user_instance

            return None
        except Exception as e:
            # 记录异常
            users_logger.error("根据用户ID查询用户异常", {
                'trace_id': trace_id,
                'userid': userid,
                'error': str(e),
                'error_type': type(e).__name__
            })
            traceback.print_exc()
            return None


if __name__ == '__main__':
    user_instance = Users()
