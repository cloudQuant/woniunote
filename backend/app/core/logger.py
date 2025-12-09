"""
日志系统配置模块

本模块配置了应用的日志系统，支持控制台输出和文件记录。
主要功能包括：
- INFO/ERROR/WARNING 等级日志记录
- 结构化日志输出 (JSON 格式)
- 自动日志轮转 (RotatingFileHandler)
- 业务日志封装 (用户操作、认证事件、数据库操作等)
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
    """
    结构化日志格式化器
    
    将日志记录格式化为 JSON 字符串，便于日志收集和分析。
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """
        格式化日志记录
        
        Args:
            record: 日志记录对象
            
        Returns:
            str: JSON 格式的日志字符串
        """
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
    """
    获取日志文件名
    
    Args:
        log_type: 日志类型 (如 info, error)
        
    Returns:
        str: 完整的日志文件路径
    """
    today = datetime.now().strftime('%Y-%m-%d')
    return os.path.join(LOG_DIR, f'{log_type}_{today}.log')


def setup_logger(name: str, log_type: str, level: int = logging.INFO) -> logging.Logger:
    """
    设置日志记录器
    
    配置日志记录器，添加文件处理器和控制台处理器。
    
    Args:
        name: 记录器名称
        log_type: 日志类型 (用于生成文件名)
        level: 日志级别
        
    Returns:
        logging.Logger: 配置好的日志记录器实例
    """
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
access_logger = setup_logger('woniunote.access', 'access', logging.INFO)  # 文章访问日志


def log_info(message: str, extra: Optional[Dict[str, Any]] = None):
    """
    记录 INFO 级别日志
    
    Args:
        message: 日志消息
        extra: 额外数据字典
    """
    record = info_logger.makeRecord(
        info_logger.name, logging.INFO, "", 0, message, (), None
    )
    record.extra_data = extra
    info_logger.handle(record)


def log_error(message: str, extra: Optional[Dict[str, Any]] = None):
    """
    记录 ERROR 级别日志
    
    Args:
        message: 日志消息
        extra: 额外数据字典
    """
    record = error_logger.makeRecord(
        error_logger.name, logging.ERROR, "", 0, message, (), None
    )
    record.extra_data = extra
    error_logger.handle(record)


def log_warning(message: str, extra: Optional[Dict[str, Any]] = None):
    """
    记录 WARNING 级别日志
    
    Args:
        message: 日志消息
        extra: 额外数据字典
    """
    record = warning_logger.makeRecord(
        warning_logger.name, logging.WARNING, "", 0, message, (), None
    )
    record.extra_data = extra
    warning_logger.handle(record)


def log_request(method: str, path: str, status_code: int, duration_ms: float, user_id: int = None):
    """
    记录 HTTP 请求日志
    
    Args:
        method: HTTP 方法
        path: 请求路径
        status_code: 响应状态码
        duration_ms: 请求耗时 (毫秒)
        user_id: 用户ID (可选)
    """
    log_info(f"HTTP {method} {path} - {status_code} - {duration_ms:.2f}ms", {
        "method": method,
        "path": path,
        "status_code": status_code,
        "duration_ms": round(duration_ms, 2),
        "user_id": user_id
    })


# ==================== 业务日志函数 ====================

def log_user_action(user_id: int, action: str, target: str = None, detail: Dict = None):
    """
    记录用户操作日志
    
    Args:
        user_id: 用户ID
        action: 操作名称
        target: 操作目标 (可选)
        detail: 详细信息 (可选)
    """
    log_info(f"用户操作: {action}", {
        "user_id": user_id,
        "action": action,
        "target": target,
        **(detail or {})
    })


def log_auth_event(event: str, username: str = None, user_id: int = None, success: bool = True, reason: str = None):
    """
    记录认证事件日志
    
    Args:
        event: 事件名称 (如 login, register)
        username: 用户名
        user_id: 用户ID
        success: 是否成功
        reason: 失败原因 (可选)
    """
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
    """
    记录数据库操作日志
    
    Args:
        operation: 操作类型 (如 create, update, delete)
        table: 表名
        record_id: 记录ID
        user_id: 操作用户ID
    """
    log_info(f"数据库操作: {operation} {table}", {
        "operation": operation,
        "table": table,
        "record_id": record_id,
        "user_id": user_id
    })


def log_api_error(path: str, method: str, error_type: str, message: str, user_id: int = None):
    """
    记录 API 错误日志
    
    Args:
        path: 请求路径
        method: HTTP 方法
        error_type: 错误类型
        message: 错误消息
        user_id: 用户ID
    """
    log_error(f"API错误: {method} {path}", {
        "path": path,
        "method": method,
        "error_type": error_type,
        "message": message,
        "user_id": user_id
    })


# ==================== 文章访问日志 ====================

def log_article_access(
    ip_address: str,
    article_id: int,
    article_title: str,
    article_url: str,
    user_id: Optional[int] = None,
    user_agent: Optional[str] = None,
    referer: Optional[str] = None
):
    """
    记录文章访问日志
    
    Args:
        ip_address: 访问者IP地址
        article_id: 文章ID
        article_title: 文章标题
        article_url: 文章链接
        user_id: 用户ID（已登录用户）
        user_agent: 浏览器User-Agent
        referer: 来源页面
    """
    access_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    log_data = {
        "access_time": access_time,
        "ip_address": ip_address,
        "article_id": article_id,
        "article_title": article_title,
        "article_url": article_url,
        "user_id": user_id,
        "user_agent": user_agent,
        "referer": referer
    }
    
    # 写入访问日志
    record = access_logger.makeRecord(
        access_logger.name, logging.INFO, "", 0,
        f"文章访问: [{ip_address}] {article_title} ({article_url})",
        (), None
    )
    record.extra_data = log_data
    access_logger.handle(record)
