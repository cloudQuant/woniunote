#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
WoniuNote 终极测试运行器
支持多种运行模式，解决超时问题
"""

import os
import sys
import time
import subprocess
import argparse
import multiprocessing
import shutil
from pathlib import Path

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='WoniuNote 终极测试运行器')
    
    # 基本参数
    parser.add_argument('test_path', nargs='?', default='tests/test_basic_app.py', 
                       help='测试文件或目录')
    
    # 运行模式
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument('--fast', action='store_true', 
                           help='极速模式：只运行单元测试，跳过所有浏览器测试')
    mode_group.add_argument('--fixed-timeout', action='store_true',
                           help='超时修复模式：运行所有测试但设置3秒超时')
    mode_group.add_argument('--unit-only', action='store_true',
                           help='单元测试模式：只运行标记为unit的测试')
    
    # 性能参数
    parser.add_argument('--workers', '-n', type=int, 
                       default=min(6, multiprocessing.cpu_count()),
                       help='并行worker数量')
    parser.add_argument('--timeout', '-t', type=int, default=3, 
                       help='超时时间（秒）')
    
    # 输出控制
    parser.add_argument('--verbose', '-v', action='store_true', help='详细输出')
    parser.add_argument('--quiet', '-q', action='store_true', help='静默输出')
    parser.add_argument('--fail-fast', '-x', action='store_true', help='快速失败')
    
    return parser.parse_args()

def backup_and_replace_conftest(mode):
    """备份并替换conftest.py"""
    conftest_original = Path('tests/conftest.py')
    conftest_backup = Path('tests/conftest.py.original')
    
    # 备份原始文件（如果还没有备份）
    if conftest_original.exists() and not conftest_backup.exists():
        shutil.copy2(conftest_original, conftest_backup)
        print(f"✅ 已备份原始conftest.py")
    
    if mode == 'fixed-timeout':
        # 使用修复超时的配置
        conftest_fixed = Path('tests/conftest_timeout_fix.py')
        if conftest_fixed.exists():
            shutil.copy2(conftest_fixed, conftest_original)
            print(f"✅ 已应用超时修复配置")
            return True
    
    return False

def restore_conftest():
    """恢复原始conftest.py"""
    conftest_original = Path('tests/conftest.py')
    conftest_backup = Path('tests/conftest.py.original')
    
    if conftest_backup.exists():
        shutil.copy2(conftest_backup, conftest_original)
        print(f"✅ 已恢复原始conftest.py")

def build_pytest_command(args):
    """构建pytest命令"""
    cmd = [sys.executable, '-m', 'pytest']
    
    # 添加测试路径
    cmd.append(args.test_path)
    
    # 基本优化参数
    cmd.extend([
        '--tb=short',
        '--disable-warnings',
        f'--timeout={args.timeout}',
        '--durations=5',
    ])
    
    # 运行模式配置
    if args.fast:
        print(f"🚀 运行模式: 极速模式")
        cmd.extend([
            '-m', 'not browser and not slow and not functional',
            '--maxfail=1',
            '-x'
        ])
        # 设置快速模式环境变量
        os.environ['PYTEST_FAST_MODE'] = '1'
        os.environ['SKIP_DB_INIT'] = '1'
        
    elif args.fixed_timeout:
        print(f"🔧 运行模式: 超时修复模式")
        cmd.extend([
            '--maxfail=3',
        ])
        # 设置快速模式环境变量（以跳过复杂的浏览器测试）
        os.environ['PYTEST_FAST_MODE'] = '1'
        
    elif args.unit_only:
        print(f"🎯 运行模式: 单元测试模式")
        cmd.extend([
            '-m', 'unit',
            '--maxfail=3'
        ])
        
    else:
        print(f"📊 运行模式: 标准模式")
        cmd.extend([
            '--maxfail=5'
        ])
    
    # 并行执行
    if args.workers > 1:
        cmd.extend(['-n', str(args.workers)])
        cmd.append('--dist=loadfile')
    
    # 输出控制
    if args.verbose:
        cmd.append('-v')
    elif args.quiet:
        cmd.append('-q')
    else:
        cmd.append('-q')  # 默认静默
    
    # 快速失败
    if args.fail_fast:
        cmd.append('-x')
    
    # 禁用插件以提高速度
    cmd.extend([
        '-p', 'no:cacheprovider',
    ])
    
    return cmd

def main():
    """主函数"""
    args = parse_args()
    conftest_modified = False
    
    try:
        # 设置环境变量
        os.environ['PYTHONDONTWRITEBYTECODE'] = '1'  # 不生成.pyc文件
        
        # 处理conftest.py
        if args.fixed_timeout:
            conftest_modified = backup_and_replace_conftest('fixed-timeout')
        
        # 构建命令
        cmd = build_pytest_command(args)
        
        # 显示信息
        print(f"🧪 WoniuNote 测试运行器")
        print(f"📁 测试路径: {args.test_path}")
        print(f"⏰ 超时设置: {args.timeout}秒")
        print(f"🔧 并行度: {args.workers} workers")
        print(f"⏱️  开始时间: {time.strftime('%H:%M:%S')}")
        if args.verbose:
            print(f"🔧 命令: {' '.join(cmd)}")
        print("=" * 50)
        
        # 记录开始时间
        start_time = time.time()
        
        # 运行pytest
        result = subprocess.run(cmd, cwd=os.getcwd())
        
        # 计算耗时
        duration = time.time() - start_time
        
        print("=" * 50)
        print(f"⏱️  结束时间: {time.strftime('%H:%M:%S')}")
        print(f"🎯 总耗时: {duration:.2f}秒")
        
        if result.returncode == 0:
            print("✅ 所有测试通过!")
        else:
            print("❌ 有测试失败!")
            if not args.verbose:
                print("💡 使用 -v 参数查看详细信息")
        
        return result.returncode
        
    except KeyboardInterrupt:
        print("\n❌ 测试被用户中断")
        return 1
    except Exception as e:
        print(f"❌ 运行测试时出错: {e}")
        return 1
    finally:
        # 恢复conftest.py
        if conftest_modified:
            restore_conftest()
        
        # 清理环境变量
        for env_var in ['PYTEST_FAST_MODE', 'SKIP_DB_INIT']:
            if env_var in os.environ:
                del os.environ[env_var]

def show_usage_examples():
    """显示使用示例"""
    examples = """
🎯 使用示例:

# 极速模式 - 只运行单元测试，最快
python test_runner.py --fast

# 超时修复模式 - 运行所有测试但设置3秒超时
python test_runner.py --fixed-timeout

# 单元测试模式 - 只运行unit标记的测试
python test_runner.py --unit-only

# 运行特定文件
python test_runner.py tests/test_basic_app.py --fast

# 详细输出
python test_runner.py --fast --verbose

# 自定义并行度和超时
python test_runner.py --fast --workers 8 --timeout 5
"""
    print(examples)

if __name__ == "__main__":
    if len(sys.argv) == 1:
        show_usage_examples()
    
    exit_code = main()
    sys.exit(exit_code) 