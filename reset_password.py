#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
重置用户密码为bcrypt格式
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from woniunote.common.database import dbconnect
from woniunote.module.users import Users
from woniunote.common.secure_password import hash_password

# 用户信息
username = 'yunjinqi@qq.com'
password = 'yunjinqi@qq.com'

print(f"准备重置用户 {username} 的密码")
print("-" * 50)

# 连接数据库
dbsession, md, DBase = dbconnect()

try:
    # 查询用户
    users = Users()
    result = users.find_by_username(username)
    
    if result and len(result) > 0:
        user = result[0]
        print(f"找到用户:")
        print(f"用户ID: {user.userid}")
        print(f"用户名: {user.username}")
        print(f"当前密码哈希: {user.password}")
        print(f"当前密码哈希长度: {len(user.password)}")
        
        # 生成新的bcrypt密码哈希
        new_hash = hash_password(password)
        print(f"\n新的bcrypt哈希: {new_hash}")
        print(f"新哈希长度: {len(new_hash)}")
        
        # 更新密码
        user.password = new_hash
        dbsession.commit()
        
        print("\n密码已成功更新为bcrypt格式!")
        
        # 验证更新
        users2 = Users()
        result2 = users2.find_by_username(username)
        if result2 and len(result2) > 0:
            updated_user = result2[0]
            print(f"\n验证更新后的密码哈希: {updated_user.password}")
            print(f"更新成功: {updated_user.password == new_hash}")
            
            # 测试登录
            from woniunote.common.secure_password import verify_password
            login_test = verify_password(password, updated_user.password)
            print(f"登录验证测试: {login_test}")
            
    else:
        print(f"用户 {username} 不存在")
        
except Exception as e:
    print(f"错误: {e}")
    dbsession.rollback()
    import traceback
    traceback.print_exc()
    
finally:
    dbsession.close()

print("\n密码重置完成！现在可以使用用户名和密码登录了。")