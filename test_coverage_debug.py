#!/usr/bin/env python
"""
调试覆盖率收集机制
"""
import sys
import os
import subprocess

def test_coverage_mechanism():
    """测试覆盖率收集机制"""
    print("=== 调试覆盖率收集机制 ===\n")

    # 1. 检查 .coverage 文件是否存在
    coverage_file = os.path.join(os.getcwd(), '.coverage')
    print(f"1. 检查覆盖率文件: {coverage_file}")
    if os.path.exists(coverage_file):
        print("   ✅ .coverage 文件存在")
        file_size = os.path.getsize(coverage_file)
        print(f"   📊 文件大小: {file_size} bytes")
    else:
        print("   ❌ .coverage 文件不存在")

    # 2. 尝试手动运行 pytest-cov
    print("\n2. 测试 pytest-cov 命令...")
    try:
        cmd = [
            sys.executable, '-m', 'pytest',
            'tests/test_simple_working.py',  # 只运行一个简单测试
            '--cov=woniunote',
            '--cov-report=term',
            '-v'
        ]

        print(f"执行命令: {' '.join(cmd)}")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
            cwd=os.getcwd()
        )

        print(f"返回码: {result.returncode}")
        if result.returncode == 0:
            print("✅ pytest-cov 执行成功")
        else:
            print("❌ pytest-cov 执行失败")
            print("STDOUT:", result.stdout[-500:])  # 只显示最后500字符
            print("STDERR:", result.stderr[-500:])  # 只显示最后500字符

    except subprocess.TimeoutExpired:
        print("⏰ pytest-cov 执行超时")
    except Exception as e:
        print(f"❌ pytest-cov 执行出错: {str(e)}")

    # 3. 检查覆盖率文件是否生成
    print("\n3. 检查覆盖率文件是否生成...")
    if os.path.exists(coverage_file):
        new_size = os.path.getsize(coverage_file)
        print(f"   ✅ .coverage 文件存在，大小: {new_size} bytes")
    else:
        print("   ❌ .coverage 文件仍不存在")

    # 4. 尝试读取覆盖率数据
    print("\n4. 尝试读取覆盖率数据...")
    try:
        import coverage
        cov = coverage.Coverage(data_file=coverage_file)
        cov.load()

        print("✅ 覆盖率数据加载成功")

        # 显示基本信息
        measured_files = list(cov._data.measured_files())
        print(f"📁 测量文件数: {len(measured_files)}")

        woniunote_files = [f for f in measured_files if 'woniunote' in f]
        print(f"🏠 WoniuNote 文件数: {len(woniunote_files)}")

        if woniunote_files:
            print("\n🎯 前5个文件的覆盖率:")
            for i, filename in enumerate(woniunote_files[:5]):
                print(f"  {i+1}. {os.path.basename(filename)}")

    except Exception as e:
        print(f"❌ 读取覆盖率数据失败: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_coverage_mechanism()
