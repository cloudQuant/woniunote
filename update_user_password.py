#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
直接更新用户密码为bcrypt格式
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pymysql
import yaml
import bcrypt

# 加载配置文件
with open('configs/user_password_config.yaml', 'r', encoding='utf-8') as f:
    db_config = yaml.safe_load(f)

# 用户信息
username = 'yunjinqi@qq.com'
password = 'yunjinqi@qq.com'

print(f"准备更新用户 {username} 的密码")
print("-" * 50)

# 生成新的bcrypt哈希
salt = bcrypt.gensalt(rounds=12)
new_hash = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
print(f"新的bcrypt哈希: {new_hash}")
print(f"哈希长度: {len(new_hash)}")

# 验证新哈希
verify_result = bcrypt.checkpw(password.encode('utf-8'), new_hash.encode('utf-8'))
print(f"验证新哈希: {verify_result}")

# 连接数据库
conn = pymysql.connect(
    host=db_config['host'],
    user=db_config['user'],
    password=db_config['password'],
    database=db_config['database'],
    charset='utf8mb4'
)

try:
    cursor = conn.cursor()
    
    # 先查询用户是否存在
    cursor.execute('SELECT userid, username, password FROM users WHERE username = %s', (username,))
    result = cursor.fetchone()
    
    if result:
        userid, db_username, old_password = result
        print(f"\n找到用户:")
        print(f"用户ID: {userid}")
        print(f"用户名: {db_username}")
        print(f"旧密码哈希: {old_password}")
        print(f"旧密码长度: {len(old_password)}")
        
        # 更新密码
        cursor.execute(
            'UPDATE users SET password = %s WHERE userid = %s',
            (new_hash, userid)
        )
        
        # 提交事务
        conn.commit()
        
        print(f"\n密码已成功更新为bcrypt格式!")
        print(f"新密码哈希: {new_hash}")
        
        # 验证更新
        cursor.execute('SELECT password FROM users WHERE userid = %s', (userid,))
        updated_password = cursor.fetchone()[0]
        print(f"\n验证更新后的密码: {updated_password}")
        print(f"更新成功: {updated_password == new_hash}")
        
    else:
        print(f"用户 {username} 不存在")
        
except Exception as e:
    print(f"错误: {e}")
    conn.rollback()
    import traceback
    traceback.print_exc()
    
finally:
    cursor.close()
    conn.close()

print("\n密码更新完成！")