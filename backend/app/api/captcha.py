"""
验证码 API 模块

本模块提供图片验证码的生成、验证以及内部验证工具函数。
"""
import random
import base64
import threading
from io import BytesIO
from datetime import datetime, timedelta
from fastapi import APIRouter, Response
from PIL import Image, ImageDraw, ImageFont
import os

router = APIRouter()

# 存储验证码 (简化版，生产环境应使用Redis)
# 格式: {captcha_id: (code, expire_time)}
captcha_store = {}
captcha_lock = threading.Lock()

# 验证码有效期（秒）
CAPTCHA_EXPIRE_SECONDS = 300  # 5分钟


def cleanup_expired_captchas():
    """
    清理过期的验证码
    
    遍历内存中的验证码存储，删除已过期的条目。
    """
    now = datetime.now()
    with captcha_lock:
        expired_keys = [
            key for key, (code, expire_time) in captcha_store.items()
            if expire_time < now
        ]
        for key in expired_keys:
            del captcha_store[key]


def get_system_font():
    """
    获取系统字体
    
    尝试获取系统中可用的字体路径，用于生成验证码图片。
    
    Returns:
        str | None: 字体文件路径，如果未找到则返回 None
    """
    font_paths = [
        "C:\\Windows\\Fonts\\arial.ttf",
        "C:\\Windows\\Fonts\\Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for path in font_paths:
        if os.path.exists(path):
            return path
    return None


def generate_captcha_image(code: str, width: int = 120, height: int = 50):
    """
    生成验证码图片
    
    根据验证码字符串生成对应的图片对象。
    
    Args:
        code: 验证码字符串
        width: 图片宽度
        height: 图片高度
        
    Returns:
        Image: PIL Image 对象
    """
    # 创建白色背景图片
    image = Image.new('RGB', (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(image)
    
    # 加载字体
    font_path = get_system_font()
    try:
        if font_path:
            font = ImageFont.truetype(font_path, 36)
        else:
            font = ImageFont.load_default()
    except Exception:
        font = ImageFont.load_default()
    
    # 为每个字符生成随机颜色并绘制
    colors = [
        (66, 133, 244),   # 蓝色
        (219, 68, 55),    # 红色
        (244, 180, 0),    # 黄色
        (15, 157, 88),    # 绿色
        (171, 71, 188),   # 紫色
    ]
    
    char_width = width // len(code)
    for i, char in enumerate(code):
        color = random.choice(colors)
        x = 10 + char_width * i
        y = random.randint(5, 10)
        draw.text((x, y), char, font=font, fill=color)
    
    return image


def generate_code(length: int = 4) -> str:
    """
    生成随机数字验证码
    
    Args:
        length: 验证码长度
        
    Returns:
        str: 随机数字字符串
    """
    return ''.join(random.choices('0123456789', k=length))


@router.get("/generate")
async def generate_captcha():
    """
    生成验证码图片
    
    生成一个新的验证码，存储在内存中，并返回 Base64 编码的图片数据。
    
    Returns:
        dict: 包含验证码 ID 和 Base64 图片数据
    """
    # 先清理过期验证码（每次生成时清理，避免内存泄漏）
    cleanup_expired_captchas()
    
    # 生成验证码
    code = generate_code()
    
    # 生成唯一ID
    captcha_id = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=16))
    
    # 存储验证码（带过期时间）
    expire_time = datetime.now() + timedelta(seconds=CAPTCHA_EXPIRE_SECONDS)
    with captcha_lock:
        captcha_store[captcha_id] = (code, expire_time)
    
    # 生成图片
    image = generate_captcha_image(code)
    
    # 转换为base64
    buffer = BytesIO()
    image.save(buffer, format='PNG')
    image_base64 = base64.b64encode(buffer.getvalue()).decode()
    
    return {
        "code": 200,
        "message": "success",
        "data": {
            "captcha_id": captcha_id,
            "image": f"data:image/png;base64,{image_base64}"
        }
    }


@router.post("/verify")
async def verify_captcha(captcha_id: str, captcha_code: str):
    """
    验证验证码
    
    验证用户输入的验证码是否正确。验证后会删除已使用的验证码。
    
    Args:
        captcha_id: 验证码 ID
        captcha_code: 用户输入的验证码
        
    Returns:
        dict: 验证结果
    """
    with captcha_lock:
        stored = captcha_store.get(captcha_id)
        
        if not stored:
            return {
                "code": 400,
                "message": "验证码已过期",
                "data": {"valid": False}
            }
        
        stored_code, expire_time = stored
        
        # 检查是否过期
        if datetime.now() > expire_time:
            del captcha_store[captcha_id]
            return {
                "code": 400,
                "message": "验证码已过期",
                "data": {"valid": False}
            }
        
        # 验证后删除
        del captcha_store[captcha_id]
    
    if stored_code.lower() == captcha_code.lower():
        return {
            "code": 200,
            "message": "验证成功",
            "data": {"valid": True}
        }
    else:
        return {
            "code": 400,
            "message": "验证码错误",
            "data": {"valid": False}
        }


def validate_captcha(captcha_id: str, captcha_code: str) -> tuple[bool, str]:
    """
    内部验证函数，供其他模块调用
    
    验证验证码并返回布尔值和错误信息。
    
    Args:
        captcha_id: 验证码 ID
        captcha_code: 用户输入的验证码
        
    Returns:
        tuple[bool, str]: (是否验证通过, 错误信息)
    """
    if not captcha_id or not captcha_code:
        return False, "请输入验证码"
    
    with captcha_lock:
        stored = captcha_store.get(captcha_id)
        
        if not stored:
            return False, "验证码已过期，请点击刷新"
        
        stored_code, expire_time = stored
        
        # 检查是否过期
        if datetime.now() > expire_time:
            del captcha_store[captcha_id]
            return False, "验证码已过期，请点击刷新"
        
        # 验证后删除
        del captcha_store[captcha_id]
    
    if stored_code.lower() == captcha_code.lower():
        return True, ""
    else:
        return False, "验证码错误"
