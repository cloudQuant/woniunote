__version__ = "0.1.4"

# 在任何其他导入之前注册 pymysql
import pymysql
pymysql.install_as_MySQLdb()

# 然后导入其他模块
from .app import create_app
from woniunote.common.database import db

# 不再创建全局应用实例
# flask_app = create_app()
