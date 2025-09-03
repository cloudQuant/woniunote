#!/usr/bin/env python3
"""
Coverage Analysis Script for WoniuNote
Generates detailed coverage reports and identifies gaps
"""

import os
import sys
import subprocess
import json
from pathlib import Path

# 确保项目根目录在Python路径中
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

def run_coverage_analysis():
    """运行覆盖率分析"""
    print("🔍 开始覆盖率分析...")

    # 清理之前的覆盖率文件
    cleanup_commands = [
        "rm -f .coverage",
        "rm -f coverage.xml",
        "rm -rf htmlcov/"
    ]

    for cmd in cleanup_commands:
        try:
            subprocess.run(cmd, shell=True, check=False)
        except:
            pass

    # 运行覆盖率分析（不执行测试，只分析现有代码）
    print("📊 生成覆盖率报告...")
    cmd = [
        sys.executable, "-m", "pytest", "--cov=woniunote",
        "--cov-report=html", "--cov-report=term-missing",
        "--cov-report=json", "--cov-fail-under=0",  # 不设置失败阈值
        "--tb=no",  # 不显示详细错误信息
        "-x",  # 遇到第一个错误就停止
        "--disable-warnings",
        "--quiet",
        "tests/unit/test_user_controller_comprehensive.py::TestUserControllerLogin::test_login_success",
        "tests/unit/test_models_comprehensive.py::TestCardModel::test_card_creation",
        "-v"
    ]

    try:
        result = subprocess.run(cmd, cwd=project_root, capture_output=True, text=True, timeout=60)
        print(f"覆盖率分析完成 (退出码: {result.returncode})")
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print("❌ 覆盖率分析超时")
        return False
    except Exception as e:
        print(f"❌ 覆盖率分析失败: {e}")
        return False

def analyze_coverage_gaps():
    """分析覆盖率空白点"""
    print("🔍 分析覆盖率空白点...")

    coverage_file = Path(project_root) / "coverage.json"
    if not coverage_file.exists():
        print("❌ 未找到覆盖率文件")
        return {}

    try:
        with open(coverage_file, 'r', encoding='utf-8') as f:
            coverage_data = json.load(f)
    except Exception as e:
        print(f"❌ 读取覆盖率文件失败: {e}")
        return {}

    gaps = {}

    # 分析每个文件的覆盖率
    for file_path, file_data in coverage_data.get('files', {}).items():
        if not file_path.startswith('woniunote/'):
            continue

        summary = file_data.get('summary', {})
        covered_lines = summary.get('covered_lines', 0)
        num_statements = summary.get('num_statements', 1)
        coverage_percent = summary.get('percent_covered', 0)

        # 找出未覆盖的行
        missing_lines = file_data.get('missing_lines', [])

        if missing_lines and coverage_percent < 100:
            gaps[file_path] = {
                'coverage_percent': coverage_percent,
                'covered_lines': covered_lines,
                'total_lines': num_statements,
                'missing_lines': missing_lines[:10],  # 只显示前10个
                'missing_count': len(missing_lines)
            }

    return gaps

def generate_coverage_report():
    """生成覆盖率分析报告"""
    print("📝 生成覆盖率分析报告...")

    if not run_coverage_analysis():
        print("❌ 覆盖率分析失败，尝试备用方案...")
        # 创建基本的覆盖率估算
        gaps = estimate_coverage_gaps()
    else:
        gaps = analyze_coverage_gaps()

    # 生成报告
    report = {
        'summary': {
            'total_files_analyzed': len(gaps),
            'files_with_gaps': len([f for f in gaps.values() if f['missing_count'] > 0]),
            'estimated_coverage': calculate_estimated_coverage(gaps)
        },
        'coverage_gaps': gaps,
        'recommendations': generate_recommendations(gaps)
    }

    # 保存报告
    report_file = Path(project_root) / "coverage_analysis_report.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"✅ 覆盖率分析报告已保存到: {report_file}")
    return report

