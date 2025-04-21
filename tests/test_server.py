#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
WoniuNote测试服务器启动器

此模块负责以可靠的方式启动和停止WoniuNote测试服务器。
设计为可以被测试runner调用，或者单独运行。
"""

import os
import sys
import time
import signal
import socket
import argparse
import platform
import subprocess
import threading
import logging
from pathlib import Path

# 设置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger('test_server')

def is_port_available(host, port, timeout=1):
    """检查端口是否可用"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            return result != 0  # 如果连接失败，则端口可用
    except Exception as e:
        logger.error(f"检查端口时出错: {e}")
        return False

def wait_for_port(host, port, timeout=30, check_interval=1, available=False):
    """等待端口变为可用或不可用
    
    Args:
        host: 主机地址
        port: 端口号
        timeout: 超时时间（秒）
        check_interval: 检查间隔（秒）
        available: 如果为True，等待端口变为可用；如果为False，等待端口变为不可用
    
    Returns:
        bool: 如果在超时前端口达到期望状态则返回True，否则返回False
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        is_available = is_port_available(host, port)
        if is_available == available:
            return True
        time.sleep(check_interval)
    return False

def terminate_process_by_port(port):
    """终止占用指定端口的进程"""
    try:
        if platform.system() == "Windows":
            # Windows使用netstat查找进程
            output = subprocess.check_output(
                f"netstat -ano | findstr :{port}", 
                shell=True, 
                text=True
            )
            
            for line in output.strip().split('\n'):
                parts = [p for p in line.split() if p]
                if len(parts) >= 5:
                    pid = parts[4]
                    logger.info(f"找到占用端口 {port} 的进程: PID={pid}")
                    
                    try:
                        # 使用taskkill终止进程
                        subprocess.run(
                            ["taskkill", "/F", "/PID", pid],
                            check=False, 
                            stdout=subprocess.PIPE, 
                            stderr=subprocess.PIPE
                        )
                        logger.info(f"已终止进程 PID={pid}")
                        time.sleep(1)  # 等待进程完全终止
                        
                        # 检查端口是否已释放
                        if is_port_available("127.0.0.1", port):
                            return True
                    except Exception as e:
                        logger.warning(f"终止进程失败: {e}")
        else:
            # Linux/macOS使用lsof查找进程
            try:
                output = subprocess.check_output(
                    f"lsof -i :{port} -t", 
                    shell=True, 
                    text=True
                )
                
                for pid in output.strip().split('\n'):
                    if pid:
                        logger.info(f"找到占用端口 {port} 的进程: PID={pid}")
                        
                        try:
                            # 使用kill终止进程
                            subprocess.run(
                                ["kill", "-9", pid], 
                                check=False
                            )
                            logger.info(f"已终止进程 PID={pid}")
                            time.sleep(1)  # 等待进程完全终止
                            
                            # 检查端口是否已释放
                            if is_port_available("127.0.0.1", port):
                                return True
                        except Exception as e:
                            logger.warning(f"终止进程失败: {e}")
            except Exception as e:
                logger.warning(f"查找进程时出错: {e}")
    except Exception as e:
        logger.error(f"终止进程时出错: {e}")
    
    # 再次检查端口是否已释放
    return is_port_available("127.0.0.1", port)

def create_reader_thread(stream, prefix, stop_event):
    """创建一个线程来读取流并记录日志"""
    def reader_fn():
        if stream is None:
            logger.warning(f"{prefix} 流为None，无法读取")
            return
            
        logger.debug(f"开始读取 {prefix} 流")
        
        try:
            while not stop_event.is_set():
                # 检查是否有数据可读
                line = stream.readline()
                if not line:
                    # 检查进程是否已终止
                    time.sleep(0.1)
                    continue
                    
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
            logger.error(f"读取 {prefix} 输出流时出错: {str(e)}")
        finally:
            logger.debug(f"流读取线程退出: {prefix}")
    
    thread = threading.Thread(target=reader_fn, name=f"{prefix}-reader")
    thread.daemon = True
    thread.start()
    return thread

def start_test_server(port=5001, timeout=30):
    """启动测试服务器
    
    Args:
        port: 服务器端口号
        timeout: 等待服务器启动的超时时间（秒）
    
    Returns:
        dict: 包含进程、停止事件和读取线程的字典，如果启动失败则返回None
    """
    # 检查端口是否可用
    if not is_port_available("127.0.0.1", port):
        logger.warning(f"端口 {port} 已被占用，尝试终止占用该端口的进程")
        terminate_process_by_port(port)
        
        # 等待端口释放
        if not wait_for_port("127.0.0.1", port, timeout=10, available=True):
            logger.error(f"端口 {port} 仍被占用，无法启动服务器")
            return None
    
    # 确定项目根目录
    current_dir = os.getcwd()
    
    # 尝试多种方式确定项目根目录
    if 'source_code\\woniunote' in current_dir:
        # 如果当前目录包含项目路径，则找到项目根目录
        while os.path.basename(current_dir) != 'woniunote':
            current_dir = os.path.dirname(current_dir)
        project_root = current_dir
    elif os.path.basename(current_dir) == 'tests':
        # 如果当前目录是tests，则上一级是项目根目录
        project_root = os.path.abspath(os.path.join(current_dir, '..'))
    elif os.path.exists(os.path.join(current_dir, 'tests')):
        # 如果当前目录下有tests目录，则当前目录是项目根目录
        project_root = current_dir
    else:
        # 其他情况，假设当前目录是项目根目录
        project_root = current_dir
        
    logger.info(f"项目根目录: {project_root}")
    
    # 设置Flask服务器环境
    env = os.environ.copy()
    env['FLASK_ENV'] = 'testing'
    env['FLASK_DEBUG'] = '0'
    env['TESTING'] = 'true'
    env['PYTHONUNBUFFERED'] = '1'  # 确保输出不被缓存
    env['PYTHONPATH'] = f"{project_root};{env.get('PYTHONPATH', '')}" if platform.system() == "Windows" else f"{project_root}:{env.get('PYTHONPATH', '')}"
    
    # 停止事件
    stop_event = threading.Event()
    
    # 启动命令 - 使用测试专用服务器脚本
    test_server_script = os.path.join(current_dir, 'server_test_runner.py')
    
    # 检查测试脚本是否存在
    if not os.path.exists(test_server_script):
        logger.error(f"测试服务器脚本不存在: {test_server_script}")
        logger.error("请确保 server_test_runner.py 文件存在于 tests 目录下")
        return None
    
    try:
        if platform.system() == "Windows":
            cmd = [
                sys.executable,
                test_server_script,
                "--host", host,
                "--port", str(port),
                "--debug"
            ]
            creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            cmd = [
                sys.executable,
                test_server_script,
                "--host", host,
                "--port", str(port),
                "--debug"
            ]
            creation_flags = 0
        
        logger.info(f"启动命令: {' '.join(cmd)}")
        logger.info(f"工作目录: {project_root}")
        logger.info("启动Flask测试服务器...")
        
        # 以非阻塞方式启动服务器
        proc = subprocess.Popen(
            cmd,
            shell=False,
            cwd=project_root,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=creation_flags if platform.system() == "Windows" else 0
        )
        
        logger.info(f"服务器进程启动成功，PID: {proc.pid}")
        
        # 创建读取输出的线程
        stdout_thread = create_reader_thread(proc.stdout, "STDOUT", stop_event)
        stderr_thread = create_reader_thread(proc.stderr, "STDERR", stop_event)
        reader_threads = [stdout_thread, stderr_thread]
        
        # 等待服务器启动
        logger.info(f"等待服务器在 {host}:{port} 启动...")
        if wait_for_port(host, port, timeout=timeout, available=False):
            logger.info(f"服务器已成功启动在 {host}:{port}")
            return {
                "process": proc,
                "stop_event": stop_event,
                "reader_threads": reader_threads,
                "host": host,
                "port": port
            }
        else:
            logger.error(f"服务器启动超时 ({timeout}秒)")
            stop_server({
                "process": proc,
                "stop_event": stop_event,
                "reader_threads": reader_threads
            })
            return None
        
    except Exception as e:
        logger.exception(f"启动Flask服务器时出错: {e}")
        return None

def stop_server(server_info):
    """停止测试服务器
    
    Args:
        server_info: 由start_test_server返回的服务器信息字典
    
    Returns:
        bool: 如果服务器成功停止则返回True，否则返回False
    """
    # 如果server_info为None，直接返回True
    if server_info is None:
        logger.warning("服务器信息为空，跳过停止操作")
        return True
    if not server_info:
        logger.warning("服务器信息为空，无法停止")
        return False
    
    process = server_info.get("process")
    stop_event = server_info.get("stop_event")
    reader_threads = server_info.get("reader_threads", [])
    
    if not process:
        logger.warning("服务器进程为空，无法停止")
        return False
    
    logger.info(f"停止Flask服务器 (PID: {process.pid})...")
    
    # 设置停止事件以通知读取线程退出
    if stop_event:
        try:
            stop_event.set()
        except Exception as e:
            logger.error(f"设置停止事件时出错: {e}")
    
    # 停止读取线程
    thread_timeout = 2  # 秒
    for thread in reader_threads:
        try:
            if thread and thread.is_alive():
                logger.debug(f"等待线程 {thread.name} 退出...")
                thread.join(timeout=thread_timeout)
        except Exception as e:
            logger.error(f"停止线程时出错: {e}")
    
    # 尝试优雅地终止进程
    terminate_success = False
    try:
        # 检查进程是否已经终止
        if process.poll() is not None:
            logger.info(f"进程已经终止，返回码: {process.poll()}")
            return True
        
        # 使用terminate()方法尝试终止进程
        try:
            if platform.system() == "Windows":
                try:
                    # Windows下使用CTRL_BREAK_EVENT信号
                    os.kill(process.pid, signal.CTRL_BREAK_EVENT)
                    logger.info(f"已发送CTRL_BREAK_EVENT到进程 {process.pid}")
                except Exception as e:
                    logger.error(f"发送CTRL_BREAK_EVENT时出错: {e}")
                    # 如果CTRL_BREAK_EVENT失败，尝试terminate()
                    process.terminate()
                    logger.info(f"已调用terminate()方法终止进程 {process.pid}")
            else:
                # 非Windows系统使用terminate()
                process.terminate()
                logger.info(f"已调用terminate()方法终止进程 {process.pid}")
            
            # 等待进程终止，最多等待5秒
            for i in range(5):
                if process.poll() is not None:
                    logger.info(f"进程已终止，返回码: {process.poll()}")
                    terminate_success = True
                    break
                time.sleep(1)
                logger.debug(f"等待进程终止，已等待{i+1}秒")
        except Exception as e:
            logger.error(f"终止进程时出错: {e}")
        
        # 如果优雅终止失败，尝试强制终止
        if not terminate_success and process.poll() is None:
            logger.warning("优雅终止失败，尝试强制终止进程")
            try:
                process.kill()
                logger.info(f"已调用kill()方法强制终止进程 {process.pid}")
                
                # 再次等待进程终止，最多等待3秒
                for i in range(3):
                    if process.poll() is not None:
                        logger.info(f"进程已被强制终止，返回码: {process.poll()}")
                        terminate_success = True
                        break
                    time.sleep(1)
            except Exception as e:
                logger.error(f"强制终止进程时出错: {e}")
        
        # 如果所有Python方法都失败，尝试使用操作系统命令
        if not terminate_success and process.poll() is None:
            logger.warning("所有Python方法都无法终止进程，尝试使用系统命令")
            
            # 获取要释放的端口
            port = server_info.get("port", 5001)
            
            # 尝试通过端口终止进程
            if terminate_process_by_port(port):
                logger.info(f"已成功终止占用端口 {port} 的进程")
                terminate_success = True
        
        # 最终检查进程状态
        if process.poll() is not None:
            logger.info(f"进程已成功终止，最终返回码: {process.poll()}")
            return True
        else:
            logger.error("无法终止进程，请手动检查并终止")
            return False
            
    except Exception as e:
        logger.exception(f"停止服务器时出错: {e}")
        return False

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='WoniuNote测试服务器启动器')
    parser.add_argument('--action', choices=['start', 'stop'], default='start',
                        help='要执行的操作：启动或停止服务器')
    parser.add_argument('--port', type=int, default=5001,
                        help='服务器端口，默认为5001')
    parser.add_argument('--timeout', type=int, default=30,
                        help='等待服务器启动或停止的超时时间（秒）')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='启用详细日志输出')
    return parser.parse_args()

def main():
    """主函数"""
    args = parse_args()
    
    # 设置日志级别
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    # 获取当前脚本路径，避免使用__file__
    try:
        script_path = os.path.abspath(__file__)
    except NameError:
        # 如果__file__未定义，使用当前工作目录
        current_dir = os.getcwd()
        if 'tests' in current_dir:
            script_path = os.path.join(current_dir, 'test_server.py')
        else:
            script_path = os.path.join(current_dir, 'tests', 'test_server.py')
    
    if args.action == 'start':
        server_info = start_test_server(port=args.port, timeout=args.timeout)
        if server_info:
            logger.info(f"服务器启动成功: http://127.0.0.1:{args.port}")
            
            # 创建PID文件以便后续停止服务器
            pid_file = os.path.join(os.path.dirname(script_path), f"test_server_{args.port}.pid")
            with open(pid_file, 'w') as f:
                f.write(str(server_info['process'].pid))
            
            logger.info(f"服务器PID已保存到文件: {pid_file}")
            logger.info("服务器将继续在后台运行。要停止服务器，请运行:")
            logger.info(f"  python {os.path.basename(script_path)} --action stop --port {args.port}")
            
            # 等待终止信号
            try:
                # 仅在控制台模式下等待
                if sys.stdout.isatty():
                    logger.info("按Ctrl+C终止服务器...")
                    while True:
                        time.sleep(1)
            except KeyboardInterrupt:
                logger.info("接收到终止信号，停止服务器...")
                stop_server(server_info)
        else:
            logger.error("服务器启动失败")
            return 1
    
    elif args.action == 'stop':
        # 查找PID文件
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
        except NameError:
            # 如果__file__未定义，使用当前工作目录
            current_dir = os.getcwd()
            if 'tests' in current_dir:
                script_dir = current_dir
            else:
                script_dir = os.path.join(current_dir, 'tests')
        
        pid_file = os.path.join(script_dir, f"test_server_{args.port}.pid")
        if os.path.exists(pid_file):
            try:
                with open(pid_file, 'r') as f:
                    pid = int(f.read().strip())
                
                logger.info(f"尝试停止PID为 {pid} 的服务器进程...")
                
                # 创建一个简单的server_info字典
                server_info = {
                    "process": subprocess.Popen(
                        ["echo", "dummy"],  # 仅创建一个进程对象
                        stdout=subprocess.PIPE
                    )
                }
                server_info["process"].pid = pid
                
                if stop_server(server_info):
                    logger.info(f"服务器进程 {pid} 已停止")
                    os.remove(pid_file)
                    logger.info(f"已删除PID文件: {pid_file}")
                else:
                    logger.error(f"无法停止服务器进程 {pid}")
                    return 1
            except Exception as e:
                logger.error(f"停止服务器时出错: {e}")
                return 1
        else:
            # 如果找不到PID文件，尝试通过端口终止进程
            logger.warning(f"找不到PID文件，尝试通过端口 {args.port} 终止进程...")
            if terminate_process_by_port(args.port):
                logger.info(f"已成功终止占用端口 {args.port} 的进程")
            else:
                logger.error(f"无法终止占用端口 {args.port} 的进程")
                return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
