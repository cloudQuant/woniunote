import os
from datetime import timedelta

class Config:
    SECRET_KEY = os.urandom(24)
    DEBUG = False
    TESTING = False
    
    # 数据库配置
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_POOL_SIZE = 10
    SQLALCHEMY_POOL_TIMEOUT = 30
    SQLALCHEMY_POOL_RECYCLE = 1800
    SQLALCHEMY_MAX_OVERFLOW = 20
    
    # 会话配置
    SESSION_COOKIE_SECURE = False  # 修改为False，允许HTTP
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_NAME = 'woniunote_session'  # 添加明确的session名称
    SESSION_PERMANENT = True
    PERMANENT_SESSION_LIFETIME = timedelta(days=1)
    
    # CSRF保护
    WTF_CSRF_ENABLED = True
    WTF_CSRF_SECRET_KEY = os.urandom(32)
    
    # 缓存配置
    CACHE_TYPE = 'redis'
    CACHE_DEFAULT_TIMEOUT = 300

class DevelopmentConfig(Config):
    DEBUG = True
    SESSION_COOKIE_SECURE = False  # 开发环境使用HTTP
    
class ProductionConfig(Config):
    # 生产环境特定配置
    SESSION_COOKIE_SECURE = True  # 生产环境使用HTTPS
    
class TestingConfig(Config):
    TESTING = True
    SESSION_COOKIE_SECURE = False  # 测试环境使用HTTP

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
