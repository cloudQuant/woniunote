#!/usr/bin/env python
"""
正确整合测试文件的脚本 - 真正整合测试用例内容
"""
import os
import re
import ast
from pathlib import Path

def extract_test_functions(content):
    """从测试文件中提取所有测试函数"""
    test_functions = []

    # 查找所有测试函数定义
    lines = content.split('\n')
    current_function = None
    function_lines = []
    indent_level = 0

    for i, line in enumerate(lines):
        stripped = line.strip()

        # 如果是测试函数开始
        if stripped.startswith('def test_') and '(' in stripped:
            if current_function:
                # 保存之前的函数
                test_functions.append({
                    'name': current_function,
                    'lines': function_lines,
                    'start_line': current_start_line
                })

            # 开始新函数
            current_function = stripped.split('(')[0].replace('def ', '')
            function_lines = [line]
            current_start_line = i
            indent_level = len(line) - len(line.lstrip())

        elif current_function and line.strip():
            # 检查是否还在函数内（通过缩进判断）
            current_indent = len(line) - len(line.lstrip())
            if current_indent > indent_level or (line.strip().startswith(('def ', 'class ')) and current_indent == indent_level):
                # 函数结束
                test_functions.append({
                    'name': current_function,
                    'lines': function_lines,
                    'start_line': current_start_line
                })
                current_function = None
                function_lines = []
            else:
                function_lines.append(line)

        elif current_function:
            function_lines.append(line)

    # 保存最后一个函数
    if current_function:
        test_functions.append({
            'name': current_function,
            'lines': function_lines,
            'start_line': current_start_line
        })

    return test_functions

def consolidate_module_tests(primary_file, other_files):
    """正确整合一个模块的测试文件"""
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
    for line in primary_lines:
        if line.strip().startswith('def test_'):
            func_name = line.strip().split('(')[0].replace('def ', '')
            primary_functions.add(func_name)

    print(f"  📊 主文件已有 {len(primary_functions)} 个测试函数")

    consolidated_functions = []
    files_to_remove = []

    # 处理其他文件
    for other_file in other_files:
        print(f"  📋 处理: {os.path.basename(other_file)}")

        try:
            with open(other_file, 'r', encoding='utf-8') as f:
                content = f.read()

            other_lines = content.split('\n')

            # 提取测试函数
            test_functions = extract_test_functions(content)

            new_functions = []
            for func in test_functions:
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

        # 在主文件末尾添加新函数
        consolidated_content = primary_content.rstrip() + '\n\n\n# === 整合的测试用例 ===\n\n' + '\n'.join(consolidated_functions)

        # 备份原文件
        backup_file = primary_file + '.backup'
        try:
            with open(backup_file, 'w', encoding='utf-8') as f:
                f.write(primary_content)
            print(f"  💾 已备份主文件: {os.path.basename(backup_file)}")
        except Exception as e:
            print(f"  ⚠️ 备份失败: {str(e)}")

        # 写入整合后的内容
        try:
            with open(primary_file, 'w', encoding='utf-8') as f:
                f.write(consolidated_content)
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

