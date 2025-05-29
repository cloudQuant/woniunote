#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
WoniuNote 快速测试执行脚本

优化点:
1. 并行测试执行
2. 跳过慢速数据库检查
3. 复用应用上下文
4. 缓存测试数据
5. 快速失败模式
6. 只运行必要的初始化
"""

import os
import sys
import time
import logging
import argparse
import pytest
import multiprocessing
from pathlib import Path

# 添加项目根目录到Python路径
project_root = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, project_root)

# 配置日志
logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("fast_test_runner")

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='快速运行WoniuNote测试')
    parser.add_argument('test_path', nargs='?', help='指定要运行的测试文件或目录路径', default=None)
    parser.add_argument('--workers', '-n', type=int, 
                       default=min(4, multiprocessing.cpu_count()), 
                       help='并行测试worker数量')
    parser.add_argument('--unit-only', action='store_true', help='只运行单元测试')
    parser.add_argument('--no-db', action='store_true', help='跳过数据库初始化')
    parser.add_argument('--fail-fast', '-x', action='store_true', help='遇到失败立即停止')
    parser.add_argument('--verbose', '-v', action='store_true', help='显示详细输出')
    parser.add_argument('--quiet', '-q', action='store_true', help='减少输出')
    parser.add_argument('--tb', choices=['short', 'line', 'no'], default='short', help='错误回溯格式')
    parser.add_argument('--durations', type=int, default=10, help='显示最慢的N个测试')
    parser.add_argument('--cache-clear', action='store_true', help='清除pytest缓存')
    parser.add_argument('--markers', '-m', help='运行指定标记的测试')
    
    return parser.parse_args()

def collect_test_files(test_path=None):
    """收集要运行的测试文件"""
    if test_path:
        if os.path.isfile(test_path):
            return [test_path]
        elif os.path.isdir(test_path):
            test_files = []
            for root, dirs, files in os.walk(test_path):
                test_files.extend([os.path.join(root, f) for f in files if f.startswith('test_') and f.endswith('.py')])
            return test_files
    
    # 默认收集所有测试文件
    tests_dir = os.path.dirname(__file__)
    test_files = []
    for root, dirs, files in os.walk(tests_dir):
        # 跳过特定目录以提高速度
        dirs[:] = [d for d in dirs if d not in ['__pycache__', '.pytest_cache', 'coverage', 'reports']]
        test_files.extend([os.path.join(root, f) for f in files if f.startswith('test_') and f.endswith('.py')])
    
    return test_files

def setup_fast_environment():
    """设置快速测试环境"""
    # 设置环境变量以跳过慢速操作
    os.environ['PYTEST_FAST_MODE'] = '1'
    os.environ['SKIP_DB_INIT'] = '1'
    os.environ['DISABLE_LOGGING'] = '1'
    
    # 禁用不必要的警告
    import warnings
    warnings.filterwarnings("ignore")
    
    # 设置日志级别
    logging.getLogger('woniunote').setLevel(logging.ERROR)
    logging.getLogger('flask').setLevel(logging.ERROR)
    logging.getLogger('werkzeug').setLevel(logging.ERROR)

def run_tests_fast(args, test_files):
    """快速运行测试"""
    pytest_args = []
    
    # 基本参数
    if args.verbose:
        pytest_args.append('-v')
    elif args.quiet:
        pytest_args.append('-q')
    
    # 并行执行
    if args.workers > 1 and len(test_files) > 1:
        pytest_args.extend(['-n', str(args.workers)])
        pytest_args.append('--dist=loadfile')  # 按文件分发测试
    
    # 快速失败
    if args.fail_fast:
        pytest_args.append('-x')
    
    # 错误回溯
    pytest_args.extend(['--tb', args.tb])
    
    # 显示耗时
    if args.durations:
        pytest_args.extend(['--durations', str(args.durations)])
    
    # 清除缓存
    if args.cache_clear:
        pytest_args.append('--cache-clear')
    
    # 标记过滤
    if args.markers:
        pytest_args.extend(['-m', args.markers])
    
    # 只运行单元测试
    if args.unit_only:
        pytest_args.extend(['-m', 'unit'])
    
    # 跳过慢速测试
    pytest_args.extend(['-m', 'not slow'])
    
    # 禁用插件以提高速度
    pytest_args.extend([
        '-p', 'no:warnings',
        '-p', 'no:cacheprovider',
        '--disable-warnings'
    ])
    
    # 添加测试文件
    pytest_args.extend(test_files)
    
    logger.info(f"运行pytest，参数: {' '.join(pytest_args)}")
    
    # 运行测试
    return pytest.main(pytest_args)

def create_minimal_conftest():
    """创建最小化的conftest.py来覆盖原有的复杂配置"""
    minimal_conftest_content = '''"""
