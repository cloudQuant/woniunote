#!/usr/bin/env python
"""
修复测试文件整合脚本 - 正确提取完整的函数定义
"""
import os
import re
import ast
from pathlib import Path

def extract_complete_test_functions(content):
    """正确提取完整的测试函数，包括函数体"""
    test_functions = []

    # 使用AST解析代码
    try:
        tree = ast.parse(content)

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name.startswith('test_'):
                # 获取函数的源代码范围
                start_line = node.lineno - 1  # AST lineno是从1开始的
                end_line = node.end_lineno

                # 从源代码中提取这个函数的完整内容
                lines = content.split('\n')
                function_lines = lines[start_line:end_line]

                # 确保第一行的缩进是正确的
                if function_lines:
                    # 找到第一行非空字符的缩进
                    first_line = function_lines[0]
                    indent_match = re.match(r'^(\s*)', first_line)
                    base_indent = indent_match.group(1) if indent_match else ''

                    # 标准化缩进（假设基础缩进是4个空格）
                    normalized_lines = []
                    for line in function_lines:
                        if line.strip():  # 非空行
                            # 如果行以更少的缩进开始，保持原样
                            line_indent_match = re.match(r'^(\s*)', line)
                            line_indent = line_indent_match.group(1) if line_indent_match else ''
                            if len(line_indent) >= len(base_indent):
                                # 移除基础缩进
                                normalized_line = line[len(base_indent):]
                            else:
                                normalized_line = line
                        else:
                            normalized_line = line
                        normalized_lines.append(normalized_line)

                    test_functions.append({
                        'name': node.name,
                        'lines': normalized_lines,
                        'start_line': start_line
                    })

    except SyntaxError as e:
        print(f"❌ 解析文件时出现语法错误: {str(e)}")
        # 回退到基于文本的解析
        return extract_test_functions_fallback(content)

    return test_functions

def extract_test_functions_fallback(content):
    """基于文本的测试函数提取（备用方案）"""
    test_functions = []
    lines = content.split('\n')

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # 查找测试函数定义
        if line.startswith('def test_') and '(' in line:
            function_lines = []
            indent_level = len(lines[i]) - len(lines[i].lstrip())

            # 添加函数定义行
            function_lines.append(lines[i])

            # 查找函数体
            j = i + 1
            while j < len(lines):
                current_line = lines[j]
                if current_line.strip() == '':
                    function_lines.append(current_line)
                    j += 1
                    continue

                current_indent = len(current_line) - len(current_line.lstrip())

                # 如果遇到相同或更少缩进的非空行，函数结束
                if current_indent <= indent_level and current_line.strip():
                    if current_line.strip().startswith(('def ', 'class ')):
                        break

                function_lines.append(current_line)
                j += 1

                # 防止无限循环
                if j - i > 1000:  # 最多1000行
                    break

            func_name = line.split('(')[0].replace('def ', '')

            test_functions.append({
                'name': func_name,
                'lines': function_lines,
                'start_line': i
            })

            i = j - 1  # 跳到函数结束后的行

        i += 1

    return test_functions

def consolidate_module_tests_fixed(primary_file, other_files):
    """修复版本的模块测试整合"""
    print(f"  📄 主文件: {os.path.basename(primary_file)}")

    # 读取主文件
    try:
        with open(primary_file, 'r', encoding='utf-8') as f:
            primary_content = f.read()
    except Exception as e:
        print(f"  ❌ 无法读取主文件: {str(e)}")
        return

    primary_lines = primary_content.split('\n')

    # 提取主文件中的测试函数名
    primary_functions = set()
    primary_test_functions = extract_complete_test_functions(primary_content)
    for func in primary_test_functions:
        primary_functions.add(func['name'])

    print(f"  📊 主文件已有 {len(primary_functions)} 个测试函数")

    consolidated_functions = []
    files_to_remove = []

    # 处理其他文件
    for other_file in other_files:
        print(f"  📋 处理: {os.path.basename(other_file)}")

        try:
            with open(other_file, 'r', encoding='utf-8') as f:
                content = f.read()

            other_test_functions = extract_complete_test_functions(content)

            new_functions = []
            for func in other_test_functions:
                if func['name'] not in primary_functions:
                    new_functions.append(func)

            if new_functions:
                print(f"    ✅ 发现 {len(new_functions)} 个新测试函数")

                # 添加新函数到主文件
                for func in new_functions:
                    consolidated_functions.extend(func['lines'])
                    consolidated_functions.append('')  # 空行分隔
                    primary_functions.add(func['name'])

            else:
                print(f"    ⚠️  所有测试函数已存在于主文件中")

            # 标记为可删除
            files_to_remove.append(other_file)

        except Exception as e:
            print(f"  ❌ 处理失败: {str(e)}")
            import traceback
            traceback.print_exc()

    # 如果有新函数要添加
    if consolidated_functions:
        print(f"  📝 添加 {len([f for f in consolidated_functions if f.strip().startswith('def test_')])} 个新测试函数到主文件")

        # 找到合适的位置插入新函数（在文件末尾）
        insert_position = len(primary_lines)

        # 确保在文件末尾有足够的空行
        while primary_lines and primary_lines[-1].strip() == '':
            primary_lines.pop()

        primary_lines.append('')
        primary_lines.append('')
        primary_lines.append('# === 整合的测试用例 ===')
        primary_lines.append('')

        # 添加新函数
        primary_lines.extend(consolidated_functions)

        # 写入文件
        try:
            with open(primary_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(primary_lines))
            print(f"  ✅ 已更新主文件")
        except Exception as e:
            print(f"  ❌ 更新主文件失败: {str(e)}")
            return

    # 删除其他文件
    for file_to_remove in files_to_remove:
        try:
            backup_file = file_to_remove + '.final_backup'
            os.rename(file_to_remove, backup_file)
            print(f"    🗑️  已备份并移除: {os.path.basename(file_to_remove)}")
        except Exception as e:
            print(f"    ❌ 删除失败: {str(e)}")

    print(f"  📊 完成: 处理了 {len(files_to_remove)} 个文件")

