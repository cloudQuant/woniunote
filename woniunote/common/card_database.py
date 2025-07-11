#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Nov 13, 22:20:56 2021

@author: cloudQuant
"""
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from woniunote.common.utils import read_config


config_result = read_config()
SQLALCHEMY_DATABASE_URI = config_result['database']["SQLALCHEMY_DATABASE_URI"]
app = Flask(__name__, template_folder='template', static_url_path='/', static_folder='resource')
app.config['SECRET_KEY'] = os.urandom(24)

# 使用集成方式处理SQLAlchemy
app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # True: 跟踪数据库的修改，及时发送信号
app.config['SQLALCHEMY_POOL_SIZE'] = 100  # 数据库连接池的大小。默认是数据库引擎的默认值（通常是 5）
# 实例化db对象
db = SQLAlchemy(app)

dbsession = db.session
DBase = db.Model


# 使用 models.card 中定义的模型
from woniunote.models.card import Card, CardCategory


if __name__ == '__main__':
    # 删除所有的表
    # db.drop_all()
    # 创建表
    db.create_all()
    # hashlib.md5("high_gold_course".encode()).hexdigest()
    # 先将admin_user对象添加到会话中，可以回滚。

    inbox = CardCategory(name=u'待完成')
    done = CardCategory(name=u'已完成')
    work_list = CardCategory(name=u'工作清单')
    learn_list = CardCategory(name=u'学习清单')
    write_list = CardCategory(name=u'写作清单')

    item4 = Card(headline=u'one paper', cardcategory=write_list)
    item5 = Card(headline=u'vnpy', cardcategory=learn_list)
    item6 = Card(headline=u'12支铅笔', cardcategory=write_list)
    item7 = Card(headline=u'test card', cardcategory=done)
    item8 = Card(headline=u'do card', cardcategory=work_list)
    db.session.add_all(
        [inbox, done, item4, item5, item6, item7, item8])
    db.session.commit()
