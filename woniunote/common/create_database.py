#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Nov 13, 22:20:56 2021
更新：集中使用主应用的数据库连接，避免多个SQLAlchemy实例

@author: ubuntu
"""
import hashlib
from woniunote.common.database import db
from woniunote.common.utils import read_config

# 读取配置，仅用于初始化数据
config_result = read_config()


class User(db.Model):
    # 给表重新定义一个名称，默认名称是类名的小写，比如该类默认的表名是user。
    __tablename__ = "users"
    userid = db.Column(db.Integer, primary_key=True, nullable=False, autoincrement=True)  #
    username = db.Column(db.String(50), nullable=False)
    password = db.Column(db.String(32), nullable=False)
    nickname = db.Column(db.String(30))
    avatar = db.Column(db.String(20))
    qq = db.Column(db.String(15))
    role = db.Column(db.String(10), nullable=False)
    credit = db.Column(db.Integer, default=50)
    createtime = db.Column(db.DateTime)
    updatetime = db.Column(db.DateTime)

    # 创建一个外键，和django不一样。flask需要指定具体的字段创建外键，不能根据类名创建外键
    # role_id = db.Column(db.Integer,db.ForeignKey("roles.id"))

    def __repr__(self):
        return f" User's info: userid = {self.userid}, username = {self.username}, password = {self.password},\
               nickname =  {self.nickname},avatar = {self.avatar}, qq = {self.qq}, role = {self.role},\
               credit = {self.credit},createtime = {self.createtime},updatetime = {self.updatetime}"


class Article(db.Model):
    __tablename__ = "article"
    articleid = db.Column(db.Integer, primary_key=True, nullable=False, autoincrement=True)
    userid = db.Column(db.Integer, db.ForeignKey("users.userid"), nullable=False)  #
    type = db.Column(db.Integer, nullable=False)
    headline = db.Column(db.String(100), nullable=False)
    content = db.Column(db.TEXT(16777216))
    thumbnail = db.Column(db.String(30))
    credit = db.Column(db.Integer, default=0)
    readcount = db.Column(db.Integer, default=0)
    replycount = db.Column(db.Integer, default=0)
    recommended = db.Column(db.Integer, default=0)
    hidden = db.Column(db.Integer, default=0)
    drafted = db.Column(db.Integer, default=0)
    checked = db.Column(db.Integer, default=1)
    createtime = db.Column(db.DateTime)
    updatetime = db.Column(db.DateTime)

    # 创建一个外键，和django不一样。flask需要指定具体的字段创建外键，不能根据类名创建外键
    # role_id = db.Column(db.Integer,db.ForeignKey("roles.id"))

    def __repr__(self):
        return f" article's info: articleid = {self.articleid} , userid = {self.userid}, type = {self.type}, \
               headline =  {self.headline},content = {self.content}, thumbnail = {self.thumbnail}, \
               credit = {self.credit},readcount = {self.readcount},replycount = {self.replycount},\
               recommended = {self.recommended},hidden = {self.hidden},drafted = {self.drafted},  \
               checked = {self.checked},createtime = {self.createtime},updatetime = {self.updatetime}"


class Comment(db.Model):
    __tablename__ = "comment"
    commentid = db.Column(db.Integer, primary_key=True, nullable=False, autoincrement=True)
    userid = db.Column(db.Integer, db.ForeignKey("users.userid"), nullable=False)  #
    articleid = db.Column(db.Integer, db.ForeignKey("article.articleid"), nullable=False)
    content = db.Column(db.Text(65536), nullable=False)
    ipaddr = db.Column(db.String(30))
    replyid = db.Column(db.Integer)
    agreecount = db.Column(db.Integer, default=0)
    opposecount = db.Column(db.Integer, default=0)
    hidden = db.Column(db.Integer, default=0)
    createtime = db.Column(db.DateTime)
    updatetime = db.Column(db.DateTime)

    # 创建一个外键，和django不一样。flask需要指定具体的字段创建外键，不能根据类名创建外键
    # role_id = db.Column(db.Integer,db.ForeignKey("roles.id"))

    def __repr__(self):
        return f" comment's info: commentid = {self.commentid},articleid = {self.articleid} , userid = {self.userid},  \
               content = {self.content}, ipaddr = {self.thumbnail},hidden = {self.hidden}, \
               replyid = {self.replyid},agreecount = {self.agreecount},opposecount = {self.opposecount},\
               createtime = {self.createtime},updatetime = {self.updatetime}"


class Favorite(db.Model):
    # 
    __tablename__ = "favorite"
    favoriteid = db.Column(db.Integer, primary_key=True, nullable=False, autoincrement=True)
    userid = db.Column(db.Integer, db.ForeignKey("users.userid"), nullable=False)  #
    articleid = db.Column(db.Integer, db.ForeignKey("article.articleid"), nullable=False)
    canceled = db.Column(db.Integer, default=0)
    createtime = db.Column(db.DateTime)
    updatetime = db.Column(db.DateTime)

    def __repr__(self):
        return (f" favorite's info: "
                f"favoriteid = {self.favoriteid}, "
                f"articleid = {self.articleid} , "
                f"userid = {self.userid},  "
                f"canceled = {self.canceled}, "
                f"createtime = {self.createtime},"
                f"updatetime = {self.updatetime}")


class Credit(db.Model):
    # 
    __tablename__ = "credit"
    creditid = db.Column(db.Integer, primary_key=True, nullable=False, autoincrement=True)
    userid = db.Column(db.Integer, db.ForeignKey("users.userid"), nullable=False)  #
    category = db.Column(db.String(10))
    target = db.Column(db.Integer)
    credit = db.Column(db.Integer)
    createtime = db.Column(db.DateTime)
    updatetime = db.Column(db.DateTime)

    def __repr__(self):
        return (f" credit's info: "
                f" creditid = {self.creditid}, "
                f" category = {self.category} , "
                f" userid = {self.userid},  "
                f" target = {self.target}, "
                f" credit = {self.credit}, "
                f" createtime = {self.createtime}, "
                f" updatetime = {self.updatetime}")


# Todo和Card模型已移动到models目录下的专门文件中
# 从woniunote.models.todo导入Item, Category
# 从woniunote.models.card导入Card, CardCategory


if __name__ == '__main__':
    admin_user = User(username=config_result['admin']['username'],
                      nickname=config_result['admin']['nickname'],
                      password=hashlib.md5(config_result['admin']['password'].encode()).hexdigest(),
                      role="admin")
    editor_user = User(username=config_result['editor']['username'],
                       nickname=config_result['editor']['nickname'],
                       password=hashlib.md5(config_result['editor']['password'].encode()).hexdigest(),
                       role="editor")

    common_user = User(username=config_result['user']['username'],
                       nickname=config_result['user']['nickname'],
                       password=hashlib.md5(config_result['user']['password'].encode()).hexdigest(),
                       role="user")
    # 先将admin_user对象添加到会话中，可以回滚。

    db.session.add(admin_user)
    db.session.add(editor_user)
    db.session.add(common_user)
    # db.session.add_all([admin_user, editor_user, common_user])
    # 最后插入完数据一定要提交
    db.session.commit()
