#!/usr/bin/env python3
"""
修复并行测试问题的脚本
将所有使用subprocess的测试转换为并行安全的版本
"""
import os
import re
import sys

def fix_subprocess_tests():
    """修复所有subprocess测试"""
    
    # 需要修复的测试文件
    test_files = [
        'tests/unit/test_database_models_comprehensive.py',
        'tests/unit/test_security_comprehensive.py', 
        'tests/unit/test_simple_working.py',
        'tests/unit/test_performance_comprehensive.py',
        'tests/unit/test_logging_comprehensive.py',
        'tests/unit/test_final_comprehensive.py'
    ]
    
    for test_file in test_files:
        if os.path.exists(test_file):
            print(f"修复文件: {test_file}")
            fix_file_subprocess_tests(test_file)
        else:
            print(f"文件不存在: {test_file}")

def fix_file_subprocess_tests(file_path):
    """修复单个文件的subprocess测试"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 查找所有subprocess测试函数
        subprocess_functions = re.findall(r'def (test_\w*subprocess\w*)\(self\):', content)
        
        if not subprocess_functions:
            print(f"  未找到subprocess测试函数")
            return
        
        print(f"  找到 {len(subprocess_functions)} 个subprocess测试函数")
        
        # 为每个subprocess函数添加pytest.mark.subprocess装饰器
        for func_name in subprocess_functions:
            # 查找函数定义
            pattern = rf'(\s+def {func_name}\(self\):)'
            replacement = rf'    @pytest.mark.subprocess\n\1'
            
            if re.search(pattern, content):
                content = re.sub(pattern, replacement, content)
                print(f"    已标记: {func_name}")
        
        # 在文件顶部添加pytest标记定义（如果还没有）
        if '@pytest.mark.subprocess' in content and 'pytestmark = pytest.mark.subprocess' not in content:
            # 在import部分后添加标记定义
            import_section_end = content.find('\n\n# 确保项目根目录')
            if import_section_end == -1:
                import_section_end = content.find('\n\nproject_root')
            if import_section_end == -1:
                import_section_end = content.find('\n\nclass Test')
            
            if import_section_end != -1:
                before = content[:import_section_end]
                after = content[import_section_end:]
                
                # 添加pytest标记配置
                marker_config = '''

# 配置pytest标记
pytestmark = pytest.mark.subprocess  # 标记所有subprocess测试
'''
                content = before + marker_config + after
        
        # 保存修改后的文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"  ✅ 文件修复完成")
        
    except Exception as e:
        print(f"  ❌ 修复文件失败: {e}")

if __name__ == '__main__':
    print("🔧 开始修复并行测试问题...")
    fix_subprocess_tests()
    print("✅ 修复完成!")
