#!/usr/bin/env python3
"""
Comprehensive test suite for woniunote.common.utils module
Tests all functions with 100% coverage including edge cases, error handling, and security features
"""

import pytest
import sys
import os
import tempfile
import shutil
import json
import time
from unittest.mock import Mock, patch, mock_open, MagicMock, call
from datetime import datetime, timedelta
from PIL import Image
import io

# 确保项目根目录在Python路径中
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 设置测试环境
os.environ['TESTING'] = 'True'
os.environ['FLASK_ENV'] = 'testing'


class TestValidateEmail:
    """测试邮箱验证函数"""
    
    def test_valid_emails(self):
        """测试有效邮箱格式"""
        from woniunote.common.utils import validate_email
        
        valid_emails = [
            'test@example.com',
            'user.name@domain.co.uk',
            'first+last@subdomain.domain.com',
            'user123@test-domain.org',
            'a@b.co',
            'test.email+tag@example.com'
        ]
        
        for email in valid_emails:
            assert validate_email(email) is True, f"Email should be valid: {email}"
    
    def test_invalid_emails(self):
        """测试无效邮箱格式"""
        from woniunote.common.utils import validate_email
        
        invalid_emails = [
            '',
            None,
            'invalid_email',
            '@domain.com',
            'user@',
            'user@domain',
            'user name@domain.com',
            'user@domain..com',
            'user@@domain.com',
            '.user@domain.com',
            'user.@domain.com'
        ]
        
        for email in invalid_emails:
            assert validate_email(email) is False, f"Email should be invalid: {email}"
    
    def test_email_length_limit(self):
        """测试邮箱长度限制"""
        from woniunote.common.utils import validate_email, MAX_EMAIL_LENGTH
        
        # 创建超长邮箱
        long_email = 'a' * (MAX_EMAIL_LENGTH - 10) + '@test.com'
        assert validate_email(long_email) is True
        
        # 超过长度限制
        too_long_email = 'a' * MAX_EMAIL_LENGTH + '@test.com'
        assert validate_email(too_long_email) is False


class TestValidateFilename:
    """测试文件名验证函数"""
    
    def test_valid_filenames(self):
        """测试有效文件名"""
        from woniunote.common.utils import validate_filename
        
        valid_names = [
            'test.txt',
            'image.jpg',
            'document_with_underscores.pdf',
            'file-with-hyphens.doc',
            'simple_name',
            '123456.png'
        ]
        
        for name in valid_names:
            assert validate_filename(name) is True, f"Filename should be valid: {name}"
    
    def test_invalid_filenames(self):
        """测试无效文件名"""
        from woniunote.common.utils import validate_filename
        
        invalid_names = [
            '',
            None,
            '../test.txt',
            'file/with/slash.txt',
            'file\\with\\backslash.txt',
            'file<with>brackets.txt',
            'file:with:colon.txt',
            'file"with"quotes.txt',
            'file|with|pipe.txt',
            'file?with?question.txt',
            'file*with*asterisk.txt',
            'file\x00with\x00null.txt'
        ]
        
        for name in invalid_names:
            assert validate_filename(name) is False, f"Filename should be invalid: {name}"
    
    def test_filename_length_limit(self):
        """测试文件名长度限制"""
        from woniunote.common.utils import validate_filename, MAX_FILENAME_LENGTH
        
        # 正常长度
        normal_name = 'a' * (MAX_FILENAME_LENGTH - 4) + '.txt'
        assert validate_filename(normal_name) is True
        
        # 超长文件名
        too_long_name = 'a' * MAX_FILENAME_LENGTH + '.txt'
        assert validate_filename(too_long_name) is False


class TestSanitizeInput:
    """测试输入清理函数"""
    
    def test_normal_input(self):
        """测试正常输入"""
        from woniunote.common.utils import sanitize_input
        
        normal_inputs = [
            'Hello World',
            'This is a test string',
            'Numbers 123456',
            'Mixed content with symbols !@#$%^&*()'
        ]
        
        for input_str in normal_inputs:
            result = sanitize_input(input_str)
            assert result == input_str.strip()
    
    def test_empty_and_none_input(self):
        """测试空值输入"""
        from woniunote.common.utils import sanitize_input
        
        assert sanitize_input('') == ''
        assert sanitize_input(None) == ''
        assert sanitize_input('   ') == ''
    
    def test_length_limit(self):
        """测试长度限制"""
        from woniunote.common.utils import sanitize_input
        
        long_string = 'a' * 2000
        result = sanitize_input(long_string, max_length=100)
        assert len(result) == 100
        assert result == 'a' * 100
    
    def test_control_character_removal(self):
        """测试控制字符移除"""
        from woniunote.common.utils import sanitize_input
        
        input_with_control = 'Hello\x00World\x01Test\x02'
        result = sanitize_input(input_with_control)
        assert result == 'HelloWorldTest'
        
        # 保留换行符和制表符
        input_with_newlines = 'Hello\nWorld\tTest\r'
        result = sanitize_input(input_with_newlines)
        assert result == 'Hello\nWorld\tTest\r'


