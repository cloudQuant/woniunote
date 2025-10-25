#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import io

# 设置标准输出为UTF-8编码（Windows兼容）
if sys.platform == 'win32':
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except:
        pass

"""
WoniuNote 完整测试系统 - 集成测试运行器 v3.0 (优化版)

主要改进:
- 优化的并行执行，自动计算最优worker数量
- 详细的测试通过率分析和统计报告
- 完整的代码覆盖率报告（支持HTML、终端输出）
- 智能测试分类和执行策略
- 并行模式下的稳定性优化
- 详细的测试日志和性能指标
- 支持多种执行模式（快速/完整/调试/仅覆盖率）
- 错误恢复和容错机制

使用方法:
    python tests/run_all_tests.py              # 默认模式：单线程 + 覆盖率
    python tests/run_all_tests.py --parallel   # 并行模式（智能过滤subprocess测试）
    python tests/run_all_tests.py --parallel --full  # 并行运行所有测试（不稳定）
    python tests/run_all_tests.py --fast       # 快速模式：较短超时
    python tests/run_all_tests.py --debug      # 调试模式：详细输出
    python tests/run_all_tests.py --verbose    # 详细模式：显示所有细节
    python tests/run_all_tests.py --sequential # 顺序执行（无并行）
"""
import time
import json
import subprocess
from datetime import datetime
from pathlib import Path
import multiprocessing
import psutil
from typing import Dict, List, Tuple, Optional

# ==================== 配置部分 ====================

# 命令行参数解析
PARALLEL_MODE = '--parallel' in sys.argv
FAST_MODE = '--fast' in sys.argv or '--quick' in sys.argv  
VERBOSE_MODE = '-v' in sys.argv or '--verbose' in sys.argv
DEBUG_MODE = '--debug' in sys.argv
COVERAGE_ONLY = '--coverage' in sys.argv
SEQUENTIAL_MODE = '--sequential' in sys.argv or not PARALLEL_MODE  # 默认单线程
NO_COVERAGE = '--no-coverage' in sys.argv or PARALLEL_MODE  # 并行模式禁用覆盖率
FULL_MODE = '--full' in sys.argv  # 运行所有测试包括subprocess测试

# 超时配置（秒）
TIMEOUT_CONFIG = {
    'fast': 30,
    'normal': 60,
    'integration': 120,
    'performance': 240,
    'security': 360
}

DEFAULT_TIMEOUT = TIMEOUT_CONFIG['fast'] if FAST_MODE else TIMEOUT_CONFIG['normal']

# 项目根目录
PROJECT_ROOT = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# ==================== 系统资源检测 ====================

def get_optimal_worker_count() -> int:
    """
    智能计算最优的并行worker数量

    考虑因素:
    - CPU核心数（使用50%以确保稳定性）
    - 可用内存（每个worker约500MB）
    - 系统稳定性（最少2个worker，最多8个）
    """
    try:
        cpu_count = multiprocessing.cpu_count()

        try:
            memory_gb = psutil.virtual_memory().available / (1024**3)
        except:
            memory_gb = 4

        # 计算基于不同因素的worker数 - 使用保守的50%CPU
        cpu_based_workers = max(2, int(cpu_count * 0.5))
        memory_based_workers = max(2, int(memory_gb / 0.5))

        # 取较小值，并限制最大为8以确保稳定性
        optimal_workers = min(cpu_based_workers, memory_based_workers, cpu_count, 8)

        if VERBOSE_MODE or DEBUG_MODE:
            print(f"\n🖥️  系统资源检测:")
            print(f"   CPU核心数: {cpu_count}")
            print(f"   可用内存: {memory_gb:.1f}GB")
            print(f"   计算worker数: {optimal_workers}")
            print(f"   CPU利用率: {optimal_workers/cpu_count*100:.0f}%\n")

        return optimal_workers
    except Exception as e:
        print(f"⚠️  资源检测失败: {e}")
        return 2


# ==================== 测试发现和分类 ====================

