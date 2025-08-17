#!/usr/bin/env python3
"""
直接覆盖率测试
"""
import pytest
import sys
import os

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

class TestDirectCoverage:
    """直接覆盖率测试"""
    
    def test_basic(self):
        """基本测试占位符"""
        pass
    
    def test_validate_email(self):
        """测试邮箱验证功能"""
        # 使用直接路径导入
        import sys
        sys.path.insert(0, '/home/yun/Documents/woniunote/woniunote/common')
        try:
            import utils
            
            # 有效邮箱
            assert utils.validate_email("test@example.com") is True
            assert utils.validate_email("user.name@domain.co.uk") is True
            
            # 无效邮箱
            assert utils.validate_email("") is False
            assert utils.validate_email("invalid") is False
            assert utils.validate_email("@domain.com") is False
            assert utils.validate_email("user@") is False
        except ImportError as e:
            assert False, f"Utils module not available: {e}"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])