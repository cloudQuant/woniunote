#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
文章类型缩略图生成脚本

用于批量生成或重新生成所有文章类型的缩略图。
解决缩略图显示乱码（中文字体问题）。

使用方法:
    python scripts/generate_type_thumbnails.py [--force] [--type TYPE_ID]

参数:
    --force     强制重新生成所有缩略图（即使已存在）
    --type      仅生成指定类型ID的缩略图
    --list      列出所有文章类型
    --check     检查现有缩略图状态
"""

import os
import sys
import argparse
import logging
from pathlib import Path

# 添加项目根目录到路径
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent
backend_dir = project_root / "backend"
sys.path.insert(0, str(backend_dir))

from PIL import Image, ImageDraw, ImageFont

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 缩略图配置
THUMB_WIDTH = 226
THUMB_HEIGHT = 136
# 新架构：缩略图存放在 backend/resource/thumb/
THUMB_DIR = project_root / "backend" / "resource" / "thumb"

# 文章类型映射（完整列表）
ARTICLE_TYPE_NAMES = {
    1: '交易策略',
    101: 'CTA策略', 102: '统计套利', 103: '高频交易', 104: '因子策略',
    105: '选股与择时', 106: '机器学习', 107: '深度学习',
    2: '量化框架',
    201: 'backtrader', 202: 'wondertrader', 203: 'wtpy',
    204: 'pyfolio', 205: 'alphalens',
    3: '投资',
    301: '股票', 302: '期货', 303: '期权', 304: '外汇',
    305: 'crypto', 306: '黄金', 307: '债券',
    4: '理财',
    401: '基金', 402: '保险', 403: '信托', 404: '银行理财', 405: '存款',
    5: '区块链与defi',
    501: '去中心化交易所', 502: '去中心化金融', 503: '去中心化借贷',
    504: '去中心化治理', 505: '其他defi', 506: '区块链',
    507: '比特币', 508: '以太坊',
    6: '机器学习',
    601: 'tensorflow', 602: 'pytorch', 603: 'keras',
    604: 'scikit-learn', 605: '机器学习与交易', 606: '深度学习与交易',
    7: '编程',
    701: 'python', 702: 'c++', 703: 'cython', 704: 'java',
    705: 'javascript', 706: 'swing', 707: 'pybind11',
    8: '笔记',
    801: '幸福', 802: '金融', 803: '经济', 804: '哲学', 805: '历史',
    806: '科技', 807: '读书笔记', 808: '其他笔记', 809: '个人知识库',
    9: '教程',
    901: 'woniunote入门', 902: 'backtrader教程', 903: 'airflow教程',
    904: 'arrow教程', 905: '量化交易入门', 906: '机器学习入门', 907: 'ib_tws_api教程',
    10: '其他',
    11: '翻译'
}


def get_chinese_font_path():
    """
    获取支持中文的字体路径
    
    按优先级尝试多个系统字体路径（Windows/Linux/Mac）。
    
    Returns:
        str | None: 字体文件路径，未找到则返回 None
    """
    if os.name == 'nt':  # Windows
        font_paths = [
            "C:\\Windows\\Fonts\\msyh.ttc",       # 微软雅黑
            "C:\\Windows\\Fonts\\msyhbd.ttc",     # 微软雅黑粗体
            "C:\\Windows\\Fonts\\simhei.ttf",     # 黑体
            "C:\\Windows\\Fonts\\simsun.ttc",     # 宋体
            "C:\\Windows\\Fonts\\simkai.ttf",     # 楷体
            "C:\\Windows\\Fonts\\STZHONGS.TTF",   # 华文中宋
        ]
    else:  # Linux/Mac
        font_paths = [
            # Linux
            "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",  # 文泉驿微米黑
            "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",    # 文泉驿正黑
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",  # Noto CJK
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
            # Mac
            "/System/Library/Fonts/PingFang.ttc",
            "/System/Library/Fonts/STHeiti Light.ttc",
            "/Library/Fonts/Arial Unicode.ttf",
        ]
    
    for font_path in font_paths:
        if os.path.exists(font_path):
            logger.info(f"使用字体: {font_path}")
            return font_path
    
    logger.warning("未找到支持中文的字体，将使用默认字体（可能无法正确显示中文）")
    return None


def generate_random_gradient():
    """
    生成随机渐变色
    
    Returns:
        tuple: ((r1, g1, b1), (r2, g2, b2)) 起始颜色和结束颜色
    """
    import random
    
    # 预定义一些好看的渐变色组合
    gradients = [
        ((139, 69, 69), (95, 47, 47)),       # 红棕色
        ((76, 132, 86), (52, 100, 52)),      # 绿色
        ((70, 130, 180), (47, 90, 130)),     # 蓝色
        ((147, 112, 219), (100, 75, 150)),   # 紫色
        ((218, 165, 32), (160, 120, 20)),    # 金色
        ((205, 92, 92), (150, 60, 60)),      # 印度红
        ((60, 179, 113), (40, 130, 80)),     # 海绿色
        ((100, 149, 237), (70, 110, 180)),   # 矢车菊蓝
        ((255, 140, 0), (200, 100, 0)),      # 深橙色
        ((123, 104, 238), (90, 75, 180)),    # 中紫色
    ]
    
    return random.choice(gradients)


def create_gradient_image(width, height, start_color, end_color):
    """
    创建渐变背景图片
    
    Args:
        width: 图片宽度
        height: 图片高度
        start_color: 起始颜色 (r, g, b)
        end_color: 结束颜色 (r, g, b)
        
    Returns:
        Image: PIL Image 对象
    """
    image = Image.new('RGB', (width, height))
    
    for y in range(height):
        ratio = y / height
        r = int(start_color[0] * (1 - ratio) + end_color[0] * ratio)
        g = int(start_color[1] * (1 - ratio) + end_color[1] * ratio)
        b = int(start_color[2] * (1 - ratio) + end_color[2] * ratio)
        
        for x in range(width):
            image.putpixel((x, y), (r, g, b))
    
    return image


def create_thumbnail(type_id, text, font_path=None, seed=None):
    """
    创建带文字的缩略图
    
    Args:
        type_id: 类型ID（用于生成一致的随机颜色）
        text: 显示的文字
        font_path: 字体路径
        seed: 随机种子（使相同type_id生成相同颜色）
    
    Returns:
        Image: PIL Image对象
    """
    import random
    
    # 使用type_id作为随机种子，确保相同类型生成相同颜色
    if seed is not None:
        random.seed(seed)
    else:
        random.seed(type_id)
    
    # 生成渐变背景
    start_color, end_color = generate_random_gradient()
    image = create_gradient_image(THUMB_WIDTH, THUMB_HEIGHT, start_color, end_color)
    draw = ImageDraw.Draw(image)
    
    # 加载字体
    try:
        if font_path:
            # 根据文字长度调整字体大小
            if len(text) <= 4:
                font_size = 32
            elif len(text) <= 6:
                font_size = 28
            elif len(text) <= 8:
                font_size = 24
            else:
                font_size = 20
            
            font = ImageFont.truetype(font_path, font_size)
        else:
            font = ImageFont.load_default()
    except Exception as e:
        logger.warning(f"加载字体失败: {e}，使用默认字体")
        font = ImageFont.load_default()
    
    # 计算文字位置（居中）
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    x = (THUMB_WIDTH - text_width) // 2
    y = (THUMB_HEIGHT - text_height) // 2
    
    # 绘制文字阴影
    shadow_offset = 2
    draw.text((x + shadow_offset, y + shadow_offset), text, font=font, fill=(0, 0, 0, 180))
    
    # 绘制主文字（白色）
    draw.text((x, y), text, font=font, fill=(255, 255, 255))
    
    return image


def generate_all_thumbnails(force=False, specific_type=None):
    """
    生成所有文章类型的缩略图
    
    Args:
        force: 是否强制重新生成（即使已存在）
        specific_type: 仅生成指定类型ID
    """
    # 确保目录存在
    THUMB_DIR.mkdir(parents=True, exist_ok=True)
    
    # 获取中文字体
    font_path = get_chinese_font_path()
    
    # 确定要生成的类型
    if specific_type is not None:
        if specific_type in ARTICLE_TYPE_NAMES:
            types_to_generate = {specific_type: ARTICLE_TYPE_NAMES[specific_type]}
        else:
            logger.error(f"未知的类型ID: {specific_type}")
            return
    else:
        types_to_generate = ARTICLE_TYPE_NAMES
    
    generated_count = 0
    skipped_count = 0
    failed_count = 0
    
    for type_id, type_name in types_to_generate.items():
        thumb_path = THUMB_DIR / f"{type_id}.png"
        
        # 检查是否需要生成
        if thumb_path.exists() and not force:
            logger.info(f"跳过 {type_id}.png ({type_name}) - 已存在")
            skipped_count += 1
            continue
        
        try:
            # 生成缩略图
            image = create_thumbnail(type_id, type_name, font_path)
            image.save(str(thumb_path), "PNG")
            logger.info(f"✓ 生成 {type_id}.png ({type_name})")
            generated_count += 1
        except Exception as e:
            logger.error(f"✗ 生成 {type_id}.png ({type_name}) 失败: {e}")
            failed_count += 1
    
    print("\n" + "=" * 50)
    print(f"生成完成！")
    print(f"  新生成: {generated_count}")
    print(f"  已跳过: {skipped_count}")
    print(f"  失败: {failed_count}")
    print(f"  缩略图目录: {THUMB_DIR}")
    print("=" * 50)


def list_article_types():
    """列出所有文章类型"""
    print("\n文章类型列表:")
    print("=" * 50)
    
    # 按父类型分组
    parent_types = {}
    child_types = {}
    
    for type_id, type_name in ARTICLE_TYPE_NAMES.items():
        if type_id < 100:
            parent_types[type_id] = type_name
        else:
            parent_id = type_id // 100
            if parent_id not in child_types:
                child_types[parent_id] = []
            child_types[parent_id].append((type_id, type_name))
    
    for parent_id in sorted(parent_types.keys()):
        print(f"\n[{parent_id}] {parent_types[parent_id]}")
        if parent_id in child_types:
            for type_id, type_name in sorted(child_types[parent_id]):
                print(f"    [{type_id}] {type_name}")
    
    print("\n" + "=" * 50)
    print(f"总计: {len(ARTICLE_TYPE_NAMES)} 个类型")


def check_thumbnails():
    """检查现有缩略图状态"""
    print("\n缩略图状态检查:")
    print("=" * 50)
    
    if not THUMB_DIR.exists():
        print(f"缩略图目录不存在: {THUMB_DIR}")
        return
    
    existing = set()
    for f in THUMB_DIR.iterdir():
        if f.suffix.lower() == '.png':
            try:
                type_id = int(f.stem)
                existing.add(type_id)
            except ValueError:
                pass
    
    missing = []
    present = []
    
    for type_id, type_name in ARTICLE_TYPE_NAMES.items():
        if type_id in existing:
            present.append((type_id, type_name))
        else:
            missing.append((type_id, type_name))
    
    print(f"\n已存在 ({len(present)} 个):")
    for type_id, type_name in present:
        thumb_path = THUMB_DIR / f"{type_id}.png"
        size = thumb_path.stat().st_size
        print(f"  ✓ [{type_id}] {type_name} ({size} bytes)")
    
    print(f"\n缺失 ({len(missing)} 个):")
    for type_id, type_name in missing:
        print(f"  ✗ [{type_id}] {type_name}")
    
    # 检查多余的文件
    all_type_ids = set(ARTICLE_TYPE_NAMES.keys())
    extra = existing - all_type_ids
    if extra:
        print(f"\n多余文件 ({len(extra)} 个):")
        for type_id in sorted(extra):
            print(f"  ? [{type_id}].png")
    
    print("\n" + "=" * 50)


def main():
    parser = argparse.ArgumentParser(
        description='文章类型缩略图生成工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python generate_type_thumbnails.py            # 生成缺失的缩略图
  python generate_type_thumbnails.py --force    # 强制重新生成所有缩略图
  python generate_type_thumbnails.py --type 101 # 仅生成类型101的缩略图
  python generate_type_thumbnails.py --list     # 列出所有文章类型
  python generate_type_thumbnails.py --check    # 检查缩略图状态
        """
    )
    
    parser.add_argument('--force', '-f', action='store_true',
                        help='强制重新生成所有缩略图（即使已存在）')
    parser.add_argument('--type', '-t', type=int, metavar='TYPE_ID',
                        help='仅生成指定类型ID的缩略图')
    parser.add_argument('--list', '-l', action='store_true',
                        help='列出所有文章类型')
    parser.add_argument('--check', '-c', action='store_true',
                        help='检查现有缩略图状态')
    
    args = parser.parse_args()
    
    if args.list:
        list_article_types()
    elif args.check:
        check_thumbnails()
    else:
        print("=" * 50)
        print("文章类型缩略图生成工具")
        print("=" * 50)
        generate_all_thumbnails(force=args.force, specific_type=args.type)


if __name__ == '__main__':
    main()
