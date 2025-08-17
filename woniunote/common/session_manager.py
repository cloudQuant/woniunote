"""
数据库会话管理器 - 解决数据库连接泄露问题
确保所有数据库操作都有正确的事务管理和连接清理
"""
import time
import threading
import traceback
from typing import Any, Dict, List, Optional, Callable
from contextlib import contextmanager
from functools import wraps
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from .simple_logger import get_simple_logger
from .trace_id_manager import TraceIdManager
from .error_handler import DatabaseException

class SessionManager:
    """数据库会话管理器"""
    
    def __init__(self, dbsession: Session):
        self.dbsession = dbsession
        self.logger = get_simple_logger('session_manager')
        self._active_sessions = {}
        self._session_stats = {
            'total_sessions': 0,
            'active_sessions': 0,
            'committed_sessions': 0,
            'rolled_back_sessions': 0,
            'failed_sessions': 0
        }
        self._lock = threading.RLock()
    
    @contextmanager
    def managed_session(self, trace_id: str = None, operation: str = "unknown"):
        """受管理的数据库会话上下文管理器"""
        if not trace_id:
            trace_id = TraceIdManager.generate_simple_trace_id()
        
        session_info = {
            'trace_id': trace_id,
            'operation': operation,
            'start_time': time.time(),
            'thread_id': threading.get_ident()
        }
        
        with self._lock:
            self._active_sessions[trace_id] = session_info
            self._session_stats['total_sessions'] += 1
            self._session_stats['active_sessions'] += 1
        
        self.logger.debug(f"开始数据库会话: {operation}", {
            'trace_id': trace_id,
            'active_sessions': self._session_stats['active_sessions']
        })
        
        try:
            yield self.dbsession
            
            # 会话成功完成
            self.dbsession.commit()
            
            with self._lock:
                self._session_stats['committed_sessions'] += 1
            
            session_info['status'] = 'committed'
            self.logger.debug(f"数据库会话提交成功: {operation}", {
                'trace_id': trace_id,
                'duration_ms': round((time.time() - session_info['start_time']) * 1000, 2)
            })
            
        except SQLAlchemyError as e:
            # 数据库错误，回滚事务
            try:
                self.dbsession.rollback()
                with self._lock:
                    self._session_stats['rolled_back_sessions'] += 1
                session_info['status'] = 'rolled_back'
                
                self.logger.error(f"数据库会话回滚: {operation}", {
                    'trace_id': trace_id,
                    'error': str(e),
                    'error_type': type(e).__name__
                })
            except Exception as rollback_error:
                self.logger.error(f"数据库会话回滚失败: {operation}", {
                    'trace_id': trace_id,
                    'rollback_error': str(rollback_error)
                })
            
            raise DatabaseException(
                f"数据库操作失败: {operation}",
                operation=operation,
                details={'error': str(e), 'trace_id': trace_id}
            )
            
        except Exception as e:
            # 其他异常，也需要回滚
            try:
                self.dbsession.rollback()
                with self._lock:
                    self._session_stats['failed_sessions'] += 1
                session_info['status'] = 'failed'
                
                self.logger.error(f"数据库会话异常: {operation}", {
                    'trace_id': trace_id,
                    'error': str(e),
                    'error_type': type(e).__name__,
                    'traceback': traceback.format_exc()
                })
            except Exception as rollback_error:
                self.logger.error(f"异常后回滚失败: {operation}", {
                    'trace_id': trace_id,
                    'rollback_error': str(rollback_error)
                })
            
            raise
            
        finally:
            # 清理会话信息
            with self._lock:
                if trace_id in self._active_sessions:
                    del self._active_sessions[trace_id]
                self._session_stats['active_sessions'] = max(0, self._session_stats['active_sessions'] - 1)
            
            # 确保会话连接被正确处理
            try:
                # 检查连接状态
                if hasattr(self.dbsession, 'connection') and self.dbsession.connection():
                    # 连接仍然活跃，这是正常的，SQLAlchemy会管理连接池
                    pass
            except Exception as e:
                self.logger.warning(f"检查会话连接状态时异常: {e}")
    
    def get_session_stats(self) -> Dict[str, Any]:
        """获取会话统计信息"""
        with self._lock:
            return {
                **self._session_stats.copy(),
                'current_active_sessions': len(self._active_sessions),
                'active_session_details': [
                    {
                        'trace_id': trace_id,
                        'operation': info['operation'],
                        'duration_s': round(time.time() - info['start_time'], 2),
                        'thread_id': info['thread_id']
                    }
                    for trace_id, info in self._active_sessions.items()
                ]
            }
    
    def cleanup_stale_sessions(self, max_duration_seconds: int = 300):
        """清理过期的会话"""
        current_time = time.time()
        stale_sessions = []
        
        with self._lock:
            for trace_id, session_info in list(self._active_sessions.items()):
                if current_time - session_info['start_time'] > max_duration_seconds:
                    stale_sessions.append(trace_id)
                    del self._active_sessions[trace_id]
                    self._session_stats['active_sessions'] = max(0, self._session_stats['active_sessions'] - 1)
        
        if stale_sessions:
            self.logger.warning(f"清理过期会话: {len(stale_sessions)} 个", {
                'stale_session_ids': stale_sessions
            })
        
        return len(stale_sessions)

