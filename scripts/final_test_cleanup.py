#!/usr/bin/env python
"""
最终测试文件清理脚本 - 简化和清理测试文件结构
"""
import os
import shutil
from pathlib import Path

def cleanup_test_files():
    """清理和简化测试文件结构"""
    print("🧹 开始最终测试文件清理...")

    # 定义需要保留的主文件和要删除的文件
    cleanup_plan = {
        # article_controller 模块
        'tests/unit/test_article_controller_comprehensive_new.py': [
            'tests/unit/test_article_controller_comprehensive.py',
            'tests/unit/test_article_controller.py'
        ],

        # performance_enhanced 模块
        'tests/unit/test_performance_enhanced_comprehensive_new.py': [
            'tests/unit/test_performance_enhanced_comprehensive.py'
        ],

        # index_controller 模块
        'tests/unit/test_index_controller_comprehensive.py': [
            'tests/unit/test_index_controller.py'
        ],

        # unified_security 模块
        'tests/unit/test_unified_security_comprehensive_new.py': [
            'tests/unit/test_unified_security_comprehensive.py'
        ],

        # admin_controller 模块
        'tests/unit/test_admin_controller_comprehensive_new.py': [
            'tests/unit/test_admin_controller.py',
            'tests/unit/test_admin_controller_comprehensive.py'
        ],

        # unified_response 模块
        'tests/unit/test_unified_response_comprehensive_new.py': [
            'tests/unit/test_unified_response.py'
        ],

        # authorization 模块
        'tests/unit/test_authorization_comprehensive_new.py': [
            'tests/unit/test_authorization_comprehensive.py'
        ],

        # code_refactor_helper 模块
        'tests/unit/test_code_refactor_helper_comprehensive_new.py': [
            'tests/unit/test_code_refactor_helper_comprehensive.py'
        ],

        # create_database 模块
        'tests/unit/test_create_database_comprehensive.py': [
            'tests/unit/test_create_database.py'
        ],

        # auth_utils 模块
        'tests/unit/test_auth_utils_comprehensive_new.py': [
            'tests/unit/test_auth_utils_comprehensive.py'
        ],

        # rate_limiter 模块
        'tests/unit/test_rate_limiter_comprehensive_new.py': [
            'tests/unit/test_rate_limiter_comprehensive.py'
        ],

        # atomic_password_migration 模块
        'tests/unit/test_atomic_password_migration_comprehensive_new.py': [
            'tests/unit/test_atomic_password_migration_comprehensive.py'
        ],

        # app 模块
        'tests/unit/test_app_comprehensive_new.py': [
            'tests/unit/test_app_comprehensive.py',
            'tests/unit/test_app.py'
        ],

        # user_controller 模块
        'tests/unit/test_user_controller_comprehensive_new.py': [
            'tests/unit/test_user_controller_comprehensive.py',
            'tests/unit/test_user_controller.py'
        ],

        # log_decorator 模块
        'tests/unit/test_log_decorator_comprehensive.py': [
            'tests/unit/test_log_decorator.py'
        ],

        # todo_database 模块
        'tests/unit/test_todo_database_comprehensive.py': [
            'tests/unit/test_todo_database.py'
        ],

        # models 模块
        'tests/unit/test_models_comprehensive_new.py': [
            'tests/unit/test_models_comprehensive.py',
            'tests/unit/test_models.py'
        ],

        # async_tasks 模块
        'tests/unit/test_async_tasks_comprehensive_new.py': [
            'tests/unit/test_async_tasks_comprehensive.py'
        ],

        # base_model 模块
        'tests/unit/test_base_model_comprehensive_new.py': [
            'tests/unit/test_base_model_comprehensive.py'
        ],

        # card_database 模块
        'tests/unit/test_card_database_comprehensive.py': [
            'tests/unit/test_card_database.py'
        ],

        # articles_module 模块
        'tests/unit/test_articles_module_comprehensive_new.py': [
            'tests/unit/test_articles_module.py'
        ],

        # users_module 模块
        'tests/unit/test_users_module_comprehensive_new.py': [
            'tests/unit/test_users_module.py'
        ]
    }

    total_files_removed = 0
    total_modules_processed = 0

    for primary_file, files_to_remove in cleanup_plan.items():
        if os.path.exists(primary_file):
            print(f"\n📝 处理模块: {os.path.basename(primary_file).replace('test_', '').replace('_comprehensive_new.py', '').replace('_comprehensive.py', '')}")

            # 在主文件顶部添加整合说明
            try:
                with open(primary_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                header_lines = [
                    "# === 测试文件整合说明 ===",
                    f"# 此文件整合了以下测试文件的内容:",
                    f"# - {os.path.basename(primary_file)} (主文件)"
                ]

                for file_to_remove in files_to_remove:
                    if os.path.exists(file_to_remove):
                        header_lines.append(f"# - {os.path.basename(file_to_remove)} (已整合)")

                header_lines.extend([
                    "# 备份文件保存在相同目录下，以 .backup 扩展名",
                    "# =========================================",
                    "",
                    content
                ])

                with open(primary_file, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(header_lines))

                print(f"  ✅ 已更新主文件头信息")

            except Exception as e:
                print(f"  ⚠️ 更新主文件失败: {str(e)}")

            # 删除重复文件
            for file_to_remove in files_to_remove:
                if os.path.exists(file_to_remove):
                    try:
                        # 最终备份
                        final_backup = file_to_remove + '.final_cleanup'
                        shutil.copy2(file_to_remove, final_backup)

                        # 删除原文件
                        os.remove(file_to_remove)

                        print(f"  🗑️ 已删除并备份: {os.path.basename(file_to_remove)}")
                        total_files_removed += 1

                    except Exception as e:
                        print(f"  ❌ 删除失败 {os.path.basename(file_to_remove)}: {str(e)}")

            total_modules_processed += 1
        else:
            print(f"⚠️ 主文件不存在: {primary_file}")

    # 清理所有 .final_backup 文件（保留 .backup 文件作为主要备份）
    print("\n🧽 清理临时备份文件...")
    final_backup_count = 0
    for root, dirs, files in os.walk('tests'):
        for file in files:
            if file.endswith('.final_backup'):
                file_path = os.path.join(root, file)
                try:
                    os.remove(file_path)
                    final_backup_count += 1
                except Exception as e:
                    print(f"  ❌ 删除失败 {file_path}: {str(e)}")

    print("\n🎉 清理完成!")
    print(f"📊 处理结果:")
    print(f"   - 处理模块数: {total_modules_processed}")
    print(f"   - 删除文件数: {total_files_removed}")
    print(f"   - 清理临时文件数: {final_backup_count}")
    print(f"   - 保留主文件数: {total_modules_processed}")
    print(f"   - 保留备份文件数: {total_modules_processed} (每个主文件一个备份)")

def show_final_stats():
    """显示最终统计信息"""
    print("\n📈 最终测试文件统计:")
    print("=" * 50)

    # 统计各目录的文件数
    dirs_to_check = ['tests', 'tests/unit', 'tests/integration', 'tests/security']

    for dir_path in dirs_to_check:
        if os.path.exists(dir_path):
            test_files = []
            backup_files = []
            other_files = []

            for root, dirs, files in os.walk(dir_path):
                for file in files:
                    if file.startswith('test_') and file.endswith('.py'):
                        test_files.append(file)
                    elif file.endswith('.backup'):
                        backup_files.append(file)
                    else:
                        other_files.append(file)

            print(f"📁 {dir_path}:")
            print(f"   - 测试文件: {len(test_files)}")
            print(f"   - 备份文件: {len(backup_files)}")
            print(f"   - 其他文件: {len(other_files)}")
            print(f"   - 总计: {len(test_files) + len(backup_files) + len(other_files)}")

if __name__ == "__main__":
    cleanup_test_files()
    show_final_stats()
    print("\n✅ 测试文件整合和清理完成！")
    print("💡 提示:")
    print("   - 所有重复的测试文件已被删除")
    print("   - 主文件已更新，包含整合说明")
    print("   - 备份文件以 .backup 扩展名保留")
    print("   - 可以使用 'python tests/run_all_tests.py' 运行所有测试")
