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
import re
import argparse
import subprocess
import logging
import psutil
import signal
import platform
import socket

# 项目目录
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger("woniunote_test")

# 为服务器日志配置单独的处理器
def setup_server_logging():
    """配置服务器日志到单独的文件"""
    server_logger = logging.getLogger("server")
    server_logger.setLevel(logging.INFO)
    
    # 创建一个文件处理器，将服务器日志写入文件
    log_dir = os.path.join(PROJECT_ROOT, 'logs')
    os.makedirs(log_dir, exist_ok=True)
    server_log_file = os.path.join(log_dir, 'server.log')
    file_handler = logging.FileHandler(server_log_file, mode='w')
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    
    # 添加处理器到日志器
    server_logger.addHandler(file_handler)
    return server_logger

# 创建服务器日志器
server_logger = setup_server_logging()

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
SERVER_URL = None   # 服务器URL

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
                # 记录所有的PID以便全部终止
                pids = []
                for line in result.stdout.strip().split('\n'):
                    if "LISTENING" in line:
                        parts = [p for p in line.split() if p.strip()]
                        if len(parts) >= 5:
                            pid = parts[4]
                            if pid not in pids:
                                pids.append(pid)
                
                if pids:
                    # 终止所有找到的进程
                    for pid in pids:
                        logger.info(f"找到进程 PID={pid}，尝试终止...")
                        try:
                            # 使用taskkill强制终止进程及其子进程
                            subprocess.run(f"taskkill /F /T /PID {pid}", shell=True, capture_output=True)
                            # 等待短暂时间确保进程被终止
                            time.sleep(0.5)
                        except Exception as e:
                            logger.warning(f"终止进程 {pid} 时出错: {e}")
                    
                    # 检查端口是否已释放
                    return is_port_available(port)
            
            # 如果没有找到进程或上面的方法失败，尝试使用更直接的方法
            try:
                # 直接通过端口终止进程
                cmd = f"FOR /F \"tokens=5\" %p IN ('netstat -ano ^| findstr :{port} ^| findstr LISTENING') DO taskkill /F /T /PID %p"
                subprocess.run(cmd, shell=True)
                return is_port_available(port)
            except Exception as e:
                logger.warning(f"尝试备用方法终止进程时出错: {e}")
        else:
            # Linux/Mac
            cmd = f"lsof -i:{port} -t"
            result = subprocess.run(cmd, shell=True, text=True, capture_output=True)
            
            if result.returncode == 0 and result.stdout:
                # 可能有多个进程占用该端口
                pids = result.stdout.strip().split('\n')
                for pid in pids:
                    if pid.strip():
                        logger.info(f"找到进程 PID={pid}，尝试终止...")
                        try:
                            subprocess.run(f"kill -9 {pid}", shell=True)
                        except Exception as e:
                            logger.warning(f"终止进程 {pid} 时出错: {e}")
                
                # 检查端口是否已释放
                return is_port_available(port)
        
        # 如果没有找到进程或者端口不再被占用，返回端口状态
        return is_port_available(port)
    except Exception as e:
        logger.error(f"尝试释放端口时出错: {e}")
        return is_port_available(port)  # 还是返回端口状态

