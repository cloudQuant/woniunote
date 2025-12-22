#!/usr/bin/env python3
"""
Generate beautiful thumbnails for article types.
Creates gradient backgrounds with decorative elements.
"""

import os
from PIL import Image, ImageDraw, ImageFont
import math

# Thumbnail dimensions
WIDTH = 226
HEIGHT = 136

# Article types with their colors (gradient start, gradient end)
ARTICLE_TYPES = {
    1: ("交易策略", "#9B59B6", "#8E44AD"),
    101: ("CTA策略", "#3498DB", "#2980B9"),
    102: ("统计套利", "#1ABC9C", "#16A085"),
    103: ("高频交易", "#E74C3C", "#C0392B"),
    104: ("因子策略", "#F39C12", "#D68910"),
    105: ("选股与择时", "#9B59B6", "#8E44AD"),
    106: ("机器学习", "#34495E", "#2C3E50"),
    107: ("深度学习", "#E67E22", "#D35400"),
    
    2: ("量化框架", "#27AE60", "#229954"),
    201: ("backtrader", "#3498DB", "#2980B9"),
    202: ("wondertrader", "#9B59B6", "#8E44AD"),
    203: ("wtpy", "#1ABC9C", "#16A085"),
    204: ("pyfolio", "#E74C3C", "#C0392B"),
    205: ("alphalens", "#F39C12", "#D68910"),
    
    3: ("投资", "#2ECC71", "#27AE60"),
    301: ("股票", "#E74C3C", "#C0392B"),
    302: ("期货", "#3498DB", "#2980B9"),
    303: ("期权", "#9B59B6", "#8E44AD"),
    304: ("外汇", "#1ABC9C", "#16A085"),
    305: ("crypto", "#F39C12", "#D68910"),
    306: ("黄金", "#F1C40F", "#D4AC0D"),
    307: ("债券", "#34495E", "#2C3E50"),
    
    4: ("理财", "#16A085", "#138D75"),
    401: ("基金", "#3498DB", "#2980B9"),
    402: ("保险", "#9B59B6", "#8E44AD"),
    403: ("信托", "#E74C3C", "#C0392B"),
    404: ("银行理财", "#27AE60", "#229954"),
    405: ("存款", "#F39C12", "#D68910"),
    
    5: ("区块链与defi", "#8E44AD", "#7D3C98"),
    501: ("去中心化交易所", "#3498DB", "#2980B9"),
    502: ("去中心化金融", "#1ABC9C", "#16A085"),
    503: ("去中心化借贷", "#E74C3C", "#C0392B"),
    504: ("去中心化治理", "#F39C12", "#D68910"),
    505: ("其他defi", "#9B59B6", "#8E44AD"),
    506: ("区块链", "#34495E", "#2C3E50"),
    507: ("比特币", "#F7931A", "#E67E22"),
    508: ("以太坊", "#627EEA", "#5B6EE1"),
    
    6: ("机器学习", "#34495E", "#2C3E50"),
    601: ("tensorflow", "#FF6F00", "#E65100"),
    602: ("pytorch", "#EE4C2C", "#D84315"),
    603: ("keras", "#D00000", "#B71C1C"),
    604: ("scikit-learn", "#F89939", "#F57C00"),
    605: ("机器学习与交易", "#3498DB", "#2980B9"),
    606: ("深度学习与交易", "#9B59B6", "#8E44AD"),
    
    7: ("编程", "#2980B9", "#1F618D"),
    701: ("python", "#3776AB", "#2E6B97"),
    702: ("c++", "#00599C", "#004D8C"),
    703: ("cython", "#F0DB4F", "#DAC84A"),
    704: ("java", "#ED8B00", "#D67E00"),
    705: ("javascript", "#F7DF1E", "#E0C91C"),
    706: ("swing", "#E74C3C", "#C0392B"),
    707: ("pybind11", "#3498DB", "#2980B9"),
    
    8: ("笔记", "#27AE60", "#229954"),
    801: ("幸福", "#2ECC71", "#27AE60"),
    802: ("金融", "#9B59B6", "#8E44AD"),
    803: ("经济", "#3498DB", "#2980B9"),
    804: ("哲学", "#8E44AD", "#7D3C98"),
    805: ("历史", "#D35400", "#BA4A00"),
    806: ("科技", "#1ABC9C", "#16A085"),
    807: ("读书笔记", "#34495E", "#2C3E50"),
    808: ("其他笔记", "#95A5A6", "#7F8C8D"),
    809: ("个人知识库", "#E74C3C", "#C0392B"),
    
    9: ("教程", "#E67E22", "#D35400"),
    901: ("woniunote入门教程", "#9B59B6", "#8E44AD"),
    902: ("backtrader基础教程", "#3498DB", "#2980B9"),
    903: ("airflow入门教程", "#00A4DC", "#0091C4"),
    904: ("arrow入门教程", "#1ABC9C", "#16A085"),
    905: ("量化交易入门教程", "#E74C3C", "#C0392B"),
    906: ("机器学习入门教程", "#34495E", "#2C3E50"),
    907: ("ib_tws_api入门教程", "#27AE60", "#229954"),
}


