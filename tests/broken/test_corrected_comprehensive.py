#!/usr/bin/env python3
"""
测试修正后的综合功能
"""
import pytest
import sys
import os

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

class TestCorrectedComprehensive:
    """修正后的综合测试"""
    
    def test_basic(self):
        """基本测试占位符"""
        pass
    
    def test_email_validation(self):
        """测试邮箱验证功能"""
        # 使用直接路径导入
        import sys
        sys.path.insert(0, '/home/yun/Documents/woniunote/woniunote/common')
        try:
            import utils
            
            # Valid emails
            assert utils.validate_email("test@example.com") is True
            assert utils.validate_email("user.name@domain.co.uk") is True
            
            # Invalid emails - updated to match actual behavior
            assert utils.validate_email("user..name@domain.com") is False  # Double dots not allowed
            assert utils.validate_email("user@domain..com") is False  # Double dots not allowed
            assert utils.validate_email("user name@domain.com") is False  # Spaces not allowed
            assert utils.validate_email("") is False
            assert utils.validate_email(None) is False
        except ImportError as e:
            assert False, f"Cannot import validate_email: {e}"
    
    def test_gen_email_code(self):
        """Test email code generation"""
        # 使用直接路径导入
        import sys
        sys.path.insert(0, '/home/yun/Documents/woniunote/woniunote/common')
        try:
            import utils
            
            # Test default length
            code = utils.gen_email_code()
            assert len(code) == 6
            assert code.isalnum()
            
            # Test custom length
            code_4 = utils.gen_email_code(4)
            assert len(code_4) == 4
            assert code_4.isalnum()
            
            # Test uniqueness
            codes = [utils.gen_email_code() for _ in range(10)]
            assert len(set(codes)) >= 8  # Should be mostly unique
        except ImportError as e:
            assert False, f"gen_email_code not available: {e}"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])