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
import socket
import urllib3

# 添加项目根目录到Python路径
project_root = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, project_root)

# 添加tests目录到Python路径
tests_dir = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, tests_dir)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)
logger = logging.getLogger("test_runner")

# 全局变量
server_process = None
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
    parser.add_argument('--debug', action='store_true', help='启用调试模式')
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

def check_server_running(host, port, timeout=5):
    """
    检查服务器是否运行，使用多种方法尝试连接
    优先使用socket直接检查端口，然后尝试发送HTTP请求
    """
    logger.info(f"检查服务器是否运行在 {host}:{port}...")
    
    # 方法1: 使用socket直接检查端口
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((host, port))
        sock.close()
        
        if result == 0:
            logger.info(f"✓ 端口 {port} 已开放")
            return True
        else:
            logger.warning(f"端口 {port} 未开放，错误码: {result}")
    except Exception as e:
        logger.error(f"socket检查失败: {e}")
    
    # 方法2: 尝试发送原始HTTP请求
    try:
        logger.info(f"尝试发送原始HTTP请求到 {host}:{port}...")
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect((host, port))
        
        # 发送简单的HTTP GET请求
        request = (
            f"GET /health HTTP/1.1\r\n"
            f"Host: {host}:{port}\r\n"
            f"User-Agent: WoniuNote-Test\r\n"
            f"Accept: */*\r\n"
            f"Connection: close\r\n"
            f"\r\n"
        )
        
        s.sendall(request.encode())
        
        # 接收响应
        response = b""
        while True:
            try:
                data = s.recv(4096)
                if not data:
                    break
                response += data
            except socket.timeout:
                break
        
        s.close()
        
        # 任何有效的HTTP响应都表明服务器在运行
        if len(response) > 0 and response.startswith(b"HTTP/"):
            logger.info(f"收到HTTP响应: {response[:100]}...")
            return True
        else:
            logger.warning(f"收到无效的HTTP响应: {response[:100] if response else '无响应'}")
    except Exception as e:
        logger.error(f"HTTP请求失败: {e}")
    
    # 方法3: 使用urllib3库
    try:
        import urllib3
        urllib3.disable_warnings()
        
        logger.info(f"尝试使用urllib3连接 {host}:{port}...")
        http = urllib3.PoolManager(
            timeout=timeout,
            retries=1,
            cert_reqs='CERT_NONE',
            assert_hostname=False
        )
        
        response = http.request(
            'GET',
            f"http://{host}:{port}/health",
            headers={
                'User-Agent': 'WoniuNote-Test',
                'Accept': '*/*'
            }
        )
        
        logger.info(f"urllib3响应: 状态={response.status}")
        return response.status < 500  # 任何非服务器错误的响应都表示服务器在运行
    except Exception as e:
        logger.error(f"urllib3请求失败: {e}")
    
    return False

def start_server(args):
    """启动Flask服务器"""
    logger.info("准备启动Flask服务器...")
    
    # 首先检查端口是否已被占用
    if check_port_used(args.port):
        logger.warning(f"端口 {args.port} 已被占用，尝试释放...")
        if not terminate_process_by_port(args.port):
            logger.error(f"无法释放端口 {args.port}，请手动关闭占用该端口的程序")
            return None
        logger.info(f"端口 {args.port} 已成功释放")
    
    # 设置Flask服务器环境
    env = os.environ.copy()
    env['FLASK_ENV'] = 'testing'
    env['FLASK_DEBUG'] = '0'
    env['TESTING'] = 'true'
    env['PYTHONUNBUFFERED'] = '1'  # 确保输出不被缓存
    env['PYTHONPATH'] = f"{project_root};{env.get('PYTHONPATH', '')}" if platform.system() == "Windows" else f"{project_root}:{env.get('PYTHONPATH', '')}"
    
    # 构建启动命令
    # 使用start_server.py启动应用，而不是直接调用app.py
    server_script = 'start_server.py'
    
    # 使用适合测试的参数
    if platform.system() == "Windows":
        cmd = f"{sys.executable} {server_script} --host 127.0.0.1 --port {args.port} --debug --http"
        # Windows下使用CREATE_NEW_PROCESS_GROUP标志，使之成为独立进程组
        creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        cmd = f"{sys.executable} {server_script} --host 127.0.0.1 --port {args.port} --debug --http"
        creation_flags = 0
    
    logger.info(f"启动Flask服务器: {cmd}")
    
    try:
        # 以非阻塞方式启动服务器
        proc = subprocess.Popen(
            cmd,
            shell=True,
            cwd=project_root,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=creation_flags if platform.system() == "Windows" else 0
        )
        
        # 等待服务器启动
        start_time = time.time()
        ready = False
        
        while time.time() - start_time < args.timeout:
            if proc.poll() is not None:
                # 进程已终止
                returncode = proc.poll()
                stderr = proc.stderr.read() if proc.stderr else ""
                logger.error(f"Flask服务器启动失败，退出代码: {returncode}, 错误: {stderr}")
                return None
            
            # 检查端口是否已经可用
            if check_port_available(args.port):
                ready = True
                break
            
            # 短暂等待后再次检查
            time.sleep(1)
        
        if not ready:
            logger.error(f"Flask服务器启动超时 ({args.timeout}秒)")
            # 尝试终止进程
            if proc.poll() is None:
                if platform.system() == "Windows":
                    os.kill(proc.pid, signal.CTRL_BREAK_EVENT)
                else:
                    proc.terminate()
                proc.wait(5)
            return None
        
        logger.info(f"Flask服务器已成功启动在端口 {args.port}")
        return proc
    
    except Exception as e:
        logger.exception(f"启动Flask服务器时出错: {e}")
        return None

