#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
WoniuNote 测试执行脚本

此脚本负责:
1. 启动Flask服务器
2. 运行所有测试
3. 关闭服务器
4. 报告测试结果

使用方法:
    python run_tests.py [测试路径]
    
参数:
    测试路径: 可选，指定要运行的测试文件或目录，默认运行所有测试
"""

import os
import sys
import time
import logging
import argparse
import subprocess
import glob
import atexit
import platform
import signal
import threading
import psutil
import pytest
import requests
from requests.exceptions import RequestException

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)
logger = logging.getLogger("test_runner")

# 全局变量
flask_process = None
server_port = 5001
base_url = f"http://localhost:{server_port}"
output_thread = None
stop_event = threading.Event()
SERVER_START_TIMEOUT = 15  # 服务器启动超时时间（秒）

# 配置
project_root = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
app_launcher = os.path.join(project_root, "tests", "utils", "app_launcher.py")

# 获取Python解释器路径
try:
    python_executable = sys.executable
    if not os.path.exists(python_executable):
        # 如果当前解释器路径不存在，尝试使用系统默认的python
        python_executable = "python"
        logger.warning(f"当前Python解释器路径不存在，使用系统默认Python: {python_executable}")
except Exception as e:
    python_executable = "python"
    logger.error(f"获取Python解释器路径时出错: {e}")

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='运行WoniuNote测试')
    parser.add_argument('test_path', nargs='?', help='指定要运行的测试文件或目录路径', default=None)
    parser.add_argument('--no-server', action='store_true', help='不启动新的Flask服务器，使用已有的')
    parser.add_argument('--verbose', '-v', action='store_true', help='显示详细输出')
    parser.add_argument('--port', type=int, default=5001, help='指定Flask服务器端口')
    parser.add_argument('--timeout', type=int, default=30, help='等待服务器启动的超时秒数')
    parser.add_argument('--unit-only', action='store_true', help='只运行单元测试，跳过所有浏览器测试')
    parser.add_argument('--continue-on-failure', action='store_true', help='即使测试失败也继续运行其他测试')
    return parser.parse_args()

def kill_process_on_port(port):
    """杀死占用指定端口的进程"""
    try:
        # 使用操作系统命令查找并终止进程
        if platform.system() == "Windows":
            # Windows下使用netstat找到占用端口的进程
            try:
                # 使用netstat查找占用端口的进程
                netstat_cmd = subprocess.run(
                    f"netstat -ano | findstr :{port}", 
                    shell=True, 
                    capture_output=True, 
                    text=True
                )
                
                if netstat_cmd.returncode == 0 and netstat_cmd.stdout.strip():
                    # 解析输出，找到PID
                    for line in netstat_cmd.stdout.strip().split('\n'):
                        parts = [p for p in line.split() if p]
                        if len(parts) >= 5 and "LISTENING" in line:
                            pid = int(parts[4])
                            logger.info(f"找到占用端口 {port} 的进程: PID={pid}")
                            
                            # 使用taskkill终止进程
                            try:
                                kill_cmd = subprocess.run(
                                    f"taskkill /F /PID {pid}", 
                                    shell=True, 
                                    capture_output=True, 
                                    text=True
                                )
                                if kill_cmd.returncode == 0:
                                    logger.info(f"已终止进程 PID={pid}")
                                else:
                                    logger.warning(f"终止进程失败: {kill_cmd.stderr}")
                            except Exception as e:
                                logger.error(f"终止进程时出错: {e}")
            except Exception as e:
                logger.error(f"使用netstat查找进程时出错: {e}")
        else:
            # Linux/Mac下使用lsof找到占用端口的进程
            try:
                lsof_cmd = subprocess.run(
                    f"lsof -i:{port} -t", 
                    shell=True, 
                    capture_output=True, 
                    text=True
                )
                if lsof_cmd.returncode == 0 and lsof_cmd.stdout.strip():
                    pids = lsof_cmd.stdout.strip().split('\n')
                    for pid in pids:
                        if pid.strip():
                            logger.info(f"找到占用端口 {port} 的进程: PID={pid}")
                            try:
                                kill_cmd = subprocess.run(
                                    f"kill -9 {pid}", 
                                    shell=True, 
                                    capture_output=True, 
                                    text=True
                                )
                                if kill_cmd.returncode == 0:
                                    logger.info(f"已终止进程 PID={pid}")
                                else:
                                    logger.warning(f"终止进程失败: {kill_cmd.stderr}")
                            except Exception as e:
                                logger.error(f"终止进程时出错: {e}")
            except Exception as e:
                logger.error(f"使用lsof查找进程时出错: {e}")
    except Exception as e:
        logger.error(f"检查端口 {port} 占用时出错: {e}")

def is_server_running(port, timeout):
    """检查服务器是否在运行"""
    # 定义健康检查端点列表，按优先级排序
    health_endpoints = ['/health', '/test-health', '/']
    
    for endpoint in health_endpoints:
        try:
            url = f"http://localhost:{port}{endpoint}"
            logger.info(f"尝试检查端点: {url}")
            response = requests.get(url, timeout=2, verify=False)  # 禁用SSL验证，设置较短的超时时间
            
            # 记录响应状态
            logger.info(f"端点 {endpoint} 响应状态码: {response.status_code}")
            
            # 如果状态码为200，则说明服务器在运行
            if response.status_code == 200:
                return True
        except RequestException as e:
            logger.debug(f"请求 {endpoint} 失败: {e}")
            continue
    
    # 如果所有端点都检查失败，尝试检查端口是否被占用
    if platform.system() == "Windows":
        try:
            netstat_cmd = subprocess.run(
                f"netstat -ano | findstr :{port} | findstr LISTENING", 
                shell=True, 
                capture_output=True, 
                text=True
            )
            return netstat_cmd.returncode == 0 and bool(netstat_cmd.stdout.strip())
        except Exception as e:
            logger.error(f"检查端口状态时出错: {e}")
    
    return False

def stream_reader(stream, prefix, stop_event):
    """读取流中的输出并记录到日志中"""
    try:
        # 使用二进制模式读取，避免解码错误
        for raw_line in iter(stream.readline, b''):
            # 如果停止事件被设置，退出循环
            if stop_event.is_set():
                break
                
            try:
                # 尝试解码，忽略错误
                line = raw_line.decode('utf-8', errors='replace').rstrip()
                
                # 只记录非空行
                if line.strip():
                    logger.info(f"{prefix}: {line}")
                    
                    # 检查行内容是否表明服务器已启动
                    if "Running on" in line and "http://" in line:
                        logger.info(f"检测到服务器启动消息: {line}")
                        # 在这里不直接设置服务器已启动标志，因为我们有专门的健康检查
            except Exception as e:
                # 如果解码失败，记录错误并继续
                logger.error(f"解码输出时出错: {e}")
                
    except Exception as e:
        logger.error(f"读取{prefix}输出流时出错: {e}")
    finally:
        logger.debug(f"流读取线程退出: {prefix}")

def start_flask_server(port, timeout):
    """启动Flask服务器"""
    global flask_process, output_thread, stop_event
    
    # 重置停止事件
    stop_event.clear()
    
    # 确保端口没有被占用
    kill_process_on_port(port)
    
    # 设置环境变量
    env = os.environ.copy()
    env["PYTHONPATH"] = project_root
    env["FLASK_ENV"] = "testing"
    env["SERVER_PORT"] = str(port)
    
    # 构建启动命令
    cmd = [
        python_executable,
        app_launcher,
        "--port",
        str(port)
    ]
    
    logger.info(f"启动Flask服务器: {' '.join(cmd)}")
    
    try:
        # 启动Flask进程
        flask_process = subprocess.Popen(
            cmd,
            cwd=project_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
            env=env,
            shell=False,  # 避免在Windows上产生额外的cmd.exe进程
            universal_newlines=False  # 避免解码错误
        )
        
        # 记录进程ID以便后续清理
        if flask_process and flask_process.pid:
            logger.info(f"Flask进程ID: {flask_process.pid}")
        else:
            logger.error("无法获取Flask进程ID")
            return False
        
        # 启动线程来处理输出
        output_thread = threading.Thread(
            target=stream_reader,
            args=(flask_process.stdout, "Flask", stop_event),
            daemon=True
        )
        output_thread.start()
        
        # 等待服务器启动
        attempts = 0
        max_attempts = timeout * 2  # 增加最大尝试次数，每次睡眠0.5秒，所以乘以2
        server_started = False
        
        logger.info(f"等待Flask服务器启动，超时时间: {timeout}秒...")
        
        start_time = time.time()
        while attempts < max_attempts:
            attempts += 1
            
            # 检查是否已超过超时时间
            elapsed_time = time.time() - start_time
            if elapsed_time > timeout:
                # 在超时前，尝试检查一次端口是否被占用，可能服务器已启动但健康检查未响应
                port_status = check_port_status(port)
                if port_status:
                    logger.info(f"检测到端口 {port} 已被占用，确认服务器已启动")
                    server_started = True
                    break
                
                logger.error(f"严格超时：Flask服务器在 {timeout} 秒内未通过健康检查，但将继续尝试10秒...")
                # 我们不立即失败，给服务器多一点时间
                timeout += 10
            
            # 检查进程是否仍在运行
            if flask_process.poll() is not None:
                logger.error(f"Flask服务器进程意外退出，退出代码: {flask_process.poll()}")
                break
            
            # 检查服务器是否运行
            if is_server_running(port, timeout):
                server_started = True
                logger.info(f"Flask服务器已启动，运行在 http://localhost:{port}")
                break
            
            # 更频繁地报告状态
            if attempts % 4 == 0:
                remaining = max(0, timeout - elapsed_time)
                logger.info(f"等待服务器启动... ({attempts}/{max_attempts}), 剩余时间: {remaining:.1f}秒")
                # 每隔几次尝试再次检查端口状态
                port_status = check_port_status(port)
                if port_status:
                    logger.info(f"检测到端口 {port} 已被占用，但健康检查尚未通过")
            
            time.sleep(0.5)  # 减少睡眠时间，更快地检测服务器状态
        
        if not server_started:
            logger.error(f"Flask服务器启动失败(已等待{timeout}秒)")
            stop_flask_server()
            return False
            
        return True
    except Exception as e:
        logger.exception(f"启动Flask服务器时出错: {e}")
        stop_flask_server()
        return False

def check_port_status(port):
    """检查端口是否被占用"""
    try:
        if platform.system() == "Windows":
            netstat_cmd = subprocess.run(
                f"netstat -ano | findstr :{port} | findstr LISTENING", 
                shell=True, 
                capture_output=True, 
                text=True
            )
            return netstat_cmd.returncode == 0 and bool(netstat_cmd.stdout.strip())
        else:
            # Linux/Mac
            lsof_cmd = subprocess.run(
                f"lsof -i:{port} -t", 
                shell=True, 
                capture_output=True, 
                text=True
            )
            return lsof_cmd.returncode == 0 and bool(lsof_cmd.stdout.strip())
    except Exception as e:
        logger.error(f"检查端口状态时出错: {e}")
        return False

def stop_flask_server():
    """停止Flask服务器"""
    global flask_process, output_thread, stop_event
    
    if flask_process is None:
        return
    
    logger.info("停止Flask服务器...")
    
    # 设置停止事件，通知所有线程退出
    stop_event.set()
    
    try:
        # 在Windows上使用taskkill确保进程被终止
        if platform.system() == "Windows" and flask_process.pid:
            try:
                # 确保进程及其子进程被终止
                subprocess.run(
                    f"taskkill /F /T /PID {flask_process.pid}", 
                    shell=True, 
                    capture_output=True, 
                    text=True
                )
                logger.info(f"使用taskkill终止进程 {flask_process.pid}")
            except Exception as e:
                logger.error(f"使用taskkill终止进程时出错: {e}")
        else:
            # 非Windows平台使用terminate和kill
            try:
                if flask_process.poll() is None:  # 如果进程仍在运行
                    flask_process.terminate()
                    try:
                        flask_process.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        flask_process.kill()
                        flask_process.wait(timeout=2)
            except Exception as e:
                logger.error(f"终止Flask进程时出错: {e}")
        
        # 关闭流
        if flask_process and flask_process.stdout:
            try:
                flask_process.stdout.close()
            except:
                pass
                
        # 确保端口没有被占用
        kill_process_on_port(server_port)
        
        logger.info("Flask服务器已停止")
            
    except Exception as e:
        logger.error(f"停止Flask服务器时出错: {e}")
    finally:
        # 清空进程引用
        flask_process = None

def cleanup():
    """清理所有资源"""
    logger.info("清理资源...")
    
    # 停止Flask服务器
    stop_flask_server()
    
    # 确保端口没有被占用
    kill_process_on_port(server_port)
    
    # 清空全局变量
    global flask_process, output_thread
    flask_process = None
    output_thread = None
    
    logger.info("清理完成")

def collect_test_files(test_path=None):
    """收集测试文件"""
    if test_path:
        # 如果指定了路径
        if os.path.isfile(test_path):
            # 如果是文件，直接返回
            return [os.path.abspath(test_path)]
        elif os.path.isdir(test_path):
            # 如果是目录，递归收集目录中的所有测试文件
            files = []
            for root, _, filenames in os.walk(test_path):
                for filename in filenames:
                    if filename.startswith("test_") and filename.endswith(".py"):
                        files.append(os.path.abspath(os.path.join(root, filename)))
            return files
        else:
            # 如果是通配符模式，使用glob收集
            if '*' in test_path:
                files = glob.glob(test_path)
                return [os.path.abspath(f) for f in files if os.path.isfile(f)]
            else:
                logger.error(f"无效的测试路径: {test_path}")
                return []
    else:
        # 如果没有指定路径，递归收集tests目录下的所有测试文件
        test_dir = os.path.abspath(os.path.dirname(__file__))
        files = []
        for root, _, filenames in os.walk(test_dir):
            for filename in filenames:
                if filename.startswith("test_") and filename.endswith(".py"):
                    files.append(os.path.abspath(os.path.join(root, filename)))
        logger.info(f"发现 {len(files)} 个测试文件")
        return files

def run_tests(args):
    """运行测试"""
    test_files = collect_test_files()
    logger.info(f"发现 {len(test_files)} 个测试文件")
    
    server_process = None
    
    # 如果指定了只运行单元测试
    if args.unit_only:
        logger.info("仅运行单元测试，跳过所有浏览器测试")
        # 设置单元测试目录
        unit_test_dirs = [
            os.path.join(os.path.dirname(__file__), "health"),
            os.path.join(os.path.dirname(__file__), "utils")
        ]
        
        # 收集单元测试文件
        unit_test_files = []
        for directory in unit_test_dirs:
            if os.path.exists(directory):
                for root, _, files in os.walk(directory):
                    for file in files:
                        if file.startswith("test_") and file.endswith(".py"):
                            unit_test_files.append(os.path.join(root, file))
        
        # 添加特定的基本测试文件
        basic_test_files = [
            os.path.join(os.path.dirname(__file__), "functional", "article", "test_article_basic.py")
        ]
        for test_file in basic_test_files:
            if os.path.exists(test_file):
                unit_test_files.append(test_file)
        
        # 运行单元测试
        test_files = unit_test_files
        
    # 启动服务器 (如果需要)
    if not args.no_server:
        server_process = start_flask_server(args.port, args.timeout)
        
        if not is_server_running(args.port, args.timeout):
            logger.error(f"无法启动Flask服务器或连接到服务器")
            stop_flask_server()
            sys.exit(1)
    else:
        logger.info("跳过Flask服务器启动，使用现有服务器")
        # 确认服务器是否运行
        if not is_server_running(args.port, args.timeout):
            logger.warning(f"警告: 服务器似乎没有运行在 http://localhost:{args.port}")
    
    # 构建pytest命令参数
    pytest_args = ["-v"]
    
    # 添加详细选项
    if args.verbose:
        pytest_args.append("-v")
    
    # 运行测试
    success = True
    for test_file in test_files:
        logger.info(f"运行测试: {test_file}")
        file_args = ["-v", test_file]
        
        if args.unit_only and not any(os.path.normpath(test_file).startswith(os.path.normpath(d)) for d in unit_test_dirs):
            # 对于函数测试，确保只运行非浏览器测试
            file_args.extend(["-m", "not browser"])
        
        result = subprocess.run([sys.executable, "-m", "pytest"] + file_args)
        
        if result.returncode != 0:
            logger.error(f"测试文件 {test_file} 失败，退出代码: {result.returncode}")
            success = False
            if not args.continue_on_failure:
                break
    
    if success:
        logger.info("所有测试通过!")
    else:
        logger.error("一些测试失败")
    
    stop_flask_server()
    return success

def main():
    """主函数"""
    try:
        # 注册退出时的清理函数
        atexit.register(cleanup)
        
        # 设置信号处理程序
        if platform.system() != "Windows":
            # 仅在非Windows平台设置信号处理
            signal.signal(signal.SIGINT, lambda sig, frame: sys.exit(130))
            signal.signal(signal.SIGTERM, lambda sig, frame: sys.exit(143))
        
        # 解析命令行参数
        args = parse_args()
        
        # 运行测试
        success = run_tests(args)
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        logger.info("测试被用户中断")
        # 确保在键盘中断时也进行清理
        cleanup()
        return 130
    except Exception as e:
        logger.exception(f"测试执行时发生未处理异常: {e}")
        # 确保在异常情况下也进行清理
        cleanup()
        return 1
        
if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
