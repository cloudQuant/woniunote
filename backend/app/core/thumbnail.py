"""
缩略图生成工具模块

本模块提供了生成随机渐变背景带文字的缩略图，以及图片压缩功能。
参考 woniunote/common/utils.py 中的 create_thumb_png 函数实现。
"""
import os
import random
import logging
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

# 常量配置
ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB


def get_system_font_path():
    """
    获取系统默认字体路径
    
    支持 Windows 和 Linux/Mac 平台，优先使用支持中文的字体。
    
    Returns:
        Optional[str]: 字体文件路径，如果未找到则返回 None
    """
    try:
        if os.name == 'nt':  # Windows
            common_fonts = [
                "C:\\Windows\\Fonts\\msyh.ttc",       # 微软雅黑
                "C:\\Windows\\Fonts\\simhei.ttf",     # 黑体
                "C:\\Windows\\Fonts\\simsun.ttc",     # 宋体
                "C:\\Windows\\Fonts\\arial.ttf",
                "C:\\Windows\\Fonts\\Arial.ttf",
                "C:\\Windows\\Fonts\\calibri.ttf"
            ]
        elif os.name == 'posix':  # Linux/Mac
            common_fonts = [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
                "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",  # 文泉驿微米黑
                "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",  # Noto CJK
                "/System/Library/Fonts/Helvetica.ttc",
                "/Library/Fonts/Arial.ttf",
                "/usr/share/fonts/TTF/arial.ttf",
            ]
        else:
            logger.warning("Unknown operating system")
            return None
        
        # 查找可用字体
        for font_path in common_fonts:
            if os.path.exists(font_path):
                logger.info(f"Using system font: {font_path}")
                return font_path
        
        logger.warning("No system font found")
        return None
        
    except Exception as e:
        logger.error(f"Error getting system font path: {str(e)}")
        return None


def generate_random_color():
    """
    生成随机 RGB 颜色
    
    Returns:
        Tuple[int, int, int]: RGB 颜色元组
    """
    return (
        random.randint(50, 200),
        random.randint(50, 200),
        random.randint(50, 200)
    )


def generate_gradient_background(width: int, height: int) -> Image.Image:
    """
    生成渐变背景图片
    
    Args:
        width: 图片宽度
        height: 图片高度
        
    Returns:
        Image.Image: PIL Image 对象
        
    Raises:
        ValueError: 当宽高无效时抛出
    """
    try:
        if not isinstance(width, int) or not isinstance(height, int):
            raise ValueError("Width and height must be integers")
        
        if width <= 0 or height <= 0 or width > 2000 or height > 2000:
            raise ValueError("Invalid dimensions")
        
        # 创建渐变图片
        image = Image.new('RGB', (width, height))
        
        # 生成渐变色
        start_color = generate_random_color()
        end_color = generate_random_color()
        
        for y in range(height):
            ratio = y / height
            r = int(start_color[0] * (1 - ratio) + end_color[0] * ratio)
            g = int(start_color[1] * (1 - ratio) + end_color[1] * ratio)
            b = int(start_color[2] * (1 - ratio) + end_color[2] * ratio)
            
            for x in range(width):
                image.putpixel((x, y), (r, g, b))
        
        return image
        
    except Exception as e:
        logger.error(f"Error generating gradient background: {str(e)}")
        raise


