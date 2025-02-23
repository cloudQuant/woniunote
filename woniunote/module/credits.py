from flask import session
from sqlalchemy import Table, Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from woniunote.common.database import dbconnect
from woniunote.module.users import Users
from woniunote.common.create_database import Credit
import time
import traceback

dbsession, md, DBase = dbconnect()


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
        try:
            now = time.strftime('%Y-%m-%d %H:%M:%S')
            credit = Credit(userid=session.get('userid'), category=credit_type, target=target,
                            credit=credit, createtime=now, updatetime=now)
            dbsession.add(credit)
            dbsession.commit()
        except Exception as e:
            print(e)
            traceback.print_exc()

    # 判断用户是否已经消耗积分
    @staticmethod
    def check_payed_article(articleid):
        try:
            result = dbsession.query(Credit).filter_by(userid=session.get('userid'), target=articleid).all()
            if len(result) > 0:
                return True
            else:
                return False
        except Exception as e:
            print(e)
            traceback.print_exc()


if __name__ == '__main__':
    credit_obj = Credit()
