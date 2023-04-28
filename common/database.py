from sqlalchemy import MetaData
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import os 
import pymysql
pymysql.install_as_MySQLdb()    # ModuleNotFoundError: No module named 'MySQLdb'
import yaml
with open('./config.yaml', 'r', encoding='utf-8') as f:
    config_result = yaml.load(f.read(), Loader=yaml.FullLoader)
SQLALCHEMY_DATABASE_URI = config_result['database']["SQLALCHEMY_DATABASE_URI"]

app = Flask(__name__, template_folder='template', static_url_path='/', static_folder='resource')
app.config['SECRET_KEY'] = os.urandom(24)

# # 使用集成方式处理SQLAlchemy
app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # True: 跟踪数据库的修改，及时发送信号
app.config['SQLALCHEMY_POOL_SIZE'] = 100  # 数据库连接池的大小。默认是数据库引擎的默认值（通常是 5）
# 实例化db对象
db = SQLAlchemy(app)
def dbconnect():
    
    dbsession = db.session
    DBase = db.Model
    metadata = MetaData(bind=db.engine)
    return (dbsession, metadata, DBase)

# dict
ARTICLE_TYPES = config_result['ARTICLE_TYPES']
# ARTICLE_TYPES = {
#         '1': '量化思考',
#         "2":"量化框架",
#         '3': '交易策略',
#         '4': '股票',
#         '5': '期货',
#         '6': '期权',
#         '7': '基金',
#         '8': '债券',
#         '9': '理财',
#         '10': '保险',
#         '11':'学习与感悟',
#         '12':'公益',
#     }

