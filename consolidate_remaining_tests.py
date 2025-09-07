#!/usr/bin/env python
"""
整合剩余的重复测试文件
"""
import os
import shutil
from pathlib import Path

def consolidate_remaining_tests():
    """整合剩余的重复测试文件"""
    print("🧹 开始整合剩余的测试文件...")

    # 定义需要整合的模块
    consolidation_plan = {
        # performance_enhanced 模块
        'tests/unit/test_performance_enhanced_comprehensive_new.py': [
            'tests/unit/test_performance_enhanced_module.py'
        ],

        # rate_limiter 模块
        'tests/unit/test_rate_limiter_comprehensive_new.py': [
            'tests/unit/test_rate_limiter_module.py'
        ],

        # app 模块
        'tests/unit/test_app_comprehensive_new.py': [
            'tests/unit/test_app_factory.py',
            'tests/unit/test_app_module.py'
        ],

        # user_experience_optimizer 模块
        'tests/unit/test_user_experience_optimizer_module.py': [
            'tests/unit/test_user_experience_optimizer.py'
        ],

        # async_tasks 模块
        'tests/unit/test_async_tasks_comprehensive_new.py': [
            'tests/unit/test_async_tasks_module.py'
        ]
    }

    total_files_removed = 0
    total_modules_processed = 0

    for primary_file, files_to_remove in consolidation_plan.items():
        if os.path.exists(primary_file):
            module_name = os.path.basename(primary_file).replace('test_', '').replace('_comprehensive_new.py', '').replace('_module.py', '').replace('.py', '')
            print(f"\n📝 整合 {module_name} 模块...")
            print(f"  📄 主文件: {os.path.basename(primary_file)}")

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

                print("  ✅ 已更新主文件头信息")
            except Exception as e:
                print(f"  ⚠️ 更新主文件失败: {str(e)}")

            # 删除重复文件
            for file_to_remove in files_to_remove:
                if os.path.exists(file_to_remove):
                    try:
                        # 创建最终备份
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

    # 清理所有 .final_cleanup 文件
    print("\n🧽 清理临时备份文件...")
    final_cleanup_count = 0
    for root, dirs, files in os.walk('tests'):
        for file in files:
            if file.endswith('.final_cleanup'):
                file_path = os.path.join(root, file)
                try:
                    os.remove(file_path)
                    final_cleanup_count += 1
                except Exception as e:
                    print(f"  ❌ 删除失败 {file_path}: {str(e)}")

    print("\n🎉 整合完成!")
    print("📊 处理结果:")
    print(f"   - 处理模块数: {total_modules_processed}")
    print(f"   - 删除文件数: {total_files_removed}")
    print(f"   - 清理临时文件数: {final_cleanup_count}")
    print(f"   - 保留主文件数: {total_modules_processed}")

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
    consolidate_remaining_tests()
    show_final_stats()
    print("\n✅ 剩余测试文件整合完成！")
    print("💡 提示:")
    print("   - 删除了剩余的重复测试文件")
    print("   - 主文件已更新，包含整合说明")
    print("   - 备份文件以 .backup 扩展名保留")
    print("   - 测试文件结构更加清晰")
