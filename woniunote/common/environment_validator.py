#!/usr/bin/env python3
"""
环境变量验证和配置管理系统
提供启动时的环境检查和配置验证
"""

import os
import sys
import re
from typing import Dict, List, Optional, Union, Any
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from woniunote.common.simple_logger import get_simple_logger

logger = get_simple_logger('environment_validator')

class ValidationSeverity(Enum):
    """验证问题严重程度"""
    ERROR = "error"      # 严重错误，阻止启动
    WARNING = "warning"  # 警告，可以启动但需要注意
    INFO = "info"        # 信息性提示

@dataclass
class ValidationResult:
    """验证结果"""
    severity: ValidationSeverity
    variable: str
    message: str
    suggestion: Optional[str] = None
    current_value: Optional[str] = None

class EnvironmentValidator:
    """环境变量验证器"""
    
    def __init__(self):
        self.results: List[ValidationResult] = []
        self.required_vars = self._get_required_variables()
        self.optional_vars = self._get_optional_variables()
    
    def _get_required_variables(self) -> Dict[str, Dict[str, Any]]:
        """获取必需的环境变量配置"""
        return {
            'SECRET_KEY': {
                'description': 'Flask应用密钥',
                'validator': self._validate_secret_key,
                'default': None,
                'production_required': True
            },
            'DATABASE_URL': {
                'description': '数据库连接URL',
                'validator': self._validate_database_url,
                'default': 'mysql+pymysql://root:123456@localhost:3306/woniunote',
                'production_required': True
            },
            'FLASK_ENV': {
                'description': 'Flask运行环境',
                'validator': self._validate_flask_env,
                'default': 'production',
                'production_required': False
            }
        }
    
    def _get_optional_variables(self) -> Dict[str, Dict[str, Any]]:
        """获取可选的环境变量配置"""
        return {
            'REDIS_HOST': {
                'description': 'Redis主机地址',
                'validator': self._validate_host,
                'default': 'localhost'
            },
            'REDIS_PORT': {
                'description': 'Redis端口',
                'validator': self._validate_port,
                'default': '6379'
            },
            'REDIS_PASSWORD': {
                'description': 'Redis密码',
                'validator': self._validate_password,
                'default': None
            },
            'MAIL_SERVER': {
                'description': '邮件服务器地址',
                'validator': self._validate_host,
                'default': None
            },
            'MAIL_PORT': {
                'description': '邮件服务器端口',
                'validator': self._validate_port,
                'default': '587'
            },
            'MAIL_USERNAME': {
                'description': '邮件用户名',
                'validator': self._validate_email,
                'default': None
            },
            'MAIL_PASSWORD': {
                'description': '邮件密码',
                'validator': self._validate_password,
                'default': None
            },
            'LOG_LEVEL': {
                'description': '日志级别',
                'validator': self._validate_log_level,
                'default': 'INFO'
            },
            'MAX_CONTENT_LENGTH': {
                'description': '最大文件上传大小',
                'validator': self._validate_file_size,
                'default': '16777216'  # 16MB
            }
        }
    
    def validate_all(self) -> bool:
        """验证所有环境变量"""
        self.results.clear()
        
        # 检查必需的环境变量
        for var_name, config in self.required_vars.items():
            self._validate_variable(var_name, config, required=True)
        
        # 检查可选的环境变量
        for var_name, config in self.optional_vars.items():
            self._validate_variable(var_name, config, required=False)
        
        # 检查生产环境特殊要求
        self._validate_production_requirements()
        
        # 检查文件系统权限
        self._validate_file_permissions()
        
        # 检查Python版本
        self._validate_python_version()
        
        return not any(result.severity == ValidationSeverity.ERROR for result in self.results)
    
    def _validate_variable(self, var_name: str, config: Dict[str, Any], required: bool):
        """验证单个环境变量"""
        value = os.environ.get(var_name)
        
        if value is None:
            if required and config.get('production_required') and self._is_production():
                self.results.append(ValidationResult(
                    severity=ValidationSeverity.ERROR,
                    variable=var_name,
                    message=f"生产环境必须设置{var_name}",
                    suggestion=f"设置环境变量: export {var_name}=<value>",
                    current_value=None
                ))
            elif required:
                default = config.get('default')
                if default:
                    self.results.append(ValidationResult(
                        severity=ValidationSeverity.WARNING,
                        variable=var_name,
                        message=f"{var_name}未设置，将使用默认值",
                        suggestion=f"建议设置: export {var_name}=<value>",
                        current_value=f"默认: {default}"
                    ))
                else:
                    self.results.append(ValidationResult(
                        severity=ValidationSeverity.WARNING,
                        variable=var_name,
                        message=f"推荐设置{var_name}",
                        suggestion=f"设置环境变量: export {var_name}=<value>",
                        current_value=None
                    ))
        else:
            # 验证值的格式
            validator = config.get('validator')
            if validator:
                is_valid, error_msg = validator(value)
                if not is_valid:
                    self.results.append(ValidationResult(
                        severity=ValidationSeverity.ERROR,
                        variable=var_name,
                        message=f"{var_name}格式无效: {error_msg}",
                        suggestion="请检查并修正环境变量值",
                        current_value=value[:50] + "..." if len(value) > 50 else value
                    ))
    
    def _is_production(self) -> bool:
        """检查是否为生产环境"""
        env = os.environ.get('FLASK_ENV', 'production').lower()
        return env in ['production', 'prod']
    
    def _validate_secret_key(self, value: str) -> tuple[bool, str]:
        """验证SECRET_KEY"""
        if len(value) < 32:
            return False, "密钥长度至少32字符"
        
        if value in ['dev-secret-key', 'development', 'secret']:
            return False, "不能使用默认或常见的密钥"
        
        # 检查是否包含多种字符类型
        has_upper = any(c.isupper() for c in value)
        has_lower = any(c.islower() for c in value)
        has_digit = any(c.isdigit() for c in value)
        has_special = any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in value)
        
        if not (has_upper and has_lower and has_digit):
            return False, "密钥应包含大写字母、小写字母和数字"
        
        return True, ""
    
    def _validate_database_url(self, value: str) -> tuple[bool, str]:
        """验证数据库URL"""
        # 基本格式检查
        if not value.startswith(('mysql://', 'mysql+pymysql://', 'postgresql://', 'sqlite://')):
            return False, "不支持的数据库类型"
        
        # 检查是否包含密码（安全提醒）
        if '://' in value and '@' in value:
            # 提取密码部分进行检查
            try:
                protocol_part, rest = value.split('://', 1)
                if '@' in rest:
                    auth_part, server_part = rest.split('@', 1)
                    if ':' in auth_part:
                        username, password = auth_part.split(':', 1)
                        if password == 'password' or password == '123456':
                            return False, "数据库密码过于简单"
            except:
                pass
        
        return True, ""
    
    def _validate_flask_env(self, value: str) -> tuple[bool, str]:
        """验证Flask环境"""
        valid_envs = ['development', 'testing', 'production', 'dev', 'test', 'prod']
        if value.lower() not in valid_envs:
            return False, f"无效的环境值，支持: {', '.join(valid_envs)}"
        return True, ""
    
    def _validate_host(self, value: str) -> tuple[bool, str]:
        """验证主机地址"""
        # 简单的主机名/IP验证
        if not value:
            return False, "主机地址不能为空"
        
        # 检查是否为有效的域名或IP
        if re.match(r'^[a-zA-Z0-9.-]+$', value):
            return True, ""
        
        return False, "无效的主机地址格式"
    
    def _validate_port(self, value: str) -> tuple[bool, str]:
        """验证端口号"""
        try:
            port = int(value)
            if 1 <= port <= 65535:
                return True, ""
            else:
                return False, "端口号必须在1-65535之间"
        except ValueError:
            return False, "端口号必须是数字"
    
    def _validate_password(self, value: str) -> tuple[bool, str]:
        """验证密码强度"""
        if len(value) < 8:
            return False, "密码长度至少8字符"
        
        if value.lower() in ['password', '12345678', 'qwertyui']:
            return False, "密码过于简单"
        
        return True, ""
    
    def _validate_email(self, value: str) -> tuple[bool, str]:
        """验证邮箱格式"""
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if re.match(email_pattern, value):
            return True, ""
        return False, "无效的邮箱格式"
    
    def _validate_log_level(self, value: str) -> tuple[bool, str]:
        """验证日志级别"""
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if value.upper() in valid_levels:
            return True, ""
        return False, f"无效的日志级别，支持: {', '.join(valid_levels)}"
    
    def _validate_file_size(self, value: str) -> tuple[bool, str]:
        """验证文件大小"""
        try:
            size = int(value)
            if size > 0:
                return True, ""
            else:
                return False, "文件大小必须大于0"
        except ValueError:
            return False, "文件大小必须是数字（字节）"
    
    def _validate_production_requirements(self):
        """验证生产环境特殊要求"""
        if not self._is_production():
            return
        
        # 生产环境不应该开启调试模式
        if os.environ.get('FLASK_DEBUG', '').lower() in ['true', '1', 'on']:
            self.results.append(ValidationResult(
                severity=ValidationSeverity.ERROR,
                variable='FLASK_DEBUG',
                message="生产环境不应开启调试模式",
                suggestion="设置 FLASK_DEBUG=false 或删除该变量"
            ))
        
        # 检查SSL配置
        if not os.environ.get('SSL_CERT_PATH') and not os.environ.get('SSL_KEY_PATH'):
            self.results.append(ValidationResult(
                severity=ValidationSeverity.WARNING,
                variable='SSL_CERT_PATH',
                message="生产环境建议配置SSL证书",
                suggestion="设置 SSL_CERT_PATH 和 SSL_KEY_PATH"
            ))
    
    def _validate_file_permissions(self):
        """验证文件系统权限"""
        # 检查日志目录
        log_dir = Path('logs')
        if not log_dir.exists():
            try:
                log_dir.mkdir(parents=True, exist_ok=True)
            except PermissionError:
                self.results.append(ValidationResult(
                    severity=ValidationSeverity.ERROR,
                    variable='FILE_PERMISSIONS',
                    message="无法创建日志目录",
                    suggestion="检查当前用户是否有写权限"
                ))
        
        # 检查上传目录
        upload_dir = Path('woniunote/resource/upload')
        if not upload_dir.exists():
            try:
                upload_dir.mkdir(parents=True, exist_ok=True)
            except PermissionError:
                self.results.append(ValidationResult(
                    severity=ValidationSeverity.ERROR,
                    variable='FILE_PERMISSIONS',
                    message="无法创建上传目录",
                    suggestion="检查当前用户是否有写权限"
                ))
    
    def _validate_python_version(self):
        """验证Python版本"""
        version = sys.version_info
        
        if version.major < 3:
            self.results.append(ValidationResult(
                severity=ValidationSeverity.ERROR,
                variable='PYTHON_VERSION',
                message="需要Python 3.x版本",
                suggestion="请升级到Python 3.8或更高版本",
                current_value=f"{version.major}.{version.minor}.{version.micro}"
            ))
        elif version.minor < 8:
            self.results.append(ValidationResult(
                severity=ValidationSeverity.WARNING,
                variable='PYTHON_VERSION',
                message="建议使用Python 3.8或更高版本",
                suggestion="当前版本可能缺少某些特性",
                current_value=f"{version.major}.{version.minor}.{version.micro}"
            ))
    
    def print_results(self):
        """打印验证结果"""
        if not self.results:
            print("✅ 所有环境变量验证通过！")
            return
        
        errors = [r for r in self.results if r.severity == ValidationSeverity.ERROR]
        warnings = [r for r in self.results if r.severity == ValidationSeverity.WARNING]
        infos = [r for r in self.results if r.severity == ValidationSeverity.INFO]
        
        print(f"\n=== 环境验证结果 ===")
        print(f"错误: {len(errors)}, 警告: {len(warnings)}, 信息: {len(infos)}\n")
        
        for result in self.results:
            icon = {"error": "❌", "warning": "⚠️", "info": "ℹ️"}[result.severity.value]
            print(f"{icon} {result.variable}: {result.message}")
            
            if result.current_value:
                print(f"   当前值: {result.current_value}")
            
            if result.suggestion:
                print(f"   建议: {result.suggestion}")
            
            print()
    
    def get_missing_vars(self) -> List[str]:
        """获取缺失的环境变量列表"""
        return [result.variable for result in self.results 
                if result.severity == ValidationSeverity.ERROR 
                and "未设置" in result.message]

def validate_environment() -> bool:
    """环境验证入口函数"""
    validator = EnvironmentValidator()
    is_valid = validator.validate_all()
    validator.print_results()
    
    if not is_valid:
        logger.error("环境验证失败，请修复错误后重新启动")
    else:
        logger.info("环境验证通过")
    
    return is_valid

if __name__ == '__main__':
    validate_environment()