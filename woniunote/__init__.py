__version__ = "0.1.5"

# 在任何其他导入之前注册 pymysql
import pymysql
pymysql.install_as_MySQLdb()

# 然后导入其他模块
# 确保common模块总是被导入
from . import common

# 其他模块不在包导入时加载，避免副作用
import warnings
warnings.warn("woniunote package initialized without starting Flask app")

# 不再创建全局应用实例
# flask_app = create_app()
