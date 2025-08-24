#!/usr/bin/env python3
"""
统一的日志系统模块
整合所有日志相关功能：日志记录、级别管理、格式化、装饰器等
"""

import os
import sys
import time
import logging
import logging.handlers
import threading
from typing import Dict, Any, Optional, List, Callable, Union
from functools import wraps
from enum import Enum
from dataclasses import dataclass, asdict
from pathlib import Path

# ==================== 枚举定义 ====================

class LogLevel(Enum):
    """日志级别"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class LogFormat(Enum):
    """日志格式"""
    SIMPLE = "simple"          # 简单格式
    DETAILED = "detailed"      # 详细格式
    JSON = "json"              # JSON格式
    STRUCTURED = "structured"  # 结构化格式

# ==================== 数据类定义 ====================

@dataclass
class LogConfig:
    """日志配置"""
    level: LogLevel = LogLevel.INFO
    format: LogFormat = LogFormat.SIMPLE
    max_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    log_dir: str = "logs"
    enable_console: bool = True
    enable_file: bool = True
    enable_rotation: bool = True
    enable_compression: bool = False

@dataclass
class LogRecord:
    """日志记录"""
    timestamp: str
    level: str
    logger_name: str
    message: str
    module: str
    function: str
    line: int
    extra: Dict[str, Any] = None

# ==================== 日志格式化器 ====================

class LogFormatter:
    """日志格式化器"""
    
    def __init__(self, format_type: LogFormat = LogFormat.SIMPLE):
        self.format_type = format_type
        self.formatters = {
            LogFormat.SIMPLE: self._simple_formatter,
            LogFormat.DETAILED: self._detailed_formatter,
            LogFormat.JSON: self._json_formatter,
            LogFormat.STRUCTURED: self._structured_formatter
        }
    
    def format(self, record: logging.LogRecord) -> str:
        """格式化日志记录"""
        formatter = self.formatters.get(self.format_type, self._simple_formatter)
        return formatter(record)
    
    def _simple_formatter(self, record: logging.LogRecord) -> str:
        """简单格式化"""
        return f"{record.levelname}: {record.getMessage()}"
    
    def _detailed_formatter(self, record: logging.LogRecord) -> str:
        """详细格式化"""
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(record.created))
        return (f"{timestamp} [{record.levelname}] {record.name}: "
                f"{record.getMessage()} ({record.filename}:{record.lineno})")
    
    def _json_formatter(self, record: logging.LogRecord) -> str:
        """JSON格式化"""
        import json
        
        log_data = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(record.created)),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.filename,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # 添加额外字段
        if hasattr(record, 'extra'):
            log_data.update(record.extra)
        
        return json.dumps(log_data, ensure_ascii=False)
    
    def _structured_formatter(self, record: logging.LogRecord) -> str:
        """结构化格式化"""
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(record.created))
        parts = [
            f"[{timestamp}]",
            f"[{record.levelname}]",
            f"[{record.name}]",
            record.getMessage()
        ]
        
        # 添加位置信息
        if record.filename and record.lineno:
            parts.append(f"({record.filename}:{record.lineno})")
        
        return " ".join(parts)

# ==================== 日志级别管理器 ====================

class LogLevelManager:
    """日志级别管理器"""
    
    def __init__(self):
        self.level_mappings = {
            'debug': logging.DEBUG,
            'info': logging.INFO,
            'warning': logging.WARNING,
            'error': logging.ERROR,
            'critical': logging.CRITICAL
        }
        self.dynamic_levels = {}
        self._lock = threading.RLock()
    
    def set_logger_level(self, logger_name: str, level: Union[str, int]) -> bool:
        """设置指定logger的级别"""
        try:
            if isinstance(level, str):
                level = self.level_mappings.get(level.lower(), logging.INFO)
            
            logger = logging.getLogger(logger_name)
            logger.setLevel(level)
            
            with self._lock:
                self.dynamic_levels[logger_name] = level
            
            return True
        except Exception:
            return False
    
    def get_logger_level(self, logger_name: str) -> Optional[int]:
        """获取指定logger的级别"""
        try:
            logger = logging.getLogger(logger_name)
            return logger.level
        except Exception:
            return None
    
    def set_global_level(self, level: Union[str, int]) -> bool:
        """设置全局日志级别"""
        try:
            if isinstance(level, str):
                level = self.level_mappings.get(level.lower(), logging.INFO)
            
            logging.getLogger().setLevel(level)
            
            # 设置所有已知logger的级别
            for logger_name in self.dynamic_levels:
                self.set_logger_level(logger_name, level)
            
            return True
        except Exception:
            return False
    
    def get_all_levels(self) -> Dict[str, int]:
        """获取所有logger的级别"""
        with self._lock:
            return self.dynamic_levels.copy()

# ==================== 日志处理器管理器 ====================

class LogHandlerManager:
    """日志处理器管理器"""
    
    def __init__(self, config: LogConfig):
        self.config = config
        self.handlers = {}
        self._setup_handlers()
    
    def _setup_handlers(self):
        """设置日志处理器"""
        # 控制台处理器
        if self.config.enable_console:
            self._setup_console_handler()
        
        # 文件处理器
        if self.config.enable_file:
            self._setup_file_handler()
    
    def _setup_console_handler(self):
        """设置控制台处理器"""
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(self.config.level.value)
        
        formatter = LogFormatter(self.config.format)
        console_handler.setFormatter(logging.Formatter(formatter.format(logging.LogRecord(
            name="", level=0, pathname="", lineno=0, msg="", args=(), exc_info=None
        ))))
        
        self.handlers['console'] = console_handler
    
    def _setup_file_handler(self):
        """设置文件处理器"""
        # 确保日志目录存在
        log_dir = Path(self.config.log_dir)
        log_dir.mkdir(exist_ok=True)
        
        # 主日志文件
        main_log_file = log_dir / "app.log"
        
        if self.config.enable_rotation:
            # 使用轮转处理器
            file_handler = logging.handlers.RotatingFileHandler(
                main_log_file,
                maxBytes=self.config.max_size,
                backupCount=self.config.backup_count,
                encoding='utf-8'
            )
        else:
            # 使用普通文件处理器
            file_handler = logging.FileHandler(main_log_file, encoding='utf-8')
        
        file_handler.setLevel(self.config.level.value)
        
        formatter = LogFormatter(self.config.format)
        file_handler.setFormatter(logging.Formatter(formatter.format(logging.LogRecord(
            name="", level=0, pathname="", lineno=0, msg="", args=(), exc_info=None
        ))))
        
        self.handlers['file'] = file_handler
    
    def get_handlers(self) -> Dict[str, logging.Handler]:
        """获取所有处理器"""
        return self.handlers.copy()
    
    def add_handler(self, name: str, handler: logging.Handler):
        """添加自定义处理器"""
        self.handlers[name] = handler
    
    def remove_handler(self, name: str):
        """移除处理器"""
        if name in self.handlers:
            del self.handlers[name]

# ==================== 统一日志管理器 ====================

class UnifiedLogManager:
    """统一的日志管理器"""
    
    def __init__(self, config: LogConfig = None):
        self.config = config or LogConfig()
        self.level_manager = LogLevelManager()
        self.handler_manager = LogHandlerManager(self.config)
        self.loggers = {}
        
        # 设置根logger
        self._setup_root_logger()
        
        print(f"统一日志系统初始化完成，级别: {self.config.level.value}")
    
    def _setup_root_logger(self):
        """设置根logger"""
        root_logger = logging.getLogger()
        root_logger.setLevel(self.config.level.value)
        
        # 清除现有处理器
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # 添加新处理器
        for handler in self.handler_manager.get_handlers().values():
            root_logger.addHandler(handler)
    
    def get_logger(self, name: str) -> logging.Logger:
        """获取logger实例"""
        if name not in self.loggers:
            logger = logging.getLogger(name)
            self.loggers[name] = logger
            
            # 设置级别
            if self.config.level:
                logger.setLevel(self.config.level.value)
        
        return self.loggers[name]
    
    def set_logger_level(self, logger_name: str, level: Union[str, int]) -> bool:
        """设置logger级别"""
        return self.level_manager.set_logger_level(logger_name, level)
    
    def set_global_level(self, level: Union[str, int]) -> bool:
        """设置全局日志级别"""
        success = self.level_manager.set_global_level(level)
        if success:
            # 更新配置
            if isinstance(level, str):
                level = self.level_manager.level_mappings.get(level.lower(), logging.INFO)
            self.config.level = LogLevel(level)
            
            # 重新设置根logger
            self._setup_root_logger()
        
        return success
    
    def get_stats(self) -> Dict[str, Any]:
        """获取日志统计信息"""
        return {
            'config': asdict(self.config),
            'loggers_count': len(self.loggers),
            'handlers_count': len(self.handler_manager.get_handlers()),
            'levels': self.level_manager.get_all_levels()
        }
    
    def rotate_logs(self):
        """轮转日志文件"""
        for handler in self.handler_manager.get_handlers().values():
            if hasattr(handler, 'doRollover'):
                try:
                    handler.doRollover()
                except Exception as e:
                    print(f"日志轮转失败: {e}")

# ==================== 日志装饰器 ====================

def log_function_call(level: str = "INFO", include_args: bool = True, include_result: bool = True):
    """
    函数调用日志装饰器
    
    Args:
        level: 日志级别
        include_args: 是否包含参数
        include_result: 是否包含结果
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = logging.getLogger(func.__module__)
            
            # 记录函数调用
            call_msg = f"调用函数: {func.__name__}"
            if include_args:
                args_str = ", ".join([str(arg) for arg in args])
                kwargs_str = ", ".join([f"{k}={v}" for k, v in kwargs.items()])
                params = f"({args_str}{', ' if args_str and kwargs_str else ''}{kwargs_str})"
                call_msg += f" 参数: {params}"
            
            getattr(logger, level.lower())(call_msg)
            
            # 执行函数
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                # 记录执行结果
                result_msg = f"函数 {func.__name__} 执行完成，耗时: {execution_time:.3f}s"
                if include_result:
                    result_msg += f" 结果: {result}"
                
                getattr(logger, level.lower())(result_msg)
                
                return result
                
            except Exception as e:
                execution_time = time.time() - start_time
                error_msg = f"函数 {func.__name__} 执行失败，耗时: {execution_time:.3f}s 错误: {e}"
                logger.error(error_msg)
                raise
        
        return wrapper
    return decorator

