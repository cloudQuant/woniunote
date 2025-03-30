"""
测试数据库连接脚本
"""
import pymysql
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

def test_mysql_direct():
    """直接使用pymysql测试连接"""
    try:
        # 连接参数
        conn = pymysql.connect(
            host="127.0.0.1",
            user="woniunote_user",
            password="Woniunote_password1!",
            database="woniunote",
            charset="utf8",
            autocommit=True
        )
        
        # 测试连接
        with conn.cursor() as cursor:
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()
            print(f"成功连接到MySQL! 版本: {version[0]}")
            
        conn.close()
        return True
    except Exception as e:
        print(f"直接连接MySQL失败: {e}")
        return False

def test_sqlalchemy():
    """使用SQLAlchemy测试连接"""
    try:
        # 连接字符串
        db_uri = "mysql://woniunote_user:Woniunote_password1!@127.0.0.1:3306/woniunote?charset=utf8&autocommit=true"
        
        # 创建引擎
        engine = create_engine(db_uri)
        
        # 测试连接
        with engine.connect() as connection:
            result = connection.execute(text("SELECT VERSION()"))
            row = result.fetchone()
            if row:
                print(f"成功通过SQLAlchemy连接到MySQL! 版本: {row[0]}")
        
        return True
    except SQLAlchemyError as e:
        print(f"SQLAlchemy连接失败: {e}")
        return False

def test_sqlalchemy_pymysql():
    """使用SQLAlchemy+pymysql测试连接"""
    try:
        # 连接字符串
        db_uri = "mysql+pymysql://woniunote_user:Woniunote_password1!@127.0.0.1:3306/woniunote?charset=utf8mb4"
        
        # 创建引擎
        engine = create_engine(db_uri)
        
        # 测试连接
        with engine.connect() as connection:
            result = connection.execute(text("SELECT VERSION()"))
            row = result.fetchone()
            if row:
                print(f"成功通过SQLAlchemy+pymysql连接到MySQL! 版本: {row[0]}")
        
        return True
    except SQLAlchemyError as e:
        print(f"SQLAlchemy+pymysql连接失败: {e}")
        return False

if __name__ == "__main__":
    print("=== 测试数据库连接 ===")
    print("\n1. 直接使用pymysql连接")
    test_mysql_direct()
    
    print("\n2. 使用SQLAlchemy连接")
    test_sqlalchemy()
    
    print("\n3. 使用SQLAlchemy+pymysql连接")
    test_sqlalchemy_pymysql()
