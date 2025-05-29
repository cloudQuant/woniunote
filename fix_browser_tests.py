#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
修复浏览器测试超时问题的脚本
将所有30秒超时改为3秒，并添加错误处理
"""

import os
import re
import glob
from pathlib import Path

def fix_browser_timeout_in_file(file_path):
    """修复单个文件中的浏览器超时问题"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        changes_made = []
        
        # 1. 添加超时设置到page.goto()
        content = re.sub(
            r'page\.goto\(([^)]+)\)',
            r'page.goto(\1, timeout=3000)',
            content
        )
        if 'page.goto(' in content and ', timeout=3000' in content:
            changes_made.append("添加page.goto超时设置")
        
        # 2. 添加超时设置到page.wait_for_load_state()
        content = re.sub(
            r'page\.wait_for_load_state\("([^"]+)"\)',
            r'page.wait_for_load_state("\1", timeout=3000)',
            content
        )
        if 'wait_for_load_state(' in content and ', timeout=3000' in content:
            changes_made.append("添加wait_for_load_state超时设置")
        
        # 3. 添加超时设置到locator操作
        content = re.sub(
            r'\.click\(\)',
            r'.click(timeout=3000)',
            content
        )
        if '.click(timeout=3000)' in content:
            changes_made.append("添加click超时设置")
        
        # 4. 添加超时设置到其他操作
        content = re.sub(
            r'\.fill\(([^)]+)\)',
            r'.fill(\1, timeout=3000)',
            content
        )
        if '.fill(' in content and ', timeout=3000' in content:
            changes_made.append("添加fill超时设置")
        
        # 5. 添加超时设置到inner_text()
        content = re.sub(
            r'\.inner_text\(\)',
            r'.inner_text(timeout=3000)',
            content
        )
        if '.inner_text(timeout=3000)' in content:
            changes_made.append("添加inner_text超时设置")
        
        # 6. 添加超时设置到wait_for_selector()
        content = re.sub(
            r'\.wait_for_selector\(([^)]+)\)',
            r'.wait_for_selector(\1, timeout=3000)',
            content
        )
        if 'wait_for_selector(' in content and ', timeout=3000' in content:
            changes_made.append("添加wait_for_selector超时设置")
        
        # 7. 添加异常处理包装器
        if '@pytest.mark.browser' in content and 'try:' not in content:
            # 找到浏览器测试函数并添加try-except
            browser_test_pattern = r'(@pytest\.mark\.browser\s+def\s+test_[^(]+\([^)]+\):\s*"""[^"]*"""\s*)(.*?)(?=\n\s*@|\n\s*def|\n\s*class|\nif __name__|\Z)'
            
            def add_try_except(match):
                decorator_and_def = match.group(1)
                function_body = match.group(2)
                
                # 如果已经有try，就不添加
                if 'try:' in function_body:
                    return match.group(0)
                
                # 添加try-except包装
                lines = function_body.split('\n')
                indented_lines = []
                for line in lines:
                    if line.strip():
                        indented_lines.append('        ' + line.lstrip())
                    else:
                        indented_lines.append(line)
                
                wrapped_body = f"""        try:
{chr(10).join(indented_lines)}
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"浏览器测试执行出错: {{e}}")
            # 尝试截图（如果可能）
            try:
                page.screenshot(path=f"test_error_{{int(time.time())}}.png")
            except:
                pass
            # 重新抛出异常，但是带有更多信息
            raise AssertionError(f"浏览器测试失败: {{e}}")"""
                
                return decorator_and_def + wrapped_body
            
            content = re.sub(browser_test_pattern, add_try_except, content, flags=re.DOTALL)
            if 'try:' in content and 'except Exception as e:' in content:
                changes_made.append("添加异常处理")
        
        # 8. 修复重复的timeout参数
        content = re.sub(r', timeout=3000, timeout=3000', ', timeout=3000', content)
        content = re.sub(r'timeout=3000, timeout=3000', 'timeout=3000', content)
        
        # 9. 添加时间导入
        if 'import time' not in content and 'time.time()' in content:
            # 在已有的import语句后添加time导入
            import_pattern = r'(import [^\n]+\n)'
            if re.search(import_pattern, content):
                content = re.sub(r'(import [^\n]+\n)', r'\1import time\n', content, count=1)
                changes_made.append("添加time模块导入")
        
        # 只有在内容确实改变时才写入文件
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print(f"✅ 修复文件: {file_path}")
            for change in changes_made:
                print(f"   - {change}")
            return True
        else:
            print(f"⏭️  跳过文件: {file_path} (无需修改)")
            return False
            
    except Exception as e:
        print(f"❌ 修复文件失败: {file_path}, 错误: {e}")
        return False

def main():
    """主函数"""
    print("🔧 开始修复浏览器测试超时问题...")
    
    # 查找所有包含浏览器测试的文件
    test_patterns = [
        'tests/functional/**/*.py',
        'tests/**/test_*browser*.py',
        'tests/**/test_*features*.py'
    ]
    
    files_to_fix = set()
    for pattern in test_patterns:
        files_to_fix.update(glob.glob(pattern, recursive=True))
    
    # 只处理包含@pytest.mark.browser的文件
    browser_test_files = []
    for file_path in files_to_fix:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                if '@pytest.mark.browser' in content:
                    browser_test_files.append(file_path)
        except:
            continue
    
    print(f"📁 找到 {len(browser_test_files)} 个包含浏览器测试的文件")
    
    fixed_count = 0
    for file_path in browser_test_files:
        if fix_browser_timeout_in_file(file_path):
            fixed_count += 1
    
    print(f"\n🎉 修复完成！")
    print(f"📊 总计处理: {len(browser_test_files)} 个文件")
    print(f"✅ 成功修复: {fixed_count} 个文件")
    print(f"⏭️  无需修改: {len(browser_test_files) - fixed_count} 个文件")
    
    print(f"\n💡 修复内容:")
    print(f"   - 所有page.goto()超时: 30秒 → 3秒")
    print(f"   - 所有page操作超时: 30秒 → 3秒")
    print(f"   - 添加异常处理和错误恢复")
    print(f"   - 自动截图保存（出错时）")

if __name__ == "__main__":
    main() 