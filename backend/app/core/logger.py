"""
日志系统配置
- INFO日志：记录正常操作
- ERROR日志：记录错误信息
- WARNING日志：记录警告信息
"""
import os
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime

# 日志目录
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

# 日志格式
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

def get_log_filename(log_type: str) -> str:
    """获取日志文件名"""
    today = datetime.now().strftime('%Y-%m-%d')
    return os.path.join(LOG_DIR, f'{log_type}_{today}.log')


def setup_logger(name: str, log_type: str, level: int = logging.INFO) -> logging.Logger:
    """设置日志记录器"""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # 避免重复添加handler
    if logger.handlers:
        return logger
    
    # 文件处理器
    file_handler = RotatingFileHandler(
        get_log_filename(log_type),
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
    file_handler.setLevel(level)
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
    console_handler.setLevel(level)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger


# 创建各类日志记录器
info_logger = setup_logger('woniunote.info', 'info', logging.INFO)
error_logger = setup_logger('woniunote.error', 'error', logging.ERROR)
warning_logger = setup_logger('woniunote.warning', 'warning', logging.WARNING)


def log_info(message: str, extra: dict = None):
    """记录INFO日志"""
    if extra:
        info_logger.info(f"{message} | {extra}")
    else:
        info_logger.info(message)


def log_error(message: str, error: Exception = None, extra: dict = None):
    """记录ERROR日志"""
    error_msg = message
    if error:
        error_msg += f" | Error: {type(error).__name__}: {str(error)}"
    if extra:
        error_msg += f" | {extra}"
    error_logger.error(error_msg, exc_info=error is not None)


def log_warning(message: str, extra: dict = None):
    """记录WARNING日志"""
    if extra:
        warning_logger.warning(f"{message} | {extra}")
    else:
        warning_logger.warning(message)


def log_request(method: str, path: str, status_code: int, duration_ms: float, user_id: int = None):
    """记录HTTP请求日志"""
    log_info(f"HTTP {method} {path} - {status_code} - {duration_ms:.2f}ms", 
             {"user_id": user_id} if user_id else None)
