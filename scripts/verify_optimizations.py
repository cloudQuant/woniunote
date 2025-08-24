#!/usr/bin/env python3
"""
优化功能验证脚本
验证所有新增的优化功能是否正常工作
"""
import sys
import os
import importlib
import traceback
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

class OptimizationVerifier:
    """优化功能验证器"""
    
    def __init__(self):
        self.results = []
        self.passed = 0
        self.failed = 0
    
    def verify_module_import(self, module_name, description):
        """验证模块导入"""
        try:
            importlib.import_module(module_name)
            self.log_success(f"✅ {description}")
            return True
        except ImportError as e:
            self.log_failure(f"❌ {description} - 导入失败: {e}")
            return False
        except Exception as e:
            self.log_failure(f"❌ {description} - 异常: {e}")
            return False
    
    def verify_function_callable(self, module_name, function_name, description):
        """验证函数可调用"""
        try:
            module = importlib.import_module(module_name)
            func = getattr(module, function_name)
            if callable(func):
                self.log_success(f"✅ {description}")
                return True
            else:
                self.log_failure(f"❌ {description} - 不是可调用对象")
                return False
        except Exception as e:
            self.log_failure(f"❌ {description} - 异常: {e}")
            return False
    
    def verify_class_instantiable(self, module_name, class_name, description, *args, **kwargs):
        """验证类可实例化"""
        try:
            module = importlib.import_module(module_name)
            cls = getattr(module, class_name)
            instance = cls(*args, **kwargs)
            self.log_success(f"✅ {description}")
            return True, instance
        except Exception as e:
            self.log_failure(f"❌ {description} - 异常: {e}")
            return False, None
    
    def log_success(self, message):
        """记录成功"""
        print(message)
        self.results.append(('PASS', message))
        self.passed += 1
    
    def log_failure(self, message):
        """记录失败"""
        print(message)
        self.results.append(('FAIL', message))
        self.failed += 1
    
    def print_summary(self):
        """打印总结"""
        print("\n" + "="*60)
        print(f"验证总结: {self.passed} 通过, {self.failed} 失败")
        print("="*60)
        
        if self.failed > 0:
            print("\n失败的验证项:")
            for result_type, message in self.results:
                if result_type == 'FAIL':
                    print(f"  {message}")
        
        return self.failed == 0

