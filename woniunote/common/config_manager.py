#!/usr/bin/env python3
"""
动态配置管理器
支持配置热重载、环境感知、配置验证等功能
"""

import os
import yaml
import json
import time
import threading
import logging
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from dataclasses import dataclass, asdict
from enum import Enum
import hashlib

logger = logging.getLogger(__name__)

class ConfigSource(Enum):
    """配置源类型"""
    FILE = "file"
    ENVIRONMENT = "environment"
    DATABASE = "database"
    REMOTE = "remote"

@dataclass
class ConfigValidationRule:
    """配置验证规则"""
    key: str
    required: bool = False
    data_type: type = str
    min_value: Optional[Any] = None
    max_value: Optional[Any] = None
    allowed_values: Optional[List[Any]] = None
    validator: Optional[Callable] = None
    description: str = ""

class ConfigValidator:
    """配置验证器"""
    
    def __init__(self):
        self.rules: Dict[str, ConfigValidationRule] = {}
        self.setup_default_rules()
    
    def setup_default_rules(self):
        """设置默认验证规则"""
        default_rules = [
            ConfigValidationRule(
                key="database.SQLALCHEMY_DATABASE_URI",
                required=True,
                description="数据库连接URI"
            ),
            ConfigValidationRule(
                key="SECRET_KEY",
                required=True,
                description="应用密钥"
            ),
            ConfigValidationRule(
                key="cache.default_ttl",
                data_type=int,
                min_value=1,
                max_value=86400,
                description="缓存默认TTL（秒）"
            ),
            ConfigValidationRule(
                key="rate_limit.default_limit",
                data_type=int,
                min_value=1,
                max_value=10000,
                description="默认限流阈值"
            ),
            ConfigValidationRule(
                key="logging.level",
                allowed_values=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                description="日志级别"
            )
        ]
        
        for rule in default_rules:
            self.add_rule(rule)
    
    def add_rule(self, rule: ConfigValidationRule):
        """添加验证规则"""
        self.rules[rule.key] = rule
    
    def validate_config(self, config: Dict[str, Any]) -> Dict[str, List[str]]:
        """验证配置，返回错误信息"""
        errors = {}
        
        for key, rule in self.rules.items():
            error_list = self._validate_single_key(config, key, rule)
            if error_list:
                errors[key] = error_list
        
        return errors
    
    def _validate_single_key(self, config: Dict[str, Any], key: str, rule: ConfigValidationRule) -> List[str]:
        """验证单个配置项"""
        errors = []
        
        # 获取嵌套键值
        value = self._get_nested_value(config, key)
        
        # 检查必需性
        if rule.required and value is None:
            errors.append(f"Required configuration '{key}' is missing")
            return errors
        
        if value is None:
            return errors
        
        # 检查数据类型
        if rule.data_type and not isinstance(value, rule.data_type):
            errors.append(f"Configuration '{key}' must be of type {rule.data_type.__name__}")
        
        # 检查值范围
        if rule.min_value is not None and value < rule.min_value:
            errors.append(f"Configuration '{key}' must be >= {rule.min_value}")
        
        if rule.max_value is not None and value > rule.max_value:
            errors.append(f"Configuration '{key}' must be <= {rule.max_value}")
        
        # 检查允许的值
        if rule.allowed_values and value not in rule.allowed_values:
            errors.append(f"Configuration '{key}' must be one of {rule.allowed_values}")
        
        # 自定义验证器
        if rule.validator:
            try:
                if not rule.validator(value):
                    errors.append(f"Configuration '{key}' failed custom validation")
            except Exception as e:
                errors.append(f"Configuration '{key}' validation error: {str(e)}")
        
        return errors
    
    def _get_nested_value(self, config: Dict[str, Any], key: str) -> Any:
        """获取嵌套配置值"""
        keys = key.split('.')
        value = config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return None
        
        return value

class ConfigWatcher(FileSystemEventHandler):
    """配置文件监控器"""
    
    def __init__(self, config_manager):
        super().__init__()
        self.config_manager = config_manager
        self.last_modified = {}
    
    def on_modified(self, event):
        """文件修改事件处理"""
        if event.is_directory:
            return
        
        file_path = event.src_path
        
        # 防止重复触发
        current_time = time.time()
        if file_path in self.last_modified:
            if current_time - self.last_modified[file_path] < 1.0:
                return
        
        self.last_modified[file_path] = current_time
        
        # 检查是否是配置文件
        if file_path in self.config_manager.watched_files:
            logger.info(f"Configuration file changed: {file_path}")
            self.config_manager.reload_config(file_path)

