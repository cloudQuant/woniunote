#!/usr/bin/env python3
"""
清理未使用导入的脚本
自动检测并报告未使用的导入
"""

import os
import ast
import sys
from pathlib import Path
from typing import Dict, Set, List

def extract_imports(file_path: str) -> Dict[str, Set[str]]:
    """提取文件中的导入语句"""
    imports = {'direct': set(), 'from': set()}
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content)
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports['direct'].add(alias.name.split('.')[0])
                    
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports['direct'].add(node.module.split('.')[0])
                for alias in node.names:
                    imports['from'].add(alias.name)
                    
    except Exception as e:
        print(f"解析文件失败 {file_path}: {e}")
        
    return imports

def extract_usage(file_path: str) -> Set[str]:
    """提取文件中使用的名称"""
    usage = set()
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content)
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                usage.add(node.id)
            elif isinstance(node, ast.Attribute):
                # 处理 module.function 形式的调用
                if isinstance(node.value, ast.Name):
                    usage.add(node.value.id)
                    
    except Exception as e:
        print(f"解析使用情况失败 {file_path}: {e}")
        
    return usage

def check_file_imports(file_path: str) -> Dict[str, List[str]]:
    """检查文件中的未使用导入"""
    imports = extract_imports(file_path)
    usage = extract_usage(file_path)
    
    unused = {
        'direct': [],
        'from': []
    }
    
    # 检查直接导入
    for imp in imports['direct']:
        if imp not in usage:
            unused['direct'].append(imp)
    
    # 检查from导入
    for imp in imports['from']:
        if imp not in usage:
            unused['from'].append(imp)
    
    return unused

def scan_directory(directory: str) -> Dict[str, Dict[str, List[str]]]:
    """扫描目录中的Python文件"""
    results = {}
    
    for root, dirs, files in os.walk(directory):
        # 跳过某些目录
        dirs[:] = [d for d in dirs if d not in ['__pycache__', '.git', 'simple_logs']]
        
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                unused = check_file_imports(file_path)
                
                if unused['direct'] or unused['from']:
                    results[file_path] = unused
    
    return results

def main():
    """主函数"""
    project_root = Path(__file__).parent.parent
    woniunote_dir = project_root / 'woniunote'
    
    print("=== 未使用导入检测报告 ===\n")
    
    results = scan_directory(str(woniunote_dir))
    
    if not results:
        print("✅ 没有发现未使用的导入！")
        return
    
    total_files = len(results)
    total_unused = sum(len(unused['direct']) + len(unused['from']) 
                      for unused in results.values())
    
    print(f"📊 发现 {total_files} 个文件中有 {total_unused} 个未使用的导入\n")
    
    for file_path, unused in results.items():
        rel_path = os.path.relpath(file_path, project_root)
        print(f"📄 {rel_path}")
        
        if unused['direct']:
            print("   直接导入:")
            for imp in unused['direct']:
                print(f"     - import {imp}")
        
        if unused['from']:
            print("   From导入:")
            for imp in unused['from']:
                print(f"     - {imp}")
        
        print()
    
    print("💡 建议:")
    print("1. 检查上述导入是否真的未使用")
    print("2. 某些导入可能用于类型检查或特殊用途")
    print("3. 谨慎删除，确保不会破坏功能")

if __name__ == '__main__':
    main()