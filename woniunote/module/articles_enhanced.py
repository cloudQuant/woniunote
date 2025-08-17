"""
增强的文章模块 - 使用 BaseModel 基础类
演示如何使用基础数据访问类来减少重复代码
"""
import time
import traceback
from flask import session
from sqlalchemy import Table, Column, Integer, String, Text, DateTime, func, ForeignKey
from sqlalchemy.orm import relationship
from woniunote.common.database import dbconnect
from woniunote.module.users import Users
from woniunote.common.create_database import Article
from woniunote.common.simple_logger import get_simple_logger
from woniunote.common.base_model import BaseModel
from woniunote.common.error_handler import DatabaseException

dbsession, md, DBase = dbconnect()

class ArticlesEnhanced(DBase, BaseModel):
    """增强的文章数据访问类 - 继承 BaseModel"""
    
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
        # 初始化基础模型
        BaseModel.__init__(self, "articles")
        from woniunote.module.users import Users
        self.user = relationship("Users", back_populates="Articles")

    # 使用基础类的标准查询方法，而不是重复实现
    def find_article_by_id(self, articleid):
        """
        根据ID查找文章
        使用基础类的 find_by_id 方法
        """
        return self.find_by_id(Article, articleid)

    def find_articles_by_user(self, userid):
        """
        根据用户ID查找文章
        使用基础类的 find_by_field 方法
        """
        return self.find_by_field(Article, 'userid', userid, first_only=False)

    def find_articles_by_type(self, article_type, limit=50):
        """
        根据类型查找文章
        使用基础类的 find_by_conditions 方法
        """
        conditions = {'type': article_type, 'drafted': 0, 'checked': 1}
        return self.find_by_conditions(Article, conditions, limit=limit)

    def create_article(self, userid, headline, content, article_type=1):
        """
        创建新文章
        使用基础类的 create 方法
        """
        now = time.strftime('%Y-%m-%d %H:%M:%S')
        data = {
            'userid': userid,
            'headline': headline,
            'content': content,
            'type': article_type,
            'createtime': now,
            'updatetime': now,
            'credit': 0,
            'readcount': 0,
            'replycount': 0,
            'recommended': 0,
            'hidden': 0,
            'drafted': 0,
            'checked': 1
        }
        return self.create(Article, data)

    def update_article(self, articleid, **kwargs):
        """
        更新文章
        使用基础类的 update_by_id 方法
        """
        if kwargs:
            kwargs['updatetime'] = time.strftime('%Y-%m-%d %H:%M:%S')
        return self.update_by_id(Article, articleid, kwargs)

    def delete_article(self, articleid):
        """
        删除文章
        使用基础类的 delete_by_id 方法
        """
        return self.delete_by_id(Article, articleid)

    def get_article_count(self, conditions=None):
        """
        获取文章数量
        使用基础类的 count 方法
        """
        return self.count(Article, conditions)

    def find_published_articles(self, offset=0, limit=20):
        """
        查找已发布的文章
        使用基础类的 find_by_conditions 方法
        """
        conditions = {'drafted': 0, 'checked': 1, 'hidden': 0}
        return self.find_by_conditions(Article, conditions, limit=limit, offset=offset)

    def find_recommended_articles(self, limit=10):
        """
        查找推荐文章
        使用基础类的 find_by_conditions 方法
        """
        conditions = {'recommended': 1, 'drafted': 0, 'checked': 1, 'hidden': 0}
        return self.find_by_conditions(Article, conditions, limit=limit)

    def increment_read_count(self, articleid):
        """
        增加文章阅读量
        使用基础类的原生SQL执行能力
        """
        try:
            sql = "UPDATE article SET readcount = readcount + 1 WHERE articleid = :articleid"
            self.execute_raw_query(sql, {'articleid': articleid})
            return True
        except DatabaseException as e:
            self.logger.error(f"增加阅读量失败: {e}")
            return False

    def switch_article_status(self, articleid, field_name):
        """
        切换文章状态（推荐、隐藏、审核等）
        使用基础类的 find_by_id 和 update_by_id 方法
        """
        try:
            # 查找文章
            article = self.find_by_id(Article, articleid)
            if not article:
                return None
                
            # 切换状态
            current_value = getattr(article, field_name, 0)
            new_value = 1 if current_value == 0 else 0
            
            # 更新文章
            success = self.update_by_id(Article, articleid, {field_name: new_value})
            return new_value if success else None
            
        except DatabaseException as e:
            self.logger.error(f"切换文章状态失败: {e}")
            return None

    # 兼容现有代码的方法
    def switch_recommended(self, articleid):
        """切换推荐状态"""
        return self.switch_article_status(articleid, 'recommended')

    def switch_hidden(self, articleid):
        """切换隐藏状态"""
        return self.switch_article_status(articleid, 'hidden')

    def switch_checked(self, articleid):
        """切换审核状态"""
        return self.switch_article_status(articleid, 'checked')

# 使用示例：
# articles_enhanced = ArticlesEnhanced()
# 
# # 查找文章
# article = articles_enhanced.find_article_by_id(123)
# 
# # 创建文章
# new_article = articles_enhanced.create_article(
#     userid=1, 
#     headline="测试文章", 
#     content="这是一篇测试文章"
# )
# 
# # 更新文章
# articles_enhanced.update_article(123, headline="更新后的标题")
# 
# # 查找用户的所有文章
# user_articles = articles_enhanced.find_articles_by_user(1)