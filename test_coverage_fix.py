#!/usr/bin/env python
"""
测试覆盖率计算修复效果
"""

import os
import sys
import subprocess

def test_coverage_fix():
    """测试覆盖率计算是否修复"""
    project_root = "/Users/yunjinqi/Documents/woniunote"
    os.chdir(project_root)

    print("🔍 测试覆盖率计算修复效果...")
    print("=" * 60)

    # 测试1: 运行单个测试文件并检查覆盖率
    print("\n📊 测试1: 运行单个测试文件检查覆盖率")
    result = subprocess.run([
        sys.executable, '-m', 'pytest',
        'tests/unit/test_app_comprehensive.py',
        '--cov=woniunote.app',
        '--cov-report=term',
        '-v'
    ], capture_output=True, text=True)

    print("测试输出:")
    print(result.stdout)
    if result.stderr:
        print("错误输出:")
        print(result.stderr)

    print(f"返回码: {result.returncode}")

    # 测试2: 检查覆盖率数据文件是否存在
    print("\n📁 测试2: 检查覆盖率数据文件")
    coverage_files = [
        '.coverage',
        'htmlcov/index.html'
    ]

    for file_path in coverage_files:
        if os.path.exists(file_path):
            print(f"✅ {file_path} 存在")
        else:
            print(f"❌ {file_path} 不存在")

    # 测试3: 手动导入模块并检查覆盖率
    print("\n🔧 测试3: 手动导入模块测试覆盖率收集")
    try:
        import coverage
        cov = coverage.Coverage(source=["woniunote"])
        cov.start()

        # 导入一些模块
        import woniunote.app
        import woniunote.common.async_tasks

        cov.stop()
        cov.save()

        print("覆盖率报告:")
        cov.report()
        print("✅ 手动覆盖率收集成功")

    except Exception as e:
        print(f"❌ 手动覆盖率收集失败: {e}")

    print("\n" + "=" * 60)
    print("🎯 覆盖率计算修复测试完成")

if __name__ == "__main__":
    test_coverage_fix()
