"""
增强的用户模块 - 使用 BaseModel 基础类
演示如何使用基础数据访问类来减少重复代码
"""
import random
import time
import traceback
from flask import session
from sqlalchemy import Table, Column, Integer, String, DateTime, text
from sqlalchemy.orm import relationship
from woniunote.common.database import dbconnect
from woniunote.common.create_database import User
from woniunote.common.simple_logger import get_simple_logger
from woniunote.common.base_model import BaseModel
from woniunote.common.error_handler import DatabaseException

dbsession, md, DBase = dbconnect()

class UsersEnhanced(DBase, BaseModel):
    """增强的用户数据访问类 - 继承 BaseModel"""
    
    __table__ = Table(
        'users', md,
        Column('userid', Integer, primary_key=True, nullable=False, autoincrement=True),
        Column('username', String(50), nullable=False),
        Column('password', String(128), nullable=False),
        Column('nickname', String(30)),
        Column('avatar', String(20)),
        Column('qq', String(15)),
        Column('role', String(10), nullable=False),
        Column('credit', Integer, default=50),
        Column('createtime', DateTime),
        Column('updatetime', DateTime)
    )

    def __init__(self):
        # 初始化基础模型
        BaseModel.__init__(self, "users")

    # 使用基础类的标准查询方法，而不是重复实现
    def find_user_by_username(self, username):
        """
        根据用户名查找用户
        使用基础类的 find_by_field 方法
        """
        return self.find_by_field(User, 'username', username, first_only=True)

    def find_user_by_id(self, userid):
        """
        根据用户ID查找用户
        使用基础类的 find_by_id 方法
        """
        return self.find_by_id(User, userid)

    def create_user(self, username, password, role='user'):
        """
        创建新用户
        使用基础类的 create 方法
        """
        now = time.strftime('%Y-%m-%d %H:%M:%S')
        nickname = username.split('@')[0]  # 默认将邮箱账号前缀作为昵称
        avatar = str(random.randint(1, 15)) + '.png'  # 从15张头像图片中随机选择一张
        
        data = {
            'username': username,
            'password': password,
            'role': role,
            'credit': 50,
            'nickname': nickname,
            'avatar': avatar,
            'createtime': now,
            'updatetime': now
        }
        
        return self.create(User, data)

    def update_user(self, userid, **kwargs):
        """
        更新用户信息
        使用基础类的 update_by_id 方法
        """
        if kwargs:
            kwargs['updatetime'] = time.strftime('%Y-%m-%d %H:%M:%S')
        return self.update_by_id(User, userid, kwargs)

    def delete_user(self, userid):
        """
        删除用户
        使用基础类的 delete_by_id 方法
        """
        return self.delete_by_id(User, userid)

    def get_user_count(self, conditions=None):
        """
        获取用户数量
        使用基础类的 count 方法
        """
        return self.count(User, conditions)

    def find_users_by_role(self, role, limit=100):
        """
        根据角色查找用户
        使用基础类的 find_by_field 方法
        """
        return self.find_by_field(User, 'role', role, first_only=False)

    def update_user_credit(self, userid, credit_change):
        """
        更新用户积分
        使用基础类的原生SQL执行能力，确保原子操作
        """
        try:
            # 使用原子更新操作避免竞态条件
            sql = """
                UPDATE users 
                SET credit = credit + :credit_change, updatetime = :updatetime 
                WHERE userid = :userid
            """
            params = {
                'credit_change': credit_change,
                'userid': userid,
                'updatetime': time.strftime('%Y-%m-%d %H:%M:%S')
            }
            
            result = self.execute_raw_query(sql, params)
            return True
            
        except DatabaseException as e:
            self.logger.error(f"更新用户积分失败: {e}")
            return False

    def update_user_password(self, userid, new_password_hash):
        """
        更新用户密码
        使用基础类的 update_by_id 方法
        """
        return self.update_by_id(User, userid, {'password': new_password_hash})

    def find_active_users(self, days=30, limit=100):
        """
        查找活跃用户（根据创建时间）
        使用基础类的原生SQL执行能力
        """
        try:
            sql = """
                SELECT * FROM users 
                WHERE createtime >= DATE_SUB(NOW(), INTERVAL :days DAY)
                ORDER BY createtime DESC
                LIMIT :limit
            """
            params = {'days': days, 'limit': limit}
            return self.execute_raw_query(sql, params)
            
        except DatabaseException as e:
            self.logger.error(f"查找活跃用户失败: {e}")
            return []

    def get_user_statistics(self):
        """
        获取用户统计信息
        使用基础类的原生SQL执行能力
        """
        try:
            sql = """
                SELECT 
                    COUNT(*) as total_users,
                    SUM(CASE WHEN role = 'admin' THEN 1 ELSE 0 END) as admin_count,
                    SUM(CASE WHEN role = 'user' THEN 1 ELSE 0 END) as user_count,
                    AVG(credit) as avg_credit,
                    MAX(credit) as max_credit,
                    MIN(credit) as min_credit
                FROM users
            """
            result = self.execute_raw_query(sql)
            return result[0] if result else {}
            
        except DatabaseException as e:
            self.logger.error(f"获取用户统计信息失败: {e}")
            return {}

    # 兼容现有代码的方法
    def find_by_username(self, username):
        """兼容现有代码的用户名查找方法"""
        user = self.find_user_by_username(username)
        return [user] if user else []

    def do_register(self, username, password):
        """兼容现有代码的注册方法"""
        return self.create_user(username, password)

    def find_by_userid(self, userid):
        """兼容现有代码的用户ID查找方法"""
        return self.find_user_by_id(userid)

    def update_credit(self, credit_change):
        """兼容现有代码的积分更新方法"""
        userid = session.get('userid')
        if not userid:
            return False
        return self.update_user_credit(userid, credit_change)

# 使用示例：
# users_enhanced = UsersEnhanced()
# 
# # 查找用户
# user = users_enhanced.find_user_by_username("test@example.com")
# 
# # 创建用户
# new_user = users_enhanced.create_user(
#     username="newuser@example.com", 
#     password="hashed_password"
# )
# 
# # 更新用户信息
# users_enhanced.update_user(123, nickname="新昵称")
# 
# # 更新积分
# users_enhanced.update_user_credit(123, 10)  # 增加10积分
# users_enhanced.update_user_credit(123, -5)  # 减少5积分