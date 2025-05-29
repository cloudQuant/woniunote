#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
专门用于浏览器测试的运行器
解决超时问题，设置合理的超时时间
"""

import os
import sys
import time
import subprocess
import argparse

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='浏览器测试运行器')
    parser.add_argument('test_path', nargs='?', default='tests/functional/', 
                       help='测试文件或目录')
    parser.add_argument('--timeout', '-t', type=int, default=10, 
                       help='整体测试超时时间（秒），默认10秒')
    parser.add_argument('--page-timeout', type=int, default=5000, 
                       help='页面操作超时时间（毫秒），默认5秒')
    parser.add_argument('--verbose', '-v', action='store_true', help='详细输出')
    parser.add_argument('--headless', action='store_true', help='无头模式运行')
    parser.add_argument('--browser', default='chromium', choices=['chromium', 'firefox', 'webkit'],
                       help='选择浏览器')
    
    return parser.parse_args()

def main():
    """主函数"""
    args = parse_args()
    
    # 设置环境变量
    os.environ['PLAYWRIGHT_BROWSERS_PATH'] = '0'
    os.environ['PYTEST_FAST_MODE'] = '1'
    os.environ['BROWSER_TIMEOUT'] = str(args.page_timeout)
    
    # 构建pytest命令
    cmd = [sys.executable, '-m', 'pytest']
    
    # 添加测试路径
    cmd.append(args.test_path)
    
    # 基本配置 - 针对浏览器测试优化
    cmd.extend([
        '--tb=short',
        '--disable-warnings',
        f'--timeout={args.timeout}',
        '--maxfail=3',
        '-m', 'browser',  # 只运行浏览器测试
        '--durations=10',
    ])
    
    # 输出控制
    if args.verbose:
        cmd.append('-v')
    else:
        cmd.append('-q')
    
    # 浏览器配置
    cmd.extend([
        '--browser', args.browser,
    ])
    
    if args.headless:
        cmd.extend(['--headed'])
    
    # 禁用多余插件
    cmd.extend([
        '-p', 'no:cacheprovider',
        '-p', 'no:randomly',
    ])
    
    print(f"🌐 浏览器测试运行器")
    print(f"📁 测试路径: {args.test_path}")
    print(f"⏰ 总体超时: {args.timeout}秒")
    print(f"🔧 页面超时: {args.page_timeout}毫秒")
    print(f"🌐 浏览器: {args.browser}")
    if args.headless:
        print(f"👻 模式: 无头模式")
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
            print("✅ 所有浏览器测试通过!")
        else:
            print("❌ 有浏览器测试失败!")
            print("💡 提示:")
            print("   - 检查浏览器是否正确安装")
            print("   - 尝试增加 --timeout 参数")
            print("   - 使用 --verbose 查看详细错误")
        
        return result.returncode
        
    except KeyboardInterrupt:
        print("\n❌ 测试被用户中断")
        return 1
    except Exception as e:
        print(f"❌ 运行测试时出错: {e}")
        return 1

def show_examples():
    """显示使用示例"""
    examples = """
🎯 使用示例:

# 运行所有浏览器测试
python browser_test_runner.py

# 运行特定文件的浏览器测试
python browser_test_runner.py tests/functional/favorite/test_favorite_features.py

# 设置较长的超时时间
python browser_test_runner.py --timeout 30 --page-timeout 10000

# 详细输出
python browser_test_runner.py --verbose

# 使用不同浏览器
python browser_test_runner.py --browser firefox

# 无头模式
python browser_test_runner.py --headless
"""
    print(examples)

if __name__ == "__main__":
    if len(sys.argv) == 1:
        show_examples()
    
    exit_code = main()
    sys.exit(exit_code) 