class TestDatabaseConnection:
    """测试数据库连接相关函数"""
    
    @pytest.fixture
    def mock_pymysql(self):
        """模拟pymysql连接"""
        with patch('woniunote.common.utils.pymysql') as mock:
            mock_connection = Mock()
            mock_cursor = Mock()
            mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
            mock.connect.return_value = mock_connection
            yield mock, mock_connection, mock_cursor
    
    def test_get_db_connection_success(self, mock_pymysql):
        """测试成功的数据库连接"""
        from woniunote.common.utils import get_db_connection
        
        mock_pymysql_module, mock_connection, mock_cursor = mock_pymysql
        
        database_info = {
            'host': 'localhost',
            'user': 'testuser',
            'password': 'testpass',
            'database': 'testdb',
            'port': 3306
        }
        
        result = get_db_connection(database_info)
        
        assert result == mock_connection
        mock_pymysql_module.connect.assert_called_once()
        mock_cursor.execute.assert_called_once_with("SELECT 1")
    
    def test_get_db_connection_missing_params(self):
        """测试缺少必要参数"""
        from woniunote.common.utils import get_db_connection
        
        incomplete_info = {
            'host': 'localhost',
            'user': 'testuser'
            # 缺少password和database
        }
        
        with pytest.raises(ValueError, match="Missing or empty database parameter"):
            get_db_connection(incomplete_info)
    
    def test_get_db_connection_retry_mechanism(self, mock_pymysql):
        """测试重试机制"""
        from woniunote.common.utils import get_db_connection
        import pymysql.err
        
        mock_pymysql_module, mock_connection, mock_cursor = mock_pymysql
        
        # 前两次连接失败，第三次成功
        mock_pymysql_module.connect.side_effect = [
            pymysql.err.OperationalError("Connection failed"),
            pymysql.err.OperationalError("Connection failed"),
            mock_connection
        ]
        
        database_info = {
            'host': 'localhost',
            'user': 'testuser',
            'password': 'testpass',
            'database': 'testdb'
        }
        
        with patch('time.sleep') as mock_sleep:
            result = get_db_connection(database_info, retry_count=3)
        
        assert result == mock_connection
        assert mock_pymysql_module.connect.call_count == 3
        assert mock_sleep.call_count == 2
    
    def test_get_db_connection_context(self, mock_pymysql):
        """测试数据库连接上下文管理器"""
        from woniunote.common.utils import get_db_connection_context
        
        mock_pymysql_module, mock_connection, mock_cursor = mock_pymysql
        
        database_info = {
            'host': 'localhost',
            'user': 'testuser',
            'password': 'testpass',
            'database': 'testdb'
        }
        
        with get_db_connection_context(database_info) as conn:
            assert conn == mock_connection
        
        mock_connection.close.assert_called_once()
    
    def test_get_db_connection_context_error(self, mock_pymysql):
        """测试上下文管理器异常处理"""
        from woniunote.common.utils import get_db_connection_context
        
        mock_pymysql_module, mock_connection, mock_cursor = mock_pymysql
        
        database_info = {
            'host': 'localhost',
            'user': 'testuser',
            'password': 'testpass',
            'database': 'testdb'
        }
        
        with pytest.raises(Exception):
            with get_db_connection_context(database_info) as conn:
                raise Exception("Test error")
        
        mock_connection.rollback.assert_called_once()
        mock_connection.close.assert_called_once()


class TestParseDbUri:
    """测试数据库URI解析函数"""
    
    def test_mysql_uri_parsing(self):
        """测试MySQL URI解析"""
        from woniunote.common.utils import parse_db_uri
        
        uri = "mysql://user:pass@localhost:3306/testdb"
        result = parse_db_uri(uri)
        
        expected = {
            'host': 'localhost',
            'port': 3306,
            'user': 'user',
            'password': 'pass',
            'database': 'testdb'
        }
        
        assert result == expected
    
    def test_sqlite_uri_parsing(self):
        """测试SQLite URI解析"""
        from woniunote.common.utils import parse_db_uri
        
        uri = "sqlite:///path/to/database.db"
        result = parse_db_uri(uri)
        
        expected = {
            'scheme': 'sqlite',
            'path': '/path/to/database.db',
            'database': '/path/to/database.db'
        }
        
        assert result == expected
    
    def test_invalid_uri(self):
        """测试无效URI"""
        from woniunote.common.utils import parse_db_uri
        
        invalid_uris = [
            '',
            None,
            'invalid_uri',
            'mysql://:@/',
            'mysql://user@/',
            'mysql://user:pass@:3306/db'
        ]
        
        for uri in invalid_uris:
            with pytest.raises((ValueError, Exception)):
                parse_db_uri(uri)
    
    def test_default_port(self):
        """测试默认端口"""
        from woniunote.common.utils import parse_db_uri
        
        uri = "mysql://user:pass@localhost/testdb"
        result = parse_db_uri(uri)
        
        assert result['port'] == 3306


