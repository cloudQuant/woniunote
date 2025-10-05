'''
WoniuNote 配置文件
统一管理应用配置项
'''
import os
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'mysql+pymysql://woniunote_user:woniunote_pass@localhost:3306/woniunote'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
        'pool_timeout': 20,
        'max_overflow': 0
    }
    REDIS_HOST = os.environ.get('REDIS_HOST') or 'localhost'
    REDIS_PORT = int(os.environ.get('REDIS_PORT') or 6379)
    REDIS_DB = int(os.environ.get('REDIS_DB') or 0)
    REDIS_PASSWORD = os.environ.get('REDIS_PASSWORD')
    SESSION_TYPE = 'filesystem'
    SESSION_FILE_DIR = BASE_DIR / 'woniunote' / 'sessions'
    SESSION_PERMANENT = False
    SESSION_USE_SIGNER = True
    SESSION_FILE_THRESHOLD = 500
    SESSION_FILE_MODE = 0o600
    UPLOAD_FOLDER = BASE_DIR / 'woniunote' / 'resource' / 'upload'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    CACHE_TYPE = 'redis'
    CACHE_DEFAULT_TIMEOUT = 300
    CACHE_KEY_PREFIX = 'woniunote:'
    LOG_LEVEL = 'INFO'
    LOG_DIR = BASE_DIR / 'logs'
    LOG_MAX_BYTES = 10 * 1024 * 1024
    LOG_BACKUP_COUNT = 5
    CSRF_ENABLED = True
    CSRF_TOKEN_TIMEOUT = 3600
    WTF_CSRF_TIME_LIMIT = 3600
    RATELIMIT_STORAGE_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
    RATELIMIT_DEFAULT = "100 per hour"
    RATELIMIT_RULES = {
        'api': {'type': 'token_bucket', 'capacity': 1000, 'refill_rate': 200, 'refill_period': 3600},
        'upload': {'type': 'token_bucket', 'capacity': 100, 'refill_rate': 50, 'refill_period': 3600},
        'strict': {'type': 'sliding_window', 'max_requests': 10, 'window_size': 60},
        'moderate': {'type': 'sliding_window', 'max_requests': 50, 'window_size': 60},
        'lenient': {'type': 'sliding_window', 'max_requests': 100, 'window_size': 60}
    }
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    
    @staticmethod
    def init_app(app):
        Config.SESSION_FILE_DIR.mkdir(parents=True, exist_ok=True)
        Config.UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
        Config.LOG_DIR.mkdir(parents=True, exist_ok=True)

class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or \
        'mysql+pymysql://woniunote_user:woniunote_pass@localhost:3306/woniunote'
    LOG_LEVEL = 'DEBUG'
    WTF_CSRF_ENABLED = False
    
class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URL') or \
        'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    CACHE_TYPE = 'simple'

class ProductionConfig(Config):
    DEBUG = False
    SECRET_KEY = os.environ.get('SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    LOG_LEVEL = 'WARNING'
    
    @classmethod
    def validate_environment(cls):
        if not cls.SECRET_KEY:
            raise ValueError("生产环境必须设置SECRET_KEY环境变量")
        if not cls.SQLALCHEMY_DATABASE_URI:
            raise ValueError("生产环境必须设置DATABASE_URL环境变量")
    
    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        import logging
        from logging.handlers import RotatingFileHandler
        if not app.debug:
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

config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
