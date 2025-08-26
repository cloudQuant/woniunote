#!/usr/bin/env python3
"""
WoniuNote Common Package
提供各种通用功能和工具
"""

# Import key modules to make them available at package level
try:
    # 统一模块（第一阶段整合）
    from . import unified_session
    from . import unified_error_handler
    from . import unified_database_optimizer
    from . import unified_monitoring
    from . import unified_security
    
    # 统一模块（第二阶段整合）
    from . import unified_cache
    from . import unified_logging
    from . import unified_config
    from . import unified_validator
    from . import unified_utils
    
    # 保留的现有模块（向后兼容）
    from . import rate_limiter
    from . import async_tasks
    from . import static_optimizer
    from . import redisdb
    from . import todo_database
    from . import card_database
    from . import log_decorator
    
except ImportError as e:
    # Handle import errors gracefully during development
    import warnings
    warnings.warn(f"Some common modules could not be imported: {e}")

__all__ = [
    # 统一模块（第一阶段整合，推荐使用）
    'unified_session',
    'unified_error_handler', 
    'unified_database_optimizer',
    'unified_monitoring',
    'unified_security',
    
    # 统一模块（第二阶段整合，推荐使用）
    'unified_cache',
    'unified_logging',
    'unified_config',
    'unified_validator',
    'unified_utils',
    
    # 保留的现有模块
    'rate_limiter',
    'async_tasks',
    'static_optimizer',
    'redisdb',
    'todo_database',
    'card_database',
    'log_decorator'
]
