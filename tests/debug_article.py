"""
针对数据库模型的简单诊断测试
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

from tests.test_helpers import db, User, Article, create_test_user

def test_article_db_schema():
    """简单测试文章模型和数据库结构"""
    try:
        # 输出数据库连接字符串 (敏感信息已隐藏)
        db_uri = config_data['database']["SQLALCHEMY_DATABASE_URI"]
        print(f"数据库连接: {db_uri[:db_uri.index(':', 5)]}")
        
        # 获取Article表的列信息
        print("\n文章模型字段:")
        for column in Article.__table__.columns:
            col_type = str(column.type)
            print(f"  - {column.name}: {col_type}")
        
        # 尝试创建一个简单的用户和文章
        with db.session.begin():
            user = User(
                username=f"test_user_{datetime.now().timestamp()}",
                password="testpassword",
                nickname="Test User",
                avatar="test.jpg",
                qq="123456789",
                role="user",
                credit=50
            )
            db.session.add(user)
            db.session.flush()  # 获取用户ID
            
            article = Article(
                userid=user.userid,
                type="blog",
                title="Test Article Title",
                content="This is test content",
                thumbnail="test.jpg",
                credit=0,
                readcount=0,
                replycount=0,
                recommended=0,
                hidden=0,
                drafted=0,
                checked=1
            )
            db.session.add(article)
        
        print("\n✅ 测试成功: 成功创建用户和文章")
        return True
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_article_db_schema()
    print(f"\n测试结果: {'成功' if success else '失败'}")
