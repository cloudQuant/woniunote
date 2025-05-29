#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
修复测试文件格式问题
"""

import os
import re
import glob

def fix_indentation_issues(file_path):
    """修复缩进问题"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # 修复破损的缩进和格式
        lines = content.split('\n')
        fixed_lines = []
        i = 0
        
        while i < len(lines):
            line = lines[i]
            
            # 如果这行是 "            try:" 而下一行缩进不对
            if line.strip() == 'try:' and i + 1 < len(lines):
                # 找到当前行的缩进
                current_indent = len(line) - len(line.lstrip())
                fixed_lines.append(line)
                i += 1
                
                # 处理try块内的内容
                while i < len(lines) and not lines[i].strip().startswith('except'):
                    next_line = lines[i]
                    if next_line.strip() and not next_line.startswith(' ' * (current_indent + 4)):
                        # 修复缩进
                        fixed_lines.append(' ' * (current_indent + 4) + next_line.lstrip())
                    else:
                        fixed_lines.append(next_line)
                    i += 1
                
                # 处理except块
                if i < len(lines) and lines[i].strip().startswith('except'):
                    except_line = lines[i]
                    # 确保except与try对齐
                    fixed_lines.append(' ' * current_indent + except_line.lstrip())
                    i += 1
                    
                    # 处理except块内容
                    while i < len(lines) and (not lines[i].strip() or lines[i].startswith(' ')):
                        next_line = lines[i]
                        if next_line.strip() and not next_line.startswith(' ' * (current_indent + 4)):
                            fixed_lines.append(' ' * (current_indent + 4) + next_line.lstrip())
                        else:
                            fixed_lines.append(next_line)
                        i += 1
                continue
            
            fixed_lines.append(line)
            i += 1
        
        content = '\n'.join(fixed_lines)
        
        # 移除重复的空行
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
        
        # 修复函数定义格式
        content = re.sub(r'(\n@pytest\.mark\.browser\s*\n)(def test_)', r'\1\2', content)
        
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ 修复格式: {file_path}")
            return True
        else:
            print(f"⏭️  格式正确: {file_path}")
            return False
            
    except Exception as e:
        print(f"❌ 修复格式失败: {file_path}, 错误: {e}")
        return False

def main():
    """主函数"""
    print("🔧 开始修复测试文件格式问题...")
    
    # 查找所有测试文件
    test_files = []
    for pattern in ['tests/functional/**/*.py']:
        test_files.extend(glob.glob(pattern, recursive=True))
    
    print(f"📁 找到 {len(test_files)} 个测试文件")
    
    fixed_count = 0
    for file_path in test_files:
        if fix_indentation_issues(file_path):
            fixed_count += 1
    
    print(f"\n🎉 格式修复完成！")
    print(f"✅ 成功修复: {fixed_count} 个文件")

if __name__ == "__main__":
    main() 