最小化测试配置 - 用于快速测试
"""
import pytest
import os
import sys

# 添加项目根目录到路径
project_root = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, project_root)

@pytest.fixture(scope="session")
def app():
    """创建测试应用"""
    from woniunote.app import create_app
    app = create_app(config_name='testing')
    return app

@pytest.fixture
def client(app):
    """创建测试客户端"""
    return app.test_client()

@pytest.fixture
def app_context(app):
    """应用上下文"""
    with app.app_context():
        yield app

# 跳过数据库相关的复杂初始化
if os.getenv('PYTEST_FAST_MODE'):
    # 禁用自动数据库准备
    pytest_plugins = []
'''
    
    conftest_backup = 'tests/conftest.py.backup'
    conftest_fast = 'tests/conftest_fast.py'
    conftest_original = 'tests/conftest.py'
    
    # 备份原始conftest.py（如果还没有备份）
    if os.path.exists(conftest_original) and not os.path.exists(conftest_backup):
        import shutil
        shutil.copy2(conftest_original, conftest_backup)
        logger.info("已备份原始conftest.py")
    
    # 创建快速conftest.py
    with open(conftest_fast, 'w', encoding='utf-8') as f:
        f.write(minimal_conftest_content)
    
    return conftest_backup, conftest_fast

def restore_conftest(conftest_backup):
    """恢复原始conftest.py"""
    conftest_original = 'tests/conftest.py'
    conftest_fast = 'tests/conftest_fast.py'
    
    try:
        # 删除快速配置文件
        if os.path.exists(conftest_fast):
            os.remove(conftest_fast)
        
        # 恢复原始配置
        if os.path.exists(conftest_backup):
            import shutil
            shutil.copy2(conftest_backup, conftest_original)
            logger.info("已恢复原始conftest.py")
    except Exception as e:
        logger.warning(f"恢复conftest.py时出错: {e}")

def main():
    """主函数"""
    start_time = time.time()
    
    try:
        # 解析参数
        args = parse_args()
        
        # 设置快速环境
        setup_fast_environment()
        
        # 收集测试文件
        test_files = collect_test_files(args.test_path)
        
        if not test_files:
            logger.error("未找到测试文件")
            return 1
        
        logger.info(f"找到 {len(test_files)} 个测试文件")
        if args.verbose:
            for f in test_files[:5]:  # 只显示前5个
                logger.info(f"  - {f}")
            if len(test_files) > 5:
                logger.info(f"  ... 还有 {len(test_files) - 5} 个文件")
        
        # 创建最小化配置（可选）
        conftest_backup = None
        if args.no_db:
            try:
                conftest_backup, conftest_fast = create_minimal_conftest()
                # 临时替换为快速配置
                import shutil
                shutil.copy2(conftest_fast, 'tests/conftest.py')
                logger.info("已切换到快速配置模式")
            except Exception as e:
                logger.warning(f"创建快速配置时出错: {e}，使用默认配置")
                conftest_backup = None
        
        try:
            # 运行测试
            result = run_tests_fast(args, test_files)
            
            end_time = time.time()
            duration = end_time - start_time
            
            print(f"\n🎯 测试完成!")
            print(f"⏱️  总耗时: {duration:.2f}秒")
            print(f"📊 测试文件: {len(test_files)}个")
            if args.workers > 1:
                print(f"🚀 并行度: {args.workers} workers")
            
            return result
            
        finally:
            # 恢复原始配置
            if conftest_backup and args.no_db:
                restore_conftest(conftest_backup)
    
    except KeyboardInterrupt:
        print("\n❌ 测试被用户中断")
        return 1
    except Exception as e:
        logger.error(f"测试执行失败: {e}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 