def hex_to_rgb(hex_color):
    """Convert hex color to RGB tuple."""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def create_gradient(width, height, color1, color2):
    """Create a vertical gradient image."""
    img = Image.new('RGB', (width, height))
    r1, g1, b1 = hex_to_rgb(color1)
    r2, g2, b2 = hex_to_rgb(color2)
    
    for y in range(height):
        ratio = y / height
        r = int(r1 + (r2 - r1) * ratio)
        g = int(g1 + (g2 - g1) * ratio)
        b = int(b1 + (b2 - b1) * ratio)
        for x in range(width):
            img.putpixel((x, y), (r, g, b))
    
    return img


def add_decorative_overlay(img):
    """Add decorative diagonal light overlay."""
    overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    
    # Draw diagonal light triangle (top-right corner)
    points = [
        (img.width * 0.5, 0),
        (img.width, 0),
        (img.width, img.height * 0.6),
    ]
    draw.polygon(points, fill=(255, 255, 255, 25))
    
    # Draw smaller inner triangle
    points2 = [
        (img.width * 0.7, 0),
        (img.width, 0),
        (img.width, img.height * 0.4),
    ]
    draw.polygon(points2, fill=(255, 255, 255, 15))
    
    # Convert original image to RGBA
    img_rgba = img.convert('RGBA')
    
    # Composite overlay
    result = Image.alpha_composite(img_rgba, overlay)
    return result.convert('RGB')


def add_bottom_dots(draw, width, height):
    """Add decorative dots at bottom left."""
    dot_y = height - 15
    dot_radius = 3
    dot_spacing = 10
    start_x = 15
    
    for i in range(3):
        x = start_x + i * dot_spacing
        draw.ellipse([x - dot_radius, dot_y - dot_radius, 
                      x + dot_radius, dot_y + dot_radius], 
                     fill=(255, 255, 255, 180))


def get_font(size):
    """Get a suitable font for text rendering."""
    # Try common Chinese font paths
    font_paths = [
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Light.ttc",
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "/Library/Fonts/Arial Unicode.ttf",
        "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    ]
    
    for font_path in font_paths:
        if os.path.exists(font_path):
            try:
                return ImageFont.truetype(font_path, size)
            except:
                continue
    
    # Fallback to default font
    return ImageFont.load_default()


def create_thumbnail(type_id, name, color1, color2, output_path):
    """Create a beautiful thumbnail for an article type."""
    # Create gradient background
    img = create_gradient(WIDTH, HEIGHT, color1, color2)
    
    # Add decorative overlay
    img = add_decorative_overlay(img)
    
    # Create drawing context
    draw = ImageDraw.Draw(img)
    
    # Add bottom dots
    add_bottom_dots(draw, WIDTH, HEIGHT)
    
    # Calculate font size based on text length
    if len(name) <= 2:
        font_size = 42
    elif len(name) <= 4:
        font_size = 36
    elif len(name) <= 6:
        font_size = 28
    else:
        font_size = 22
    
    font = get_font(font_size)
    
    # Get text bounding box
    bbox = draw.textbbox((0, 0), name, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    # Center text (slightly above center for visual balance)
    x = (WIDTH - text_width) // 2
    y = (HEIGHT - text_height) // 2 - 8
    
    # Draw text with slight shadow for depth
    shadow_offset = 2
    draw.text((x + shadow_offset, y + shadow_offset), name, 
              font=font, fill=(0, 0, 0, 60))
    draw.text((x, y), name, font=font, fill=(255, 255, 255))
    
    # Save thumbnail
    img.save(output_path, 'PNG', quality=95)
    print(f"Generated: {output_path}")


def main():
    """Generate all thumbnails."""
    # Determine output directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(script_dir, "..", "resource", "thumb")
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"Generating thumbnails to: {output_dir}")
    
    # Generate thumbnail for each article type
    for type_id, (name, color1, color2) in ARTICLE_TYPES.items():
        output_path = os.path.join(output_dir, f"{type_id}.png")
        create_thumbnail(type_id, name, color1, color2, output_path)
    
    # Generate default thumbnail (type 1)
    default_path = os.path.join(output_dir, "1.png")
    if not os.path.exists(default_path):
        create_thumbnail(1, "交易策略", "#9B59B6", "#8E44AD", default_path)
    
    print(f"\nGenerated {len(ARTICLE_TYPES)} thumbnails successfully!")


if __name__ == "__main__":
    main()