class TestConfigUtils:
    """测试配置相关函数"""
    
    @pytest.fixture
    def temp_config_dir(self):
        """创建临时配置目录"""
        temp_dir = tempfile.mkdtemp()
        config_dir = os.path.join(temp_dir, 'configs')
        os.makedirs(config_dir)
        yield config_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def sample_config_file(self, temp_config_dir):
        """创建示例配置文件"""
        config_data = {
            'database': {
                'SQLALCHEMY_DATABASE_URI': 'sqlite:///test.db',
                'SQLALCHEMY_TRACK_MODIFICATIONS': False
            },
            'SECRET_KEY': 'test-secret-key',
            'cache': {
                'default_ttl': 300
            }
        }
        
        config_file = os.path.join(temp_config_dir, 'user_password_config.yaml')
        with open(config_file, 'w', encoding='utf-8') as f:
            import yaml
            yaml.dump(config_data, f, default_flow_style=False)
        
        return config_file
    
    def test_read_config_success(self, sample_config_file):
        """测试配置文件读取成功"""
        from woniunote.common.utils import read_config
        
        with patch('os.getcwd') as mock_cwd:
            mock_cwd.return_value = os.path.dirname(os.path.dirname(sample_config_file))
            
            config = read_config()
            
            assert config is not None
            assert 'database' in config
            assert 'SECRET_KEY' in config
            assert config['SECRET_KEY'] == 'test-secret-key'
    
    def test_read_config_file_not_found(self):
        """测试配置文件不存在时创建默认配置"""
        from woniunote.common.utils import read_config
        
        with patch('os.getcwd') as mock_cwd, \
             patch('os.path.exists') as mock_exists, \
             patch('os.makedirs'), \
             patch('builtins.open', mock_open()) as mock_file:
            
            mock_cwd.return_value = '/tmp/test'
            mock_exists.return_value = False
            
            config = read_config()
            
            # 验证返回默认配置
            assert config is not None
            assert 'database' in config
            assert 'SECRET_KEY' in config
    
    def test_read_config_yaml_error(self):
        """测试YAML解析错误"""
        from woniunote.common.utils import read_config
        
        with patch('builtins.open', mock_open(read_data='invalid: yaml: content:')), \
             patch('os.path.exists', return_value=True), \
             patch('os.path.getsize', return_value=100):
            
            config = read_config()
            
            # 应该返回默认配置
            assert config is not None
            assert config['SECRET_KEY'] == 'dev-woniunote-secret-key-2025'
    
    def test_read_config_oversized_file(self):
        """测试配置文件过大"""
        from woniunote.common.utils import read_config
        
        with patch('os.path.exists', return_value=True), \
             patch('os.path.getsize', return_value=2 * 1024 * 1024):  # 2MB
            
            with pytest.raises(ValueError, match="Config file too large"):
                read_config()
    
    def test_get_package_path(self):
        """测试获取包路径"""
        from woniunote.common.utils import get_package_path
        
        # 测试已知包
        path = get_package_path('sys')
        assert path is not None
        
        # 测试不存在的包
        path = get_package_path('nonexistent_package')
        assert path is None
    
    def test_get_package_path_invalid_name(self):
        """测试无效包名"""
        from woniunote.common.utils import get_package_path
        
        with pytest.raises(ValueError, match="Invalid package name"):
            get_package_path('')
        
        with pytest.raises(ValueError, match="Package name contains invalid characters"):
            get_package_path('invalid-name')