def start_flask_server():
    """启动 Flask 服务器并返回进程对象"""
    global SERVER_URL
    port = SERVER_PORT
    
    # 确保端口可用
    if not is_port_available(port):
        logger.warning(f"端口 {port} 已被占用")
        if not kill_process_on_port(port):
            logger.error(f"无法释放端口 {port}，请手动关闭占用该端口的程序")
            return None
        
        # 再次检查端口
        if not is_port_available(port):
            logger.error(f"尝试释放端口后，端口 {port} 仍然被占用")
            return None
        else:
            logger.info(f"端口 {port} 已成功释放")
    
    # 设置环境变量
    env = os.environ.copy()
    env['FLASK_ENV'] = 'development'
    env['FLASK_DEBUG'] = '1'
    env['PYTHONUNBUFFERED'] = '1'  # 确保输出不被缓存
    env['PYTHONPATH'] = f"{PROJECT_ROOT};{env.get('PYTHONPATH', '')}" if platform.system() == "Windows" else f"{PROJECT_ROOT}:{env.get('PYTHONPATH', '')}"
    # 强制使用HTTP协议
    env['WONIUNOTE_TEST_FORCE_HTTP'] = 'true'
    
    # 构建服务器启动命令 - 始终使用HTTP协议以避免SSL错误
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
        
        # 创建输出读取线程来监控服务器日志
        def read_output(stream, prefix):
            for line in iter(stream.readline, ''):
                if line.strip():
                    # 使用单独的服务器日志器记录日志
                    server_logger.info(f"{prefix}: {line.strip()}")
        
        # 启动读取线程
        import threading
        stdout_thread = threading.Thread(target=read_output, args=(process.stdout, "SERVER STDOUT"), daemon=True)
        stderr_thread = threading.Thread(target=read_output, args=(process.stderr, "SERVER STDERR"), daemon=True)
        stdout_thread.start()
        stderr_thread.start()
        
        # 等待服务器启动
        logger.info(f"等待服务器启动，最长等待 {SERVER_TIMEOUT} 秒...")
        
        start_time = time.time()
        while time.time() - start_time < SERVER_TIMEOUT:
            # 检查进程是否已终止
            if process.poll() is not None:
                stderr = process.stderr.read() if process.stderr else ""
                logger.error(f"服务器进程过早终止，退出代码: {process.poll()}, 错误: {stderr}")
                return None
                
            # 尝试建立 HTTP 连接来检查服务器是否响应
            try:
                # 使用urllib请求测试服务器连接（只测试HTTP）
                import urllib.request
                from urllib.error import URLError
                
                try:
                    # 尝试打开HTTP连接
                    urllib.request.urlopen(f"http://127.0.0.1:{port}", timeout=1)
                    logger.info(f"服务器已成功启动，可以访问: http://127.0.0.1:{port}")
                    
                    # 成功连接，返回服务器进程
                    SERVER_URL = f"http://127.0.0.1:{port}"
                    return process
                except URLError as e:
                    logger.warning(f"HTTP连接失败: {e}")
                    # 失败后尝试使用更底层的套接字连接测试
            except Exception as e:
                logger.warning(f"HTTP请求失败: {e}")
            
            # 如果HTTP请求失败，尝试原始套接字连接
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(1)
                s.connect(('127.0.0.1', port))
                s.close()
                logger.info(f"服务器已成功启动，端口 {port} 可响应（套接字连接）")
                
                # 底层连接成功，但HTTP层可能还没准备好，等待一秒
                time.sleep(1)
                
                SERVER_URL = f"http://127.0.0.1:{port}"
                return process
            except (socket.timeout, ConnectionRefusedError):
                # 连接还不可用，继续等待
                time.sleep(0.5)
            except Exception as e:
                logger.warning(f"套接字连接失败: {e}")
                time.sleep(0.5)
        
        # 超时后未能启动
        logger.error(f"服务器启动超时（{SERVER_TIMEOUT}秒）")
        if process.poll() is None:
            # 尝试温和终止
            process.terminate()
            # 给进程一些时间终止
            time.sleep(1)
            # 如果还没终止，强制终止
            if process.poll() is None:
                process.kill()
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
        # 先检查进程是否还在运行
        if process.poll() is None:
            # 温和地终止进程
            if platform.system() == "Windows":
                try:
                    process.send_signal(signal.CTRL_BREAK_EVENT)  # Windows
                    logger.info("发送 CTRL_BREAK_EVENT 信号给服务器进程")
                except Exception as e:
                    logger.warning(f"发送信号时出错: {e}")
            else:
                try:
                    process.terminate()  # SIGTERM
                    logger.info("发送 SIGTERM 信号给服务器进程")
                except Exception as e:
                    logger.warning(f"发送信号时出错: {e}")
            
            # 等待一段时间让进程正常终止
            wait_start = time.time()
            while process.poll() is None and time.time() - wait_start < 3:
                time.sleep(0.5)
        
        # 如果进程仍在运行，强制终止
        if process.poll() is None:
            try:
                process.kill()
                logger.info("服务器进程已强制终止")
                # 等待进程终止
                process.wait(timeout=2)
            except Exception as e:
                logger.error(f"强制终止进程时出错: {e}")
        else:
            logger.info(f"服务器进程已终止，退出代码: {process.poll()}")
        
        # 确保端口已释放
        if not is_port_available(SERVER_PORT):
            logger.warning(f"应用已关闭，但端口 {SERVER_PORT} 仍被占用，尝试强制释放")
            kill_process_on_port(SERVER_PORT)
            
    except Exception as e:
        logger.error(f"停止服务器时出错: {e}")
        # 最后尝试强制释放端口
        kill_process_on_port(SERVER_PORT)

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
    
    # 特别处理文章模块测试，确保先执行可处理数据映射问题的测试
    # 排序测试文件，优先运行可处理数据映射问题的测试
    def get_priority(file_path):
        file_name = os.path.basename(file_path)
        # 基本测试和容错测试先运行
        if file_name in ['test_basic.py', 'test_basic_app.py', 'test_article_minimal.py']:
            return 0
        # 直接API测试优先于浏览器测试
        elif '_direct' in file_name or 'minimal' in file_name:
            return 1
        # 其他测试后运行
        else:
            return 2
    
    # 排序测试文件
    all_tests.sort(key=get_priority)
    tolerant_tests.sort(key=get_priority)
    
    # 打印测试文件信息
    if include_all:
        logger.info(f"找到 {len(all_tests)} 个测试文件")
        for i, test in enumerate(all_tests[:10], 1):
            logger.info(f"  {i}. {os.path.basename(test)}")
        if len(all_tests) > 10:
            logger.info(f"  ... 及其他 {len(all_tests) - 10} 个测试文件")
        return all_tests
    else:
        logger.info(f"找到 {len(tolerant_tests)} 个容错测试文件")
        for i, test in enumerate(tolerant_tests, 1):
            logger.info(f"  {i}. {os.path.basename(test)}")
        return tolerant_tests

