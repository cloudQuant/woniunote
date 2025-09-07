#!/usr/bin/env python
"""
测试 run_all_tests.py 的修复效果
"""
import sys
import os
import subprocess

def test_run_all_tests_with_continue_on_error():
    """测试 --continue-on-error 参数"""
    print("=== 测试 --continue-on-error 参数 ===")

    cmd = [sys.executable, "tests/run_all_tests.py", "--continue-on-error", "--fast"]

    print(f"执行命令: {' '.join(cmd)}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=False,
            text=True,
            timeout=120,  # 2分钟超时
            cwd=os.getcwd()
        )

        print(f"\n返回码: {result.returncode}")

        if result.returncode == 0:
            print("✅ 测试成功完成")
        else:
            print("⚠️ 测试完成但有非零返回码")

    except subprocess.TimeoutExpired:
        print("⏰ 测试超时")
    except Exception as e:
        print(f"❌ 测试执行失败: {e}")

def test_run_all_tests_help():
    """测试帮助信息"""
    print("\n=== 测试帮助信息 ===")

    cmd = [sys.executable, "tests/run_all_tests.py", "--help"]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=os.getcwd()
        )

        print("帮助信息:")
        print(result.stdout)

    except Exception as e:
        print(f"❌ 获取帮助信息失败: {e}")

if __name__ == "__main__":
    print("开始测试 run_all_tests.py 修复效果...\n")

    test_run_all_tests_help()
    test_run_all_tests_with_continue_on_error()

    print("\n=== 测试完成 ===")
