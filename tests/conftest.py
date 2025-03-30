"""
WoniuNote Test Configuration

This module contains fixtures and setup code for all tests.
"""
import os
import sys
import pytest
import yaml
import importlib.util
import importlib.machinery
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

# ===== 重要：解决pytest导入问题 =====
# 将项目根目录添加到Python路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

# 将woniunote目录添加到Python路径
WONIUNOTE_DIR = os.path.join(BASE_DIR, 'woniunote')
if WONIUNOTE_DIR not in sys.path:
    sys.path.insert(0, WONIUNOTE_DIR)

# 调试信息
print("\n===== PYTEST DEBUG INFO =====")
print(f"Python路径: {sys.path[:3]}...")
print(f"BASE_DIR: {BASE_DIR}")
print(f"当前目录: {os.getcwd()}")
print(f"woniunote目录: {WONIUNOTE_DIR}")
print("============================\n")

# ===== 创建woniunote命名空间包的虚拟模块 =====
print("\n===== 创建woniunote虚拟模块 =====")

# 记录所有虚拟模块和对应的实际文件路径
virtual_modules = {}

# 创建虚拟模块的辅助函数
def create_virtual_module(name, actual_path=None):
    if name in sys.modules:
        return sys.modules[name]
    
    # 创建模块规格和模块对象
    spec = importlib.machinery.ModuleSpec(name, None)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    
    # 记录实际路径（如果有）
    if actual_path:
        virtual_modules[name] = actual_path
    
    print(f"创建了虚拟模块: {name}")
    return module

# 创建woniunote顶级包
woniunote_module = create_virtual_module('woniunote')

# 递归创建所有子包和子模块的虚拟模块
def create_subpackages(parent_dir, parent_module_name):
    if not os.path.isdir(parent_dir):
        return
    
    # 为所有子目录创建虚拟包
    for item_name in os.listdir(parent_dir):
        item_path = os.path.join(parent_dir, item_name)
        
        # 跳过特殊目录和非目录项
        if item_name.startswith('__') or item_name.startswith('.'):
            continue
        
        # 处理子包（目录）
        if os.path.isdir(item_path):
            sub_module_name = f"{parent_module_name}.{item_name}"
            create_virtual_module(sub_module_name)
            
            # 递归处理子包的子包
            create_subpackages(item_path, sub_module_name)
        
        # 处理模块（.py文件）
        elif item_name.endswith('.py'):
            module_name = item_name[:-3]  # 去掉.py后缀
            if module_name != '__init__':
                sub_module_name = f"{parent_module_name}.{module_name}"
                module_path = os.path.join(parent_dir, item_name)
                create_virtual_module(sub_module_name, module_path)

# 开始创建子包
create_subpackages(WONIUNOTE_DIR, 'woniunote')

# 使用自定义导入钩子来为woniunote命名空间提供实际实现
class WoniuNoteFinder:
    @staticmethod
    def find_spec(fullname, path=None, target=None):
        # 只处理woniunote命名空间下的导入
        if not fullname.startswith('woniunote.'):
            return None
        
        # 检查是否有对应的实际模块文件
        path_components = fullname.split('.')
        rel_path = os.path.join(*path_components[1:]) + '.py'
        abs_path = os.path.join(WONIUNOTE_DIR, rel_path)
        
        # 如果是目录，查找__init__.py
        if not os.path.exists(abs_path):
            dir_path = os.path.join(WONIUNOTE_DIR, *path_components[1:])
            init_path = os.path.join(dir_path, '__init__.py')
            if os.path.exists(init_path):
                return importlib.machinery.FileFinder(os.path.dirname(init_path)).find_spec(
                    path_components[-1], [os.path.dirname(init_path)])
        else:
            return importlib.machinery.FileFinder(os.path.dirname(abs_path)).find_spec(
                path_components[-1], [os.path.dirname(abs_path)])
        
        return None

# 注册导入钩子
sys.meta_path.insert(0, WoniuNoteFinder())
print("已注册 WoniuNote 自定义导入钩子")