def consolidate_all_modules():
    """整合所有需要整合的模块"""
    print("🚀 开始正确整合测试文件...\n")

    # 定义需要整合的模块
    modules_to_consolidate = [
        {
            'primary': 'tests/unit/test_article_controller_comprehensive_new.py',
            'others': [
                'tests/unit/test_article_controller_comprehensive.py',
                'tests/unit/test_article_controller.py'
            ]
        },
        {
            'primary': 'tests/unit/test_performance_enhanced_comprehensive_new.py',
            'others': ['tests/unit/test_performance_enhanced_comprehensive.py']
        },
        {
            'primary': 'tests/unit/test_index_controller_comprehensive.py',
            'others': ['tests/unit/test_index_controller.py']
        },
        {
            'primary': 'tests/unit/test_unified_security_comprehensive_new.py',
            'others': ['tests/unit/test_unified_security_comprehensive.py']
        },
        {
            'primary': 'tests/unit/test_admin_controller_comprehensive_new.py',
            'others': [
                'tests/unit/test_admin_controller.py',
                'tests/unit/test_admin_controller_comprehensive.py'
            ]
        },
        {
            'primary': 'tests/unit/test_unified_response_comprehensive_new.py',
            'others': ['tests/unit/test_unified_response.py']
        },
        {
            'primary': 'tests/unit/test_authorization_comprehensive_new.py',
            'others': ['tests/unit/test_authorization_comprehensive.py']
        },
        {
            'primary': 'tests/unit/test_code_refactor_helper_comprehensive_new.py',
            'others': ['tests/unit/test_code_refactor_helper_comprehensive.py']
        },
        {
            'primary': 'tests/unit/test_create_database_comprehensive.py',
            'others': ['tests/unit/test_create_database.py']
        },
        {
            'primary': 'tests/unit/test_auth_utils_comprehensive_new.py',
            'others': ['tests/unit/test_auth_utils_comprehensive.py']
        },
        {
            'primary': 'tests/unit/test_rate_limiter_comprehensive_new.py',
            'others': ['tests/unit/test_rate_limiter_comprehensive.py']
        },
        {
            'primary': 'tests/unit/test_atomic_password_migration_comprehensive_new.py',
            'others': ['tests/unit/test_atomic_password_migration_comprehensive.py']
        },
        {
            'primary': 'tests/unit/test_app_comprehensive_new.py',
            'others': [
                'tests/unit/test_app_comprehensive.py',
                'tests/unit/test_app.py'
            ]
        },
        {
            'primary': 'tests/unit/test_user_controller_comprehensive_new.py',
            'others': [
                'tests/unit/test_user_controller_comprehensive.py',
                'tests/unit/test_user_controller.py'
            ]
        },
        {
            'primary': 'tests/unit/test_log_decorator_comprehensive.py',
            'others': ['tests/unit/test_log_decorator.py']
        },
        {
            'primary': 'tests/unit/test_todo_database_comprehensive.py',
            'others': ['tests/unit/test_todo_database.py']
        },
        {
            'primary': 'tests/unit/test_models_comprehensive_new.py',
            'others': [
                'tests/unit/test_models_comprehensive.py',
                'tests/unit/test_models.py'
            ]
        },
        {
            'primary': 'tests/unit/test_async_tasks_comprehensive_new.py',
            'others': ['tests/unit/test_async_tasks_comprehensive.py']
        },
        {
            'primary': 'tests/unit/test_base_model_comprehensive_new.py',
            'others': ['tests/unit/test_base_model_comprehensive.py']
        },
        {
            'primary': 'tests/unit/test_card_database_comprehensive.py',
            'others': ['tests/unit/test_card_database.py']
        },
        {
            'primary': 'tests/unit/test_articles_module_comprehensive_new.py',
            'others': ['tests/unit/test_articles_module.py']
        },
        {
            'primary': 'tests/unit/test_users_module_comprehensive_new.py',
            'others': ['tests/unit/test_users_module.py']
        }
    ]

    total_files_removed = 0
    total_functions_added = 0

    for module in modules_to_consolidate:
        primary_file = module['primary']
        other_files = module['others']

        # 检查主文件是否存在
        if not os.path.exists(primary_file):
            print(f"⚠️  主文件不存在: {primary_file}")
            continue

        # 检查是否有其他文件需要整合
        existing_others = [f for f in other_files if os.path.exists(f)]
        if not existing_others:
            print(f"⚠️  没有找到需要整合的文件: {os.path.basename(primary_file)}")
            continue

        module_name = os.path.basename(primary_file).replace('test_', '').replace('_comprehensive_new.py', '').replace('_comprehensive.py', '').replace('.py', '')
        print(f"\n📝 整合 {module_name} 模块...")

        # 统计整合前的函数数量
        try:
            with open(primary_file, 'r', encoding='utf-8') as f:
                before_content = f.read()
            before_functions = len(re.findall(r'def test_\w+\s*\(', before_content))
        except:
            before_functions = 0

        consolidate_module_tests(primary_file, existing_others)

        # 统计整合后的函数数量
        try:
            with open(primary_file, 'r', encoding='utf-8') as f:
                after_content = f.read()
            after_functions = len(re.findall(r'def test_\w+\s*\(', after_content))
        except:
            after_functions = 0

        functions_added = after_functions - before_functions
        total_functions_added += functions_added
        total_files_removed += len(existing_others)

        print(f"  📊 {module_name}: 添加了 {functions_added} 个测试函数")

    print(f"\n🎉 整合完成!")
    print(f"📊 统计结果:")
    print(f"   - 删除文件数: {total_files_removed}")
    print(f"   - 新增测试函数: {total_functions_added}")
    print(f"   - 剩余主文件数: {len(modules_to_consolidate)}")

if __name__ == "__main__":
    consolidate_all_modules()
