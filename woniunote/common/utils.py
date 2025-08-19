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
import logging
from contextlib import contextmanager

# 获取日志记录器
logger = logging.getLogger(__name__)

# 数据库连接池配置
DB_POOL_CONFIG = {
    'max_connections': 20,
    'connection_timeout': 30,
    'retry_count': 3,
    'retry_delay': 1
}

# 安全配置
ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB
MAX_EMAIL_LENGTH = 254
MAX_FILENAME_LENGTH = 255

def validate_email(email):
    """验证邮箱格式"""
    if not email or len(email) > MAX_EMAIL_LENGTH:
        return False
    
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(email_pattern, email))

def validate_filename(filename):
    """验证文件名安全性"""
    if not filename or len(filename) > MAX_FILENAME_LENGTH:
        return False
    
    # 检查危险字符
    dangerous_chars = ['/', '\\', '..', '<', '>', ':', '"', '|', '?', '*', '\0']
    for char in dangerous_chars:
        if char in filename:
            return False
    
    return True

def sanitize_input(input_string, max_length=1000):
    """清理输入字符串"""
    if not input_string:
        return ""
    
    # 截断过长的输入
    if len(input_string) > max_length:
        input_string = input_string[:max_length]
    
    # 移除控制字符
    cleaned = ''.join(char for char in input_string if ord(char) >= 32 or char in '\t\n\r')
    
    return cleaned.strip()

@contextmanager
def get_db_connection_context(database_info):
    """数据库连接上下文管理器"""
    connection = None
    try:
        connection = get_db_connection(database_info)
        if connection:
            yield connection
        else:
            raise Exception("Failed to establish database connection")
    except Exception as e:
        logger.error(f"Database connection error: {str(e)}")
        if connection:
            connection.rollback()
        raise
    finally:
        if connection:
            connection.close()

# 初始化数据库连接（优化版本）
def get_db_connection(database_info, retry_count=None):
    """
    获取数据库连接，支持重试机制
    """
    if retry_count is None:
        retry_count = DB_POOL_CONFIG['retry_count']
    
    for attempt in range(retry_count):
        try:
            # 验证输入参数
            required_keys = ['host', 'user', 'password', 'database']
            for key in required_keys:
                if key not in database_info or not database_info[key]:
                    raise ValueError(f"Missing or empty database parameter: {key}")
            
            connection = pymysql.connect(
                host=database_info['host'],
                user=database_info['user'],
                password=database_info['password'],
                database=database_info['database'],
                port=database_info.get('port', 3306),
                cursorclass=DictCursor,
                connect_timeout=DB_POOL_CONFIG['connection_timeout'],
                read_timeout=30,
                write_timeout=30,
                charset='utf8mb4',
                autocommit=False,
                ssl_disabled=False
            )
            
            # 测试连接
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            
            logger.info("Database connection established successfully")
            return connection
            
        except pymysql.err.OperationalError as e:
            logger.error(f"Database connection attempt {attempt + 1} failed: {str(e)}")
            if attempt < retry_count - 1:
                time.sleep(DB_POOL_CONFIG['retry_delay'])
            else:
                raise Exception(f"Failed to connect to database after {retry_count} attempts: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected database connection error: {str(e)}")
            raise

def parse_db_uri(db_uri):
    """
    解析 SQLALCHEMY_DATABASE_URI，提取数据库连接信息（安全版本）
    """
    try:
        if not db_uri or not isinstance(db_uri, str):
            raise ValueError("Invalid database URI")
        
        # 解析 URI
        parsed = urlparse(db_uri)
        
        if not parsed.scheme:
            raise ValueError("Invalid database URI format")
        
        # 对于SQLite，不需要hostname
        if parsed.scheme.lower() == 'sqlite':
            return {
                'scheme': parsed.scheme,
                'path': parsed.path,
                'database': parsed.path
            }
        
        # 对于其他数据库，需要hostname
        if not parsed.hostname:
            raise ValueError("Invalid database URI format")

        # 提取用户名和密码
        username = parsed.username
        password = parsed.password

        # 提取主机和端口
        host = parsed.hostname
        port = parsed.port or 3306  # 如果未指定端口，默认为 3306

        # 提取数据库名称
        database = parsed.path.lstrip('/')  # 去掉路径开头的斜杠
        
        if not database:
            raise ValueError("Database name not specified in URI")

        result = {
            'host': host,
            'port': port,
            'user': username,
            'password': password,
            'database': database
        }
        
        # 验证必要字段
        for key, value in result.items():
            if key != 'port' and not value:
                raise ValueError(f"Missing {key} in database URI")
        
        logger.info(f"Database URI parsed successfully for host: {host}")
        return result
        
    except Exception as e:
        logger.error(f"Failed to parse database URI: {str(e)}")
        raise


