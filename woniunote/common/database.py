import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import MetaData
from woniunote.common.utils import read_config


# 配置读取
def load_config():
    config_result = read_config()
    article_config_result = read_config("/configs/article_type_config.yaml")

    return {
        'SQLALCHEMY_DATABASE_URI': config_result['database']["SQLALCHEMY_DATABASE_URI"],
        'ARTICLE_TYPES': article_config_result['ARTICLE_TYPES']
    }


config = load_config()

# Flask应用初始化
app = Flask(__name__, template_folder='template', static_url_path='/', static_folder='resource')
app.config['SECRET_KEY'] = os.urandom(24)

# 数据库配置
app.config['SQLALCHEMY_DATABASE_URI'] = config['SQLALCHEMY_DATABASE_URI']
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # 禁用对象修改追踪
app.config['SQLALCHEMY_POOL_SIZE'] = 100  # 设置连接池大小

# 实例化SQLAlchemy对象
db = SQLAlchemy(app)


# 创建数据库连接
def dbconnect():
    with app.app_context():
        dbsession = db.session
        dbase = db.Model
        metadata = MetaData()
        metadata.bind = db.engine
        return dbsession, metadata, dbase


# 获取文章配置
ARTICLE_TYPES = config['ARTICLE_TYPES']
# 数据库地址
SQLALCHEMY_DATABASE_URI = config['SQLALCHEMY_DATABASE_URI']
# Flask应用启动
if __name__ == '__main__':
    dbconnect()  # 初始化数据库连接