def fix_consolidation():
    """修复整合问题"""
    print("🔧 修复测试文件整合...")

    # 需要修复的文件
    files_to_fix = [
        'tests/unit/test_article_controller_comprehensive_new.py',
        'tests/unit/test_performance_enhanced_comprehensive_new.py',
        'tests/unit/test_index_controller_comprehensive.py',
        'tests/unit/test_unified_security_comprehensive_new.py',
        'tests/unit/test_admin_controller_comprehensive_new.py',
        'tests/unit/test_unified_response_comprehensive_new.py',
        'tests/unit/test_authorization_comprehensive_new.py',
        'tests/unit/test_code_refactor_helper_comprehensive_new.py',
        'tests/unit/test_create_database_comprehensive.py',
        'tests/unit/test_auth_utils_comprehensive_new.py',
        'tests/unit/test_rate_limiter_comprehensive_new.py',
        'tests/unit/test_atomic_password_migration_comprehensive_new.py',
        'tests/unit/test_app_comprehensive_new.py',
        'tests/unit/test_user_controller_comprehensive_new.py',
        'tests/unit/test_log_decorator_comprehensive.py',
        'tests/unit/test_todo_database_comprehensive.py',
        'tests/unit/test_models_comprehensive_new.py',
        'tests/unit/test_async_tasks_comprehensive_new.py',
        'tests/unit/test_base_model_comprehensive_new.py',
        'tests/unit/test_card_database_comprehensive.py',
        'tests/unit/test_articles_module_comprehensive_new.py',
        'tests/unit/test_users_module_comprehensive_new.py'
    ]

    # 对应的源文件
    source_files = [
        ['tests/unit/test_article_controller_comprehensive.py.final_backup', 'tests/unit/test_article_controller.py.final_backup'],
        ['tests/unit/test_performance_enhanced_comprehensive.py.final_backup'],
        ['tests/unit/test_index_controller.py.final_backup'],
        ['tests/unit/test_unified_security_comprehensive.py.final_backup'],
        ['tests/unit/test_admin_controller.py.final_backup', 'tests/unit/test_admin_controller_comprehensive.py.final_backup'],
        ['tests/unit/test_unified_response.py.final_backup'],
        ['tests/unit/test_authorization_comprehensive.py.final_backup'],
        ['tests/unit/test_code_refactor_helper_comprehensive.py.final_backup'],
        ['tests/unit/test_create_database.py.final_backup'],
        ['tests/unit/test_auth_utils_comprehensive.py.final_backup'],
        ['tests/unit/test_rate_limiter_comprehensive.py.final_backup'],
        ['tests/unit/test_atomic_password_migration_comprehensive.py.final_backup'],
        ['tests/unit/test_app_comprehensive.py.final_backup', 'tests/unit/test_app.py.final_backup'],
        ['tests/unit/test_user_controller_comprehensive.py.final_backup', 'tests/unit/test_user_controller.py.final_backup'],
        ['tests/unit/test_log_decorator.py.final_backup'],
        ['tests/unit/test_todo_database.py.final_backup'],
        ['tests/unit/test_models_comprehensive.py.final_backup', 'tests/unit/test_models.py.final_backup'],
        ['tests/unit/test_async_tasks_comprehensive.py.final_backup'],
        ['tests/unit/test_base_model_comprehensive.py.final_backup'],
        ['tests/unit/test_card_database.py.final_backup'],
        ['tests/unit/test_articles_module.py.final_backup'],
        ['tests/unit/test_users_module.py.final_backup']
    ]

    for i, primary_file in enumerate(files_to_fix):
        if os.path.exists(primary_file):
            print(f"\n🔄 修复 {os.path.basename(primary_file)}")

            # 检查源文件是否存在
            existing_sources = [f for f in source_files[i] if os.path.exists(f)]
            if existing_sources:
                consolidate_module_tests_fixed(primary_file, existing_sources)
            else:
                print(f"  ⚠️  没有找到源文件")
        else:
            print(f"⚠️  主文件不存在: {primary_file}")

    print("\n✅ 修复完成！")

if __name__ == "__main__":
    fix_consolidation()