class TestImageCode:
    """测试图片验证码生成器"""
    
    def test_image_code_init(self):
        """测试ImageCode初始化"""
        from woniunote.common.utils import ImageCode
        
        # 正常初始化
        img_code = ImageCode()
        assert img_code.width == 120
        assert img_code.height == 50
        
        # 自定义尺寸
        img_code = ImageCode(150, 60)
        assert img_code.width == 150
        assert img_code.height == 60
    
    def test_image_code_invalid_dimensions(self):
        """测试无效尺寸"""
        from woniunote.common.utils import ImageCode
        
        with pytest.raises(ValueError, match="Width and height must be integers"):
            ImageCode("invalid", 50)
        
        with pytest.raises(ValueError, match="Invalid image dimensions"):
            ImageCode(10, 10)  # 太小
        
        with pytest.raises(ValueError, match="Invalid image dimensions"):
            ImageCode(400, 300)  # 太大
    
    def test_gen_text(self):
        """测试随机字符串生成"""
        from woniunote.common.utils import ImageCode
        
        img_code = ImageCode()
        
        # 默认长度
        text = img_code.gen_text()
        assert len(text) == 4
        assert all(c in '0123456789' for c in text)
        
        # 指定长度
        text = img_code.gen_text(6)
        assert len(text) == 6
        
        # 无效长度（应该使用默认值）
        text = img_code.gen_text(15)
        assert len(text) == 4
    
    def test_rand_color(self):
        """测试随机颜色生成"""
        from woniunote.common.utils import ImageCode
        
        img_code = ImageCode()
        color = img_code.rand_color()
        
        assert isinstance(color, tuple)
        assert len(color) == 3
        assert all(0 <= c <= 255 for c in color)
    
    def test_get_code(self):
        """测试验证码生成"""
        from woniunote.common.utils import ImageCode
        
        with patch('woniunote.common.utils.get_system_font_path', return_value=None):
            img_code = ImageCode()
            code, image_bytes = img_code.get_code()
            
            assert isinstance(code, str)
            assert len(code) == 4
            assert isinstance(image_bytes, bytes)
            assert len(image_bytes) > 0


class TestEmailUtils:
    """测试邮件相关工具函数"""
    
    def test_gen_email_code(self):
        """测试邮箱验证码生成"""
        from woniunote.common.utils import gen_email_code
        
        # 默认长度
        code = gen_email_code()
        assert len(code) == 6
        assert all(c in '23456789ABCDEFGHJKLMNPQRSTUVWXYZ' for c in code)
        
        # 指定长度
        code = gen_email_code(8)
        assert len(code) == 8
        
        # 无效长度（使用默认值）
        code = gen_email_code(15)
        assert len(code) == 6
        
        # 生成的验证码应该不同
        code1 = gen_email_code()
        code2 = gen_email_code()
        assert code1 != code2
    
    @patch('woniunote.common.utils.SMTP_SSL')
    def test_send_email_success(self, mock_smtp):
        """测试邮件发送成功"""
        from woniunote.common.utils import send_email
        
        mock_smtp_instance = Mock()
        mock_smtp.return_value = mock_smtp_instance
        
        result = send_email('test@example.com', '123456')
        
        assert result is True
        mock_smtp_instance.login.assert_called_once()
        mock_smtp_instance.sendmail.assert_called_once()
        mock_smtp_instance.quit.assert_called_once()
    
    def test_send_email_invalid_receiver(self):
        """测试无效收件人"""
        from woniunote.common.utils import send_email
        
        with pytest.raises(ValueError, match="Invalid receiver email address"):
            send_email('invalid_email', '123456')
    
    def test_send_email_invalid_code(self):
        """测试无效验证码"""
        from woniunote.common.utils import send_email
        
        with pytest.raises(ValueError, match="Invalid verification code"):
            send_email('test@example.com', '')
        
        with pytest.raises(ValueError, match="Invalid verification code"):
            send_email('test@example.com', 'a' * 25)  # 过长
    
    @patch('woniunote.common.utils.SMTP_SSL')
    def test_send_email_smtp_error(self, mock_smtp):
        """测试SMTP错误"""
        from woniunote.common.utils import send_email
        
        mock_smtp.side_effect = Exception("SMTP connection failed")
        
        with pytest.raises(Exception):
            send_email('test@example.com', '123456')


