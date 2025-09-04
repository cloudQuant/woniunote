#!/usr/bin/env python3
"""
WoniuNote 测试优化项目 - 最终测试报告生成器
"""

import subprocess
import sys
import os
import json
from datetime import datetime

def run_test_command(command, description):
    """运行测试命令并返回结果"""
    print(f"\n{'='*80}")
    print(f"执行: {description}")
    print(f"命令: {command}")
    print('='*80)

    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=120)
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "测试超时"
    except Exception as e:
        return False, "", str(e)

def parse_test_results(output):
    """解析pytest输出结果"""
    results = {
        'passed': 0,
        'failed': 0,
        'skipped': 0,
        'errors': 0,
        'total': 0
    }

    if not output:
        return results

    lines = output.split('\n')
    for line in lines:
        line = line.strip()

        # 查找类似 "42 passed, 0 failed, 0 skipped in 4.49s" 的行
        if 'passed' in line and 'failed' in line and 'skipped' in line and 'in' in line:
            try:
                # 移除时间部分
                line = line.split(' in ')[0]
                parts = line.split(',')
                for part in parts:
                    part = part.strip()
                    if 'passed' in part:
                        results['passed'] = int(part.split()[0])
                    elif 'failed' in part:
                        results['failed'] = int(part.split()[0])
                    elif 'skipped' in part:
                        results['skipped'] = int(part.split()[0])
            except Exception as e:
                print(f"解析行失败: {line}, 错误: {e}")
                pass

        # 查找单独的统计行
        elif line.startswith('======') and ('passed' in line or 'failed' in line):
            continue
        elif 'passed' in line and ',' not in line:
            try:
                parts = line.split()
                if len(parts) >= 2 and parts[1] == 'passed':
                    results['passed'] = int(parts[0])
                    results['total'] = int(parts[0])
            except:
                pass
        elif 'failed' in line and ',' not in line:
            try:
                parts = line.split()
                if len(parts) >= 2 and parts[1] == 'failed':
                    results['failed'] = int(parts[0])
            except:
                pass
        elif 'skipped' in line and ',' not in line:
            try:
                parts = line.split()
                if len(parts) >= 2 and parts[1] == 'skipped':
                    results['skipped'] = int(parts[0])
            except:
                pass

    results['total'] = results['passed'] + results['failed'] + results['skipped'] + results['errors']
    return results

def main():
    """主函数"""
    os.chdir('/Users/yunjinqi/Documents/woniunote')

    print("🎯 WoniuNote 测试优化项目 - 最终测试报告")
    print("="*80)
    print(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # 测试各个控制器
    test_suites = [
        ("python -m pytest tests/unit/test_user_controller_comprehensive.py --tb=no -q", "用户控制器"),
        ("python -m pytest tests/unit/test_comment_controller_comprehensive.py --tb=no -q", "评论控制器"),
        ("python -m pytest tests/unit/test_index_controller_comprehensive.py --tb=no -q", "索引控制器"),
        ("python -m pytest tests/unit/test_admin_controller_comprehensive.py --tb=no -q", "管理控制器"),
        ("python -m pytest tests/unit/test_article_controller_comprehensive.py --tb=no -q", "文章控制器"),
    ]

    total_results = {
        'passed': 0,
        'failed': 0,
        'skipped': 0,
        'errors': 0,
        'total': 0
    }

    suite_results = {}

    for command, name in test_suites:
        success, stdout, stderr = run_test_command(command, f"{name}测试")
        results = parse_test_results(stdout)

        suite_results[name] = results

        total_results['passed'] += results['passed']
        total_results['failed'] += results['failed']
        total_results['skipped'] += results['skipped']
        total_results['errors'] += results['errors']

        print(f"📊 {name}结果: {results['passed']} 通过, {results['failed']} 失败, {results['skipped']} 跳过")

    total_results['total'] = total_results['passed'] + total_results['failed'] + total_results['skipped'] + total_results['errors']

    # 计算通过率
    if total_results['total'] > 0:
        pass_rate = (total_results['passed'] / total_results['total']) * 100
        fail_rate = (total_results['failed'] / total_results['total']) * 100
        skip_rate = (total_results['skipped'] / total_results['total']) * 100
    else:
        pass_rate = fail_rate = skip_rate = 0

    print("\n" + "="*80)
    print("📈 最终测试统计报告")
    print("="*80)
    print(f"🎯 总测试数量: {total_results['total']}")
    print(f"✅ 通过测试: {total_results['passed']} ({pass_rate:.1f}%)")
    print(f"❌ 失败测试: {total_results['failed']} ({fail_rate:.1f}%)")
    print(f"⏭️  跳过测试: {total_results['skipped']} ({skip_rate:.1f}%)")
    print(f"🔧 错误测试: {total_results['errors']}")

    print("\n📋 各控制器详细结果:")
    for name, results in suite_results.items():
        if results['total'] > 0:
            rate = (results['passed'] / results['total']) * 100
            status = "✅" if results['failed'] == 0 else "⚠️" if results['failed'] < 5 else "❌"
            print(f"  {status} {name}: {results['passed']}/{results['total']} ({rate:.1f}%)")

    print("\n" + "="*80)
    if total_results['failed'] == 0 and total_results['skipped'] == 0:
        print("🎉 恭喜！所有测试均通过！")
        print("🏆 项目目标达成：测试通过率 100%，无跳过测试")
    elif total_results['failed'] == 0 and total_results['skipped'] <= 2:
        print("🎊 优秀！测试通过率达标，只有少量跳过测试")
        print("🎯 项目目标基本达成")
    elif pass_rate >= 95:
        print("👍 良好！测试通过率很高")
        print("🔧 还有少量问题需要解决")
    else:
        print("⚠️ 需要进一步优化")
        print("🔧 建议继续修复失败的测试")

    print("="*80)

    # 生成JSON报告
    report_data = {
        'timestamp': datetime.now().isoformat(),
        'total_results': total_results,
        'suite_results': suite_results,
        'pass_rate': pass_rate,
        'status': 'success' if total_results['failed'] == 0 and total_results['skipped'] == 0 else 'partial' if pass_rate >= 95 else 'needs_work'
    }

    with open('test_final_report.json', 'w', encoding='utf-8') as f:
        json.dump(report_data, f, ensure_ascii=False, indent=2)

    print("📄 详细报告已保存到: test_final_report.json")

    return 0 if total_results['failed'] == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
