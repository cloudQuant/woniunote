"""
WoniuNote Common Utilities Package

This package contains common utilities and shared functionality for the WoniuNote application.
"""

# Import key modules to make them available at package level
try:
    # 核心模块
    from . import simple_logger
    from . import timer
    from . import utils
    from . import database
    
    # 统一模块（第一阶段整合）
    from . import unified_session
    from . import unified_error_handler
    from . import unified_database_optimizer
    from . import unified_monitoring
    from . import unified_security
    
    # 保留的现有模块（向后兼容）
    from . import cache_utils
    from . import rate_limiter
    from . import async_tasks
    from . import config_manager
    from . import static_optimizer
    from . import redisdb
    from . import todo_database
    from . import card_database
    from . import log_decorator
    
    # 已整合的模块（标记为废弃）
    from . import session_util
    from . import monitoring
    from . import database_optimizer
    from . import security_enhanced
    
except ImportError as e:
    # Handle import errors gracefully during development
    import warnings
    warnings.warn(f"Some common modules could not be imported: {e}")

__all__ = [
    # 核心模块
    'simple_logger',
    'timer', 
    'utils',
    'database',
    
    # 统一模块（推荐使用）
    'unified_session',
    'unified_error_handler', 
    'unified_database_optimizer',
    'unified_monitoring',
    'unified_security',
    
    # 保留的现有模块
    'cache_utils',
    'rate_limiter',
    'async_tasks',
    'config_manager',
    'static_optimizer',
    'redisdb',
    'todo_database',
    'card_database',
    'log_decorator',
    
    # 已整合的模块（向后兼容，但建议迁移到统一模块）
    'session_util',
    'monitoring',
    'database_optimizer', 
    'security_enhanced'
]