class TestModelConversion:
    """测试模型转换函数"""
    
    def test_model_list_empty(self):
        """测试空结果集"""
        from woniunote.common.utils import model_list
        
        assert model_list([]) == []
        assert model_list(None) == []
    
    def test_model_list_single_object(self):
        """测试单个对象转换"""
        from woniunote.common.utils import model_list
        
        # 创建模拟模型对象
        mock_obj = Mock()
        mock_obj.__dict__ = {
            'id': 1,
            'name': 'test',
            'created_at': datetime(2023, 1, 1, 12, 0, 0),
            '_sa_instance_state': 'should_be_ignored'
        }
        
        result = model_list([mock_obj])
        
        assert len(result) == 1
        assert result[0]['id'] == 1
        assert result[0]['name'] == 'test'
        assert result[0]['created_at'] == '2023-01-01 12:00:00'
        assert '_sa_instance_state' not in result[0]
    
    def test_model_list_multiple_objects(self):
        """测试多个对象转换"""
        from woniunote.common.utils import model_list
        
        objects = []
        for i in range(3):
            mock_obj = Mock()
            mock_obj.__dict__ = {
                'id': i,
                'name': f'test{i}',
                'value': None,
                'active': True,
                '_sa_instance_state': 'ignore'
            }
            objects.append(mock_obj)
        
        result = model_list(objects)
        
        assert len(result) == 3
        for i, item in enumerate(result):
            assert item['id'] == i
            assert item['name'] == f'test{i}'
            assert item['value'] is None
            assert item['active'] is True
    
    def test_model_list_non_iterable(self):
        """测试非可迭代对象"""
        from woniunote.common.utils import model_list
        
        mock_obj = Mock()
        mock_obj.__dict__ = {'id': 1, 'name': 'test'}
        
        result = model_list(mock_obj)
        
        assert len(result) == 1
        assert result[0]['id'] == 1
        assert result[0]['name'] == 'test'
    
    def test_model_join_list_named_tuple(self):
        """测试命名元组结果转换"""
        from woniunote.common.utils import model_join_list
        from collections import namedtuple
        
        # 创建命名元组
        Row = namedtuple('Row', ['id', 'name', 'created_at'])
        rows = [
            Row(1, 'test1', datetime(2023, 1, 1)),
            Row(2, 'test2', datetime(2023, 1, 2))
        ]
        
        result = model_join_list(rows)
        
        assert len(result) == 2
        assert result[0]['id'] == 1
        assert result[0]['name'] == 'test1'
        assert result[0]['created_at'] == '2023-01-01 00:00:00'
    
    def test_model_join_list_dict(self):
        """测试字典结果转换"""
        from woniunote.common.utils import model_join_list
        
        dicts = [
            {'id': 1, 'name': 'test1', 'created_at': datetime(2023, 1, 1)},
            {'id': 2, 'name': 'test2', 'value': None}
        ]
        
        result = model_join_list(dicts)
        
        assert len(result) == 2
        assert result[0]['id'] == 1
        assert result[0]['created_at'] == '2023-01-01 00:00:00'
        assert result[1]['value'] is None


class TestImageProcessing:
    """测试图片处理函数"""
    
    @pytest.fixture
    def temp_image(self):
        """创建临时测试图片"""
        # 创建一个简单的测试图片
        img = Image.new('RGB', (200, 150), color='red')
        temp_file = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
        img.save(temp_file.name, 'JPEG')
        temp_file.close()
        yield temp_file.name
        os.unlink(temp_file.name)
    
    def test_compress_image_success(self, temp_image):
        """测试图片压缩成功"""
        from woniunote.common.utils import compress_image
        
        dest_file = temp_image + '_compressed.jpg'
        
        try:
            result = compress_image(temp_image, dest_file, 100, 80)
            
            assert result is True
            assert os.path.exists(dest_file)
            
            # 验证压缩后图片
            with Image.open(dest_file) as img:
                assert img.size == (200, 150)  # 小于目标宽度，尺寸不变
        finally:
            if os.path.exists(dest_file):
                os.unlink(dest_file)
    
    def test_compress_image_resize(self, temp_image):
        """测试图片缩放"""
        from woniunote.common.utils import compress_image
        
        dest_file = temp_image + '_resized.jpg'
        
        try:
            result = compress_image(temp_image, dest_file, 100, 80)  # 缩放到100px宽
            
            assert result is True
            
            with Image.open(dest_file) as img:
                assert img.size[0] <= 100  # 宽度应该被限制
        finally:
            if os.path.exists(dest_file):
                os.unlink(dest_file)
    
    def test_compress_image_invalid_params(self):
        """测试无效参数"""
        from woniunote.common.utils import compress_image
        
        with pytest.raises(ValueError, match="Source and destination paths required"):
            compress_image('', '/tmp/dest.jpg', 100)
        
        with pytest.raises(ValueError, match="Invalid width parameter"):
            compress_image('/tmp/src.jpg', '/tmp/dest.jpg', -1)
        
        with pytest.raises(ValueError, match="Invalid width parameter"):
            compress_image('/tmp/src.jpg', '/tmp/dest.jpg', 10000)
    
    def test_compress_image_file_not_found(self):
        """测试源文件不存在"""
        from woniunote.common.utils import compress_image
        
        with pytest.raises(FileNotFoundError):
            compress_image('/nonexistent/file.jpg', '/tmp/dest.jpg', 100)
    
    def test_convert_image_to_webp(self, temp_image):
        """测试WebP转换"""
        from woniunote.common.utils import convert_image_to_webp
        
        dest_file = temp_image + '.webp'
        
        try:
            result = convert_image_to_webp(temp_image, dest_file, 80)
            
            assert result is True
            assert os.path.exists(dest_file)
            
            with Image.open(dest_file) as img:
                assert img.format == 'WEBP'
        finally:
            if os.path.exists(dest_file):
                os.unlink(dest_file)


