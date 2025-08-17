#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试密码验证问题
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from woniunote.common.database import dbconnect
from woniunote.module.users import Users
from woniunote.common.secure_password import verify_password_with_migration
from woniunote.common.atomic_password_migration import verify_and_migrate_user_password
import hashlib

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
    user = result[0]
    print(f"用户ID: {user.userid}")
    print(f"用户名: {user.username}")
    print(f"数据库密码哈希: {user.password}")
    print(f"密码哈希长度: {len(user.password)}")
    print("-" * 50)
    
    # 检测密码格式
    stored_hash = user.password
    if stored_hash.startswith('$2b$') or stored_hash.startswith('$2a$') or stored_hash.startswith('$2y$'):
        print("密码格式: bcrypt")
    elif stored_hash.startswith('pbkdf2:'):
        print("密码格式: PBKDF2 (Werkzeug)")
    elif len(stored_hash) == 32 and all(c in '0123456789abcdef' for c in stored_hash.lower()):
        print("密码格式: MD5")
    else:
        print("密码格式: 未知")
    print("-" * 50)
    
    # 测试直接密码验证
    print("测试直接密码验证:")
    is_valid, needs_migration, new_hash = verify_password_with_migration(password, stored_hash)
    print(f"验证结果: {is_valid}")
    print(f"需要迁移: {needs_migration}")
    if new_hash:
        print(f"新哈希: {new_hash[:20]}...")
    print("-" * 50)
    
    # 如果是MD5，手动验证
    if len(stored_hash) == 32:
        print("手动MD5验证:")
        md5_hash = hashlib.md5(password.encode('utf-8')).hexdigest()
        print(f"计算的MD5: {md5_hash}")
        print(f"存储的哈希: {stored_hash}")
        print(f"MD5匹配: {md5_hash == stored_hash}")
        print("-" * 50)
    
    # 测试原子密码迁移
    print("测试原子密码迁移:")
    try:
        migration_valid, migration_info = verify_and_migrate_user_password(
            user.userid, username, password, stored_hash
        )
        print(f"迁移验证结果: {migration_valid}")
        print(f"迁移信息: {migration_info}")
    except Exception as e:
        print(f"迁移错误: {e}")
        import traceback
        traceback.print_exc()
        
else:
    print("用户不存在")