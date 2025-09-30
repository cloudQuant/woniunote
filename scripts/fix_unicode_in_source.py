#!/usr/bin/env python3
"""
修复源代码文件中的Unicode编码问题
针对app.py等源文件中的Unicode字符
"""

import os
import re

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

def fix_source_files():
    """修复源代码文件"""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # 要修复的源文件
    source_files = [
        'woniunote/app.py',
        'woniunote/app_factory.py'
    ]
    
    fixed_files = 0
    for source_file in source_files:
        file_path = os.path.join(project_root, source_file)
        if os.path.exists(file_path):
            if fix_unicode_in_file(file_path):
                fixed_files += 1
        else:
            print(f"File not found: {file_path}")
    
    print(f"Fixed Unicode issues in {fixed_files} source files")
    return fixed_files

if __name__ == "__main__":
    fix_source_files()