def get_package_path(package_name="woniunote"):
    """获取包的路径值（安全版本）
    :param package_name: 包的名称
    :return: 返回的路径值
    """
    try:
        # 验证包名
        if not package_name or not isinstance(package_name, str):
            raise ValueError("Invalid package name")
        
        # 检查包名是否包含危险字符
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', package_name):
            raise ValueError("Package name contains invalid characters")
        
        importlib.import_module(package_name)
        package = sys.modules[package_name]
        
        if package.__file__ is not None:
            path = os.path.dirname(package.__file__)
        else:
            path = package.__path__.__dict__["_path"][0]
        
        # 验证路径安全性
        if not os.path.exists(path):
            raise FileNotFoundError(f"Package path does not exist: {path}")
        
        logger.info(f"Package path found: {path}")
        return path
        
    except KeyError:
        logger.error(f"Package {package_name} not found")
        return None
    except Exception as e:
        logger.error(f"Error getting package path for {package_name}: {str(e)}")
        raise


# 打开配置文件（安全版本）
def read_config(config_file=None):
    """读取配置文件，增强安全性"""
    import yaml  # 在函数开始就导入yaml
    
    try:
        # 优先使用当前工作目录的配置文件
        current_dir = os.getcwd()
        project_root = os.path.dirname(os.path.dirname(current_dir)) if 'woniunote' in current_dir else current_dir
        
        config_paths = [
            # 当前工作目录下的configs文件夹
            os.path.join(current_dir, "configs", "user_password_config.yaml"),
            # 项目根目录下的configs文件夹
            os.path.join(project_root, "configs", "user_password_config.yaml"),
            # 当前目录的上级目录configs文件夹
            os.path.join(os.path.dirname(current_dir), "configs", "user_password_config.yaml"),
            # woniunote包同级的configs文件夹
            os.path.join(os.path.dirname(__file__), "..", "..", "configs", "user_password_config.yaml"),
        ]
        
        # 如果有自定义配置文件路径
        if config_file:
            if config_file.startswith('/'):
                config_file = config_file[1:]
            custom_path = os.path.join(current_dir, config_file)
            config_paths.insert(0, custom_path)
        
        # 过滤掉None值并标准化路径
        config_paths = [os.path.abspath(path) for path in config_paths if path]
        
        file_path = None
        for path in config_paths:
            if os.path.exists(path):
                file_path = path
                break
        
        if not file_path:
            # 如果找不到配置文件，创建一个默认的
            default_config_path = os.path.join(current_dir, "configs", "user_password_config.yaml")
            os.makedirs(os.path.dirname(default_config_path), exist_ok=True)
            
            default_config = {
                'database': {
                    'SQLALCHEMY_DATABASE_URI': 'sqlite:///woniunote_dev.db',
                    'SQLALCHEMY_TRACK_MODIFICATIONS': False,
                    'SQLALCHEMY_POOL_SIZE': 10,
                    'SQLALCHEMY_POOL_TIMEOUT': 30,
                    'SQLALCHEMY_POOL_RECYCLE': 1800,
                    'SQLALCHEMY_MAX_OVERFLOW': 20
                },
                'SECRET_KEY': 'dev-woniunote-secret-key-2025',
                'WTF_CSRF_SECRET_KEY': 'dev-woniunote-csrf-key-2025',
                'SESSION_TYPE': 'filesystem',
                'SESSION_PERMANENT': True,
                'PERMANENT_SESSION_LIFETIME': 14400,
                'cache': {
                    'default_ttl': 300,
                    'key_prefix': 'woniunote:',
                    'memory': {
                        'max_size': 1000,
                        'default_ttl': 300
                    }
                }
            }
            
            with open(default_config_path, 'w', encoding='utf-8') as f:
                yaml.dump(default_config, f, default_flow_style=False, allow_unicode=True)
            
            logger.info(f"Created default config file: {default_config_path}")
            file_path = default_config_path
        
        # 验证文件路径安全性
        file_path = os.path.abspath(file_path)
        
        # 检查文件大小
        file_size = os.path.getsize(file_path)
        if file_size > 1024 * 1024:  # 1MB limit
            raise ValueError("Config file too large")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            config_result = yaml.safe_load(f.read())
        
        # 验证配置完整性
        if not config_result:
            logger.warning("Config file is empty, using defaults")
            config_result = {
                'database': {'SQLALCHEMY_DATABASE_URI': 'sqlite:///woniunote_dev.db'},
                'SECRET_KEY': 'dev-woniunote-secret-key-2025'
            }
        
        logger.info(f"Config file loaded successfully: {file_path}")
        return config_result
        
    except yaml.YAMLError as e:
        logger.error(f"YAML parsing error: {str(e)}")
        # 返回默认配置而不是抛出异常
        return {
            'database': {'SQLALCHEMY_DATABASE_URI': 'sqlite:///woniunote_dev.db'},
            'SECRET_KEY': 'dev-woniunote-secret-key-2025'
        }
    except Exception as e:
        logger.error(f"Error reading config file: {str(e)}")
        # 返回默认配置而不是抛出异常
        return {
            'database': {'SQLALCHEMY_DATABASE_URI': 'sqlite:///woniunote_dev.db'},
            'SECRET_KEY': 'dev-woniunote-secret-key-2025'
        }