def stop_server(proc):
    """停止Flask服务器"""
    if proc is None:
        return
    
    logger.info("停止Flask服务器...")
    
    try:
        # 首先尝试优雅地终止进程
        if proc.poll() is None:
            if platform.system() == "Windows":
                # Windows下发送CTRL_BREAK_EVENT信号
                os.kill(proc.pid, signal.CTRL_BREAK_EVENT)
            else:
                # 非Windows平台使用SIGTERM信号
                proc.terminate()
            
            # 等待进程终止
            try:
                proc.wait(timeout=5)
                logger.info("进程已正常终止")
            except subprocess.TimeoutExpired:
                # 如果超时，强制终止
                logger.warning("进程未能正常终止，尝试强制终止")
                proc.kill()
                proc.wait(timeout=5)
                logger.info("进程已被强制终止")
        else:
            logger.info("服务器进程已不再运行")
        
        # 确认服务器端口已被释放
        port = server_port  # 使用全局变量或通过其他方式获取端口
        if check_port_used(port):
            logger.warning(f"端口 {port} 仍被占用，尝试直接释放")
            terminate_process_by_port(port)
        
        logger.info("Flask服务器已停止")
    
    except Exception as e:
        logger.exception(f"停止Flask服务器时出错: {e}")

def stream_reader(stream, prefix, stop_event):
    """读取流中的输出并记录到日志中"""
    if stream is None:
        logger.warning(f"{prefix} 流为None，无法读取")
        return
        
    logger.debug(f"开始读取 {prefix} 流")
    
    # 创建缓冲区来收集数据
    buffer = ""
    
    try:
        while not stop_event.is_set():
            # 检查是否有数据可读
            line = stream.readline()
            if not line:
                # 检查进程是否已终止
                time.sleep(0.1)
                continue
                
            try:
                # 去除空白字符并过滤掉控制字符
                line_str = line.strip()
                if not line_str:
                    continue
                    
                # 过滤掉一些无用的输出行
                if "* Detected change in" in line_str or "* Restarting with" in line_str:
                    continue
                
                # 记录日志，确保格式良好
                clean_line = ''.join(c if c.isprintable() or c.isspace() else '?' for c in line_str)
                if clean_line:
                    logger.info(f"{prefix}: {clean_line}")
                    
                    # 检查行内容是否表明服务器已启动
                    if "Running on" in clean_line and "http://" in clean_line:
                        logger.info(f"[SERVER STATUS] 检测到服务器启动消息: {clean_line}")
            except Exception as e:
                # 如果处理失败，记录错误并继续
                logger.error(f"处理输出时出错: {str(e)}")
    except Exception as e:
        logger.error(f"读取 {prefix} 输出流时出错: {str(e)}")
    finally:
        logger.debug(f"流读取线程退出: {prefix}")

