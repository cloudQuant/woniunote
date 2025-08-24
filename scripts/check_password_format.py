#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查用户密码哈希格式的脚本
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 设置环境变量，避免生产环境验证失败
os.environ['FLASK_ENV'] = 'development'
os.environ['WONIUNOTE_ENV'] = 'dev'

from woniunote.common.db_connection_manager import get_db_session
from woniunote.models.user import Users
from woniunote.common.unified_logging import get_simple_logger

logger = get_simple_logger('check_password_format')

def check_user_password_format(email):
    """检查指定邮箱用户的密码哈希格式"""
    
    try:
        with get_db_session() as session:
            # 查询用户
            user = session.query(Users).filter_by(email=email).first()
            
            if not user:
                print(f"未找到邮箱为 {email} 的用户")
                return
            
            print(f"\n用户信息:")
            print(f"用户名: {user.username}")
            print(f"邮箱: {user.email}")
            print(f"用户ID: {user.userid}")
            
            password_hash = user.password
            print(f"\n密码哈希信息:")
            print(f"哈希值: {password_hash}")
            print(f"长度: {len(password_hash)}")
            
            # 检测哈希类型
            if password_hash.startswith('$2b$') or password_hash.startswith('$2a$') or password_hash.startswith('$2y$'):
                print(f"哈希类型: bcrypt")
                parts = password_hash.split('$')
                if len(parts) >= 4:
                    print(f"算法版本: {parts[1]}")
                    print(f"工作因子: {parts[2]}")
                    print(f"Salt和哈希值: {parts[3][:22]}... (salt部分)")
            elif password_hash.startswith('pbkdf2:'):
                print(f"哈希类型: PBKDF2 (Werkzeug格式)")
                parts = password_hash.split(':')
                if len(parts) >= 3:
                    print(f"算法: {parts[0]}")
                    print(f"哈希方法: {parts[1]}")
                    if '$' in parts[2]:
                        iterations = parts[2].split('$')[0]
                        print(f"迭代次数: {iterations}")
            elif password_hash.startswith('scrypt:'):
                print(f"哈希类型: scrypt (Werkzeug格式)")
            elif len(password_hash) == 32 and all(c in '0123456789abcdef' for c in password_hash.lower()):
                print(f"哈希类型: MD5 (32个十六进制字符)")
                print(f"注意: MD5已不安全，系统会在用户下次登录时自动升级到bcrypt")
            elif len(password_hash) == 40:
                print(f"哈希类型: 可能是SHA-1 (40个字符)")
            elif len(password_hash) == 64:
                print(f"哈希类型: 可能是SHA-256 (64个字符)")
            else:
                print(f"哈希类型: 未知格式")
            
            # 显示哈希预览
            if len(password_hash) > 40:
                print(f"\n哈希预览: {password_hash[:30]}...{password_hash[-20:]}")
            else:
                print(f"\n完整哈希: {password_hash}")
                
    except Exception as e:
        logger.error(f"检查密码格式时出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    email = "yunjinqi@qq.com"
    print(f"正在检查用户 {email} 的密码哈希格式...")
    check_user_password_format(email)