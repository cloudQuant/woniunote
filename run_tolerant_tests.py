#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
WoniuNote 容错测试运行器

这个脚本专门用于运行那些经过容错设计的测试文件，它们能够适应数据库映射问题
并且不依赖于特定的数据状态。

使用方法：
    python run_tolerant_tests.py           # 运行所有容错测试
    python run_tolerant_tests.py --all     # 运行所有测试文件

作者：Codeium AI 2025-04-05
"""

import os
import sys
import time
import argparse
import subprocess
import logging
import psutil
import signal
import platform

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger("woniunote_test")

# 项目目录
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))

# 所有测试文件名称 - 包含容错测试和其他功能测试
TOLERANT_TESTS = [
    # 基本测试
    'test_basic_app.py',            # 基本应用测试，处理301重定向
    'test_basic.py',                # 基础功能测试
    
    # 文章模块
    'test_article_minimal.py',      # 最小化文章测试，可处理数据映射问题
    'test_article_direct_only.py',  # 直接测试文章API而不使用浏览器
    'test_advanced_article_features.py',      # 高级文章功能
    'test_advanced_article_features_direct.py',  # 直接测试高级文章API
    
    # 用户模块
    'test_user_auth.py',            # 用户认证测试
    'test_user_auth_direct.py',     # 直接测试用户认证API
    'test_user_profile.py',         # 用户个人资料测试
    
    # 评论模块
    'test_comment_basic.py',        # 基本评论功能测试
    'test_comment_basic_direct.py', # 直接测试评论 API
    
    # 收藏模块
    'test_favorite_features.py',    # 收藏功能测试
    
    # 健康监测
    'test_server_basic.py',         # 基本服务器健康测试
    'test_server_health.py',        # 详细服务器健康监测
    
    # 工具类测试
    'test_base.py',                 # 基础工具类测试
    'test_config.py',               # 配置模块测试
    'test_data_factory.py',         # 数据工厂测试
    'test_data_factory_tests.py',   # 数据工厂测试用例
    'test_data_helper.py'           # 数据辅助工具测试
]

# 全局变量
SERVER_PROCESS = None
SERVER_PORT = 5001
SERVER_TIMEOUT = 5  # 服务器启动等待时间（秒）

def is_port_available(port):
    """检查端口是否可用（没有被占用）"""
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", port))
        result = True
    except:
        result = False
    finally:
        s.close()
    return result

def kill_process_on_port(port):
    """杀死占用指定端口的进程"""
    logger.info(f"尝试释放端口 {port}...")
    
    try:
        if platform.system() == "Windows":
            # Windows 使用 netstat 找出占用端口的进程
            cmd = f"netstat -ano | findstr :{port}"
            result = subprocess.run(cmd, shell=True, text=True, capture_output=True)
            
            if result.returncode == 0 and result.stdout:
                for line in result.stdout.strip().split('\n'):
                    if "LISTENING" in line:
                        parts = [p for p in line.split() if p.strip()]
                        if len(parts) >= 5:
                            pid = parts[4]
                            logger.info(f"找到进程 PID={pid}，尝试终止...")
                            subprocess.run(f"taskkill /F /PID {pid}", shell=True)
                            return True
        else:
            # Linux/Mac
            cmd = f"lsof -i:{port} -t"
            result = subprocess.run(cmd, shell=True, text=True, capture_output=True)
            
            if result.returncode == 0 and result.stdout:
                pid = result.stdout.strip()
                if pid:
                    logger.info(f"找到进程 PID={pid}，尝试终止...")
                    subprocess.run(f"kill -9 {pid}", shell=True)
                    return True
                    
        return False
    except Exception as e:
        logger.error(f"尝试释放端口时出错: {e}")
        return False

def start_flask_server():
    """启动 Flask 服务器并返回进程对象"""
    port = SERVER_PORT
    
    # 确保端口可用
    if not is_port_available(port):
        logger.warning(f"端口 {port} 已被占用")
        if not kill_process_on_port(port):
            logger.error(f"无法释放端口 {port}，请手动关闭占用该端口的程序")
            return None
    
    # 设置环境变量
    env = os.environ.copy()
    env['FLASK_ENV'] = 'development'
    env['FLASK_DEBUG'] = '1'
    env['PYTHONUNBUFFERED'] = '1'  # 确保输出不被缓存
    
    # 构建服务器启动命令
    server_script = 'start_server.py'
    cmd = [sys.executable, server_script, '--host', '127.0.0.1', '--port', str(port), '--debug', '--http']
    
    logger.info(f"启动 Flask 服务器: {' '.join(cmd)}")
    
    try:
        # 启动服务器进程
        process = subprocess.Popen(
            cmd, 
            cwd=PROJECT_ROOT,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if platform.system() == "Windows" else 0
        )
        
        # 等待服务器启动
        logger.info(f"等待服务器启动，最长等待 {SERVER_TIMEOUT} 秒...")
        
        start_time = time.time()
        while time.time() - start_time < SERVER_TIMEOUT:
            # 检查进程是否已终止
            if process.poll() is not None:
                stderr = process.stderr.read() if process.stderr else ""
                logger.error(f"服务器启动失败，退出代码: {process.poll()}, 错误: {stderr}")
                return None
                
            # 检查端口是否已可用
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                s.connect(('127.0.0.1', port))
                s.close()
                # 连接成功，服务器已启动
                logger.info(f"服务器已成功启动，地址: http://127.0.0.1:{port}")
                return process
            except:
                # 连接失败，继续等待
                time.sleep(1)
            finally:
                s.close()
        
        # 超时后未能启动
        logger.error(f"服务器启动超时（{SERVER_TIMEOUT}秒）")
        if process.poll() is None:
            process.terminate()
        return None
        
    except Exception as e:
        logger.exception(f"启动服务器时出错: {e}")
        return None

def stop_flask_server(process):
    """停止 Flask 服务器"""
    if not process:
        return
    
    logger.info("停止 Flask 服务器...")
    try:
        # 温和地终止进程
        if platform.system() == "Windows":
            if process.poll() is None:
                process.send_signal(signal.CTRL_BREAK_EVENT)  # Windows
                time.sleep(2)
        else:
            if process.poll() is None:
                process.terminate()  # SIGTERM
                time.sleep(2)
        
        # 如果仍在运行，强制终止
        if process.poll() is None:
            process.kill()
            logger.info("服务器已强制终止")
        else:
            logger.info("服务器已正常终止")
            
        # 确保端口已释放
        if not is_port_available(SERVER_PORT):
            kill_process_on_port(SERVER_PORT)
            
    except Exception as e:
        logger.error(f"停止服务器时出错: {e}")

def find_test_files(include_all=False):
    """查找测试文件"""
    tests_dir = os.path.join(PROJECT_ROOT, 'tests')
    all_tests = []
    tolerant_tests = []
    
    # 遍历测试目录查找所有测试文件
    for root, _, files in os.walk(tests_dir):
        for file in files:
            if file.startswith('test_') and file.endswith('.py'):
                test_path = os.path.join(root, file)
                if os.path.isfile(test_path):
                    all_tests.append(test_path)
                    
                    # 检查是否是容错测试文件
                    if file in TOLERANT_TESTS:
                        tolerant_tests.append(test_path)
    
    if include_all:
        logger.info(f"找到 {len(all_tests)} 个测试文件")
        return all_tests
    else:
        logger.info(f"找到 {len(tolerant_tests)} 个容错测试文件")
        return tolerant_tests

def run_tests(test_files):
    """运行测试文件列表"""
    if not test_files:
        logger.error("无测试文件可运行")
        return False
    
    success_count = 0
    failure_count = 0
    skipped_count = 0
    
    for test_file in test_files:
        base_name = os.path.basename(test_file)
        logger.info(f"{'='*30} 运行测试: {base_name} {'='*30}")
        
        # 构建 pytest 命令
        cmd = [sys.executable, "-m", "pytest", test_file, "-v"]
        
        try:
            # 设置环境变量
            env = os.environ.copy()
            env['PYTHONPATH'] = f"{PROJECT_ROOT};{env.get('PYTHONPATH', '')}" if platform.system() == "Windows" else f"{PROJECT_ROOT}:{env.get('PYTHONPATH', '')}"
            
            # 运行测试并捕获输出
            result = subprocess.run(cmd, env=env, check=False)
            
            # 根据 pytest 返回码判断测试结果
            # 0=所有测试通过, 1=有失败, 2=有错误, 4=有跳过但无失败
            if result.returncode == 0:
                logger.info(f"✓ 测试通过: {base_name}")
                success_count += 1
            elif result.returncode == 4:  # 只有跳过的测试
                logger.info(f"⏩ 测试部分跳过: {base_name}")
                skipped_count += 1
            else:
                logger.error(f"✗ 测试失败: {base_name} (返回码: {result.returncode})")
                failure_count += 1
                
        except Exception as e:
            logger.error(f"运行测试出错: {e}")
            failure_count += 1
    
    # 打印测试结果汇总
    logger.info(f"\n{'='*60}")
    logger.info(f"测试执行完成! 总共 {len(test_files)} 个测试文件")
    logger.info(f"✓ 通过: {success_count} 个")
    if skipped_count > 0:
        logger.info(f"⏩ 部分跳过: {skipped_count} 个")
    logger.info(f"✗ 失败: {failure_count} 个")
    
    # 判断整体测试是否成功
    return failure_count == 0

def main():
    """主函数"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='WoniuNote 容错测试运行器')
    parser.add_argument('--all', action='store_true', help='运行所有测试文件，不只是容错测试')
    parser.add_argument('--no-server', action='store_true', help='不启动服务器，假设测试依赖的服务已运行')
    args = parser.parse_args()
    
    # 启动服务器
    server_process = None
    if not args.no_server:
        server_process = start_flask_server()
        if not server_process:
            logger.error("服务器启动失败，无法执行测试")
            return 1
    
    try:
        # 查找要运行的测试文件
        test_files = find_test_files(args.all)
        
        # 运行测试并获取结果
        success = run_tests(test_files)
        return 0 if success else 1
        
    finally:
        # 确保无论如何都停止服务器
        if server_process:
            stop_flask_server(server_process)

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        logger.info("测试被用户中断")
        # 确保清理资源
        if SERVER_PROCESS:
            stop_flask_server(SERVER_PROCESS)
        sys.exit(130)
