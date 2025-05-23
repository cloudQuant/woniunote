import random
import string
import time
import yaml
import re
from datetime import datetime
from email.header import Header
from email.mime.text import MIMEText
from io import BytesIO
# 发送邮箱验证码
from smtplib import SMTP_SSL
import importlib
import hashlib
import sys
import os
import requests
import pymysql
from pymysql.cursors import DictCursor
from PIL import Image, ImageFont, ImageDraw, ImageOps, ImageFilter
from urllib.parse import urlparse
import math

# 初始化数据库连接
def get_db_connection(database_info):
    try:
        connection = pymysql.connect(
            host=database_info['host'],
            user=database_info['user'],
            password=database_info['password'],
            database=database_info['database'],
            cursorclass=DictCursor
        )
        return connection
    except pymysql.err.OperationalError as e:
        print("连接数据库失败, {}".format(e))

def parse_db_uri(db_uri):
    """
    解析 SQLALCHEMY_DATABASE_URI，提取数据库连接信息
    """
    try:
        # 解析 URI
        parsed = urlparse(db_uri)

        # 提取用户名和密码
        username = parsed.username
        password = parsed.password

        # 提取主机和端口
        host = parsed.hostname
        port = parsed.port or 3306  # 如果未指定端口，默认为 3306

        # 提取数据库名称
        database = parsed.path.lstrip('/')  # 去掉路径开头的斜杠

        result = {
            'host': host,
            'port': port,
            'user': username,
            'password': password,
            'database': database
        }
        print(result)
        return result
    except Exception as e:
        print(e)


def get_package_path(package_name="lv"):
    """获取包的路径值
    :param package_name: 包的名称
    :return: 返回的路径值
    """
    try:
        importlib.import_module(package_name)
        package = sys.modules[package_name]
    except KeyError:
        print(f"Package {package_name} not found")
        return None
    if package.__file__ is not None:
        return os.path.dirname(package.__file__)
    else:
        return package.__path__.__dict__["_path"][0]


# 打开配置文件
def read_config(config_file=None):
    package_path = get_package_path("woniunote")
    if config_file is None:
        file_path = package_path + "/configs/user_password_config.yaml"
        with open(file_path, 'r', encoding='utf-8') as f:
            config_result = yaml.load(f.read(), Loader=yaml.FullLoader)
    else:
        file_path = package_path + f"/{config_file}"
        if not os.path.exists(file_path):
            return None
        with open(file_path, 'r', encoding='utf-8') as f:
            config_result = yaml.load(f.read(), Loader=yaml.FullLoader)
    return config_result


class ImageCode:
    def __init__(self, width=120, height=40):
        self.width = width
        self.height = height
        self.img = Image.new('RGB', (width, height), color=(255, 255, 255))
        self.font = ImageFont.truetype(get_system_font_path(), 32)
    # 生成用于绘制字符串的随机颜色
    def rand_color(self):
        red = random.randint(32, 200)
        green = random.randint(22, 255)
        blue = random.randint(0, 200)
        return red, green, blue

    # 生成4位随机字符串
    def gen_text(self):
        # sample用于从一个大的列表或字符串中，随机取得N个字符，来构建出一个子列表
        # list = random.sample(string.ascii_letters+string.digits, 4)
        s_list = random.sample(string.digits, 4)
        return ''.join(s_list)

    # 画一些干扰线，其中draw为PIL中的ImageDraw对象
    def draw_lines(self, draw, num, width, height):
        for num in range(num):
            x1 = random.randint(0, width / 2)
            y1 = random.randint(0, height / 2)
            x2 = random.randint(0, width)
            y2 = random.randint(height / 2, height)
            draw.line(((x1, y1), (x2, y2)), fill='black', width=2)

    # 绘制验证码图片
    def draw_verify_code(self):
        code = self.gen_text()
        # 创建图片对象，并设定背景色为白色
        im = Image.new('RGB', (self.width, self.height), 'white')
        # 选择使用何种字体及字体大小
        font = ImageFont.load_default(size=40)  # 使用 Pillow 自带的字体
        draw = ImageDraw.Draw(im)  # 新建ImageDraw对象
        # 绘制字符串
        for i in range(4):
            draw.text((5 + random.randint(-3, 3) + 23 * i, 5 + random.randint(-3, 3)),
                      text=code[i], fill=self.rand_color(), font=font)
        # 绘制干扰线
        # self.draw_lines(draw, 4, width, height)
        # im.show()   # 如需临时调试，可以直接将生成的图片显示出来
        return im, code

    # 生成图片验证码并返回给控制器
    def get_code(self):
        image, code = self.draw_verify_code()
        buf = BytesIO()
        image.save(buf, 'jpeg')
        b_string = buf.getvalue()
        return code, b_string