# 手动加载关键模块
print("\n===== 尝试按原始方式导入 =====")
try:
    import app
    create_app = app.create_app
    print("成功导入 app 模块")
except Exception as e:
    print(f"导入 app 模块失败: {e}")
    
    # 尝试直接加载 app.py
    try:
        print("尝试直接加载 app.py...")
        app_path = os.path.join(WONIUNOTE_DIR, 'app.py')
        spec = importlib.util.spec_from_file_location('app', app_path)
        app = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(app)
        create_app = app.create_app
        print("成功加载 app.py 并获取 create_app 函数")
    except Exception as e:
        print(f"直接加载 app.py 失败: {e}")

try:
    from common.create_database import db, User, Article, Comment, Favorite, Credit, Category, Item, Card, CardCategory
    print("成功导入数据库模型")
except Exception as e:
    print(f"导入数据库模型失败: {e}")
    
    # 尝试直接加载
    try:
        print("尝试直接加载 create_database.py...")
        db_path = os.path.join(WONIUNOTE_DIR, 'common', 'create_database.py')
        spec = importlib.util.spec_from_file_location('common.create_database', db_path)
        db_module = importlib.util.module_from_spec(spec)
        sys.modules['common.create_database'] = db_module
        spec.loader.exec_module(db_module)
        
        db = db_module.db
        User = db_module.User
        Article = db_module.Article
        Comment = db_module.Comment
        Favorite = db_module.Favorite
        Credit = db_module.Credit
        Category = db_module.Category
        Item = db_module.Item
        Card = db_module.Card
        CardCategory = db_module.CardCategory
        print("成功直接加载数据库模型")
    except Exception as e:
        print(f"直接加载数据库模型失败: {e}")

# 安装测试和导入钩子修复
def pytest_collect_file(parent, path):
    # 这个钩子可以用来控制pytest如何收集测试文件
    return None


@pytest.fixture(scope="session")
def test_config():
    """Load test configuration from test_config.yaml"""
    config_path = os.path.join(BASE_DIR, 'tests', 'test_config.yaml')
    with open(config_path, 'r', encoding='utf-8') as file:
        return yaml.safe_load(file)


@pytest.fixture(scope="session")
def app():
    """Create and return a Flask application for testing"""
    from tests.test_helpers import app
    app.testing = True
    return app


@pytest.fixture(scope="session")
def app_context(app):
    """Provide a Flask application context for testing"""
    with app.app_context():
        yield


@pytest.fixture(scope="session", autouse=True)
def setup_app_context(app_context):
    """Automatically setup app context for all tests"""
    # This automatically sets up the app context for all tests
    pass


@pytest.fixture(scope="session")
def db_engine(test_config):
    """Create and return a database engine"""
    db_uri = test_config['database']['SQLALCHEMY_DATABASE_URI']
    return create_engine(db_uri)


@pytest.fixture(scope="session")
def db_session_factory(db_engine):
    """Create a factory for database sessions"""
    return sessionmaker(bind=db_engine)


@pytest.fixture(scope="function")
def db_session(db_session_factory):
    """Create a new database session for a test"""
    session = scoped_session(db_session_factory)
    yield session
    session.close()


@pytest.fixture(scope="session")
def test_app(test_config):
    """Create a Flask test application"""
    app = create_app('test')
    app.config.update(test_config)
    
    # Create the application context
    with app.app_context():
        yield app


@pytest.fixture(scope="session")
def test_client(test_app):
    """Create a Flask test client"""
    with test_app.test_client() as client:
        yield client


@pytest.fixture(scope="function")
def authenticated_client(test_app, db_session):
    """Create an authenticated test client"""
    with test_app.test_client() as client:
        # Log in as admin user
        client.post('/user/login', data={
            'username': 'admin',
            'password': 'admin123'  # Assuming this is the admin password from init_test_db.py
        }, follow_redirects=True)
        yield client
        # Log out after test
        client.get('/user/logout', follow_redirects=True)
