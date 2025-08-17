"""
增强输入验证模块
提供全面的输入验证、清理和安全检查
"""
import re
import html
import json
import ipaddress
import urllib.parse
from typing import Optional, Union, List, Dict, Any, Tuple
from dataclasses import dataclass
from woniunote.common.simple_logger import get_simple_logger

logger = get_simple_logger('enhanced_input_validator')

@dataclass
class ValidationResult:
    """验证结果"""
    is_valid: bool
    cleaned_value: Any = None
    error_message: str = ""
    error_code: str = ""

class EnhancedInputValidator:
    """增强输入验证器"""
    
    def __init__(self):
        # 危险模式匹配
        self.dangerous_patterns = {
            'sql_injection': [
                r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\b)",
                r"(\b(OR|AND)\s+\w+\s*=\s*\w+)",
                r"(\b\w+\s*(=|LIKE)\s*['\"].*['\"])",
                r"(-{2,}|/\*|\*/)",  # SQL注释
            ],
            'xss_patterns': [
                r"<script[^>]*>.*?</script>",
                r"javascript:",
                r"on\w+\s*=",
                r"<iframe[^>]*>",
                r"<object[^>]*>",
                r"<embed[^>]*>",
                r"<link[^>]*>",
                r"<meta[^>]*>",
            ],
            'path_traversal': [
                r"\.\./",
                r"\.\.\\",
                r"/\.\./",
                r"\\\.\.\\"
            ],
            'command_injection': [
                r"[;&|`$()]",
                r"\b(cat|ls|pwd|whoami|id|uname)\b",
                r">\s*/",
                r"<\s*/",
            ]
        }
        
        # 编译正则表达式以提高性能
        self.compiled_patterns = {}
        for category, patterns in self.dangerous_patterns.items():
            self.compiled_patterns[category] = [
                re.compile(pattern, re.IGNORECASE | re.MULTILINE | re.DOTALL)
                for pattern in patterns
            ]
    
    def validate_string(self, value: Any, min_length: int = 0, max_length: int = 1000,
                       allow_empty: bool = True, strip_whitespace: bool = True,
                       check_dangerous_patterns: bool = True) -> ValidationResult:
        """
        验证字符串输入
        
        Args:
            value: 输入值
            min_length: 最小长度
            max_length: 最大长度
            allow_empty: 是否允许空值
            strip_whitespace: 是否清理空白字符
            check_dangerous_patterns: 是否检查危险模式
            
        Returns:
            ValidationResult: 验证结果
        """
        # 类型检查和转换
        if value is None:
            if allow_empty:
                return ValidationResult(True, "", "", "")
            else:
                return ValidationResult(False, None, "值不能为空", "empty_value")
        
        if not isinstance(value, str):
            try:
                value = str(value)
            except Exception:
                return ValidationResult(False, None, "无法转换为字符串", "type_error")
        
        # 清理空白字符
        if strip_whitespace:
            value = value.strip()
        
        # 检查长度
        if not allow_empty and len(value) == 0:
            return ValidationResult(False, None, "值不能为空", "empty_value")
        
        if len(value) < min_length:
            return ValidationResult(False, None, f"长度不能少于{min_length}个字符", "too_short")
        
        if len(value) > max_length:
            return ValidationResult(False, None, f"长度不能超过{max_length}个字符", "too_long")
        
        # 检查危险模式
        if check_dangerous_patterns:
            danger_result = self._check_dangerous_patterns(value)
            if not danger_result.is_valid:
                return danger_result
        
        return ValidationResult(True, value, "", "")
    
    def validate_username(self, username: Any) -> ValidationResult:
        """验证用户名"""
        result = self.validate_string(username, min_length=3, max_length=50, allow_empty=False)
        if not result.is_valid:
            return result
        
        # 用户名格式检查
        username_pattern = re.compile(r'^[a-zA-Z0-9_.-]+$')
        if not username_pattern.match(result.cleaned_value):
            return ValidationResult(False, None, "用户名只能包含字母、数字、下划线、点和横线", "invalid_format")
        
        # 不能以数字开头
        if result.cleaned_value[0].isdigit():
            return ValidationResult(False, None, "用户名不能以数字开头", "invalid_format")
        
        return ValidationResult(True, result.cleaned_value, "", "")
    
    def validate_email(self, email: Any) -> ValidationResult:
        """验证邮箱地址"""
        result = self.validate_string(email, min_length=5, max_length=254, allow_empty=False)
        if not result.is_valid:
            return result
        
        # 邮箱格式检查
        email_pattern = re.compile(
            r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        )
        
        if not email_pattern.match(result.cleaned_value):
            return ValidationResult(False, None, "邮箱格式不正确", "invalid_email")
        
        # 检查常见的无效邮箱
        invalid_domains = ['test.com', 'example.com', 'localhost']
        domain = result.cleaned_value.split('@')[1].lower()
        if domain in invalid_domains:
            return ValidationResult(False, None, "请使用有效的邮箱域名", "invalid_domain")
        
        return ValidationResult(True, result.cleaned_value.lower(), "", "")
    
    def validate_password(self, password: Any) -> ValidationResult:
        """验证密码强度"""
        result = self.validate_string(password, min_length=8, max_length=128, 
                                    allow_empty=False, strip_whitespace=False,
                                    check_dangerous_patterns=False)
        if not result.is_valid:
            return result
        
        password = result.cleaned_value
        strength_score = 0
        requirements = []
        
        # 长度检查
        if len(password) >= 8:
            strength_score += 1
        else:
            requirements.append("至少8个字符")
        
        # 复杂度检查
        if re.search(r'[a-z]', password):
            strength_score += 1
        else:
            requirements.append("包含小写字母")
        
        if re.search(r'[A-Z]', password):
            strength_score += 1
        else:
            requirements.append("包含大写字母")
        
        if re.search(r'\d', password):
            strength_score += 1
        else:
            requirements.append("包含数字")
        
        if re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            strength_score += 1
        else:
            requirements.append("包含特殊字符")
        
        # 检查常见弱密码
        weak_passwords = [
            '12345678', 'password', 'qwerty', '123456789', 'abc123',
            'password123', 'admin', 'root', 'user'
        ]
        
        if password.lower() in weak_passwords:
            return ValidationResult(False, None, "密码过于简单，请使用更复杂的密码", "weak_password")
        
        # 检查重复字符
        if len(set(password)) < len(password) * 0.5:
            return ValidationResult(False, None, "密码重复字符过多", "repetitive_password")
        
        # 强度评估
        if strength_score < 3:
            error_msg = "密码强度不足，需要：" + "、".join(requirements)
            return ValidationResult(False, None, error_msg, "weak_password")
        
        return ValidationResult(True, password, "", "")
    
    def validate_integer(self, value: Any, min_value: int = None, 
                        max_value: int = None) -> ValidationResult:
        """验证整数"""
        if value is None:
            return ValidationResult(False, None, "值不能为空", "empty_value")
        
        try:
            if isinstance(value, str):
                # 移除空白字符
                value = value.strip()
                if not value:
                    return ValidationResult(False, None, "值不能为空", "empty_value")
                
                # 检查是否为有效整数字符串
                if not re.match(r'^-?\d+$', value):
                    return ValidationResult(False, None, "必须是整数", "invalid_integer")
                
                int_value = int(value)
            else:
                int_value = int(value)
        except (ValueError, TypeError):
            return ValidationResult(False, None, "无法转换为整数", "conversion_error")
        
        # 范围检查
        if min_value is not None and int_value < min_value:
            return ValidationResult(False, None, f"值不能小于{min_value}", "too_small")
        
        if max_value is not None and int_value > max_value:
            return ValidationResult(False, None, f"值不能大于{max_value}", "too_large")
        
        return ValidationResult(True, int_value, "", "")
    
    def validate_url(self, url: Any, allowed_schemes: List[str] = None) -> ValidationResult:
        """验证URL"""
        result = self.validate_string(url, max_length=2048, allow_empty=False)
        if not result.is_valid:
            return result
        
        url = result.cleaned_value
        allowed_schemes = allowed_schemes or ['http', 'https']
        
        try:
            parsed = urllib.parse.urlparse(url)
            
            # 检查协议
            if parsed.scheme not in allowed_schemes:
                return ValidationResult(False, None, f"URL协议必须是: {', '.join(allowed_schemes)}", "invalid_scheme")
            
            # 检查域名
            if not parsed.netloc:
                return ValidationResult(False, None, "URL缺少域名", "missing_domain")
            
            # 检查是否为IP地址
            try:
                ipaddress.ip_address(parsed.hostname)
                # 如果是IP地址，可以根据需要允许或拒绝
                logger.warning("URL使用IP地址而非域名", {'url': url})
            except ValueError:
                pass  # 不是IP地址，继续检查
            
            return ValidationResult(True, url, "", "")
            
        except Exception as e:
            return ValidationResult(False, None, f"URL格式错误: {str(e)}", "parse_error")
    
    def validate_json(self, json_string: Any, max_depth: int = 10) -> ValidationResult:
        """验证JSON字符串"""
        result = self.validate_string(json_string, allow_empty=False)
        if not result.is_valid:
            return result
        
        try:
            parsed_json = json.loads(result.cleaned_value)
            
            # 检查嵌套深度
            depth = self._get_json_depth(parsed_json)
            if depth > max_depth:
                return ValidationResult(False, None, f"JSON嵌套层次过深（最大{max_depth}层）", "too_deep")
            
            return ValidationResult(True, parsed_json, "", "")
            
        except json.JSONDecodeError as e:
            return ValidationResult(False, None, f"JSON格式错误: {str(e)}", "json_error")
    
    def validate_file_path(self, file_path: Any, allowed_extensions: List[str] = None,
                          max_length: int = 255) -> ValidationResult:
        """验证文件路径"""
        result = self.validate_string(file_path, max_length=max_length, allow_empty=False)
        if not result.is_valid:
            return result
        
        path = result.cleaned_value
        
        # 检查路径遍历攻击
        if '..' in path or path.startswith('/') or '\\' in path:
            return ValidationResult(False, None, "文件路径包含非法字符", "invalid_path")
        
        # 检查文件扩展名
        if allowed_extensions:
            extension = path.split('.')[-1].lower() if '.' in path else ""
            if extension not in allowed_extensions:
                return ValidationResult(False, None, 
                                      f"文件类型不允许，允许的类型: {', '.join(allowed_extensions)}", 
                                      "invalid_extension")
        
        return ValidationResult(True, path, "", "")
    
    def _check_dangerous_patterns(self, text: str) -> ValidationResult:
        """检查危险模式"""
        for category, patterns in self.compiled_patterns.items():
            for pattern in patterns:
                if pattern.search(text):
                    logger.warning(f"检测到危险模式: {category}", {
                        'pattern': pattern.pattern,
                        'text_sample': text[:100]
                    })
                    return ValidationResult(False, None, f"输入包含潜在危险内容", f"dangerous_{category}")
        
        return ValidationResult(True, text, "", "")
    
    def _get_json_depth(self, obj, depth=0):
        """计算JSON对象的嵌套深度"""
        if isinstance(obj, dict):
            if not obj:
                return depth
            return max(self._get_json_depth(value, depth + 1) for value in obj.values())
        elif isinstance(obj, list):
            if not obj:
                return depth
            return max(self._get_json_depth(item, depth + 1) for item in obj)
        else:
            return depth
    
    def sanitize_html(self, html_content: str, allowed_tags: List[str] = None,
                     allowed_attributes: Dict[str, List[str]] = None) -> str:
        """清理HTML内容"""
        if not html_content:
            return ""
        
        # 基本HTML转义
        sanitized = html.escape(html_content)
        
        # 如果指定了允许的标签，使用bleach库进行更精细的清理
        if allowed_tags is not None:
            try:
                import bleach
                sanitized = bleach.clean(
                    html_content,
                    tags=allowed_tags,
                    attributes=allowed_attributes or {},
                    strip=True
                )
            except ImportError:
                logger.warning("bleach库不可用，使用基本HTML转义")
                sanitized = html.escape(html_content)
        
        return sanitized

# 全局验证器实例
enhanced_validator = EnhancedInputValidator()

# 便捷函数
def validate_string_input(value: Any, **kwargs) -> ValidationResult:
    """便捷函数：验证字符串输入"""
    return enhanced_validator.validate_string(value, **kwargs)

def validate_user_input(username: Any, email: Any, password: Any) -> Dict[str, ValidationResult]:
    """便捷函数：验证用户输入"""
    return {
        'username': enhanced_validator.validate_username(username),
        'email': enhanced_validator.validate_email(email),
        'password': enhanced_validator.validate_password(password)
    }

def check_input_security(text: str) -> bool:
    """便捷函数：检查输入安全性"""
    result = enhanced_validator._check_dangerous_patterns(text)
    return result.is_valid