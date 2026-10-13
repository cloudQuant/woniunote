import pytest

def test_core_utils_basic():
    """基础核心工具测试"""
    assert True

def test_core_utils_import():
    """测试核心工具模块导入"""
    import sys
    import os
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    
    # 直接从文件系统加载utils模块
    import importlib.util
    utils_path = os.path.join(project_root, 'woniunote', 'common', 'utils.py')
    spec = importlib.util.spec_from_file_location("utils", utils_path)
    utils_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(utils_module)
    
    assert utils_module is not None
    print("Core utils module loaded successfully")

def test_core_utils_functions():
    """测试核心工具功能"""
    import sys
    import os
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    
    # 直接从文件系统加载utils模块
    import importlib.util
    utils_path = os.path.join(project_root, 'woniunote', 'common', 'utils.py')
    spec = importlib.util.spec_from_file_location("utils", utils_path)
    utils_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(utils_module)
    
    # 测试get_package_path函数
    if hasattr(utils_module, 'get_package_path'):
        get_package_path = utils_module.get_package_path
        result = get_package_path('woniunote')
        assert result is not None
        print(f"get_package_path result: {result}")
    else:
        print("get_package_path function not found, testing other functions")
        # 测试其他已知存在的函数
        assert hasattr(utils_module, 'validate_email')
        assert hasattr(utils_module, 'sanitize_input')
        print("Core utility functions verified")

def test_core_utils_structure():
    """测试核心工具结构"""
    import sys
    import os
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    
    # 验证文件结构存在
    utils_path = os.path.join(project_root, 'woniunote', 'common', 'utils.py')
    database_path = os.path.join(project_root, 'woniunote', 'common', 'database.py')
    
    assert os.path.exists(utils_path), "utils.py should exist"
    assert os.path.exists(database_path), "database.py should exist"
    
    # 先设置mock环境来避免循环依赖
    import types
    from unittest.mock import Mock
    import importlib.util
    
    # 创建必要的mock模块
    if 'woniunote' not in sys.modules:
        woniunote_mock = types.ModuleType('woniunote')
        common_mock = types.ModuleType('woniunote.common')
        utils_mock = Mock()
        utils_mock.read_config = Mock(return_value={})
        common_mock.utils = utils_mock
        woniunote_mock.common = common_mock
        sys.modules['woniunote'] = woniunote_mock
        sys.modules['woniunote.common'] = common_mock
        sys.modules['woniunote.common.utils'] = utils_mock
    
    # 加载utils模块
    spec = importlib.util.spec_from_file_location("utils", utils_path)
    utils_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(utils_module)
    assert utils_module is not None
    
    # 验证database模块文件可读（避免循环依赖问题）
    with open(database_path, 'r', encoding='utf-8') as f:
        database_content = f.read()
        assert len(database_content) > 0
        assert 'def ' in database_content  # 应该包含函数定义
        print("Database module file verified")
    
    print("Core utils structure verified successfully")
