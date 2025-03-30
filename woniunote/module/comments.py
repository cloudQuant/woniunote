import time
import traceback
from woniunote.common.utils import model_join_list
from flask import session
from sqlalchemy import Table, Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from woniunote.common.database import dbconnect
from woniunote.module.users import Users
from woniunote.common.create_database import Comment
from woniunote.module.articles import Articles, Article

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
    @staticmethod
    def insert_comment(articleid, content, ipaddr):
        try:
            userid = session.get('main_userid')
            if not userid:
                print("No user ID found in session")
                return None
                
            now = time.strftime('%Y-%m-%d %H:%M:%S')
            comment = Comment(userid=userid, articleid=articleid,
                            content=content, ipaddr=ipaddr,
                            createtime=now, updatetime=now)
            dbsession.add(comment)
            dbsession.commit()
            return comment
        except Exception as e:
            print("Error in insert_comment:", e)
            traceback.print_exc()
            return None

    # 根据用户编号查询所有评论
    @staticmethod
    def find_by_userid(userid):
        try:
            # 查询用户的所有评论，并关联文章信息
            results = dbsession.query(Comment, Article)\
                .join(Article, Comment.articleid == Article.articleid)\
                .filter(Comment.userid == userid)\
                .filter(Comment.hidden == 0)\
                .order_by(Comment.commentid.desc())\
                .all()
            return results
        except Exception as e:
            print("Error in find_by_userid:", e)
            traceback.print_exc()
            return None

    # 根据文章编号查询所有评论
    @staticmethod
    def find_by_articleid(articleid):
        try:
            result = dbsession.query(Comment).filter_by(articleid=articleid, hidden=0, replyid=0).all()
            return result
        except Exception as e:
            print(e)
            traceback.print_exc()

    # 根据用户编号和日期进行查询是否已经超过每天5条限制
    @staticmethod
    def check_limit_per_5():
        try:
            start = time.strftime("%Y-%m-%d 00:00:00")  # 当天的起始时间
            end = time.strftime("%Y-%m-%d 23:59:59")  # 当天的结束时间
            result = dbsession.query(Comment).filter(Comment.userid == session.get('userid'),
                                                     Comment.createtime.between(start, end)).all()
            if len(result) >= 5:
                return True  # 返回True表示今天已经不能再发表评论
            else:
                return False
        except Exception as e:
            print(e)
            traceback.print_exc()

    # 查询评论与用户信息，注意评论也需要分页 [(Comment, Users), (Comment, Users)]
    @staticmethod
    def find_limit_with_user(articleid, start, count):
        try:
            result = dbsession.query(Comment, Users).join(Users, Users.userid == Comment.userid).filter(
                Comment.articleid == articleid, Comment.hidden == 0).order_by(
                Comment.commentid.desc()).limit(count).offset(start).all()
            return result
        except Exception as e:
            print(e)
            traceback.print_exc()

    @staticmethod
    def find_all():
        try:
            result = dbsession.query(Comment).all()
            return result
        except Exception as e:
            print(e)
            traceback.print_exc()

    # 新增一条回复，将原始评论的ID作为新评论的replyid字段来进行关联
    @staticmethod
    def insert_reply(articleid, commentid, content, ipaddr):
        try:
            now = time.strftime('%Y-%m-%d %H:%M:%S')
            comment = Comment(userid=session.get('userid'), articleid=articleid,
                              content=content, ipaddr=ipaddr, replyid=commentid,
                              createtime=now, updatetime=now)
            dbsession.add(comment)
            dbsession.commit()
        except Exception as e:
            print(e)
            traceback.print_exc()

    # 查询原始评论与对应的用户信息，带分页参数
    @staticmethod
    def find_comment_with_user(articleid, start, count):
        try:
            result = dbsession.query(Comment, Users).join(
                Users, Users.userid == Comment.userid).filter(
                Comment.articleid == articleid,
                Comment.hidden == 0,
                Comment.replyid == 0).order_by(
                Comment.commentid.desc()).limit(count).offset(start).all()
            return result
        except Exception as e:
            print(e)
            traceback.print_exc()

    # 查询回复评论，回复评论不需要分页
    @staticmethod
    def find_reply_with_user(replyid):
        try:
            result = dbsession.query(Comment, Users).join(Users, Users.userid ==
                                                          Comment.userid).filter(Comment.replyid == replyid,
                                                                                 Comment.hidden == 0).all()
            return result
        except Exception as e:
            print(e)
            traceback.print_exc()

    # 根据原始评论和回复评论生成一个关联列表
    def get_comment_user_list(self, articleid, start, count):
        try:
            result = self.find_comment_with_user(articleid, start, count)
            comment_list = model_join_list(result)  # 原始评论的连接结果
            for comment in comment_list:
                # 查询原始评论对应的回复评论,并转换为列表保存到comment_list中
                result = self.find_reply_with_user(comment['commentid'])
                # 为comment_list列表中的原始评论字典对象添加一个新Key叫reply_list
                # 用于存储当前这条原始评论的所有回复评论,如果无回复评论则列表值为空
                comment['reply_list'] = model_join_list(result)
            return comment_list  # 将新的数据结构返回给控制器接口
        except Exception as e:
            print(e)
            traceback.print_exc()

    # 查询某篇文章的原始评论总数量
    @staticmethod
    def get_count_by_article(articleid):
        try:
            count = dbsession.query(Comment).filter_by(articleid=articleid, hidden=0, replyid=0).count()
            return count
        except Exception as e:
            print(e)
            traceback.print_exc()

    # 添加兼容方法，作为get_count_by_article的别名
    @staticmethod
    def get_comment_count(articleid):
        return Comments.get_count_by_article(articleid)

    # 根据当前登录用户查询他的所有评论
    @staticmethod
    def find_my_comments():
        try:
            userid = session.get('userid')
            if not userid:
                return []
            comments = dbsession.query(Comment).filter_by(userid=userid, hidden=0).order_by(Comment.commentid.desc()).all()
            return comments
        except Exception as e:
            print(e)
            traceback.print_exc()
            return []
            
    # 根据评论ID查询单条评论
    @staticmethod
    def find_by_commentid(commentid):
        try:
            comment = dbsession.query(Comment).filter_by(commentid=commentid, hidden=0).first()
            return comment
        except Exception as e:
            print(e)
            traceback.print_exc()
            return None
            
    # 删除评论（软删除，将hidden标记为1）
    @staticmethod
    def delete(commentid):
        try:
            comment = dbsession.query(Comment).filter_by(commentid=commentid).first()
            if comment:
                comment.hidden = 1
                dbsession.commit()
                return True
            return False
        except Exception as e:
            print(e)
            traceback.print_exc()
            return False


if __name__ == '__main__':
    comment_instance = Comment()
