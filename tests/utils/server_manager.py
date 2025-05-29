#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试服务器管理器

自动启动和停止测试服务器，用于浏览器测试
"""

import os
import sys
import time
import signal
import subprocess
import requests
import logging
from typing import Optional, Tuple

# 添加项目根目录到路径
project_root = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
sys.path.insert(0, project_root)

logger = logging.getLogger(__name__)

class TestServerManager:
    """测试服务器管理器"""
    
    def __init__(self, host: str = "127.0.0.1", port: int = 5001, use_http: bool = True):
        self.host = host
        self.port = port
        self.use_http = use_http
        self.protocol = "http" if use_http else "https"
        self.base_url = f"{self.protocol}://{self.host}:{self.port}"
        self.process: Optional[subprocess.Popen] = None
        self.is_external_server = False
        
    def is_server_running(self) -> bool:
        """检查服务器是否正在运行"""
        try:
            response = requests.get(self.base_url, timeout=3, verify=False)
            return response.status_code in [200, 301, 302, 404]
        except:
            return False
    
    def wait_for_server(self, timeout: int = 30) -> bool:
        """等待服务器启动"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.is_server_running():
                logger.info(f"服务器已启动: {self.base_url}")
                return True
            time.sleep(1)
        return False
    
    def start_server(self) -> bool:
        """启动测试服务器"""
        # 首先检查是否已有服务器在运行
        if self.is_server_running():
            logger.info(f"检测到外部服务器已在运行: {self.base_url}")
            self.is_external_server = True
            return True
        
        # 启动新的服务器进程
        logger.info(f"启动测试服务器: {self.base_url}")
        
        try:
            # 构建启动命令
            cmd = [
                sys.executable,
                os.path.join(project_root, "tests", "start_server.py"),
                "--test",
                "--host", self.host,
                "--port", str(self.port)
            ]
            
            if self.use_http:
                cmd.append("--http")
            
            # 启动服务器进程
            self.process = subprocess.Popen(
                cmd,
                cwd=project_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
            )
            
            # 等待服务器启动
            if self.wait_for_server():
                logger.info("测试服务器启动成功")
                return True
            else:
                logger.error("测试服务器启动超时")
                self.stop_server()
                return False
                
        except Exception as e:
            logger.error(f"启动测试服务器失败: {e}")
            return False
    
    def stop_server(self):
        """停止测试服务器"""
        if self.is_external_server:
            logger.info("检测到外部服务器，不进行停止操作")
            return
        
        if self.process:
            logger.info("停止测试服务器")
            try:
                if os.name == 'nt':  # Windows
                    # 在Windows上使用taskkill强制终止进程树
                    subprocess.run(['taskkill', '/F', '/T', '/PID', str(self.process.pid)], 
                                 capture_output=True)
                else:  # Unix/Linux
                    # 发送SIGTERM信号
                    os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
                
                # 等待进程结束
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    # 如果进程没有在5秒内结束，强制杀死
                    if os.name == 'nt':
                        subprocess.run(['taskkill', '/F', '/T', '/PID', str(self.process.pid)], 
                                     capture_output=True)
                    else:
                        os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
                
                logger.info("测试服务器已停止")
            except Exception as e:
                logger.warning(f"停止服务器时出错: {e}")
            finally:
                self.process = None
    
    def __enter__(self):
        """上下文管理器入口"""
        if self.start_server():
            return self
        else:
            raise RuntimeError("无法启动测试服务器")
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.stop_server()

# 全局服务器管理器实例
_server_manager: Optional[TestServerManager] = None

def get_server_manager() -> TestServerManager:
    """获取全局服务器管理器实例"""
    global _server_manager
    if _server_manager is None:
        _server_manager = TestServerManager()
    return _server_manager

def ensure_server_running() -> Tuple[bool, str]:
    """确保测试服务器正在运行"""
    manager = get_server_manager()
    if manager.start_server():
        return True, manager.base_url
    else:
        return False, ""

def stop_test_server():
    """停止测试服务器"""
    global _server_manager
    if _server_manager:
        _server_manager.stop_server()
        _server_manager = None 