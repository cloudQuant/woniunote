#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
简单的密码验证测试
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import hashlib
import bcrypt

# 测试密码
password = 'yunjinqi@qq.com'

# 生成不同格式的哈希
print("测试密码:", password)
print("-" * 50)

# 1. MD5哈希
md5_hash = hashlib.md5(password.encode('utf-8')).hexdigest()
print("MD5哈希:", md5_hash)
print("MD5长度:", len(md5_hash))

# 2. bcrypt哈希
salt = bcrypt.gensalt(rounds=12)
bcrypt_hash = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
print("\nbcrypt哈希:", bcrypt_hash)
print("bcrypt长度:", len(bcrypt_hash))

# 3. 验证bcrypt
print("\n验证bcrypt:")
is_valid = bcrypt.checkpw(password.encode('utf-8'), bcrypt_hash.encode('utf-8'))
print("bcrypt验证结果:", is_valid)

# 测试werkzeug格式
try:
    from werkzeug.security import generate_password_hash, check_password_hash
    werkzeug_hash = generate_password_hash(password)
    print("\nWerkzeug哈希:", werkzeug_hash)
    print("Werkzeug验证:", check_password_hash(werkzeug_hash, password))
except ImportError:
    print("\nWerkzeug未安装")

print("\n" + "-" * 50)
print("如果数据库中的密码是上述任一格式，系统应该能够正确验证。")