def log_performance(threshold: float = 1.0):
    """
    性能日志装饰器
    
    Args:
        threshold: 性能阈值（秒）
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = logging.getLogger(func.__module__)
            
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                if execution_time > threshold:
                    logger.warning(f"函数 {func.__name__} 执行时间过长: {execution_time:.3f}s")
                else:
                    logger.debug(f"函数 {func.__name__} 执行时间: {execution_time:.3f}s")
                
                return result
                
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(f"函数 {func.__name__} 执行失败，耗时: {execution_time:.3f}s 错误: {e}")
                raise
        
        return wrapper
    return decorator

# ==================== 全局实例和工厂函数 ====================

# 全局日志管理器实例
_global_log_manager = None

def init_unified_logging(config: LogConfig = None) -> UnifiedLogManager:
    """初始化全局日志管理器"""
    global _global_log_manager
    _global_log_manager = UnifiedLogManager(config)
    return _global_log_manager

def get_log_manager() -> Optional[UnifiedLogManager]:
    """获取全局日志管理器"""
    return _global_log_manager

def get_logger(name: str) -> logging.Logger:
    """获取logger实例"""
    if _global_log_manager:
        return _global_log_manager.get_logger(name)
    else:
        # 如果没有初始化，返回标准logger
        return logging.getLogger(name)

# ==================== 向后兼容 ====================

# 为了向后兼容，保留旧的函数名
init_simple_logger = init_unified_logging
get_simple_logger = get_logger
init_enhanced_logger = init_unified_logging
get_enhanced_logger = get_logger
