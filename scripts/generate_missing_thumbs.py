#!/usr/bin/env python3
"""
生成缺失的缩略图文件
"""

import os
import sys
from PIL import Image, ImageDraw, ImageFont
import random

# 添加项目路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from woniunote.common.database import ARTICLE_TYPES

def generate_thumb_image(type_id, title, output_path, width=226, height=136):
    """生成缩略图"""
    # 创建背景色
    colors = [
        (135, 206, 235),  # 天蓝色
        (255, 182, 193),  # 粉色
        (144, 238, 144),  # 淡绿色
        (255, 218, 185),  # 杏色
        (221, 160, 221),  # 梅红色
        (176, 196, 222),  # 钢蓝色
        (255, 228, 181),  # 浅黄色
        (188, 143, 143),  # 玫瑰棕色
        (152, 251, 152),  # 苍绿色
        (255, 192, 203),  # 粉红色
    ]

    # 根据类型ID选择颜色
    color = colors[int(type_id) % len(colors)]

    # 创建图像
    image = Image.new('RGB', (width, height), color)
    draw = ImageDraw.Draw(image)

    # 尝试加载字体
    try:
        # 使用系统字体
        font_path = "/System/Library/Fonts/PingFang.ttc"  # macOS
        if not os.path.exists(font_path):
            font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"  # Linux
        if not os.path.exists(font_path):
            font_path = "C:/Windows/Fonts/simhei.ttf"  # Windows
        if os.path.exists(font_path):
            title_font = ImageFont.truetype(font_path, 24)
            type_font = ImageFont.truetype(font_path, 18)
        else:
            title_font = ImageFont.load_default()
            type_font = ImageFont.load_default()
    except:
        title_font = ImageFont.load_default()
        type_font = ImageFont.load_default()

    # 绘制标题
    title_bbox = draw.textbbox((0, 0), title, font=title_font)
    title_width = title_bbox[2] - title_bbox[0]
    title_height = title_bbox[3] - title_bbox[1]

    # 限制标题长度
    if title_width > width - 20:
        while title_width > width - 20 and len(title) > 3:
            title = title[:-1]
            title_bbox = draw.textbbox((0, 0), title + "...", font=title_font)
            title_width = title_bbox[2] - title_bbox[0]
        title += "..."
        title_bbox = draw.textbbox((0, 0), title, font=title_font)
        title_width = title_bbox[2] - title_bbox[0]

    # 绘制标题
    title_x = (width - title_width) // 2
    title_y = (height - title_height) // 2 - 10
    draw.text((title_x, title_y), title, fill='white', font=title_font)

    # 绘制类型ID
    type_text = f"类型 {type_id}"
    type_bbox = draw.textbbox((0, 0), type_text, font=type_font)
    type_width = type_bbox[2] - type_bbox[0]
    type_x = (width - type_width) // 2
    type_y = title_y + title_height + 10
    draw.text((type_x, type_y), type_text, fill='white', font=type_font)

    # 保存图像
    image.save(output_path, 'PNG')
    print(f"已生成缩略图: {output_path}")

def main():
    """主函数"""
    thumb_dir = os.path.join(project_root, 'woniunote', 'resource', 'thumb')

    if not os.path.exists(thumb_dir):
        print(f"缩略图目录不存在: {thumb_dir}")
        return

    print("开始生成缺失的缩略图文件...")

    # 获取现有文件列表
    existing_files = set()
    for filename in os.listdir(thumb_dir):
        if filename.endswith('.png'):
            try:
                file_id = int(filename[:-4])  # 移除.png扩展名
                existing_files.add(file_id)
            except ValueError:
                continue

    print(f"现有缩略图文件数量: {len(existing_files)}")

    # 生成缺失的缩略图
    generated_count = 0
    for type_id, title in ARTICLE_TYPES.items():
        if type_id not in existing_files:
            output_path = os.path.join(thumb_dir, f"{type_id}.png")
            try:
                generate_thumb_image(str(type_id), title, output_path)
                generated_count += 1
            except Exception as e:
                print(f"生成缩略图失败 {type_id}: {e}")

    print(f"生成完成! 新生成 {generated_count} 个缩略图文件")
    print(f"总缩略图文件数量: {len(existing_files) + generated_count}")

if __name__ == "__main__":
    main()
