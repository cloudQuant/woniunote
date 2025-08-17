"""
安全配置管理模块
提供环境变量支持、配置验证和安全默认值
"""
import os
import sys
import logging
import secrets
from typing import Any, Dict, Optional, Union, List
from pathlib import Path

logger = logging.getLogger(__name__)

class ConfigError(Exception):
    """配置错误异常"""
    pass

class SecureConfigManager:
    """安全配置管理器"""
    
    def __init__(self, app=None):
        self.app = app
        self.config_cache = {}
        self.required_env_vars = set()
        self.config_validators = {}
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """初始化应用配置"""
        self.app = app
        self._load_environment_config()
        self._validate_security_config()
        self._set_secure_defaults()
        
    def _load_environment_config(self):
        """加载环境变量配置"""
        env_mappings = {
            'SECRET_KEY': 'SECRET_KEY',
            'DATABASE_URL': 'SQLALCHEMY_DATABASE_URI', 
            'REDIS_URL': 'REDIS_URL',
            'DEBUG': 'DEBUG',
            'TESTING': 'TESTING',
            'CSRF_SECRET_KEY': 'CSRF_SECRET_KEY',
            'SESSION_SECRET_KEY': 'SESSION_SECRET_KEY',
            'JWT_SECRET_KEY': 'JWT_SECRET_KEY',
            'UPLOAD_FOLDER': 'UPLOAD_FOLDER',
            'MAX_CONTENT_LENGTH': 'MAX_CONTENT_LENGTH',
            'MAIL_SERVER': 'MAIL_SERVER',
            'MAIL_USERNAME': 'MAIL_USERNAME',
            'MAIL_PASSWORD': 'MAIL_PASSWORD',
            'SSL_CERT_PATH': 'SSL_CERT_PATH',
            'SSL_KEY_PATH': 'SSL_KEY_PATH'
        }
        
        for env_var, config_key in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                # 类型转换
                if config_key in ['DEBUG', 'TESTING']:
                    value = value.lower() in ('true', '1', 'yes', 'on')
                elif config_key == 'MAX_CONTENT_LENGTH':
                    try:
                        value = int(value)
                    except ValueError:
                        logger.warning(f"无效的 {config_key} 值: {value}")
                        continue
                
                self.app.config[config_key] = value
                logger.info(f"从环境变量加载配置: {config_key}")
    
    def _validate_security_config(self):
        """验证安全配置"""
        errors = []
        
        # 检查关键安全配置
        secret_key = self.app.config.get('SECRET_KEY')
        if not secret_key:
            errors.append("SECRET_KEY 未设置")
        elif secret_key in ['your-secret-key', 'change-me', 'default']:
            errors.append("SECRET_KEY 使用了不安全的默认值")
        elif len(secret_key) < 32:
            errors.append("SECRET_KEY 长度应至少为32个字符")
        
        # 检查生产环境配置
        if not self.app.config.get('DEBUG', False):
            if self.app.config.get('SESSION_COOKIE_SECURE') is False:
                logger.warning("生产环境建议启用 SESSION_COOKIE_SECURE")
            
            if not self.app.config.get('SESSION_COOKIE_HTTPONLY', True):
                errors.append("SESSION_COOKIE_HTTPONLY 应该为 True")
        
        # 检查数据库连接
        db_uri = self.app.config.get('SQLALCHEMY_DATABASE_URI')
        if not db_uri:
            errors.append("SQLALCHEMY_DATABASE_URI 未设置")
        elif 'password' in db_uri.lower() and 'localhost' not in db_uri:
            logger.warning("数据库连接字符串包含密码，确保环境安全")
        
        if errors:
            error_msg = "配置安全检查失败:\n" + "\n".join(f"- {error}" for error in errors)
            raise ConfigError(error_msg)
    
    def _set_secure_defaults(self):
        """设置安全默认值"""
        defaults = {
            # 会话安全
            'SESSION_COOKIE_SECURE': not self.app.config.get('DEBUG', False),
            'SESSION_COOKIE_HTTPONLY': True,
            'SESSION_COOKIE_SAMESITE': 'Lax',
            'SESSION_COOKIE_NAME': 'woniunote_session',
            'PERMANENT_SESSION_LIFETIME': 3600,  # 1小时
            
            # CSRF 保护
            'CSRF_ENABLED': True,
            'CSRF_TOKEN_TIMEOUT': 3600,
            'CSRF_HEADER_NAME': 'X-CSRFToken',
            'CSRF_FIELD_NAME': 'csrf_token',
            
            # 文件上传安全
            'MAX_CONTENT_LENGTH': 16 * 1024 * 1024,  # 16MB
            'UPLOAD_EXTENSIONS': ['.jpg', '.jpeg', '.png', '.gif', '.pdf', '.doc', '.docx'],
            'UPLOAD_FOLDER': self._get_secure_upload_folder(),
            
            # 安全头
            'SECURITY_HEADERS': {
                'X-Content-Type-Options': 'nosniff',
                'X-Frame-Options': 'DENY',
                'X-XSS-Protection': '1; mode=block',
                'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
                'Content-Security-Policy': self._get_csp_policy()
            },
            
            # 数据库连接池安全
            'SQLALCHEMY_POOL_TIMEOUT': 30,
            'SQLALCHEMY_POOL_RECYCLE': 1800,
            'SQLALCHEMY_POOL_PRE_PING': True,
            
            # 日志配置
            'LOG_LEVEL': 'INFO' if not self.app.config.get('DEBUG') else 'DEBUG',
            'LOG_MAX_BYTES': 10 * 1024 * 1024,  # 10MB
            'LOG_BACKUP_COUNT': 5,
        }
        
        # 生成缺失的密钥
        if not self.app.config.get('SECRET_KEY'):
            self.app.config['SECRET_KEY'] = secrets.token_hex(32)
            logger.warning("已生成临时 SECRET_KEY，请在生产环境中设置固定值")
        
        if not self.app.config.get('CSRF_SECRET_KEY'):
            self.app.config['CSRF_SECRET_KEY'] = secrets.token_hex(32)
        
        # 应用默认配置
        for key, value in defaults.items():
            if key not in self.app.config:
                self.app.config[key] = value
    
    def _get_secure_upload_folder(self) -> str:
        """获取安全的上传文件夹路径"""
        # 在应用目录外创建上传文件夹
        app_root = Path(self.app.root_path).parent
        upload_folder = app_root / 'uploads'
        upload_folder.mkdir(exist_ok=True)
        
        # 设置安全权限（仅限 Unix 系统）
        if hasattr(os, 'chmod'):
            os.chmod(upload_folder, 0o755)
        
        return str(upload_folder)
    
    def _get_csp_policy(self) -> str:
        """获取内容安全策略"""
        if self.app.config.get('DEBUG'):
            # 开发环境较宽松的 CSP
            return ("default-src 'self'; "
                   "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                   "style-src 'self' 'unsafe-inline'; "
                   "img-src 'self' data: https:; "
                   "font-src 'self' https:")
        else:
            # 生产环境严格的 CSP
            return ("default-src 'self'; "
                   "script-src 'self'; "
                   "style-src 'self' 'unsafe-inline'; "
                   "img-src 'self' data: https:; "
                   "font-src 'self'; "
                   "connect-src 'self'; "
                   "frame-ancestors 'none'")
    
    def get_config(self, key: str, default: Any = None, required: bool = False) -> Any:
        """安全获取配置值"""
        value = self.app.config.get(key, default)
        
        if required and value is None:
            raise ConfigError(f"必需的配置项 {key} 未设置")
        
        return value
    
    def validate_config_type(self, key: str, expected_type: type) -> bool:
        """验证配置类型"""
        value = self.app.config.get(key)
        if value is not None and not isinstance(value, expected_type):
            logger.error(f"配置项 {key} 类型错误，期望 {expected_type.__name__}，实际 {type(value).__name__}")
            return False
        return True
    
    def mask_sensitive_value(self, key: str, value: Any) -> str:
        """掩码敏感配置值用于日志"""
        sensitive_keys = ['PASSWORD', 'SECRET', 'KEY', 'TOKEN', 'PRIVATE']
        
        if any(sensitive in key.upper() for sensitive in sensitive_keys):
            if isinstance(value, str) and len(value) > 4:
                return f"{value[:2]}{'*' * (len(value) - 4)}{value[-2:]}"
            else:
                return "***"
        
        return str(value)
    
    def log_configuration(self):
        """记录配置信息（掩码敏感信息）"""
        logger.info("应用配置概要:")
        
        important_configs = [
            'DEBUG', 'TESTING', 'SECRET_KEY', 'SQLALCHEMY_DATABASE_URI',
            'SESSION_COOKIE_SECURE', 'CSRF_ENABLED', 'MAX_CONTENT_LENGTH'
        ]
        
        for key in important_configs:
            value = self.app.config.get(key)
            if value is not None:
                masked_value = self.mask_sensitive_value(key, value)
                logger.info(f"  {key}: {masked_value}")
    
    def check_environment(self) -> Dict[str, Any]:
        """检查环境配置状态"""
        checks = {
            'secret_key_set': bool(self.app.config.get('SECRET_KEY')),
            'database_configured': bool(self.app.config.get('SQLALCHEMY_DATABASE_URI')),
            'csrf_enabled': self.app.config.get('CSRF_ENABLED', False),
            'secure_cookies': self.app.config.get('SESSION_COOKIE_SECURE', False),
            'debug_mode': self.app.config.get('DEBUG', False),
            'upload_folder_exists': os.path.exists(self.app.config.get('UPLOAD_FOLDER', '')),
        }
        
        # 计算安全评分
        security_score = sum([
            checks['secret_key_set'],
            checks['csrf_enabled'],
            checks['secure_cookies'] or checks['debug_mode'],  # 开发模式可以不启用
            not checks['debug_mode']  # 生产模式加分
        ]) / 4 * 100
        
        checks['security_score'] = round(security_score, 1)
        
        return checks

