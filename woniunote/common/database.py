import os
from flask import Flask, current_app
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import MetaData
from woniunote.common.utils import read_config

# 创建SQLAlchemy实例，但不立即绑定到app
db = SQLAlchemy()

# 配置读取
def load_config():
    """加载配置，如果配置文件不存在则使用测试默认值"""
    try:
        config_result = read_config()
        article_config_result = read_config("/configs/article_type_config.yaml")
        
        # 如果配置文件不存在或读取失败，使用测试默认值
        if config_result is None:
            config_result = {
                'database': {
                    'SQLALCHEMY_DATABASE_URI': 'sqlite:///test_database.db'
                }
            }
            
        if article_config_result is None:
            article_config_result = {
                'ARTICLE_TYPES': {
                    1: {'name': '原创文章', 'color': '#007bff'},
                    2: {'name': '转载文章', 'color': '#28a745'},
                    3: {'name': '翻译文章', 'color': '#ffc107'}
                }
            }

        return {
            'SQLALCHEMY_DATABASE_URI': config_result['database']["SQLALCHEMY_DATABASE_URI"],
            'ARTICLE_TYPES': article_config_result['ARTICLE_TYPES']
        }
    except Exception as e:
        # 如果出现任何错误，返回测试默认配置
        return {
            'SQLALCHEMY_DATABASE_URI': 'sqlite:///test_database.db',
            'ARTICLE_TYPES': {
                1: {'name': '原创文章', 'color': '#007bff'},
                2: {'name': '转载文章', 'color': '#28a745'},
                3: {'name': '翻译文章', 'color': '#ffc107'}
            }
        }

# 获取配置
config = load_config()

# 获取文章配置
ARTICLE_TYPES = config['ARTICLE_TYPES']
# 数据库地址
SQLALCHEMY_DATABASE_URI = config['SQLALCHEMY_DATABASE_URI']

# 创建数据库连接
def dbconnect(app=None):
    """创建数据库连接
    
    Args:
        app: Flask应用实例，如果为None则尝试使用current_app
        
    Returns:
        tuple: (dbsession, metadata, DBase)
    """
    if app is None:
        try:
            app = current_app._get_current_object()
        except RuntimeError:
            # 如果没有应用上下文，创建一个临时应用
            app = Flask(__name__)
            app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
            app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
            db.init_app(app)
    
    with app.app_context():
        dbsession = db.session
        dbase = db.Model
        metadata = MetaData()
        metadata.bind = db.engine
        return dbsession, metadata, dbase


# Flask应用启动
if __name__ == '__main__':
    dbconnect()  # 初始化数据库连接

