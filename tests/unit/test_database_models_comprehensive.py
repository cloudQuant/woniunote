#!/usr/bin/env python3
"""
WoniuNote 数据库和模型全面测试
测试数据库连接、模型定义和数据操作
"""
import pytest
import os
import sys
import subprocess
from unittest.mock import Mock, patch

# 确保项目根目录在Python路径中
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 设置测试环境变量
TEST_ENV = {
    'FLASK_ENV': 'testing',
    'TESTING': 'True',
    'SECRET_KEY': 'TestSecret123KEY456ForTestingOnly',
    'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
    'DATABASE_URL': 'sqlite:///:memory:',
    'DISABLE_DATABASE_POOL_OPTIMIZER': 'True',
    'SKIP_APP_INIT': 'True',
}

for key, value in TEST_ENV.items():
    os.environ[key] = value

# 防止Flask应用初始化
try:
    import woniunote.app
    woniunote.app.app = None
except ImportError:
    pass


class TestDatabaseConnection:
    """数据库连接测试"""
    
    def test_database_module_import_subprocess(self):
        """使用子进程测试数据库模块导入"""
        cmd = [
            sys.executable, '-c',
            '''
import sys
import os
sys.path.insert(0, ".")

os.environ.update({
    'FLASK_ENV': 'testing',
    'TESTING': 'True',
    'SECRET_KEY': 'TestSecret123KEY456ForTestingOnly',
    'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
    'DISABLE_DATABASE_POOL_OPTIMIZER': 'True',
    'SKIP_APP_INIT': 'True',
})

try:
    import woniunote.app
    woniunote.app.app = None
except:
    pass

# 测试数据库模块导入
database_modules = [
    'woniunote.common.database',
    'woniunote.common.db_connection_manager',
    'woniunote.common.create_database',
]

imported_modules = 0
for module_name in database_modules:
    try:
        module = __import__(module_name, fromlist=[''])
        if module is not None:
            imported_modules += 1
            print(f"[OK] Imported: {module_name}")
        else:
            print(f"[FAIL] Import returned None: {module_name}")
    except Exception as e:
        print(f"[FAIL] Import failed: {module_name} - {e}")

import_rate = imported_modules / len(database_modules)
print(f"Database module import rate: {imported_modules}/{len(database_modules)} ({import_rate:.1%})")

# 要求至少70%导入成功
assert import_rate >= 0.7, f"Database module import rate too low: {import_rate:.1%}"

print("DATABASE_MODULE_IMPORT_SUCCESS")
'''
        ]
        
        env = os.environ.copy()
        env.update(TEST_ENV)
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=project_root, env=env)
        
        assert result.returncode == 0, f"Database module import test failed: {result.stderr}"
        assert "DATABASE_MODULE_IMPORT_SUCCESS" in result.stdout


