import time

from flask import session
from sqlalchemy import Table, Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from woniunote.common.database import dbconnect
from woniunote.module.articles import Article
from woniunote.module.users import Users
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
    def insert_favorite(self, articleid):
        row = dbsession.query(Favorite).filter_by(articleid=articleid, userid=session.get('userid')).first()
        if row is not None:
            row.canceled = 0
        else:
            now = time.strftime('%Y-%m-%d %H:%M:%S')
            favorite = Favorite(articleid=articleid, userid=session.get('userid'), canceled=0, createtime=now,
                                updatetime=now)
            dbsession.add(favorite)
        dbsession.commit()

    # 取消收藏
    def cancel_favorite(self, articleid):
        row = dbsession.query(Favorite).filter_by(articleid=articleid, userid=session.get('userid')).first()
        row.canceled = 1
        dbsession.commit()

    # 判断是否已经被收藏
    def check_favorite(self, articleid):
        row = dbsession.query(Favorite).filter_by(articleid=articleid, userid=session.get('userid')).first()
        if row is None:
            return False
        elif row.canceled == 1:
            return False
        else:
            return True

    # 为用户中心查询我的收藏添加数据操作方法
    def find_my_favorite(self):
        result = dbsession.query(Favorite, Article).join(Article, Favorite.articleid ==
                                                         Article.articleid).filter(
            Favorite.userid == session.get('userid')).all()
        return result

    # 切换收藏和取消收藏的状态
    def switch_favorite(self, favoriteid):
        row = dbsession.query(Favorite).filter_by(favoriteid=favoriteid).first()
        if row.canceled == 1:
            row.canceled = 0
        else:
            row.canceled = 1
        dbsession.commit()
        return row.canceled


if __name__ == '__main__':
    favorite_instance = Favorite()
