#!/usr/bin/env python3
"""
日志级别管理器
根据环境和配置动态调整日志级别和详细程度
"""

import os
import logging
from enum import Enum
from typing import Dict, Any, Optional
from woniunote.common.simple_logger import get_simple_logger

class LogLevel(Enum):
    """日志级别枚举"""
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL

class LogVerbosity(Enum):
    """日志详细程度"""
    MINIMAL = "minimal"      # 最少日志，只记录错误和关键信息
    NORMAL = "normal"        # 正常日志，记录重要操作
    DETAILED = "detailed"    # 详细日志，记录大部分操作
    VERBOSE = "verbose"      # 详尽日志，记录所有操作（调试用）

class LogLevelManager:
    """日志级别管理器"""
    
    def __init__(self):
        self.logger = get_simple_logger('log_level_manager')
        self.current_level = self._determine_log_level()
        self.current_verbosity = self._determine_verbosity()
        self.module_configs = self._get_module_configs()
    
    def _determine_log_level(self) -> LogLevel:
        """根据环境确定日志级别"""
        env = os.environ.get('FLASK_ENV', 'production').lower()
        log_level_str = os.environ.get('LOG_LEVEL', '').upper()
        
        # 优先使用环境变量设置的级别
        if log_level_str:
            try:
                return LogLevel[log_level_str]
            except KeyError:
                pass
        
        # 根据环境自动确定
        if env in ['development', 'dev']:
            return LogLevel.DEBUG
        elif env in ['testing', 'test']:
            return LogLevel.INFO
        else:  # production
            return LogLevel.WARNING
    
    def _determine_verbosity(self) -> LogVerbosity:
        """根据环境确定日志详细程度"""
        env = os.environ.get('FLASK_ENV', 'production').lower()
        verbosity_str = os.environ.get('LOG_VERBOSITY', '').lower()
        
        # 优先使用环境变量设置
        if verbosity_str:
            try:
                return LogVerbosity(verbosity_str)
            except ValueError:
                pass
        
        # 根据环境自动确定
        if env in ['development', 'dev']:
            return LogVerbosity.DETAILED
        elif env in ['testing', 'test']:
            return LogVerbosity.NORMAL
        else:  # production
            return LogVerbosity.MINIMAL
    
    def _get_module_configs(self) -> Dict[str, Dict[str, Any]]:
        """获取各模块的日志配置"""
        return {
            # 核心模块 - 重要日志
            'app': {
                'min_level': LogLevel.INFO,
                'verbosity': LogVerbosity.NORMAL,
                'include_sensitive': False
            },
            'app_factory': {
                'min_level': LogLevel.INFO,
                'verbosity': LogVerbosity.NORMAL,
                'include_sensitive': False
            },
            
            # 控制器模块 - 根据重要性调整
            'user_controller': {
                'min_level': LogLevel.INFO,
                'verbosity': LogVerbosity.NORMAL,
                'include_sensitive': False  # 用户相关不记录敏感信息
            },
            'admin_controller': {
                'min_level': LogLevel.INFO,
                'verbosity': LogVerbosity.DETAILED,  # 管理员操作需要详细记录
                'include_sensitive': False
            },
            'article_controller': {
                'min_level': LogLevel.WARNING,
                'verbosity': LogVerbosity.NORMAL,
                'include_sensitive': False
            },
            
            # 数据库模块 - 减少详细程度
            'users': {
                'min_level': LogLevel.WARNING,
                'verbosity': LogVerbosity.MINIMAL,
                'include_sensitive': False
            },
            'articles': {
                'min_level': LogLevel.WARNING,
                'verbosity': LogVerbosity.MINIMAL,
                'include_sensitive': False
            },
            'db_connection_manager': {
                'min_level': LogLevel.WARNING,
                'verbosity': LogVerbosity.MINIMAL,
                'include_sensitive': False
            },
            
            # 安全模块 - 保持详细记录
            'secure_password': {
                'min_level': LogLevel.INFO,
                'verbosity': LogVerbosity.DETAILED,
                'include_sensitive': False
            },
            'atomic_password_migration': {
                'min_level': LogLevel.INFO,
                'verbosity': LogVerbosity.DETAILED,
                'include_sensitive': False
            },
            
            # 缓存和性能模块 - 减少冗余日志
            'unified_cache_strategy': {
                'min_level': LogLevel.WARNING,
                'verbosity': LogVerbosity.MINIMAL,
                'include_sensitive': False
            },
            'memory_optimizer': {
                'min_level': LogLevel.WARNING,
                'verbosity': LogVerbosity.MINIMAL,
                'include_sensitive': False
            },
            
            # 工具模块 - 最小日志
            'trace_id_manager': {
                'min_level': LogLevel.ERROR,
                'verbosity': LogVerbosity.MINIMAL,
                'include_sensitive': False
            },
            'enhanced_input_validator': {
                'min_level': LogLevel.WARNING,
                'verbosity': LogVerbosity.MINIMAL,
                'include_sensitive': False
            }
        }
    
    def should_log(self, module_name: str, level: LogLevel, is_sensitive: bool = False) -> bool:
        """判断是否应该记录日志"""
        module_config = self.module_configs.get(module_name, {})
        
        # 检查级别要求
        min_level = module_config.get('min_level', self.current_level)
        if level.value < min_level.value:
            return False
        
        # 检查敏感信息策略
        if is_sensitive and not module_config.get('include_sensitive', False):
            return False
        
        return True
    
    def should_include_details(self, module_name: str) -> bool:
        """判断是否应该包含详细信息"""
        module_config = self.module_configs.get(module_name, {})
        module_verbosity = module_config.get('verbosity', self.current_verbosity)
        
        return module_verbosity in [LogVerbosity.DETAILED, LogVerbosity.VERBOSE]
    
    def should_include_trace_info(self, module_name: str) -> bool:
        """判断是否应该包含跟踪信息"""
        module_config = self.module_configs.get(module_name, {})
        module_verbosity = module_config.get('verbosity', self.current_verbosity)
        
        return module_verbosity == LogVerbosity.VERBOSE
    
    def filter_log_data(self, module_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """过滤日志数据，移除不必要的信息"""
        if not self.should_include_details(module_name):
            # 只保留关键信息
            filtered = {}
            essential_keys = ['trace_id', 'username', 'userid', 'error', 'error_type', 'success', 'status']
            for key in essential_keys:
                if key in data:
                    filtered[key] = data[key]
            return filtered
        
        if not self.should_include_trace_info(module_name):
            # 移除详细的跟踪信息
            filtered = data.copy()
            verbose_keys = ['traceback', 'stack_trace', 'query_time_ms', 'memory_usage', 'cache_stats']
            for key in verbose_keys:
                filtered.pop(key, None)
            return filtered
        
        return data
    
    def optimize_log_message(self, module_name: str, message: str, data: Dict[str, Any] = None) -> tuple[str, Optional[Dict[str, Any]]]:
        """优化日志消息和数据"""
        optimized_data = None
        
        if data:
            optimized_data = self.filter_log_data(module_name, data)
            
            # 如果数据为空，则不传递数据
            if not optimized_data:
                optimized_data = None
        
        # 根据详细程度调整消息
        if not self.should_include_details(module_name):
            # 简化消息
            if '成功' in message and len(message) > 20:
                message = message.split('成功')[0] + '成功'
            elif '失败' in message and len(message) > 20:
                message = message.split('失败')[0] + '失败'
        
        return message, optimized_data
    
    def get_log_config_summary(self) -> Dict[str, Any]:
        """获取当前日志配置摘要"""
        return {
            'global_level': self.current_level.name,
            'global_verbosity': self.current_verbosity.value,
            'module_count': len(self.module_configs),
            'environment': os.environ.get('FLASK_ENV', 'production'),
            'log_optimization': True
        }
    
    def apply_optimizations(self):
        """应用日志优化"""
        # 更新simple_logger的行为
        try:
            # 这里可以动态调整现有的日志记录器
            for module_name, config in self.module_configs.items():
                # 如果需要，可以在这里修改已存在的logger配置
                pass
            
            self.logger.info("日志优化已应用", self.get_log_config_summary())
            
        except Exception as e:
            self.logger.error(f"应用日志优化失败: {e}")

# 创建全局实例
log_level_manager = LogLevelManager()

def optimize_logging():
    """优化日志记录的便捷函数"""
    log_level_manager.apply_optimizations()
    return log_level_manager

def should_log_details(module_name: str) -> bool:
    """检查是否应该记录详细信息的便捷函数"""
    return log_level_manager.should_include_details(module_name)

def filter_sensitive_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """过滤敏感数据的便捷函数"""
    if not data:
        return data
    
    sensitive_keys = ['password', 'token', 'secret', 'key', 'auth', 'credential']
    filtered = data.copy()
    
    for key in list(filtered.keys()):
        if any(sensitive in key.lower() for sensitive in sensitive_keys):
            filtered[key] = '***'
        elif isinstance(filtered[key], str) and len(filtered[key]) > 100:
            # 截断过长的字符串
            filtered[key] = filtered[key][:100] + '...'
    
    return filtered

if __name__ == '__main__':
    # 测试日志级别管理器
    manager = LogLevelManager()
    
    print("=== 日志配置摘要 ===")
    config = manager.get_log_config_summary()
    for key, value in config.items():
        print(f"{key}: {value}")
    
    print("\n=== 模块日志配置示例 ===")
    test_modules = ['user_controller', 'users', 'unified_cache_strategy']
    for module in test_modules:
        details = manager.should_include_details(module)
        trace = manager.should_include_trace_info(module)
        print(f"{module}: 详细={details}, 跟踪={trace}")
    
    print("\n=== 应用优化 ===")
    manager.apply_optimizations()