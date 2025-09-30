#!/usr/bin/env python3
"""
修复测试文件中的Unicode编码问题

这个脚本将：
1. 查找所有使用Unicode字符的测试文件
2. 将Unicode字符替换为ASCII字符或英文描述
3. 修复Windows环境下的编码问题
"""

import os
import re
import glob
from pathlib import Path

# Unicode字符映射表
UNICODE_REPLACEMENTS = {
    '✓': '[OK]',
    '✗': '[FAIL]', 
    '⚠': '[WARN]',
    '✅': '[SUCCESS]',
    '❌': '[ERROR]',
    '🔍': '[SEARCH]',
    '📊': '[STATS]',
    '⏰': '[TIMEOUT]',
    '🚀': '[START]',
    '📦': '[PACKAGE]',
    '🎯': '[TARGET]',
    '💡': '[TIP]',
    '🔧': '[FIX]',
    '📈': '[REPORT]',
    '⭐': '[STAR]',
    '🌟': '[GOOD]',
    '🎉': '[GREAT]',
    '👍': '[OK]',
    '🛡️': '[SECURITY]',
    '🔄': '[PROCESS]'
}

def fix_unicode_in_file(file_path):
    """修复单个文件中的Unicode字符"""
    try:
        # 读取文件内容
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        changes_made = 0
        
        # 替换Unicode字符
        for unicode_char, ascii_replacement in UNICODE_REPLACEMENTS.items():
            if unicode_char in content:
                content = content.replace(unicode_char, ascii_replacement)
                changes_made += 1
        
        # 修复f-string中的Unicode字符问题
        # 查找形如 f"...{unicode_char}..." 的模式
        unicode_pattern = r'f["\']([^"\']*[✓✗⚠✅❌🔍📊⏰🚀📦🎯💡🔧📈⭐🌟🎉👍🛡️🔄][^"\']*)["\']'
        
        def replace_unicode_in_fstring(match):
            fstring_content = match.group(1)
            for unicode_char, ascii_replacement in UNICODE_REPLACEMENTS.items():
                fstring_content = fstring_content.replace(unicode_char, ascii_replacement)
            return f'f"{fstring_content}"'
        
        new_content = re.sub(unicode_pattern, replace_unicode_in_fstring, content)
        if new_content != content:
            content = new_content
            changes_made += 1
        
        # 如果有修改，写回文件
        if changes_made > 0:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Fixed {changes_made} Unicode issues in {file_path}")
            return True
        else:
            return False
            
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def fix_all_test_files():
    """修复所有测试文件"""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    tests_dir = os.path.join(project_root, 'tests')
    
    # 查找所有Python测试文件
    test_files = []
    for root, dirs, files in os.walk(tests_dir):
        for file in files:
            if file.endswith('.py') and ('test_' in file or file.endswith('_test.py')):
                test_files.append(os.path.join(root, file))
    
    print(f"Found {len(test_files)} test files to check")
    
    fixed_files = 0
    for test_file in test_files:
        if fix_unicode_in_file(test_file):
            fixed_files += 1
    
    print(f"Fixed Unicode issues in {fixed_files} files")
    return fixed_files

if __name__ == "__main__":
    fix_all_test_files()
