#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import logging
import datetime
import json
import traceback
from logging.handlers import TimedRotatingFileHandler

class SimpleLogger:
    """使用标准logging模块实现的日志记录器，保持与原来简单日志记录器相同的使用方式"""
    
    # 日志级别映射
    _level_map = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL
    }
    
    def __init__(self, name, log_dir=None):
        """初始化日志记录器
        
        Args:
            name: 日志记录器名称
            log_dir: 日志目录，默认为项目根目录下的 simple_logs 目录
        """
        self.name = name
        
        # 确定日志目录 - 修复：始终使用项目根目录
        if log_dir is None:
            # 获取项目根目录（woniunote包的父目录）
            current_file = os.path.abspath(__file__)
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
            self.log_dir = os.path.join(project_root, 'simple_logs')
        else:
            self.log_dir = log_dir
            
        # 确保日志目录存在
        try:
            os.makedirs(self.log_dir, exist_ok=True)
        except Exception as e:
            print(f"创建日志目录失败: {str(e)}")
            
        # 创建日志文件目录结构：按年月划分
        today = datetime.datetime.now()
        year_month_dir = os.path.join(self.log_dir, f"{today.year:04d}-{today.month:02d}")
        try:
            os.makedirs(year_month_dir, exist_ok=True)
        except Exception as e:
            print(f"创建年月日志目录失败: {str(e)}")
        
        # 日志文件路径基础名
        self.log_file_base = os.path.join(year_month_dir, f"{name}")
        self.log_file = f"{self.log_file_base}.log"
        
        # 创建logging对象
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)  # 设置为最低级别，允许所有日志通过
        
        # 清除现有的处理器，避免重复输出
        if self.logger.handlers:
            self.logger.handlers.clear()
        
        # 创建文件处理器，使用TimedRotatingFileHandler实现按日期划分日志文件
        file_handler = TimedRotatingFileHandler(
            self.log_file,
            when='midnight',     # 每天午夜切换一次
            interval=1,         # 间隔为1天
            backupCount=31,     # 保留最近31天的日志
            encoding='utf-8',
            atTime=datetime.time(0, 0, 0)  # 在午夜0点执行
        )
        # 设置日志文件后缀格式为日期
        file_handler.suffix = "%Y-%m-%d.log"
        file_handler.setLevel(logging.DEBUG)
        
        # 创建格式化器，确保日志内容不会被logging自动格式化
        formatter = logging.Formatter('%(message)s')
        file_handler.setFormatter(formatter)
        
        # 将处理器添加到logger
        self.logger.addHandler(file_handler)
        
        # 为了兼容性，添加handlers属性和方法
        self.handlers = self.logger.handlers
        self.level = self.logger.level
        
        # 打印日志文件路径
        print(f"简单日志记录器初始化: {self.log_file}")
    
    def _setup_logger(self):
        """重新设置logger"""
        try:
            # 清除现有的处理器
            if self.logger.handlers:
                for handler in self.logger.handlers[:]:
                    try:
                        handler.close()
                        self.logger.removeHandler(handler)
                    except:
                        pass
            
            # 重新创建文件处理器
            file_handler = TimedRotatingFileHandler(
                self.log_file,
                when='midnight',
                interval=1,
                backupCount=31,
                encoding='utf-8',
                atTime=datetime.time(0, 0, 0)
            )
            file_handler.suffix = "%Y-%m-%d.log"
            file_handler.setLevel(logging.DEBUG)
            
            formatter = logging.Formatter('%(message)s')
            file_handler.setFormatter(formatter)
            
            self.logger.addHandler(file_handler)
            self.handlers = self.logger.handlers
            
        except Exception as e:
            print(f"重新设置logger失败: {str(e)}")
    
    def _format_log_content(self, level: str, message: str, extra: dict = None) -> str:
        """
        格式化日志内容为JSON格式
        
        Args:
            level: 日志级别
            message: 日志消息
            extra: 额外信息
            
        Returns:
            str: 格式化后的JSON字符串
        """
        # 基础日志信息
        log_data = {
            'time': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'level': level,
            'module': self.name,
            'message': message
        }
        
        # 添加额外信息
        if extra:
            log_data.update(extra)
            
        # 转换为JSON字符串
        return json.dumps(log_data, ensure_ascii=False)
    
    def _write_log(self, level: str, message: str, extra: dict = None) -> bool:
        """
        写入日志的核心方法
        
        Args:
            level: 日志级别
            message: 日志消息
            extra: 额外信息
            
        Returns:
            bool: 写入是否成功
        """
        try:
            # 格式化日志内容
            log_content = self._format_log_content(level, message, extra)
            
            # 获取对应的日志级别
            log_level = getattr(logging, level.upper(), logging.INFO)
            
            # 写入日志 - 添加Windows句柄错误处理
            try:
                self.logger.log(log_level, log_content)
            except (OSError, IOError) as handle_error:
                # Windows句柄错误，尝试重新初始化logger
                if "句柄无效" in str(handle_error) or "handle" in str(handle_error).lower():
                    try:
                        self._setup_logger()
                        self.logger.log(log_level, log_content)
                    except:
                        # 如果重新初始化也失败，使用print作为备用
                        print(f"[{level}] {message}")
                        return False
                else:
                    raise
            
            return True
            
        except Exception as e:
            # 备用日志输出
            try:
                print(f"[{level}] {message} (日志系统错误: {e})")
            except:
                pass
            return False
    
    def info(self, message, extra=None):
        """记录INFO级别日志"""
        return self._write_log('INFO', message, extra)
        
    def warning(self, message, extra=None):
        """记录WARNING级别日志"""
        return self._write_log('WARNING', message, extra)
        
    def error(self, message, extra=None):
        """记录ERROR级别日志"""
        return self._write_log('ERROR', message, extra)
        
    def debug(self, message, extra=None):
        """记录DEBUG级别日志"""
        return self._write_log('DEBUG', message, extra)
        
    def critical(self, message, extra=None):
        """记录CRITICAL级别日志"""
        return self._write_log('CRITICAL', message, extra)
    
    def setLevel(self, level):
        """设置日志级别（兼容性方法）"""
        self.logger.setLevel(level)
        self.level = level

# 日志实例缓存，避免重复创建
_logger_cache = {}

# 获取日志记录器
def get_simple_logger(name):
    """获取简单日志记录器
    
    Args:
        name: 日志记录器名称
        
    Returns:
        SimpleLogger: 简单日志记录器实例
    """
    # 使用缓存避免重复创建同名日志器
    if name not in _logger_cache:
        _logger_cache[name] = SimpleLogger(name)
    return _logger_cache[name]
