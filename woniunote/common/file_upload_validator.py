"""
文件上传安全验证模块
提供文件类型、大小、内容等安全检查
"""
import os
import mimetypes
from typing import Optional, List, Tuple, Dict, Any

# Make magic import optional
try:
    import magic
    HAS_MAGIC = True
except ImportError:
    HAS_MAGIC = False
    magic = None
from werkzeug.datastructures import FileStorage
from woniunote.common.simple_logger import get_simple_logger

logger = get_simple_logger('file_upload_validator')

class FileUploadError(Exception):
    """文件上传错误异常"""
    pass

class FileUploadValidator:
    """文件上传安全验证器"""
    
    def __init__(self):
        # 允许的图片文件扩展名
        self.allowed_image_extensions = {
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'
        }
        
        # 允许的文档文件扩展名
        self.allowed_document_extensions = {
            '.pdf', '.doc', '.docx', '.txt', '.rtf'
        }
        
        # 允许的MIME类型
        self.allowed_image_mimes = {
            'image/jpeg', 'image/png', 'image/gif', 
            'image/bmp', 'image/webp'
        }
        
        self.allowed_document_mimes = {
            'application/pdf', 'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'text/plain', 'application/rtf'
        }
        
        # 文件大小限制（字节）
        self.max_image_size = 5 * 1024 * 1024  # 5MB
        self.max_document_size = 10 * 1024 * 1024  # 10MB
        
        # 危险文件扩展名黑名单
        self.dangerous_extensions = {
            '.exe', '.bat', '.cmd', '.com', '.pif', '.scr', '.vbs', '.js',
            '.jar', '.jsp', '.php', '.asp', '.aspx', '.py', '.pl', '.sh',
            '.bin', '.msi', '.dmg', '.pkg', '.deb', '.rpm'
        }
        
        # 危险MIME类型黑名单
        self.dangerous_mimes = {
            'application/x-executable', 'application/x-msdownload',
            'application/x-msdos-program', 'application/java-archive',
            'text/x-php', 'application/x-php', 'text/html'
        }
    
    def validate_image_file(self, file: FileStorage, 
                           allowed_extensions: Optional[List[str]] = None,
                           max_size: Optional[int] = None) -> Tuple[bool, str, Dict[str, Any]]:
        """
        验证图片文件
        
        Args:
            file: 上传的文件对象
            allowed_extensions: 允许的扩展名列表
            max_size: 最大文件大小
            
        Returns:
            Tuple[bool, str, Dict]: (是否有效, 错误信息, 文件信息)
        """
        if allowed_extensions is None:
            allowed_extensions = self.allowed_image_extensions
        else:
            allowed_extensions = {ext.lower() for ext in allowed_extensions}
        
        if max_size is None:
            max_size = self.max_image_size
        
        return self._validate_file(
            file, allowed_extensions, self.allowed_image_mimes, 
            max_size, "image"
        )
    
    def validate_document_file(self, file: FileStorage,
                              allowed_extensions: Optional[List[str]] = None,
                              max_size: Optional[int] = None) -> Tuple[bool, str, Dict[str, Any]]:
        """
        验证文档文件
        
        Args:
            file: 上传的文件对象
            allowed_extensions: 允许的扩展名列表
            max_size: 最大文件大小
            
        Returns:
            Tuple[bool, str, Dict]: (是否有效, 错误信息, 文件信息)
        """
        if allowed_extensions is None:
            allowed_extensions = self.allowed_document_extensions
        else:
            allowed_extensions = {ext.lower() for ext in allowed_extensions}
        
        if max_size is None:
            max_size = self.max_document_size
        
        return self._validate_file(
            file, allowed_extensions, self.allowed_document_mimes,
            max_size, "document"
        )
    
    def _validate_file(self, file: FileStorage, allowed_extensions: set,
                      allowed_mimes: set, max_size: int, 
                      file_type: str) -> Tuple[bool, str, Dict[str, Any]]:
        """
        内部文件验证方法
        """
        file_info = {
            'filename': '',
            'size': 0,
            'extension': '',
            'mime_type': '',
            'detected_mime': ''
        }
        
        try:
            # 检查文件是否存在
            if not file or not file.filename:
                return False, "未提供有效文件", file_info
            
            filename = file.filename.strip()
            file_info['filename'] = filename
            
            # 检查文件名长度
            if len(filename) > 255:
                return False, "文件名过长", file_info
            
            # 检查文件名中的危险字符
            dangerous_chars = ['..', '/', '\\', ':', '*', '?', '"', '<', '>', '|']
            if any(char in filename for char in dangerous_chars):
                return False, "文件名包含非法字符", file_info
            
            # 获取文件扩展名
            _, ext = os.path.splitext(filename.lower())
            file_info['extension'] = ext
            
            # 检查扩展名是否在危险列表中
            if ext in self.dangerous_extensions:
                logger.warning("检测到危险文件类型", {
                    'filename': filename,
                    'extension': ext,
                    'file_type': file_type
                })
                return False, f"不允许上传{ext}类型的文件", file_info
            
            # 检查扩展名是否在允许列表中
            if ext not in allowed_extensions:
                return False, f"不支持的文件类型{ext}", file_info
            
            # 检查文件大小
            file.seek(0, 2)  # 移动到文件末尾
            file_size = file.tell()
            file.seek(0)  # 重置文件指针
            file_info['size'] = file_size
            
            if file_size > max_size:
                return False, f"文件大小超过限制({max_size // (1024*1024)}MB)", file_info
            
            if file_size == 0:
                return False, "文件为空", file_info
            
            # 检查MIME类型
            declared_mime = file.content_type
            file_info['mime_type'] = declared_mime
            
            # 检查声明的MIME类型是否在危险列表中
            if declared_mime in self.dangerous_mimes:
                logger.warning("检测到危险MIME类型", {
                    'filename': filename,
                    'mime_type': declared_mime,
                    'file_type': file_type
                })
                return False, "检测到危险的文件类型", file_info
            
            # 检查声明的MIME类型是否在允许列表中
            if declared_mime not in allowed_mimes:
                logger.warning("MIME类型不在允许列表中", {
                    'filename': filename,
                    'declared_mime': declared_mime,
                    'allowed_mimes': list(allowed_mimes)
                })
            
            # 使用magic库检测实际的MIME类型
            try:
                file_content = file.read(1024)  # 读取前1KB
                file.seek(0)  # 重置文件指针
                
                if HAS_MAGIC:
                    detected_mime = magic.from_buffer(file_content, mime=True)
                else:
                    detected_mime = mimetypes.guess_type(file.filename)[0] or 'application/octet-stream'
                    logger.warning("缺少python-magic库，使用基本文件类型检测")
                file_info['detected_mime'] = detected_mime
                
                # 检查检测到的MIME类型是否匹配
                if detected_mime not in allowed_mimes:
                    logger.warning("文件实际类型与扩展名不匹配", {
                        'filename': filename,
                        'declared_mime': declared_mime,
                        'detected_mime': detected_mime,
                        'extension': ext
                    })
                    return False, "文件类型验证失败", file_info
                
            except Exception as e:
                logger.warning("无法检测文件MIME类型", {
                    'filename': filename,
                    'error': str(e)
                })
                # 如果无法检测MIME类型，继续验证但记录警告
            
            # 针对图片文件的额外检查
            if file_type == "image":
                if not self._validate_image_content(file):
                    return False, "图片内容验证失败", file_info
            
            logger.info("文件验证成功", {
                'filename': filename,
                'size': file_size,
                'extension': ext,
                'mime_type': declared_mime,
                'file_type': file_type
            })
            
            return True, "", file_info
            
        except Exception as e:
            logger.error("文件验证异常", {
                'filename': file_info.get('filename', ''),
                'error': str(e),
                'file_type': file_type
            })
            return False, f"文件验证失败: {str(e)}", file_info
    
    def _validate_image_content(self, file: FileStorage) -> bool:
        """
        验证图片内容
        """
        try:
            from PIL import Image
            file.seek(0)
            
            # 尝试打开图片
            image = Image.open(file)
            
            # 检查图片尺寸
            width, height = image.size
            if width > 10000 or height > 10000:
                logger.warning("图片尺寸过大", {
                    'width': width,
                    'height': height
                })
                return False
            
            # 验证图片格式
            if image.format not in ['JPEG', 'PNG', 'GIF', 'BMP', 'WEBP']:
                logger.warning("不支持的图片格式", {
                    'format': image.format
                })
                return False
            
            file.seek(0)  # 重置文件指针
            return True
            
        except Exception as e:
            logger.warning("图片内容验证失败", {
                'error': str(e)
            })
            return False
    
    def generate_safe_filename(self, original_filename: str, user_id: str = None) -> str:
        """
        生成安全的文件名
        
        Args:
            original_filename: 原始文件名
            user_id: 用户ID（可选）
            
        Returns:
            str: 安全的文件名
        """
        import uuid
        from datetime import datetime
        
        # 获取文件扩展名
        _, ext = os.path.splitext(original_filename.lower())
        
        # 生成时间戳
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 生成UUID
        file_uuid = str(uuid.uuid4())[:8]
        
        # 构造安全文件名
        if user_id:
            safe_filename = f"{user_id}_{timestamp}_{file_uuid}{ext}"
        else:
            safe_filename = f"{timestamp}_{file_uuid}{ext}"
        
        return safe_filename

# 全局验证器实例
file_validator = FileUploadValidator()

# 便捷函数
def validate_image_upload(file: FileStorage) -> Tuple[bool, str, Dict[str, Any]]:
    """便捷函数：验证图片上传"""
    return file_validator.validate_image_file(file)

def validate_document_upload(file: FileStorage) -> Tuple[bool, str, Dict[str, Any]]:
    """便捷函数：验证文档上传"""
    return file_validator.validate_document_file(file)

def generate_safe_filename(original_filename: str, user_id: str = None) -> str:
    """便捷函数：生成安全文件名"""
    return file_validator.generate_safe_filename(original_filename, user_id)