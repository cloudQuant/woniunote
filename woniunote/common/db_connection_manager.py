"""
数据库连接管理器
提供安全的数据库连接管理，防止连接泄露和资源浪费
"""
import time
import threading
from contextlib import contextmanager
from typing import Optional, Generator, Dict, Any
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.exc import SQLAlchemyError, DisconnectionError
from sqlalchemy import create_engine, MetaData
from woniunote.common.simple_logger import get_simple_logger

logger = get_simple_logger('db_connection_manager')

class DatabaseConnectionManager:
    """数据库连接管理器"""
    
    def __init__(self, database_url: str = None, pool_size: int = 10, 
                 max_overflow: int = 20, pool_timeout: int = 30):
        """
        初始化数据库连接管理器
        
        Args:
            database_url: 数据库连接URL
            pool_size: 连接池大小
            max_overflow: 最大溢出连接数
            pool_timeout: 连接池获取连接超时时间
        """
        self.database_url = database_url
        self.engine = None
        self.session_factory = None
        self.metadata = None
        self._lock = threading.RLock()
        self._connection_stats = {
            'created_sessions': 0,
            'closed_sessions': 0,
            'active_sessions': 0,
            'failed_sessions': 0
        }
        
        # 连接池配置
        self.pool_config = {
            'pool_size': pool_size,
            'max_overflow': max_overflow,
            'pool_timeout': pool_timeout,
            'pool_recycle': 3600,  # 1小时回收连接
            'pool_pre_ping': True  # 连接前ping检查
        }
        
        self._initialize_engine()
    
    def _initialize_engine(self):
        """初始化数据库引擎"""
        try:
            if not self.database_url:
                # 从配置中获取数据库URL
                from woniunote.common.database import SQLALCHEMY_DATABASE_URI
                self.database_url = SQLALCHEMY_DATABASE_URI
            
            self.engine = create_engine(
                self.database_url,
                **self.pool_config,
                echo=False  # 生产环境关闭SQL回显
            )
            
            self.session_factory = sessionmaker(bind=self.engine)
            self.metadata = MetaData()
            self.metadata.bind = self.engine
            
            logger.info("数据库连接管理器初始化成功", {
                'pool_size': self.pool_config['pool_size'],
                'max_overflow': self.pool_config['max_overflow'],
                'pool_timeout': self.pool_config['pool_timeout']
            })
            
        except Exception as e:
            logger.error(f"数据库连接管理器初始化失败: {e}")
            raise
    
    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """
        获取数据库会话的上下文管理器
        
        Yields:
            Session: 数据库会话
        """
        session = None
        session_id = None
        
        try:
            session = self.session_factory()
            session_id = id(session)
            
            with self._lock:
                self._connection_stats['created_sessions'] += 1
                self._connection_stats['active_sessions'] += 1
            
            logger.debug(f"创建数据库会话: {session_id}")
            
            yield session
            
            # 正常完成时提交事务
            session.commit()
            logger.debug(f"会话事务提交成功: {session_id}")
            
        except SQLAlchemyError as e:
            # 数据库相关异常
            if session:
                try:
                    session.rollback()
                    logger.warning(f"会话事务回滚: {session_id}, 原因: {e}")
                except Exception as rollback_error:
                    logger.error(f"会话回滚失败: {session_id}, 错误: {rollback_error}")
            
            with self._lock:
                self._connection_stats['failed_sessions'] += 1
            
            raise
            
        except Exception as e:
            # 其他异常
            if session:
                try:
                    session.rollback()
                    logger.warning(f"会话事务回滚: {session_id}, 原因: {e}")
                except Exception as rollback_error:
                    logger.error(f"会话回滚失败: {session_id}, 错误: {rollback_error}")
            
            with self._lock:
                self._connection_stats['failed_sessions'] += 1
            
            raise
            
        finally:
            # 确保会话被正确关闭
            if session:
                try:
                    session.close()
                    logger.debug(f"会话关闭成功: {session_id}")
                    
                    with self._lock:
                        self._connection_stats['closed_sessions'] += 1
                        self._connection_stats['active_sessions'] -= 1
                        
                except Exception as e:
                    logger.error(f"会话关闭失败: {session_id}, 错误: {e}")
    
    @contextmanager
    def get_read_only_session(self) -> Generator[Session, None, None]:
        """
        获取只读数据库会话
        
        Yields:
            Session: 只读数据库会话
        """
        with self.get_session() as session:
            # 设置为只读模式
            session.connection(execution_options={"isolation_level": "READ_COMMITTED"})
            yield session
            # 只读会话不需要提交
            session.rollback()
    
    def execute_query(self, query: str, params: Dict[str, Any] = None) -> Any:
        """
        执行原生SQL查询
        
        Args:
            query: SQL查询语句
            params: 查询参数
            
        Returns:
            查询结果
        """
        with self.get_session() as session:
            try:
                if params:
                    result = session.execute(query, params)
                else:
                    result = session.execute(query)
                
                return result.fetchall()
                
            except Exception as e:
                logger.error(f"SQL查询执行失败: {e}", {
                    'query': query[:100] if query else None,
                    'params': str(params)[:100] if params else None
                })
                raise
    
    def test_connection(self) -> bool:
        """
        测试数据库连接
        
        Returns:
            bool: 连接是否正常
        """
        try:
            with self.get_session() as session:
                session.execute("SELECT 1")
            
            logger.info("数据库连接测试成功")
            return True
            
        except Exception as e:
            logger.error(f"数据库连接测试失败: {e}")
            return False
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """
        获取连接统计信息
        
        Returns:
            Dict: 连接统计信息
        """
        with self._lock:
            stats = self._connection_stats.copy()
        
        # 添加连接池信息
        if self.engine and hasattr(self.engine.pool, 'size'):
            stats.update({
                'pool_size': self.engine.pool.size(),
                'checked_in': self.engine.pool.checkedin(),
                'checked_out': self.engine.pool.checkedout(),
                'overflow': self.engine.pool.overflow(),
                'invalid': self.engine.pool.invalid()
            })
        
        return stats
    
    def close_all_connections(self):
        """关闭所有连接"""
        try:
            if self.engine:
                self.engine.dispose()
                logger.info("所有数据库连接已关闭")
                
        except Exception as e:
            logger.error(f"关闭数据库连接失败: {e}")
    
    def health_check(self) -> Dict[str, Any]:
        """
        健康检查
        
        Returns:
            Dict: 健康检查结果
        """
        health_info = {
            'status': 'unknown',
            'timestamp': time.time(),
            'connection_test': False,
            'stats': self.get_connection_stats()
        }
        
        try:
            # 测试连接
            health_info['connection_test'] = self.test_connection()
            
            # 检查活跃会话数是否过多
            active_sessions = health_info['stats'].get('active_sessions', 0)
            if active_sessions > self.pool_config['pool_size'] * 2:
                health_info['status'] = 'warning'
                health_info['warning'] = f'活跃会话数过多: {active_sessions}'
            elif health_info['connection_test']:
                health_info['status'] = 'healthy'
            else:
                health_info['status'] = 'unhealthy'
                
        except Exception as e:
            health_info['status'] = 'error'
            health_info['error'] = str(e)
        
        return health_info

