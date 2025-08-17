"""
输入验证和清理模块
防止 XSS、SQL 注入和其他输入攻击
"""
import re
import html
import bleach
import logging
from urllib.parse import urlparse
from typing import Optional, Union, List, Dict, Any

logger = logging.getLogger(__name__)

# 允许的HTML标签和属性（用于富文本编辑器）
ALLOWED_TAGS = {
    'p', 'br', 'strong', 'em', 'u', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'ul', 'ol', 'li', 'blockquote', 'code', 'pre', 'a', 'img', 'table',
    'thead', 'tbody', 'tr', 'th', 'td', 'div', 'span'
}

ALLOWED_ATTRIBUTES = {
    'a': ['href', 'title'],
    'img': ['src', 'alt', 'title', 'width', 'height'],
    'div': ['class'],
    'span': ['class'],
    'table': ['class'],
    'th': ['colspan', 'rowspan'],
    'td': ['colspan', 'rowspan']
}

# 危险的模式
DANGEROUS_PATTERNS = [
    r'<script[^>]*>.*?</script>',  # script标签
    r'javascript:',  # javascript协议
    r'data:',  # data协议
    r'vbscript:',  # vbscript协议
    r'on\w+\s*=',  # 事件处理器
    r'<iframe[^>]*>.*?</iframe>',  # iframe标签
    r'<object[^>]*>.*?</object>',  # object标签
    r'<embed[^>]*>.*?</embed>',  # embed标签
    r'<form[^>]*>.*?</form>',  # form标签
    r'<input[^>]*>',  # input标签
    r'<textarea[^>]*>.*?</textarea>',  # textarea标签
]

