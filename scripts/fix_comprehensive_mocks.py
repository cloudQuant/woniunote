#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全面修复所有测试文件中的mock属性问题
"""

import os
import re
import glob

def fix_comprehensive_mock_issues():
    """全面修复mock问题"""
    
    # 查找所有测试文件
    test_files = glob.glob("tests/unit/*.py", recursive=True)
    
    for test_file in test_files:
        try:
            with open(test_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            
            # 1. 修复mock_utils缺少logger等属性的问题
            if 'mock_utils = Mock()' in content:
                # 确保mock_utils有所有必要的属性
                content = re.sub(
                    r'(mock_utils = Mock\(\))',
                    r'''\1
    mock_utils.logger = Mock()
    mock_utils.jieba = Mock()
    mock_utils.jieba.cut = Mock(return_value=['test', 'words'])
    mock_utils.Flask = Mock()
    mock_utils.gc = Mock()
    mock_utils.gc.collect = Mock(return_value=10)
    mock_utils.psutil = Mock()
    mock_utils.sys = Mock()
    mock_utils.get_logger = Mock()
    mock_utils.__doc__ = "Mock utils module"
    mock_utils.__file__ = "mock_file_path"
    mock_utils.UserExperienceOptimizer = Mock''',
                    content
                )
            
            # 2. 修复mock_common.utils缺少属性的问题
            if 'mock_common.utils = Mock()' in content and 'mock_common.utils.logger' not in content:
                content = re.sub(
                    r'(mock_common\.utils = Mock\(\))',
                    r'''\1
    mock_common.utils.logger = Mock()
    mock_common.utils.jieba = Mock()
    mock_common.utils.jieba.cut = Mock(return_value=['test', 'words'])
    mock_common.utils.Flask = Mock()
    mock_common.utils.gc = Mock()
    mock_common.utils.gc.collect = Mock(return_value=10)
    mock_common.utils.psutil = Mock()
    mock_common.utils.sys = Mock()
    mock_common.utils.get_logger = Mock()
    mock_common.utils.__doc__ = "Mock utils module"
    mock_common.utils.__file__ = "mock_file_path"
    mock_common.utils.UserExperienceOptimizer = Mock''',
                    content
                )
            
            # 3. 修复mock_db缺少db属性的问题
            if 'mock_db = Mock()' in content and 'mock_db.db' not in content:
                content = re.sub(
                    r'(mock_db = Mock\(\))',
                    r'''\1
    mock_db.db = Mock()
    mock_db.dbconnect = Mock()''',
                    content
                )
            
            # 4. 修复mock_logging缺少logging属性的问题
            if 'mock_logging = Mock()' in content and 'mock_logging.logging' not in content:
                content = re.sub(
                    r'(mock_logging = Mock\(\))',
                    r'''\1
    mock_logging.logging = Mock()''',
                    content
                )
            
            # 5. 为使用@patch装饰器的测试添加完整的mock_utils
            if '@patch(' in content and 'mock_utils' in content:
                # 在文件开头添加完整的mock_utils定义
                if 'if \'mock_utils\' not in sys.modules:' not in content:
                    mock_setup = '''
# 完整的mock_utils设置
import types
from unittest.mock import Mock

if 'mock_utils' not in sys.modules:
    mock_utils = types.ModuleType('mock_utils')
    mock_utils.logger = Mock()
    mock_utils.jieba = Mock()
    mock_utils.jieba.cut = Mock(return_value=['test', 'words'])
    mock_utils.Flask = Mock()
    mock_utils.gc = Mock()
    mock_utils.gc.collect = Mock(return_value=10)
    mock_utils.psutil = Mock()
    mock_utils.sys = Mock()
    mock_utils.get_logger = Mock()
    mock_utils.__doc__ = "Mock utils module"
    mock_utils.__file__ = "mock_file_path"
    mock_utils.UserExperienceOptimizer = Mock
    sys.modules['mock_utils'] = mock_utils

'''
                    # 在import语句后添加
                    content = re.sub(
                        r'(import sys\nimport os)',
                        r'\1' + mock_setup,
                        content
                    )
            
            # 如果内容有变化，写回文件
            if content != original_content:
                with open(test_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"✅ 修复了mock属性 {test_file}")
                
        except Exception as e:
            print(f"❌ 修复mock属性 {test_file} 失败: {e}")

if __name__ == "__main__":
    print("开始全面修复mock属性问题...")
    fix_comprehensive_mock_issues()
    print("修复完成!")