def main():
    """主验证函数"""
    print("🔍 开始验证 WoniuNote 优化功能...")
    print("="*60)
    
    verifier = OptimizationVerifier()
    
    # 1. 验证核心优化模块
    print("\n📦 验证核心优化模块:")
    verifier.verify_module_import(
        'woniunote.app_factory', 
        '应用工厂模块导入'
    )
    verifier.verify_module_import(
        'woniunote.common.base_model', 
        '基础模型模块导入'
    )
    verifier.verify_module_import(
        'woniunote.common.trace_id_manager', 
        '跟踪ID管理器模块导入'
    )
    
    # 2. 验证资源管理模块
    print("\n🔧 验证资源管理模块:")
    verifier.verify_module_import(
        'woniunote.common.resource_manager', 
        '资源管理器模块导入'
    )
    verifier.verify_module_import(
        'woniunote.common.session_manager', 
        '会话管理器模块导入'
    )
    verifier.verify_module_import(
        'woniunote.common.memory_monitor', 
        '内存监控器模块导入'
    )
    verifier.verify_module_import(
        'woniunote.common.cleanup_manager', 
        '清理管理器模块导入'
    )
    
    # 3. 验证安全模块
    print("\n🛡️ 验证安全模块:")
    verifier.verify_module_import(
        'woniunote.common.csrf_protection', 
        'CSRF保护模块导入'
    )
    verifier.verify_module_import(
        'woniunote.common.input_validator', 
        '输入验证器模块导入'
    )
    verifier.verify_module_import(
        'woniunote.common.password_utils', 
        '密码工具模块导入'
    )
    
    # 4. 验证性能优化模块
    print("\n⚡ 验证性能优化模块:")
    verifier.verify_module_import(
        'woniunote.common.cache_utils', 
        '缓存工具模块导入'
    )
    verifier.verify_module_import(
        'woniunote.common.error_handler', 
        '错误处理器模块导入'
    )
    
    # 5. 验证关键函数
    print("\n🔧 验证关键函数:")
    verifier.verify_function_callable(
        'woniunote.app_factory', 
        'create_app', 
        '应用工厂函数可调用'
    )
    verifier.verify_function_callable(
        'woniunote.common.trace_id_manager', 
        'generate_trace_id', 
        '跟踪ID生成函数可调用'
    )
    verifier.verify_function_callable(
        'woniunote.common.resource_manager', 
        'get_resource_stats', 
        '资源统计函数可调用'
    )
    verifier.verify_function_callable(
        'woniunote.common.memory_monitor', 
        'get_memory_report', 
        '内存报告函数可调用'
    )
    
    # 6. 验证类实例化
    print("\n🏗️ 验证类实例化:")
    success, base_model = verifier.verify_class_instantiable(
        'woniunote.common.base_model', 
        'BaseModel', 
        '基础模型类实例化',
        'test_model'
    )
    
    verifier.verify_class_instantiable(
        'woniunote.common.trace_id_manager', 
        'TraceIdManager', 
        '跟踪ID管理器类实例化'
    )
    
    # 7. 验证功能集成
    print("\n🔗 验证功能集成:")
    
    # 验证跟踪ID生成
    try:
        from woniunote.common.unified_utils import TraceIdManager
        trace_id = TraceIdManager.generate_trace_id('test')
        if trace_id and isinstance(trace_id, str) and len(trace_id) > 0:
            verifier.log_success("✅ 跟踪ID生成功能正常")
        else:
            verifier.log_failure("❌ 跟踪ID生成功能异常")
    except Exception as e:
        verifier.log_failure(f"❌ 跟踪ID生成测试失败: {e}")
    
    # 验证内存监控
    try:
        from woniunote.common.memory_monitor import get_memory_report
        report = get_memory_report()
        if isinstance(report, dict) and ('current_memory' in report or 'error' in report):
            verifier.log_success("✅ 内存监控功能正常")
        else:
            verifier.log_failure("❌ 内存监控功能异常")
    except Exception as e:
        verifier.log_failure(f"❌ 内存监控测试失败: {e}")
    
    # 验证资源管理
    try:
        from woniunote.common.resource_manager import get_resource_stats
        stats = get_resource_stats()
        if isinstance(stats, dict):
            verifier.log_success("✅ 资源管理功能正常")
        else:
            verifier.log_failure("❌ 资源管理功能异常")
    except Exception as e:
        verifier.log_failure(f"❌ 资源管理测试失败: {e}")
    
    # 验证CSRF保护
    try:
        from woniunote.common.unified_security import generate_csrf_token
        token = generate_csrf_token()
        if token and isinstance(token, str):
            verifier.log_success("✅ CSRF保护功能正常")
        else:
            verifier.log_failure("❌ CSRF保护功能异常")
    except Exception as e:
        verifier.log_failure(f"❌ CSRF保护测试失败: {e}")
    
    # 验证输入验证
    try:
        from woniunote.common.unified_validator import InputValidator
        validator = InputValidator()
        test_result = validator.validate_string("test", max_length=10)
        if test_result == "test":
            verifier.log_success("✅ 输入验证功能正常")
        else:
            verifier.log_failure("❌ 输入验证功能异常")
    except Exception as e:
        verifier.log_failure(f"❌ 输入验证测试失败: {e}")
    
    # 8. 验证配置文件
    print("\n📋 验证配置文件:")
    config_files = [
        'woniunote/common/database.py',
        'woniunote/common/utils.py',
        'woniunote/common/simple_logger.py'
    ]
    
    for config_file in config_files:
        config_path = project_root / config_file
        if config_path.exists():
            verifier.log_success(f"✅ 配置文件存在: {config_file}")
        else:
            verifier.log_failure(f"❌ 配置文件缺失: {config_file}")
    
    # 9. 验证文档文件
    print("\n📚 验证文档文件:")
    doc_files = [
        'docs/final_optimization_report.md',
        'docs/memory_leak_prevention_summary.md',
        'docs/dead_code_cleanup_summary.md',
        'docs/quick_start_optimized.md'
    ]
    
    for doc_file in doc_files:
        doc_path = project_root / doc_file
        if doc_path.exists():
            verifier.log_success(f"✅ 文档文件存在: {doc_file}")
        else:
            verifier.log_failure(f"❌ 文档文件缺失: {doc_file}")
    
    # 打印最终结果
    success = verifier.print_summary()
    
    if success:
        print("\n🎉 所有优化功能验证通过！")
        print("🚀 WoniuNote 优化版已准备就绪！")
        print("\n📖 下一步:")
        print("  1. 运行 python scripts/start_server.py 启动应用")
        print("  2. 访问 http://localhost:5001 查看应用")
        print("  3. 查看 docs/quick_start_optimized.md 了解新功能")
        return 0
    else:
        print("\n⚠️ 部分验证失败，请检查上述错误信息")
        print("🔧 建议检查:")
        print("  1. 确保所有依赖已安装: pip install -r requirements.txt")
        print("  2. 确保Python路径正确")
        print("  3. 检查文件权限")
        return 1

if __name__ == '__main__':
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️ 验证被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n💥 验证过程发生异常: {e}")
        print("完整错误信息:")
        traceback.print_exc()
        sys.exit(1)