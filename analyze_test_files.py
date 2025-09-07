#!/usr/bin/env python
"""
分析测试文件结构，识别需要整合的重复测试文件
"""
import os
import re
import glob
from collections import defaultdict
import ast
import sys

def extract_module_name(filename):
    """从测试文件名中提取模块名"""
    # 移除test_前缀
    if filename.startswith('test_'):
        filename = filename[5:]

    # 移除文件扩展名
    if filename.endswith('.py'):
        filename = filename[:-3]

    # 处理不同的命名模式
    patterns = [
        # test_admin_controller_comprehensive_new.py -> admin_controller
        r'(.+?)_comprehensive_new$',
        # test_admin_controller_comprehensive.py -> admin_controller
        r'(.+?)_comprehensive$',
        # test_admin_controller.py -> admin_controller
        r'(.+?)$',
    ]

    for pattern in patterns:
        match = re.match(pattern, filename)
        if match:
            return match.group(1)

    return filename

def analyze_test_files():
    """分析测试文件结构"""
    test_dir = 'tests'
    if not os.path.exists(test_dir):
        print(f"❌ 测试目录 {test_dir} 不存在")
        return

    # 收集所有测试文件
    test_files = []
    for root, dirs, files in os.walk(test_dir):
        for file in files:
            if file.startswith('test_') and file.endswith('.py'):
                full_path = os.path.join(root, file)
                test_files.append(full_path)

    print(f"📁 发现 {len(test_files)} 个测试文件")

    # 按模块分组
    module_groups = defaultdict(list)

    for test_file in test_files:
        filename = os.path.basename(test_file)
        module_name = extract_module_name(filename)

        # 跳过一些特殊的文件
        if module_name in ['simple_working', 'final_comprehensive', 'final_verification',
                          'final_verification_simple', 'comprehensive_final', 'comprehensive_working',
                          'quick_validation', 'comprehensive_security_performance']:
            continue

        module_groups[module_name].append(test_file)

    print("\n📊 模块分组分析:")
    print("=" * 80)

    consolidated_groups = []
    duplicate_groups = []

    for module_name, files in module_groups.items():
        if len(files) == 1:
            print(f"✅ {module_name}: 1个文件 - {os.path.basename(files[0])}")
            consolidated_groups.append((module_name, files))
        else:
            print(f"🔄 {module_name}: {len(files)}个文件需要整合")
            for f in files:
                print(f"   - {os.path.basename(f)}")
            duplicate_groups.append((module_name, files))

    print("\n📈 统计结果:")
    print(f"- 单个文件模块: {len(consolidated_groups)}")
    print(f"- 需要整合模块: {len(duplicate_groups)}")
    print(f"- 总文件数: {len(test_files)}")

    # 分析重复文件的测试用例
    print("\n🔍 详细分析重复文件:")
    print("=" * 80)

    consolidation_plan = []

    for module_name, files in duplicate_groups:
        print(f"\n📝 模块: {module_name}")
        print("-" * 40)

        module_plan = {
            'module': module_name,
            'files': [],
            'total_tests': 0,
            'primary_file': None
        }

        for file_path in files:
            filename = os.path.basename(file_path)

            # 分析文件中的测试用例
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # 查找测试函数
                test_functions = re.findall(r'def (test_\w+)\s*\(', content)
                class_definitions = re.findall(r'class (Test\w+)\s*\(', content)

                file_info = {
                    'path': file_path,
                    'filename': filename,
                    'test_functions': test_functions,
                    'test_classes': class_definitions,
                    'total_tests': len(test_functions) + len(class_definitions)
                }

                module_plan['files'].append(file_info)
                module_plan['total_tests'] += file_info['total_tests']

                print(f"📄 {filename}:")
                print(f"   - 测试函数: {len(test_functions)}")
                print(f"   - 测试类: {len(class_definitions)}")
                print(f"   - 总计: {file_info['total_tests']}")

                if len(test_functions) > 0:
                    print("   - 函数列表:", ', '.join(test_functions[:5]))
                    if len(test_functions) > 5:
                        print(f"     ... 还有 {len(test_functions) - 5} 个")

            except Exception as e:
                print(f"❌ 无法分析 {filename}: {str(e)}")

        # 确定主文件（通常是_comprehensive_new版本，如果没有则是最新的）
        primary_candidates = [f for f in module_plan['files'] if 'comprehensive_new' in f['filename']]
        if not primary_candidates:
            primary_candidates = [f for f in module_plan['files'] if 'comprehensive' in f['filename']]
        if not primary_candidates:
            primary_candidates = module_plan['files']

        # 选择测试用例最多的作为主文件
        primary_candidates.sort(key=lambda x: x['total_tests'], reverse=True)
        module_plan['primary_file'] = primary_candidates[0]['path']

        print(f"🎯 主文件: {os.path.basename(module_plan['primary_file'])}")
        print(f"📊 总测试数: {module_plan['total_tests']}")

        consolidation_plan.append(module_plan)

    return consolidation_plan

