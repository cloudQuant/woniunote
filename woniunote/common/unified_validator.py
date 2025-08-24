#!/usr/bin/env python3
"""
统一的验证器模块
整合所有验证相关功能：输入验证、文件上传验证、权限验证等
"""

import os
import re
import html
import mimetypes
from typing import Dict, Any, Optional, List, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from .unified_logging import get_logger

logger = get_logger('unified_validator')

# ==================== 枚举定义 ====================

class ValidationType(Enum):
    """验证类型"""
    REQUIRED = "required"          # 必需
    TYPE = "type"                  # 类型
    LENGTH = "length"              # 长度
    RANGE = "range"                # 范围
    PATTERN = "pattern"            # 模式
    ENUM = "enum"                  # 枚举
    CUSTOM = "custom"              # 自定义

class FileType(Enum):
    """文件类型"""
    IMAGE = "image"                # 图片
    DOCUMENT = "document"          # 文档
    VIDEO = "video"                # 视频
    AUDIO = "audio"                # 音频
    ARCHIVE = "archive"            # 压缩包
    CODE = "code"                  # 代码文件
    OTHER = "other"                # 其他

class SecurityLevel(Enum):
    """安全级别"""
    LOW = "low"                    # 低安全级别
    MEDIUM = "medium"              # 中等安全级别
    HIGH = "high"                  # 高安全级别
    CRITICAL = "critical"          # 关键安全级别

# ==================== 数据类定义 ====================

@dataclass
class ValidationRule:
    """验证规则"""
    type: ValidationType
    value: Any = None
    message: str = ""
    params: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ValidationResult:
    """验证结果"""
    is_valid: bool
    cleaned_value: Any = None
    error_message: str = ""
    error_code: str = ""
    warnings: List[str] = field(default_factory=list)

@dataclass
class FileValidationRule:
    """文件验证规则"""
    allowed_types: List[str] = field(default_factory=list)
    max_size: int = 10 * 1024 * 1024  # 10MB
    min_size: int = 0
    allowed_extensions: List[str] = field(default_factory=list)
    check_content: bool = False
    virus_scan: bool = False
    security_level: SecurityLevel = SecurityLevel.MEDIUM

# ==================== 统一验证管理器 ====================