# 发送QQ邮箱验证码, 参数为收件箱地址和随机生成的验证码
def send_email(receiver, ecode):
    sender = 'WoniuNote <15903523@qq.com>'  # 你的邮箱账号和发件者签名
    # 定义发送邮件的内容，支持HTML标签和CSS样式
    content = f"<br/>欢迎注册蜗牛笔记博客系统账号，您的邮箱验证码为：" \
              f"<span style='color: red; font-size: 20px;'>{ecode}</span>，" \
              f"请复制到注册窗口中完成注册，感谢您的支持。<br/>"
    # 实例化邮件对象，并指定邮件的关键信息
    message = MIMEText(content, 'html', 'utf-8')
    # 指定邮件的标题，同样使用utf-8 编码
    message['Subject'] = Header('蜗牛笔记的注册验证码', 'utf-8')
    message['From'] = sender  # 指定发件人信息
    message['To'] = receiver  # 指定收件人邮箱地址

    smtp_obj = SMTP_SSL('smtp.qq.com')  # 建议与QQ邮件服务器的连接
    # 通过你的邮箱账号和获取到的授权码登录QQ邮箱
    smtp_obj.login(user='15903523@qq.com', password='uczmmmqvpxwjbjaf')
    # 指定发件人，收件人和邮件内容
    smtp_obj.sendmail(sender, receiver, str(message))
    smtp_obj.quit()


# 生成6位随机字符串作为邮箱验证码
def gen_email_code():
    return ''.join(random.sample(string.ascii_letters + string.digits, 6))


# 单个模型类转换为标准的Python List数据
def model_list(result):
    m_list = []
    for row in result:
        m_dict = {}
        for k, v in row.__dict__.items():
            if not k.startswith('_sa_instance_state'):
                # 如果某个字段的值是datetime类型，则将其格式为字符串
                if isinstance(v, datetime):
                    v = v.strftime('%Y-%m-%d %H:%M:%S')
                m_dict[k] = v
        m_list.append(m_dict)

    return m_list


# SQLAlchemy连接查询两张表的结果集转换为[{},{}]


# 获取系统默认字体路径
def get_system_font_path():
    """Get a valid font path for different OS"""
    if os.name == 'nt':  # Windows
        return "C:\\Windows\\Fonts\\Arial.ttf"
    elif os.name == 'posix':  # Linux/Mac
        # 常见Linux/Mac字体位置
        common_fonts = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "/Library/Fonts/Arial.ttf"
        ]
        for font in common_fonts:
            if os.path.exists(font):
                return font
    return None  # 如果都找不到，返回None


