#!/usr/bin/env python3
"""
批量修复测试文件的导入问题
为所有测试文件添加环境设置和mock导入
"""

import os
import re
import glob

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 通用的测试文件头部模板
TEST_HEADER_TEMPLATE = '''# 设置环境和路径
import sys
import os
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, PROJECT_ROOT)

# 设置环境变量
os.environ.setdefault('TESTING', 'True')
os.environ.setdefault('FLASK_ENV', 'testing')
os.environ.setdefault('SECRET_KEY', 'test-key-{filename}')

'''

# Mock模块模板
MOCK_MODULES_TEMPLATE = '''
# 创建必要的mock模块
import types
from unittest.mock import Mock, MagicMock

# Mock woniunote.common模块
if 'woniunote.common' not in sys.modules:
    mock_common = types.ModuleType('woniunote.common')
    sys.modules['woniunote.common'] = mock_common
    
    # 添加常用的mock属性
    mock_common.utils = Mock()
    mock_common.database = Mock()
    mock_common.resource_manager = Mock()
    mock_common.unified_logging = Mock()
    mock_common.performance_enhanced = Mock()
    mock_common.user_experience_optimizer = Mock()
    mock_common.memory_monitor = Mock()

# Mock woniunote.controller模块
if 'woniunote.controller' not in sys.modules:
    mock_controller = types.ModuleType('woniunote.controller')
    sys.modules['woniunote.controller'] = mock_controller
    
    # 添加基本的控制器mock
    mock_controller.index = Mock()
    mock_controller.user = Mock()
    mock_controller.article = Mock()
    mock_controller.admin = Mock()

# Mock woniunote.app_factory模块
if 'woniunote.app_factory' not in sys.modules:
    mock_app_factory = types.ModuleType('woniunote.app_factory')
    mock_app_factory.create_app = Mock()
    sys.modules['woniunote.app_factory'] = mock_app_factory

'''

def fix_test_file(file_path):
    """修复单个测试文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查是否已经有环境设置
        if 'PROJECT_ROOT = os.path.abspath' in content:
            return False  # 已经修复过
        
        # 查找导入部分的结束位置
        lines = content.split('\n')
        insert_position = 0
        
        # 找到第一个非导入、非注释的行
        for i, line in enumerate(lines):
            stripped = line.strip()
            if (stripped and 
                not stripped.startswith('#') and 
                not stripped.startswith('import ') and 
                not stripped.startswith('from ') and
                not stripped.startswith('"""') and
                not stripped.startswith("'''") and
                stripped != ''):
                insert_position = i
                break
        
        # 获取文件名用于生成唯一的SECRET_KEY
        filename = os.path.basename(file_path).replace('.py', '').replace('test_', '')
        
        # 插入环境设置和mock模块
        header = TEST_HEADER_TEMPLATE.format(filename=filename) + MOCK_MODULES_TEMPLATE
        
        # 在适当位置插入
        lines.insert(insert_position, header)
        
        # 写回文件
        new_content = '\n'.join(lines)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print(f"Fixed test file: {file_path}")
        return True
        
    except Exception as e:
        print(f"Error fixing {file_path}: {e}")
        return False

def fix_all_failing_tests():
    """修复所有失败的测试文件"""
    tests_dir = os.path.join(PROJECT_ROOT, 'tests', 'unit')
    
    # 需要修复的测试文件（基于错误报告）
    problematic_files = [
        'test_api_endpoints_advanced.py',
        'test_app_comprehensive_new.py', 
        'test_async_tasks_comprehensive_new.py',
        'test_atomic_password_migration_comprehensive_new.py',
        'test_auth_utils_comprehensive_new.py',
        'test_comment_controller_comprehensive.py',
        'test_core_modules_comprehensive.py',
        'test_performance_enhanced_comprehensive_new.py',
        'test_quick_validation.py',
        'test_user_experience_optimizer_module.py',
        'test_memory_monitor.py'
    ]
    
    fixed_count = 0
    for filename in problematic_files:
        file_path = os.path.join(tests_dir, filename)
        if os.path.exists(file_path):
            if fix_test_file(file_path):
                fixed_count += 1
        else:
            print(f"File not found: {filename}")
    
    print(f"Fixed {fixed_count} test files")
    return fixed_count

if __name__ == "__main__":
    fix_all_failing_tests()