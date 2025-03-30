"""
针对Card数据库模型的简单诊断测试
"""
import os
import sys
import yaml
from datetime import datetime

# 添加项目根目录到Python路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# 读取配置
TEST_CONFIG_PATH = os.path.join(BASE_DIR, 'test_config.yaml')
with open(TEST_CONFIG_PATH, 'r', encoding='utf-8') as f:
    config_data = yaml.safe_load(f.read())

from sqlalchemy import create_engine, inspect, MetaData, Table
from sqlalchemy.orm import sessionmaker, scoped_session
from tests.test_helpers import User, CardCategory, Card, app

def test_card_db_schema():
    """简单测试Card模型和数据库结构"""
    try:
        # 输出数据库连接字符串 (敏感信息已隐藏)
        db_uri = config_data['database']["SQLALCHEMY_DATABASE_URI"]
        print(f"数据库连接: {db_uri[:db_uri.index('@') if '@' in db_uri else len(db_uri)]}")
        
        # 使用纯SQLAlchemy创建连接，避免Flask上下文问题
        engine = create_engine(db_uri)
        Session = scoped_session(sessionmaker(bind=engine))
        session = Session()
        
        # 获取Card表和CardCategory表的列信息
        print("\nCardCategory模型字段:")
        for column in CardCategory.__table__.columns:
            col_type = str(column.type)
            print(f"  - {column.name}: {col_type}")
        
        print("\nCard模型字段:")
        for column in Card.__table__.columns:
            col_type = str(column.type)
            print(f"  - {column.name}: {col_type}")
        
        # 检查数据库实际表结构
        inspector = inspect(engine)
        
        print("\n数据库中的cardcategory表结构:")
        try:
            columns = inspector.get_columns('cardcategory')
            for column in columns:
                print(f"  - {column['name']}: {column['type']}")
        except Exception as e:
            print(f"  无法获取cardcategory表结构: {e}")
        
        print("\n数据库中的card表结构:")
        try:
            columns = inspector.get_columns('card')
            for column in columns:
                print(f"  - {column['name']}: {column['type']}")
        except Exception as e:
            print(f"  无法获取card表结构: {e}")
        
        # 检查其它表
        print("\n数据库中的所有表:")
        tables = inspector.get_table_names()
        for table in tables:
            print(f"  - {table}")
        
        print("\n✅ 测试成功: 成功查询数据库结构")
        return True
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_card_db_schema()
    print(f"\n测试结果: {'成功' if success else '失败'}")
