#!/usr/bin/env python3
"""
Redis问题修复脚本
解决"Redis客户端未配置，Redis缓存功能不可用"的问题
"""

import os
import sys
import subprocess
import time
import signal
from pathlib import Path

def start_redis_manually():
    """手动启动Redis服务器"""
    redis_exe = Path("C:/Program Files/Redis/redis-server.exe")
    
    if not redis_exe.exists():
        print("❌ Redis未安装，请先运行安装脚本")
        return None
    
    print("正在启动Redis服务器...")
    
    try:
        # 启动Redis服务器
        process = subprocess.Popen([
            str(redis_exe),
            "--port", "6379",
            "--bind", "127.0.0.1",
            "--save", "",  # 禁用持久化避免权限问题
            "--appendonly", "no"
        ], 
        stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE,
        creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
        )
        
        # 等待启动
        time.sleep(3)
        
        if process.poll() is None:  # 进程仍在运行
            print("✓ Redis服务器启动成功")
            return process
        else:
            stdout, stderr = process.communicate()
            print(f"❌ Redis启动失败: {stderr.decode()}")
            return None
            
    except Exception as e:
        print(f"❌ 启动Redis时出错: {e}")
        return None

def test_redis_connection():
    """测试Redis连接"""
    try:
        import redis
        r = redis.Redis(host='127.0.0.1', port=6379, db=0, 
                       socket_connect_timeout=2, socket_timeout=2)
        r.ping()
        print("✓ Redis连接测试成功")
        return True
    except Exception as e:
        print(f"❌ Redis连接测试失败: {e}")
        return False

def test_woniunote_redis():
    """测试WoniuNote Redis配置"""
    try:
        sys.path.insert(0, str(Path.cwd()))
        from woniunote.common.redisdb import redis_connect
        
        redis_client = redis_connect()
        if redis_client:
            redis_client.ping()
            print("✓ WoniuNote Redis配置测试成功")
            return True
        else:
            print("❌ WoniuNote Redis连接失败")
            return False
    except Exception as e:
        print(f"❌ WoniuNote Redis配置测试失败: {e}")
        return False

def main():
    """主函数"""
    print("="*60)
    print("Redis问题修复工具")
    print("="*60)
    
    # 检查Redis是否已在运行
    if test_redis_connection():
        print("Redis已在运行，测试WoniuNote配置...")
        if test_woniunote_redis():
            print("\n🎉 Redis环境正常，缓存功能可用!")
            return True
        else:
            print("\n⚠ Redis运行正常，但WoniuNote配置有问题")
            return False
    
    print("Redis未运行，尝试启动...")
    
    # 启动Redis
    redis_process = start_redis_manually()
    if not redis_process:
        print("\n❌ 无法启动Redis服务器")
        print("建议:")
        print("1. 以管理员身份重新运行安装脚本")
        print("2. 检查防火墙和杀毒软件设置")
        print("3. 手动下载Redis并解压到C:\\redis目录")
        return False
    
    # 测试连接
    print("\n测试Redis连接...")
    if not test_redis_connection():
        print("❌ Redis启动了但无法连接")
        redis_process.terminate()
        return False
    
    # 测试WoniuNote配置
    print("测试WoniuNote配置...")
    if test_woniunote_redis():
        print("\n🎉 Redis问题已解决!")
        print("Redis服务器正在运行，缓存功能现在可用")
        print("\n注意: Redis在新的控制台窗口中运行")
        print("关闭该窗口将停止Redis服务")
        
        print("\n要让Redis持续运行，请:")
        print("1. 保持Redis控制台窗口打开")
        print("2. 或以管理员身份重新安装Redis服务")
        
        return True
    else:
        print("\n⚠ Redis运行正常，但WoniuNote配置仍有问题")
        print("请检查项目配置文件")
        return False

if __name__ == "__main__":
    try:
        success = main()
        
        if success:
            print("\n✅ Redis缓存功能现已可用")
        else:
            print("\n❌ 仍存在Redis配置问题")
        
        input("\n按回车键退出...")
        
    except KeyboardInterrupt:
        print("\n\n操作被用户取消")
    except Exception as e:
        print(f"\n修复过程中出现错误: {e}")

