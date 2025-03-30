"""
使用原始SQL查询测试Card和CardCategory功能
避免ORM映射问题
"""
import os
import sys
import yaml
from datetime import datetime, timedelta
import random
import string

# 添加项目根目录到Python路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# 读取配置
TEST_CONFIG_PATH = os.path.join(BASE_DIR, 'test_config.yaml')
with open(TEST_CONFIG_PATH, 'r', encoding='utf-8') as f:
    config_data = yaml.safe_load(f.read())

# 获取数据库连接
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# 设置测试数据库连接
db_uri = config_data.get('db_uri', 'sqlite:///test.db')
engine = create_engine(db_uri, echo=False)
Session = sessionmaker(bind=engine)

def random_string(length=8):
    """生成随机字符串"""
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

def test_card_operations():
    """测试卡片的创建、查询和更新操作（使用原始SQL）"""
    session = Session()
    
    try:
        # 1. 创建卡片分类
        category_name = f"Test Category {random_string()}"
        result = session.execute(
            text("INSERT INTO cardcategory (name) VALUES (:name)"),
            {"name": category_name}
        )
        session.commit()
        
        # 获取新创建的分类ID
        result = session.execute(
            text("SELECT id FROM cardcategory WHERE name = :name"),
            {"name": category_name}
        )
        category_id = result.scalar()
        print(f"创建的分类ID: {category_id}")
        
        # 2. 创建卡片
        headline = f"Test Card {random_string()}"
        content = f"Test content {random_string(20)}"
        now = datetime.now()
        end_time = now + timedelta(days=7)
        
        session.execute(
            text("""
                INSERT INTO card 
                (type, headline, content, cardcategory_id, begintime, endtime, createtime, updatetime) 
                VALUES (:type, :headline, :content, :category_id, :begintime, :endtime, :createtime, :updatetime)
            """),
            {
                "type": 1, 
                "headline": headline, 
                "content": content,
                "category_id": category_id,
                "begintime": now,
                "endtime": end_time,
                "createtime": now,
                "updatetime": now
            }
        )
        session.commit()
        
        # 3. 查询卡片
        result = session.execute(
            text("SELECT * FROM card WHERE headline = :headline"),
            {"headline": headline}
        )
        card = result.mappings().first()
        
        if card:
            print(f"卡片ID: {card['id']}")
            print(f"卡片标题: {card['headline']}")
            print(f"卡片内容: {card['content']}")
            print(f"卡片类型: {card['type']}")
            print(f"卡片分类ID: {card['cardcategory_id']}")
            
            # 4. 更新卡片状态（完成）
            session.execute(
                text("UPDATE card SET donetime = :donetime WHERE id = :id"),
                {"donetime": datetime.now(), "id": card['id']}
            )
            session.commit()
            
            # 5. 再次查询验证更新
            result = session.execute(
                text("SELECT * FROM card WHERE id = :id"),
                {"id": card['id']}
            )
            updated_card = result.mappings().first()
            
            print(f"卡片完成时间: {updated_card['donetime']}")
            print("测试成功!")
            return True
        else:
            print("未找到卡片!")
            return False
    
    except Exception as e:
        session.rollback()
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        session.close()

if __name__ == "__main__":
    success = test_card_operations()
    print(f"测试结果: {'成功' if success else '失败'}")
