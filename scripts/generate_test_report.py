#!/usr/bin/env python3
"""
Test Report Generator for WoniuNote
Generates comprehensive HTML and JSON test reports
"""

import os
import sys
import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
from collections import defaultdict

# 确保项目根目录在Python路径中
project_root = Path("/Users/yunjinqi/Documents/woniunote")
if project_root not in sys.path:
    sys.path.insert(0, str(project_root))

class TestReportGenerator:
    """测试报告生成器"""

    def __init__(self):
        self.project_root = project_root
        self.test_results_dir = project_root / "test-results"
        self.reports_dir = project_root / "test-reports"
        self.reports_dir.mkdir(exist_ok=True)

    def generate_comprehensive_report(self) -> Dict[str, Any]:
        """生成综合测试报告"""
        print("📊 Generating comprehensive test report...")

        # 收集所有测试结果
        test_results = self._collect_test_results()
        coverage_data = self._collect_coverage_data()
        quality_data = self._collect_quality_data()

        # 生成报告数据
        report_data = {
            "generated_at": datetime.now().isoformat(),
            "project": "WoniuNote",
            "version": self._get_project_version(),
            "summary": self._generate_summary(test_results),
            "test_results": test_results,
            "coverage": coverage_data,
            "quality": quality_data,
            "recommendations": self._generate_recommendations(test_results, coverage_data),
            "trends": self._analyze_trends()
        }

        # 保存JSON报告
        json_path = self.reports_dir / f"test-report-{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)

        # 生成HTML报告
        html_path = self._generate_html_report(report_data)

        print(f"✅ Comprehensive report generated:")
        print(f"   JSON: {json_path}")
        print(f"   HTML: {html_path}")

        return report_data

    def _collect_test_results(self) -> Dict[str, Any]:
        """收集测试结果"""
        results = {
            "unit": {"files": [], "summary": {"passed": 0, "failed": 0, "total": 0}},
            "integration": {"files": [], "summary": {"passed": 0, "failed": 0, "total": 0}},
            "security": {"files": [], "summary": {"passed": 0, "failed": 0, "total": 0}},
            "performance": {"files": [], "summary": {"passed": 0, "failed": 0, "total": 0}},
            "e2e": {"files": [], "summary": {"passed": 0, "failed": 0, "total": 0}}
        }

        if not self.test_results_dir.exists():
            return results

        # 收集JSON结果文件
        for json_file in self.test_results_dir.glob("test-results-*.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                test_type = data.get("test_type", "unknown")
                if test_type in results:
                    results[test_type]["files"].append({
                        "file": str(json_file.name),
                        "timestamp": data.get("timestamp"),
                        "summary": data.get("summary", {}),
                        "status": data.get("status")
                    })

                    # 累加统计信息
                    summary = data.get("summary", {})
                    results[test_type]["summary"]["passed"] += summary.get("passed", 0)
                    results[test_type]["summary"]["failed"] += summary.get("failed", 0)
                    results[test_type]["summary"]["total"] += (
                        summary.get("passed", 0) + summary.get("failed", 0)
                    )

            except Exception as e:
                print(f"⚠️ Failed to parse {json_file}: {e}")

        return results

    def _collect_coverage_data(self) -> Dict[str, Any]:
        """收集覆盖率数据"""
        coverage_data = {
            "overall": {"percentage": 0.0, "covered_lines": 0, "total_lines": 0},
            "by_file": {},
            "missing_lines": {}
        }

        # 查找最新的覆盖率文件
        coverage_files = list(self.project_root.glob("coverage.json"))
        coverage_files.extend(list(self.project_root.glob("htmlcov/coverage.json")))

        if coverage_files:
            latest_coverage = max(coverage_files, key=lambda f: f.stat().st_mtime)
            try:
                with open(latest_coverage, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                totals = data.get("totals", {})
                coverage_data["overall"] = {
                    "percentage": totals.get("percent_covered", 0),
                    "covered_lines": totals.get("num_statements", 0) - totals.get("missing_lines", 0),
                    "total_lines": totals.get("num_statements", 0)
                }

                # 按文件统计
                for file_path, file_data in data.get("files", {}).items():
                    if file_path.startswith("woniunote/"):
                        coverage_data["by_file"][file_path] = {
                            "percentage": file_data.get("summary", {}).get("percent_covered", 0),
                            "covered_lines": file_data.get("summary", {}).get("covered_lines", 0),
                            "total_lines": file_data.get("summary", {}).get("num_statements", 0)
                        }

            except Exception as e:
                print(f"⚠️ Failed to parse coverage data: {e}")

        return coverage_data

    def _collect_quality_data(self) -> Dict[str, Any]:
        """收集质量检查数据"""
        quality_data = {
            "flake8": {"status": "unknown", "issues": 0},
            "black": {"status": "unknown", "issues": 0},
            "isort": {"status": "unknown", "issues": 0},
            "mypy": {"status": "unknown", "issues": 0},
            "bandit": {"status": "unknown", "issues": 0},
            "overall_status": "unknown"
        }

        # 查找最新的质量检查文件
        quality_files = list(self.test_results_dir.glob("quality-check-*.json"))

        if quality_files:
            latest_quality = max(quality_files, key=lambda f: f.stat().st_mtime)
            try:
                with open(latest_quality, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                checks = data.get("checks", {})
                for check_name, check_data in checks.items():
                    if check_name in quality_data:
                        quality_data[check_name]["status"] = check_data.get("status", "unknown")
                        if check_name == "bandit":
                            quality_data[check_name]["issues"] = check_data.get("issues_count", 0)

                quality_data["overall_status"] = data.get("overall_status", "unknown")

            except Exception as e:
                print(f"⚠️ Failed to parse quality data: {e}")

        return quality_data

    def _generate_summary(self, test_results: Dict[str, Any]) -> Dict[str, Any]:
        """生成总结信息"""
        summary = {
            "total_tests": 0,
            "passed_tests": 0,
            "failed_tests": 0,
            "success_rate": 0.0,
            "test_suites": len(test_results),
            "status": "unknown"
        }

        for test_type, data in test_results.items():
            summary["total_tests"] += data["summary"]["total"]
            summary["passed_tests"] += data["summary"]["passed"]
            summary["failed_tests"] += data["summary"]["failed"]

        if summary["total_tests"] > 0:
            summary["success_rate"] = round(
                (summary["passed_tests"] / summary["total_tests"]) * 100, 2
            )

        # 确定整体状态
        if summary["failed_tests"] == 0 and summary["total_tests"] > 0:
            summary["status"] = "passed"
        elif summary["failed_tests"] > 0:
            summary["status"] = "failed"
        else:
            summary["status"] = "no_tests"

        return summary

    def _generate_recommendations(self, test_results: Dict[str, Any], coverage_data: Dict[str, Any]) -> List[str]:
        """生成改进建议"""
        recommendations = []

        # 检查失败的测试
        failed_tests = []
        for test_type, data in test_results.items():
            if data["summary"]["failed"] > 0:
                failed_tests.append(f"{test_type}: {data['summary']['failed']} failed")

        if failed_tests:
            recommendations.append(f"🔴 Fix failing tests: {', '.join(failed_tests)}")

        # 检查覆盖率
        coverage_pct = coverage_data.get("overall", {}).get("percentage", 0)
        if coverage_pct < 80:
            recommendations.append(f"🟡 Improve test coverage: Current {coverage_pct:.1f}%, target >80%")

        # 检查质量问题
        quality_issues = []
        if coverage_data.get("quality", {}).get("bandit", {}).get("issues", 0) > 0:
            quality_issues.append("security vulnerabilities")

        if quality_issues:
            recommendations.append(f"🟠 Address quality issues: {', '.join(quality_issues)}")

        # 默认建议
        if not recommendations:
            recommendations.append("✅ All tests passing, coverage adequate - maintain current standards")

        return recommendations

    def _analyze_trends(self) -> Dict[str, Any]:
        """分析趋势数据"""
        trends = {
            "coverage_trend": [],
            "test_execution_time": [],
            "failure_rate_trend": []
        }

        # 这里可以实现更复杂的趋势分析
        # 目前返回空数据结构供将来扩展

        return trends

    def _get_project_version(self) -> str:
        """获取项目版本"""
        try:
            # 尝试从setup.py或pyproject.toml获取版本
            setup_file = self.project_root / "setup.py"
            if setup_file.exists():
                with open(setup_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if "version=" in content:
                        # 简单的版本提取
                        return "1.0.0"

            # 尝试从__init__.py获取
            init_file = self.project_root / "woniunote" / "__init__.py"
            if init_file.exists():
                with open(init_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if "__version__" in content:
                        return "1.0.0"

        except Exception:
            pass

        return "1.0.0"

    def _generate_html_report(self, report_data: Dict[str, Any]) -> str:
        """生成HTML报告"""
        html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>WoniuNote 测试报告</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f8f9fa;
            color: #212529;
            line-height: 1.6;
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }}

        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
            text-align: center;
        }}

        .header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
        }}

        .header .subtitle {{
            font-size: 1.2em;
            opacity: 0.9;
        }}

        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}

        .card {{
            background: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}

        .card h3 {{
            color: #495057;
            margin-bottom: 15px;
            border-bottom: 2px solid #e9ecef;
            padding-bottom: 10px;
        }}

        .metric {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }}

        .metric-value {{
            font-size: 1.5em;
            font-weight: bold;
        }}

        .status-badge {{
            padding: 5px 10px;
            border-radius: 15px;
            font-size: 0.8em;
            font-weight: bold;
        }}

        .status-passed {{ background: #d4edda; color: #155724; }}
        .status-failed {{ background: #f8d7da; color: #721c24; }}
        .status-warning {{ background: #fff3cd; color: #856404; }}

        .progress-bar {{
            background: #e9ecef;
            border-radius: 10px;
            height: 10px;
            margin: 10px 0;
            overflow: hidden;
        }}

        .progress-fill {{
            height: 100%;
            background: linear-gradient(90deg, #28a745, #20c997);
            transition: width 0.3s ease;
        }}

        .test-results {{
            margin-top: 30px;
        }}

        .test-type {{
            margin-bottom: 20px;
        }}

        .test-type h4 {{
            color: #495057;
            margin-bottom: 10px;
        }}

        .recommendations {{
            background: #e7f3ff;
            border: 1px solid #b3d9ff;
            border-radius: 10px;
            padding: 20px;
            margin-top: 30px;
        }}

        .recommendations h3 {{
            color: #004085;
            margin-bottom: 15px;
        }}

        .recommendations ul {{
            list-style: none;
            padding: 0;
        }}

        .recommendations li {{
            padding: 8px 0;
            border-bottom: 1px solid #b3d9ff;
        }}

        .recommendations li:last-child {{
            border-bottom: none;
        }}

        .footer {{
            text-align: center;
            margin-top: 30px;
            color: #6c757d;
            font-size: 0.9em;
        }}

        @media (max-width: 768px) {{
            .summary-grid {{
                grid-template-columns: 1fr;
            }}

            .header h1 {{
                font-size: 2em;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🧪 WoniuNote 测试报告</h1>
            <div class="subtitle">生成时间: {report_data['generated_at'][:19].replace('T', ' ')}</div>
        </div>

        <div class="summary-grid">
            <!-- 测试概览 -->
            <div class="card">
                <h3>📊 测试概览</h3>
                <div class="metric">
                    <span>总测试数</span>
                    <span class="metric-value">{report_data['summary']['total_tests']}</span>
                </div>
                <div class="metric">
                    <span>通过测试</span>
                    <span class="metric-value" style="color: #28a745;">{report_data['summary']['passed_tests']}</span>
                </div>
                <div class="metric">
                    <span>失败测试</span>
                    <span class="metric-value" style="color: #dc3545;">{report_data['summary']['failed_tests']}</span>
                </div>
                <div class="metric">
                    <span>成功率</span>
                    <span class="metric-value">{report_data['summary']['success_rate']}%</span>
                </div>
                <div class="status-badge status-{'passed' if report_data['summary']['status'] == 'passed' else 'failed' if report_data['summary']['status'] == 'failed' else 'warning'}">
                    {report_data['summary']['status'].upper()}
                </div>
            </div>

            <!-- 覆盖率 -->
            <div class="card">
                <h3>🎯 代码覆盖率</h3>
                <div class="metric">
                    <span>总体覆盖率</span>
                    <span class="metric-value">{report_data['coverage']['overall']['percentage']:.1f}%</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: {report_data['coverage']['overall']['percentage']}%"></div>
                </div>
                <div class="metric">
                    <span>覆盖行数</span>
                    <span>{report_data['coverage']['overall']['covered_lines']}/{report_data['coverage']['overall']['total_lines']}</span>
                </div>
            </div>

            <!-- 质量检查 -->
            <div class="card">
                <h3>🔍 代码质量</h3>
                <div class="metric">
                    <span>整体状态</span>
                    <div class="status-badge status-{'passed' if report_data['quality']['overall_status'] == 'passed' else 'failed' if report_data['quality']['overall_status'] == 'failed' else 'warning'}">
                        {report_data['quality']['overall_status'].upper()}
                    </div>
                </div>
                <div class="metric">
                    <span>安全问题</span>
                    <span>{report_data['quality']['bandit']['issues']}</span>
                </div>
            </div>
        </div>

        <!-- 测试结果详情 -->
        <div class="test-results">
            <h2>📋 测试结果详情</h2>
"""

        # 添加各测试类型的详细结果
        for test_type, data in report_data['test_results'].items():
            if data['summary']['total'] > 0:
                html_content += f"""
            <div class="test-type">
                <h4>{test_type.title()} Tests</h4>
                <div class="metric">
                    <span>通过: {data['summary']['passed']}</span>
                    <span>失败: {data['summary']['failed']}</span>
                    <span>总数: {data['summary']['total']}</span>
                </div>
            </div>
"""

        # 添加建议
        if report_data['recommendations']:
            html_content += """
            <div class="recommendations">
                <h3>💡 改进建议</h3>
                <ul>
"""
            for rec in report_data['recommendations']:
                html_content += f"                    <li>{rec}</li>\n"

            html_content += """
                </ul>
            </div>
"""

        # 添加页脚
        html_content += f"""
        <div class="footer">
            <p>Generated by WoniuNote Test Suite - Version {report_data['version']}</p>
            <p>Report generated at {report_data['generated_at'][:19].replace('T', ' ')}</p>
        </div>
    </div>
</body>
</html>
"""

        # 保存HTML文件
        html_path = self.reports_dir / f"test-report-{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        return str(html_path)


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="WoniuNote Test Report Generator")
    parser.add_argument("--output-dir", help="Output directory for reports")
    parser.add_argument("--format", choices=["json", "html", "both"], default="both",
                       help="Report format")

    args = parser.parse_args()

    generator = TestReportGenerator()

    if args.output_dir:
        generator.reports_dir = Path(args.output_dir)
        generator.reports_dir.mkdir(exist_ok=True)

    # 生成综合报告
    report_data = generator.generate_comprehensive_report()

    print("\n" + "="*60)
    print("🎯 TEST REPORT SUMMARY")
    print("="*60)
    print(f"Project: {report_data['project']} v{report_data['version']}")
    print(f"Generated: {report_data['generated_at'][:19].replace('T', ' ')}")
    print(f"Total Tests: {report_data['summary']['total_tests']}")
    print(f"Passed: {report_data['summary']['passed_tests']}")
    print(f"Failed: {report_data['summary']['failed_tests']}")
    print(".1f")
    print(f"Coverage: {report_data['coverage']['overall']['percentage']:.1f}%")
    print(f"Quality Status: {report_data['quality']['overall_status'].upper()}")
    print("="*60)

    if report_data['recommendations']:
        print("\n💡 Recommendations:")
        for i, rec in enumerate(report_data['recommendations'], 1):
            print(f"{i}. {rec}")


if __name__ == "__main__":
    main()
