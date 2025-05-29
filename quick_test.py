#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
超快速测试运行器
- 3秒超时设置
- 跳过所有浏览器和慢速测试
- 最小化日志输出
- 快速失败
"""

import os
import sys
import time
import subprocess
import argparse
import multiprocessing

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='超快速测试运行器')
    parser.add_argument('test_path', nargs='?', default='tests/test_basic_app.py', 
                       help='测试文件或目录，默认只运行基础测试')
    parser.add_argument('--all', action='store_true', help='运行所有非浏览器测试')
    parser.add_argument('--workers', '-n', type=int, 
                       default=min(6, multiprocessing.cpu_count()),
                       help='并行worker数量，默认6个')
    parser.add_argument('--timeout', '-t', type=int, default=3, help='超时时间（秒），默认3秒')
    parser.add_argument('--verbose', '-v', action='store_true', help='详细输出')
    
    return parser.parse_args()

def main():
    """主函数"""
    args = parse_args()
    
    # 设置环境变量
    os.environ['PYTEST_FAST_MODE'] = '1'
    os.environ['SKIP_DB_INIT'] = '1'
    os.environ['DISABLE_LOGGING'] = '1'
    os.environ['PYTEST_TIMEOUT'] = str(args.timeout)
    
    # 确定测试路径
    if args.all:
        test_path = 'tests/'
    else:
        test_path = args.test_path
    
    # 构建pytest命令
    cmd = [sys.executable, '-m', 'pytest']
    
    # 超快速配置
    cmd.extend([
        test_path,
        '-x',                           # 快速失败
        '--tb=no',                      # 不显示回溯信息
        '--disable-warnings',           # 禁用所有警告
        '--maxfail=1',                  # 1个失败就停止
        '--timeout=' + str(args.timeout),  # 设置超时
        '-m', 'not browser and not slow and not functional',  # 跳过浏览器、慢速和功能测试
        '--durations=3',                # 只显示最慢的3个
    ])
    
    # 并行执行（单元测试适合并行）
    if args.workers > 1:
        cmd.extend(['-n', str(args.workers)])
        cmd.append('--dist=loadfile')
    
    # 输出控制
    if args.verbose:
        cmd.append('-v')
    else:
        cmd.append('-q')
    
    # 禁用多余插件
    cmd.extend([
        '-p', 'no:warnings',
        '-p', 'no:cacheprovider',
        '-p', 'no:randomly',
    ])
    
    print(f"⚡ 超快速测试运行器")
    print(f"📁 测试路径: {test_path}")
    print(f"⏰ 超时设置: {args.timeout}秒")
    print(f"🔧 并行度: {args.workers} workers")
    print(f"⏱️  开始时间: {time.strftime('%H:%M:%S')}")
    print("=" * 40)
    
    # 记录开始时间
    start_time = time.time()
    
    try:
        # 运行pytest
        result = subprocess.run(cmd, cwd=os.getcwd())
        
        # 计算耗时
        duration = time.time() - start_time
        
        print("=" * 40)
        print(f"⏱️  结束时间: {time.strftime('%H:%M:%S')}")
        print(f"🎯 总耗时: {duration:.2f}秒")
        
        if result.returncode == 0:
            print("✅ 所有测试通过!")
        else:
            print("❌ 测试失败!")
            print("💡 提示: 使用 -v 参数查看详细信息")
        
        return result.returncode
        
    except KeyboardInterrupt:
        print("\n❌ 测试被用户中断")
        return 1
    except Exception as e:
        print(f"❌ 运行测试时出错: {e}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 