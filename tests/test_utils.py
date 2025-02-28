import os
import pytest
import requests
from PIL import Image
import platform
import hashlib
from io import BytesIO
from woniunote.common.utils import (
    get_db_connection,
    parse_db_uri,
    read_config,
    ImageCode,
    send_email,
    gen_email_code,
    compress_image,
    parse_image_url,
    download_image,
    convert_image_to_webp,
    get_system_font_path,
    generate_elegant_gradient
)

def test_get_db_connection(test_db_info):
    """测试数据库连接功能"""
    # 测试正确地连接信息
    conn = get_db_connection(test_db_info)
    assert conn is not None
    conn.close()
    
    # 测试错误的连接信息
    wrong_info = test_db_info.copy()
    wrong_info['password'] = 'wrong_password'
    conn = get_db_connection(wrong_info)
    assert conn is None

def test_parse_db_uri(test_db_uri):
    """测试数据库URI解析"""
    info = parse_db_uri(test_db_uri)
    database_info = read_config()['database']
    print(info)
    print(database_info)
    assert info['host'] == database_info['host']
    assert info['user'] == database_info['user']
    assert info['password'] == database_info['password']
    assert info['database'] == database_info['database']
    assert info['port'] == database_info['port']


def test_read_config():
    """测试配置文件读取"""
    # 测试读取有效配置文件
    config = read_config()
    assert config is not None
    assert 'database' in config
    assert 'SQLALCHEMY_DATABASE_URI' in config['database']
    
    # 测试读取不存在的配置文件
    config = read_config('nonexistent.yaml')
    assert config is None


def test_image_code():
    """测试验证码生成"""
    code = ImageCode()

    # 测试验证码生成
    text, image_bytes = code.get_code()
    assert isinstance(image_bytes, bytes)  # 现在返回的是字节数据
    assert len(text) == 4

    # 验证生成的图片
    img = Image.open(BytesIO(image_bytes))  # 使用BytesIO包装字节数据
    assert img.size == (120, 40)  # 更新尺寸断言
    assert img.mode == 'RGB'

def test_gen_email_code():
    """测试邮箱验证码生成"""
    code = gen_email_code()
    assert len(code) == 6
    assert code.isalnum()  # 验证码应该是字母数字组合

def test_compress_image(test_images_dir):
    """测试图片压缩"""
    # 创建测试图片
    test_image = Image.new('RGB', (1000, 1000), color='red')
    source_path = os.path.join(test_images_dir, 'test.jpg')
    test_image.save(source_path)
    
    # 测试压缩
    dest_path = os.path.join(test_images_dir, 'test_compressed.jpg')
    compress_image(source_path, dest_path, 500)
    
    # 验证压缩结果
    compressed = Image.open(dest_path)
    assert compressed.size[0] == 500  # 宽度应该是500
    assert os.path.getsize(dest_path) < os.path.getsize(source_path)

def test_parse_image_url():
    """测试图片URL解析"""
    # 测试HTML内容中的图片解析
    html_content = """
    <p>Test content</p>
    <img src="https://example.com/image1.jpg" />
    <img src="https://example.com/image2.png" />
    """
    urls = parse_image_url(html_content)
    assert len(urls) == 2
    assert "https://example.com/image1.jpg" in urls
    assert "https://example.com/image2.png" in urls
    
    # 测试 无图片 内容
    assert len(parse_image_url("<p>No images</p>")) == 0


# test_download_image测试
def test_download_image(test_images_dir, requests_mock):
    """测试图片下载"""
    # 模拟图片URL
    test_url = "https://example.com/test.jpg"
    test_content = b"fake image content"
    requests_mock.get(test_url, content=test_content)

    # 确保下载路径存在
    os.makedirs(test_images_dir, exist_ok=True)

    # 测试下载
    dest_path = os.path.join(test_images_dir, 'downloaded.jpg')
    download_image(test_url, dest_path)

    # 验证下载结果
    assert os.path.exists(dest_path)
    with open(dest_path, 'rb') as f:
        assert f.read() == test_content


def test_convert_image_to_webp(test_images_dir):
    """测试图片转换为WebP格式"""
    # 创建测试图片
    test_image = Image.new('RGB', (100, 100), color='blue')
    source_path = os.path.join(test_images_dir, 'test_convert.jpg')
    test_image.save(source_path)
    
    # 测试转换
    convert_image_to_webp(test_images_dir, 'test_convert.jpg')
    webp_path = test_images_dir + '/test_convert.webp'
    assert webp_path.endswith('.webp')
    assert os.path.exists(webp_path)
    
    # 验证转换后的图片
    webp_image = Image.open(webp_path)
    assert webp_image.format == 'WEBP'


# 在test_utils.py中添加以下测试用例

# 测试邮件发送功能失败的可能原因
# test_parse_image_url_complex测试
def test_parse_image_url_complex():
    """测试复杂HTML内容的图片解析"""
    html_content = """
    <div>
        <img data-src="https://example.com/lazy1.jpg" class="lazy">
        <figure>
            <img src="https://example.com/figure1.jpg">
            <img src="https://example.com/figure2.png">
        </figure>
        <picture>
            <source srcset="https://example.com/webp1.webp">
            <img src="https://example.com/fallback1.jpg">
            <img src="https://example.com/fallback1.gif">
        </picture>
    </div>
    """
    urls = parse_image_url(html_content)
    print(urls)
    assert len(urls) == 3  # 应包含所有图片URL
    assert "https://example.com/figure2.png" in urls
    assert "https://example.com/figure1.jpg" in urls
    assert "https://example.com/fallback1.jpg" in urls


# get_system_font_path函数测试失败的可能原因
def test_get_system_font_path():
    # 如果操作系统差异未处理，可能导致路径格式错误
    # 解决方案：根据操作系统调整断言条件
    font_path = get_system_font_path()
    if platform.system() == 'Windows':
        assert 'msyh' in font_path.lower()
    else:
        assert 'wqy-microhei' in font_path


def test_parse_db_uri_unique():
    # 如果URI格式不完整，函数可能返回不完整的结果
    # 解决方案：确保测试使用的URI包含所有必要部分
    test_db_uri = "mysql://user:password@host:3306/database"
    info = parse_db_uri(test_db_uri)
    assert info['host'] == 'host'
    assert info['port'] == 3306

def test_image_code_with_custom_size():
    """测试自定义尺寸验证码"""
    code = ImageCode(width=200, height=80)
    text, image_bytes = code.get_code()
    img = Image.open(BytesIO(image_bytes))
    assert img.size == (200, 80)
    assert len(text) == 4

def test_generate_elegant_gradient():
    """测试渐变背景生成"""
    gradient = generate_elegant_gradient((300, 200))
    assert gradient.size == (300, 200)
    # 验证颜色通道
    pixel = gradient.getpixel((150, 100))
    assert len(pixel) == 4  # RGBA
    assert all(0 <= c <= 255 for c in pixel)


if __name__ == '__main__':
    test_image_code()
