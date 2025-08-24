#!/usr/bin/env python3
"""
WoniuNote Common Package
提供各种通用功能和工具
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
    
    # 统一模块（第二阶段整合）
    from . import unified_cache
    from . import unified_logging
    from . import unified_config
    from . import unified_validator
    from . import unified_utils
    
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
    
    # 第二阶段已整合的模块（标记为废弃）
    from . import advanced_cache
    from . import unified_cache_strategy
    from . import static_cache_optimizer
    from . import enhanced_logger
    from . import log_level_manager
    from . import secure_config
    from . import environment_validator
    from . import input_validator
    from . import enhanced_input_validator
    from . import file_upload_validator
    from . import permission_validator
    
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
    'security_enhanced',
    
    # 第二阶段已整合的模块（向后兼容，但建议迁移到统一模块）
    'advanced_cache',
    'unified_cache_strategy',
    'static_cache_optimizer',
    'enhanced_logger',
    'log_level_manager',
    'secure_config',
    'environment_validator',
    'input_validator',
    'enhanced_input_validator',
    'file_upload_validator',
    'permission_validator'
]
