"""
调试 Card 和 CardCategory 关系
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

from sqlalchemy import create_engine, inspect
from tests.test_helpers import CardCategory, Card

def inspect_relationship():
    """检查Card和CardCategory之间的关系"""
    try:
        # 打印Card上定义的外键
        print("==== Card外键信息 ====")
        for fk in Card.__table__.foreign_keys:
            print(f"外键: {fk}")
            print(f"  来源列: {fk.parent}")
            print(f"  目标列: {fk.column}")
            print(f"  约束: {fk.constraint}")
        
        # 打印CardCategory上的关系
        print("\n==== CardCategory关系定义 ====")
        for rel in CardCategory.__mapper__.relationships:
            print(f"关系名: {rel.key}")
            print(f"  目标: {rel.target}")
            print(f"  方向: {rel.direction}")
            print(f"  关系表达式: {rel.primaryjoin}")
        
        print("\n==== Card关系定义 ====")
        for rel in Card.__mapper__.relationships:
            print(f"关系名: {rel.key}")
            print(f"  目标: {rel.target}")
            print(f"  方向: {rel.direction}")
            print(f"  关系表达式: {rel.primaryjoin}")
        
        return True
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = inspect_relationship()
    print(f"\n调试结果: {'成功' if success else '失败'}")
