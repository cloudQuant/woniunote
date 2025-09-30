__version__ = "0.1.5"

# 在任何其他导入之前注册 pymysql
import pymysql
pymysql.install_as_MySQLdb()

# 然后导入其他模块
# 确保common模块总是被导入
from . import common

# 其他模块可以有条件导入
try:
    from . import app
    from .app import create_app
    from . import app_factory
    from woniunote.common.database import db
except ImportError as e:
    import warnings
    warnings.warn(f"Module import warning: {e}")

# 不再创建全局应用实例
# flask_app = create_app()