class TestImageUtils:
    """测试图片工具函数"""
    
    def test_parse_image_url_valid_content(self):
        """测试从HTML内容中解析图片URL"""
        from woniunote.common.utils import parse_image_url
        
        html_content = '''
        <div>
            <img src="http://example.com/image1.jpg" alt="Image 1">
            <img src="https://example.com/image2.png" alt="Image 2">
            <img src="/local/image3.gif">
        </div>
        '''
        
        urls = parse_image_url(html_content)
        
        assert len(urls) == 3
        assert 'http://example.com/image1.jpg' in urls
        assert 'https://example.com/image2.png' in urls
        assert '/local/image3.gif' in urls
    
    def test_parse_image_url_empty_content(self):
        """测试空内容"""
        from woniunote.common.utils import parse_image_url
        
        assert parse_image_url('') == []
        assert parse_image_url(None) == []
    
    def test_parse_image_url_no_images(self):
        """测试无图片内容"""
        from woniunote.common.utils import parse_image_url
        
        html_content = '<div><p>No images here</p></div>'
        urls = parse_image_url(html_content)
        assert urls == []
    
    def test_parse_image_url_limit(self):
        """测试URL数量限制"""
        from woniunote.common.utils import parse_image_url
        
        # 创建包含大量图片的HTML
        html_content = ''
        for i in range(60):
            html_content += f'<img src="http://example.com/image{i}.jpg">'
        
        urls = parse_image_url(html_content, max_urls=10)
        assert len(urls) == 10
    
    def test_parse_image_url_malicious_content(self):
        """测试恶意内容过滤"""
        from woniunote.common.utils import parse_image_url
        
        malicious_html = '''
        <img src="http://example.com/safe.jpg">
        <img src="javascript:alert('xss')">
        <img src="http://example.com/image<script>.jpg">
        <img src="http://example.com/clean.png">
        '''
        
        urls = parse_image_url(malicious_html)
        
        # 应该只包含安全的URL
        safe_urls = [url for url in urls if not any(char in url for char in ['<', '>', '"', "'", '`'])]
        assert len(safe_urls) >= 2  # 至少包含两个安全URL
    
    @patch('woniunote.common.utils.requests.get')
    def test_download_image_success(self, mock_get):
        """测试图片下载成功"""
        from woniunote.common.utils import download_image
        
        # 模拟成功的HTTP响应
        mock_response = Mock()
        mock_response.headers = {'content-type': 'image/jpeg', 'content-length': '1024'}
        mock_response.iter_content.return_value = [b'fake_image_data']
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        dest_file = tempfile.NamedTemporaryFile(delete=False).name
        
        try:
            result = download_image('http://example.com/image.jpg', dest_file)
            
            assert result is True
            assert os.path.exists(dest_file)
            
            with open(dest_file, 'rb') as f:
                content = f.read()
                assert content == b'fake_image_data'
        finally:
            if os.path.exists(dest_file):
                os.unlink(dest_file)
    
    def test_download_image_invalid_url(self):
        """测试无效URL"""
        from woniunote.common.utils import download_image
        
        with pytest.raises(ValueError, match="Invalid URL"):
            download_image('', '/tmp/image.jpg')
        
        with pytest.raises(ValueError, match="URL must start with http"):
            download_image('ftp://example.com/image.jpg', '/tmp/image.jpg')
    
    @patch('woniunote.common.utils.requests.get')
    def test_download_image_invalid_content_type(self, mock_get):
        """测试无效内容类型"""
        from woniunote.common.utils import download_image
        
        mock_response = Mock()
        mock_response.headers = {'content-type': 'text/html'}
        mock_get.return_value = mock_response
        
        with pytest.raises(ValueError, match="Invalid content type"):
            download_image('http://example.com/notimage.html', '/tmp/image.jpg')
    
    @patch('woniunote.common.utils.requests.get')
    def test_download_image_too_large(self, mock_get):
        """测试文件过大"""
        from woniunote.common.utils import download_image, MAX_IMAGE_SIZE
        
        mock_response = Mock()
        mock_response.headers = {
            'content-type': 'image/jpeg', 
            'content-length': str(MAX_IMAGE_SIZE + 1)
        }
        mock_get.return_value = mock_response
        
        with pytest.raises(ValueError, match="File too large"):
            download_image('http://example.com/large.jpg', '/tmp/image.jpg')


