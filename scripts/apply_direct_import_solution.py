#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将直接文件系统导入的成功方案应用到所有测试文件
"""

import os
import re
import glob

def create_direct_import_helper():
    """创建直接导入的辅助函数"""
    return '''
def load_module_from_file(module_name, file_path, project_root):
    """从文件路径直接加载模块"""
    import importlib.util
    import sys
    
    # 确保项目根目录在路径中
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    
    # 直接从文件加载模块
    full_path = os.path.join(project_root, file_path)
    if not os.path.exists(full_path):
        raise FileNotFoundError(f"Module file not found: {full_path}")
    
    spec = importlib.util.spec_from_file_location(module_name, full_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
'''

def apply_direct_import_to_file(test_file):
    """应用直接导入方案到单个测试文件"""
    try:
        with open(test_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # 1. 在文件开头添加辅助函数（如果还没有）
        if 'def load_module_from_file(' not in content:
            # 在import语句后添加辅助函数
            import_section = re.search(r'(import.*?\n)+', content)
            if import_section:
                insert_pos = import_section.end()
                content = content[:insert_pos] + create_direct_import_helper() + '\n' + content[insert_pos:]
        
        # 2. 替换woniunote.common.xxx的导入
        # 替换 "from woniunote.common.utils import xxx"
        content = re.sub(
            r'from woniunote\.common\.(\w+) import (\w+(?:, \w+)*)',
            lambda m: f'''# 直接加载{m.group(1)}模块
        {m.group(1)}_module = load_module_from_file("{m.group(1)}", "woniunote/common/{m.group(1)}.py", project_root)
        {m.group(2)} = {m.group(1)}_module.{m.group(2)}''',
            content
        )
        
        # 替换 "import woniunote.common.xxx"
        content = re.sub(
            r'import woniunote\.common\.(\w+)',
            lambda m: f'''# 直接加载{m.group(1)}模块
        {m.group(1)}_module = load_module_from_file("{m.group(1)}", "woniunote/common/{m.group(1)}.py", project_root)''',
            content
        )
        
        # 3. 替换woniunote.module.xxx的导入
        content = re.sub(
            r'from woniunote\.module\.(\w+) import (\w+(?:, \w+)*)',
            lambda m: f'''# 直接加载{m.group(1)}模块
        {m.group(1)}_module = load_module_from_file("{m.group(1)}", "woniunote/module/{m.group(1)}.py", project_root)
        {m.group(2)} = {m.group(1)}_module.{m.group(2)}''',
            content
        )
        
        # 4. 确保每个测试方法都有project_root
        content = re.sub(
            r'(def test_\w+\(self\):\s*""".*?"""\s*)',
            r'''\1# 设置项目根目录
        import sys
        import os
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
        
        ''',
            content,
            flags=re.DOTALL
        )
        
        # 5. 移除"跳过测试"的处理
        content = re.sub(
            r'except ImportError.*?:\s*assert True.*?# Test converted from skip',
            '',
            content,
            flags=re.DOTALL
        )
        
        # 如果内容有变化，写回文件
        if content != original_content:
            with open(test_file, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        return False
        
    except Exception as e:
        print(f"❌ 处理 {test_file} 失败: {e}")
        return False

def apply_to_all_tests():
    """应用到所有测试文件"""
    
    # 重点修复的测试文件
    priority_files = [
        'tests/unit/test_user_experience_optimizer_module.py',
        'tests/unit/test_core_utils_comprehensive.py',
        'tests/unit/test_core_functionality_reliable.py',
        'tests/unit/test_memory_monitor.py',
        'tests/unit/test_ultra_high_coverage.py'
    ]
    
    fixed_count = 0
    
    for test_file in priority_files:
        if os.path.exists(test_file):
            if apply_direct_import_to_file(test_file):
                print(f"✅ 修复了 {test_file}")
                fixed_count += 1
            else:
                print(f"⚪ {test_file} 无需修改")
        else:
            print(f"❌ 文件不存在: {test_file}")
    
    print(f"\n总共修复了 {fixed_count} 个文件")

if __name__ == "__main__":
    print("开始应用直接导入解决方案...")
    apply_to_all_tests()
    print("修复完成!")
