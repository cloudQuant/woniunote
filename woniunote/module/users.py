import random
import time
import traceback
from flask import session
from sqlalchemy import Table, Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from woniunote.common.database import dbconnect
from woniunote.common.create_database import User

dbsession, md, DBase = dbconnect()


class Users(DBase):
    __table__ = Table(
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
        Column('updatetime', DateTime)
    )

    # 查询用户名，可用于注册时判断用户名是否已注册，也可用于登录校验
    @staticmethod
    def find_by_username(username):
        try:
            result = dbsession.query(Users).filter_by(username=username).all()
            return result
        except Exception as e:
            print(e)
            traceback.print_exc()

    # 实现注册，首次注册时用户只需要输入用户名和密码，所以只需要两个参数
    # 注册时，在模型类中为其他字段尽力生成一些可用的值，虽不全面，但可用
    # 通常用户注册时不建议填写太多资料，影响体验，可待用户后续逐步完善
    @staticmethod
    def do_register(username, password):
        try:
            now = time.strftime('%Y-%m-%d %H:%M:%S')
            nickname = username.split('@')[0]  # 默认将邮箱账号前缀作为昵称
            avatar = str(random.randint(1, 15))  # 从15张头像图片中随机选择一张
            user = Users(username=username, password=password, role='user', credit=50,
                         nickname=nickname, avatar=avatar + '.png', createtime=now, updatetime=now)
            dbsession.add(user)
            dbsession.commit()
            return user
        except Exception as e:
            print(e)
            traceback.print_exc()

    # 修改用户剩余积分，积分为正数表示增加积分，为负数表示减少积分
    @staticmethod
    def update_credit(credit):
        try:
            user = dbsession.query(Users).filter_by(userid=session.get('userid')).one()
            user.credit = int(user.credit) + credit
            dbsession.commit()
        except Exception as e:
            print(e)
            traceback.print_exc()

    @staticmethod
    def find_by_userid(userid):
        try:
            user = dbsession.query(Users).filter_by(userid=userid).one()
            return user
        except Exception as e:
            print(e)
            traceback.print_exc()


if __name__ == '__main__':
    user_instance = Users()