class InputValidator:
    """输入验证和清理类"""
    
    def __init__(self):
        self.dangerous_pattern = re.compile('|'.join(DANGEROUS_PATTERNS), re.IGNORECASE | re.DOTALL)
    
    def validate_string(self, value: Any, max_length: int = 255, allow_empty: bool = True, 
                       field_name: str = "字段") -> Optional[str]:
        """
        验证和清理字符串输入
        
        Args:
            value: 输入值
            max_length: 最大长度
            allow_empty: 是否允许空值
            field_name: 字段名称（用于错误信息）
            
        Returns:
            清理后的字符串或None
        """
        if value is None:
            if allow_empty:
                return None
            else:
                raise ValueError(f"{field_name}不能为空")
        
        # 转换为字符串并去除首尾空格
        if not isinstance(value, str):
            value = str(value)
        
        value = value.strip()
        
        # 检查空值
        if not value and not allow_empty:
            raise ValueError(f"{field_name}不能为空")
        
        # 检查长度
        if len(value) > max_length:
            raise ValueError(f"{field_name}长度不能超过{max_length}个字符")
        
        # 基本XSS防护
        value = html.escape(value)
        
        # 检查危险模式
        if self.dangerous_pattern.search(value):
            logger.warning(f"检测到危险输入模式: {field_name}={value[:100]}...")
            raise ValueError(f"{field_name}包含不安全的内容")
        
        return value
    
    def validate_username(self, username: Any) -> str:
        """
        验证用户名
        
        Args:
            username: 用户名
            
        Returns:
            验证后的用户名
        """
        username = self.validate_string(username, max_length=50, allow_empty=False, field_name="用户名")
        
        # 用户名格式检查：只允许字母、数字、下划线、中文
        pattern = r'^[\w\u4e00-\u9fa5]+$'
        if not re.match(pattern, username):
            raise ValueError("用户名只能包含字母、数字、下划线和中文字符")
        
        # 长度检查
        if len(username) < 2:
            raise ValueError("用户名长度不能少于2个字符")
        
        return username
    
    def validate_password(self, password: Any) -> str:
        """
        验证密码强度
        
        Args:
            password: 密码
            
        Returns:
            验证后的密码
        """
        if not password:
            raise ValueError("密码不能为空")
        
        password = str(password)
        
        # 密码长度检查
        if len(password) < 6:
            raise ValueError("密码长度不能少于6个字符")
        if len(password) > 128:
            raise ValueError("密码长度不能超过128个字符")
        
        # 密码复杂度检查（可选，根据需求调整）
        has_letter = bool(re.search(r'[a-zA-Z]', password))
        has_digit = bool(re.search(r'\d', password))
        
        if not (has_letter or has_digit):
            raise ValueError("密码必须包含字母或数字")
        
        return password
    
    def validate_email(self, email: Any) -> Optional[str]:
        """
        验证邮箱地址
        
        Args:
            email: 邮箱地址
            
        Returns:
            验证后的邮箱地址
        """
        if not email:
            return None
        
        email = self.validate_string(email, max_length=100, field_name="邮箱")
        
        # 邮箱格式验证
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, email):
            raise ValueError("邮箱地址格式不正确")
        
        return email.lower()
    
    def validate_url(self, url: Any) -> Optional[str]:
        """
        验证URL地址
        
        Args:
            url: URL地址
            
        Returns:
            验证后的URL
        """
        if not url:
            return None
        
        url = self.validate_string(url, max_length=500, field_name="URL")
        
        try:
            parsed = urlparse(url)
            # 只允许http和https协议
            if parsed.scheme not in ['http', 'https']:
                raise ValueError("URL只支持http和https协议")
            
            if not parsed.netloc:
                raise ValueError("URL格式不正确")
            
        except Exception:
            raise ValueError("URL格式不正确")
        
        return url
    
    def validate_integer(self, value: Any, min_value: int = None, max_value: int = None,
                        field_name: str = "数字字段") -> Optional[int]:
        """
        验证整数
        
        Args:
            value: 输入值
            min_value: 最小值
            max_value: 最大值
            field_name: 字段名称
            
        Returns:
            验证后的整数
        """
        if value is None or value == '':
            return None
        
        try:
            value = int(value)
        except (ValueError, TypeError):
            raise ValueError(f"{field_name}必须是整数")
        
        if min_value is not None and value < min_value:
            raise ValueError(f"{field_name}不能小于{min_value}")
        
        if max_value is not None and value > max_value:
            raise ValueError(f"{field_name}不能大于{max_value}")
        
        return value
    
    def sanitize_html(self, content: str, allow_rich_text: bool = False) -> str:
        """
        清理HTML内容
        
        Args:
            content: HTML内容
            allow_rich_text: 是否允许富文本标签
            
        Returns:
            清理后的HTML
        """
        if not content:
            return ""
        
        if allow_rich_text:
            # 允许部分HTML标签（用于富文本编辑器）
            return bleach.clean(content, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES)
        else:
            # 完全清除HTML标签
            return bleach.clean(content, tags=[], attributes={}, strip=True)
    
    def validate_file_name(self, filename: Any) -> str:
        """
        验证文件名
        
        Args:
            filename: 文件名
            
        Returns:
            验证后的文件名
        """
        filename = self.validate_string(filename, max_length=255, allow_empty=False, field_name="文件名")
        
        # 检查危险字符
        dangerous_chars = ['..', '/', '\\', ':', '*', '?', '"', '<', '>', '|']
        for char in dangerous_chars:
            if char in filename:
                raise ValueError(f"文件名不能包含字符: {char}")
        
        # 检查文件扩展名
        allowed_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.pdf', '.doc', '.docx', '.txt'}
        ext = filename.lower().split('.')[-1] if '.' in filename else ''
        if ext and f'.{ext}' not in allowed_extensions:
            raise ValueError(f"不支持的文件类型: {ext}")
        
        return filename
    
    def validate_article_title(self, title: Any) -> str:
        """
        验证文章标题
        
        Args:
            title: 文章标题
            
        Returns:
            验证后的标题
        """
        title = self.validate_string(title, max_length=200, allow_empty=False, field_name="文章标题")
        
        # 清理HTML后检查长度
        clean_title = self.sanitize_html(title, allow_rich_text=False)
        if len(clean_title) < 5:
            raise ValueError("文章标题不能少于5个字符")
        
        return title
    
    def validate_article_content(self, content: Any) -> str:
        """
        验证文章内容
        
        Args:
            content: 文章内容
            
        Returns:
            验证后的内容
        """
        if not content:
            raise ValueError("文章内容不能为空")
        
        content = str(content)
        
        # 检查原始长度
        if len(content) > 50000:
            raise ValueError("文章内容长度不能超过50000个字符")
        
        # 清理HTML后检查长度
        clean_content = self.sanitize_html(content, allow_rich_text=False)
        if len(clean_content) < 10:
            raise ValueError("文章内容不能少于10个字符")
        
        return content
    
    def validate_comment_content(self, content: Any) -> str:
        """
        验证评论内容
        
        Args:
            content: 评论内容
            
        Returns:
            验证后的内容
        """
        content = self.validate_string(content, max_length=1000, allow_empty=False, field_name="评论内容")
        
        # 清理HTML后检查长度
        clean_content = self.sanitize_html(content, allow_rich_text=False)
        if len(clean_content) < 5:
            raise ValueError("评论内容不能少于5个字符")
        
        return content
    
    def validate_form_data(self, form_data: Dict[str, Any], 
                          validation_rules: Dict[str, Dict]) -> Dict[str, Any]:
        """
        批量验证表单数据
        
        Args:
            form_data: 表单数据
            validation_rules: 验证规则
            
        Returns:
            验证后的数据
        """
        validated_data = {}
        errors = {}
        
        for field_name, rules in validation_rules.items():
            try:
                value = form_data.get(field_name)
                field_type = rules.get('type', 'string')
                
                if field_type == 'string':
                    validated_data[field_name] = self.validate_string(
                        value,
                        max_length=rules.get('max_length', 255),
                        allow_empty=rules.get('allow_empty', True),
                        field_name=rules.get('display_name', field_name)
                    )
                elif field_type == 'username':
                    validated_data[field_name] = self.validate_username(value)
                elif field_type == 'password':
                    validated_data[field_name] = self.validate_password(value)
                elif field_type == 'email':
                    validated_data[field_name] = self.validate_email(value)
                elif field_type == 'url':
                    validated_data[field_name] = self.validate_url(value)
                elif field_type == 'integer':
                    validated_data[field_name] = self.validate_integer(
                        value,
                        min_value=rules.get('min_value'),
                        max_value=rules.get('max_value'),
                        field_name=rules.get('display_name', field_name)
                    )
                elif field_type == 'html':
                    validated_data[field_name] = self.sanitize_html(
                        value,
                        allow_rich_text=rules.get('allow_rich_text', False)
                    )
                elif field_type == 'article_title':
                    validated_data[field_name] = self.validate_article_title(value)
                elif field_type == 'article_content':
                    validated_data[field_name] = self.validate_article_content(value)
                elif field_type == 'comment_content':
                    validated_data[field_name] = self.validate_comment_content(value)
                elif field_type == 'filename':
                    validated_data[field_name] = self.validate_file_name(value)
                
            except ValueError as e:
                errors[field_name] = str(e)
        
        if errors:
            raise ValueError(f"表单验证失败: {errors}")
        
        return validated_data

# 全局验证器实例
validator = InputValidator()

# 便捷函数
def validate_string(value, max_length=255, allow_empty=True, field_name="字段"):
    return validator.validate_string(value, max_length, allow_empty, field_name)

def validate_username(username):
    return validator.validate_username(username)

def validate_password(password):
    return validator.validate_password(password)

def validate_email(email):
    return validator.validate_email(email)

def validate_url(url):
    return validator.validate_url(url)

def validate_integer(value, min_value=None, max_value=None, field_name="数字字段"):
    return validator.validate_integer(value, min_value, max_value, field_name)

def sanitize_html(content, allow_rich_text=False):
    return validator.sanitize_html(content, allow_rich_text)

def validate_file_name(filename):
    return validator.validate_file_name(filename)

def validate_article_title(title):
    return validator.validate_article_title(title)

def validate_article_content(content):
    return validator.validate_article_content(content)

def validate_comment_content(content):
    return validator.validate_comment_content(content)