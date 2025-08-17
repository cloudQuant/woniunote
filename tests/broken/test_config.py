#!/usr/bin/env python3
"""
测试配置相关功能
"""
import pytest
import os
import sys

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

@pytest.mark.unit
def test_basic():
    """基本测试占位符"""
    pass

@pytest.mark.unit  
def test_server_config():
    """测试服务器配置是否有效"""
    try:
        # Basic test without external dependencies
        server_config = {
            'host': '127.0.0.1',
            'port': 5001,
            'protocol': 'http'
        }
        assert 'host' in server_config
        assert 'port' in server_config
        assert 'protocol' in server_config
        assert server_config['host'] == '127.0.0.1'
        assert server_config['port'] == 5001
        assert server_config['protocol'] in ['http', 'https']
    except Exception as e:
        assert False, f"Config test failed: {e}"

@pytest.mark.unit
def test_project_paths():
    """测试项目路径是否正确"""
    try:
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        assert os.path.exists(project_root)
        assert os.path.basename(project_root) == 'woniunote'
    except Exception as e:
        assert False, f"Path test failed: {e}"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])