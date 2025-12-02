"""
工具函数和核心模块测试
"""
import pytest
from datetime import datetime, timedelta


class TestPasswordSecurity:
    """密码安全测试"""
    
    def test_bcrypt_hash(self):
        """测试bcrypt哈希"""
        from app.core.security import get_password_hash, verify_password
        
        password = "TestPassword123"
        hashed = get_password_hash(password)
        
        assert hashed != password
        assert len(hashed) > 32  # bcrypt哈希长度大于MD5
        assert verify_password(password, hashed)
        assert not verify_password("WrongPassword", hashed)
    
    def test_md5_hash(self):
        """测试MD5哈希（兼容旧系统）"""
        from app.core.security import get_md5_hash, verify_password
        
        password = "TestPassword123"
        md5_hash = get_md5_hash(password)
        
        assert len(md5_hash) == 32  # MD5长度为32
        assert verify_password(password, md5_hash)
    
    def test_is_md5_password(self):
        """测试MD5密码检测"""
        from app.core.security import is_md5_password, get_md5_hash, get_password_hash
        
        md5_hash = get_md5_hash("password")
        bcrypt_hash = get_password_hash("password")
        
        assert is_md5_password(md5_hash)
        assert not is_md5_password(bcrypt_hash)


class TestJWTToken:
    """JWT Token测试"""
    
    def test_create_access_token(self):
        """测试创建访问令牌"""
        from app.core.security import create_access_token, decode_token
        
        token = create_access_token(data={"sub": "123"})
        payload = decode_token(token)
        
        assert payload is not None
        assert payload["sub"] == "123"
        assert payload["type"] == "access"
    
    def test_create_refresh_token(self):
        """测试创建刷新令牌"""
        from app.core.security import create_refresh_token, decode_token
        
        token = create_refresh_token(data={"sub": "123"})
        payload = decode_token(token)
        
        assert payload is not None
        assert payload["sub"] == "123"
        assert payload["type"] == "refresh"
    
    def test_decode_invalid_token(self):
        """测试解码无效令牌"""
        from app.core.security import decode_token
        
        result = decode_token("invalid_token")
        assert result is None


class TestCaptcha:
    """验证码测试"""
    
    def test_generate_code(self):
        """测试生成验证码"""
        from app.api.captcha import generate_code
        
        code = generate_code(4)
        assert len(code) == 4
        assert code.isdigit()
    
    def test_validate_captcha_expired(self):
        """测试验证过期验证码"""
        from app.api.captcha import validate_captcha
        
        valid, error = validate_captcha("nonexistent_id", "1234")
        assert not valid
        assert "过期" in error


class TestRateLimiter:
    """限流器测试"""
    
    def test_rate_limiter_allows_requests(self):
        """测试限流器允许请求"""
        from app.core.rate_limit import RateLimiter
        
        limiter = RateLimiter()
        allowed, remaining = limiter.is_allowed("test_key", max_requests=5, window_seconds=60)
        
        assert allowed
        assert remaining == 4
    
    def test_rate_limiter_blocks_excess_requests(self):
        """测试限流器阻止超额请求"""
        from app.core.rate_limit import RateLimiter
        
        limiter = RateLimiter()
        
        # 发送5个请求
        for i in range(5):
            limiter.is_allowed("block_test", max_requests=5, window_seconds=60)
        
        # 第6个请求应该被阻止
        allowed, remaining = limiter.is_allowed("block_test", max_requests=5, window_seconds=60)
        assert not allowed
        assert remaining == 0


class TestExceptions:
    """自定义异常测试"""
    
    def test_app_exception(self):
        """测试应用异常"""
        from app.core.exceptions import AppException
        
        exc = AppException(code=400, message="测试错误", detail={"field": "test"})
        assert exc.code == 400
        assert exc.message == "测试错误"
        assert exc.detail["field"] == "test"
    
    def test_not_found_exception(self):
        """测试404异常"""
        from app.core.exceptions import NotFoundException
        
        exc = NotFoundException("用户不存在")
        assert exc.code == 404
        assert exc.message == "用户不存在"
    
    def test_validation_exception(self):
        """测试验证异常"""
        from app.core.exceptions import ValidationException
        
        exc = ValidationException(detail=["字段A不能为空", "字段B格式错误"])
        assert exc.code == 422
        assert len(exc.detail) == 2


class TestLogger:
    """日志测试"""
    
    def test_log_functions_no_error(self):
        """测试日志函数不抛出错误"""
        from app.core.logger import (
            log_info, log_error, log_warning,
            log_user_action, log_auth_event, log_db_operation
        )
        
        # 这些函数调用不应该抛出异常
        log_info("测试信息", {"key": "value"})
        log_error("测试错误", {"error": "test"})
        log_warning("测试警告", {"warn": "test"})
        log_user_action(1, "测试操作", "target")
        log_auth_event("login", username="test", success=True)
        log_db_operation("INSERT", "users", record_id=1)
