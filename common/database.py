from sqlalchemy import MetaData
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import os
from woniunote.utils import read_config


config_result = read_config()
SQLALCHEMY_DATABASE_URI = config_result['database']["SQLALCHEMY_DATABASE_URI"]

app = Flask(__name__, template_folder='template', static_url_path='/', static_folder='resource')
app.config['SECRET_KEY'] = os.urandom(24)

# # 使用集成方式处理SQLAlchemy
app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # True: 跟踪数据库的修改，及时发送信号
app.config['SQLALCHEMY_POOL_SIZE'] = 100  # 数据库连接池的大小。默认是数据库引擎的默认值（通常是 5）
# 实例化db对象
db = SQLAlchemy(app)


# def dbconnect():
#     dbsession = db.session
#     DBase = db.Model
#     metadata = MetaData(bind=db.engine)
#     return dbsession, metadata, DBase

def dbconnect():
    with app.app_context():
        dbsession = db.session
        DBase = db.Model
        metadata = MetaData()
        metadata.bind = db.engine
        return dbsession, metadata, DBase


# dict
ARTICLE_TYPES = config_result['ARTICLE_TYPES']

if __name__ == '__main__':
    dbconnect()
