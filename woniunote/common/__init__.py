#!/usr/bin/env python3
"""
WoniuNote Common Package
提供各种通用功能和工具
"""

# Import key modules to make them available at package level
# Only import modules that actually exist and don't have circular dependencies

# First, import basic utility modules
try:
    from . import utils
    from . import database
except ImportError as e:
    import warnings
    warnings.warn(f"Basic modules import failed: {e}")

# Then import other modules individually with error handling
modules_to_import = [
    'utils',
    'database',
    'unified_session',
    'unified_error_handler', 
    'unified_database_optimizer',
    'unified_monitoring',
    'unified_security',
    'unified_cache',
    'unified_logging',
    'unified_config',
    'unified_validator',
    'unified_utils',
    'rate_limiter',
    'async_tasks',
    'static_optimizer',
    'redisdb',
    'todo_database',
    'card_database',
    'log_decorator',
    'memory_optimizer',
    'memory_monitor',
    'password_utils',
    'performance_enhanced',
    'user_experience_optimizer',
    'resource_manager',
    'auth_utils',
    'atomic_password_migration',
    'authorization',
    'base_model',
    'code_refactor_helper',
    'create_database',
    'db_connection_manager',
    'safe_credit_manager',
    'secure_password',
    'secure_redis_manager'
]

successfully_imported = []
failed_imports = []

for module_name in modules_to_import:
    try:
        module = __import__(f'woniunote.common.{module_name}', fromlist=[module_name])
        globals()[module_name] = module
        successfully_imported.append(module_name)
    except ImportError as e:
        failed_imports.append(f"{module_name}: {str(e)}")
    except Exception as e:
        failed_imports.append(f"{module_name}: {str(e)}")

# Log import results (only in development)
import os
if os.environ.get('FLASK_ENV') == 'development':
    if successfully_imported:
        print(f"Common modules imported: {len(successfully_imported)}")
    if failed_imports:
        print(f"Failed imports: {len(failed_imports)}")

# 动态生成__all__基于成功导入的模块
__all__ = successfully_imported.copy()
