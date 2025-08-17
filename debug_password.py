#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
调试密码验证问题
"""
import pymysql
import yaml
import sys
import os

# 加载配置文件
try:
    with open('configs/user_password_config.yaml', 'r', encoding='utf-8') as f:
        db_config = yaml.safe_load(f)
except Exception as e:
    print(f'无法加载配置文件: {e}')
    sys.exit(1)

# 连接数据库
try:
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
        print(f'密码哈希: {password_hash}')
        print(f'密码长度: {len(password_hash)}')
        print(f'密码前10个字符: {password_hash[:10]}')
        
        # 检测密码格式
        if password_hash.startswith('$2b$') or password_hash.startswith('$2a$') or password_hash.startswith('$2y$'):
            print('密码格式: bcrypt')
        elif len(password_hash) == 32 and all(c in '0123456789abcdef' for c in password_hash.lower()):
            print('密码格式: MD5')
        elif password_hash.startswith('pbkdf2:'):
            print('密码格式: PBKDF2')
        else:
            print('密码格式: 未知')
            
        # 测试密码验证
        sys.path.append('/home/yun/Documents/woniunote')
        from woniunote.common.secure_password import verify_password_with_migration
        
        print("\n开始测试密码验证...")
        result, needs_migration, new_hash = verify_password_with_migration('yunjinqi@qq.com', password_hash)
        print(f'密码验证结果: {result}')
        print(f'需要迁移: {needs_migration}')
        
        # 如果是MD5，手动测试
        if len(password_hash) == 32:
            import hashlib
            test_password = 'yunjinqi@qq.com'
            md5_hash = hashlib.md5(test_password.encode('utf-8')).hexdigest()
            print(f'计算的MD5: {md5_hash}')
            print(f'存储的MD5: {password_hash}')
            print(f'MD5匹配: {md5_hash == password_hash}')
            
    else:
        print('用户不存在')
        
    conn.close()
    
except Exception as e:
    print(f'数据库查询错误: {e}')
    import traceback
    traceback.print_exc()