__version__ = "0.1.4"
from .app import create_app
from woniunote.common.database import db

# 不再创建全局应用实例
# flask_app = create_app()
