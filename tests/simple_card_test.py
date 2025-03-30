"""
简化的卡片模型测试
"""
import os
import sys
from datetime import datetime, timedelta

# 添加项目根目录到Python路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# 导入测试助手中的组件
from tests.test_helpers import (
    app, db, Card, CardCategory, random_string
)

def test_card_model():
    """简化的卡片模型创建和查询测试"""
    with app.app_context():
        # 确保表存在
        db.create_all()
        
        try:
            # 创建卡片分类
            category_name = f"Test Category {random_string(8)}"
            category = CardCategory(name=category_name)
            db.session.add(category)
            db.session.commit()
            
            # 确认创建成功
            print(f"创建的分类: {category.id}, {category.name}")
            
            # 创建卡片
            headline = f"Test Card {random_string(8)}"
            content = f"Test Content {random_string(20)}"
            now = datetime.now()
            
            card = Card(
                type=1,
                headline=headline,
                content=content,
                cardcategory_id=category.id,
                begintime=now,
                endtime=now + timedelta(days=7),
                createtime=now,
                updatetime=now
            )
            db.session.add(card)
            db.session.commit()
            
            # 确认创建成功
            print(f"创建的卡片: {card.id}, {card.headline}")
            
            # 查询卡片
            query_card = db.session.query(Card).filter_by(headline=headline).first()
            
            if query_card:
                print("查询成功:")
                print(f"  ID: {query_card.id}")
                print(f"  标题: {query_card.headline}")
                print(f"  内容: {query_card.content}")
                print(f"  分类ID: {query_card.cardcategory_id}")
                print(f"  创建时间: {query_card.createtime}")
                
                # 测试兼容性属性
                print(f"  完成状态(done): {query_card.done}")
                print(f"  优先级(priority): {query_card.priority}")
                print(f"  用户ID(userid): {query_card.userid}")
                
                # 更新完成状态
                query_card.done = 1
                db.session.commit()
                
                # 再次查询确认更新成功
                updated_card = db.session.query(Card).get(query_card.id)
                print("\n更新后状态:")
                print(f"  完成状态: {updated_card.done}")
                print(f"  完成时间: {updated_card.donetime}")
                
                print("\n测试成功!")
                return True
            else:
                print("卡片查询失败!")
                return False
                
        except Exception as e:
            print(f"测试失败: {e}")
            import traceback
            traceback.print_exc()
            return False
            
        finally:
            # 清理测试数据
            db.session.query(Card).delete()
            db.session.query(CardCategory).delete()
            db.session.commit()

if __name__ == "__main__":
    success = test_card_model()
    print(f"\n测试结果: {'成功' if success else '失败'}")
