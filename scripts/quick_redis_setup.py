#!/usr/bin/env python3
"""
快速Redis环境检查和设置脚本
用于快速检查和修复Redis环境问题

使用方法:
python scripts/quick_redis_setup.py
"""

import os
import sys
import subprocess
import time
from pathlib import Path

def check_redis_service():
    """检查Redis服务状态"""
    try:
        result = subprocess.run(['sc', 'query', 'Redis'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            if 'RUNNING' in result.stdout:
                return 'running'
            elif 'STOPPED' in result.stdout:
                return 'stopped'
            else:
                return 'unknown'
        return 'not_installed'
    except:
        return 'error'

def check_redis_connection():
    """检查Redis连接"""
    try:
        # 尝试使用redis-cli
        result = subprocess.run(['redis-cli', 'ping'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0 and 'PONG' in result.stdout:
            return True
    except:
        pass
    
    # 尝试使用Python redis库
    try:
        import redis
        r = redis.Redis(host='127.0.0.1', port=6379, db=0, 
                       socket_connect_timeout=2, socket_timeout=2)
        r.ping()
        return True
    except:
        pass
    
    return False

def start_redis_service():
    """启动Redis服务"""
    try:
        result = subprocess.run(['sc', 'start', 'Redis'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✓ Redis服务启动成功")
            time.sleep(3)  # 等待服务启动
            return True
        else:
            print(f"✗ Redis服务启动失败: {result.stderr}")
            return False
    except Exception as e:
        print(f"✗ 启动Redis服务时出错: {e}")
        return False

def install_redis_python_package():
    """安装Redis Python包"""
    try:
        print("正在安装Redis Python包...")
        result = subprocess.run([sys.executable, '-m', 'pip', 'install', 'redis>=4.5.4'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✓ Redis Python包安装成功")
            return True
        else:
            print(f"✗ Redis Python包安装失败: {result.stderr}")
            return False
    except Exception as e:
        print(f"✗ 安装Redis Python包时出错: {e}")
        return False

def check_redis_python_package():
    """检查Redis Python包"""
    try:
        import redis
        print(f"✓ Redis Python包已安装 (版本: {redis.__version__})")
        return True
    except ImportError:
        print("✗ Redis Python包未安装")
        return False

def test_woniunote_redis_config():
    """测试WoniuNote Redis配置"""
    try:
        # 尝试导入项目的Redis连接函数
        sys.path.insert(0, str(Path.cwd()))
        from woniunote.common.redisdb import redis_connect
        
        redis_client = redis_connect()
        if redis_client:
            redis_client.ping()
            print("✓ WoniuNote Redis配置测试成功")
            return True
        else:
            print("✗ WoniuNote Redis连接失败")
            return False
    except Exception as e:
        print(f"✗ WoniuNote Redis配置测试失败: {e}")
        return False

def main():
    """主函数"""
    print("="*60)
    print("WoniuNote Redis 环境快速检查工具")
    print("="*60)
    
    # 检查Redis Python包
    print("\n1. 检查Redis Python包...")
    redis_package_ok = check_redis_python_package()
    if not redis_package_ok:
        if input("是否安装Redis Python包? (y/n): ").lower() == 'y':
            redis_package_ok = install_redis_python_package()
    
    # 检查Redis服务
    print("\n2. 检查Redis服务状态...")
    service_status = check_redis_service()
    print(f"Redis服务状态: {service_status}")
    
    if service_status == 'not_installed':
        print("✗ Redis服务未安装")
        print("请运行完整安装脚本: python scripts/install_redis_windows.py")
        return False
    elif service_status == 'stopped':
        print("Redis服务已停止，尝试启动...")
        if not start_redis_service():
            return False
    elif service_status == 'running':
        print("✓ Redis服务正在运行")
    
    # 检查Redis连接
    print("\n3. 检查Redis连接...")
    connection_ok = check_redis_connection()
    if connection_ok:
        print("✓ Redis连接测试成功")
    else:
        print("✗ Redis连接测试失败")
        print("请检查Redis服务是否正常运行")
        return False
    
    # 测试WoniuNote配置
    print("\n4. 测试WoniuNote Redis配置...")
    woniunote_ok = test_woniunote_redis_config()
    
    # 显示结果
    print("\n" + "="*60)
    print("检查结果汇总:")
    print("="*60)
    print(f"Redis Python包: {'✓' if redis_package_ok else '✗'}")
    print(f"Redis服务: {'✓' if service_status == 'running' else '✗'}")
    print(f"Redis连接: {'✓' if connection_ok else '✗'}")
    print(f"WoniuNote配置: {'✓' if woniunote_ok else '✗'}")
    
    if all([redis_package_ok, service_status == 'running', connection_ok, woniunote_ok]):
        print("\n🎉 Redis环境配置完全正常!")
        print("WoniuNote缓存功能可以正常使用")
        
        # 显示连接信息
        print("\n连接信息:")
        print("  主机: 127.0.0.1")
        print("  端口: 6379")
        print("  数据库: 0")
        
        return True
    else:
        print("\n⚠ Redis环境存在问题")
        print("建议运行完整安装脚本: python scripts/install_redis_windows.py")
        return False

if __name__ == "__main__":
    try:
        success = main()
        if not success:
            print("\n如需完整安装Redis，请运行:")
            print("python scripts/install_redis_windows.py")
        
        input("\n按回车键退出...")
        
    except KeyboardInterrupt:
        print("\n\n检查被用户取消")
    except Exception as e:
        print(f"\n检查过程中出现错误: {e}")