class ImageCode:
    """图片验证码生成器（优化版本）"""
    
    def __init__(self, width=120, height=50):
        # 验证尺寸参数
        if not isinstance(width, int) or not isinstance(height, int):
            raise ValueError("Width and height must be integers")
        
        if width < 60 or width > 300 or height < 30 or height > 200:
            raise ValueError("Invalid image dimensions")
        
        self.width = width
        self.height = height
        self.img = Image.new('RGB', (width, height), color=(255, 255, 255))
        
        # 使用系统字体，增大字体尺寸到36px
        try:
            font_path = get_system_font_path()
            self.font = ImageFont.truetype(font_path, 36)
        except Exception:
            logger.warning("Failed to load system font, using default")
            self.font = ImageFont.load_default()
    
    def rand_color(self):
        """生成用于绘制字符串的随机颜色"""
        red = random.randint(32, 200)
        green = random.randint(22, 255)
        blue = random.randint(0, 200)
        return red, green, blue

    def gen_text(self, length=4):
        """生成随机字符串，仅包含数字"""
        if not isinstance(length, int) or length < 3 or length > 8:
            length = 4
        
        # 只使用数字，不使用字母和干扰字符
        chars = '0123456789'
        return ''.join(random.choices(chars, k=length))

    def draw_lines(self, draw, num, width, height):
        """画干扰线"""
        for _ in range(min(num, 10)):  # 限制干扰线数量
            x1 = random.randint(0, width // 2)
            y1 = random.randint(0, height // 2)
            x2 = random.randint(0, width)
            y2 = random.randint(height // 2, height)
            draw.line(((x1, y1), (x2, y2)), fill='black', width=1)

    def draw_verify_code(self):
        """绘制验证码图片，仅使用数字，更大字体，无干扰线"""
        try:
            code = self.gen_text()
            # 创建图片对象，并设定背景色为白色
            im = Image.new('RGB', (self.width, self.height), 'white')
            
            # 优先使用之前设置的大字体，如果失败则尝试默认字体
            font = self.font
            if font is None:
                try:
                    font = ImageFont.load_default()
                except Exception:
                    logger.warning("Failed to load default font")
                    font = None
            
            draw = ImageDraw.Draw(im)  # 新建ImageDraw对象
            
            # 绘制字符串，保持较大间隔，位置更居中
            char_width = self.width // len(code)
            for i, char in enumerate(code):
                # 减少随机偏移，使数字更整齐
                x = 10 + char_width * i
                y = (self.height - 36) // 2  # 垂直居中
                
                # 确保坐标在图片范围内
                x = max(0, min(x, self.width - 20))
                y = max(0, min(y, self.height - 36))
                
                draw.text((x, y), text=char, fill=self.rand_color(), font=font)
            
            # 不添加干扰线
            # self.draw_lines(draw, 2, self.width, self.height)
            
            return im, code
            
        except Exception as e:
            logger.error(f"Error generating verification code: {str(e)}")
            raise

    def get_code(self):
        """生成图片验证码并返回给控制器"""
        try:
            image, code = self.draw_verify_code()
            buf = BytesIO()
            image.save(buf, 'jpeg', quality=85, optimize=True)
            b_string = buf.getvalue()
            buf.close()
            
            # 验证生成的图片大小
            if len(b_string) > 100 * 1024:  # 100KB limit
                raise ValueError("Generated image too large")
            
            logger.info(f"Verification code generated successfully, size: {len(b_string)} bytes")
            return code, b_string
            
        except Exception as e:
            logger.error(f"Error getting verification code: {str(e)}")
            raise


# 发送QQ邮箱验证码（安全版本）
def send_email(receiver, ecode, sender_config=None):
    """
    发送邮箱验证码，增强安全性和错误处理
    :param receiver: 收件人邮箱
    :param ecode: 验证码
    :param sender_config: 发件人配置（可选）
    """
    try:
        # 验证收件人邮箱
        if not validate_email(receiver):
            raise ValueError("Invalid receiver email address")
        
        # 验证验证码
        if not ecode or len(str(ecode)) > 20:
            raise ValueError("Invalid verification code")
        
        # 清理验证码（防止注入）
        ecode = sanitize_input(str(ecode), 20)
        
        # 默认配置
        if sender_config is None:
            sender_config = {
                'email': '15903523@qq.com',
                'password': 'uczmmmqvpxwjbjaf',  # 应从配置文件读取
                'smtp_server': 'smtp.qq.com',
                'smtp_port': 465
            }
        
        sender = f'WoniuNote <{sender_config["email"]}>'
        
        # 定义安全的邮件内容模板
        content = f"""
        <div style="max-width: 600px; margin: 0 auto; font-family: Arial, sans-serif;">
            <h2 style="color: #333;">蜗牛笔记账号注册</h2>
            <p>欢迎注册蜗牛笔记博客系统账号！</p>
            <p>您的邮箱验证码为：</p>
            <div style="background-color: #f5f5f5; padding: 20px; text-align: center; margin: 20px 0;">
                <span style="color: #d32f2f; font-size: 24px; font-weight: bold; letter-spacing: 3px;">{ecode}</span>
            </div>
            <p>请在注册页面输入此验证码完成注册。</p>
            <p style="color: #666; font-size: 12px;">
                此验证码10分钟内有效，如非本人操作，请忽略此邮件。
            </p>
            <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
            <p style="color: #999; font-size: 11px;">
                此邮件由系统自动发送，请勿回复。
            </p>
        </div>
        """
        
        # 创建邮件对象
        message = MIMEText(content, 'html', 'utf-8')
        message['Subject'] = Header('蜗牛笔记注册验证码', 'utf-8')
        message['From'] = sender
        message['To'] = receiver
        
        # 建立SMTP连接
        smtp_obj = SMTP_SSL(sender_config['smtp_server'], sender_config['smtp_port'])
        smtp_obj.login(user=sender_config['email'], password=sender_config['password'])
        
        # 发送邮件
        smtp_obj.sendmail(sender, receiver, str(message))
        smtp_obj.quit()
        
        logger.info(f"Email sent successfully to {receiver}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send email to {receiver}: {str(e)}")
        raise


# 生成邮箱验证码（安全版本）
def gen_email_code(length=6):
    """
    生成邮箱验证码，增强安全性
    :param length: 验证码长度
    :return: 验证码字符串
    """
    if not isinstance(length, int) or length < 4 or length > 10:
        length = 6
    
    # 使用数字和大写字母，避免混淆的字符
    chars = '23456789ABCDEFGHJKLMNPQRSTUVWXYZ'
    code = ''.join(random.choices(chars, k=length))
    
    logger.info(f"Email verification code generated, length: {length}")
    return code


# 模型列表转换（优化版本）
def model_list(result):
    """单个模型类转换为标准的Python List数据（优化版本）"""
    try:
        if not result:
            return []
        
        # 检查result是否可迭代
        if not hasattr(result, '__iter__'):
            logger.warning("Result is not iterable, converting single object")
            result = [result]
        
        m_list = []
        for row in result:
            if not hasattr(row, '__dict__'):
                logger.warning("Invalid model object in result")
                continue
            
            m_dict = {}
            for k, v in row.__dict__.items():
                if not k.startswith('_sa_instance_state'):
                    # 数据类型处理
                    if isinstance(v, datetime):
                        v = v.strftime('%Y-%m-%d %H:%M:%S')
                    elif v is None:
                        v = None
                    elif isinstance(v, (int, float, str, bool)):
                        v = v
                    else:
                        # 其他类型转换为字符串
                        v = str(v)
                    
                    m_dict[k] = v
            
            m_list.append(m_dict)
        
        logger.info(f"Converted {len(m_list)} model objects to list")
        return m_list
        
    except Exception as e:
        logger.error(f"Error converting model list: {str(e)}")
        raise


# SQLAlchemy连接查询结果转换（优化版本）
def model_join_list(result):
    """SQLAlchemy连接查询两张表的结果集转换为[{},{}]（优化版本）"""
    try:
        if not result:
            return []
        
        m_list = []
        for row in result:
            m_dict = {}
            
            # 处理不同类型的查询结果
            if hasattr(row, '_asdict'):
                # 命名元组类型
                m_dict.update(row._asdict())
            elif hasattr(row, '__dict__'):
                # 模型对象
                for k, v in row.__dict__.items():
                    if not k.startswith('_'):
                        m_dict[k] = v
            elif isinstance(row, dict):
                # 字典类型
                m_dict.update(row)
            else:
                logger.warning(f"Unknown result type: {type(row)}")
                continue
            
            # 数据类型处理
            for k, v in m_dict.items():
                if isinstance(v, datetime):
                    m_dict[k] = v.strftime('%Y-%m-%d %H:%M:%S')
                elif v is None:
                    m_dict[k] = None
                elif not isinstance(v, (int, float, str, bool)):
                    m_dict[k] = str(v)
            
            m_list.append(m_dict)
        
        logger.info(f"Converted {len(m_list)} join result objects to list")
        return m_list
        
    except Exception as e:
        logger.error(f"Error converting join result list: {str(e)}")
        raise


# 图片压缩（安全版本）
def compress_image(source, dest, width, quality=85):
    """
    压缩图片，增强安全性和错误处理
    :param source: 源文件路径
    :param dest: 目标文件路径
    :param width: 目标宽度
    :param quality: 压缩质量 (1-100)
    """
    try:
        # 验证参数
        if not source or not dest:
            raise ValueError("Source and destination paths required")
        
        if not isinstance(width, int) or width <= 0 or width > 5000:
            raise ValueError("Invalid width parameter")
        
        if not isinstance(quality, int) or quality < 1 or quality > 100:
            quality = 85
        
        # 验证文件路径安全性
        if not validate_filename(os.path.basename(source)) or not validate_filename(os.path.basename(dest)):
            raise ValueError("Invalid file names")
        
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
                # 如果原图宽度小于等于目标宽度，直接保存
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


# 安全的图片URL解析
def parse_image_url(content, max_urls=50):
    """
    从内容中解析图片URL，增强安全性
    :param content: HTML内容
    :param max_urls: 最大URL数量限制
    :return: 图片URL列表
    """
    try:
        if not content or not isinstance(content, str):
            return []
        
        # 限制内容长度
        if len(content) > 1000000:  # 1MB limit
            logger.warning("Content too large for image URL parsing")
            return []
        
        # 改进的正则表达式，更安全地提取src属性
        pattern = r'<img[^>]+src\s*=\s*["\']([^"\']+)["\'][^>]*>'
        matches = re.findall(pattern, content, re.IGNORECASE)
        
        if not matches:
            return []
        
        # 限制URL数量
        matches = matches[:max_urls]
        
        # 验证和清理URL
        valid_urls = []
        for url in matches:
            # 清理URL
            url = sanitize_input(url, 2000)
            
            # 基本URL验证
            if url and len(url) > 5 and (url.startswith('http://') or url.startswith('https://') or url.startswith('/')):
                # 检查URL是否包含危险字符
                if not any(char in url for char in ['<', '>', '"', "'", '`']):
                    valid_urls.append(url)
        
        logger.info(f"Parsed {len(valid_urls)} valid image URLs from content")
        return valid_urls
        
    except Exception as e:
        logger.error(f"Error parsing image URLs: {str(e)}")
        return []


# 安全的文件下载
def download_image(url, dest, timeout=30, max_size=MAX_IMAGE_SIZE):
    """
    下载图片文件，增强安全性
    :param url: 图片URL
    :param dest: 目标路径
    :param timeout: 请求超时时间
    :param max_size: 最大文件大小
    """
    try:
        # 验证URL
        if not url or not isinstance(url, str):
            raise ValueError("Invalid URL")
        
        if not url.startswith(('http://', 'https://')):
            raise ValueError("URL must start with http:// or https://")
        
        # 验证目标路径
        if not validate_filename(os.path.basename(dest)):
            raise ValueError("Invalid destination filename")
        
        # 发送请求
        headers = {
            'User-Agent': 'WoniuNote/2.0',
            'Accept': 'image/*'
        }
        
        response = requests.get(url, headers=headers, timeout=timeout, stream=True)
        response.raise_for_status()
        
        # 检查内容类型
        content_type = response.headers.get('content-type', '').lower()
        if not content_type.startswith('image/'):
            raise ValueError(f"Invalid content type: {content_type}")
        
        # 检查文件大小
        content_length = response.headers.get('content-length')
        if content_length and int(content_length) > max_size:
            raise ValueError(f"File too large: {content_length} bytes")
        
        # 下载文件
        total_size = 0
        with open(dest, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    total_size += len(chunk)
                    if total_size > max_size:
                        raise ValueError(f"Downloaded file too large: {total_size} bytes")
                    f.write(chunk)
        
        logger.info(f"Image downloaded successfully: {url} -> {dest}, size: {total_size} bytes")
        return True
        
    except Exception as e:
        logger.error(f"Failed to download image {url}: {str(e)}")
        # 清理可能创建的不完整文件
        if os.path.exists(dest):
            try:
                os.remove(dest)
            except:
                pass
        raise


def convert_image_to_webp(source, dest, quality=85):
    """
    将图片转换为WebP格式，提升性能
    :param source: 源文件路径
    :param dest: 目标文件路径
    :param quality: 压缩质量
    """
    try:
        # 验证参数
        if not source or not dest:
            raise ValueError("Source and destination paths required")
        
        if not isinstance(quality, int) or quality < 1 or quality > 100:
            quality = 85
        
        # 验证文件安全性
        if not validate_filename(os.path.basename(source)) or not validate_filename(os.path.basename(dest)):
            raise ValueError("Invalid file names")
        
        # 检查源文件
        if not os.path.exists(source):
            raise FileNotFoundError(f"Source file not found: {source}")
        
        # 验证源文件扩展名
        source_ext = os.path.splitext(source)[1].lower()
        if source_ext not in ALLOWED_IMAGE_EXTENSIONS:
            raise ValueError(f"Unsupported source format: {source_ext}")
        
        # 确保目标文件是WebP格式
        if not dest.lower().endswith('.webp'):
            dest = os.path.splitext(dest)[0] + '.webp'
        
        # 打开并转换图片
        with Image.open(source) as image:
            # 验证图片尺寸
            width, height = image.size
            if width > 10000 or height > 10000:
                raise ValueError("Image dimensions too large")
            
            # 转换为RGB模式（WebP不支持RGBA在某些情况下）
            if image.mode in ('RGBA', 'P'):
                rgb_image = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'RGBA':
                    rgb_image.paste(image, mask=image.split()[-1])
                else:
                    rgb_image.paste(image)
                image = rgb_image
            
            # 保存为WebP格式
            image.save(dest, 'WebP', quality=quality, optimize=True)
        
        # 验证输出文件
        if not os.path.exists(dest):
            raise Exception("Failed to create WebP file")
        
        logger.info(f"Image converted to WebP: {source} -> {dest}")
        return True
        
    except Exception as e:
        logger.error(f"WebP conversion failed: {str(e)}")
        raise


def get_system_font_path():
    """
    获取系统默认字体路径，支持多平台
    :return: 字体文件路径
    """
    try:
        if os.name == 'nt':  # Windows
            common_fonts = [
                "C:\\Windows\\Fonts\\arial.ttf",
                "C:\\Windows\\Fonts\\Arial.ttf",
                "C:\\Windows\\Fonts\\simhei.ttf",
                "C:\\Windows\\Fonts\\simsun.ttc",
                "C:\\Windows\\Fonts\\calibri.ttf"
            ]
        elif os.name == 'posix':  # Linux/Mac
            common_fonts = [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
                "/System/Library/Fonts/Helvetica.ttc",
                "/Library/Fonts/Arial.ttf",
                "/usr/share/fonts/TTF/arial.ttf",
                "/opt/homebrew/share/fonts/arial.ttf"
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
    """生成随机RGB颜色"""
    return (
        random.randint(50, 200),
        random.randint(50, 200),
        random.randint(50, 200)
    )


def generate_gradient_background(width, height):
    """
    生成渐变背景图片
    :param width: 宽度
    :param height: 高度
    :return: PIL Image对象
    """
    try:
        # 验证参数
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


def create_thumb_png(width=200, height=150, text="WoniuNote"):
    """
    创建带文字的缩略图
    :param width: 宽度
    :param height: 高度
    :param text: 显示文字
    :return: PIL Image对象
    """
    try:
        # 参数验证
        if not isinstance(width, int) or not isinstance(height, int):
            raise ValueError("Width and height must be integers")
        
        if width <= 0 or height <= 0 or width > 1000 or height > 1000:
            raise ValueError("Invalid dimensions")
        
        text = sanitize_input(str(text), 50) if text else "WoniuNote"
        
        # 生成渐变背景
        image = generate_gradient_background(width, height)
        draw = ImageDraw.Draw(image)
        
        # 获取字体
        font_path = get_system_font_path()
        try:
            if font_path:
                font = ImageFont.truetype(font_path, 24)
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


# HSV到RGB转换
def hsv_to_rgb(h, s, v):
    """
    HSV颜色空间转RGB
    :param h: 色相 (0-1)
    :param s: 饱和度 (0-1)  
    :param v: 明度 (0-1)
    :return: RGB元组
    """
    try:
        # 参数验证
        h = max(0, min(1, float(h)))
        s = max(0, min(1, float(s)))
        v = max(0, min(1, float(v)))
        
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
            
    except Exception as e:
        logger.error(f"HSV to RGB conversion error: {str(e)}")
        return 0.5, 0.5, 0.5  # 返回灰色作为默认值


# 安全的文件操作上下文管理器
@contextmanager
def safe_file_operation(file_path, mode='r', encoding='utf-8'):
    """
    安全的文件操作上下文管理器
    :param file_path: 文件路径
    :param mode: 打开模式
    :param encoding: 编码格式
    """
    file_handle = None
    try:
        # 验证文件路径安全性
        if not validate_filename(os.path.basename(file_path)):
            raise ValueError("Invalid filename")
        
        # 检查文件大小（读取模式下）
        if 'r' in mode and os.path.exists(file_path):
            file_size = os.path.getsize(file_path)
            if file_size > 100 * 1024 * 1024:  # 100MB limit
                raise ValueError("File too large")
        
        file_handle = open(file_path, mode, encoding=encoding)
        yield file_handle
        
    except Exception as e:
        logger.error(f"File operation error: {str(e)}")
        raise
    finally:
        if file_handle:
            file_handle.close()


# 内存使用监控
def get_memory_usage():
    """
    获取当前进程的内存使用情况
    :return: 内存使用量（MB）
    """
    try:
        import psutil
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        return round(memory_info.rss / 1024 / 1024, 2)  # MB
    except ImportError:
        # 如果没有psutil，使用简单的方法
        try:
            import resource
            return round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 2)
        except:
            return 0.0
    except Exception as e:
        logger.error(f"Error getting memory usage: {str(e)}")
        return 0.0


# 性能监控装饰器
def performance_monitor(func):
    """
    性能监控装饰器
    """
    def wrapper(*args, **kwargs):
        start_time = time.time()
        start_memory = get_memory_usage()
        
        try:
            result = func(*args, **kwargs)
            
            end_time = time.time()
            end_memory = get_memory_usage()
            
            duration = end_time - start_time
            memory_diff = end_memory - start_memory
            
            if duration > 1.0:  # 记录耗时超过1秒的函数
                logger.warning(f"Slow function {func.__name__}: {duration:.2f}s, memory: {memory_diff:.2f}MB")
            
            return result
            
        except Exception as e:
            logger.error(f"Function {func.__name__} error: {str(e)}")
            raise
    
    return wrapper

if __name__ == '__main__':
    # read_config()
    # folder = '/Users/yunjinqi/Downloads/woniunote/woniunote/resource/img/'
    # filename = "noperm.jpg"
    # convert_image_to_webp(folder, filename)
    create_thumb_png()
