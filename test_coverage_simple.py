#!/usr/bin/env python
"""
简单的覆盖率测试脚本
"""
import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from tests.run_all_tests import init_coverage_collection, stop_coverage_collection, generate_coverage_report_from_current_session

def test_basic_coverage():
    """测试基础覆盖率功能"""
    print("=== 测试覆盖率收集功能 ===\n")

    # 1. 初始化覆盖率
    print("1. 初始化覆盖率收集...")
    coverage_enabled = init_coverage_collection()
    if coverage_enabled:
        print("✅ 覆盖率初始化成功")
    else:
        print("❌ 覆盖率初始化失败")
        return False

    # 2. 导入一些模块来产生覆盖率数据
    print("\n2. 导入模块产生覆盖率数据...")
    try:
        import woniunote.app
        import woniunote.common.database
        import woniunote.models
        print("✅ 模块导入成功")
    except ImportError as e:
        print(f"❌ 模块导入失败: {e}")
        return False

    # 3. 停止覆盖率收集
    print("\n3. 停止覆盖率收集...")
    if stop_coverage_collection():
        print("✅ 覆盖率收集停止成功")
    else:
        print("❌ 覆盖率收集停止失败")

    # 4. 生成覆盖率报告
    print("\n4. 生成覆盖率报告...")
    if generate_coverage_report_from_current_session():
        print("✅ 覆盖率报告生成成功")
    else:
        print("❌ 覆盖率报告生成失败")
        return False

    print("\n=== 覆盖率测试完成 ===")
    return True

if __name__ == "__main__":
    success = test_basic_coverage()
    sys.exit(0 if success else 1)
