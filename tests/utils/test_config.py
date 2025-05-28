#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试配置模块

此模块提供WoniuNote测试的配置参数和环境设置
"""

import os
import sys
import logging
import yaml
from pathlib import Path
from cryptography.fernet import Fernet
from dotenv import load_dotenv
from woniunote.common.simple_logger import get_simple_logger

# 加载环境变量
load_dotenv()

# 项目路径配置
PROJECT_ROOT = Path(__file__).parent.parent.parent.absolute()
TESTS_DIR = os.path.join(PROJECT_ROOT, 'tests')
TEMP_DIR = os.path.join(TESTS_DIR, 'temp')

# 配置加密密钥
ENCRYPTION_KEY = os.getenv('TEST_CONFIG_KEY', Fernet.generate_key())
cipher_suite = Fernet(ENCRYPTION_KEY)

def encrypt_value(value):
    """加密配置值"""
    if isinstance(value, str):
        return cipher_suite.encrypt(value.encode()).decode()
    return value

def decrypt_value(value):
    """解密配置值"""
    if isinstance(value, str):
        try:
            return cipher_suite.decrypt(value.encode()).decode()
        except:
            return value
    return value

# 服务器配置
SERVER_CONFIG = {
    'host': os.getenv('TEST_SERVER_HOST', '127.0.0.1'),
    'port': int(os.getenv('TEST_SERVER_PORT', '5001')),
    'protocol': os.getenv('TEST_SERVER_PROTOCOL', 'http'),
    'timeout': int(os.getenv('TEST_SERVER_TIMEOUT', '5')),
    'retry_count': int(os.getenv('TEST_SERVER_RETRY_COUNT', '3')),
    'retry_delay': int(os.getenv('TEST_SERVER_RETRY_DELAY', '1')),
    'health_endpoint': os.getenv('TEST_SERVER_HEALTH_ENDPOINT', '/health')
}

# 数据库配置
DATABASE_CONFIG = {
    'host': os.getenv('TEST_DB_HOST', '127.0.0.1'),
    'port': int(os.getenv('TEST_DB_PORT', '3306')),
    'user': os.getenv('TEST_DB_USER', 'woniunote_user'),
    'password': decrypt_value(os.getenv('TEST_DB_PASSWORD', 'Woniunote_password1!')),
    'database': os.getenv('TEST_DB_NAME', 'woniunote')
}

# 测试用户账户
TEST_USERS = {
    'admin': {
        'username': os.getenv('TEST_ADMIN_USERNAME', 'admin'),
        'password': decrypt_value(os.getenv('TEST_ADMIN_PASSWORD', 'admin123')),
        'email': os.getenv('TEST_ADMIN_EMAIL', 'admin@example.com')
    },
    'normal': {
        'username': os.getenv('TEST_USER_USERNAME', 'testuser'),
        'password': decrypt_value(os.getenv('TEST_USER_PASSWORD', 'password123')),
        'email': os.getenv('TEST_USER_EMAIL', 'test@example.com')
    }
}

# 测试数据
TEST_DATA = {
    'article': {
        'sample_id': int(os.getenv('TEST_ARTICLE_SAMPLE_ID', '398')),
        'headline': os.getenv('TEST_ARTICLE_HEADLINE', '测试文章'),
        'content': os.getenv('TEST_ARTICLE_CONTENT', '这是一篇测试文章的内容'),
        'type': os.getenv('TEST_ARTICLE_TYPE', 'test'),
        'numeric_type': int(os.getenv('TEST_ARTICLE_NUMERIC_TYPE', '1'))
    },
    'comment': {
        'content': os.getenv('TEST_COMMENT_CONTENT', '这是一条测试评论')
    },
    'favorite': {
        'reason': os.getenv('TEST_FAVORITE_REASON', '测试收藏')
    }
}

# 日志配置
LOG_CONFIG = {
    'level': getattr(logging, os.getenv('TEST_LOG_LEVEL', 'INFO')),
    'format': os.getenv('TEST_LOG_FORMAT', '%(asctime)s - %(levelname)s - %(name)s - %(message)s'),
    'file': os.getenv('TEST_LOG_FILE', os.path.join(TESTS_DIR, 'test.log'))
}

# 性能测试配置
PERFORMANCE_CONFIG = {
    'concurrent_users': int(os.getenv('TEST_CONCURRENT_USERS', '10')),
    'request_timeout': int(os.getenv('TEST_REQUEST_TIMEOUT', '30')),
    'think_time': int(os.getenv('TEST_THINK_TIME', '1')),
    'ramp_up_time': int(os.getenv('TEST_RAMP_UP_TIME', '60'))
}

# 测试覆盖率配置
COVERAGE_CONFIG = {
    'enabled': os.getenv('TEST_COVERAGE_ENABLED', 'true').lower() == 'true',
    'report_dir': os.getenv('TEST_COVERAGE_REPORT_DIR', os.path.join(TESTS_DIR, 'coverage')),
    'source_dir': os.getenv('TEST_COVERAGE_SOURCE_DIR', os.path.join(PROJECT_ROOT, 'woniunote')),
    'exclude_patterns': os.getenv('TEST_COVERAGE_EXCLUDE', 'tests/*,venv/*').split(',')
}

def load_yaml_config(config_path):
    """加载YAML配置文件"""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            # 解密敏感信息
            if 'database' in config:
                config['database']['password'] = decrypt_value(config['database']['password'])
            return config
    except Exception as e:
        logger.error(f"加载配置文件失败: {e}")
        return {}

def save_yaml_config(config_path, config):
    """保存YAML配置文件"""
    try:
        # 加密敏感信息
        if 'database' in config:
            config['database']['password'] = encrypt_value(config['database']['password'])
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.safe_dump(config, f, allow_unicode=True)
        return True
    except Exception as e:
        logger.error(f"保存配置文件失败: {e}")
        return False

def setup_logging(name="woniunote_test"):
    """使用SimpleLogger初始化日志记录器"""
    return get_simple_logger(name)

logger = setup_logging("woniunote_test")

# 获取基础URL
def get_base_url():
    """返回服务器基础URL"""
    proto = SERVER_CONFIG['protocol']
    host = SERVER_CONFIG['host']
    port = SERVER_CONFIG['port']
    return f"{proto}://{host}:{port}"

# 确保临时目录存在
if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR, exist_ok=True)

# 添加单元测试
import pytest

@pytest.mark.unit
def test_server_config():
    """测试服务器配置是否有效"""
    assert 'host' in SERVER_CONFIG
    assert 'port' in SERVER_CONFIG
    assert 'protocol' in SERVER_CONFIG
    assert SERVER_CONFIG['host'] == '127.0.0.1'
    assert SERVER_CONFIG['port'] == 5001
    assert SERVER_CONFIG['protocol'] in ['http', 'https']
    logging.info("服务器配置测试通过")

@pytest.mark.unit
def test_project_paths():
    """测试项目路径是否正确"""
    assert os.path.exists(PROJECT_ROOT)
    assert os.path.exists(TESTS_DIR)
    assert os.path.exists(TEMP_DIR)
    assert os.path.basename(PROJECT_ROOT) == 'woniunote'
    logging.info("项目路径测试通过")

@pytest.mark.unit
def test_get_base_url():
    """测试基础URL生成是否正确"""
    base_url = get_base_url()
    assert base_url.startswith(SERVER_CONFIG['protocol'])
    assert SERVER_CONFIG['host'] in base_url
    assert str(SERVER_CONFIG['port']) in base_url
    logging.info(f"基础URL测试通过: {base_url}")

@pytest.mark.unit
def test_config_encryption():
    """测试配置加密功能"""
    test_value = "test_password"
    encrypted = encrypt_value(test_value)
    decrypted = decrypt_value(encrypted)
    assert decrypted == test_value
    assert encrypted != test_value
    logging.info("配置加密测试通过")