class UnifiedValidator:
    """统一的验证管理器"""
    
    def __init__(self, security_level: SecurityLevel = SecurityLevel.MEDIUM):
        self.security_level = security_level
        self._setup_dangerous_patterns()
        
        logger.info(f"统一验证器初始化完成，安全级别: {security_level.value}")
    
    def _setup_dangerous_patterns(self):
        """设置危险模式检测"""
        self.dangerous_patterns = {
            'sql_injection': [
                r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\b)",
                r"(\b(OR|AND)\s+\w+\s*=\s*\w+)",
                r"(-{2,}|/\*|\*/)",  # SQL注释
            ],
            'xss_patterns': [
                r"<script[^>]*>.*?</script>",
                r"javascript:",
                r"on\w+\s*=",
                r"<iframe[^>]*>",
                r"<object[^>]*>",
            ],
            'path_traversal': [
                r"\.\./",
                r"\.\.\\",
                r"/\.\./",
                r"\\\.\.\\"
            ]
        }
        
        # 编译正则表达式
        self.compiled_patterns = {}
        for category, patterns in self.dangerous_patterns.items():
            self.compiled_patterns[category] = [
                re.compile(pattern, re.IGNORECASE | re.MULTILINE | re.DOTALL)
                for pattern in patterns
            ]
    
    def validate_input(self, data: Dict[str, Any], rules: Dict[str, List[ValidationRule]] = None) -> ValidationResult:
        """验证输入数据"""
        if not data:
            return ValidationResult(False, None, "输入数据不能为空", "empty_data")
        
        errors = []
        cleaned_data = {}
        
        for field, value in data.items():
            field_rules = rules.get(field, []) if rules else []
            
            # 应用验证规则
            field_result = self._apply_field_rules(field, value, field_rules)
            
            if not field_result.is_valid:
                errors.append(f"{field}: {field_result.error_message}")
            else:
                cleaned_data[field] = field_result.cleaned_value
        
        if errors:
            return ValidationResult(False, None, "; ".join(errors), "validation_failed")
        
        return ValidationResult(True, cleaned_data, "", "")
    
    def validate_file(self, file_path: str, file_type: FileType = None, 
                      custom_rules: FileValidationRule = None) -> ValidationResult:
        """验证文件"""
        try:
            # 检查文件是否存在
            if not os.path.exists(file_path):
                return ValidationResult(False, None, "文件不存在", "file_not_found")
            
            # 获取文件信息
            file_size = os.path.getsize(file_path)
            file_extension = Path(file_path).suffix.lower()
            mime_type, _ = mimetypes.guess_type(file_path)
            
            # 应用自定义规则
            if custom_rules:
                if file_size > custom_rules.max_size:
                    return ValidationResult(False, None, "文件大小超过限制", "file_too_large")
                
                if custom_rules.allowed_extensions and file_extension not in custom_rules.allowed_extensions:
                    return ValidationResult(False, None, f"不支持的文件类型: {file_extension}", "unsupported_extension")
            
            return ValidationResult(True, {
                'file_path': file_path,
                'file_size': file_size,
                'file_extension': file_extension,
                'mime_type': mime_type
            }, "", "")
            
        except Exception as e:
            logger.error(f"文件验证失败: {e}")
            return ValidationResult(False, None, f"文件验证失败: {e}", "validation_error")
    
    def check_permission(self, user_role: str, user_id: Union[int, str], 
                        resource_type: str, action: str, 
                        resource_user_id: Union[int, str] = None) -> bool:
        """检查权限"""
        # 基础权限检查
        if user_role == 'superadmin':
            return True
        
        if user_role == 'admin':
            return action in ['read', 'write', 'edit', 'delete']
        
        if user_role == 'editor':
            return action in ['read', 'write', 'edit']
        
        if user_role == 'user':
            return action in ['read', 'write']
        
        if user_role == 'guest':
            return action == 'read'
        
        return False
    
    def _apply_field_rules(self, field: str, value: Any, rules: List[ValidationRule]) -> ValidationResult:
        """应用字段验证规则"""
        if not rules:
            # 默认验证
            return self._validate_string(value)
        
        for rule in rules:
            if rule.type == ValidationType.REQUIRED:
                if not value:
                    return ValidationResult(False, None, rule.message or f"{field}是必需的", "required")
            
            elif rule.type == ValidationType.TYPE:
                if not self._validate_type(value, rule.value):
                    return ValidationResult(False, None, rule.message or f"{field}类型不正确", "type_error")
            
            elif rule.type == ValidationType.LENGTH:
                if not self._validate_length(value, rule.params):
                    return ValidationResult(False, None, rule.message or f"{field}长度不符合要求", "length_error")
        
        return ValidationResult(True, value, "", "")
    
    def _validate_string(self, value: Any) -> ValidationResult:
        """验证字符串"""
        if value is None:
            return ValidationResult(False, None, "值不能为空", "empty_value")
        
        if not isinstance(value, str):
            try:
                value = str(value)
            except Exception:
                return ValidationResult(False, None, "无法转换为字符串", "type_error")
        
        value = value.strip()
        
        # 检查危险模式
        security_check = self._check_security_patterns(value)
        if not security_check['is_safe']:
            return ValidationResult(False, None, f"包含不安全内容: {security_check['threat']}", "security_threat")
        
        return ValidationResult(True, value, "", "")
    
    def _validate_type(self, value: Any, expected_type: str) -> bool:
        """验证类型"""
        if expected_type == 'int':
            try:
                int(value)
                return True
            except (ValueError, TypeError):
                return False
        elif expected_type == 'float':
            try:
                float(value)
                return True
            except (ValueError, TypeError):
                return False
        elif expected_type == 'bool':
            return str(value).lower() in ['true', 'false', '1', '0', 'yes', 'no']
        return True
    
    def _validate_length(self, value: Any, params: Dict[str, Any]) -> bool:
        """验证长度"""
        if not value:
            return True
        
        value_str = str(value)
        min_length = params.get('min', 0)
        max_length = params.get('max', float('inf'))
        
        return min_length <= len(value_str) <= max_length
    
    def _check_security_patterns(self, value: str) -> Dict[str, Any]:
        """检查安全模式"""
        for category, patterns in self.compiled_patterns.items():
            for pattern in patterns:
                if pattern.search(value):
                    return {
                        'is_safe': False,
                        'threat': category,
                        'pattern': pattern.pattern
                    }
        
        return {'is_safe': True}

# ==================== 全局实例和工厂函数 ====================

# 全局验证器实例
_global_validator = None

def init_unified_validator(security_level: SecurityLevel = SecurityLevel.MEDIUM) -> UnifiedValidator:
    """初始化全局验证器"""
    global _global_validator
    _global_validator = UnifiedValidator(security_level)
    return _global_validator

def get_validator() -> Optional[UnifiedValidator]:
    """获取全局验证器"""
    return _global_validator

def validate_input(data: Dict[str, Any], rules: Dict[str, List[ValidationRule]] = None) -> ValidationResult:
    """验证输入数据"""
    if _global_validator:
        return _global_validator.validate_input(data, rules)
    return ValidationResult(False, None, "验证器未初始化", "not_initialized")

def validate_file(file_path: str, file_type: FileType = None, 
                  custom_rules: FileValidationRule = None) -> ValidationResult:
    """验证文件"""
    if _global_validator:
        return _global_validator.validate_file(file_path, file_type, custom_rules)
    return ValidationResult(False, None, "验证器未初始化", "not_initialized")

def check_permission(user_role: str, user_id: Union[int, str], 
                    resource_type: str, action: str, 
                    resource_user_id: Union[int, str] = None) -> bool:
    """检查权限"""
    if _global_validator:
        return _global_validator.check_permission(user_role, user_id, resource_type, action, resource_user_id)
    return False

# ==================== 向后兼容 ====================

# 为了向后兼容，保留旧的函数名
init_input_validator = init_unified_validator
get_input_validator = get_validator
init_enhanced_input_validator = init_unified_validator
get_enhanced_input_validator = get_validator
init_file_upload_validator = init_unified_validator
get_file_upload_validator = get_validator
init_permission_validator = init_unified_validator
get_permission_validator = get_validator
