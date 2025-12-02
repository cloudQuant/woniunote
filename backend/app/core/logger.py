"""
日志系统配置
- INFO日志：记录正常操作
- ERROR日志：记录错误信息
- WARNING日志：记录警告信息
- 支持结构化日志输出（JSON格式）
"""
import os
import json
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
from typing import Any, Dict, Optional

# 日志目录
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

# 日志格式
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
JSON_LOG_FORMAT = '%(message)s'
DATE_FORMAT = '%Y-%m-%d %H:%M:%S'


class StructuredLogFormatter(logging.Formatter):
    """结构化日志格式化器（JSON格式）"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # 添加额外数据
        if hasattr(record, 'extra_data') and record.extra_data:
            log_data["data"] = record.extra_data
        
        # 添加异常信息
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_data, ensure_ascii=False, default=str)

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


def log_info(message: str, extra: Optional[Dict[str, Any]] = None):
    """记录INFO日志"""
    record = info_logger.makeRecord(
        info_logger.name, logging.INFO, "", 0, message, (), None
    )
    record.extra_data = extra
    info_logger.handle(record)


def log_error(message: str, extra: Optional[Dict[str, Any]] = None):
    """记录ERROR日志"""
    record = error_logger.makeRecord(
        error_logger.name, logging.ERROR, "", 0, message, (), None
    )
    record.extra_data = extra
    error_logger.handle(record)


def log_warning(message: str, extra: Optional[Dict[str, Any]] = None):
    """记录WARNING日志"""
    record = warning_logger.makeRecord(
        warning_logger.name, logging.WARNING, "", 0, message, (), None
    )
    record.extra_data = extra
    warning_logger.handle(record)


def log_request(method: str, path: str, status_code: int, duration_ms: float, user_id: int = None):
    """记录HTTP请求日志"""
    log_info(f"HTTP {method} {path} - {status_code} - {duration_ms:.2f}ms", {
        "method": method,
        "path": path,
        "status_code": status_code,
        "duration_ms": round(duration_ms, 2),
        "user_id": user_id
    })


# ==================== 业务日志函数 ====================

def log_user_action(user_id: int, action: str, target: str = None, detail: Dict = None):
    """记录用户操作日志"""
    log_info(f"用户操作: {action}", {
        "user_id": user_id,
        "action": action,
        "target": target,
        **(detail or {})
    })


def log_auth_event(event: str, username: str = None, user_id: int = None, success: bool = True, reason: str = None):
    """记录认证事件日志"""
    data = {
        "event": event,
        "username": username,
        "user_id": user_id,
        "success": success
    }
    if reason:
        data["reason"] = reason
    
    if success:
        log_info(f"认证事件: {event}", data)
    else:
        log_warning(f"认证失败: {event}", data)


def log_db_operation(operation: str, table: str, record_id: Any = None, user_id: int = None):
    """记录数据库操作日志"""
    log_info(f"数据库操作: {operation} {table}", {
        "operation": operation,
        "table": table,
        "record_id": record_id,
        "user_id": user_id
    })


def log_api_error(path: str, method: str, error_type: str, message: str, user_id: int = None):
    """记录API错误日志"""
    log_error(f"API错误: {method} {path}", {
        "path": path,
        "method": method,
        "error_type": error_type,
        "message": message,
        "user_id": user_id
    })
