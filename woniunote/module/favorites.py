import time
import traceback
from flask import session
from sqlalchemy import Table, Column, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from woniunote.common.database import dbconnect
from woniunote.module.articles import Article
from woniunote.common.create_database import Favorite

dbsession, md, DBase = dbconnect()


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

    # 播入文章收藏数据
    @staticmethod
    def insert_favorite(articleid):
        try:
            userid = session.get('main_userid')
            if not userid:
                print("No user ID found in session")
                return False
                
            row = dbsession.query(Favorite).filter_by(articleid=articleid, userid=userid).first()
            if row is not None:
                row.canceled = 0
            else:
                now = time.strftime('%Y-%m-%d %H:%M:%S')
                favorite = Favorite(articleid=articleid, userid=userid, canceled=0, createtime=now,
                                    updatetime=now)
                dbsession.add(favorite)
            dbsession.commit()
            return True
        except Exception as e:
            print("Error in insert_favorite:", e)
            traceback.print_exc()
            return False

    @staticmethod
    def find_by_userid(userid):
        try:
            result = dbsession.query(Favorite).filter_by(userid=userid, canceled=0).all()
            return result
        except Exception as e:
            print("Error in find_by_userid:", e)
            traceback.print_exc()
            return None

    # 取消收藏
    @staticmethod
    def cancel_favorite(articleid):
        try:
            row = dbsession.query(Favorite).filter_by(articleid=articleid, userid=session.get('userid')).first()
            row.canceled = 1
            dbsession.commit()
        except Exception as e:
            print(e)
            traceback.print_exc()

    # 判断是否已经被收藏
    @staticmethod
    def check_favorite(articleid):
        try:
            row = dbsession.query(Favorite).filter_by(articleid=articleid, userid=session.get('userid')).first()
            if row is None:
                return False
            elif row.canceled == 1:
                return False
            else:
                return True
        except Exception as e:
            print(e)
            traceback.print_exc()

    # 为用户中心查询我的收藏添加数据操作方法
    @staticmethod
    def find_my_favorite():
        try:
            result = dbsession.query(Favorite, Article).join(Article, Favorite.articleid ==
                                                             Article.articleid).filter(
                Favorite.userid == session.get('userid')).all()
            return result
        except Exception as e:
            print(e)
            traceback.print_exc()

    # 切换收藏和取消收藏的状态
    @staticmethod
    def switch_favorite(favoriteid):
        try:
            row = dbsession.query(Favorite).filter_by(favoriteid=favoriteid).first()
            if row.canceled == 1:
                row.canceled = 0
            else:
                row.canceled = 1
            dbsession.commit()
            return row.canceled
        except Exception as e:
            print(e)
            traceback.print_exc()


if __name__ == '__main__':
    favorite_instance = Favorite()
