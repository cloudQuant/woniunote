import os
import pytest
import tempfile
import yaml
from woniunote.common.utils import get_db_connection, parse_db_uri, read_config


@pytest.fixture(scope="session")
def test_db_info():
    """数据库连接信息"""
    config = read_config()
    return parse_db_uri(config['database']['SQLALCHEMY_DATABASE_URI'])

@pytest.fixture(scope="session")
def test_db_uri():
    """测试数据库URI"""
    config = read_config()
    return config['database']['SQLALCHEMY_DATABASE_URI']

@pytest.fixture(scope="session")
def test_images_dir():
    """测试图片目录"""
    test_dir = os.path.join(os.path.dirname(__file__), 'test_images/')
    if not os.path.exists(test_dir):
        os.makedirs(test_dir)
    return test_dir
