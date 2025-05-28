#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试清理工具

提供测试数据的清理功能，包括:
- 数据库清理
- 文件清理
- 会话清理
- 缓存清理
"""

import os
import sys
import shutil
import logging
from typing import List, Optional
import pytest

# 添加项目根目录到Python路径
project_root = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
sys.path.insert(0, project_root)

# 导入Flask应用
try:
    from woniunote.app import create_app
    from woniunote.common.database import db
    from sqlalchemy import text
except ImportError as e:
    logging.warning(f"无法导入所需模块: {e}")
    create_app = None
    db = None

# 配置日志
logger = logging.getLogger(__name__)

@pytest.fixture
def app():
    """创建测试用Flask应用"""
    if create_app:
        app = create_app('testing')
        return app
    return None

# 测试数据目录
TEMP_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'temp')

class TestCleanupHelper:
    """测试数据清理工具助手类（不是测试类）"""
    
    @staticmethod
    def cleanup_database(app, tables: Optional[List[str]] = None):
        """清理数据库表数据
        
        Args:
            app: Flask应用实例
            tables: 要清理的表名列表，如果为None则清理所有测试表
        """
        if not app or not db:
            logger.warning("无法清理数据库：缺少应用或数据库连接")
            return
            
        default_tables = ['users', 'articles', 'comments', 'favorites']
        target_tables = tables or default_tables
        
        try:
            with app.app_context():
                for table in target_tables:
                    try:
                        # 使用text()包装SQL字符串
                        db.session.execute(text(f"TRUNCATE TABLE {table}"))
                        logger.info(f"已清理表: {table}")
                    except Exception as e:
                        logger.warning(f"清理表 {table} 失败: {e}")
                        # 尝试使用DELETE代替TRUNCATE
                        try:
                            db.session.execute(text(f"DELETE FROM {table}"))
                            logger.info(f"已使用DELETE清理表: {table}")
                        except Exception as delete_e:
                            logger.error(f"DELETE清理表 {table} 也失败: {delete_e}")
                
                db.session.commit()
                logger.info("数据库清理完成")
        except Exception as e:
            logger.error(f"数据库清理失败: {e}")
            try:
                db.session.rollback()
            except:
                pass
    
    @staticmethod
    def cleanup_files(paths: Optional[List[str]] = None):
        """清理测试文件和目录
        
        Args:
            paths: 要清理的路径列表，如果为None则清理默认测试目录
        """
        default_paths = [TEMP_DIR]
        target_paths = paths or default_paths
        
        for path in target_paths:
            try:
                if os.path.exists(path):
                    logger.info(f"清理文件/目录: {path}")
                    if os.path.isfile(path):
                        os.remove(path)
                    elif os.path.isdir(path):
                        shutil.rmtree(path)
                else:
                    logger.debug(f"路径不存在，跳过: {path}")
            except Exception as e:
                logger.error(f"清理路径 {path} 失败: {e}")
    
    @staticmethod
    def cleanup_sessions(app):
        """清理Flask会话数据"""
        if not app:
            logger.warning("无法清理会话：缺少应用实例")
            return
            
        try:
            with app.app_context():
                # 清理Flask-Session数据
                session_dir = app.config.get('SESSION_FILE_DIR')
                if session_dir and os.path.exists(session_dir):
                    for file in os.listdir(session_dir):
                        if file.startswith('flask_session_'):
                            os.remove(os.path.join(session_dir, file))
            logger.info("会话清理完成")
        except Exception as e:
            logger.error(f"会话清理失败: {e}")
    
    @staticmethod
    def cleanup_cache(app):
        """清理缓存数据"""
        if not app:
            logger.warning("无法清理缓存：缺少应用实例")
            return
            
        try:
            with app.app_context():
                # 检查应用是否有cache属性
                if hasattr(app, 'cache'):
                    app.cache.clear()
                    logger.info("应用缓存清理完成")
                else:
                    logger.debug("应用没有cache属性，跳过缓存清理")
        except Exception as e:
            logger.warning(f"缓存清理失败: {e}")
    
    @staticmethod
    def cleanup_all(app):
        """清理所有测试数据"""
        logger.info("开始清理所有测试数据")
        TestCleanupHelper.cleanup_database(app)
        TestCleanupHelper.cleanup_files()
        TestCleanupHelper.cleanup_sessions(app)
        TestCleanupHelper.cleanup_cache(app)
        logger.info("所有测试数据清理完成")

@pytest.fixture
def test_cleanup(app):
    """pytest fixture for test cleanup"""
    yield TestCleanupHelper
    # 测试结束后清理
    try:
        TestCleanupHelper.cleanup_all(app)
    except Exception as e:
        logger.error(f"测试清理失败: {e}")

@pytest.mark.unit
def test_cleanup_database(app):
    """测试数据库清理功能"""
    if app and db:
        # 测试清理功能
        TestCleanupHelper.cleanup_database(app)
        logger.info("✓ 数据库清理测试通过")
    else:
        pytest.skip("跳过数据库清理测试：缺少数据库连接")

@pytest.mark.unit
def test_cleanup_files():
    """测试文件清理功能"""
    # 创建临时测试文件
    test_file = os.path.join(TEMP_DIR, 'test_file.txt')
    os.makedirs(TEMP_DIR, exist_ok=True)
    with open(test_file, 'w') as f:
        f.write('test')
    
    # 测试清理功能
    TestCleanupHelper.cleanup_files([test_file])
    assert not os.path.exists(test_file)
    logger.info("✓ 文件清理测试通过")

if __name__ == "__main__":
    print("手动运行测试清理工具...") 