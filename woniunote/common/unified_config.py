#!/usr/bin/env python3
"""
统一的配置管理模块
整合所有配置相关功能：环境变量、配置文件、安全配置等
"""

import os
import json
import yaml
import configparser
import threading
from typing import Dict, Any, Optional, List, Union, Callable
from pathlib import Path
from dataclasses import dataclass, asdict, field
from enum import Enum
import time

from .unified_logging import get_logger

logger = get_logger('unified_config')

# ==================== 枚举定义 ====================

class ConfigSource(Enum):
    """配置源"""
    ENVIRONMENT = "environment"      # 环境变量
    FILE = "file"                   # 配置文件
    DATABASE = "database"           # 数据库
    REMOTE = "remote"               # 远程配置
    DEFAULT = "default"             # 默认值

class ConfigFormat(Enum):
    """配置格式"""
    JSON = "json"
    YAML = "yaml"
    INI = "ini"
    ENV = "env"
    PYTHON = "python"

# ==================== 数据类定义 ====================

@dataclass
class ConfigItem:
    """配置项"""
    key: str
    value: Any
    source: ConfigSource
    description: str = ""
    required: bool = False
    sensitive: bool = False
    validation_rules: List[str] = field(default_factory=list)
    last_updated: Optional[str] = None

@dataclass
class ConfigSection:
    """配置节"""
    name: str
    items: Dict[str, ConfigItem] = field(default_factory=dict)
    description: str = ""

@dataclass
class ConfigValidation:
    """配置验证结果"""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

# ==================== 环境变量验证器 ====================