class TestColorUtils:
    """测试颜色相关函数"""
    
    def test_generate_random_color(self):
        """测试随机颜色生成"""
        from woniunote.common.utils import generate_random_color
        
        color = generate_random_color()
        
        assert isinstance(color, tuple)
        assert len(color) == 3
        assert all(50 <= c <= 200 for c in color)
    
    def test_hsv_to_rgb_conversion(self):
        """测试HSV到RGB转换"""
        from woniunote.common.utils import hsv_to_rgb
        
        # 测试纯红色 (H=0, S=1, V=1)
        r, g, b = hsv_to_rgb(0, 1, 1)
        assert abs(r - 1.0) < 0.01
        assert abs(g - 0.0) < 0.01
        assert abs(b - 0.0) < 0.01
        
        # 测试白色 (H=0, S=0, V=1)
        r, g, b = hsv_to_rgb(0, 0, 1)
        assert abs(r - 1.0) < 0.01
        assert abs(g - 1.0) < 0.01
        assert abs(b - 1.0) < 0.01
        
        # 测试黑色 (H=0, S=0, V=0)
        r, g, b = hsv_to_rgb(0, 0, 0)
        assert abs(r - 0.0) < 0.01
        assert abs(g - 0.0) < 0.01
        assert abs(b - 0.0) < 0.01
    
    def test_hsv_to_rgb_invalid_input(self):
        """测试无效HSV输入的处理"""
        from woniunote.common.utils import hsv_to_rgb
        
        # 超出范围的值应该被限制
        r, g, b = hsv_to_rgb(2.0, 2.0, 2.0)
        assert all(0 <= c <= 1 for c in [r, g, b])
        
        r, g, b = hsv_to_rgb(-1.0, -1.0, -1.0)
        assert all(0 <= c <= 1 for c in [r, g, b])


class TestImageGeneration:
    """测试图片生成函数"""
    
    def test_generate_gradient_background(self):
        """测试渐变背景生成"""
        from woniunote.common.utils import generate_gradient_background
        
        img = generate_gradient_background(100, 80)
        
        assert img.size == (100, 80)
        assert img.mode == 'RGB'
    
    def test_generate_gradient_background_invalid_params(self):
        """测试无效参数"""
        from woniunote.common.utils import generate_gradient_background
        
        with pytest.raises(ValueError, match="Width and height must be integers"):
            generate_gradient_background("invalid", 100)
        
        with pytest.raises(ValueError, match="Invalid dimensions"):
            generate_gradient_background(-1, 100)
        
        with pytest.raises(ValueError, match="Invalid dimensions"):
            generate_gradient_background(3000, 100)  # 过大
    
    def test_create_thumb_png(self):
        """测试缩略图创建"""
        from woniunote.common.utils import create_thumb_png
        
        with patch('woniunote.common.utils.get_system_font_path', return_value=None):
            img = create_thumb_png(200, 150, "Test")
            
            assert img.size == (200, 150)
            assert img.mode == 'RGB'
    
    def test_create_thumb_png_invalid_params(self):
        """测试缩略图创建的无效参数"""
        from woniunote.common.utils import create_thumb_png
        
        with pytest.raises(ValueError, match="Width and height must be integers"):
            create_thumb_png("invalid", 150)
        
        with pytest.raises(ValueError, match="Invalid dimensions"):
            create_thumb_png(1500, 150)  # 过大


class TestSystemUtils:
    """测试系统工具函数"""
    
    def test_get_system_font_path_windows(self):
        """测试Windows系统字体路径"""
        from woniunote.common.utils import get_system_font_path
        
        with patch('os.name', 'nt'), \
             patch('os.path.exists') as mock_exists:
            
            # 模拟找到字体文件
            mock_exists.side_effect = lambda path: 'arial.ttf' in path
            
            font_path = get_system_font_path()
            assert font_path is not None
            assert 'arial.ttf' in font_path.lower()
    
    def test_get_system_font_path_linux(self):
        """测试Linux系统字体路径"""
        from woniunote.common.utils import get_system_font_path
        
        with patch('os.name', 'posix'), \
             patch('os.path.exists') as mock_exists:
            
            # 模拟找到字体文件
            mock_exists.side_effect = lambda path: 'DejaVuSans.ttf' in path
            
            font_path = get_system_font_path()
            assert font_path is not None
            assert 'DejaVuSans.ttf' in font_path
    
    def test_get_system_font_path_not_found(self):
        """测试找不到系统字体"""
        from woniunote.common.utils import get_system_font_path
        
        with patch('os.name', 'posix'), \
             patch('os.path.exists', return_value=False):
            
            font_path = get_system_font_path()
            assert font_path is None
    
    def test_get_memory_usage_with_psutil(self):
        """测试使用psutil获取内存使用量"""
        from woniunote.common.utils import get_memory_usage
        
        mock_process = Mock()
        mock_process.memory_info.return_value.rss = 100 * 1024 * 1024  # 100MB
        
        with patch('woniunote.common.utils.psutil.Process', return_value=mock_process), \
             patch('woniunote.common.utils.os.getpid', return_value=1234):
            
            memory = get_memory_usage()
            assert memory == 100.0
    
    def test_get_memory_usage_without_psutil(self):
        """测试没有psutil时的内存获取"""
        from woniunote.common.utils import get_memory_usage
        
        with patch.dict('sys.modules', {'psutil': None}), \
             patch('woniunote.common.utils.resource') as mock_resource:
            
            mock_resource.getrusage.return_value.ru_maxrss = 100 * 1024  # 100MB in KB
            mock_resource.RUSAGE_SELF = 0
            
            memory = get_memory_usage()
            assert memory == 100.0