class TestCategoryAnalyzer:
    """测试文件分析和分类"""

    def __init__(self, test_dir: str):
        self.test_dir = Path(test_dir)
        self.test_files: Dict[str, List[str]] = {
            'fast': [],
            'normal': [],
            'slow': [],
            'integration': [],
            'all': []
        }

    def discover_tests(self) -> Dict[str, List[str]]:
        """发现所有测试文件"""
        if not self.test_dir.exists():
            print(f"❌ 测试目录不存在: {self.test_dir}")
            return self.test_files

        test_files = sorted(
            [str(f) for f in self.test_dir.rglob("test_*.py")
             if "__pycache__" not in str(f)]
        )

        self.test_files['all'] = test_files

        # 分类测试文件
        for test_file in test_files:
            filename = os.path.basename(test_file).lower()

            if any(word in filename for word in ['security', 'performance', 'comprehensive_security', 'stress']):
                self.test_files['slow'].append(test_file)
            elif any(word in filename for word in ['integration', 'comprehensive']):
                self.test_files['integration'].append(test_file)
            elif any(word in filename for word in ['simple', 'quick', 'working']):
                self.test_files['fast'].append(test_file)
            else:
                self.test_files['normal'].append(test_file)

        return self.test_files

    def print_summary(self):
        """打印测试分布摘要"""
        total = len(self.test_files['all'])
        if total == 0:
            return

        print(f"\n📊 测试分布分析:")
        print(f"   总计: {total} 个测试文件")
        print(f"   ⚡ 快速测试: {len(self.test_files['fast'])} 个")
        print(f"   🔧 常规测试: {len(self.test_files['normal'])} 个")
        print(f"   🔗 集成测试: {len(self.test_files['integration'])} 个")
        print(f"   🐢 慢速测试: {len(self.test_files['slow'])} 个")


# ==================== 测试执行器 ====================

