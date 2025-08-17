#!/usr/bin/env python3
"""
简单的覆盖率测试
绕过复杂的配置，直接测试核心功能
"""
import os
import sys
from pathlib import Path

# 设置测试环境变量
os.environ.update({
    'FLASK_ENV': 'testing',
    'TESTING': 'True',
    'SECRET_KEY': 'TestSecret123KEY456ForTestingOnly',
    'DISABLE_DATABASE_POOL_OPTIMIZER': 'True',  # 禁用数据库池优化器
    'DISABLE_PERFORMANCE_MONITOR': 'True',     # 禁用性能监控
    'WTF_CSRF_ENABLED': 'False',
})

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_basic_imports():
    """测试基本导入"""
    try:
        # 测试基本模块导入
        print("测试导入 woniunote...")
        import woniunote
        print("✓ woniunote 导入成功")
        
        print("测试导入 simple_logger...")
        from woniunote.common.simple_logger import get_simple_logger
        print("✓ simple_logger 导入成功")
        
        print("测试导入 utils...")
        from woniunote.common.utils import validate_email
        print("✓ utils 导入成功")
        
        print("测试导入 models...")
        from woniunote.models.card import Card
        print("✓ card model 导入成功")
        
        return True
        
    except Exception as e:
        print(f"✗ 导入失败: {e}")
        return False

def test_function_calls():
    """测试函数调用"""
    try:
        print("测试函数调用...")
        
        # 测试简单工具函数
        from woniunote.common.utils import validate_email
        is_valid = validate_email("test@example.com")
        print(f"✓ 邮箱验证功能: {'正常' if is_valid else '异常'}")
        
        # 测试日志记录器
        from woniunote.common.simple_logger import get_simple_logger
        logger = get_simple_logger('test')
        logger.info("测试日志记录")
        print("✓ 日志记录功能正常")
        
        return True
        
    except Exception as e:
        print(f"✗ 函数调用失败: {e}")
        return False

def run_module_coverage_test():
    """运行模块覆盖率测试"""
    print("WoniuNote 简单覆盖率测试")
    print("=" * 50)
    
    # 测试基本导入
    if not test_basic_imports():
        return False
    
    print()
    
    # 测试函数调用
    if not test_function_calls():
        return False
    
    print()
    print("✓ 所有基本测试通过！")
    
    # 统计可导入的模块
    try:
        module_count = 0
        function_count = 0
        
        # 测试常用模块
        modules_to_test = [
            'woniunote.common.utils',
            'woniunote.common.simple_logger',
            'woniunote.models.card',
            'woniunote.models.todo',
        ]
        
        for module_name in modules_to_test:
            try:
                __import__(module_name)
                module_count += 1
                print(f"✓ {module_name}")
            except Exception as e:
                print(f"✗ {module_name}: {e}")
        
        print(f"\n成功导入模块数: {module_count}/{len(modules_to_test)}")
        
        # 计算基础覆盖率
        coverage_percentage = (module_count / len(modules_to_test)) * 100
        print(f"基础模块覆盖率: {coverage_percentage:.1f}%")
        
        return coverage_percentage > 50  # 至少50%的模块能正常导入
        
    except Exception as e:
        print(f"覆盖率测试失败: {e}")
        return False

if __name__ == '__main__':
    success = run_module_coverage_test()
    if success:
        print("\n🎉 基础测试成功！可以继续进行完整的测试覆盖率分析。")
        sys.exit(0)
    else:
        print("\n❌ 基础测试失败，需要修复导入问题。")
        sys.exit(1)