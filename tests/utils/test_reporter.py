#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试报告生成器

此模块提供测试报告的生成功能，包括：
- HTML报告生成
- XML报告生成
- 测试覆盖率报告
- 性能测试报告
"""

import os
import sys
import json
import time
import logging
import pytest
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
import jinja2
import coverage

# 添加项目根目录到Python路径
project_root = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
sys.path.insert(0, project_root)

from tests.utils.test_config import COVERAGE_CONFIG

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestReporter:
    """测试报告生成器"""
    
    def __init__(self, output_dir: str = None):
        self.output_dir = output_dir or os.path.join(project_root, 'tests', 'reports')
        self.report_time = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.report_dir = os.path.join(self.output_dir, self.report_time)
        os.makedirs(self.report_dir, exist_ok=True)
        
        # 初始化Jinja2环境
        self.template_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(os.path.join(project_root, 'tests', 'templates')),
            autoescape=True
        )
    
    def generate_html_report(self, test_results: Dict[str, Any]):
        """生成HTML测试报告"""
        try:
            # 加载HTML模板
            template = self.template_env.get_template('test_report.html')
            
            # 准备报告数据
            report_data = {
                'title': 'WoniuNote Test Report',
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'results': test_results,
                'summary': self._generate_summary(test_results)
            }
            
            # 渲染报告
            html_content = template.render(**report_data)
            
            # 保存报告
            report_file = os.path.join(self.report_dir, 'test_report.html')
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            logger.info(f"HTML测试报告已生成: {report_file}")
            return report_file
        except Exception as e:
            logger.error(f"生成HTML测试报告失败: {e}")
            return None
    
    def generate_xml_report(self, test_results: Dict[str, Any]):
        """生成XML测试报告"""
        try:
            # 准备XML数据
            xml_data = {
                'testsuites': {
                    'testsuite': {
                        'name': 'WoniuNote Tests',
                        'timestamp': datetime.now().isoformat(),
                        'tests': len(test_results.get('tests', [])),
                        'failures': len(test_results.get('failures', [])),
                        'errors': len(test_results.get('errors', [])),
                        'skipped': len(test_results.get('skipped', [])),
                        'testcase': []
                    }
                }
            }
            
            # 添加测试用例数据
            for test in test_results.get('tests', []):
                testcase = {
                    'name': test['name'],
                    'classname': test['class'],
                    'time': test['duration'],
                    'status': test['status']
                }
                if test['status'] == 'failed':
                    testcase['failure'] = {
                        'message': test['message'],
                        'type': test['error_type']
                    }
                xml_data['testsuites']['testsuite']['testcase'].append(testcase)
            
            # 保存XML报告
            report_file = os.path.join(self.report_dir, 'test_report.xml')
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(xml_data, f, indent=2)
            
            logger.info(f"XML测试报告已生成: {report_file}")
            return report_file
        except Exception as e:
            logger.error(f"生成XML测试报告失败: {e}")
            return None
    
    def generate_coverage_report(self):
        """生成测试覆盖率报告"""
        if not COVERAGE_CONFIG['enabled']:
            logger.info("测试覆盖率报告生成已禁用")
            return None
        
        try:
            # 初始化覆盖率工具
            cov = coverage.Coverage(
                source=[COVERAGE_CONFIG['source_dir']],
                omit=COVERAGE_CONFIG['exclude_patterns']
            )
            
            # 加载覆盖率数据
            cov.load()
            
            # 生成HTML报告
            html_report_dir = os.path.join(self.report_dir, 'coverage')
            cov.html_report(directory=html_report_dir)
            
            # 生成XML报告
            xml_report_file = os.path.join(self.report_dir, 'coverage.xml')
            cov.xml_report(outfile=xml_report_file)
            
            logger.info(f"测试覆盖率报告已生成: {html_report_dir}")
            return html_report_dir
        except Exception as e:
            logger.error(f"生成测试覆盖率报告失败: {e}")
            return None
    
    def generate_performance_report(self, performance_results: Dict[str, Any]):
        """生成性能测试报告"""
        try:
            # 加载性能报告模板
            template = self.template_env.get_template('performance_report.html')
            
            # 准备报告数据
            report_data = {
                'title': 'WoniuNote Performance Test Report',
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'results': performance_results,
                'summary': self._generate_performance_summary(performance_results)
            }
            
            # 渲染报告
            html_content = template.render(**report_data)
            
            # 保存报告
            report_file = os.path.join(self.report_dir, 'performance_report.html')
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            logger.info(f"性能测试报告已生成: {report_file}")
            return report_file
        except Exception as e:
            logger.error(f"生成性能测试报告失败: {e}")
            return None
    
    def _generate_summary(self, test_results: Dict[str, Any]) -> Dict[str, Any]:
        """生成测试结果摘要"""
        total = len(test_results.get('tests', []))
        passed = len([t for t in test_results.get('tests', []) if t['status'] == 'passed'])
        failed = len([t for t in test_results.get('tests', []) if t['status'] == 'failed'])
        skipped = len([t for t in test_results.get('tests', []) if t['status'] == 'skipped'])
        
        return {
            'total': total,
            'passed': passed,
            'failed': failed,
            'skipped': skipped,
            'pass_rate': (passed / total * 100) if total > 0 else 0
        }
    
    def _generate_performance_summary(self, performance_results: Dict[str, Any]) -> Dict[str, Any]:
        """生成性能测试摘要"""
        return {
            'total_requests': performance_results.get('total_requests', 0),
            'successful_requests': performance_results.get('successful_requests', 0),
            'failed_requests': performance_results.get('failed_requests', 0),
            'average_response_time': performance_results.get('average_response_time', 0),
            'min_response_time': performance_results.get('min_response_time', 0),
            'max_response_time': performance_results.get('max_response_time', 0),
            'p95_response_time': performance_results.get('p95_response_time', 0),
            'p99_response_time': performance_results.get('p99_response_time', 0)
        }

@pytest.fixture
def test_reporter():
    """测试报告生成器fixture"""
    reporter = TestReporter()
    yield reporter

@pytest.mark.unit
def test_report_generation(test_reporter):
    """测试报告生成功能"""
    # 准备测试数据
    test_results = {
        'tests': [
            {
                'name': 'test_example',
                'class': 'TestExample',
                'duration': 0.1,
                'status': 'passed'
            },
            {
                'name': 'test_failure',
                'class': 'TestExample',
                'duration': 0.2,
                'status': 'failed',
                'message': 'Assertion failed',
                'error_type': 'AssertionError'
            }
        ]
    }
    
    # 生成报告
    html_report = test_reporter.generate_html_report(test_results)
    xml_report = test_reporter.generate_xml_report(test_results)
    
    # 验证报告文件是否存在
    assert os.path.exists(html_report), "HTML报告未生成"
    assert os.path.exists(xml_report), "XML报告未生成"

if __name__ == "__main__":
    print("手动运行测试报告生成器...") 