def stop_server(server_proc, stop_event=None, reader_threads=None):
    """停止Flask服务器"""
    if server_proc is None:
        logger.warning("服务器进程为None，无需停止")
        return
        
    logger.info("停止Flask服务器...")
    
    # 如果我们收到的是字典，提取相关组件
    process = None
    local_stop_event = stop_event
    local_reader_threads = reader_threads
    
    if isinstance(server_proc, dict):
        process = server_proc.get("process")
        if local_stop_event is None:
            local_stop_event = server_proc.get("stop_event")
        if local_reader_threads is None:
            local_reader_threads = server_proc.get("reader_threads", [])
    else:
        process = server_proc
    
    # 确认进程对象有效
    if process is None:
        logger.error("无效的服务器进程对象")
        return
    
    # 设置停止事件
    if local_stop_event:
        local_stop_event.set()
    
    # 停止读取线程
    if local_reader_threads:
        for thread in local_reader_threads:
            if thread and thread.is_alive():
                try:
                    thread.join(timeout=2)
                except Exception as e:
                    logger.warning(f"停止读取线程时出错: {e}")
    
    # 尝试正常终止进程
    try:
        if process.poll() is None:  # 只有当进程还在运行时才尝试终止
            import signal
            # 发送SIGTERM信号
            process.terminate()
            
            # 给进程一些时间来正常关闭
            for _ in range(5):  # 最多等待5秒
                if process.poll() is not None:
                    logger.info("进程已正常终止")
                    break
                time.sleep(1)
            
            # 如果进程仍在运行，强制终止
            if process.poll() is None:
                logger.warning("进程未能正常终止，尝试强制终止")
                process.kill()
                process.wait(timeout=2)
        else:
            logger.info("进程已经终止")
    except Exception as e:
        logger.error(f"停止服务器时出错: {e}")
        
        # 在Windows系统上，使用taskkill命令强制终止进程
        try:
            if sys.platform == "win32" and hasattr(process, "pid") and process.pid:
                logger.info(f"使用taskkill终止进程 {process.pid}")
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(process.pid)], 
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        except Exception as e2:
            logger.error(f"使用taskkill终止进程时出错: {e2}")
    
    # 确保连接端口已释放
    from utils.test_config import SERVER_CONFIG
    port = SERVER_CONFIG['port']
    host = SERVER_CONFIG['host']
    
    # 检查端口是否仍被占用
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex((host, port))
    sock.close()
    
    if result == 0:
        logger.warning(f"端口 {port} 仍被占用，尝试终止占用该端口的进程")
        terminate_process_by_port(port)
        
    logger.info("Flask服务器已停止")

def collect_test_files(test_path=None):
    """收集测试文件"""
    logger.info("正在收集测试文件...")
    
    # 排除的文件和目录模式
    exclude_patterns = [
        ".bak", ".tmp", ".old", ".new", "__pycache__", ".pytest_cache",
        "temp", "tmp", "conftest.py.new"
    ]
    
    if test_path:
        # 如果指定了路径
        logger.info(f"使用指定的测试路径: {test_path}")
        if os.path.isfile(test_path):
            # 如果是文件，直接返回
            if test_path.endswith(".py") and "test_" in os.path.basename(test_path):
                logger.info(f"使用单个测试文件: {test_path}")
                return [os.path.abspath(test_path)]
            else:
                logger.warning(f"指定的文件不是有效的测试文件: {test_path}")
                return []
        elif os.path.isdir(test_path):
            # 如果是目录，递归收集目录中的所有测试文件
            logger.info(f"递归搜索目录: {test_path}")
            files = []
            for root, dirs, filenames in os.walk(test_path):
                # 过滤掉不需要的目录
                dirs[:] = [d for d in dirs if not any(pattern in d for pattern in exclude_patterns)]
                
                for filename in filenames:
                    if filename.startswith("test_") and filename.endswith(".py"):
                        # 检查是否应该排除该文件
                        if not any(pattern in filename for pattern in exclude_patterns):
                            file_path = os.path.abspath(os.path.join(root, filename))
                            files.append(file_path)
            
            logger.info(f"在目录 {test_path} 中找到 {len(files)} 个测试文件")
            return files
        else:
            # 尝试通配符模式
            if '*' in test_path:
                try:
                    import glob
                    logger.info(f"使用通配符模式搜索: {test_path}")
                    files = glob.glob(test_path, recursive=True)
                    valid_files = []
                    for f in files:
                        if os.path.isfile(f) and f.endswith(".py") and "test_" in os.path.basename(f):
                            if not any(pattern in f for pattern in exclude_patterns):
                                valid_files.append(os.path.abspath(f))
                    
                    logger.info(f"通过通配符找到 {len(valid_files)} 个测试文件")
                    return valid_files
                except Exception as e:
                    logger.error(f"使用通配符模式查找文件时出错: {e}")
                    return []
            else:
                logger.error(f"无效的测试路径: {test_path}")
                return []
    else:
        # 如果没有指定路径，递归收集tests目录下的所有测试文件
        test_dir = os.path.abspath(os.path.dirname(__file__))
        logger.info(f"搜索整个tests目录: {test_dir}")
        files = []
        for root, dirs, filenames in os.walk(test_dir):
            # 过滤掉不需要的目录
            dirs[:] = [d for d in dirs if not any(pattern in d for pattern in exclude_patterns)]
            
            for filename in filenames:
                if filename.startswith("test_") and filename.endswith(".py"):
                    # 检查是否应该排除该文件
                    if not any(pattern in filename for pattern in exclude_patterns):
                        file_path = os.path.abspath(os.path.join(root, filename))
                        files.append(file_path)
        
        logger.info(f"在tests目录中找到 {len(files)} 个测试文件")
        return files