class DynamicConfigManager:
    """动态配置管理器"""
    
    def __init__(self):
        self.config: Dict[str, Any] = {}
        self.config_sources: Dict[str, ConfigSource] = {}
        self.watched_files: Set[str] = set()
        self.observer = None
        self.validator = ConfigValidator()
        self.change_callbacks: List[Callable] = []
        self.lock = threading.RLock()
        self.config_history: List[Dict[str, Any]] = []
        self.max_history = 10
        
        # 环境特定配置
        self.environment = os.environ.get('FLASK_ENV', 'production')
        self.config_priority = [
            ConfigSource.ENVIRONMENT,
            ConfigSource.FILE,
            ConfigSource.DATABASE,
            ConfigSource.REMOTE
        ]
    
    def load_from_file(self, file_path: str, watch: bool = True) -> bool:
        """从文件加载配置"""
        try:
            file_path = os.path.abspath(file_path)
            
            if not os.path.exists(file_path):
                logger.warning(f"Configuration file not found: {file_path}")
                return False
            
            # 读取文件内容
            with open(file_path, 'r', encoding='utf-8') as f:
                if file_path.endswith('.yaml') or file_path.endswith('.yml'):
                    file_config = yaml.safe_load(f) or {}
                elif file_path.endswith('.json'):
                    file_config = json.load(f) or {}
                else:
                    logger.error(f"Unsupported config file format: {file_path}")
                    return False
            
            # 环境特定配置
            env_config = file_config.get(self.environment, {})
            if env_config:
                file_config.update(env_config)
            
            with self.lock:
                # 保存历史记录
                self._save_config_history()
                
                # 合并配置
                self._merge_config(file_config, ConfigSource.FILE)
                self.config_sources[file_path] = ConfigSource.FILE
                
                # 监控文件变化
                if watch:
                    self.watched_files.add(file_path)
                    self._start_file_watcher()
            
            logger.info(f"Configuration loaded from file: {file_path}")
            self._notify_config_change('file_loaded', file_path)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to load configuration from {file_path}: {e}")
            return False
    
    def load_from_env(self, prefix: str = "WONIUNOTE_") -> bool:
        """从环境变量加载配置"""
        try:
            env_config = {}
            
            for key, value in os.environ.items():
                if key.startswith(prefix):
                    config_key = key[len(prefix):].lower().replace('_', '.')
                    
                    # 尝试转换数据类型
                    converted_value = self._convert_env_value(value)
                    self._set_nested_value(env_config, config_key, converted_value)
            
            if env_config:
                with self.lock:
                    self._save_config_history()
                    self._merge_config(env_config, ConfigSource.ENVIRONMENT)
                
                logger.info(f"Configuration loaded from environment variables (prefix: {prefix})")
                self._notify_config_change('env_loaded', prefix)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to load configuration from environment: {e}")
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        with self.lock:
            return self._get_nested_value(self.config, key) or default
    
    def set(self, key: str, value: Any, source: ConfigSource = ConfigSource.REMOTE) -> bool:
        """设置配置值"""
        try:
            with self.lock:
                self._save_config_history()
                self._set_nested_value(self.config, key, value)
                self.config_sources[key] = source
            
            logger.info(f"Configuration updated: {key} = {value}")
            self._notify_config_change('value_updated', key)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to set configuration {key}: {e}")
            return False
    
    def validate(self) -> Dict[str, List[str]]:
        """验证当前配置"""
        with self.lock:
            return self.validator.validate_config(self.config)
    
    def reload_config(self, file_path: str = None):
        """重新加载配置"""
        try:
            if file_path:
                # 重新加载特定文件
                self.load_from_file(file_path, watch=False)
            else:
                # 重新加载所有文件
                for watched_file in list(self.watched_files):
                    self.load_from_file(watched_file, watch=False)
            
            # 验证配置
            errors = self.validate()
            if errors:
                logger.warning(f"Configuration validation errors after reload: {errors}")
            else:
                logger.info("Configuration reloaded and validated successfully")
        
        except Exception as e:
            logger.error(f"Configuration reload failed: {e}")
    
    def add_change_callback(self, callback: Callable):
        """添加配置变更回调"""
        with self.lock:
            self.change_callbacks.append(callback)
    
    def remove_change_callback(self, callback: Callable):
        """移除配置变更回调"""
        with self.lock:
            if callback in self.change_callbacks:
                self.change_callbacks.remove(callback)
    
    def get_config_info(self) -> Dict[str, Any]:
        """获取配置信息"""
        with self.lock:
            return {
                'environment': self.environment,
                'config_keys': list(self._flatten_dict(self.config).keys()),
                'watched_files': list(self.watched_files),
                'validation_errors': self.validate(),
                'last_updated': datetime.now().isoformat(),
                'config_hash': self._get_config_hash()
            }
    
    def export_config(self, file_path: str, format: str = 'yaml') -> bool:
        """导出配置到文件"""
        try:
            with self.lock:
                config_copy = self.config.copy()
            
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                if format.lower() == 'yaml':
                    yaml.dump(config_copy, f, default_flow_style=False, allow_unicode=True)
                elif format.lower() == 'json':
                    json.dump(config_copy, f, indent=2, ensure_ascii=False)
                else:
                    raise ValueError(f"Unsupported export format: {format}")
            
            logger.info(f"Configuration exported to: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export configuration: {e}")
            return False
    
    def rollback_config(self, steps: int = 1) -> bool:
        """回滚配置"""
        try:
            with self.lock:
                if len(self.config_history) < steps:
                    logger.warning("Not enough configuration history for rollback")
                    return False
                
                # 获取历史配置
                target_config = self.config_history[-steps]
                
                # 应用历史配置
                self.config = target_config.copy()
                
                # 移除已回滚的历史记录
                self.config_history = self.config_history[:-steps]
            
            logger.info(f"Configuration rolled back {steps} steps")
            self._notify_config_change('rollback', steps)
            
            return True
            
        except Exception as e:
            logger.error(f"Configuration rollback failed: {e}")
            return False
    
    def _merge_config(self, new_config: Dict[str, Any], source: ConfigSource):
        """合并配置"""
        def deep_merge(base: Dict, update: Dict):
            for key, value in update.items():
                if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                    deep_merge(base[key], value)
                else:
                    base[key] = value
        
        deep_merge(self.config, new_config)
    
    def _save_config_history(self):
        """保存配置历史"""
        config_copy = self.config.copy()
        self.config_history.append(config_copy)
        
        # 限制历史记录数量
        if len(self.config_history) > self.max_history:
            self.config_history.pop(0)
    
    def _start_file_watcher(self):
        """启动文件监控"""
        if self.observer is None:
            self.observer = Observer()
            
            # 监控所有配置文件的目录
            watched_dirs = set()
            for file_path in self.watched_files:
                dir_path = os.path.dirname(file_path)
                if dir_path not in watched_dirs:
                    self.observer.schedule(
                        ConfigWatcher(self),
                        path=dir_path,
                        recursive=False
                    )
                    watched_dirs.add(dir_path)
            
            self.observer.start()
            logger.info("Configuration file watcher started")
    
    def _stop_file_watcher(self):
        """停止文件监控"""
        if self.observer:
            self.observer.stop()
            self.observer.join()
            self.observer = None
            logger.info("Configuration file watcher stopped")
    
    def _notify_config_change(self, change_type: str, details: Any):
        """通知配置变更"""
        for callback in self.change_callbacks:
            try:
                callback(change_type, details)
            except Exception as e:
                logger.error(f"Configuration change callback error: {e}")
    
    def _convert_env_value(self, value: str) -> Any:
        """转换环境变量值"""
        # 布尔值
        if value.lower() in ('true', 'false'):
            return value.lower() == 'true'
        
        # 数字
        if value.isdigit():
            return int(value)
        
        # 浮点数
        try:
            return float(value)
        except ValueError:
            pass
        
        # JSON对象/数组
        if value.startswith(('{', '[')):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                pass
        
        # 逗号分隔的列表
        if ',' in value:
            return [item.strip() for item in value.split(',')]
        
        return value
    
    def _get_nested_value(self, config: Dict[str, Any], key: str) -> Any:
        """获取嵌套配置值"""
        keys = key.split('.')
        value = config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return None
        
        return value
    
    def _set_nested_value(self, config: Dict[str, Any], key: str, value: Any):
        """设置嵌套配置值"""
        keys = key.split('.')
        current = config
        
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        
        current[keys[-1]] = value
    
    def _flatten_dict(self, config: Dict[str, Any], prefix: str = '') -> Dict[str, Any]:
        """扁平化字典"""
        result = {}
        
        for key, value in config.items():
            new_key = f"{prefix}.{key}" if prefix else key
            
            if isinstance(value, dict):
                result.update(self._flatten_dict(value, new_key))
            else:
                result[new_key] = value
        
        return result
    
    def _get_config_hash(self) -> str:
        """获取配置哈希值"""
        config_str = json.dumps(self.config, sort_keys=True, default=str)
        return hashlib.md5(config_str.encode()).hexdigest()
    
    def __del__(self):
        """析构函数"""
        self._stop_file_watcher()

