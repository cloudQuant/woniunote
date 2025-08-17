#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
检查密码验证问题
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pymysql
import yaml
import hashlib
import bcrypt

# 加载配置文件
with open('configs/user_password_config.yaml', 'r', encoding='utf-8') as f:
    db_config = yaml.safe_load(f)

# 连接数据库
conn = pymysql.connect(
    host=db_config['host'],
    user=db_config['user'],
    password=db_config['password'],
    database=db_config['database'],
    charset='utf8mb4'
)

cursor = conn.cursor()

# 查询用户密码信息
cursor.execute('SELECT userid, username, password FROM users WHERE username = %s', ('yunjinqi@qq.com',))
result = cursor.fetchone()

if result:
    userid, username, password_hash = result
    print(f'用户ID: {userid}')
    print(f'用户名: {username}')
    print(f'数据库中的密码哈希: {password_hash}')
    print(f'密码哈希长度: {len(password_hash)}')
    
    # 检测密码格式
    if password_hash.startswith('$2b$') or password_hash.startswith('$2a$') or password_hash.startswith('$2y$'):
        print('密码格式: bcrypt')
    elif password_hash.startswith('pbkdf2:'):
        print('密码格式: PBKDF2 (Werkzeug)')
    elif len(password_hash) == 32 and all(c in '0123456789abcdef' for c in password_hash.lower()):
        print('密码格式: MD5')
    else:
        print('密码格式: 未知')
    
    # 测试密码
    test_password = 'yunjinqi@qq.com'
    print(f'\n测试密码: {test_password}')
    
    # 测试不同的哈希方式
    print('\n测试不同的哈希验证:')
    
    # 1. MD5测试
    md5_hash = hashlib.md5(test_password.encode('utf-8')).hexdigest()
    print(f'MD5哈希: {md5_hash}')
    print(f'MD5匹配: {md5_hash == password_hash}')
    
    # 2. 如果是bcrypt格式
    if password_hash.startswith('$2'):
        try:
            bcrypt_match = bcrypt.checkpw(test_password.encode('utf-8'), password_hash.encode('utf-8'))
            print(f'Bcrypt匹配: {bcrypt_match}')
        except Exception as e:
            print(f'Bcrypt验证错误: {e}')
    
    # 3. 如果是werkzeug的pbkdf2格式
    if password_hash.startswith('pbkdf2:'):
        try:
            from werkzeug.security import check_password_hash
            werkzeug_match = check_password_hash(password_hash, test_password)
            print(f'Werkzeug PBKDF2匹配: {werkzeug_match}')
        except Exception as e:
            print(f'Werkzeug验证错误: {e}')
    
else:
    print('用户不存在')

cursor.close()
conn.close()