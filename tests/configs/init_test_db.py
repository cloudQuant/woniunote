"""
初始化WoniuNote测试数据库
从test_config.yaml读取数据库配置，首先删除已有表，然后从SQL文件导入数据
"""
import os
import sys
import yaml
import time
import subprocess
import pymysql
from sqlalchemy import create_engine, text, inspect

# 设置项目根目录
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

print("初始化WoniuNote测试数据库...")

# 读取配置文件
config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'test_config.yaml')
with open(config_path, 'r', encoding='utf-8') as file:
    config = yaml.safe_load(file)

# 获取数据库连接URI
db_uri = config['database']['SQLALCHEMY_DATABASE_URI']
print(f"数据库连接URI: {db_uri}")

# 解析数据库连接字符串
# 示例: mysql+pymysql://root:password@localhost:3306/woniunote_test
def parse_db_uri(uri):
    """解析数据库连接URI，处理特殊格式和字符"""
    print(f"开始解析URI: {uri}")
    
    try:
        # 检查URI是否包含完整的协议部分
        if '://' not in uri:
            print("URI格式错误: 缺少协议部分")
            raise ValueError("URI格式错误")
            
        # 提取协议和剩余部分
        protocol_part, remaining = uri.split('://', 1)
        
        # 处理查询参数
        if '?' in remaining:
            connection_part, query_part = remaining.split('?', 1)
        else:
            connection_part = remaining
            query_part = ""
            
        # 分离用户认证信息和主机/数据库部分
        if '@' in connection_part:
            auth_part, server_part = connection_part.split('@', 1)
        else:
            auth_part = ""
            server_part = connection_part
            
        # 解析用户名和密码
        if ':' in auth_part:
            user, password = auth_part.split(':', 1)
        else:
            user = auth_part
            password = ""
            
        # 解析主机、端口和数据库名
        if '/' in server_part:
            host_port, db_name = server_part.split('/', 1)
            
            # 处理主机和端口
            if ':' in host_port:
                host, port_str = host_port.split(':', 1)
                try:
                    port = int(port_str)
                except ValueError:
                    print(f"端口格式错误: {port_str}")
                    port = 3306
            else:
                host = host_port
                port = 3306
        else:
            host = server_part
            port = 3306
            db_name = ""
        
        # 完成解析
        result = {
            'user': user,
            'password': password,
            'host': host,
            'port': port,
            'database': db_name
        }
        
        print(f"URI解析结果: {result['user']}:****@{result['host']}:{result['port']}/{result['database']}")
        return result
    except Exception as e:
        print(f"解析URI时出错: {e}")
        print("尝试使用备用方法解析URI")
        
        # 备用解析方法
        try:
            # 提取主机和端口
            if '@' in uri:
                host_start = uri.index('@') + 1
                host_part = uri[host_start:]
                
                # 提取数据库名
                if '/' in host_part:
                    host_end = host_part.index('/')
                    host_and_port = host_part[:host_end]
                    db_part = host_part[host_end+1:]
                    
                    # 处理查询参数
                    if '?' in db_part:
                        db_name = db_part.split('?', 1)[0]
                    else:
                        db_name = db_part
                else:
                    host_and_port = host_part
                    db_name = ""
                
                # 提取主机和端口
                if ':' in host_and_port:
                    host, port_str = host_and_port.split(':', 1)
                    try:
                        port = int(port_str)
                    except ValueError:
                        port = 3306
                else:
                    host = host_and_port
                    port = 3306
                
                # 提取用户名和密码
                auth_part = uri[uri.index('://')+3:host_start-1]
                if ':' in auth_part:
                    user, password = auth_part.split(':', 1)
                else:
                    user = auth_part
                    password = ""
                
                result = {
                    'user': user,
                    'password': password,
                    'host': host,
                    'port': port,
                    'database': db_name
                }
                
                print(f"备用解析结果: {result['user']}:****@{result['host']}:{result['port']}/{result['database']}")
                return result
            else:
                # 无法解析，使用默认值
                print("无法解析URI，使用默认值")
                return {
                    'user': 'woniunote_user',
                    'password': 'Woniunote_password1!',
                    'host': '127.0.0.1',
                    'port': 3306,
                    'database': 'woniunote'
                }
        except Exception as e2:
            print(f"备用解析也失败: {e2}")
            print("使用硬编码默认值")
            return {
                'user': 'woniunote_user',
                'password': 'Woniunote_password1!',
                'host': '127.0.0.1',
                'port': 3306,
                'database': 'woniunote'
            }

# 创建数据库引擎
engine = create_engine(db_uri)

def drop_all_tables():
    """删除数据库中的所有表"""
    print("删除已有的所有表...")
    
    # 使用inspect获取所有表名
    inspector = inspect(engine)
    metadata = inspector.get_table_names()
    
    # 创建会话并删除表
    with engine.connect() as connection:
        # 关闭外键约束检查
        connection.execute(text("SET FOREIGN_KEY_CHECKS = 0;"))
        
        # 删除所有表
        for table in metadata:
            print(f"删除表: {table}")
            connection.execute(text(f"DROP TABLE IF EXISTS {table};"))
        
        # 恢复外键约束检查
        connection.execute(text("SET FOREIGN_KEY_CHECKS = 1;"))
    
    print("已删除所有表")
    time.sleep(5)

def import_from_sql_file():
    """从SQL文件导入测试数据到数据库，确保保留HTML标签和特殊字符"""
    import pymysql
    
    # SQL文件路径在项目根目录的docs文件夹下
    sql_file_path = os.path.join(project_root, 'docs', 'woniunote_db.sql')
    print(f"从SQL文件导入数据: {sql_file_path}")
    
    if not os.path.exists(sql_file_path):
        print(f"错误: SQL文件不存在: {sql_file_path}")
        return False
    
    try:
        # 直接连接到测试数据库
        conn = pymysql.connect(
            host='localhost',
            user='root',
            password='123456',
            database='woniunote_test',
            charset='utf8mb4',
            autocommit=False
        )
        
        # 创建游标
        cursor = conn.cursor()
        
        # 读取SQL文件内容
        with open(sql_file_path, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        # 确保SQL语句是以分号结尾的
        sql_statements = sql_content.split(';')
        
        # 逐个执行SQL语句
        for statement in sql_statements:
            if statement.strip():
                # 直接执行SQL语句，不做任何处理以保留所有内容
                try:
                    cursor.execute(statement)
                except Exception as e:
                    print(f"执行SQL语句时出错: {e}")
                    print(f"有问题的SQL语句: {statement[:200]}...")
        
        # 提交事务
        conn.commit()
        print("SQL文件导入成功")
    except Exception as e:
        # 出错时回滚
        conn.rollback()
        print(f"导入SQL文件时出错: {e}")
    finally:
        # 关闭连接
        cursor.close()
        conn.close()

def main():
    """主函数，执行初始化流程"""
    try:
        # 删除所有已有表
        drop_all_tables()
        
        # 从SQL文件导入数据
        if import_from_sql_file():
            print("数据库初始化完成")
            return 0
        else:
            print("数据库初始化失败")
            return 1
    except Exception as e:
        print(f"初始化过程中出现错误: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
