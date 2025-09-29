import uuid
import datetime
from woniunote.common.database import dbconnect
from woniunote.common.create_database import Credit
from woniunote.common.unified_logging import get_simple_logger

# 创建积分模块的日志记录器
credits_logger = get_simple_logger('credits')

# 生成积分模块的跟踪ID
def get_credits_trace_id():
    return str(uuid.uuid4())

class Credits:
    """积分管理类 - 所有方法都是静态方法"""

    @staticmethod
    def check_payed_article(articleid):
        """检查文章是否已经付费"""
        trace_id = get_credits_trace_id()
        try:
            userid = None
            from flask import session
            try:
                userid = session.get('userid')
            except RuntimeError:
                # 没有应用上下文
                pass
            
            if not userid:
                credits_logger.info("用户未登录，跳过积分检查", {
                    'trace_id': trace_id,
                    'articleid': articleid
                })
                return False

            # 动态获取数据库连接
            dbsession, md, DBase = dbconnect()
            if dbsession is None:
                credits_logger.error("无法获取数据库连接", {
                    'trace_id': trace_id,
                    'articleid': articleid
                })
                return False

            # 查询积分记录
            credit_record = dbsession.query(Credit).filter_by(
                userid=userid,
                target=articleid,
                credit_type='article'
            ).first()

            if credit_record:
                credits_logger.info("找到积分消耗记录", {
                    'trace_id': trace_id,
                    'articleid': articleid,
                    'userid': userid
                })
                return True
            else:
                credits_logger.info("未找到积分消耗记录", {
                    'trace_id': trace_id,
                    'articleid': articleid,
                    'userid': userid
                })
                return False

        except Exception as e:
            credits_logger.error("检查积分消耗异常", {
                'trace_id': trace_id,
                'articleid': articleid,
                'error': str(e)
            })
            return False

    @staticmethod
    def insert_detail(credit_type, target, credit):
        """插入积分详情"""
        trace_id = get_credits_trace_id()
        try:
            userid = None
            from flask import session
            try:
                userid = session.get('userid')
            except RuntimeError:
                # 没有应用上下文
                pass
            
            if not userid:
                credits_logger.info("用户未登录，跳过积分记录", {
                    'trace_id': trace_id,
                    'target': target
                })
                return None

            # 动态获取数据库连接
            dbsession, md, DBase = dbconnect()
            if dbsession is None:
                credits_logger.error("无法获取数据库连接", {
                    'trace_id': trace_id
                })
                return None

            # 创建积分记录
            new_credit = Credit()
            new_credit.userid = userid
            new_credit.credit_type = credit_type
            new_credit.target = target
            new_credit.credit = credit
            new_credit.createtime = datetime.datetime.now()

            dbsession.add(new_credit)
            dbsession.commit()

            credits_logger.info("积分记录创建成功", {
                'trace_id': trace_id,
                'userid': userid,
                'credit_type': credit_type,
                'target': target,
                'credit': credit
            })

            return new_credit

        except Exception as e:
            credits_logger.error("积分记录创建异常", {
                'trace_id': trace_id,
                'error': str(e)
            })
            return None

    @staticmethod
    def find_by_userid(userid):
        """根据用户ID查询积分记录"""
        trace_id = get_credits_trace_id()
        credits_logger.info("开始根据用户ID查询积分记录", {
            'trace_id': trace_id,
            'userid': userid
        })

        try:
            # 动态获取数据库连接
            dbsession, md, DBase = dbconnect()
            if dbsession is None:
                credits_logger.error("无法获取数据库连接", {
                    'trace_id': trace_id,
                    'userid': userid
                })
                return []

            # 查询积分记录
            credits = dbsession.query(Credit).filter_by(userid=userid).order_by(Credit.createtime.desc()).all()

            credits_logger.info("根据用户ID查询积分记录成功", {
                'trace_id': trace_id,
                'userid': userid,
                'credits_count': len(credits)
            })

            return credits

        except Exception as e:
            credits_logger.error("根据用户ID查询积分记录异常", {
                'trace_id': trace_id,
                'userid': userid,
                'error': str(e)
            })
            return []