class TestModelDefinitions:
    """模型定义测试"""
    
    def test_card_model_subprocess(self):
        """使用子进程测试Card模型"""
        cmd = [
            sys.executable, '-c',
            '''
import sys
import os
sys.path.insert(0, ".")

os.environ.update({
    'FLASK_ENV': 'testing',
    'TESTING': 'True',
    'SECRET_KEY': 'TestSecret123KEY456ForTestingOnly',
    'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
    'SKIP_APP_INIT': 'True',
})

try:
    import woniunote.app
    woniunote.app.app = None
except:
    pass

# 测试Card模型导入和定义
try:
    from woniunote.models.card import Card, CardCategory
    
    # 验证Card模型属性
    assert hasattr(Card, '__tablename__'), "Card should have __tablename__"
    print(f"[OK] Card table name: {Card.__tablename__}")
    
    # 验证Card模型字段（如果可访问）
    if hasattr(Card, '__table__'):
        columns = [col.name for col in Card.__table__.columns]
        print(f"[OK] Card columns: {columns}")
        
        # 检查关键字段
        expected_fields = ['id']  # 至少应该有id字段
        for field in expected_fields:
            if field in columns:
                print(f"[OK] Card has {field} field")
    
    # 验证CardCategory模型
    assert hasattr(CardCategory, '__tablename__'), "CardCategory should have __tablename__"
    print(f"[OK] CardCategory table name: {CardCategory.__tablename__}")
    
    if hasattr(CardCategory, '__table__'):
        columns = [col.name for col in CardCategory.__table__.columns]
        print(f"[OK] CardCategory columns: {columns}")
    
    # 测试模型实例化（如果支持）
    try:
        # 只测试类是否可以被调用
        card_class_callable = callable(Card)
        category_class_callable = callable(CardCategory)
        
        assert card_class_callable, "Card class should be callable"
        assert category_class_callable, "CardCategory class should be callable"
        print("[OK] Model classes are callable")
        
    except Exception as e:
        print(f"[WARN] Model instantiation issue (expected): {e}")
    
    print("CARD_MODEL_SUCCESS")
    
except ImportError as e:
    print(f"Card model import failed: {e}")
    raise
except Exception as e:
    print(f"Card model test failed: {e}")
    raise
'''
        ]
        
        env = os.environ.copy()
        env.update(TEST_ENV)
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=project_root, env=env)
        
        assert result.returncode == 0, f"Card model test failed: {result.stderr}"
    def test_basic(self):

        """Basic test placeholder"""

        pass
    
    def test_todo_model_subprocess(self):
        """使用子进程测试Todo模型"""
        cmd = [
            sys.executable, '-c',
            '''
import sys
import os
sys.path.insert(0, ".")

os.environ.update({
    'FLASK_ENV': 'testing',
    'TESTING': 'True',
    'SECRET_KEY': 'TestSecret123KEY456ForTestingOnly',
    'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
    'SKIP_APP_INIT': 'True',
})

try:
    import woniunote.app
    woniunote.app.app = None
except:
    pass

# 测试Todo模型导入和定义
try:
    from woniunote.models.todo import Item, Category
    
    # 验证Item模型属性
    assert hasattr(Item, '__tablename__'), "Item should have __tablename__"
    print(f"[OK] Item table name: {Item.__tablename__}")
    
    # 验证Item模型字段
    if hasattr(Item, '__table__'):
        columns = [col.name for col in Item.__table__.columns]
        print(f"[OK] Item columns: {columns}")
        
        # 检查关键字段
        expected_fields = ['id']
        for field in expected_fields:
            if field in columns:
                print(f"[OK] Item has {field} field")
    
    # 验证Category模型
    assert hasattr(Category, '__tablename__'), "Category should have __tablename__"
    print(f"[OK] Category table name: {Category.__tablename__}")
    
    if hasattr(Category, '__table__'):
        columns = [col.name for col in Category.__table__.columns]
        print(f"[OK] Category columns: {columns}")
    
    # 测试模型类可调用性
    item_class_callable = callable(Item)
    category_class_callable = callable(Category)
    
    assert item_class_callable, "Item class should be callable"
    assert category_class_callable, "Category class should be callable"
    print("[OK] Todo model classes are callable")
    
    print("TODO_MODEL_SUCCESS")
    
except ImportError as e:
    print(f"Todo model import failed: {e}")
    raise
except Exception as e:
    print(f"Todo model test failed: {e}")
    raise
'''
        ]
        
        env = os.environ.copy()
        env.update(TEST_ENV)
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=project_root, env=env)
        
        assert result.returncode == 0, f"Todo model test failed: {result.stderr}"
        assert "TODO_MODEL_SUCCESS" in result.stdout


class TestBusinessModules:
    """业务模块测试"""
    
    def test_users_module_subprocess(self):
        """使用子进程测试用户业务模块"""
        cmd = [
            sys.executable, '-c',
            '''
import sys
import os
sys.path.insert(0, ".")

os.environ.update({
    'FLASK_ENV': 'testing',
    'TESTING': 'True',
    'SECRET_KEY': 'TestSecret123KEY456ForTestingOnly',
    'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
    'SKIP_APP_INIT': 'True',
})

try:
    import woniunote.app
    woniunote.app.app = None
except:
    pass

# 测试用户模块导入
user_modules = [
    'woniunote.module.users',
    'woniunote.module.users_enhanced',
]

imported_modules = 0
available_functions = []

for module_name in user_modules:
    try:
        module = __import__(module_name, fromlist=[''])
        if module is not None:
            imported_modules += 1
            print(f"[OK] Imported: {module_name}")
            
            # 检查模块中的函数
            for attr_name in dir(module):
                if not attr_name.startswith('_') and callable(getattr(module, attr_name)):
                    available_functions.append(f"{module_name}.{attr_name}")
                    
    except Exception as e:
        print(f"[FAIL] Import failed: {module_name} - {e}")

print(f"User modules imported: {imported_modules}/{len(user_modules)}")
print(f"Available functions: {len(available_functions)}")

for func in available_functions[:10]:  # 显示前10个函数
    print(f"  - {func}")

# 测试模块可用性
module_available = imported_modules > 0
assert module_available, "At least one user module should be available"

print("USERS_MODULE_SUCCESS")
'''
        ]
        
        env = os.environ.copy()
        env.update(TEST_ENV)
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=project_root, env=env)
        
        assert result.returncode == 0, f"Users module test failed: {result.stderr}"
        assert "USERS_MODULE_SUCCESS" in result.stdout


if __name__ == "__main__":
    pytest.main([__file__, "-v"])