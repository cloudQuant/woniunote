#!/usr/bin/env python3
"""
数据库迁移脚本：更新密码字段长度
将用户表中的密码字段从 VARCHAR(32) 扩展到 VARCHAR(128) 以支持 bcrypt 哈希
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from woniunote.common.utils import get_db_connection
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_password_field():
    """迁移密码字段长度"""
    try:
        # 获取数据库连接
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 检查当前密码字段长度
        logger.info("检查当前密码字段结构...")
        cursor.execute("""
            SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_NAME = 'users' AND COLUMN_NAME = 'password'
        """)
        
        result = cursor.fetchone()
        if result:
            current_length = result[2]
            logger.info(f"当前密码字段长度: {current_length}")
            
            if current_length >= 128:
                logger.info("密码字段长度已足够，无需迁移")
                return True
        
        # 备份数据
        logger.info("开始备份用户表...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users_backup_migrate AS 
            SELECT * FROM users
        """)
        
        # 更新密码字段长度
        logger.info("更新密码字段长度到 VARCHAR(128)...")
        cursor.execute("""
            ALTER TABLE users 
            MODIFY COLUMN password VARCHAR(128) NOT NULL
        """)
        
        # 验证更改
        cursor.execute("""
            SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_NAME = 'users' AND COLUMN_NAME = 'password'
        """)
        
        result = cursor.fetchone()
        if result:
            new_length = result[2]
            logger.info(f"更新后密码字段长度: {new_length}")
            
            if new_length >= 128:
                logger.info("密码字段迁移成功！")
                conn.commit()
                return True
            else:
                logger.error("密码字段迁移失败")
                conn.rollback()
                return False
        
    except Exception as e:
        logger.error(f"迁移过程中发生错误: {e}")
        conn.rollback()
        return False
        
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

def cleanup_backup():
    """清理备份表（可选）"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        logger.info("清理备份表...")
        cursor.execute("DROP TABLE IF EXISTS users_backup_migrate")
        conn.commit()
        logger.info("备份表已清理")
        
    except Exception as e:
        logger.error(f"清理备份表时发生错误: {e}")
        
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='密码字段迁移脚本')
    parser.add_argument('--cleanup', action='store_true', help='清理备份表')
    args = parser.parse_args()
    
    if args.cleanup:
        cleanup_backup()
    else:
        success = migrate_password_field()
        if success:
            logger.info("迁移完成！可以使用 --cleanup 参数清理备份表")
            sys.exit(0)
        else:
            logger.error("迁移失败！")
            sys.exit(1)