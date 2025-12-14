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


# 预定义的渐变色方案（参考原网站风格）
GRADIENT_COLORS = [
    ((88, 86, 214), (155, 89, 182)),    # 紫色渐变
    ((52, 152, 219), (41, 128, 185)),   # 蓝色渐变
    ((46, 204, 113), (39, 174, 96)),    # 绿色渐变
    ((231, 76, 60), (192, 57, 43)),     # 红色渐变
    ((241, 196, 15), (243, 156, 18)),   # 黄色渐变
    ((26, 188, 156), (22, 160, 133)),   # 青色渐变
    ((155, 89, 182), (142, 68, 173)),   # 深紫渐变
    ((52, 73, 94), (44, 62, 80)),       # 深蓝灰渐变
    ((230, 126, 34), (211, 84, 0)),     # 橙色渐变
    ((149, 165, 166), (127, 140, 141)), # 灰色渐变
]


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
            ]
        elif os.name == 'posix':  # Linux/Mac
            common_fonts = [
                # macOS 中文字体（优先）
                "/System/Library/Fonts/PingFang.ttc",           # 苹方
                "/System/Library/Fonts/STHeiti Light.ttc",      # 华文黑体
                "/System/Library/Fonts/STHeiti Medium.ttc",     # 华文黑体
                "/Library/Fonts/Arial Unicode.ttf",              # Arial Unicode
                "/System/Library/Fonts/Hiragino Sans GB.ttc",   # 冬青黑体
                # Linux 中文字体
                "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",  # 文泉驿微米黑
                "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",  # Noto CJK
                "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
                # 备选
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "/System/Library/Fonts/Helvetica.ttc",
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


def get_gradient_colors(seed: int = None):
    """
    根据种子值获取固定的渐变颜色
    
    Args:
        seed: 种子值，用于确定使用哪个颜色方案
        
    Returns:
        Tuple[Tuple, Tuple]: (起始颜色, 结束颜色)
    """
    if seed is not None:
        index = seed % len(GRADIENT_COLORS)
    else:
        index = random.randint(0, len(GRADIENT_COLORS) - 1)
    return GRADIENT_COLORS[index]


def generate_gradient_background(width: int, height: int, seed: int = None) -> Image.Image:
    """
    生成渐变背景图片
    
    Args:
        width: 图片宽度
        height: 图片高度
        seed: 颜色种子，用于生成固定颜色
        
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
        
        # 获取渐变色（基于种子值的固定颜色）
        start_color, end_color = get_gradient_colors(seed)
        
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


def create_thumb_png(width: int = 200, height: int = 150, text: str = "WoniuNote", seed: int = None) -> Image.Image:
    """
    创建带文字的缩略图
    
    生成一个带有固定渐变背景和居中文字的图片。
    
    Args:
        width: 图片宽度
        height: 图片高度
        text: 显示的文字
        seed: 颜色种子，用于生成固定颜色（通常使用文章类型ID）
        
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
        
        # 生成渐变背景（使用种子确保颜色固定）
        image = generate_gradient_background(width, height, seed)
        draw = ImageDraw.Draw(image)
        
        # 获取字体
        font_path = get_system_font_path()
        try:
            if font_path:
                # 根据文字长度调整字体大小，确保较大的字体
                base_size = min(width, height) // 4  # 基础大小为短边的1/4
                font_size = min(base_size, int(width / max(len(text), 1) * 1.5))
                font_size = max(20, min(font_size, 48))  # 限制在20-48px之间
                font = ImageFont.truetype(font_path, font_size)
            else:
                font = ImageFont.load_default()
        except Exception as e:
            logger.warning(f"Failed to load font: {e}")
            font = ImageFont.load_default()
        
        # 计算文字位置（居中）
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        x = (width - text_width) // 2
        y = (height - text_height) // 2
        
        # 绘制文字（带阴影效果增强可读性）
        shadow_color = (0, 0, 0)
        text_color = (255, 255, 255)
        
        # 绘制阴影（多层阴影增强效果）
        for offset in [(2, 2), (1, 1)]:
            draw.text((x + offset[0], y + offset[1]), text, font=font, fill=shadow_color)
        # 绘制白色文字
        draw.text((x, y), text, font=font, fill=text_color)
        
        logger.info(f"Thumbnail created: {width}x{height}, text: {text}, seed: {seed}")
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