def run_tests(test_files):
    """运行测试文件列表"""
    if not test_files:
        logger.error("无测试文件可运行")
        return False
    
    success_count = 0
    failure_count = 0
    skipped_count = 0
    
    # 准备测试环境
    # 设置环境变量，处理数据库映射问题
    env = os.environ.copy()
    env['PYTHONPATH'] = f"{PROJECT_ROOT};{env.get('PYTHONPATH', '')}" if platform.system() == "Windows" else f"{PROJECT_ROOT}:{env.get('PYTHONPATH', '')}"
    
    # 设置关键环境变量设置来解决数据映射问题
    env['WONIUNOTE_TEST_USE_TITLE'] = 'true'              # 告知测试使用'title'而非'headline'
    env['WONIUNOTE_TEST_TYPE_IS_STRING'] = 'true'         # 告知测试'type'字段是字符串
    env['WONIUNOTE_DB_FIELD_MAPPING'] = 'true'            # 启用数据库字段映射兼容模式
    
    # 处理其他数据库映射问题
    env['WONIUNOTE_USER_CREATED_AT'] = 'true'             # 用户表使用created_at而非create_time
    env['WONIUNOTE_COMMENT_CREATED_AT'] = 'true'          # 评论表使用created_at而非create_time
    env['WONIUNOTE_CREDIT_CREATED_AT'] = 'true'           # 积分表使用created_at而非create_time
    
    # 强制HTTP协议相关设置
    env['WONIUNOTE_TEST_FORCE_HTTP'] = 'true'             # 强制测试使用HTTP连接
    env['PYTEST_BASE_URL'] = f'http://127.0.0.1:{SERVER_PORT}' # 确保测试使用HTTP连接
    env['PLAYWRIGHT_FORCE_HTTP'] = 'true'                 # 强制playwright使用HTTP
    env['REQUESTS_CA_BUNDLE'] = ''                        # 避免SSL证书验证
    env['SSL_CERT_FILE'] = ''                             # 禁用SSL证书
    
    # 其他调试和兼容性设置
    env['PYTHONIOENCODING'] = 'utf-8'                     # 确保文件编码为UTF-8
    env['LANG'] = 'zh_CN.UTF-8'                           # 设置语言为中文UTF-8
    env['LC_ALL'] = 'zh_CN.UTF-8'                         # 设置区域设置为中文UTF-8
    env['FLASK_ENV'] = 'testing'                          # 设置 Flask 为测试模式
    env['PYTHONWARNINGS'] = 'ignore::DeprecationWarning'  # 忽略弃用警告
    
    # 运行所有测试文件
    for test_file in test_files:
        base_name = os.path.basename(test_file)
        logger.info(f"{'='*30} 运行测试: {base_name} {'='*30}")
        
        # 构建 pytest 命令
        cmd = [sys.executable, "-m", "pytest", test_file, "-v", "-s"]
        
        # 如果测试文件包含 playwright 测试，加载强制HTTP的插件
        if 'article_features' in base_name or 'browser' in base_name:
            # 强制使用HTTP协议的插件
            cmd.extend(['-p', os.path.join(test_log_dir, "http_fix.py")])
            # 指定Base URL
            cmd.extend(['--base-url', f'http://127.0.0.1:{SERVER_PORT}'])
        
        # 对文章测试没有单独的命令行参数，这些都通过环境变量来控制
        
        try:
            # 运行测试并捕获输出
            logger.info(f"执行命令: {' '.join(cmd)}")
            
            # 创建详细输出文件
            test_log_dir = os.path.join(PROJECT_ROOT, 'logs', 'tests')
            os.makedirs(test_log_dir, exist_ok=True)
            
            # 创建一个HTTP协议修复插件
            http_fix_script = os.path.join(test_log_dir, "http_fix.py")
            with open(http_fix_script, 'w', encoding='utf-8') as f:
                f.write("""
# HTTP协议强制修正插件
# 注册这个插件来确保Pytest和Playwright使用HTTP连接

import os
import sys
from urllib.parse import urlparse, urlunparse

# 强制使用HTTP
def force_http(url):
    if not url or not isinstance(url, str):
        return url
    
    # 解析URL
    parsed = urlparse(url)
    
    # 如果是HTTPS，则转换为HTTP
    if parsed.scheme == 'https':
        components = list(parsed)
        components[0] = 'http'
        return urlunparse(tuple(components))
    return url

# 覆盖playwright的goto方法
def patch_playwright_methods():
    try:
        # 尝试导入playwright
        from playwright.sync_api import Page
        
        # 修补Page.goto方法
        if not hasattr(Page, '_original_goto'):
            Page._original_goto = Page.goto
            
            def patched_goto(self, url, **kwargs):
                patched_url = force_http(url)
                print(f"Playwright: 将URL从 {url} 更改为 {patched_url}")
                return self._original_goto(patched_url, **kwargs)
            
            Page.goto = patched_goto
            print("Playwright goto方法已被覆盖以强制使用HTTP")
    except ImportError:
        print("Playwright模块不可用")
        pass

# 注册插件函数
def pytest_configure(config):
    print("\n\u542f用HTTP协议强制插件...")
    
    # 确保base_url使用HTTP
    if hasattr(config.option, 'base_url'):
        original_base_url = getattr(config.option, 'base_url', None)
        if original_base_url and original_base_url.startswith('https'):
            setattr(config.option, 'base_url', force_http(original_base_url))
            print(f"Base URL已从 {original_base_url} 更改为 {config.option.base_url}")
    
    # 修补 Playwright 方法
    patch_playwright_methods()
    
    print("HTTP协议强制插件加载完成!")
""")
            
            # 使用测试文件名创建日志文件
            test_log_file = os.path.join(test_log_dir, f"{os.path.splitext(base_name)[0]}.log")
            
            # 将stdout和stderr重定向到日志文件
            with open(test_log_file, 'w', encoding='utf-8') as f_log:
                f_log.write(f"\n{'='*50}\n测试文件: {base_name}\n{'='*50}\n")
                f_log.write(f"\u6267行命令: {' '.join(cmd)}\n\n")
                f_log.write(f"\u73af境变量:\n")
                for key in sorted([k for k in env.keys() if k.startswith('WONIUNOTE') or k.startswith('PYTHON') or k == 'FLASK_ENV']):
                    f_log.write(f"  {key}={env[key]}\n")
                f_log.write("\n\u6d4b试输出:\n\n")
                
                # 运行测试并捕获输出
                log_env = env.copy()
                log_env['PYTHONUNBUFFERED'] = '1'  # 确保输出不被缓存
                
                result = subprocess.run(
                    cmd, 
                    env=log_env, 
                    stdout=f_log, 
                    stderr=subprocess.STDOUT,
                    check=False,
                    text=True
                )
            
            # 根据 pytest 返回码判断测试结果
            # 0=所有测试通过, 1=有失败, 2=有错误, 4=有跳过但无失败
            if result.returncode == 0:
                logger.info(f"✓ 测试通过: {base_name}")
                success_count += 1
            elif result.returncode == 4:  # 只有跳过的测试
                logger.info(f"⮚ 测试部分跳过: {base_name}")
                skipped_count += 1
            else:
                # 提取失败日志中最后一个失败的消息
                error_message = "无详细信息"
                try:
                    # 尝试从日志文件中提取最后一个失败信息
                    with open(test_log_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        # 尝试匹配常见的错误模式
                        error_matches = []
                        for pattern in [
                            r"E\s+(.+Error:.+?)\n", 
                            r"FAILED.+\n(.+?)\n", 
                            r"AssertionError\s*:(.+?)\n",
                            r"Exception\s*:(.+?)\n"
                        ]:
                            matches = re.findall(pattern, content, re.MULTILINE)
                            if matches:
                                error_matches.extend(matches)
                                
                        if error_matches:
                            # 测试失败信息通常在最后
                            error_message = error_matches[-1].strip()
                            # 限制错误消息长度
                            if len(error_message) > 150:
                                error_message = error_message[:147] + "..."
                except Exception as e:
                    logger.warning(f"无法解析测试错误信息: {e}")
                
                logger.error(f"✗ 测试失败: {base_name} (返回码: {result.returncode})")
                logger.error(f"  错误信息: {error_message}")
                logger.info(f"  详细日志: {test_log_file}")
                failure_count += 1
                
        except Exception as e:
            logger.error(f"运行测试出错: {e}")
            failure_count += 1
            
        # 每个测试文件之间暂停一秒，让资源有时间释放
        time.sleep(1)
    
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
    parser.add_argument('--test', type=str, help='运行指定的测试文件（完整路径或文件名）')
    args = parser.parse_args()
    
    # 启动服务器
    server_process = None
    if not args.no_server:
        server_process = start_flask_server()
        if not server_process:
            logger.error("服务器启动失败，无法执行测试")
            return 1
    
    try:
        # 处理特定测试文件的情况
        if args.test:
            test_file = args.test
            # 如果只提供了文件名，则在测试目录中查找完整路径
            if not os.path.isfile(test_file):
                test_path = os.path.join(PROJECT_ROOT, 'tests')
                for root, _, files in os.walk(test_path):
                    if os.path.basename(test_file) in files:
                        test_file = os.path.join(root, os.path.basename(test_file))
                        break
            
            if os.path.isfile(test_file):
                logger.info(f"运行指定的测试文件: {os.path.basename(test_file)}")
                test_files = [test_file]
            else:
                logger.error(f"找不到指定的测试文件: {args.test}")
                return 1
        else:
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
