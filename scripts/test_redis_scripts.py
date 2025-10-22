#!/usr/bin/env python3
"""
Redis安装脚本测试工具
用于测试Redis安装脚本的各个功能模块

使用方法:
python scripts/test_redis_scripts.py
"""

import os
import sys
import subprocess
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

# 添加项目路径
sys.path.insert(0, str(Path.cwd()))

def test_redis_installer_import():
    """测试RedisInstaller类导入"""
    try:
        from scripts.install_redis_windows import RedisInstaller
        print("✓ RedisInstaller类导入成功")
        return True
    except Exception as e:
        print(f"✗ RedisInstaller类导入失败: {e}")
        return False

def test_redis_installer_initialization():
    """测试RedisInstaller初始化"""
    try:
        from scripts.install_redis_windows import RedisInstaller
        installer = RedisInstaller()
        
        # 检查基本属性
        assert hasattr(installer, 'redis_version')
        assert hasattr(installer, 'install_dir')
        assert hasattr(installer, 'redis_config')
        
        print("✓ RedisInstaller初始化成功")
        return True
    except Exception as e:
        print(f"✗ RedisInstaller初始化失败: {e}")
        return False

def test_admin_privileges_check():
    """测试管理员权限检查"""
    try:
        from scripts.install_redis_windows import RedisInstaller
        installer = RedisInstaller()
        
        # 这个方法应该能正常执行，不管返回什么
        result = installer.check_admin_privileges()
        print(f"✓ 管理员权限检查功能正常 (结果: {result})")
        return True
    except Exception as e:
        print(f"✗ 管理员权限检查失败: {e}")
        return False

def test_redis_detection():
    """测试Redis检测功能"""
    try:
        from scripts.install_redis_windows import RedisInstaller
        installer = RedisInstaller()
        
        # 测试Redis安装检查
        installed = installer.check_redis_installed()
        print(f"✓ Redis安装检查功能正常 (已安装: {installed})")
        
        # 测试Redis运行检查
        running = installer.check_redis_running()
        print(f"✓ Redis运行检查功能正常 (运行中: {running})")
        
        # 测试Redis连接
        connected = installer.test_redis_connection()
        print(f"✓ Redis连接测试功能正常 (连接成功: {connected})")
        
        return True
    except Exception as e:
        print(f"✗ Redis检测功能测试失败: {e}")
        return False

