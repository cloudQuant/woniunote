#!/usr/bin/env python3
"""
修复测试文件中的路径问题
"""

import os
import re

def fix_path_issue(file_path):
    """修复单个文件的路径问题"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        modified = False
        
        # 修复错误的路径设置
        if "os.path.join(os.path.dirname(__file__), '..', '..')" in content:
            content = content.replace(
                "os.path.join(os.path.dirname(__file__), '..', '..')",
                "os.path.join(os.path.dirname(__file__), '..')"
            )
            modified = True
        
        # 移除重复的路径设置
        lines = content.split('\n')
        new_lines = []
        seen_project_root = False
        
        for line in lines:
            if 'project_root = os.path.abspath(' in line:
                if seen_project_root:
                    # 跳过重复的project_root设置
                    continue
                else:
                    seen_project_root = True
                    new_lines.append(line)
            elif 'if project_root not in sys.path:' in line:
                if seen_project_root:
                    new_lines.append(line)
                # 如果没有seen_project_root，跳过这行
            elif 'sys.path.insert(0, project_root)' in line:
                if seen_project_root:
                    new_lines.append(line)
                # 如果没有seen_project_root，跳过这行
            else:
                new_lines.append(line)
        
        if len(new_lines) != len(lines):
            modified = True
            content = '\n'.join(new_lines)
        
        if modified:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ 修复路径: {file_path}")
            return True
        
        return False
        
    except Exception as e:
        print(f"❌ 修复文件 {file_path} 时出错: {e}")
        return False

def main():
    """主函数"""
    test_dir = os.path.join(os.path.dirname(__file__), '..', 'tests')
    
    # 查找所有测试文件
    files_to_fix = []
    
    for root, dirs, files in os.walk(test_dir):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if ('project_root = os.path.abspath(' in content or
                            'os.environ[\'TESTING\'] = \'True\'' in content):
                            files_to_fix.append(file_path)
                except Exception:
                    continue
    
    print(f"找到 {len(files_to_fix)} 个需要检查路径的文件")
    
    fixed_count = 0
    for file_path in files_to_fix:
        if fix_path_issue(file_path):
            fixed_count += 1
    
    print(f"修复了 {fixed_count} 个文件的路径问题")

if __name__ == '__main__':
    main()