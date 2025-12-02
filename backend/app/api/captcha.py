"""
验证码API
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
    """清理过期的验证码"""
    now = datetime.now()
    with captcha_lock:
        expired_keys = [
            key for key, (code, expire_time) in captcha_store.items()
            if expire_time < now
        ]
        for key in expired_keys:
            del captcha_store[key]


def get_system_font():
    """获取系统字体"""
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
    """生成验证码图片"""
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
    """生成随机数字验证码"""
    return ''.join(random.choices('0123456789', k=length))


@router.get("/generate")
async def generate_captcha():
    """生成验证码图片"""
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
    """验证验证码"""
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
    返回: (是否验证通过, 错误信息)
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