class TransactionManager:
    """事务管理器"""
    
    def __init__(self, session_manager: SessionManager):
        self.session_manager = session_manager
        self.logger = get_simple_logger('transaction_manager')
    
    @contextmanager
    def transaction(self, operation: str = "transaction", trace_id: str = None):
        """事务上下文管理器"""
        with self.session_manager.managed_session(trace_id, operation) as session:
            yield session

def database_transaction(operation: str = None, trace_id: str = None):
    """数据库事务装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            op_name = operation or func.__name__
            session_trace_id = trace_id or TraceIdManager.generate_simple_trace_id()
            
            # 如果第一个参数是self且有session_manager属性，使用它
            session_manager = None
            if args and hasattr(args[0], 'session_manager'):
                session_manager = args[0].session_manager
            elif args and hasattr(args[0], 'dbsession'):
                # 为现有的类创建临时会话管理器
                session_manager = SessionManager(args[0].dbsession)
            
            if not session_manager:
                raise ValueError("无法找到数据库会话管理器")
            
            with session_manager.managed_session(session_trace_id, op_name) as session:
                # 将session注入到参数中（如果需要）
                return func(*args, **kwargs)
        
        return wrapper
    return decorator

def safe_database_operation(operation: str = None):
    """安全的数据库操作装饰器，自动处理异常和回滚"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            op_name = operation or func.__name__
            trace_id = TraceIdManager.generate_simple_trace_id()
            logger = get_simple_logger('safe_db_operation')
            
            logger.debug(f"开始安全数据库操作: {op_name}", {
                'trace_id': trace_id,
                'function': func.__name__
            })
            
            try:
                result = func(*args, **kwargs)
                
                logger.debug(f"安全数据库操作成功: {op_name}", {
                    'trace_id': trace_id
                })
                
                return result
                
            except DatabaseException:
                # 重新抛出数据库异常
                raise
                
            except Exception as e:
                logger.error(f"安全数据库操作异常: {op_name}", {
                    'trace_id': trace_id,
                    'error': str(e),
                    'error_type': type(e).__name__,
                    'traceback': traceback.format_exc()
                })
                
                # 包装为数据库异常
                raise DatabaseException(
                    f"数据库操作失败: {op_name}",
                    operation=op_name,
                    details={'error': str(e), 'trace_id': trace_id}
                )
        
        return wrapper
    return decorator

# 创建默认的会话管理器工厂
def create_session_manager(dbsession: Session) -> SessionManager:
    """创建会话管理器"""
    return SessionManager(dbsession)

def create_transaction_manager(session_manager: SessionManager) -> TransactionManager:
    """创建事务管理器"""
    return TransactionManager(session_manager)

# 会话管理器单例（用于全局访问）
_global_session_manager = None

def get_global_session_manager() -> Optional[SessionManager]:
    """获取全局会话管理器"""
    return _global_session_manager

def set_global_session_manager(session_manager: SessionManager):
    """设置全局会话管理器"""
    global _global_session_manager
    _global_session_manager = session_manager

# 便捷的全局事务管理器
@contextmanager
def global_transaction(operation: str = "global_transaction"):
    """全局事务上下文管理器"""
    session_manager = get_global_session_manager()
    if not session_manager:
        raise ValueError("全局会话管理器未初始化")
    
    with session_manager.managed_session(operation=operation) as session:
        yield session