class EnvironmentValidator:
    """环境变量验证器"""
    
    def __init__(self):
        self.required_vars = set()
        self.optional_vars = set()
        self.validation_rules = {}
    
    def add_required(self, var_name: str, description: str = ""):
        """添加必需的环境变量"""
        self.required_vars.add(var_name)
        if description:
            self.validation_rules[var_name] = description
    
    def add_optional(self, var_name: str, description: str = ""):
        """添加可选的环境变量"""
        self.optional_vars.add(var_name)
        if description:
            self.validation_rules[var_name] = description
    
    def validate(self) -> ConfigValidation:
        """验证环境变量"""
        errors = []
        warnings = []
        
        # 检查必需的环境变量
        for var in self.required_vars:
            if not os.getenv(var):
                errors.append(f"必需的环境变量 {var} 未设置")
            elif not os.getenv(var).strip():
                errors.append(f"环境变量 {var} 不能为空")
        
        # 检查可选的环境变量
        for var in self.optional_vars:
            if os.getenv(var) is not None and not os.getenv(var).strip():
                warnings.append(f"环境变量 {var} 为空")
        
        return ConfigValidation(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def get_missing_vars(self) -> List[str]:
        """获取缺失的环境变量"""
        return [var for var in self.required_vars if not os.getenv(var)]

# ==================== 配置文件加载器 ====================

class ConfigFileLoader:
    """配置文件加载器"""
    
    def __init__(self):
        self.supported_formats = {
            '.json': self._load_json,
            '.yaml': self._load_yaml,
            '.yml': self._load_yaml,
            '.ini': self._load_ini,
            '.cfg': self._load_ini,
            '.conf': self._load_ini,
            '.py': self._load_python
        }
    
    def load_config(self, file_path: str) -> Dict[str, Any]:
        """加载配置文件"""
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {file_path}")
        
        file_ext = file_path.suffix.lower()
        loader = self.supported_formats.get(file_ext)
        
        if not loader:
            raise ValueError(f"不支持的配置文件格式: {file_ext}")
        
        try:
            return loader(file_path)
        except Exception as e:
            logger.error(f"加载配置文件失败 {file_path}: {e}")
            raise
    
    def _load_json(self, file_path: Path) -> Dict[str, Any]:
        """加载JSON配置文件"""
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _load_yaml(self, file_path: Path) -> Dict[str, Any]:
        """加载YAML配置文件"""
        try:
            import yaml
            with open(file_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except ImportError:
            logger.error("PyYAML未安装，无法加载YAML配置文件")
            raise ImportError("PyYAML未安装")
    
    def _load_ini(self, file_path: Path) -> Dict[str, Any]:
        """加载INI配置文件"""
        config = configparser.ConfigParser()
        config.read(file_path, encoding='utf-8')
        
        result = {}
        for section in config.sections():
            result[section] = dict(config.items(section))
        
        return result
    
    def _load_python(self, file_path: Path) -> Dict[str, Any]:
        """加载Python配置文件"""
        import importlib.util
        
        spec = importlib.util.spec_from_file_location("config", file_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # 提取配置变量（以大写开头的变量）
        config = {}
        for attr_name in dir(module):
            if attr_name.isupper() and not attr_name.startswith('_'):
                config[attr_name] = getattr(module, attr_name)
        
        return config

# ==================== 配置验证器 ====================

class ConfigValidator:
    """配置验证器"""
    
    def __init__(self):
        self.validators = {}
        self._register_default_validators()
    
    def _register_default_validators(self):
        """注册默认验证器"""
        self.validators.update({
            'required': self._validate_required,
            'type': self._validate_type,
            'range': self._validate_range,
            'pattern': self._validate_pattern,
            'enum': self._validate_enum,
            'custom': self._validate_custom
        })
    
    def add_validator(self, name: str, validator_func: Callable):
        """添加自定义验证器"""
        self.validators[name] = validator_func
    
    def validate_item(self, item: ConfigItem, value: Any) -> List[str]:
        """验证配置项"""
        errors = []
        
        for rule in item.validation_rules:
            if ':' in rule:
                validator_name, rule_value = rule.split(':', 1)
            else:
                validator_name, rule_value = rule, None
            
            validator = self.validators.get(validator_name)
            if validator:
                try:
                    error = validator(value, rule_value, item)
                    if error:
                        errors.append(error)
                except Exception as e:
                    errors.append(f"验证器 {validator_name} 执行失败: {e}")
            else:
                errors.append(f"未知的验证器: {validator_name}")
        
        return errors
    
    def _validate_required(self, value: Any, rule_value: str, item: ConfigItem) -> Optional[str]:
        """验证必需性"""
        if item.required and (value is None or str(value).strip() == ""):
            return f"配置项 {item.key} 是必需的"
        return None
    
    def _validate_type(self, value: Any, rule_value: str, item: ConfigItem) -> Optional[str]:
        """验证类型"""
        if value is None:
            return None
        
        expected_type = rule_value.lower()
        if expected_type == 'int':
            try:
                int(value)
            except (ValueError, TypeError):
                return f"配置项 {item.key} 必须是整数"
        elif expected_type == 'float':
            try:
                float(value)
            except (ValueError, TypeError):
                return f"配置项 {item.key} 必须是浮点数"
        elif expected_type == 'bool':
            if str(value).lower() not in ['true', 'false', '1', '0', 'yes', 'no']:
                return f"配置项 {item.key} 必须是布尔值"
        
        return None
    
    def _validate_range(self, value: Any, rule_value: str, item: ConfigItem) -> Optional[str]:
        """验证范围"""
        if value is None:
            return None
        
        try:
            if ',' in rule_value:
                min_val, max_val = rule_value.split(',')
                min_val = float(min_val.strip())
                max_val = float(max_val.strip())
                
                if float(value) < min_val or float(value) > max_val:
                    return f"配置项 {item.key} 必须在 {min_val} 和 {max_val} 之间"
        except (ValueError, TypeError):
            pass
        
        return None
    
    def _validate_pattern(self, value: Any, rule_value: str, item: ConfigItem) -> Optional[str]:
        """验证模式"""
        if value is None:
            return None
        
        import re
        if not re.match(rule_value, str(value)):
            return f"配置项 {item.key} 不符合模式 {rule_value}"
        
        return None
    
    def _validate_enum(self, value: Any, rule_value: str, item: ConfigItem) -> Optional[str]:
        """验证枚举值"""
        if value is None:
            return None
        
        allowed_values = [v.strip() for v in rule_value.split(',')]
        if str(value) not in allowed_values:
            return f"配置项 {item.key} 必须是以下值之一: {', '.join(allowed_values)}"
        
        return None
    
    def _validate_custom(self, value: Any, rule_value: str, item: ConfigItem) -> Optional[str]:
        """自定义验证"""
        # 这里可以实现自定义验证逻辑
        return None

# ==================== 统一配置管理器 ====================

class UnifiedConfigManager:
    """统一的配置管理器"""
    
    def __init__(self, config_dir: str = "configs"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)
        
        self.environment_validator = EnvironmentValidator()
        self.file_loader = ConfigFileLoader()
        self.validator = ConfigValidator()
        
        self.config_sections: Dict[str, ConfigSection] = {}
        self.config_cache: Dict[str, Any] = {}
        self.watchers: List[Callable] = []
        self._lock = threading.RLock()
        
        # 设置默认配置
        self._setup_default_config()
        
        logger.info("统一配置管理器初始化完成")
    
    def _setup_default_config(self):
        """设置默认配置"""
        # 数据库配置
        db_section = ConfigSection("database", description="数据库配置")
        db_section.items.update({
            'host': ConfigItem('host', 'localhost', ConfigSource.DEFAULT, '数据库主机', True),
            'port': ConfigItem('port', 3306, ConfigSource.DEFAULT, '数据库端口', True),
            'username': ConfigItem('username', '', ConfigSource.DEFAULT, '数据库用户名', True),
            'password': ConfigItem('password', '', ConfigSource.DEFAULT, '数据库密码', True, True),
            'database': ConfigItem('database', '', ConfigSource.DEFAULT, '数据库名', True)
        })
        self.config_sections['database'] = db_section
        
        # Redis配置
        redis_section = ConfigSection("redis", description="Redis配置")
        redis_section.items.update({
            'host': ConfigItem('host', 'localhost', ConfigSource.DEFAULT, 'Redis主机', False),
            'port': ConfigItem('port', 6379, ConfigSource.DEFAULT, 'Redis端口', False),
            'password': ConfigItem('password', '', ConfigSource.DEFAULT, 'Redis密码', False, True),
            'db': ConfigItem('db', 0, ConfigSource.DEFAULT, 'Redis数据库', False)
        })
        self.config_sections['redis'] = redis_section
        
        # 应用配置
        app_section = ConfigSection("app", description="应用配置")
        app_section.items.update({
            'debug': ConfigItem('debug', False, ConfigSource.DEFAULT, '调试模式', False),
            'secret_key': ConfigItem('secret_key', '', ConfigSource.DEFAULT, '密钥', True, True),
            'host': ConfigItem('host', '127.0.0.1', ConfigSource.DEFAULT, '主机地址', False),
            'port': ConfigItem('port', 5000, ConfigSource.DEFAULT, '端口号', False)
        })
        self.config_sections['app'] = app_section
    
    def load_from_file(self, file_path: str, section: str = None) -> bool:
        """从文件加载配置"""
        try:
            config_data = self.file_loader.load_config(file_path)
            
            with self._lock:
                if section:
                    # 加载到指定节
                    if section not in self.config_sections:
                        self.config_sections[section] = ConfigSection(section)
                    
                    for key, value in config_data.items():
                        if key in self.config_sections[section].items:
                            self.config_sections[section].items[key].value = value
                            self.config_sections[section].items[key].source = ConfigSource.FILE
                        else:
                            # 创建新的配置项
                            self.config_sections[section].items[key] = ConfigItem(
                                key, value, ConfigSource.FILE, required=False
                            )
                else:
                    # 加载到根级别
                    for key, value in config_data.items():
                        self.config_cache[key] = value
            
            logger.info(f"配置文件加载成功: {file_path}")
            self._notify_watchers()
            return True
            
        except Exception as e:
            logger.error(f"配置文件加载失败: {e}")
            return False
    
    def load_from_environment(self, prefix: str = "WONIU_"):
        """从环境变量加载配置"""
        with self._lock:
            for section_name, section in self.config_sections.items():
                for item_name, item in section.items.items():
                    env_key = f"{prefix}{section_name.upper()}_{item_name.upper()}"
                    env_value = os.getenv(env_key)
                    
                    if env_value is not None:
                        # 类型转换
                        if item.validation_rules:
                            for rule in item.validation_rules:
                                if rule.startswith('type:'):
                                    _, expected_type = rule.split(':', 1)
                                    try:
                                        if expected_type == 'int':
                                            env_value = int(env_value)
                                        elif expected_type == 'float':
                                            env_value = float(env_value)
                                        elif expected_type == 'bool':
                                            env_value = env_value.lower() in ['true', '1', 'yes']
                                    except (ValueError, TypeError):
                                        logger.warning(f"环境变量类型转换失败: {env_key}={env_value}")
                        
                        item.value = env_value
                        item.source = ConfigSource.ENVIRONMENT
                        item.last_updated = str(time.time())
        
        logger.info("环境变量配置加载完成")
        self._notify_watchers()
    
    def get(self, key: str, section: str = None, default: Any = None) -> Any:
        """获取配置值"""
        with self._lock:
            if section:
                # 从指定节获取
                if section in self.config_sections:
                    if key in self.config_sections[section].items:
                        return self.config_sections[section].items[key].value
            else:
                # 从根级别获取
                if key in self.config_cache:
                    return self.config_cache[key]
            
            return default
    
    def set(self, key: str, value: Any, section: str = None) -> bool:
        """设置配置值"""
        try:
            with self._lock:
                if section:
                    # 设置到指定节
                    if section not in self.config_sections:
                        self.config_sections[section] = ConfigSection(section)
                    
                    if key in self.config_sections[section].items:
                        self.config_sections[section].items[key].value = value
                        self.config_sections[section].items[key].last_updated = str(time.time())
                    else:
                        self.config_sections[section].items[key] = ConfigItem(
                            key, value, ConfigSource.DEFAULT, required=False
                        )
                else:
                    # 设置到根级别
                    self.config_cache[key] = value
            
            self._notify_watchers()
            return True
            
        except Exception as e:
            logger.error(f"设置配置失败: {e}")
            return False
    
    def validate_config(self) -> ConfigValidation:
        """验证配置"""
        errors = []
        warnings = []
        
        # 验证环境变量
        env_validation = self.environment_validator.validate()
        errors.extend(env_validation.errors)
        warnings.extend(env_validation.warnings)
        
        # 验证配置项
        with self._lock:
            for section_name, section in self.config_sections.items():
                for item_name, item in section.items.items():
                    if item.validation_rules:
                        item_errors = self.validator.validate_item(item, item.value)
                        errors.extend([f"{section_name}.{item_name}: {error}" for error in item_errors])
        
        return ConfigValidation(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def get_config_summary(self) -> Dict[str, Any]:
        """获取配置摘要"""
        with self._lock:
            summary = {
                'sections': {},
                'cache': self.config_cache.copy(),
                'validation': self.validate_config()
            }
            
            for section_name, section in self.config_sections.items():
                summary['sections'][section_name] = {
                    'description': section.description,
                    'items_count': len(section.items),
                    'items': {
                        name: {
                            'value': item.value if not item.sensitive else '***',
                            'source': item.source.value,
                            'required': item.required,
                            'last_updated': item.last_updated
                        }
                        for name, item in section.items.items()
                    }
                }
            
            return summary
    
    def add_watcher(self, callback: Callable):
        """添加配置变更监听器"""
        self.watchers.append(callback)
    
    def remove_watcher(self, callback: Callable):
        """移除配置变更监听器"""
        if callback in self.watchers:
            self.watchers.remove(callback)
    
    def _notify_watchers(self):
        """通知监听器"""
        for watcher in self.watchers:
            try:
                watcher()
            except Exception as e:
                logger.error(f"配置监听器执行失败: {e}")

# ==================== 全局实例和工厂函数 ====================

# 全局配置管理器实例
_global_config_manager = None

def init_unified_config_manager(config_dir: str = "configs") -> UnifiedConfigManager:
    """初始化全局配置管理器"""
    global _global_config_manager
    _global_config_manager = UnifiedConfigManager(config_dir)
    return _global_config_manager

def get_config_manager() -> Optional[UnifiedConfigManager]:
    """获取全局配置管理器"""
    return _global_config_manager

def get_config(key: str, section: str = None, default: Any = None) -> Any:
    """获取配置值"""
    if _global_config_manager:
        return _global_config_manager.get(key, section, default)
    return default

def set_config(key: str, value: Any, section: str = None) -> bool:
    """设置配置值"""
    if _global_config_manager:
        return _global_config_manager.set(key, value, section)
    return False

# ==================== 向后兼容 ====================

# 为了向后兼容，保留旧的函数名
init_config_manager = init_unified_config_manager
get_config_manager_legacy = get_config_manager
init_secure_config = init_unified_config_manager
get_secure_config = get_config_manager
