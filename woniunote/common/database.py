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
    import yaml
    try:
        # 读取主配置文件
        config_result = read_config()
        
        # 手动读取文章类型配置文件
        article_config_result = None
        current_dir = os.getcwd()
        
        # 查找文章类型配置文件的可能路径
        article_config_paths = [
            os.path.join(current_dir, "configs", "article_type_config.yaml"),
            os.path.join(current_dir, "woniunote", "configs", "article_type_config.yaml"),
            os.path.join(os.path.dirname(current_dir), "configs", "article_type_config.yaml"),
            os.path.join(os.path.dirname(__file__), "..", "configs", "article_type_config.yaml"),
        ]
        
        # 尝试读取文章类型配置文件
        for path in article_config_paths:
            abs_path = os.path.abspath(path)
            if os.path.exists(abs_path):
                try:
                    with open(abs_path, 'r', encoding='utf-8') as f:
                        article_config_result = yaml.safe_load(f)
                    print(f"Successfully loaded article config from: {abs_path}")
                    break
                except Exception as e:
                    print(f"Failed to load article config from {abs_path}: {e}")
                    continue
        
        # 如果配置文件不存在或读取失败，使用测试默认值
        if config_result is None:
            config_result = {
                'database': {
                    'SQLALCHEMY_DATABASE_URI': 'sqlite:///test_database.db'
                }
            }
            
        if article_config_result is None:
            print("Using default article types configuration")
            article_config_result = {
                'ARTICLE_TYPES': {
                    1: '交易策略',
                    101: 'CTA策略',
                    102: '统计套利',
                    103: '高频交易',
                    2: '量化框架',
                    201: 'backtrader',
                    202: 'wondertrader',
                    3: '投资',
                    301: '股票',
                    302: '期货',
                    303: '期权'
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
                1: '交易策略',
                101: 'CTA策略',
                102: '统计套利',
                103: '高频交易',
                2: '量化框架',
                201: 'backtrader',
                202: 'wondertrader',
                3: '投资',
                301: '股票',
                302: '期货',
                303: '期权'
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
            # 如果没有应用上下文，检查是否在测试环境中
            if os.environ.get('TESTING') == 'True':
                # 在测试环境中，创建临时应用
                app = Flask(__name__)
                app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
                app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
                db.init_app(app)
            else:
                # 创建临时应用
                app = Flask(__name__)
                app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
                app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
                db.init_app(app)
    
    if app is None:
        return None, None, None
        
    with app.app_context():
        try:
            dbsession = db.session
            dbase = db.Model
            metadata = MetaData()
            metadata.bind = db.engine
            return dbsession, metadata, dbase
        except Exception:
            # 如果数据库初始化失败，返回None
            return None, None, None


# 数据库会话管理
_db_session = None

def get_db():
    """获取数据库会话"""
    global _db_session
    if _db_session is None:
        # 创建数据库会话
        try:
            from flask import Flask
            app = Flask(__name__)
            app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
            app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
            db.init_app(app)

            with app.app_context():
                _db_session = db.session
        except Exception as e:
            print(f"数据库初始化失败: {e}")
            return None

    return _db_session

def init_db():
    """初始化数据库"""
    try:
        from flask import Flask
        app = Flask(__name__)
        app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        db.init_app(app)

        with app.app_context():
            # 创建所有表
            db.create_all()
            print("数据库表创建成功")

    except Exception as e:
        print(f"数据库初始化失败: {e}")

# Flask应用启动
if __name__ == '__main__':
    dbconnect()  # 初始化数据库连接

