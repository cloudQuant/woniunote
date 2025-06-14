"""
WoniuNote Common Utilities Package

This package contains common utilities and shared functionality for the WoniuNote application.
"""

# Import key modules to make them available at package level
try:
    from . import simple_logger
    from . import timer
    from . import utils
    from . import database
    from . import cache_utils
    from . import rate_limiter
    from . import async_tasks
    from . import monitoring
    from . import config_manager
    from . import database_optimizer
    from . import static_optimizer
    from . import session_util
    from . import redisdb
    from . import todo_database
    from . import card_database
    from . import log_decorator
    from . import api_security_enhancer
    from . import database_advanced_optimizer
    from . import intelligent_ops_manager
    from . import performance_enhanced
    from . import security_enhanced
    from . import user_experience_optimizer
except ImportError as e:
    # Handle import errors gracefully during development
    import warnings
    warnings.warn(f"Some common modules could not be imported: {e}")

__all__ = [
    'simple_logger',
    'timer', 
    'utils',
    'database',
    'cache_utils',
    'rate_limiter',
    'async_tasks',
    'monitoring',
    'config_manager',
    'database_optimizer',
    'static_optimizer',
    'session_util',
    'redisdb',
    'todo_database',
    'card_database',
    'log_decorator',
    'api_security_enhancer',
    'database_advanced_optimizer',
    'intelligent_ops_manager',
    'performance_enhanced',
    'security_enhanced',
    'user_experience_optimizer'
]
