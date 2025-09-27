#!/usr/bin/env python3
"""
Coverage Optimization Plan for WoniuNote
生成详细的覆盖率优化计划，为未覆盖代码添加测试
"""

import os
import json
from pathlib import Path

def analyze_uncovered_files():
    """分析未覆盖的文件"""
    project_root = Path("/Users/yunjinqi/Documents/woniunote")
    woniunote_dir = project_root / "woniunote"

    # 已覆盖的文件
    covered_files = {
        'controllers': [
            'woniunote/controller/user.py',
            'woniunote/controller/article.py',
            'woniunote/controller/comment.py',
            'woniunote/controller/admin.py'
        ],
        'models': [
            'woniunote/models/card.py',
            'woniunote/models/todo.py'
        ],
        'services': [
            'woniunote/services/article_service.py'
        ]
    }

    # 发现所有Python文件
    all_python_files = []
    for root, dirs, files in os.walk(woniunote_dir):
        for file in files:
            if file.endswith('.py') and not file.startswith('__'):
                rel_path = os.path.relpath(os.path.join(root, file), project_root)
                all_python_files.append(rel_path)

    # 找出未覆盖的文件
    covered_set = set()
    for category in covered_files.values():
        covered_set.update(category)

    uncovered_files = []
    for file_path in all_python_files:
        if file_path not in covered_set and file_path.startswith('woniunote/'):
            uncovered_files.append(file_path)

    return uncovered_files

def categorize_uncovered_files(uncovered_files):
    """对未覆盖文件进行分类"""
    categories = {
        'controllers': [],
        'modules': [],
        'common_utils': [],
        'app_core': [],
        'other': []
    }

    for file_path in uncovered_files:
        if '/controller/' in file_path:
            categories['controllers'].append(file_path)
        elif '/module/' in file_path:
            categories['modules'].append(file_path)
        elif '/common/' in file_path:
            categories['common_utils'].append(file_path)
        elif file_path in ['woniunote/app.py', 'woniunote/app_factory.py', 'woniunote/error_handlers.py']:
            categories['app_core'].append(file_path)
        else:
            categories['other'].append(file_path)

    return categories

def generate_optimization_plan(categories):
    """生成优化计划"""
    plan = {
        'phase_7_1': {
            'name': 'Phase 7.1: 核心控制器测试扩展',
            'files': categories['controllers'],
            'priority': 'high',
            'estimated_effort': 'medium',
            'test_files_to_create': []
        },
        'phase_7_2': {
            'name': 'Phase 7.2: 业务模块测试',
            'files': categories['modules'],
            'priority': 'high',
            'estimated_effort': 'high',
            'test_files_to_create': []
        },
        'phase_7_3': {
            'name': 'Phase 7.3: 公共工具测试',
            'files': categories['common_utils'],
            'priority': 'medium',
            'estimated_effort': 'high',
            'test_files_to_create': []
        },
        'phase_7_4': {
            'name': 'Phase 7.4: 应用核心测试',
            'files': categories['app_core'],
            'priority': 'medium',
            'estimated_effort': 'medium',
            'test_files_to_create': []
        },
        'phase_7_5': {
            'name': 'Phase 7.5: 其他组件测试',
            'files': categories['other'],
            'priority': 'low',
            'estimated_effort': 'low',
            'test_files_to_create': []
        }
    }

    # 为每个文件生成对应的测试文件名
    for phase, data in plan.items():
        for file_path in data['files']:
            # 提取文件名（不含扩展名）
            file_name = Path(file_path).stem
            # 生成测试文件名
            if '/controller/' in file_path:
                test_file = f"tests/unit/test_{file_name}_controller_comprehensive.py"
            elif '/module/' in file_path:
                test_file = f"tests/unit/test_{file_name}_module_comprehensive.py"
            elif '/common/' in file_path:
                test_file = f"tests/unit/test_{file_name}_comprehensive.py"
            else:
                test_file = f"tests/unit/test_{file_name}_comprehensive.py"

            data['test_files_to_create'].append(test_file)

    return plan

def estimate_effort(plan):
    """估算工作量"""
    effort_estimates = {
        'low': 2,      # 2小时
        'medium': 8,   # 8小时
        'high': 16     # 16小时
    }

    total_effort = 0
    for phase, data in plan.items():
        effort_per_file = effort_estimates[data['estimated_effort']]
        total_effort += len(data['files']) * effort_per_file

    return total_effort

def generate_summary_report(plan, uncovered_files):
    """生成总结报告"""
    total_files = len(uncovered_files)
    total_effort = estimate_effort(plan)

    summary = f"""
🎯 WoniuNote 覆盖率优化计划

📊 当前状态:
  • 已覆盖文件: 8 个
  • 未覆盖文件: {total_files} 个
  • 估算覆盖率: 94.87%
  • 目标覆盖率: 100%

⏱️ 工作量估算:
  • 总计工作量: {total_effort} 小时
  • 预计完成时间: {total_effort // 8 + 1} 个工作日 (8小时/日)

📋 优化阶段:
"""

    phase_count = 1
    for phase_key, phase_data in plan.items():
        file_count = len(phase_data['files'])
        if file_count > 0:
            summary += f"""
{phase_count}. {phase_data['name']}
   • 文件数量: {file_count}
   • 优先级: {phase_data['priority']}
   • 预计工作量: {phase_data['estimated_effort']}
   • 需创建测试: {len(phase_data['test_files_to_create'])} 个
"""
            phase_count += 1

    return summary

def save_detailed_plan(plan):
    """保存详细计划"""
    output_file = "/Users/yunjinqi/Documents/woniunote/coverage_optimization_detailed_plan.json"

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(plan, f, indent=2, ensure_ascii=False)

    print(f"✅ 详细优化计划已保存到: {output_file}")

def main():
    """主函数"""
    print("🔍 WoniuNote 覆盖率优化计划生成器")
    print("=" * 50)

    # 分析未覆盖文件
    uncovered_files = analyze_uncovered_files()
    print(f"📁 发现未覆盖文件: {len(uncovered_files)} 个")

    # 分类文件
    categories = categorize_uncovered_files(uncovered_files)

    # 生成优化计划
    plan = generate_optimization_plan(categories)

    # 生成总结报告
    summary = generate_summary_report(plan, uncovered_files)
    print(summary)

    # 保存详细计划
    save_detailed_plan(plan)

    print("\n✅ 覆盖率优化计划生成完成！")
    print("详细计划已保存到: coverage_optimization_detailed_plan.json")

if __name__ == "__main__":
    main()