def test_config_generation():
    """测试配置文件生成"""
    try:
        from scripts.install_redis_windows import RedisInstaller
        installer = RedisInstaller()
        
        # 使用临时目录测试
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            installer.install_dir = temp_path
            installer.redis_conf = temp_path / "redis.conf"
            
            # 测试配置文件创建
            result = installer.create_redis_config()
            
            if result and installer.redis_conf.exists():
                print("✓ Redis配置文件生成功能正常")
                
                # 检查配置内容
                with open(installer.redis_conf, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if 'port 6379' in content and 'bind 127.0.0.1' in content:
                        print("✓ 配置文件内容正确")
                        return True
                    else:
                        print("✗ 配置文件内容不正确")
                        return False
            else:
                print("✗ 配置文件生成失败")
                return False
                
    except Exception as e:
        print(f"✗ 配置文件生成测试失败: {e}")
        return False

def test_script_creation():
    """测试管理脚本创建"""
    try:
        from scripts.install_redis_windows import RedisInstaller
        installer = RedisInstaller()
        
        # 使用临时目录测试
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            installer.install_dir = temp_path
            
            # 测试脚本创建
            result = installer.create_redis_scripts()
            
            if result:
                # 检查脚本文件是否存在
                scripts = [
                    temp_path / "start_redis.bat",
                    temp_path / "stop_redis.bat", 
                    temp_path / "redis_status.bat"
                ]
                
                all_exist = all(script.exists() for script in scripts)
                if all_exist:
                    print("✓ Redis管理脚本创建功能正常")
                    return True
                else:
                    print("✗ 部分管理脚本创建失败")
                    return False
            else:
                print("✗ 管理脚本创建失败")
                return False
                
    except Exception as e:
        print(f"✗ 管理脚本创建测试失败: {e}")
        return False

def test_quick_setup_import():
    """测试快速设置脚本导入"""
    try:
        from scripts.quick_redis_setup import (
            check_redis_service,
            check_redis_connection,
            check_redis_python_package
        )
        print("✓ 快速设置脚本导入成功")
        return True
    except Exception as e:
        print(f"✗ 快速设置脚本导入失败: {e}")
        return False

def test_quick_setup_functions():
    """测试快速设置功能"""
    try:
        from scripts.quick_redis_setup import (
            check_redis_service,
            check_redis_connection,
            check_redis_python_package
        )
        
        # 测试服务检查
        service_status = check_redis_service()
        print(f"✓ Redis服务检查功能正常 (状态: {service_status})")
        
        # 测试Python包检查
        package_ok = check_redis_python_package()
        print(f"✓ Redis Python包检查功能正常 (已安装: {package_ok})")
        
        # 测试连接检查
        connection_ok = check_redis_connection()
        print(f"✓ Redis连接检查功能正常 (连接成功: {connection_ok})")
        
        return True
    except Exception as e:
        print(f"✗ 快速设置功能测试失败: {e}")
        return False

def test_batch_scripts():
    """测试批处理脚本"""
    try:
        scripts_dir = Path("scripts")
        batch_scripts = [
            scripts_dir / "install_redis.bat",
            scripts_dir / "check_redis.bat"
        ]
        
        all_exist = all(script.exists() for script in batch_scripts)
        if all_exist:
            print("✓ 批处理脚本文件存在")
            
            # 检查脚本内容
            for script in batch_scripts:
                with open(script, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if 'python' in content.lower():
                        print(f"✓ {script.name} 内容正确")
                    else:
                        print(f"✗ {script.name} 内容可能有问题")
                        return False
            
            return True
        else:
            print("✗ 部分批处理脚本文件不存在")
            return False
            
    except Exception as e:
        print(f"✗ 批处理脚本测试失败: {e}")
        return False

def test_documentation():
    """测试文档文件"""
    try:
        doc_file = Path("scripts/README_Redis_Install.md")
        if doc_file.exists():
            with open(doc_file, 'r', encoding='utf-8') as f:
                content = f.read()
                if len(content) > 1000 and 'Redis' in content:
                    print("✓ Redis安装文档存在且内容完整")
                    return True
                else:
                    print("✗ Redis安装文档内容不完整")
                    return False
        else:
            print("✗ Redis安装文档不存在")
            return False
    except Exception as e:
        print(f"✗ 文档测试失败: {e}")
        return False

def run_all_tests():
    """运行所有测试"""
    print("="*60)
    print("Redis安装脚本功能测试")
    print("="*60)
    
    tests = [
        ("RedisInstaller导入", test_redis_installer_import),
        ("RedisInstaller初始化", test_redis_installer_initialization),
        ("管理员权限检查", test_admin_privileges_check),
        ("Redis检测功能", test_redis_detection),
        ("配置文件生成", test_config_generation),
        ("管理脚本创建", test_script_creation),
        ("快速设置脚本导入", test_quick_setup_import),
        ("快速设置功能", test_quick_setup_functions),
        ("批处理脚本", test_batch_scripts),
        ("文档文件", test_documentation),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n测试: {test_name}")
        print("-" * 40)
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"✗ 测试执行失败: {e}")
            results.append((test_name, False))
    
    # 显示测试结果汇总
    print("\n" + "="*60)
    print("测试结果汇总")
    print("="*60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{test_name:<20} {status}")
        if result:
            passed += 1
    
    print(f"\n总计: {passed}/{total} 个测试通过")
    
    if passed == total:
        print("🎉 所有测试都通过了!")
        print("Redis安装脚本功能正常，可以安全使用")
    else:
        print("⚠ 部分测试失败")
        print("请检查失败的测试项目")
    
    return passed == total

def main():
    """主函数"""
    try:
        success = run_all_tests()
        
        if success:
            print("\n✅ 所有功能测试通过")
            print("可以安全使用Redis安装脚本")
        else:
            print("\n❌ 部分功能测试失败")
            print("建议检查失败的功能模块")
        
        return success
        
    except KeyboardInterrupt:
        print("\n\n测试被用户取消")
        return False
    except Exception as e:
        print(f"\n测试过程中出现错误: {e}")
        return False

if __name__ == "__main__":
    success = main()
    input("\n按回车键退出...")
    sys.exit(0 if success else 1)