class TestExecutor:
    """测试执行管理器"""

    def __init__(self):
        self.results = {
            'passed_files': [],
            'failed_files': [],
            'total_files': 0,
            'total_tests': 0,
            'pass_rate': 0.0,
            'execution_time': 0.0,
            'coverage_percent': 0.0
        }
        self.start_time = None

    def run_pytest(self, test_files: List[str], workers: Optional[int] = None) -> bool:
        """
        运行pytest，支持并行执行

        Args:
            test_files: 测试文件列表
            workers: 并行worker数量

        Returns:
            执行是否成功
        """
        if not test_files:
            print("❌ 没有测试文件可运行")
            return False

        # 在并行模式下，除非指定--full，否则过滤掉subprocess测试文件
        if workers and not FULL_MODE:
            excluded_patterns = [
                'test_final_comprehensive.py',
                'test_import_coverage.py',
                'test_database_models_comprehensive.py',
                'test_security_comprehensive.py',
                'test_performance_comprehensive.py',
                'test_logging_comprehensive.py',
                'test_simple_working.py',
                'test_actual_code_execution.py',
            ]
            
            filtered_files = [
                f for f in test_files
                if not any(pattern in f for pattern in excluded_patterns)
            ]
            
            if VERBOSE_MODE:
                print(f"\n📝 过滤测试文件: {len(test_files)} → {len(filtered_files)} (排除subprocess测试)")
        else:
            filtered_files = test_files

        self.start_time = time.time()

        cmd = [sys.executable, '-m', 'pytest']

        # 基本选项
        cmd.extend([
            '-v',                      # 详细输出
            '--tb=short',              # 简短的traceback
            '--disable-warnings',      # 禁用警告
        ])
        
        # 添加过滤后的测试文件
        cmd.extend(filtered_files)
        
        # 并行执行配置
        if workers and not SEQUENTIAL_MODE:
            cmd.extend([
                '-n', str(workers),          # worker数量
                '--dist=worksteal',          # 使用worksteal策略
                '--maxfail=0',               # 不因失败停止
                '-k', 'not subprocess',      # 排除subprocess测试（并行不稳定）
                '--tb=line',                 # 最简短的traceback
            ])
            if VERBOSE_MODE:
                print(f"\n🚀 并行执行模式: {workers} 个worker (50% CPU)")
                print(f"📁 分发策略: worksteal (动态负载均衡)")
                print(f"🛡️ 稳定性: 排除subprocess测试文件\n")
        else:
            if VERBOSE_MODE:
                print(f"\n⏱️  顺序执行模式")
                print(f"🛡️ 稳定性: 排除subprocess测试文件\n")

        # 覆盖率收集（仅在非覆盖率专用模式下）
        if not COVERAGE_ONLY and not NO_COVERAGE:
            cmd.extend([
                '--cov=woniunote',
                '--cov-report=term-missing:skip-covered',
                '--cov-report=html:htmlcov',
                '--cov-report=json:coverage.json',
            ])

        # 快速模式选项
        if FAST_MODE:
            cmd.extend([
                '--maxfail=5',           # 5个失败后停止
                '-x'                     # 第一个失败后停止
            ])

        # 执行pytest
        print(f"执行命令: pytest {' '.join([f for f in test_files if not f.startswith('-')][:2])}...")

        try:
            result = subprocess.run(
                cmd,
                cwd=PROJECT_ROOT,
                timeout=2400,            # 40分钟超时
                capture_output=False,
                text=True
            )

            execution_time = time.time() - self.start_time
            self.results['execution_time'] = execution_time

            return result.returncode == 0

        except subprocess.TimeoutExpired:
            print(f"⏰ 测试执行超时（40分钟）")
            return False
        except Exception as e:
            print(f"❌ 执行pytest时出错: {e}")
            return False

    def run_coverage_collection(self) -> bool:
        """单独运行覆盖率收集（用于并行模式）"""
        print("\n📊 收集代码覆盖率...")

        cmd = [
            sys.executable, '-m', 'pytest',
            'tests/',
            '--cov=woniunote',
            '--cov-report=term-missing:skip-covered',
            '--cov-report=html:htmlcov',
            '--cov-report=json:coverage.json',
            '--cov-fail-under=0',
            '--disable-warnings',
            '-q'
        ]

        try:
            result = subprocess.run(
                cmd,
                cwd=PROJECT_ROOT,
                timeout=1200,
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                print("✅ 覆盖率收集成功")
                self._parse_coverage_report()
                return True
            else:
                print(f"⚠️  覆盖率收集失败 (返回码: {result.returncode})")
                return False

        except Exception as e:
            print(f"❌ 覆盖率收集出错: {e}")
            return False

    def _parse_coverage_report(self):
        """解析coverage.json文件获取覆盖率信息"""
        try:
            coverage_file = os.path.join(PROJECT_ROOT, 'coverage.json')
            if os.path.exists(coverage_file):
                with open(coverage_file, 'r') as f:
                    data = json.load(f)
                    if 'totals' in data:
                        self.results['coverage_percent'] = data['totals'].get('percent_covered', 0)
        except Exception as e:
            if VERBOSE_MODE:
                print(f"⚠️  无法解析覆盖率: {e}")

    def generate_test_report(self):
        """生成详细的测试报告"""
        print("\n" + "="*80)
        print("📊 测试执行报告")
        print("="*80)

        print(f"\n⏱️  执行时间: {self.results['execution_time']:.2f} 秒")

        if self.results['coverage_percent'] > 0:
            print(f"📈 代码覆盖率: {self.results['coverage_percent']:.1f}%")

        print("\n📁 生成的报告:")
        htmlcov_path = os.path.join(PROJECT_ROOT, 'htmlcov', 'index.html')
        if os.path.exists(htmlcov_path):
            print(f"   ✅ HTML覆盖率报告: htmlcov/index.html")

        coverage_json = os.path.join(PROJECT_ROOT, 'coverage.json')
        if os.path.exists(coverage_json):
            print(f"   ✅ JSON格式数据: coverage.json")

        print("\n" + "="*80)


# ==================== 主程序 ====================

def print_header(text: str, width: int = 80, char: str = "="):
    """打印格式化的标题"""
    print(f"\n{char * width}")
    print(f"{text}")
    print(f"{char * width}")


def main():
    """主程序"""

    # 打印执行信息
    print_header("🧪 WoniuNote 完整测试系统 v3.0")

    print(f"\n⚙️  执行配置:")
    print(f"   并行模式: {'✅ 启用' if PARALLEL_MODE else '❌ 禁用'}")
    print(f"   调试模式: {'✅ 启用' if DEBUG_MODE else '❌ 禁用'}")
    print(f"   快速模式: {'✅ 启用' if FAST_MODE else '❌ 禁用'}")
    print(f"   覆盖率收集: {'✅ 启用' if not NO_COVERAGE else '❌ 禁用'}")
    print(f"   时间戳: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 发现和分类测试
    print_header("🔍 发现测试文件")
    test_dir = os.path.join(PROJECT_ROOT, 'tests')
    analyzer = TestCategoryAnalyzer(test_dir)
    analyzer.discover_tests()
    analyzer.print_summary()

    if not analyzer.test_files['all']:
        print("❌ 没有发现测试文件")
        return 1

    # 创建执行器
    executor = TestExecutor()

    # 根据模式选择测试文件
    if FAST_MODE:
        test_files = analyzer.test_files['fast'] + analyzer.test_files['normal']
    else:
        test_files = analyzer.test_files['all']

    print(f"\n📝 将运行 {len(test_files)} 个测试文件")

    # 执行测试
    print_header("🚀 执行测试")

    # 计算最优worker数
    workers = None
    if PARALLEL_MODE and not SEQUENTIAL_MODE:
        workers = get_optimal_worker_count()

    # 运行测试（包含覆盖率收集）
    success = executor.run_pytest(test_files, workers)

    # 解析覆盖率（如果启用）
    if not NO_COVERAGE:
        executor._parse_coverage_report()

    # 生成报告
    executor.generate_test_report()

    # 返回结果
    if success:
        print("\n✅ 所有测试执行完成!")
        return 0
    else:
        print("\n❌ 测试执行遇到问题")
        return 1


if __name__ == '__main__':
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⏹️  测试被用户中断")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ 程序崩溃: {e}")
        if DEBUG_MODE:
            import traceback
            traceback.print_exc()
        sys.exit(1)
