"""
WoniuNote 配置文件
统一管理应用配置项
"""
import os
from pathlib import Path

# 项目根目录
BASE_DIR = Path(__file__).parent.parent

class Config:
    """基础配置"""
    
    # Flask配置
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # 数据库配置
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'mysql+pymysql://woniunote_user:woniunote_pass@localhost:3306/woniunote'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
        'pool_timeout': 20,
        'max_overflow': 0
    }
    
    # Redis配置
    REDIS_HOST = os.environ.get('REDIS_HOST') or 'localhost'
    REDIS_PORT = int(os.environ.get('REDIS_PORT') or 6379)
    REDIS_DB = int(os.environ.get('REDIS_DB') or 0)
    REDIS_PASSWORD = os.environ.get('REDIS_PASSWORD')
    
    # 会话配置
    SESSION_TYPE = 'filesystem'
    SESSION_FILE_DIR = BASE_DIR / 'woniunote' / 'sessions'
    SESSION_PERMANENT = False
    SESSION_USE_SIGNER = True
    SESSION_FILE_THRESHOLD = 500
    SESSION_FILE_MODE = 0o600
    
    # 上传配置
    UPLOAD_FOLDER = BASE_DIR / 'woniunote' / 'resource' / 'upload'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    
    # 缓存配置
    CACHE_TYPE = 'redis'
    CACHE_DEFAULT_TIMEOUT = 300  # 5分钟
    CACHE_KEY_PREFIX = 'woniunote:'
    
    # 日志配置
    LOG_LEVEL = 'INFO'
    LOG_DIR = BASE_DIR / 'logs'
    LOG_MAX_BYTES = 10 * 1024 * 1024  # 10MB
    LOG_BACKUP_COUNT = 5
    
    # 安全配置
    CSRF_ENABLED = True
    CSRF_TOKEN_TIMEOUT = 3600  # 1小时
    WTF_CSRF_TIME_LIMIT = 3600
    
    # 限流配置
    RATELIMIT_STORAGE_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
    RATELIMIT_DEFAULT = "100 per hour"
    
    # 邮件配置
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    
    @staticmethod
    def init_app(app):
        """初始化应用配置"""
        # 确保必要目录存在
        Config.SESSION_FILE_DIR.mkdir(parents=True, exist_ok=True)
        Config.UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
        Config.LOG_DIR.mkdir(parents=True, exist_ok=True)

class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or \
        'mysql+pymysql://woniunote_user:woniunote_pass@localhost:3306/woniunote'
    LOG_LEVEL = 'DEBUG'
    
    # 开发环境下禁用一些安全特性以便调试
    WTF_CSRF_ENABLED = False
    
class TestingConfig(Config):
    """测试环境配置"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URL') or \
        'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    
    # 测试环境使用内存缓存
    CACHE_TYPE = 'simple'

class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False
    
    # 生产环境必须使用环境变量设置敏感信息
    SECRET_KEY = os.environ.get('SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    
    if not SECRET_KEY:
        raise ValueError("生产环境必须设置SECRET_KEY环境变量")
    
    if not SQLALCHEMY_DATABASE_URI:
        raise ValueError("生产环境必须设置DATABASE_URL环境变量")
    
    # 生产环境日志级别
    LOG_LEVEL = 'WARNING'
    
    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        
        # 生产环境特定初始化
        import logging
        from logging.handlers import RotatingFileHandler
        
        if not app.debug:
            # 设置文件日志
            file_handler = RotatingFileHandler(
                cls.LOG_DIR / 'woniunote.log',
                maxBytes=cls.LOG_MAX_BYTES,
                backupCount=cls.LOG_BACKUP_COUNT
            )
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
            ))
            file_handler.setLevel(logging.INFO)
            app.logger.addHandler(file_handler)
            
            app.logger.setLevel(logging.INFO)
            app.logger.info('WoniuNote 启动')

# 配置映射
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}