# 全局连接管理器实例
_connection_manager = None
_manager_lock = threading.Lock()

def get_connection_manager() -> DatabaseConnectionManager:
    """
    获取全局连接管理器实例（单例模式）
    
    Returns:
        DatabaseConnectionManager: 连接管理器实例
    """
    global _connection_manager
    
    if _connection_manager is None:
        with _manager_lock:
            if _connection_manager is None:
                _connection_manager = DatabaseConnectionManager()
    
    return _connection_manager

def initialize_connection_manager(database_url: str = None, **kwargs) -> DatabaseConnectionManager:
    """
    初始化连接管理器
    
    Args:
        database_url: 数据库连接URL
        **kwargs: 其他配置参数
        
    Returns:
        DatabaseConnectionManager: 连接管理器实例
    """
    global _connection_manager
    
    with _manager_lock:
        _connection_manager = DatabaseConnectionManager(database_url, **kwargs)
    
    return _connection_manager

# 便捷函数
def get_db_session():
    """便捷函数：获取数据库会话"""
    return get_connection_manager().get_session()

def get_read_only_session():
    """便捷函数：获取只读数据库会话"""
    return get_connection_manager().get_read_only_session()

def execute_sql(query: str, params: Dict[str, Any] = None):
    """便捷函数：执行SQL查询"""
    return get_connection_manager().execute_query(query, params)

def test_db_connection() -> bool:
    """便捷函数：测试数据库连接"""
    return get_connection_manager().test_connection()

def get_db_stats() -> Dict[str, Any]:
    """便捷函数：获取数据库连接统计"""
    return get_connection_manager().get_connection_stats()

def close_all_db_connections():
    """便捷函数：关闭所有数据库连接"""
    return get_connection_manager().close_all_connections()