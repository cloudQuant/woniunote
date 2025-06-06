#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Nov 13, 22:20:56 2021

@author: ubuntu
"""
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from woniunote.common.database import SQLALCHEMY_DATABASE_URI
from woniunote.common.create_database import Item, Category

app = Flask(__name__,
            template_folder='template',
            static_url_path='/',
            static_folder='resource')
app.config['SECRET_KEY'] = os.urandom(24)

# 使用集成方式处理SQLAlchemy
app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # True: 跟踪数据库的修改，及时发送信号
app.config['SQLALCHEMY_POOL_SIZE'] = 100  # 数据库连接池的大小。默认是数据库引擎的默认值（通常是 5）
# 实例化db对象
db = SQLAlchemy(app)

dbsession = db.session
DBase = db.Model

if __name__ == '__main__':
    # 删除所有的表
    # db.drop_all()
    # 创建表
    db.create_all()
    # hashlib.md5("high_gold_course".encode()).hexdigest()
    # 先将admin_user对象添加到会话中，可以回滚。

    inbox = Category(name=u'收件箱')
    done = Category(name=u'已完成')
    shopping_list = Category(name=u'购物清单')
    work_list = Category(name=u'工作清单')
    learn_list = Category(name=u'学习清单')
    write_list = Category(name=u'写作清单')
    item = Item(body=u'sleep 30min')
    item2 = Item(body=u'晒太阳')
    item3 = Item(body=u'写作练习30分钟')
    item4 = Item(body=u'3瓶牛奶', category=shopping_list)
    item5 = Item(body=u'5个苹果', category=shopping_list)
    item6 = Item(body=u'12支铅笔', category=shopping_list)
    item7 = Item(body=u'浇花', category=done)
    item8 = Item(body=u'done to do test', category=work_list)
    db.session.add_all(
        [inbox, done, item, item2, item3, item4, item5, item6, item7, item8])
    db.session.commit()