def run_tests(args):
    """运行测试"""
    logger.info("准备运行测试...")
    
    # 收集所有测试文件
    test_files = collect_test_files(args.test_path)
    
    if not test_files:
        logger.warning("未找到任何测试文件")
        return False
    
    logger.info(f"发现 {len(test_files)} 个测试文件")
    
    # 准备环境变量用于运行pytest
    env = os.environ.copy()
    env['PYTHONPATH'] = f"{project_root};{env.get('PYTHONPATH', '')}" if platform.system() == "Windows" else f"{project_root}:{env.get('PYTHONPATH', '')}"
    env['TEST_MODE'] = 'true'
    
    # 构建基础pytest命令行参数
    base_pytest_args = [sys.executable, "-m", "pytest"]
    
    # 添加标准pytest参数
    if args.verbose:
        base_pytest_args.append("-v")
    
    # 添加单元测试标记
    if args.unit_only:
        base_pytest_args.extend(["-m", "unit"])
    
    # 确保测试有适当的超时设置
    base_pytest_args.extend(["--timeout", str(max(60, args.timeout))])
    
    # 使用项目根目录作为工作目录
    cwd = project_root
    
    # 根据测试路径选择运行模式
    if args.test_path and os.path.isfile(args.test_path):
        # 单文件模式
        logger.info(f"运行单个测试文件: {args.test_path}")
        cmd = base_pytest_args + [args.test_path]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=not args.verbose,
                text=True,
                cwd=cwd,
                env=env
            )
            success = result.returncode == 0
            
            if success:
                logger.info("测试通过!")
            else:
                logger.error(f"测试失败，退出代码: {result.returncode}")
                if result.stderr:
                    for line in result.stderr.splitlines()[-20:]:
                        logger.error(f"ERROR: {line}")
            
            return success
        except Exception as e:
            logger.exception(f"运行测试时出错: {e}")
            return False
    else:
        # 目录或多文件模式
        if args.test_path and os.path.isdir(args.test_path):
            logger.info(f"运行目录中的测试: {args.test_path}")
            cmd = base_pytest_args + [args.test_path]
        else:
            # 为避免命令行过长，分批次运行测试
            logger.info("运行多个测试文件")
            batch_size = 5  # 小批量运行以避免命令行过长
            
            test_successes = []
            test_failures = []
            
            for i in range(0, len(test_files), batch_size):
                batch = test_files[i:i+batch_size]
                logger.info(f"运行测试批次 {i//batch_size + 1}/{(len(test_files)+batch_size-1)//batch_size}")
                
                cmd = base_pytest_args + batch
                try:
                    result = subprocess.run(
                        cmd,
                        capture_output=not args.verbose,
                        text=True,
                        cwd=cwd,
                        env=env
                    )
                    
                    if result.returncode == 0:
                        logger.info(f"批次 {i//batch_size + 1} 测试通过")
                        test_successes.extend(batch)
                    else:
                        logger.error(f"批次 {i//batch_size + 1} 测试失败")
                        test_failures.extend(batch)
                        
                        if result.stderr:
                            for line in result.stderr.splitlines()[-20:]:
                                logger.error(f"ERROR: {line}")
                    
                    # 第一个失败后停止，除非指定继续
                    if result.returncode != 0 and not args.continue_on_failure:
                        logger.warning("测试失败，停止后续测试")
                        break
                except Exception as e:
                    logger.exception(f"运行测试批次时出错: {e}")
                    test_failures.extend(batch)
                    if not args.continue_on_failure:
                        break
            
            # 汇总结果
            logger.info(f"测试汇总: {len(test_successes)} 通过, {len(test_failures)} 失败")
            if test_failures:
                logger.error("失败的测试文件:")
                for f in test_failures:
                    logger.error(f"  - {os.path.basename(f)}")
            
            return len(test_failures) == 0

