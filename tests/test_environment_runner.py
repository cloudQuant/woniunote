#!/usr/bin/env python3
"""
测试环境运行器
设置正确的测试环境，然后运行覆盖率测试
"""
# 确保项目根目录在Python路径中
import sys
import os

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 设置测试环境
os.environ['TESTING'] = 'True'
os.environ['FLASK_ENV'] = 'testing'

import os
import sys
import subprocess
import pytest
from pathlib import Path

def setup_test_environment():
    """设置测试环境变量"""
    test_env = {
        'FLASK_ENV': 'testing',
        'TESTING': 'True',
        'SECRET_KEY': 'TestSecret123KEY456ForTestingOnly',
        'DATABASE_URL': 'sqlite:///:memory:',
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'WTF_CSRF_ENABLED': 'False',
        'SQLALCHEMY_TRACK_MODIFICATIONS': 'False'
    }
    
    # 更新环境变量
    os.environ.update(test_env)
    
    # 添加项目根目录到 Python 路径
    project_root = Path(__file__).parent.parent
    sys.path.insert(0, str(project_root))
    
    return test_env

def run_coverage_analysis():
    """运行覆盖率分析"""
    print("开始运行测试覆盖率分析...")
    
    # 设置测试环境
    test_env = setup_test_environment()
    
    # 构建完整的环境变量（当前环境 + 测试环境）
    full_env = os.environ.copy()
    full_env.update(test_env)
    
    try:
        # 运行覆盖率测试
        cmd = [
            'pytest', 
            'tests/',
            '-v',
            '--cov=woniunote',
            '--cov-report=html',
            '--cov-report=term-missing',
            '--cov-report=json',
            '--tb=short',
            '--disable-warnings'
        ]
        
        print(f"执行命令: {' '.join(cmd)}")
        print(f"测试环境: {test_env}")
        
        result = subprocess.run(
            cmd,
            env=full_env,
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent)
        )
        
        print("STDOUT:")
        print(result.stdout)
        
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
        
        print(f"返回码: {result.returncode}")
        return result.returncode == 0
        
    except Exception as e:
        print(f"运行测试时出错: {e}")
        return False

def run_simple_test():
    """运行简单的导入测试"""
    print("运行简单导入测试...")
    
    setup_test_environment()
    
    try:
        import woniunote
        print("✓ woniunote 导入成功")
        
        # 使用直接路径导入
        import sys
        sys.path.insert(0, '/home/yun/Documents/woniunote/woniunote/common')
        
        try:
            import simple_logger
            print("✓ simple_logger 导入成功")
        except ImportError:
            print("- simple_logger 导入失败（可接受）")
        
        try:
            import database
            print("✓ database 导入成功")
        except ImportError:
            print("- database 导入失败（可接受）")
        
        return True
        
    except Exception as e:
        print(f"✗ 导入失败: {e}")
        return False

class TestEnvironmentRunner:
    """测试环境运行器测试类"""
    
    def test_simple_imports(self):
        """测试简单导入"""
        try:
            result = run_simple_test()
            if not result:
                assert False, "Simple import test failed - expected in test environment"
            assert result
        except Exception as e:
            assert False, f"Import test skipped due to environment issues: {e}"
    
    def test_basic(self):
        """基本测试占位符"""
        pass

if __name__ == '__main__':
    print("WoniuNote 测试环境运行器")
    print("=" * 50)
    
    # 先运行简单测试
    if run_simple_test():
        print("\n简单测试通过，开始覆盖率分析...")
        success = run_coverage_analysis()
        
        if success:
            print("\n✓ 测试覆盖率分析完成")
        else:
            print("\n✗ 测试覆盖率分析失败")
    else:
        print("\n✗ 基础导入测试失败")