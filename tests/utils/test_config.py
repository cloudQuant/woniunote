#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试配置模块

此模块提供WoniuNote测试的配置参数和环境设置
"""

import os
import sys
import logging
from pathlib import Path

# 项目路径配置
PROJECT_ROOT = Path(__file__).parent.parent.parent.absolute()
TESTS_DIR = os.path.join(PROJECT_ROOT, 'tests')
TEMP_DIR = os.path.join(TESTS_DIR, 'temp')

# 服务器配置
SERVER_CONFIG = {
    'host': '127.0.0.1',
    'port': 5000,
    'protocol': 'https',
    'timeout': 5,
    'retry_count': 3,
    'retry_delay': 1,
    'health_endpoint': '/health'
}

# 数据库配置
DATABASE_CONFIG = {
    'host': '127.0.0.1',
    'port': 3306,
    'user': 'woniunote_user',
    'password': 'Woniunote_password1!',
    'database': 'woniunote'
}

# 测试用户账户
TEST_USERS = {
    'admin': {
        'username': 'admin',
        'password': 'admin123',
        'email': 'admin@example.com'
    },
    'normal': {
        'username': 'testuser',
        'password': 'password123',
        'email': 'test@example.com'
    }
}

# 测试数据
TEST_DATA = {
    'article': {
        'sample_id': 398,  # 用于简单测试的文章ID
        'headline': '测试文章',  # 数据库和代码模型都使用headline字段
        'content': '这是一篇测试文章的内容',
        'type': 'test',  # 注意字段类型为varchar(10)，使用字符串而不是整数
        'numeric_type': 1  # 当需要整数类型时使用此字段
    },
    'comment': {
        'content': '这是一条测试评论'
    },
    'favorite': {
        'reason': '测试收藏'
    }
}

# 日志配置
LOG_CONFIG = {
    'level': logging.INFO,
    'format': '%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    'file': os.path.join(TESTS_DIR, 'test.log')
}

# 配置日志
def setup_logging(name='test'):
    """设置日志配置"""
    logging.basicConfig(
        level=LOG_CONFIG['level'],
        format=LOG_CONFIG['format']
    )
    return logging.getLogger(name)

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
    assert SERVER_CONFIG['port'] == 5000
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