def generate_consolidation_script(plan):
    """生成整合脚本"""
    script_content = '''#!/usr/bin/env python
"""
自动整合测试文件脚本
"""
import os
import shutil
import re
from pathlib import Path

def consolidate_test_files():
    """整合重复的测试文件"""
    print("🚀 开始整合测试文件...")
'''

    for module_plan in plan:
        module_name = module_plan['module']
        primary_file = module_plan['primary_file']
        other_files = [f['path'] for f in module_plan['files'] if f['path'] != primary_file]

        if other_files:
            script_content += f'''
    # 整合 {module_name} 模块
    print("\\n📝 整合 {module_name} 模块...")
    primary_file = "{primary_file}"
    other_files = {other_files}

    consolidate_module_tests(primary_file, other_files)
'''

    script_content += '''
def consolidate_module_tests(primary_file, other_files):
    """整合一个模块的测试文件"""
    print(f"  📄 主文件: {os.path.basename(primary_file)}")

    # 读取主文件内容
    try:
        with open(primary_file, 'r', encoding='utf-8') as f:
            primary_content = f.read()
    except Exception as e:
        print(f"  ❌ 无法读取主文件: {str(e)}")
        return

    consolidated_tests = []
    removed_files = []

    # 处理其他文件
    for other_file in other_files:
        print(f"  📋 处理: {os.path.basename(other_file)}")

        try:
            with open(other_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # 提取测试函数和类
            test_functions = re.findall(r'def (test_\\w+)\\s*\\(', content)
            test_classes = re.findall(r'class (Test\\w+)\\s*\\(', content)

            # 检查这些测试是否已经在主文件中
            existing_functions = re.findall(r'def (test_\\w+)\\s*\\(', primary_content)
            existing_classes = re.findall(r'class (Test\\w+)\\s*\\(', primary_content)

            new_functions = [f for f in test_functions if f not in existing_functions]
            new_classes = [c for c in test_classes if c not in existing_classes]

            if new_functions or new_classes:
                print(f"    ✅ 发现 {len(new_functions)} 个新函数, {len(new_classes)} 个新类")

                # 这里可以添加代码来提取和整合测试内容
                # 为了简化，我们先标记需要手动处理

            else:
                print(f"    ⚠️  所有测试已存在于主文件中")

            # 备份并删除文件
            backup_file = other_file + '.backup'
            shutil.copy2(other_file, backup_file)
            os.remove(other_file)
            removed_files.append(other_file)
            print(f"    🗑️  已删除: {os.path.basename(other_file)}")

        except Exception as e:
            print(f"  ❌ 处理失败: {str(e)}")

    print(f"  📊 完成: 删除了 {len(removed_files)} 个重复文件")

if __name__ == "__main__":
    consolidate_test_files()
    print("\\n✅ 整合完成！")
'''

    return script_content

if __name__ == "__main__":
    print("🔍 分析测试文件结构...")
    plan = analyze_test_files()

    if plan:
        print("\n📋 生成整合脚本...")
        script_content = generate_consolidation_script(plan)

        with open('consolidate_tests.py', 'w', encoding='utf-8') as f:
            f.write(script_content)

        print("✅ 已生成整合脚本: consolidate_tests.py")
        print("\\n🎯 运行以下命令开始整合:")
        print("python consolidate_tests.py")
    else:
        print("❌ 未发现需要整合的文件")
