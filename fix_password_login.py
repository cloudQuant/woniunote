#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
修复密码登录问题
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import hashlib
import bcrypt
from woniunote.common.database import dbconnect
from woniunote.module.users import Users

# 连接数据库
dbsession, md, DBase = dbconnect()

# 测试用户信息
username = 'yunjinqi@qq.com'
password = 'yunjinqi@qq.com'

print(f"用户名: {username}")
print(f"密码: {password}")
print("-" * 50)

# 查询用户
user_instance = Users()
users = user_instance.find_by_username(username)

if users and len(users) > 0:
    user = users[0]
    stored_hash = user.password
    
    print(f"用户ID: {user.userid}")
    print(f"数据库中的密码哈希: {stored_hash}")
    print(f"哈希长度: {len(stored_hash)}")
    print("-" * 50)
    
    # 检测当前密码格式
    if stored_hash.startswith('$2b$') or stored_hash.startswith('$2a$') or stored_hash.startswith('$2y$'):
        print("当前密码格式: bcrypt")
        # 验证bcrypt密码
        try:
            is_valid = bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8'))
            print(f"bcrypt验证结果: {is_valid}")
        except Exception as e:
            print(f"bcrypt验证错误: {e}")
            
    elif stored_hash.startswith('pbkdf2:'):
        print("当前密码格式: PBKDF2 (Werkzeug)")
        # 尝试验证werkzeug密码
        try:
            from werkzeug.security import check_password_hash
            is_valid = check_password_hash(stored_hash, password)
            print(f"Werkzeug验证结果: {is_valid}")
        except Exception as e:
            print(f"Werkzeug验证错误: {e}")
            
    elif len(stored_hash) == 32 and all(c in '0123456789abcdef' for c in stored_hash.lower()):
        print("当前密码格式: MD5")
        # 验证MD5密码
        md5_hash = hashlib.md5(password.encode('utf-8')).hexdigest()
        print(f"计算的MD5: {md5_hash}")
        print(f"存储的MD5: {stored_hash}")
        is_valid = md5_hash == stored_hash
        print(f"MD5验证结果: {is_valid}")
        
        if is_valid:
            print("\nMD5密码验证成功，但建议升级到bcrypt...")
            # 生成新的bcrypt哈希
            salt = bcrypt.gensalt(rounds=12)
            new_hash = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
            print(f"新的bcrypt哈希: {new_hash}")
            
            # 询问是否更新
            response = input("\n是否将密码更新为bcrypt格式？(y/n): ")
            if response.lower() == 'y':
                try:
                    user.password = new_hash
                    dbsession.commit()
                    print("密码已成功更新为bcrypt格式！")
                except Exception as e:
                    dbsession.rollback()
                    print(f"更新失败: {e}")
    else:
        print(f"未知的密码格式")
        print("尝试生成一个新的bcrypt密码...")
        
        # 生成新的bcrypt哈希
        salt = bcrypt.gensalt(rounds=12)
        new_hash = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
        print(f"新的bcrypt哈希: {new_hash}")
        
        # 询问是否更新
        response = input("\n是否更新密码？(y/n): ")
        if response.lower() == 'y':
            try:
                user.password = new_hash
                dbsession.commit()
                print("密码已成功更新！")
            except Exception as e:
                dbsession.rollback()
                print(f"更新失败: {e}")
else:
    print("用户不存在")
    
# 关闭数据库会话
dbsession.close()