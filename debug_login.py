#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
调试登录问题
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from woniunote.module.users import Users
from woniunote.common.atomic_password_migration import verify_and_migrate_user_password
from woniunote.common.secure_password import verify_password_with_migration
import hashlib

# 设置日志级别
import logging
logging.basicConfig(level=logging.DEBUG)

# 测试用户信息
username = 'yunjinqi@qq.com'
password = 'yunjinqi@qq.com'

print(f"测试用户: {username}")
print(f"测试密码: {password}")
print("-" * 50)

# 查询用户
users = Users()
result = users.find_by_username(username)

if result and len(result) > 0:
    user_record = result[0]
    current_hash = user_record.password
    
    print(f"用户ID: {user_record.userid}")
    print(f"用户名: {user_record.username}")
    print(f"数据库密码哈希: {current_hash}")
    print(f"密码哈希长度: {len(current_hash)}")
    print(f"密码哈希前20字符: {current_hash[:20]}...")
    print("-" * 50)
    
    # 检测密码格式
    if current_hash.startswith('$2b$') or current_hash.startswith('$2a$') or current_hash.startswith('$2y$'):
        print("密码格式: bcrypt")
    elif current_hash.startswith('pbkdf2:'):
        print("密码格式: PBKDF2 (Werkzeug)")
    elif len(current_hash) == 32 and all(c in '0123456789abcdef' for c in current_hash.lower()):
        print("密码格式: MD5")
    else:
        print("密码格式: 未知")
    print("-" * 50)
    
    # 1. 先测试直接密码验证
    print("1. 测试直接密码验证 (verify_password_with_migration):")
    try:
        is_valid, needs_migration, new_hash = verify_password_with_migration(password, current_hash)
        print(f"   验证结果: {is_valid}")
        print(f"   需要迁移: {needs_migration}")
        if new_hash:
            print(f"   新哈希: {new_hash[:20]}...")
    except Exception as e:
        print(f"   错误: {e}")
        import traceback
        traceback.print_exc()
    
    print("-" * 50)
    
    # 2. 测试原子密码迁移
    print("2. 测试原子密码迁移 (verify_and_migrate_user_password):")
    try:
        is_valid, migration_info = verify_and_migrate_user_password(
            user_record.userid, username, password, current_hash
        )
        print(f"   验证结果: {is_valid}")
        print(f"   迁移信息: {migration_info}")
    except Exception as e:
        print(f"   错误: {e}")
        import traceback
        traceback.print_exc()
    
    print("-" * 50)
    
    # 3. 如果是MD5，手动验证
    if len(current_hash) == 32:
        print("3. 手动MD5验证:")
        md5_hash = hashlib.md5(password.encode('utf-8')).hexdigest()
        print(f"   计算的MD5: {md5_hash}")
        print(f"   存储的哈希: {current_hash}")
        print(f"   MD5匹配: {md5_hash == current_hash}")
        
else:
    print("用户不存在")