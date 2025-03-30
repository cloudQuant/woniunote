"""
测试配置

为单元测试提供固定装置（fixtures）和配置
"""
import os
import sys
import pytest

# 添加项目根目录到Python路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT_DIR = os.path.dirname(BASE_DIR)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# 导入测试助手
from tests.test_helpers import db, app, BaseModel


@pytest.fixture(scope="session")
def app_ctx():
    """提供应用上下文"""
    with app.app_context() as ctx:
        yield ctx


@pytest.fixture(scope="session")
def init_db(app_ctx):
    """初始化数据库"""
    # 创建所有表
    BaseModel.metadata.drop_all(bind=db.engine)
    BaseModel.metadata.create_all(bind=db.engine)
    yield
    # 测试结束后清理数据库
    BaseModel.metadata.drop_all(bind=db.engine)


@pytest.fixture(scope="function")
def db_session(init_db):
    """为每个测试函数提供干净的数据库会话"""
    # 开始事务
    connection = db.engine.connect()
    transaction = connection.begin()
    
    # 创建会话
    session = db.session
    session.configure(bind=connection)
    
    yield session
    
    # 回滚事务
    session.close()
    transaction.rollback()
    connection.close()
