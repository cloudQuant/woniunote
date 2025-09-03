#!/usr/bin/env python3
"""
Test Management System for WoniuNote
Automated test execution, reporting, and management
"""

import os
import sys
import json
import subprocess
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import xml.etree.ElementTree as ET

# 确保项目根目录在Python路径中
project_root = Path("/Users/yunjinqi/Documents/woniunote")
if project_root not in sys.path:
    sys.path.insert(0, str(project_root))

class TestManager:
    """测试管理器"""

    def __init__(self):
        self.project_root = project_root
        self.test_results_dir = project_root / "test-results"
        self.test_results_dir.mkdir(exist_ok=True)

    def run_tests(self, test_type: str = "all", verbose: bool = False, coverage: bool = True) -> Dict:
        """运行指定类型的测试"""
        print(f"🚀 Running {test_type} tests...")

        cmd = self._build_test_command(test_type, verbose, coverage)

        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=1800  # 30分钟超时
            )

            # 解析测试结果
            test_results = self._parse_test_results(result, test_type)

            # 保存测试结果
            self._save_test_results(test_results, test_type)

            return test_results

        except subprocess.TimeoutExpired:
            print(f"❌ Test execution timed out for {test_type}")
            return {"status": "timeout", "test_type": test_type}

        except Exception as e:
            print(f"❌ Test execution failed: {e}")
            return {"status": "error", "test_type": test_type, "error": str(e)}

    def _build_test_command(self, test_type: str, verbose: bool, coverage: bool) -> List[str]:
        """构建测试命令"""
        cmd = [sys.executable, "-m", "pytest"]

        # 根据测试类型设置测试路径
        if test_type == "unit":
            cmd.extend(["tests/unit/"])
        elif test_type == "integration":
            cmd.extend(["tests/integration/"])
        elif test_type == "security":
            cmd.extend(["tests/security/"])
        elif test_type == "performance":
            cmd.extend(["tests/performance/"])
        elif test_type == "e2e":
            cmd.extend(["tests/e2e/"])
        else:  # all
            cmd.extend(["tests/"])

        # 添加选项
        if verbose:
            cmd.append("-v")
        else:
            cmd.append("--tb=short")

        if coverage:
            cmd.extend([
                "--cov=woniunote",
                "--cov-report=xml",
                "--cov-report=html",
                "--cov-report=term-missing",
                "--cov-fail-under=80"
            ])

        # 添加JUnit XML输出
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        xml_file = f"test-results-{test_type}-{timestamp}.xml"
        cmd.extend(["--junitxml", str(self.test_results_dir / xml_file)])

        return cmd

    def _parse_test_results(self, result: subprocess.CompletedProcess, test_type: str) -> Dict:
        """解析测试结果"""
        test_results = {
            "test_type": test_type,
            "status": "completed",
            "return_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "timestamp": datetime.now().isoformat(),
            "summary": {}
        }

        # 解析stdout中的测试统计信息
        stdout_lines = result.stdout.split('\n')
        for line in stdout_lines:
            if "passed" in line and "failed" in line:
                # 解析类似 "5 passed, 2 failed, 1 skipped" 的行
                parts = line.replace(',', '').split()
                for i, part in enumerate(parts):
                    if part.isdigit():
                        if i + 1 < len(parts):
                            key = parts[i + 1].lower()
                            if key in ["passed", "failed", "skipped", "errors"]:
                                test_results["summary"][key] = int(part)

        return test_results

    def _save_test_results(self, test_results: Dict, test_type: str):
        """保存测试结果"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"test-results-{test_type}-{timestamp}.json"

        with open(self.test_results_dir / filename, 'w', encoding='utf-8') as f:
            json.dump(test_results, f, indent=2, ensure_ascii=False)

        print(f"✅ Test results saved to: {self.test_results_dir / filename}")

    def generate_report(self, test_type: Optional[str] = None) -> Dict:
        """生成测试报告"""
        print("📊 Generating test report...")

        # 收集所有测试结果文件
        result_files = list(self.test_results_dir.glob("test-results-*.json"))

        if test_type:
            result_files = [f for f in result_files if test_type in f.name]

        all_results = []
        for result_file in result_files:
            try:
                with open(result_file, 'r', encoding='utf-8') as f:
                    result = json.load(f)
                    all_results.append(result)
            except Exception as e:
                print(f"❌ Failed to load {result_file}: {e}")

        # 生成综合报告
        report = self._generate_comprehensive_report(all_results)

        # 保存报告
        report_file = self.test_results_dir / f"comprehensive-report-{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"✅ Comprehensive report saved to: {report_file}")
        return report

    def _generate_comprehensive_report(self, results: List[Dict]) -> Dict:
        """生成综合报告"""
        report = {
            "generated_at": datetime.now().isoformat(),
            "total_test_runs": len(results),
            "summary": {
                "total_passed": 0,
                "total_failed": 0,
                "total_skipped": 0,
                "total_errors": 0,
                "success_rate": 0.0
            },
            "by_test_type": {},
            "recent_runs": []
        }

        # 按测试类型分组
        test_type_stats = {}

        for result in results:
            test_type = result.get("test_type", "unknown")

            if test_type not in test_type_stats:
                test_type_stats[test_type] = {
                    "runs": 0,
                    "passed": 0,
                    "failed": 0,
                    "skipped": 0,
                    "errors": 0
                }

            test_type_stats[test_type]["runs"] += 1

            summary = result.get("summary", {})
            test_type_stats[test_type]["passed"] += summary.get("passed", 0)
            test_type_stats[test_type]["failed"] += summary.get("failed", 0)
            test_type_stats[test_type]["skipped"] += summary.get("skipped", 0)
            test_type_stats[test_type]["errors"] += summary.get("errors", 0)

        # 计算总数
        for stats in test_type_stats.values():
            report["summary"]["total_passed"] += stats["passed"]
            report["summary"]["total_failed"] += stats["failed"]
            report["summary"]["total_skipped"] += stats["skipped"]
            report["summary"]["total_errors"] += stats["errors"]

        total_tests = (report["summary"]["total_passed"] +
                      report["summary"]["total_failed"] +
                      report["summary"]["total_errors"])

        if total_tests > 0:
            report["summary"]["success_rate"] = round(
                (report["summary"]["total_passed"] / total_tests) * 100, 2
            )

        report["by_test_type"] = test_type_stats

        # 最近的运行记录
        recent_results = sorted(results, key=lambda x: x.get("timestamp", ""), reverse=True)[:10]
        report["recent_runs"] = recent_results

        return report

    def run_quality_checks(self) -> Dict:
        """运行代码质量检查"""
        print("🔍 Running code quality checks...")

        checks = {
            "flake8": self._run_flake8(),
            "black": self._run_black(),
            "isort": self._run_isort(),
            "mypy": self._run_mypy(),
            "bandit": self._run_bandit()
        }

        # 保存质量检查结果
        quality_report = {
            "timestamp": datetime.now().isoformat(),
            "checks": checks,
            "overall_status": "passed" if all(check.get("status") == "passed" for check in checks.values()) else "failed"
        }

        quality_file = self.test_results_dir / f"quality-check-{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(quality_file, 'w', encoding='utf-8') as f:
            json.dump(quality_report, f, indent=2, ensure_ascii=False)

        print(f"✅ Quality check results saved to: {quality_file}")
        return quality_report

    def _run_flake8(self) -> Dict:
        """运行flake8检查"""
        try:
            result = subprocess.run(
                ["flake8", "woniunote", "--count", "--statistics"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300
            )
            return {
                "status": "passed" if result.returncode == 0 else "failed",
                "return_code": result.returncode,
                "output": result.stdout,
                "errors": result.stderr
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _run_black(self) -> Dict:
        """运行black格式检查"""
        try:
            result = subprocess.run(
                ["black", "--check", "--diff", "woniunote", "tests"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300
            )
            return {
                "status": "passed" if result.returncode == 0 else "failed",
                "return_code": result.returncode,
                "output": result.stdout,
                "errors": result.stderr
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _run_isort(self) -> Dict:
        """运行isort导入排序检查"""
        try:
            result = subprocess.run(
                ["isort", "--check-only", "--diff", "woniunote", "tests"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300
            )
            return {
                "status": "passed" if result.returncode == 0 else "failed",
                "return_code": result.returncode,
                "output": result.stdout,
                "errors": result.stderr
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _run_mypy(self) -> Dict:
        """运行mypy类型检查"""
        try:
            result = subprocess.run(
                ["mypy", "woniunote", "--ignore-missing-imports"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300
            )
            return {
                "status": "passed" if result.returncode == 0 else "failed",
                "return_code": result.returncode,
                "output": result.stdout,
                "errors": result.stderr
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _run_bandit(self) -> Dict:
        """运行bandit安全检查"""
        try:
            result = subprocess.run(
                ["bandit", "-r", "woniunote", "-f", "json"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300
            )

            # 解析bandit的JSON输出
            try:
                bandit_results = json.loads(result.stdout)
                issues_count = len(bandit_results.get("results", []))
                high_severity = sum(1 for issue in bandit_results.get("results", [])
                                  if issue.get("issue_severity") == "HIGH")
            except:
                issues_count = 0
                high_severity = 0

            return {
                "status": "passed" if high_severity == 0 else "warning",
                "return_code": result.returncode,
                "issues_count": issues_count,
                "high_severity_count": high_severity,
                "output": result.stdout,
                "errors": result.stderr
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="WoniuNote Test Manager")
    parser.add_argument("action", choices=["run", "report", "quality", "all"],
                       help="Action to perform")
    parser.add_argument("--type", choices=["unit", "integration", "security", "performance", "e2e", "all"],
                       default="all", help="Test type to run")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--no-coverage", action="store_true", help="Skip coverage report")

    args = parser.parse_args()

    manager = TestManager()

    if args.action == "run":
        result = manager.run_tests(args.type, args.verbose, not args.no_coverage)
        print(f"Test execution completed with status: {result.get('status')}")

    elif args.action == "report":
        report = manager.generate_report(args.type if args.type != "all" else None)
        print(f"Report generated: {report.get('summary', {})}")

    elif args.action == "quality":
        quality_report = manager.run_quality_checks()
        print(f"Quality check completed: {quality_report.get('overall_status')}")

    elif args.action == "all":
        # 运行所有测试
        print("🚀 Running complete test suite...")

        # 1. 质量检查
        print("1. Running quality checks...")
        quality_report = manager.run_quality_checks()

        # 2. 运行测试
        print("2. Running test suite...")
        test_result = manager.run_tests("all", args.verbose, not args.no_coverage)

        # 3. 生成报告
        print("3. Generating reports...")
        report = manager.generate_report()

        # 4. 输出总结
        print("\n" + "="*60)
        print("🎯 TEST EXECUTION SUMMARY")
        print("="*60)
        print(f"Quality Checks: {quality_report.get('overall_status', 'unknown').upper()}")
        print(f"Test Status: {test_result.get('status', 'unknown').upper()}")
        print(f"Success Rate: {report.get('summary', {}).get('success_rate', 0):.1f}%")
        print(f"Total Tests: {report.get('summary', {}).get('total_passed', 0) + report.get('summary', {}).get('total_failed', 0)}")
        print("="*60)


if __name__ == "__main__":
    main()
