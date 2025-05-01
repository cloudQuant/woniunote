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
            log_dir: 日志目录，默认为当前工作目录下的 simple_logs 目录
        """
        self.name = name
        
        # 确定日志目录
        if log_dir is None:
            self.log_dir = os.path.join(os.getcwd(), 'simple_logs')
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
        
        # 打印日志文件路径
        print(f"简单日志记录器初始化: {self.log_file}")
    
    def _write_log(self, level, message, extra=None):
        """写入日志
        
        Args:
            level: 日志级别
            message: 日志消息
            extra: 额外信息
        """
        try:
            # 获取当前时间
            now = datetime.datetime.now()
            now_str = now.strftime('%Y-%m-%d %H:%M:%S')
            
            # 检查是否需要更新日志目录（如果跨月份）
            today = datetime.datetime.now()
            year_month_dir = os.path.join(self.log_dir, f"{today.year:04d}-{today.month:02d}")
            expected_log_file_base = os.path.join(year_month_dir, f"{self.name}")
            
            # 如果当前日志文件基础路径与预期不符，则需要更新处理器
            if self.log_file_base != expected_log_file_base:
                # 更新日志文件路径
                self.log_file_base = expected_log_file_base
                self.log_file = f"{self.log_file_base}.log"
                
                # 确保目录存在
                try:
                    os.makedirs(year_month_dir, exist_ok=True)
                except Exception as e:
                    print(f"创建年月日志目录失败: {str(e)}")
            
            # 构建日志内容
            log_data = {
                'time': now_str,
                'level': level,
                'module': self.name,
                'message': message
            }
            
            # 添加额外信息
            if extra:
                log_data.update(extra)
                
            # 转换为JSON字符串
            log_content = json.dumps(log_data, ensure_ascii=False)
            
            # 使用logging模块记录日志
            log_level = self._level_map.get(level, logging.INFO)
            self.logger.log(log_level, log_content)
                
            return True
        except Exception as e:
            print(f"写入日志失败: {str(e)}")
            print(traceback.format_exc())
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