# 创建七彩蜗牛图标函数
def create_colorful_snail_icon():
    """Create a colorful snail icon as favicon based on the left part of the logo.png"""
    try:
        # 获取包路径
        package_path = get_package_path("woniunote")
        
        # 读取原始图标
        logo_path = f"{package_path}/resource/img/logo.png"
        favicon_path = f"{package_path}/resource/static/favicon.ico"
        
        if not os.path.exists(logo_path):
            print(f"Logo file not found at {logo_path}")
            return False
        
        # 打开原始图标并转换为RGBA模式以支持透明
        logo = Image.open(logo_path).convert('RGBA')
        
        # 获取图标尺寸
        width, height = logo.width, logo.height
        
        # 裁剪左半部分(假设蜗牛在左半部分)
        snail_part = logo.crop((0, 0, width // 2, height))
        
        # 创建新的正方形画布，由于favicon通常是正方形
        favicon_size = max(width // 2, height)
        
        # 创建新图像为透明背景
        new_icon = Image.new('RGBA', (favicon_size, favicon_size), (0, 0, 0, 0))
        
        # 将裁剪后的蜗牛图标粘贴到中心位置
        paste_position = (
            (favicon_size - snail_part.width) // 2,
            (favicon_size - snail_part.height) // 2
        )
        new_icon.paste(snail_part, paste_position, snail_part)
        
        # 应用七彩色彩效果 - 使用色相旋转和强化饱和度
        enhancer = ImageOps.colorize(
            snail_part.convert('L'), 
            black=(30, 0, 50),  # 深色调(紫色)
            white=(255, 100, 50),  # 浅色调(橙红色)
            mid=(50, 180, 230)   # 中间色调(蓝色)
        ).convert('RGBA')
        
        # 应用彩色效果
        colored_snail = Image.new('RGBA', snail_part.size, (0, 0, 0, 0))
        for y in range(snail_part.height):
            for x in range(snail_part.width):
                r, g, b, a = snail_part.getpixel((x, y))
                if a > 50:  # 只对非透明像素应用彩色
                    # 使用渐变色彩效果
                    h = (x + y) % 360  # 基于像素位置的色相值
                    s = 0.8  # 饱和度
                    v = 0.9  # 亮度
                    r, g, b = hsv_to_rgb(h/360, s, v)
                    colored_snail.putpixel((x, y), (int(r*255), int(g*255), int(b*255), a))
            
        # 将彩色蜗牛图像粘贴到新图标上
        new_icon.paste(colored_snail, paste_position, colored_snail)
        
        # 应用轮廓效果使图标更清晰
        new_icon = new_icon.filter(ImageFilter.SHARPEN)
        
        # 调整大小为标准favicon尺寸(32x32)
        new_icon = new_icon.resize((32, 32), Image.LANCZOS)
        
        # 保存为ICO格式
        new_icon.save(favicon_path, format='ICO')
        
        print(f"Colorful snail favicon created at {favicon_path}")
        return True
    except Exception as e:
        print(f"Error creating favicon: {e}")
        return False


# HSV到RGB的转换函数
def hsv_to_rgb(h, s, v):
    """
    Convert HSV color values to RGB
    h: 0-1 (hue)
    s: 0-1 (saturation)
    v: 0-1 (value)
    """
    if s == 0.0:
        return v, v, v
    
    i = int(h * 6)
    f = (h * 6) - i
    p = v * (1 - s)
    q = v * (1 - s * f)
    t = v * (1 - s * (1 - f))
    
    i %= 6
    if i == 0:
        return v, t, p
    elif i == 1:
        return q, v, p
    elif i == 2:
        return p, v, t
    elif i == 3:
        return p, q, v
    elif i == 4:
        return t, p, v
    else:
        return v, p, q
# Comment，Users， [(Comment, Users),(Comment, Users),(Comment, Users)]
def model_join_list(result):
    m_list = []  # 定义列表用于存放所有行
    for obj1, obj2 in result:
        m_dict = {}
        for k1, v1 in obj1.__dict__.items():
            if not k1.startswith('_sa_instance_state'):
                if k1 not in m_dict:  # 如果字典中已经存在相同的Key则跳过
                    m_dict[k1] = v1
        for k2, v2 in obj2.__dict__.items():
            if not k2.startswith('_sa_instance_state'):
                if k2 not in m_dict:  # 如果字典中已经存在相同的Key则跳过
                    m_dict[k2] = v2
        m_list.append(m_dict)
    return m_list


# 压缩图片，通过参数width指定压缩后的图片大小
def compress_image(source, dest, width):
    from PIL import Image
    # 如果图片宽度大于1200，则调整为1200的宽度
    im = Image.open(source)
    x, y = im.size  # 获取源图片的宽和高
    if x > width:
        # 等比例缩放
        ys = int(y * width / x)
        xs = width
        # 调整当前图片的尺寸（同时也会压缩大小）
        temp = im.resize((xs, ys), Image.Resampling.LANCZOS)
        # 将图片保存并使用80%的质量进行压缩
        temp.save(dest, quality=80)
    # 如果尺寸小于指定宽度则不缩减尺寸，只压缩保存
    else:
        im.save(dest, quality=80)


# 解析文章内容中的图片地址
def parse_image_url(content):
    # 正则表达式改进：考虑到可能有额外的空格或不同的属性顺序，确保提取 `src` 属性中的 URL
    temp_list = re.findall(r'<img[^>]*\s+src="([^"]+)"', content)

    url_list = []
    for url in temp_list:
        # 如果图片类型为 gif，则跳过
        if url.lower().endswith('.gif'):
            continue
        url_list.append(url)

    return url_list


# 远程下载指定URL地址的图片，并保存到临时目录中
def download_image(url, dest):
    try:
        response = requests.get(url)  # 获取图片的响应
        # 将图片以二进制方式保存到指定文件中
        with open(file=dest, mode='wb') as file:
            file.write(response.content)
            return True
    except Exception as e:
        print(e)
        return False


def convert_image_to_webp(folder_, filename_):
    # 打开 JPG 图片
    img = Image.open(folder_ + filename_)
    new_filename = filename_.split('.')[0] + '.webp'
    # 转换并保存为 WebP 格式
    img.save(folder_ + new_filename, "WEBP")


def get_system_font_path():
    import platform
    # 根据操作系统选择字体路径
    if platform.system() == "Windows":
        font_path = "C:/Windows/Fonts/msyh.ttc"  # 微软雅黑路径
    elif platform.system() == "Darwin":  # macOS
        font_path = "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"  # 微软雅黑路径
    else:  # Linux (Ubuntu)
        font_path = "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"  # 文泉驿微米黑路径
    return font_path


def generate_random_color():
    """生成一个随机的鲜艳颜色"""
    return random.randint(100, 255), random.randint(100, 255), random.randint(100, 255)

def generate_gradient_background(width, height):
    """生成一个更加鲜艳的背景渐变"""
    # 随机选择两种颜色作为背景渐变的起始和终止颜色
    start_color = generate_random_color()
    end_color = generate_random_color()

    gradient = Image.new('RGB', (width, height), start_color)
    for y in range(height):
        blend_factor = y / height
        r = int(start_color[0] * (1 - blend_factor) + end_color[0] * blend_factor)
        g = int(start_color[1] * (1 - blend_factor) + end_color[1] * blend_factor)
        b = int(start_color[2] * (1 - blend_factor) + end_color[2] * blend_factor)
        for x in range(width):
            gradient.putpixel((x, y), (r, g, b))
    return gradient

def create_thumb_png():
    # 从文件加载 YAML 内容
    yaml_file_path = '../configs/article_type_config.yaml'

    # 确保文件存在
    if not os.path.exists(yaml_file_path):
        raise FileNotFoundError(f"配置文件 {yaml_file_path} 不存在!")

    # 读取并解析 YAML 文件
    with open(yaml_file_path, 'r', encoding='utf-8') as file:
        yaml_content = file.read()

    # 解析 YAML 内容
    article_types = yaml.safe_load(yaml_content)["ARTICLE_TYPES"]

    # 输出查看
    print(article_types)

    # Directory to save images
    output_dir = "../resource/thumb/"
    os.makedirs(output_dir, exist_ok=True)

    # Font configuration
    font_path = get_system_font_path()
    image_size = (226, 136)  # (width, height)

    # Generate images
    for key, value in article_types.items():
        image = generate_gradient_background(*image_size)  # Create a gradient background
        draw = ImageDraw.Draw(image)

        # Dynamically adjust font size and text wrapping
        font_size = 60  # Initial font size
        font = ImageFont.truetype(font_path, font_size)

        # Check text width and adjust font size to fit
        text_bbox = draw.textbbox((0, 0), value, font=font)
        while text_bbox[2] - text_bbox[0] > image_size[0] * 0.9 or text_bbox[3] - text_bbox[1] > image_size[1] * 0.9:
            font_size -= 2
            font = ImageFont.truetype(font_path, font_size)
            text_bbox = draw.textbbox((0, 0), value, font=font)

        # Center the text
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        position = ((image_size[0] - text_width) // 2, (image_size[1] - text_height) // 2)

        # Draw text with shadow effect for better visibility
        shadow_offset = 2
        shadow_color = (50, 50, 50)  # Shadow color (dark gray)
        draw.text((position[0] + shadow_offset, position[1] + shadow_offset), value, fill=shadow_color, font=font)

        # Text color (randomly generated fresh colors)
        text_color = generate_random_color()
        draw.text(position, value, fill=text_color, font=font)

        # Optionally, add a border around the image
        border_thickness = 10
        draw.rectangle([0, 0, image_size[0] - 1, image_size[1] - 1], outline=(0, 0, 0), width=border_thickness)

        # Save image
        filename = os.path.join(output_dir, f"{key}.png")
        image.save(filename)

    print(f"Images saved to {output_dir}")


def generate_elegant_gradient(size):
    """生成优雅地渐变背景"""
    gradient = Image.new('RGBA', size)
    draw = ImageDraw.Draw(gradient)
    
    # 生成柔和的渐变色
    color1 = generate_pastel_color()
    color2 = generate_complementary_color(color1)
    
    for y in range(size[1]):
        r = int(color1[0] + (color2[0] - color1[0]) * y / size[1])
        g = int(color1[1] + (color2[1] - color1[1]) * y / size[1])
        b = int(color1[2] + (color2[2] - color1[2]) * y / size[1])
        draw.line([(0, y), (size[0], y)], fill=(r, g, b, 255))
    
    return gradient

def generate_pastel_color():
    """生成柔和的粉彩色"""
    base = random.randint(0, 360)  # HSV色相
    saturation = random.randint(25, 40)  # 较低的饱和度
    value = random.randint(90, 100)  # 较高的明度
    
    # 将HSV转换为RGB
    h = base / 360
    s = saturation / 100
    v = value / 100
    
    if s == 0:
        return (v, v, v)
    
    i = int(h * 6)
    f = (h * 6) - i
    p = v * (1 - s)
    q = v * (1 - s * f)
    t = v * (1 - s * (1 - f))
    
    i = i % 6
    if i == 0:
        rgb = (v, t, p)
    elif i == 1:
        rgb = (q, v, p)
    elif i == 2:
        rgb = (p, v, t)
    elif i == 3:
        rgb = (p, q, v)
    elif i == 4:
        rgb = (t, p, v)
    else:
        rgb = (v, p, q)
    
    return tuple(int(x * 255) for x in rgb)

def generate_complementary_color(color):
    """生成互补色"""
    return (255 - color[0], 255 - color[1], 255 - color[2])

def add_pattern_overlay(draw, size):
    """添加图案装饰"""
    # 添加细小的点状装饰
    for _ in range(50):
        x = random.randint(0, size[0])
        y = random.randint(0, size[1])
        radius = random.randint(1, 3)
        color = (255, 255, 255, random.randint(30, 60))  # 半透明白色
        draw.ellipse([x-radius, y-radius, x+radius, y+radius], fill=color)

def calculate_optimal_font_size(draw, text, font_path, image_size):
    """计算最佳字体大小"""
    font_size = 80  # 起始字体大小
    max_width = image_size[0] * 0.85  # 留出15%边距
    max_height = image_size[1] * 0.85
    
    while font_size > 20:  # 最小字体大小限制
        font = ImageFont.truetype(font_path, font_size)
        text_bbox = draw.textbbox((0, 0), text, font=font)
        if text_bbox[2] - text_bbox[0] <= max_width and text_bbox[3] - text_bbox[1] <= max_height:
            break
        font_size -= 2
    
    return font_size

def add_text_decorations(draw, text, position, font, image_size):
    """添加文本装饰效果"""
    # 添加文字光晕效果
    glow_color = (255, 255, 255, 30)
    for offset in range(3, 8, 2):
        for angle in range(0, 360, 45):
            x = position[0] + offset * math.cos(math.radians(angle))
            y = position[1] + offset * math.sin(math.radians(angle))
            draw.text((x, y), text, font=font, fill=glow_color)

def draw_beautiful_text(draw, text, position, font):
    """绘制美化的文本"""
    # 绘制文字阴影
    shadow_color = (0, 0, 0, 100)
    offset = 2
    draw.text((position[0] + offset, position[1] + offset), text, font=font, fill=shadow_color)
    
    # 绘制主文本
    main_color = (255, 255, 255, 255)  # 纯白色
    draw.text(position, text, font=font, fill=main_color)

def add_frame_and_decorations(draw, size):
    """添加边框和装饰"""
    # 添加圆角边框
    border_color = (255, 255, 255, 100)
    border_width = 3
    radius = 15
    
    # 绘制圆角矩形
    draw.rounded_rectangle([border_width, border_width, 
                          size[0]-border_width, size[1]-border_width],
                         radius=radius, outline=border_color, width=border_width)
    
    # 在四角添加装饰
    corner_size = 10
    for x, y in [(0, 0), (0, size[1]), (size[0], 0), (size[0], size[1])]:
        draw.ellipse([x-corner_size, y-corner_size, x+corner_size, y+corner_size],
                    fill=(255, 255, 255, 50))

def create_beautiful_thumb_png():
    """
    创建专业的文章类型缩略图，特点：
    1. 简洁现代的设计风格
    2. 适合白色背景的配色方案
    3. 专业的排版和布局
    4. 清晰的视觉层次
    """
    yaml_file_path = '../configs/article_type_config.yaml'

    if not os.path.exists(yaml_file_path):
        raise FileNotFoundError(f"配置文件 {yaml_file_path} 不存在!")

    with open(yaml_file_path, 'r', encoding='utf-8') as file:
        article_types = yaml.safe_load(file.read())["ARTICLE_TYPES"]

    output_dir = "../resource/thumb/"
    os.makedirs(output_dir, exist_ok=True)

    # 基础配置
    image_size = (280, 160)  # 适中的尺寸
    font_path = get_system_font_path()
    
    # 预定义的专业配色方案
    color_schemes = [
        {
            'bg': (41, 128, 185),     # 专业蓝
            'accent': (52, 152, 219),  # 亮蓝
            'text': (255, 255, 255)    # 白色文字
        },
        {
            'bg': (39, 174, 96),      # 专业绿
            'accent': (46, 204, 113),  # 亮绿
            'text': (255, 255, 255)    # 白色文字
        },
        {
            'bg': (142, 68, 173),     # 优雅紫
            'accent': (155, 89, 182),  # 亮紫
            'text': (255, 255, 255)    # 白色文字
        },
        {
            'bg': (44, 62, 80),       # 深蓝灰
            'accent': (52, 73, 94),    # 亮蓝灰
            'text': (255, 255, 255)    # 白色文字
        }
    ]
    
    for key, value in article_types.items():
        # 为每个类型选择一个固定的配色方案
        color_scheme = color_schemes[hash(key) % len(color_schemes)]
        
        # 创建底图
        image = Image.new('RGB', image_size, color_scheme['bg'])
        draw = ImageDraw.Draw(image)

        # 添加专业风格的装饰
        add_professional_decoration(draw, image_size, color_scheme)

        # 计算最佳字体大小和位置
        font_size, position = calculate_text_position(draw, value, font_path, image_size)
        font = ImageFont.truetype(font_path, font_size)

        # 绘制专业风格文本
        draw_professional_text(draw, value, position, font, color_scheme)

        # 添加边框
        add_professional_frame(draw, image_size, color_scheme)

        # 保存图片
        filename = os.path.join(output_dir, f"{key}.png")
        image.save(filename)

    print(f"专业版缩略图已保存至 {output_dir}")

def calculate_text_position(draw, text, font_path, image_size):
    """计算文本的最佳字体大小和位置，确保完全居中"""
    font_size = 60  # 起始字体大小
    max_width = image_size[0] * 0.75  # 留出25%边距
    max_height = image_size[1] * 0.6  # 留出40%边距
    
    # 计算最佳字体大小
    while font_size > 24:  # 最小字体大小限制
        font = ImageFont.truetype(font_path, font_size)
        # 使用getbbox获取更精确的文本边界
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        if text_width <= max_width and text_height <= max_height:
            break
        font_size -= 2

    # 重新获取最终的文本尺寸
    font = ImageFont.truetype(font_path, font_size)
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    # 计算精确的居中位置
    x = (image_size[0] - text_width) // 2 - bbox[0]  # 减去bbox[0]来补偿文本的边界偏移
    y = (image_size[1] - text_height) // 2 - bbox[1]  # 减去bbox[1]来补偿文本的边界偏移
    
    return font_size, (x, y)

def add_professional_decoration(draw, size, color_scheme):
    """添加专业风格的装饰"""
    # 添加右上角的装饰条
    accent_color = color_scheme['accent']
    stripe_width = 40
    points = [
        (size[0] - stripe_width, 0),
        (size[0], 0),
        (size[0], stripe_width)
    ]
    draw.polygon(points, fill=accent_color)

    # 添加左下角的装饰点
    dot_size = 6
    dot_margin = 15
    dot_spacing = 12
    for i in range(3):
        x = dot_margin + (i * dot_spacing)
        y = size[1] - dot_margin
        draw.ellipse([x-dot_size//2, y-dot_size//2, x+dot_size//2, y+dot_size//2],
                    fill=accent_color)

def calculate_professional_font_size(draw, text, font_path, image_size):
    """计算专业排版的字体大小"""
    font_size = 60  # 起始字体大小
    max_width = image_size[0] * 0.75  # 留出25%边距
    max_height = image_size[1] * 0.6  # 留出40%边距
    
    while font_size > 24:  # 最小字体大小限制
        font = ImageFont.truetype(font_path, font_size)
        text_bbox = draw.textbbox((0, 0), text, font=font)
        if text_bbox[2] - text_bbox[0] <= max_width and text_bbox[3] - text_bbox[1] <= max_height:
            break
        font_size -= 2
    
    return font_size

def draw_professional_text(draw, text, position, font, color_scheme):
    """绘制专业风格的文本"""
    # 绘制主文本
    text_color = color_scheme['text']
    draw.text(position, text, font=font, fill=text_color)

def add_professional_frame(draw, size, color_scheme):
    """添加专业风格的边框"""
    # 添加底部强调线
    accent_color = color_scheme['accent']
    line_thickness = 3
    line_width = size[0] * 0.3  # 线长为图片宽度的30%
    start_x = (size[0] - line_width) // 2
    y = size[1] - 20  # 距离底部20像素
    
    draw.line([(start_x, y), (start_x + line_width, y)],
             fill=accent_color, width=line_thickness)

if __name__ == '__main__':
    # read_config()
    # folder = '/Users/yunjinqi/Downloads/woniunote/woniunote/resource/img/'
    # filename = "noperm.jpg"
    # convert_image_to_webp(folder, filename)
    create_beautiful_thumb_png()