# 全局配置管理器实例
_config_manager = None

def get_config_manager() -> DynamicConfigManager:
    """获取配置管理器实例"""
    global _config_manager
    if _config_manager is None:
        _config_manager = DynamicConfigManager()
    return _config_manager

def init_config_management(app, config_files: List[str] = None):
    """初始化配置管理"""
    try:
        config_manager = get_config_manager()
        
        # 加载环境变量
        config_manager.load_from_env()
        
        # 加载配置文件
        if config_files:
            for config_file in config_files:
                config_manager.load_from_file(config_file)
        
        # 添加Flask应用的配置变更回调
        def on_config_change(change_type: str, details: Any):
            logger.info(f"Configuration change detected: {change_type} - {details}")
            
            # 可以在这里添加配置变更后的处理逻辑
            # 例如：重新初始化某些组件、发送通知等
        
        config_manager.add_change_callback(on_config_change)
        
        # 验证配置（非阻塞）
        try:
            errors = config_manager.validate()
            if errors:
                logger.warning(f"Configuration validation warnings: {errors}")
                logger.info("Application will continue with default values for missing configurations")
        except Exception as e:
            logger.warning(f"Configuration validation failed, using defaults: {e}")
        
        # 将配置管理器添加到Flask应用
        app.config_manager = config_manager
        
        logger.info("Configuration management initialized successfully")
        return config_manager
        
    except Exception as e:
        logger.error(f"Failed to initialize configuration management: {e}")
        raise


# 为了兼容性，提供ConfigManager别名
ConfigManager = DynamicConfigManager 