"""
验证数据库连接和配置
"""

import os
import sys
import yaml
import pymysql
from pymysql.cursors import DictCursor

# 添加项目根目录到Python路径
project_root = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, project_root)

def load_config():
    """加载配置文件"""
    # 测试配置文件
    test_config_path = os.path.join(project_root, "tests", "user_password_config.yaml")
    
    # 如果测试配置不存在，使用示例配置
    if not os.path.exists(test_config_path):
        example_config = os.path.join(project_root, "woniunote", "configs", "user_password_config_example.yaml")
        if os.path.exists(example_config):
            test_config_path = example_config
        else:
            print("错误: 找不到配置文件")
            return None
    
    # 读取配置
    try:
        with open(test_config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            return config
    except Exception as e:
        print(f"读取配置文件时出错: {e}")
        return None

def parse_db_uri(db_uri):
    """解析数据库连接字符串"""
    print(f"解析数据库URI: {db_uri}")
    
    # 示例: mysql://user:password@host:port/database
    prefix = "mysql://"
    if db_uri.startswith(prefix):
        # 去掉前缀
        uri = db_uri[len(prefix):]
        
        # 分割用户名密码和主机信息
        auth_host_db = uri.split('@')
        if len(auth_host_db) != 2:
            print("URI格式错误: 缺少@分隔符")
            return None
            
        # 用户名和密码
        auth = auth_host_db[0].split(':')
        if len(auth) != 2:
            print("URI格式错误: 用户名和密码格式不正确")
            return None
        
        username, password = auth
        
        # 主机、端口和数据库
        host_db = auth_host_db[1].split('/')
        if len(host_db) < 2:
            print("URI格式错误: 主机和数据库格式不正确")
            return None
            
        host_port = host_db[0].split(':')
        host = host_port[0]
        port = int(host_port[1]) if len(host_port) > 1 else 3306
        
        # 处理数据库名和参数
        db_parts = host_db[1].split('?')
        database = db_parts[0]
        
        return {
            'host': host,
            'port': port,
            'user': username,
            'password': password,
            'database': database
        }
    elif "mysql+pymysql" in db_uri:
        # 另一种格式: mysql+pymysql://user:password@host:port/database
        prefix = "mysql+pymysql://"
        uri = db_uri[len(prefix):]
        
        # 分割用户名密码和主机信息
        auth_host_db = uri.split('@')
        if len(auth_host_db) != 2:
            print("URI格式错误: 缺少@分隔符")
            return None
            
        # 用户名和密码
        auth = auth_host_db[0].split(':')
        if len(auth) != 2:
            print("URI格式错误: 用户名和密码格式不正确")
            return None
        
        username, password = auth
        
        # 主机、端口和数据库
        host_db = auth_host_db[1].split('/')
        if len(host_db) < 2:
            print("URI格式错误: 主机和数据库格式不正确")
            return None
            
        host_port = host_db[0].split(':')
        host = host_port[0]
        port = int(host_port[1]) if len(host_port) > 1 else 3306
        
        # 处理数据库名和参数
        db_parts = host_db[1].split('?')
        database = db_parts[0]
        
        return {
            'host': host,
            'port': port,
            'user': username,
            'password': password,
            'database': database
        }
    else:
        print(f"不支持的数据库URI格式: {db_uri}")
        return None

def test_db_connection(db_info):
    """测试数据库连接"""
    print(f"测试数据库连接: {db_info}")
    
    try:
        # 连接数据库
        conn = pymysql.connect(
            host=db_info['host'],
            port=db_info['port'],
            user=db_info['user'],
            password=db_info['password'],
            database=db_info['database'],
            cursorclass=DictCursor,
            charset='utf8mb4'
        )
        
        # 创建游标
        with conn.cursor() as cursor:
            # 执行简单查询
            cursor.execute("SELECT VERSION()")
            result = cursor.fetchone()
            print(f"数据库连接成功! MySQL版本: {result['VERSION()']}")
            
            # 尝试查询user表
            try:
                cursor.execute("SELECT COUNT(*) as count FROM users")
                result = cursor.fetchone()
                print(f"users表记录数: {result['count']}")
            except Exception as e:
                print(f"查询users表失败: {e}")
            
            # 尝试查询article表
            try:
                cursor.execute("SELECT COUNT(*) as count FROM article")
                result = cursor.fetchone()
                print(f"article表记录数: {result['count']}")
            except Exception as e:
                print(f"查询article表失败: {e}")
        
        # 关闭连接
        conn.close()
        return True
    except Exception as e:
        print(f"数据库连接失败: {e}")
        return False

if __name__ == "__main__":
    print("验证数据库连接...")
    
    # 加载配置
    config = load_config()
    if not config:
        print("无法加载配置文件")
        sys.exit(1)
    
    # 打印配置信息
    print("\n配置信息:")
    for section, values in config.items():
        print(f"  {section}:")
        if isinstance(values, dict):
            for key, value in values.items():
                # 打印敏感信息时隐藏部分内容
                if 'password' in key.lower() and isinstance(value, str):
                    value_display = value[:3] + '****' if len(value) > 3 else '****'
                    print(f"    {key}: {value_display}")
                else:
                    print(f"    {key}: {value}")
        else:
            print(f"    {values}")
    
    # 解析数据库连接信息
    if 'database' in config and 'SQLALCHEMY_DATABASE_URI' in config['database']:
        db_uri = config['database']['SQLALCHEMY_DATABASE_URI']
        db_info = parse_db_uri(db_uri)
        
        if db_info:
            # 测试数据库连接
            print("\n验证数据库连接...")
            if test_db_connection(db_info):
                print("\n✅ 验证成功: 数据库连接正常")
            else:
                print("\n❌ 验证失败: 数据库连接异常")
        else:
            print("\n❌ 验证失败: 数据库URI解析失败")
    else:
        print("\n❌ 验证失败: 配置文件中未找到数据库URI配置")