def create_config_from_env() -> Dict[str, Any]:
    """从环境变量创建配置字典"""
    config = {}
    
    # 数据库配置
    db_url = os.getenv('DATABASE_URL')
    if db_url:
        config['SQLALCHEMY_DATABASE_URI'] = db_url
    
    # Redis 配置
    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    config['REDIS_URL'] = redis_url
    
    # 安全配置
    config['SECRET_KEY'] = os.getenv('SECRET_KEY', secrets.token_hex(32))
    config['CSRF_SECRET_KEY'] = os.getenv('CSRF_SECRET_KEY', secrets.token_hex(32))
    
    # 应用配置
    config['DEBUG'] = os.getenv('DEBUG', 'False').lower() in ('true', '1', 'yes')
    config['TESTING'] = os.getenv('TESTING', 'False').lower() in ('true', '1', 'yes')
    
    # 文件上传配置
    config['UPLOAD_FOLDER'] = os.getenv('UPLOAD_FOLDER', '/tmp/woniunote_uploads')
    config['MAX_CONTENT_LENGTH'] = int(os.getenv('MAX_CONTENT_LENGTH', '16777216'))  # 16MB
    
    return config

def load_config_file(file_path: str) -> Dict[str, Any]:
    """从文件加载配置"""
    import yaml
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            if file_path.endswith('.yaml') or file_path.endswith('.yml'):
                return yaml.safe_load(f)
            elif file_path.endswith('.json'):
                import json
                return json.load(f)
            else:
                raise ConfigError(f"不支持的配置文件格式: {file_path}")
    
    except FileNotFoundError:
        logger.warning(f"配置文件未找到: {file_path}")
        return {}
    except Exception as e:
        raise ConfigError(f"配置文件加载失败 {file_path}: {e}")

# 全局配置管理器实例
secure_config = SecureConfigManager()