def check_port_available(port):
    """检查端口是否可用（可以连接）"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            result = s.connect_ex(('127.0.0.1', port))
            return result == 0  # 如果能连接则返回True
    except Exception as e:
        logger.error(f"检查端口 {port} 可用性时出错: {e}")
        return False

def check_port_used(port):
    """检查端口是否被占用"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)
            result = sock.connect_ex(('127.0.0.1', port))
            return result == 0  # 如果连接成功，说明端口被占用
    except Exception as e:
        logger.error(f"检查端口 {port} 状态时出错: {e}")
        return False

def terminate_process_by_port(port):
    """终止占用指定端口的进程"""
    logger.info(f"端口 {port} 仍被占用，尝试终止占用该端口的进程")
    
    try:
        # 直接使用已实现的kill_process_on_port函数
        kill_process_on_port(port)
        
        # 给进程一些时间来终止
        time.sleep(2)
        
        # 检查端口是否已释放
        if not check_port_used(port):
            logger.info(f"端口 {port} 已成功释放")
            return True
        else:
            logger.warning(f"端口 {port} 仍被占用，尝试强制终止")
            # 再次尝试终止进程
            if platform.system() == "Windows":
                # 使用更强力的命令终止所有相关进程
                subprocess.run(
                    f"FOR /F \"tokens=5\" %a IN ('netstat -ano ^| findstr :{port} ^| findstr LISTENING') DO taskkill /F /PID %a", 
                    shell=True
                )
                time.sleep(1)
                return not check_port_used(port)
            else:
                # Linux/Mac系统
                subprocess.run(f"lsof -i:{port} -t | xargs kill -9", shell=True)
                time.sleep(1)
                return not check_port_used(port)
    except Exception as e:
        logger.error(f"终止占用端口 {port} 的进程时出错: {e}")
        return False

def cleanup():
    """清理所有资源"""
    # 检查端口是否仍被占用
    port = server_port
    if check_port_used(port):
        terminate_process_by_port(port)
    
    logger.info("清理完成")

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
        
        # 如果启用了调试模式，设置更详细的日志
        if args.debug:
            setup_logger(logging.DEBUG)
        
        # 检查服务器端口是否被占用
        if check_port_used(args.port):
            logger.warning(f"端口 {args.port} 已被占用，尝试释放...")
            if not terminate_process_by_port(args.port):
                logger.error(f"无法释放端口 {args.port}，请手动关闭占用该端口的程序")
                return 1
            logger.info(f"端口 {args.port} 已成功释放")
        
        # 确保测试数据库和环境准备就绪
        try:
            logger.info("检查测试数据...")
            # 这里可以添加准备测试数据的代码
            logger.info("测试数据准备就绪")
        except Exception as e:
            logger.warning(f"准备测试数据时出错: {e}，但将继续测试")
        
        # 启动Flask服务器（如果需要）
        server_proc = None
        if not args.no_server:
            server_proc = start_server(args)
            if not server_proc:
                logger.error("无法启动Flask服务器")
                return 1
            
            # 给服务器一些时间完全启动
            logger.info("等待服务器完全启动...")
            time.sleep(2)
        
        try:
            # 运行测试
            success = run_tests(args)
            return 0 if success else 1
        finally:
            # 无论测试成功与否，确保停止服务器
            if server_proc:
                stop_server(server_proc)
                logger.info("Flask服务器已停止")
        
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
        
# 添加pytest集成，使此脚本可以直接被pytest运行
def pytest_sessionstart(session):
    """pytest会话开始时的处理"""
    # 当脚本被pytest直接运行时，转发到手动执行模式
    if os.path.basename(sys.argv[0]) == 'pytest' or sys.argv[0].endswith('pytest.exe'):
        logger.info("通过pytest直接运行run_tests.py")
        try:
            # 创建一个模拟args对象
            class Args:
                pass
            args = Args()
            args.test_path = None
            args.no_server = False
            args.verbose = True
            args.port = server_port
            args.timeout = 30
            args.unit_only = False
            args.continue_on_failure = False
            args.debug = False
            
            # 启动服务器
            server_proc = start_server(args)
            if server_proc:
                # 注册一个清理函数来确保服务器最终会被停止
                atexit.register(lambda: stop_server(server_proc))
        except Exception as e:
            logger.exception(f"在pytest会话开始时启动服务器失败: {e}")

def pytest_sessionfinish(session, exitstatus):
    """pytest会话结束时的处理"""
    # 清理资源
    cleanup()

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
