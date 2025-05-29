#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
简单快速测试脚本
直接使用优化的pytest参数，无需修改配置文件
"""

import os
import sys
import time
import subprocess
import argparse
import multiprocessing

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='快速运行测试')
    parser.add_argument('test_path', nargs='?', default='tests/test_basic_app.py', 
                       help='测试文件或目录')
    parser.add_argument('--workers', '-n', type=int, 
                       default=min(4, multiprocessing.cpu_count()),
                       help='并行worker数量')
    parser.add_argument('--unit-only', action='store_true', help='只运行单元测试')
    parser.add_argument('--verbose', '-v', action='store_true', help='详细输出')
    parser.add_argument('--quiet', '-q', action='store_true', help='静默输出')
    parser.add_argument('--fail-fast', '-x', action='store_true', help='快速失败')
    
    return parser.parse_args()

def main():
    """主函数"""
    args = parse_args()
    
    # 设置环境变量以跳过慢速操作
    os.environ['PYTEST_FAST_MODE'] = '1'
    
    # 构建pytest命令
    cmd = [sys.executable, '-m', 'pytest']
    
    # 基本优化参数
    cmd.extend([
        '--tb=short',           # 简短错误信息
        '--disable-warnings',   # 禁用警告
        '--durations=5',        # 显示最慢的5个测试
        '--maxfail=3',          # 最多失败3个就停止
    ])
    
    # 并行执行
    if args.workers > 1:
        cmd.extend(['-n', str(args.workers)])
    
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
    
    # 标记过滤
    if args.unit_only:
        cmd.extend(['-m', 'unit'])
    else:
        # 跳过慢速测试
        cmd.extend(['-m', 'not slow and not browser'])
    
    # 添加测试路径
    cmd.append(args.test_path)
    
    print(f"🚀 快速测试运行器")
    print(f"📁 测试路径: {args.test_path}")
    print(f"🔧 命令: {' '.join(cmd)}")
    print(f"⏱️  开始时间: {time.strftime('%H:%M:%S')}")
    print("=" * 50)
    
    # 记录开始时间
    start_time = time.time()
    
    try:
        # 运行pytest
        result = subprocess.run(cmd, cwd=os.getcwd())
        
        # 计算耗时
        duration = time.time() - start_time
        
        print("=" * 50)
        print(f"⏱️  结束时间: {time.strftime('%H:%M:%S')}")
        print(f"🎯 总耗时: {duration:.2f}秒")
        
        if result.returncode == 0:
            print("✅ 测试通过!")
        else:
            print("❌ 测试失败!")
        
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