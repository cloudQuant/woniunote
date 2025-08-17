#!/usr/bin/env python3
"""
WoniuNote 综合测试运行器
运行所有综合测试并生成报告
"""
import sys
import os
import subprocess
import time
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def run_test_file(test_file, timeout=120):
    """运行单个测试文件"""
    print(f"\n{'='*60}")
    print(f"Running: {test_file}")
    print(f"{'='*60}")
    
    start_time = time.time()
    
    try:
        result = subprocess.run(
            [sys.executable, '-m', 'pytest', f'tests/{test_file}', '-v', '--tb=short'],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        duration = time.time() - start_time
        
        if result.returncode == 0:
            status = "✅ PASSED"
        else:
            status = "❌ FAILED"
        
        print(f"{status} ({duration:.1f}s)")
        
        # 显示输出摘要
        if result.stdout:
            lines = result.stdout.split('\n')
            # 查找测试结果摘要
            for line in lines:
                if 'passed' in line or 'failed' in line or 'error' in line:
                    if '::' not in line and ('passed' in line or 'failed' in line):
                        print(f"  {line.strip()}")
        
        if result.returncode != 0 and result.stderr:
            # 显示错误的简要信息
            error_lines = result.stderr.split('\n')[:5]
            print("  Error preview:")
            for line in error_lines:
                if line.strip():
                    print(f"    {line.strip()}")
        
        return {
            'file': test_file,
            'status': 'passed' if result.returncode == 0 else 'failed',
            'duration': duration,
            'returncode': result.returncode,
            'stdout': result.stdout,
            'stderr': result.stderr
        }
        
    except subprocess.TimeoutExpired:
        duration = timeout
        print(f"⏰ TIMEOUT ({duration}s)")
        return {
            'file': test_file,
            'status': 'timeout',
            'duration': duration,
            'returncode': -1,
            'stdout': '',
            'stderr': 'Test timed out'
        }
    except Exception as e:
        duration = time.time() - start_time
        print(f"💥 ERROR: {e}")
        return {
            'file': test_file,
            'status': 'error',
            'duration': duration,
            'returncode': -2,
            'stdout': '',
            'stderr': str(e)
        }

def main():
    """主函数"""
    print("WoniuNote 综合测试运行器")
    print("=" * 50)
    
    # 综合测试文件列表
    comprehensive_tests = [
        'test_core_utils_comprehensive.py',
        'test_logging_comprehensive.py', 
        'test_database_models_comprehensive.py',
        'test_controllers_comprehensive.py',
        'test_security_comprehensive.py',
        'test_performance_comprehensive.py',
    ]
    
    # 检查测试文件是否存在
    existing_tests = []
    missing_tests = []
    
    for test_file in comprehensive_tests:
        test_path = project_root / 'tests' / test_file
        if test_path.exists():
            existing_tests.append(test_file)
        else:
            missing_tests.append(test_file)
    
    print(f"发现 {len(existing_tests)} 个综合测试文件")
    if missing_tests:
        print(f"缺失 {len(missing_tests)} 个测试文件: {missing_tests}")
    
    # 运行测试
    results = []
    total_start_time = time.time()
    
    for test_file in existing_tests:
        result = run_test_file(test_file)
        results.append(result)
    
    total_duration = time.time() - total_start_time
    
    # 生成报告
    print(f"\n{'='*60}")
    print("测试结果摘要")
    print(f"{'='*60}")
    
    passed_count = sum(1 for r in results if r['status'] == 'passed')
    failed_count = sum(1 for r in results if r['status'] == 'failed')
    timeout_count = sum(1 for r in results if r['status'] == 'timeout')
    error_count = sum(1 for r in results if r['status'] == 'error')
    
    print(f"总计: {len(results)} 个测试文件")
    print(f"✅ 通过: {passed_count}")
    print(f"❌ 失败: {failed_count}")
    print(f"⏰ 超时: {timeout_count}")
    print(f"💥 错误: {error_count}")
    print(f"⏱️ 总时间: {total_duration:.1f}s")
    
    success_rate = passed_count / len(results) * 100 if results else 0
    print(f"📊 成功率: {success_rate:.1f}%")
    
    # 详细结果
    print(f"\n详细结果:")
    for result in results:
        status_icon = {
            'passed': '✅',
            'failed': '❌', 
            'timeout': '⏰',
            'error': '💥'
        }.get(result['status'], '❓')
        
        print(f"  {status_icon} {result['file']} ({result['duration']:.1f}s)")
    
    # 失败的测试详情
    failed_tests = [r for r in results if r['status'] != 'passed']
    if failed_tests:
        print(f"\n失败测试详情:")
        for result in failed_tests:
            print(f"\n📁 {result['file']}:")
            if result['stderr']:
                # 显示错误的关键信息
                stderr_lines = result['stderr'].split('\n')
                key_errors = []
                for line in stderr_lines:
                    if any(keyword in line.lower() for keyword in ['error', 'failed', 'assert', 'exception']):
                        key_errors.append(line.strip())
                
                for error in key_errors[:3]:  # 只显示前3个关键错误
                    print(f"    {error}")
    
    print(f"\n{'='*60}")
    
    # 生成简要报告文件
    report_file = project_root / 'test_comprehensive_report.txt'
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("WoniuNote 综合测试报告\n")
        f.write("=" * 30 + "\n\n")
        f.write(f"测试时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"总测试文件: {len(results)}\n")
        f.write(f"通过: {passed_count}\n")
        f.write(f"失败: {failed_count}\n")
        f.write(f"成功率: {success_rate:.1f}%\n\n")
        
        f.write("详细结果:\n")
        for result in results:
            f.write(f"  {result['status'].upper()} - {result['file']} ({result['duration']:.1f}s)\n")
    
    print(f"报告已保存到: {report_file}")
    
    # 返回成功率
    return success_rate >= 80  # 80%以上认为成功

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)