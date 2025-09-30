#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将真正的导入修复方案应用到所有测试文件
"""

import os
import re
import glob

def apply_real_import_solution():
    """应用真正的导入解决方案到所有测试文件"""
    
    # 查找所有测试文件
    test_files = glob.glob("tests/unit/*.py", recursive=True)
    
    for test_file in test_files:
        try:
            with open(test_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            
            # 1. 移除所有"跳过测试"的ImportError处理
            content = re.sub(
                r'except ImportError.*?:\s*print\(f?"Import failed.*?\)\s*assert True',
                'except ImportError as e:\n            pytest.fail(f"Import failed: {e}")',
                content,
                flags=re.DOTALL
            )
            
            # 2. 替换简单的woniunote.common导入为直接文件加载
            # 查找类似 "from woniunote.common.utils import xxx" 的模式
            def replace_import(match):
                module_path = match.group(1)  # 如 "woniunote.common.utils"
                import_items = match.group(2)  # 如 "sanitize_input, gen_email_code"
                
                # 将模块路径转换为文件路径
                file_path = module_path.replace('.', '/')
                if not file_path.endswith('.py'):
                    file_path += '.py'
                
                replacement = f'''# 直接从文件系统加载模块
        import importlib.util
        module_path = os.path.join(project_root, '{file_path}')
        spec = importlib.util.spec_from_file_location("loaded_module", module_path)
        loaded_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(loaded_module)
        
        # 提取需要的函数/类
        {import_items} = loaded_module.{import_items}'''
                
                return replacement
            
            # 应用导入替换
            content = re.sub(
                r'from (woniunote\.common\.\w+) import (\w+(?:, \w+)*)',
                replace_import,
                content
            )
            
            # 3. 替换简单的import woniunote.common.xxx
            content = re.sub(
                r'import (woniunote\.common\.\w+)',
                lambda m: f'''# 直接从文件系统加载模块
        import importlib.util
        module_path = os.path.join(project_root, '{m.group(1).replace(".", "/")}.py')
        spec = importlib.util.spec_from_file_location("loaded_module", module_path)
        loaded_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(loaded_module)''',
                content
            )
            
            # 4. 确保每个测试方法都有project_root设置
            if 'project_root = os.path.abspath' not in content:
                # 在类定义后添加setup方法
                content = re.sub(
                    r'(class \w+.*?:\s*""".*?"""\s*)',
                    r'''\1
    def setup_method(self):
        """设置测试环境"""
        import sys
        import os
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
        self.project_root = project_root
    
    ''',
                    content,
                    flags=re.DOTALL
                )
            
            # 如果内容有变化，写回文件
            if content != original_content:
                with open(test_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"✅ 应用真实导入修复 {test_file}")
                
        except Exception as e:
            print(f"❌ 修复 {test_file} 失败: {e}")

if __name__ == "__main__":
    print("开始应用真实导入解决方案...")
    apply_real_import_solution()
    print("修复完成!")