def estimate_coverage_gaps():
    """估算覆盖率空白点（当覆盖率分析失败时使用）"""
    print("📊 估算覆盖率空白点...")

    gaps = {}

    # 基于现有测试文件估算覆盖率
    test_files = [
        'tests/unit/test_user_controller_comprehensive.py',
        'tests/unit/test_article_controller_comprehensive.py',
        'tests/unit/test_comment_controller_comprehensive.py',
        'tests/unit/test_admin_controller_comprehensive.py',
        'tests/unit/test_models_comprehensive.py',
        'tests/unit/test_services_comprehensive.py',
        'tests/integration/test_user_workflow_integration.py',
        'tests/security/test_security_vulnerabilities.py'
    ]

    # 对应的源代码文件映射
    source_mapping = {
        'test_user_controller_comprehensive.py': 'woniunote/controller/user.py',
        'test_article_controller_comprehensive.py': 'woniunote/controller/article.py',
        'test_comment_controller_comprehensive.py': 'woniunote/controller/comment.py',
        'test_admin_controller_comprehensive.py': 'woniunote/controller/admin.py',
        'test_models_comprehensive.py': ['woniunote/models/card.py', 'woniunote/models/todo.py'],
        'test_services_comprehensive.py': 'woniunote/services/article_service.py',
        'test_user_workflow_integration.py': 'woniunote/controller/user.py',
        'test_security_vulnerabilities.py': 'woniunote/controller/user.py'
    }

    for test_file in test_files:
        test_path = Path(project_root) / test_file
        if test_path.exists():
            # 估算测试文件的覆盖率
            source_files = source_mapping.get(test_path.name, [])
            if isinstance(source_files, str):
                source_files = [source_files]

            for source_file in source_files:
                source_path = Path(project_root) / source_file
                if source_path.exists():
                    # 简单估算：基于测试文件大小估算覆盖率
                    try:
                        with open(test_path, 'r', encoding='utf-8') as f:
                            test_lines = len(f.readlines())

                        with open(source_path, 'r', encoding='utf-8') as f:
                            source_lines = len(f.readlines())

                        # 估算覆盖率（基于测试代码行数与源代码行数的比例）
                        estimated_coverage = min(95, (test_lines / source_lines) * 100)

                        gaps[source_file] = {
                            'coverage_percent': estimated_coverage,
                            'covered_lines': int(source_lines * estimated_coverage / 100),
                            'total_lines': source_lines,
                            'missing_lines': [],  # 无法精确知道
                            'missing_count': max(0, int(source_lines * (100 - estimated_coverage) / 100)),
                            'estimated': True
                        }
                    except Exception as e:
                        print(f"❌ 分析文件失败 {source_file}: {e}")

    return gaps

def calculate_estimated_coverage(gaps):
    """计算估算的总体覆盖率"""
    if not gaps:
        return 0

    total_lines = sum(gap['total_lines'] for gap in gaps.values())
    covered_lines = sum(gap['covered_lines'] for gap in gaps.values())

    if total_lines == 0:
        return 0

    return round((covered_lines / total_lines) * 100, 2)

def generate_recommendations(gaps):
    """生成改进建议"""
    recommendations = []

    # 按覆盖率排序，优先处理覆盖率最低的文件
    sorted_gaps = sorted(gaps.items(), key=lambda x: x[1]['coverage_percent'])

    for file_path, gap_data in sorted_gaps:
        if gap_data['coverage_percent'] < 90:
            recommendations.append({
                'file': file_path,
                'priority': 'high' if gap_data['coverage_percent'] < 70 else 'medium',
                'action': f"为 {gap_data['missing_count']} 行未覆盖代码添加测试用例",
                'estimated_effort': 'high' if gap_data['missing_count'] > 50 else 'medium'
            })

    return recommendations

def main():
    """主函数"""
    print("🎯 WoniuNote 覆盖率分析工具")
    print("=" * 50)

    # 生成覆盖率报告
    report = generate_coverage_report()

    # 显示摘要
    summary = report.get('summary', {})
    print("\n📊 分析结果摘要:")
    print(f"  • 分析文件数: {summary.get('total_files_analyzed', 0)}")
    print(f"  • 有空白文件数: {summary.get('files_with_gaps', 0)}")
    print(f"  • 估算覆盖率: {summary.get('estimated_coverage', 0):.2f}%")
    # 显示前5个需要改进的文件
    print("\n🔧 优先改进文件:")
    recommendations = report.get('recommendations', [])
    for i, rec in enumerate(recommendations[:5]):
        print(f"  {i+1}. {rec['file']} (优先级: {rec['priority']})")
        print(f"     {rec['action']}")

    print("\n✅ 覆盖率分析完成！")
    print("详细报告已保存到: coverage_analysis_report.json")
if __name__ == "__main__":
    main()
