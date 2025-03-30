"""
WoniuNote 数据库模块

提供数据库连接、ORM基类和通用数据库操作功能
"""
import os
import yaml
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Type, Union

from flask import Flask, current_app
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import MetaData, inspect, Column, Integer, DateTime, func
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import Query, Session
from woniunote.common.utils import get_package_path

# 导入配置管理器
root_path = get_package_path("woniunote")
file_path = root_path+"/configs/user_password_config.yaml"
with open(file_path, 'r', encoding='utf-8') as f:
    config_result = yaml.load(f.read(), Loader=yaml.FullLoader)
print("config:", config_result)
# 设置日志
logger = logging.getLogger(__name__)


# 数据库初始化
def init_db(app: Flask) -> SQLAlchemy:
    """
    初始化数据库
    
    Args:
        app: Flask应用实例
        
    Returns:
        SQLAlchemy实例
    """
    try:
        # 配置数据库连接
        app.config['SQLALCHEMY_DATABASE_URI'] = config_result['database']['SQLALCHEMY_DATABASE_URI']
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        app.config['SQLALCHEMY_POOL_SIZE'] = config_result['database'].get('pool_size', 100)
        app.config['SQLALCHEMY_POOL_TIMEOUT'] = config_result['database'].get('pool_timeout', 30)
        app.config['SQLALCHEMY_POOL_RECYCLE'] = config_result['database'].get('pool_recycle', 3600)
        
        # 实例化SQLAlchemy
        db_instance = SQLAlchemy(app)
        logger.info("数据库初始化成功")
        return db_instance
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        # 返回一个空的SQLAlchemy实例，避免应用程序崩溃
        return SQLAlchemy()


# 创建Flask应用实例
app = Flask(__name__, template_folder='template', static_url_path='/', static_folder='resource')
app.config['SECRET_KEY'] = os.urandom(24)

# 初始化数据库
db = init_db(app)


# 创建基础模型类
class BaseModel(db.Model):
    """
    所有模型的基类，提供公共字段和方法
    
    使用__abstract__=True表示这是一个抽象基类，不会创建实际的数据库表
    """
    __abstract__ = True
    
    # 公共时间戳字段
    createtime = Column(DateTime, default=datetime.now, nullable=False, 
                        doc="创建时间")
    updatetime = Column(DateTime, default=datetime.now, onupdate=datetime.now, 
                        nullable=False, doc="更新时间")
    
    @declared_attr
    def __tablename__(cls) -> str:
        """默认表名为类名小写，子类可覆盖此属性"""
        return cls.__name__.lower()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        将模型实例转换为字典
        
        Returns:
            包含模型属性的字典
        """
        return {c.key: getattr(self, c.key)
                for c in inspect(self).mapper.column_attrs}
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BaseModel':
        """
        从字典创建模型实例
        
        Args:
            data: 包含模型属性的字典
            
        Returns:
            模型实例
        """
        return cls(**{k: v for k, v in data.items() 
                    if k in [c.key for c in inspect(cls).mapper.column_attrs]})
    
    @classmethod
    def get_by_id(cls, id: int, session: Optional[Session] = None) -> Optional['BaseModel']:
        """
        根据ID获取模型实例
        
        Args:
            id: 主键ID
            session: 可选的数据库会话
            
        Returns:
            模型实例或None
        """
        if session is None:
            session = db.session
        
        # 找到主键列
        primary_key = next((column.key for column in inspect(cls).primary_key), None)
        if primary_key is None:
            return None
        
        # 构建查询
        return session.query(cls).filter_by(**{primary_key: id}).first()


# 数据库会话管理装饰器
def db_session(func):
    """
    数据库会话管理装饰器
    
    自动处理会话的创建、提交和回滚
    """
    def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
            db.session.commit()
            return result
        except Exception as e:
            db.session.rollback()
            logger.error(f"数据库操作失败: {e}")
            raise
    return wrapper


# 数据库错误处理装饰器
def db_error_handler(func):
    """
    数据库错误处理装饰器
    
    捕获和记录数据库操作错误
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"数据库错误: {e}")
            # 重新抛出异常，让调用者处理
            raise
    return wrapper


# 创建数据库连接
def dbconnect() -> Tuple[Session, MetaData, Type[db.Model]]:
    """
    创建数据库连接
    
    Returns:
        包含会话、元数据和基础模型的元组
    """
    try:
        with app.app_context():
            dbsession = db.session
            dbase = db.Model
            metadata = MetaData()
            metadata.bind = db.engine
            return dbsession, metadata, dbase
    except Exception as e:
        logger.error(f"创建数据库连接失败: {e}")
        # 返回一个空会话和空元数据，避免应用程序崩溃
        return db.session, MetaData(), db.Model


# 事务管理上下文管理器
class transaction:
    """
    数据库事务上下文管理器
    
    使用方法:
    with transaction() as session:
        # 执行数据库操作
    """
    def __init__(self, session=None):
        self.session = session or db.session
    
    def __enter__(self):
        return self.session
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            # 发生异常，回滚事务
            self.session.rollback()
            logger.error(f"事务回滚: {exc_val}")
        else:
            # 无异常，提交事务
            try:
                self.session.commit()
            except Exception as e:
                self.session.rollback()
                logger.error(f"提交事务失败: {e}")
                raise


# 提供便捷的分页查询方法
def paginate(query: Query, page: int = 1, per_page: int = 20) -> Dict[str, Any]:
    """
    对查询结果进行分页
    
    Args:
        query: SQLAlchemy查询对象
        page: 页码，从1开始
        per_page: 每页条数
        
    Returns:
        包含分页信息和结果的字典
    """
    total = query.count()
    items = query.limit(per_page).offset((page - 1) * per_page).all()
    
    # 计算分页信息
    total_pages = (total + per_page - 1) // per_page
    has_next = page < total_pages
    has_prev = page > 1
    
    return {
        'items': items,
        'page': page,
        'per_page': per_page,
        'total': total,
        'total_pages': total_pages,
        'has_next': has_next,
        'has_prev': has_prev
    }


# 获取文章类型配置
file_path = root_path+"/configs/article_type_config.yaml"
with open(file_path, 'r', encoding='utf-8') as f:
    config = yaml.load(f.read(), Loader=yaml.FullLoader)
print("config:", config_result)
ARTICLE_TYPES = config.get('ARTICLE_TYPES', [
    {'id': 1, 'name': '博客', 'value': 'blog'},
    {'id': 2, 'name': '问答', 'value': 'qa'},
    {'id': 3, 'name': '分享', 'value': 'share'}
])

# 数据库连接URI
SQLALCHEMY_DATABASE_URI = config_result['database']['SQLALCHEMY_DATABASE_URI']

# 导出模块公共接口
__all__ = [
    'db', 'app', 'BaseModel', 'dbconnect', 'transaction', 
    'db_session', 'db_error_handler', 'paginate',
    'ARTICLE_TYPES', 'SQLALCHEMY_DATABASE_URI'
]


# 应用启动入口
if __name__ == '__main__':
    dbconnect()  # 初始化数据库连接
