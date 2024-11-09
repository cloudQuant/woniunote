import time
from woniunote.utils import model_join_list
from flask import session
from sqlalchemy import Table, Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from woniunote.common.database import dbconnect
from woniunote.module.users import Users
from woniunote.module.articles import Article
from woniunote.common.create_database import Comment

dbsession, md, DBase = dbconnect()


class Comments(DBase):
    __table__ = Table(
        'comment', md,
        Column('commentid', Integer, primary_key=True, nullable=False, autoincrement=True),
        Column('userid', Integer, ForeignKey('users.userid'), nullable=False),
        Column('articleid', Integer, ForeignKey('article.articleid'), nullable=False),
        Column('content', Text(65536), nullable=False),
        Column('ipaddr', String(30)),
        Column('replyid', Integer),
        Column('agreecount', Integer, default=0),
        Column('opposecount', Integer, default=0),
        Column('hidden', Integer, default=0),
        Column('createtime', DateTime),
        Column('updatetime', DateTime)
    )

    def __init__(self):
        from woniunote.module.users import Users
        self.user = relationship("Users", back_populates="Comments")
        self.article = relationship("Articles", back_populates="Comments")

    # # 定义外键关系
    # user = relationship("Users",
    #                     foreign_keys=[__table__.c.userid],
    #                     primaryjoin="Comment.userid == Users.userid")
    # article = relationship("Article",
    #                        foreign_keys=[__table__.c.articleid],
    #                        primaryjoin="Comment.articleid == Article.articleid")

    # 新增一条评论
    def insert_comment(self, articleid, content, ipaddr):
        now = time.strftime('%Y-%m-%d %H:%M:%S')
        comment = Comment(userid=session.get('userid'), articleid=articleid,
                          content=content, ipaddr=ipaddr, createtime=now, updatetime=now)
        dbsession.add(comment)
        dbsession.commit()

    # 根据文章编号查询所有评论
    def find_by_articleid(self, articleid):
        result = dbsession.query(Comment).filter_by(articleid=articleid, hidden=0, replyid=0).all()
        return result

    # 根据用户编号和日期进行查询是否已经超过每天5条限制
    def check_limit_per_5(self):
        start = time.strftime("%Y-%m-%d 00:00:00")  # 当天的起始时间
        end = time.strftime("%Y-%m-%d 23:59:59")  # 当天的结束时间
        result = dbsession.query(Comment).filter(Comment.userid == session.get('userid'),
                                                 Comment.createtime.between(start, end)).all()
        if len(result) >= 5:
            return True  # 返回True表示今天已经不能再发表评论
        else:
            return False

    # 查询评论与用户信息，注意评论也需要分页 [(Comment, Users), (Comment, Users)]
    def find_limit_with_user(self, articleid, start, count):
        result = dbsession.query(Comment, Users).join(Users, Users.userid == Comment.userid).filter(
            Comment.articleid == articleid, Comment.hidden == 0).order_by(
            Comment.commentid.desc()).limit(count).offset(start).all()
        return result

    def find_all(self):
        result = dbsession.query(Comment).all()
        return result

    # 新增一条回复，将原始评论的ID作为新评论的replyid字段来进行关联
    def insert_reply(self, articleid, commentid, content, ipaddr):
        now = time.strftime('%Y-%m-%d %H:%M:%S')
        comment = Comment(userid=session.get('userid'), articleid=articleid,
                          content=content, ipaddr=ipaddr, replyid=commentid,
                          createtime=now, updatetime=now)
        dbsession.add(comment)
        dbsession.commit()

    # 查询原始评论与对应的用户信息，带分页参数
    def find_comment_with_user(self, articleid, start, count):
        result = dbsession.query(Comment, Users).join(
            Users, Users.userid == Comment.userid).filter(
            Comment.articleid == articleid,
            Comment.hidden == 0,
            Comment.replyid == 0).order_by(
            Comment.commentid.desc()).limit(count).offset(start).all()
        return result

    # 查询回复评论，回复评论不需要分页
    def find_reply_with_user(self, replyid):
        result = dbsession.query(Comment, Users).join(Users, Users.userid ==
                                                      Comment.userid).filter(Comment.replyid == replyid,
                                                                             Comment.hidden == 0).all()
        return result

    # 根据原始评论和回复评论生成一个关联列表
    def get_comment_user_list(self, articleid, start, count):
        result = self.find_comment_with_user(articleid, start, count)
        comment_list = model_join_list(result)  # 原始评论的连接结果
        for comment in comment_list:
            # 查询原始评论对应的回复评论,并转换为列表保存到comment_list中
            result = self.find_reply_with_user(comment['commentid'])
            # 为comment_list列表中的原始评论字典对象添加一个新Key叫reply_list
            # 用于存储当前这条原始评论的所有回复评论,如果无回复评论则列表值为空
            comment['reply_list'] = model_join_list(result)
        return comment_list  # 将新的数据结构返回给控制器接口

    # 查询某篇文章的原始评论总数量
    def get_count_by_article(self, articleid):
        count = dbsession.query(Comment).filter_by(articleid=articleid, hidden=0, replyid=0).count()
        return count


if __name__ == '__main__':
    comment_instance = Comment()
