#!/usr/bin/env python3
"""
测试验证脚本
运行各个测试套件并统计结果
"""

import subprocess
import sys
import os

def run_test_command(command, description):
    """运行测试命令并返回结果"""
    print(f"\n{'='*60}")
    print(f"运行: {description}")
    print(f"命令: {command}")
    print('='*60)

    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=300)
        print(f"退出码: {result.returncode}")
        if result.stdout:
            print("标准输出:")
            print(result.stdout[-1000:])  # 只显示最后1000字符
        if result.stderr:
            print("标准错误:")
            print(result.stderr[-1000:])  # 只显示最后1000字符
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        print("测试超时")
        return False, "", "Timeout"
    except Exception as e:
        print(f"执行失败: {e}")
        return False, "", str(e)

def main():
    """主函数"""
    os.chdir('/Users/yunjinqi/Documents/woniunote')

    test_commands = [
        ("python -m pytest tests/unit/test_user_controller_comprehensive.py --tb=no -q", "用户控制器测试"),
        ("python -m pytest tests/unit/test_comment_controller_comprehensive.py --tb=no -q", "评论控制器测试"),
        ("python -m pytest tests/unit/test_index_controller_comprehensive.py --tb=no -q", "索引控制器测试"),
        ("python -m pytest tests/unit/test_article_controller_comprehensive.py --tb=no -q", "文章控制器测试"),
    ]

    total_passed = 0
    total_failed = 0
    total_skipped = 0

    for command, description in test_commands:
        success, stdout, stderr = run_test_command(command, description)

        # 解析测试结果
        if stdout:
            lines = stdout.split('\n')
            for line in lines:
                if 'passed' in line and 'failed' in line and 'skipped' in line:
                    try:
                        parts = line.split(',')
                        passed = int(parts[0].split()[0])
                        failed = int(parts[1].split()[0])
                        skipped = int(parts[2].split()[0]) if len(parts) > 2 else 0

                        total_passed += passed
                        total_failed += failed
                        total_skipped += skipped

                        print(f"解析结果: {passed} 通过, {failed} 失败, {skipped} 跳过")
                    except:
                        pass

    print(f"\n{'='*60}")
    print("总计结果:")
    print(f"通过: {total_passed}")
    print(f"失败: {total_failed}")
    print(f"跳过: {total_skipped}")
    print(f"总计: {total_passed + total_failed + total_skipped}")

    if total_failed == 0 and total_skipped == 0:
        print("🎉 所有测试通过！")
        return 0
    else:
        print(f"⚠️ 仍有 {total_failed} 个失败和 {total_skipped} 个跳过的测试")
        return 1

if __name__ == "__main__":
    sys.exit(main())
