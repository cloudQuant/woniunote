#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复测试文件中缺少的mock属性
"""

import os
import re
import glob

def fix_mock_utils_attributes():
    """修复mock_utils缺少的属性"""
    
    # 查找所有测试文件
    test_files = glob.glob("tests/unit/*.py", recursive=True)
    
    for test_file in test_files:
        try:
            with open(test_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            
            # 检查是否有mock_utils的创建
            if 'mock_utils = Mock()' in content and 'mock_utils.logger = Mock()' not in content:
                # 在mock_utils创建后添加缺少的属性
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
            
            # 检查是否有mock_common.utils的创建  
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
            
            # 检查是否有mock_db的创建但缺少db属性
            if 'mock_db = Mock()' in content and 'mock_db.db' not in content:
                content = re.sub(
                    r'(mock_db = Mock\(\))',
                    r'''\1
    mock_db.db = Mock()
    mock_db.dbconnect = Mock()''',
                    content
                )
            
            # 检查是否有mock_logging但缺少logging属性
            if 'mock_logging = Mock()' in content and 'mock_logging.logging' not in content:
                content = re.sub(
                    r'(mock_logging = Mock\(\))',
                    r'''\1
    mock_logging.logging = Mock()''',
                    content
                )
            
            # 如果内容有变化，写回文件
            if content != original_content:
                with open(test_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"✅ 修复了 {test_file}")
                
        except Exception as e:
            print(f"❌ 修复 {test_file} 失败: {e}")

def fix_column_mock_issues():
    """修复Column mock的参数问题"""
    
    test_files = glob.glob("tests/unit/*.py", recursive=True)
    
    for test_file in test_files:
        try:
            with open(test_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            
            # 修复Column.__init__的参数问题
            content = re.sub(
                r'def __init__\(self, \*args, \*\*kwargs\):',
                r'def __init__(self, *args, **kwargs):',
                content
            )
            
            # 修复Column类的定义，使其接受任意参数
            if 'class Column:' in content and 'def __init__(self):' in content:
                content = re.sub(
                    r'(class Column:\s+def __init__\(self\):)',
                    r'''class Column:
                def __init__(self, *args, **kwargs):
                    self.args = args
                    self.kwargs = kwargs''',
                    content,
                    flags=re.MULTILINE | re.DOTALL
                )
            
            if content != original_content:
                with open(test_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"✅ 修复了Column问题 {test_file}")
                
        except Exception as e:
            print(f"❌ 修复Column问题 {test_file} 失败: {e}")

if __name__ == "__main__":
    print("开始修复mock属性...")
    fix_mock_utils_attributes()
    fix_column_mock_issues()
    print("修复完成!")