def create_thumb_png(width: int = 200, height: int = 150, text: str = "WoniuNote") -> Image.Image:
    """
    创建带文字的缩略图
    
    生成一个带有随机渐变背景和居中文字的图片。
    
    Args:
        width: 图片宽度
        height: 图片高度
        text: 显示的文字
        
    Returns:
        Image.Image: PIL Image 对象
        
    Raises:
        ValueError: 当参数无效时抛出
    """
    try:
        # 参数验证
        if not isinstance(width, int) or not isinstance(height, int):
            raise ValueError("Width and height must be integers")
        
        if width <= 0 or height <= 0 or width > 1000 or height > 1000:
            raise ValueError("Invalid dimensions")
        
        # 清理文字
        if text:
            text = str(text)[:50]
        else:
            text = "WoniuNote"
        
        # 生成渐变背景
        image = generate_gradient_background(width, height)
        draw = ImageDraw.Draw(image)
        
        # 获取字体
        font_path = get_system_font_path()
        try:
            if font_path:
                # 根据文字长度调整字体大小
                font_size = min(24, int(width / len(text) * 1.2))
                font_size = max(12, font_size)  # 最小12px
                font = ImageFont.truetype(font_path, font_size)
            else:
                font = ImageFont.load_default()
        except Exception:
            font = ImageFont.load_default()
        
        # 计算文字位置（居中）
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        x = (width - text_width) // 2
        y = (height - text_height) // 2
        
        # 绘制文字（带阴影效果）
        shadow_color = (0, 0, 0, 128)
        text_color = (255, 255, 255)
        
        # 绘制阴影
        draw.text((x + 2, y + 2), text, font=font, fill=shadow_color)
        # 绘制文字
        draw.text((x, y), text, font=font, fill=text_color)
        
        logger.info(f"Thumbnail created: {width}x{height}, text: {text}")
        return image
        
    except Exception as e:
        logger.error(f"Error creating thumbnail: {str(e)}")
        raise


def compress_image(source: str, dest: str, width: int, quality: int = 85) -> bool:
    """
    压缩图片
    
    调整图片大小并压缩质量。
    
    Args:
        source: 源文件路径
        dest: 目标文件路径
        width: 目标宽度（高度按比例缩放）
        quality: 压缩质量 (1-100)
        
    Returns:
        bool: 是否成功
        
    Raises:
        ValueError: 当参数无效或文件过大时抛出
        FileNotFoundError: 当源文件不存在时抛出
    """
    try:
        # 验证参数
        if not source or not dest:
            raise ValueError("Source and destination paths required")
        
        if not isinstance(width, int) or width <= 0 or width > 5000:
            raise ValueError("Invalid width parameter")
        
        if not isinstance(quality, int) or quality < 1 or quality > 100:
            quality = 85
        
        # 检查源文件是否存在
        if not os.path.exists(source):
            raise FileNotFoundError(f"Source file not found: {source}")
        
        # 检查文件大小
        file_size = os.path.getsize(source)
        if file_size > MAX_IMAGE_SIZE:
            raise ValueError(f"Image file too large: {file_size} bytes")
        
        # 验证文件扩展名
        source_ext = os.path.splitext(source)[1].lower()
        if source_ext not in ALLOWED_IMAGE_EXTENSIONS:
            raise ValueError(f"Unsupported image format: {source_ext}")
        
        # 打开并处理图片
        with Image.open(source) as image:
            # 验证图片尺寸
            orig_width, orig_height = image.size
            if orig_width > 10000 or orig_height > 10000:
                raise ValueError("Image dimensions too large")
            
            # 计算新的高度，保持宽高比
            if orig_width <= width:
                new_width, new_height = orig_width, orig_height
            else:
                ratio = width / orig_width
                new_width = width
                new_height = int(orig_height * ratio)
            
            # 调整图片大小
            if new_width != orig_width or new_height != orig_height:
                image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # 转换为RGB模式（如果需要）
            if image.mode in ('RGBA', 'P'):
                rgb_image = Image.new('RGB', image.size, (255, 255, 255))
                rgb_image.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
                image = rgb_image
            
            # 保存压缩后的图片
            image.save(dest, 'JPEG', quality=quality, optimize=True)
        
        logger.info(f"Image compressed successfully: {source} -> {dest}")
        return True
        
    except Exception as e:
        logger.error(f"Image compression failed: {str(e)}")
        raise


if __name__ == '__main__':
    # 测试缩略图生成
    img = create_thumb_png(226, 136, "测试缩略图")
    img.save("test_thumb.png", "PNG")
    print("Thumbnail saved to test_thumb.png")
