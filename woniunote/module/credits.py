from flask import session
from sqlalchemy import Table, Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from woniunote.common.database import dbconnect
from woniunote.module.users import Users
from woniunote.common.create_database import Credit
import time
import traceback
import uuid
from woniunote.common.simple_logger import get_simple_logger

dbsession, md, DBase = dbconnect()

# 创建积分模块的日志记录器
credits_logger = get_simple_logger('credits')

# 生成积分模块的跟踪ID
def get_credits_trace_id():
    return str(uuid.uuid4())


class Credits(DBase):
    __table__ = Table(
        'credit', md,
        Column('creditid', Integer, primary_key=True, nullable=False, autoincrement=True),
        Column('userid', Integer, ForeignKey('users.userid'), nullable=False),
        Column('category', String(10)),
        Column('target', Integer),
        Column('credit', Integer),
        Column('createtime', DateTime),
        Column('updatetime', DateTime)
    )

    # 定义外键关系
    # user = relationship("Users", foreign_keys=[__table__.c.userid],
    #                     primaryjoin="Credit.userid == Users.userid")
    # user = relationship("Users", foreign_keys=[__table__.c.userid])
    # user = relationship("Users", back_populates="credit", lazy='dynamic')

    # 延迟导入 Users
    def __init__(self):
        from woniunote.module.users import Users
        self.user = relationship("Users", back_populates="credits")

    # 插入积分明细数据
    @staticmethod
    def insert_detail(credit_type, target, credit):
        # 生成跟踪ID
        trace_id = get_credits_trace_id()
        
        # 获取当前用户ID
        userid = session.get('userid')
        
        # 记录积分插入开始
        credits_logger.info("开始插入积分明细", {
            'trace_id': trace_id,
            'userid': userid,
            'credit_type': credit_type,
            'target': target,
            'credit': credit
        })
        
        try:
            # 检查用户ID是否存在
            if not userid:
                # 记录用户ID不存在
                credits_logger.warning("插入积分明细失败，用户ID不存在", {
                    'trace_id': trace_id,
                    'credit_type': credit_type,
                    'target': target,
                    'credit': credit
                })
                return None
                
            # 执行插入
            now = time.strftime('%Y-%m-%d %H:%M:%S')
            credit_obj = Credit(userid=userid, category=credit_type, target=target,
                            credit=credit, createtime=now, updatetime=now)
            dbsession.add(credit_obj)
            dbsession.commit()
            
            # 记录积分插入成功
            credits_logger.info("插入积分明细成功", {
                'trace_id': trace_id,
                'userid': userid,
                'credit_type': credit_type,
                'target': target,
                'credit': credit,
                'creditid': credit_obj.creditid
            })
            
            return credit_obj
        except Exception as e:
            # 记录异常
            credits_logger.error("插入积分明细异常", {
                'trace_id': trace_id,
                'userid': userid,
                'credit_type': credit_type,
                'target': target,
                'credit': credit,
                'error': str(e),
                'error_type': type(e).__name__
            })
            traceback.print_exc()
            return None

    # 判断用户是否已经消耗积分
    @staticmethod
    def check_payed_article(articleid):
        # 生成跟踪ID
        trace_id = get_credits_trace_id()
        
        # 获取当前用户ID
        userid = session.get('userid')
        
        # 记录检查开始
        credits_logger.info("开始检查用户是否已消耗积分", {
            'trace_id': trace_id,
            'userid': userid,
            'articleid': articleid
        })
        
        try:
            # 检查用户ID是否存在
            if not userid:
                # 记录用户ID不存在
                credits_logger.warning("检查积分消耗失败，用户ID不存在", {
                    'trace_id': trace_id,
                    'articleid': articleid
                })
                return False
                
            # 执行查询
            query_start_time = time.time()
            result = dbsession.query(Credit).filter_by(userid=userid, target=articleid).first()
            query_end_time = time.time()
            
            is_payed = True if result else False
            
            # 记录检查结果
            credits_logger.info("检查用户是否已消耗积分成功", {
                'trace_id': trace_id,
                'userid': userid,
                'articleid': articleid,
                'is_payed': is_payed,
                'query_time_ms': round((query_end_time - query_start_time) * 1000, 2)
            })
            
            return is_payed
        except Exception as e:
            # 记录异常
            credits_logger.error("检查用户是否已消耗积分异常", {
                'trace_id': trace_id,
                'userid': userid,
                'articleid': articleid,
                'error': str(e),
                'error_type': type(e).__name__
            })
            traceback.print_exc()
            return False

    # 获取用户积分明细
    @staticmethod
    def find_by_userid(userid):
        # 生成跟踪ID
        trace_id = get_credits_trace_id()
        
        # 记录查询开始
        credits_logger.info("开始查询用户积分明细", {
            'trace_id': trace_id,
            'userid': userid
        })
        
        try:
            # 执行查询
            query_start_time = time.time()
            result = dbsession.query(Credit).filter_by(userid=userid).order_by(Credit.creditid.desc()).all()
            query_end_time = time.time()
            
            # 记录查询结果
            credits_logger.info("查询用户积分明细成功", {
                'trace_id': trace_id,
                'userid': userid,
                'result_count': len(result) if result else 0,
                'query_time_ms': round((query_end_time - query_start_time) * 1000, 2)
            })
            
            return result
        except Exception as e:
            # 记录异常
            credits_logger.error("查询用户积分明细异常", {
                'trace_id': trace_id,
                'userid': userid,
                'error': str(e),
                'error_type': type(e).__name__
            })
            traceback.print_exc()
            return []


if __name__ == '__main__':
    credit_obj = Credit()