class TestPerformanceMonitor:
    """测试性能监控装饰器"""
    
    def test_performance_monitor_normal_function(self):
        """测试正常函数的性能监控"""
        from woniunote.common.utils import performance_monitor
        
        @performance_monitor
        def test_function(x, y):
            return x + y
        
        result = test_function(1, 2)
        assert result == 3
    
    def test_performance_monitor_slow_function(self):
        """测试慢函数的性能监控"""
        from woniunote.common.utils import performance_monitor
        
        with patch('woniunote.common.utils.time.time') as mock_time, \
             patch('woniunote.common.utils.get_memory_usage', return_value=100.0):
            
            # 模拟慢函数（执行时间超过1秒）
            mock_time.side_effect = [0.0, 2.0]  # 开始时间和结束时间
            
            @performance_monitor
            def slow_function():
                return "done"
            
            with patch('woniunote.common.utils.logger') as mock_logger:
                result = slow_function()
                
                assert result == "done"
                # 验证记录了慢函数警告
                mock_logger.warning.assert_called_once()
    
    def test_performance_monitor_function_error(self):
        """测试函数出错时的性能监控"""
        from woniunote.common.utils import performance_monitor
        
        @performance_monitor
        def error_function():
            raise ValueError("Test error")
        
        with patch('woniunote.common.utils.logger') as mock_logger:
            with pytest.raises(ValueError):
                error_function()
            
            # 验证记录了错误
            mock_logger.error.assert_called_once()


class TestSafeFileOperation:
    """测试安全文件操作上下文管理器"""
    
    def test_safe_file_operation_success(self):
        """测试安全文件操作成功"""
        from woniunote.common.utils import safe_file_operation
        
        temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False)
        temp_file.write("test content")
        temp_file.close()
        
        try:
            with safe_file_operation(temp_file.name, 'r') as f:
                content = f.read()
                assert content == "test content"
        finally:
            os.unlink(temp_file.name)
    
    def test_safe_file_operation_invalid_filename(self):
        """测试无效文件名"""
        from woniunote.common.utils import safe_file_operation
        
        with pytest.raises(ValueError, match="Invalid filename"):
            with safe_file_operation('/path/../invalid.txt', 'r'):
                pass
    
    def test_safe_file_operation_large_file(self):
        """测试大文件限制"""
        from woniunote.common.utils import safe_file_operation
        
        with patch('os.path.exists', return_value=True), \
             patch('os.path.getsize', return_value=200 * 1024 * 1024):  # 200MB
            
            with pytest.raises(ValueError, match="File too large"):
                with safe_file_operation('/tmp/large_file.txt', 'r'):
                    pass


@pytest.mark.integration
class TestIntegrationScenarios:
    """测试集成场景"""
    
    def test_complete_image_processing_workflow(self):
        """测试完整的图片处理工作流"""
        from woniunote.common.utils import ImageCode, compress_image, convert_image_to_webp
        
        # 1. 生成验证码图片
        with patch('woniunote.common.utils.get_system_font_path', return_value=None):
            img_code = ImageCode()
            code, image_bytes = img_code.get_code()
        
        assert len(image_bytes) > 0
        assert len(code) == 4
        
        # 2. 保存图片到临时文件
        temp_original = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
        temp_original.write(image_bytes)
        temp_original.close()
        
        temp_compressed = temp_original.name + '_compressed.jpg'
        temp_webp = temp_original.name + '.webp'
        
        try:
            # 3. 压缩图片
            compress_result = compress_image(temp_original.name, temp_compressed, 80, 70)
            assert compress_result is True
            assert os.path.exists(temp_compressed)
            
            # 4. 转换为WebP
            webp_result = convert_image_to_webp(temp_compressed, temp_webp, 70)
            assert webp_result is True
            assert os.path.exists(temp_webp)
            
        finally:
            # 清理临时文件
            for file_path in [temp_original.name, temp_compressed, temp_webp]:
                if os.path.exists(file_path):
                    os.unlink(file_path)
    
    def test_config_and_database_workflow(self):
        """测试配置和数据库工作流"""
        from woniunote.common.utils import read_config, parse_db_uri
        
        # 1. 读取配置（模拟配置文件不存在，会创建默认配置）
        with patch('os.path.exists', return_value=False), \
             patch('os.makedirs'), \
             patch('builtins.open', mock_open()) as mock_file:
            
            config = read_config()
            
            assert config is not None
            assert 'database' in config
            
            # 2. 解析数据库URI
            db_uri = config['database']['SQLALCHEMY_DATABASE_URI']
            db_info = parse_db_uri(db_uri)
            
            assert 'database' in db_info


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])