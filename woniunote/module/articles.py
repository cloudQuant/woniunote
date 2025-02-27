import time
import traceback
from flask import session
from sqlalchemy import Table, Column, Integer, String, Text, DateTime, func, ForeignKey
from sqlalchemy.orm import relationship
from woniunote.common.database import dbconnect
from woniunote.module.users import Users
from woniunote.common.create_database import Article

dbsession, md, DBase = dbconnect()


class Articles(DBase):
    __table__ = Table(
        'article', md,
        Column('articleid', Integer, primary_key=True, nullable=False, autoincrement=True),
        Column('userid', Integer, ForeignKey('users.userid'), nullable=False),
        Column('type', Integer, nullable=False),
        Column('headline', String(100), nullable=False),
        Column('content', Text(16777216)),
        Column('thumbnail', String(30)),
        Column('credit', Integer, default=0),
        Column('readcount', Integer, default=0),
        Column('replycount', Integer, default=0),
        Column('recommended', Integer, default=0),
        Column('hidden', Integer, default=0),
        Column('drafted', Integer, default=0),
        Column('checked', Integer, default=1),
        Column('createtime', DateTime),
        Column('updatetime', DateTime)
    )

    def __init__(self):
        from woniunote.module.users import Users
        self.user = relationship("Users", back_populates="Articles")

    # 定义外键关系
    # user = relationship("Users", foreign_keys=[__table__.c.userid], primaryjoin="Article.userid == Users.userid")

    # 查询所有文章
    @staticmethod
    def find_all():
        try:
            result = dbsession.query(Article).all()
            return result
        except Exception as e:
            print(e)
            traceback.print_exc()

    # 根据id查询文章，数据格式：(Article, 'nickname')
    @staticmethod
    def find_by_id(articleid):
        try:
            result = dbsession.query(Article).filter_by(articleid=articleid).first()
            return result
        except Exception as e:
            print(e)
            traceback.print_exc()

    # 根据多个文章ID查询文章
    @staticmethod
    def find_by_ids(articleids):
        try:
            if not articleids:
                return []
            result = dbsession.query(Article).filter(Article.articleid.in_(articleids)).all()
            return result
        except Exception as e:
            print(e)
            traceback.print_exc()
            return []

    # 根据用户ID查询文章
    @staticmethod
    def find_by_userid(userid):
        try:
            result = dbsession.query(Article).filter_by(userid=userid, drafted=0).order_by(Article.articleid.desc()).all()
            return result
        except Exception as e:
            print(e)
            traceback.print_exc()
            return []

    # 根据用户ID查询草稿
    @staticmethod
    def find_drafts_by_userid(userid):
        try:
            result = dbsession.query(Article).filter_by(userid=userid, drafted=1).order_by(Article.articleid.desc()).all()
            return result
        except Exception as e:
            print(e)
            traceback.print_exc()
            return []

    # 指定分页的limit和offset的参数值，同时与用户表做连接查询
    @staticmethod
    def find_limit_with_users(start, count):
        try:
            result = dbsession.query(Article, Users.nickname).join(Users, Users.userid == Article.userid) \
                .all()
            begin = start
            end = start + count
            if begin == -10:
                result = result[begin:]
            else:
                result = result[begin:end]
            result = result[::-1]
            return result
        except Exception as e:
            print(e)
            traceback.print_exc()

    # 统计一下当前文章的总数量
    @staticmethod
    def get_total_count():
        try:
            count = dbsession.query(Article).filter(Article.hidden == 0, Article.drafted == 0, Article.checked == 1).count()
            return count
        except Exception as e:
            print(e)
            traceback.print_exc()

    # 根据文章类型获取文章
    @staticmethod
    def find_by_type(article_type, start, count):
        try:
            result = dbsession.query(Article, Users.nickname).join(Users, Users.userid == Article.userid) \
                .filter(Article.hidden == 0, Article.drafted == 0, Article.checked == 1, Article.type == article_type) \
                .order_by(Article.articleid.desc()).limit(count).offset(start).all()
            return result
        except Exception as e:
            print(e)
            traceback.print_exc()

    # 根据文章类型来获取总数量
    @staticmethod
    def get_count_by_type(article_type):
        try:
            count = dbsession.query(Article).filter(Article.hidden == 0,
                                                    Article.drafted == 0,
                                                    Article.checked == 1,
                                                    Article.type == article_type).count()
            return count
        except Exception as e:
            print(e)
            traceback.print_exc()

    # 根据文章标题进行模糊搜索
    @staticmethod
    def find_by_headline(headline, start, count):
        try:
            result = dbsession.query(Article, Users.nickname).join(Users, Users.userid == Article.userid) \
                .filter(Article.hidden == 0, Article.drafted == 0, Article.checked == 1,
                        Article.headline.like('%' + headline + '%')) \
                .order_by(Article.articleid.desc()).limit(count).offset(start).all()
            return result
        except Exception as e:
            print(e)
            traceback.print_exc()

    # 统计分页总数量
    @staticmethod
    def get_count_by_headline(headline):
        try:
            count = dbsession.query(Article).filter(Article.hidden == 0,
                                                    Article.drafted == 0,
                                                    Article.checked == 1,
                                                    Article.headline.like('%' + headline + '%')).count()
            return count
        except Exception as e:
            print(e)
            traceback.print_exc()

    # 最新文章[(id, headline),(id, headline)]
    @staticmethod
    def find_last_9():
        try:
            result = dbsession.query(Article.articleid, Article.headline). \
                filter(Article.hidden == 0, Article.drafted == 0, Article.checked == 1) \
                .order_by(Article.articleid.desc()).limit(9).all()
            return result
        except Exception as e:
            print(e)
            traceback.print_exc()

    # 最多阅读
    @staticmethod
    def find_most_9():
        try:
            result = dbsession.query(Article.articleid, Article.headline). \
                filter(Article.hidden == 0, Article.drafted == 0, Article.checked == 1) \
                .order_by(Article.readcount.desc()).limit(9).all()
            return result
        except Exception as e:
            print(e)
            traceback.print_exc()

    # 特别推荐，如果超过9篇，可以考虑order by rand()的方式随机显示9篇
    @staticmethod
    def find_recommended_9():
        try:
            result = dbsession.query(Article.articleid, Article.headline). \
                filter(Article.hidden == 0, Article.drafted == 0, Article.checked == 1, Article.recommended == 1) \
                .order_by(func.rand()).limit(9).all()
            return result
        except Exception as e:
            print(e)
            traceback.print_exc()

    # 一次性返回三个推荐数据
    def find_last_most_recommended(self):
        try:
            last = self.find_last_9()
            most = self.find_most_9()
            recommended = self.find_recommended_9()
            return last, most, recommended
        except Exception as e:
            print(e)
            traceback.print_exc()

    # 每阅读一次文章，阅读次数+1
    @staticmethod
    def update_read_count(articleid):
        try:
            article = dbsession.query(Article).filter_by(articleid=articleid).first()
            if article.readcount is None:
                article.readcount = 0
            article.readcount += 1
            dbsession.commit()
        except Exception as e:
            print(e)
            traceback.print_exc()

    # 根据文章编号查询文章标题
    @staticmethod
    def find_headline_by_id(articleid):
        try:
            row = dbsession.query(Article.headline).filter_by(articleid=articleid).first()
            return row.headline
        except Exception as e:
            print(e)
            traceback.print_exc()

    # 获取当前文章的 上一篇和下一篇
    def find_prev_next_by_id(self, articleid):
        try:
            m_dict = {}

            # 查询比当前编号小的当中最大的一个
            row = dbsession.query(Article).filter(Article.hidden == 0,
                                                  Article.drafted == 0,
                                                  Article.checked == 1,
                                                  Article.articleid < articleid).order_by(
                Article.articleid.desc()).limit(1).first()
            # 如果当前已经是第一篇，上一篇也是当前文章
            if row is None:
                prev_id = articleid
            else:
                prev_id = row.articleid

            m_dict['prev_id'] = prev_id
            m_dict['prev_headline'] = self.find_headline_by_id(prev_id)

            # 查询比当前编号大的当中最小的一个
            row = dbsession.query(Article).filter(Article.hidden == 0,
                                                  Article.drafted == 0,
                                                  Article.checked == 1,
                                                  Article.articleid > articleid).order_by(
                Article.articleid).limit(1).first()
            # 如果当前已经是最后一篇，下一篇也是当前文章
            if row is None:
                next_id = articleid
            else:
                next_id = row.articleid

            m_dict['next_id'] = next_id
            m_dict['next_headline'] = self.find_headline_by_id(next_id)

            return m_dict
        except Exception as e:
            print(e)
            traceback.print_exc()

    # 当发表或者回复评论后，为文章表字段replycount加1
    @staticmethod
    def update_replycount(articleid):
        try:
            row = dbsession.query(Article).filter_by(articleid=articleid).first()
            row.replycount += 1
            dbsession.commit()
        except Exception as e:
            print(e)
            traceback.print_exc()

    # 插入一篇新的文章，草稿或投稿通过参数进行区分
    @staticmethod
    def insert_article(article_type, headline, content, thumbnail, credit, drafted=0, checked=1):
        try:
            now = time.strftime('%Y-%m-%d %H:%M:%S')
            userid = session.get('userid')
            # 其他字段在数据库中均已设置好默认值，无须手工插入
            article = Article(userid=userid, type=article_type, headline=headline, content=content,
                              thumbnail=thumbnail, credit=credit, drafted=drafted, readcount=0,
                              checked=checked, createtime=now, updatetime=now)
            dbsession.add(article)
            dbsession.commit()

            return article.articleid  # 将新的文章编号返回，便于前端页面跳转
        except Exception as e:
            print(e)
            traceback.print_exc()

    # 根据文章编号更新文章的内容，可用于文章编辑或草稿修改，以及基于草稿的发布
    @staticmethod
    def update_article(articleid, article_type, headline, content, thumbnail, credit, drafted=0, checked=1):
        try:
            now = time.strftime('%Y-%m-%d %H:%M:%S')
            row = dbsession.query(Article).filter_by(articleid=articleid).first()
            row.type = article_type
            row.headline = headline
            row.content = content
            row.thumbnail = thumbnail
            row.credit = credit
            row.drafted = drafted
            row.checked = checked
            row.updatetime = now  # 修改文章的更新时间
            dbsession.commit()
            return articleid  # 继续将文章ID返回调用处
        except Exception as e:
            print(e)
            traceback.print_exc()

    # =========== 以下方法主要用于后台管理类操作 ================== #

    # 查询article表中除草稿外的所有数据并返回结果集
    @staticmethod
    def find_all_except_draft(start, count):
        try:
            result = dbsession.query(Article).filter(Article.drafted == 0).order_by(
                Article.articleid.desc()).limit(count).offset(start).all()
            return result
        except Exception as e:
            print(e)
            traceback.print_exc()

    # 查询除草稿外的所有文章的总数量
    @staticmethod
    def get_count_except_draft():
        try:
            count = dbsession.query(Article).filter(Article.drafted == 0).count()
            return count
        except Exception as e:
            print(e)
            traceback.print_exc()

    # 按照文章分类进行查询（不含草稿，该方法直接返回文章总数量用于分页）
    def find_by_type_except_draft(self, start, count, article_type):
        try:
            if type == 0:
                result = self.find_all_except_draft(start, count)
                total = self.get_count_except_draft()
            else:
                result = dbsession.query(Article).filter(Article.drafted == 0,
                                                         Article.type == article_type).order_by(Article.articleid.desc()) \
                    .limit(count).offset(start).all()
                total = dbsession.query(Article).filter(Article.drafted == 0,
                                                        Article.type == article_type).count()
            return result, total  # 返回分页结果集和不分页的总数量
        except Exception as e:
            print(e)
            traceback.print_exc()

    # 按照标题模糊查询（不含草稿，不分页）
    @staticmethod
    def find_by_headline_except_draft(headline):
        try:
            result = dbsession.query(Article).filter(Article.drafted == 0,
                                                     Article.headline.like('%' + headline + '%')) \
                .order_by(Article.articleid.desc()).all()
            return result
        except Exception as e:
            print(e)
            traceback.print_exc()

    # 切换文章的隐藏状态：1表示隐藏，0表示显示
    @staticmethod
    def switch_hidden(articleid):
        try:
            row = dbsession.query(Article).filter_by(articleid=articleid).first()
            if row.hidden == 1:
                row.hidden = 0
            else:
                row.hidden = 1
            dbsession.commit()
            return row.hidden  # 将当前最新状态返回给控制层
        except Exception as e:
            print(e)
            traceback.print_exc()

    # 切换文章的推荐状态：1表示推荐，0表示正常
    @staticmethod
    def switch_recommended(articleid):
        try:
            row = dbsession.query(Article).filter_by(articleid=articleid).first()
            if row.recommended == 1:
                row.recommended = 0
            else:
                row.recommended = 1
            dbsession.commit()
            return row.recommended
        except Exception as e:
            print(e)
            traceback.print_exc()

    # 切换文章的审核状态：1表示已审，0表示待审
    @staticmethod
    def switch_checked(articleid):
        try:
            row = dbsession.query(Article).filter_by(articleid=articleid).first()
            if row.checked == 1:
                row.checked = 0
            else:
                row.checked = 1
            dbsession.commit()
            return row.checked
        except Exception as e:
            print(e)
            traceback.print_exc()


if __name__ == "__main__":
    article_instance = Articles()
