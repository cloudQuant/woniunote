#!/usr/bin/env python
"""
分析剩余的测试文件，识别需要进一步整合的文件
"""
import os
import re
from collections import defaultdict

def extract_module_name(filename):
    """从测试文件名中提取模块名"""
    if filename.startswith('test_'):
        filename = filename[5:]

    if filename.endswith('.py'):
        filename = filename[:-3]

    # 处理不同的命名模式
    patterns = [
        r'(.+?)_comprehensive_new$',
        r'(.+?)_comprehensive$',
        r'(.+?)_module$',
        r'(.+?)_factory$',
        r'(.+?)$',
    ]

    for pattern in patterns:
        match = re.match(pattern, filename)
        if match:
            return match.group(1)

    return filename

def analyze_remaining_files():
    """分析剩余的测试文件"""
    print("🔍 分析剩余的测试文件...")

    # 获取所有测试文件
    test_files = []
    for root, dirs, files in os.walk('tests'):
        for file in files:
            if file.startswith('test_') and file.endswith('.py') and not file.endswith('.backup'):
                full_path = os.path.join(root, file)
                test_files.append(full_path)

    print(f"📁 发现 {len(test_files)} 个测试文件")

    # 按模块分组
    module_groups = defaultdict(list)

    for test_file in test_files:
        filename = os.path.basename(test_file)
        module_name = extract_module_name(filename)
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
                try:
                    # 分析文件大小
                    size = os.path.getsize(f)
                    print(f"   - {os.path.basename(f)} ({size} bytes)")
                except:
                    print(f"   - {os.path.basename(f)}")
            duplicate_groups.append((module_name, files))

    print("\n📈 统计结果:")
    print(f"- 单个文件模块: {len(consolidated_groups)}")
    print(f"- 需要整合模块: {len(duplicate_groups)}")
    print(f"- 总文件数: {len(test_files)}")

    if duplicate_groups:
        print("\n🔍 需要整合的模块详细分析:")
        print("=" * 80)

        for module_name, files in duplicate_groups:
            print(f"\n📝 模块: {module_name}")
            print("-" * 40)

            for file_path in files:
                filename = os.path.basename(file_path)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # 查找测试函数
                    test_functions = re.findall(r'def (test_\w+)\s*\(', content)
                    test_classes = re.findall(r'class (Test\w+)\s*\(', content)

                    print(f"📄 {filename}:")
                    print(f"   - 测试函数: {len(test_functions)}")
                    print(f"   - 测试类: {len(test_classes)}")
                    print(f"   - 总计: {len(test_functions) + len(test_classes)}")

                except Exception as e:
                    print(f"❌ 无法分析 {filename}: {str(e)}")

    return duplicate_groups

if __name__ == "__main__":
    duplicates = analyze_remaining_files()

    if duplicates:
        print("\n📋 发现需要整合的模块:")
        for module_name, files in duplicates:
            print(f"- {module_name}: {len(files)}个文件")
    else:
        print("\n✅ 未发现需要整合的文件")
