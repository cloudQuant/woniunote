import pytest
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import MetaData
from woniunote.common.database import dbconnect

# 测试配置
@pytest.fixture
def test_config():
    return {
        "SQLALCHEMY_DATABASE_URI": "mysql+pymysql://testuser:testpass@localhost/test_woniunote",
        'ARTICLE_TYPES': ["news", "tutorial", "review"]
    }

# 创建测试用的 Flask 应用
@pytest.fixture
def test_app(test_config):
    # 创建新的 Flask 应用
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.urandom(24)
    
    # 配置数据库连接
    app.config['SQLALCHEMY_DATABASE_URI'] = test_config["SQLALCHEMY_DATABASE_URI"]
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_POOL_SIZE'] = 100
    
    # 返回配置好的应用
    return app

# 创建测试用的数据库连接
@pytest.fixture
def test_db(test_app):
    # 创建新的 SQLAlchemy 实例
    db = SQLAlchemy(test_app)
    
    # 清理旧的测试数据
    yield db
    
    # 确保在应用上下文中清理
    with test_app.app_context():
        db.session.remove()

# 测试配置是否正确
def test_config_values(test_config):
    """测试配置值是否正确"""
    # 测试数据库配置
    assert test_config['SQLALCHEMY_DATABASE_URI'] == "mysql+pymysql://testuser:testpass@localhost/test_woniunote"
    
    # 测试文章类型配置
    assert test_config['ARTICLE_TYPES'] == ["news", "tutorial", "review"]

# 测试 Flask 应用配置
def test_flask_app_config(test_app, test_config):
    """测试 Flask 应用的配置"""
    assert test_app.config['SQLALCHEMY_DATABASE_URI'] == test_config['SQLALCHEMY_DATABASE_URI']
    assert test_app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] is False
    assert test_app.config['SQLALCHEMY_POOL_SIZE'] == 100

# 测试数据库连接
def test_db_connection(test_db, test_app):
    """测试数据库连接是否正常"""
    # 创建应用上下文
    with test_app.app_context():
        # 测试 session 是否有效
        assert test_db.session is not None
        
        # 测试元数据是否绑定了正确的数据库引擎
        metadata = MetaData()
        metadata.bind = test_db.engine
        assert metadata.bind is not None
        
        # 测试 Model 类是否正确
        assert test_db.Model is not None
        # assert hasattr(test_db.Model, 'query')
