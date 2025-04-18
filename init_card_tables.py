#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
初始化Card模块所需的数据库表
"""
from woniunote.app import create_app
from woniunote.common.database import db
from woniunote.controller.card_center import Card, CardCategory
import datetime

def init_card_tables():
    """创建Card相关表并初始化默认数据"""
    print("开始初始化Card数据库表...")
    
    # 创建应用上下文
    app = create_app()
    
    with app.app_context():
        # 检查表是否存在
        try:
            # 尝试查询，如果出错说明表不存在
            CardCategory.query.first()
            print("表已存在，无需创建")
        except Exception as e:
            print(f"表不存在，开始创建: {str(e)}")
            # 创建表
            db.create_all()
            
            # 添加默认分类
            default_categories = [
                CardCategory(id=1, name="待办卡片"),
                CardCategory(id=2, name="已完成")
            ]
            
            for category in default_categories:
                # 检查分类是否已存在
                existing = CardCategory.query.filter_by(id=category.id).first()
                if not existing:
                    db.session.add(category)
            
            # 添加示例卡片
            example_card = Card(
                headline="这是一个示例卡片", 
                cardcategory_id=1,
                createtime=datetime.datetime.now(),
                type=1
            )
            db.session.add(example_card)
            
            # 提交事务
            db.session.commit()
            print("Card表创建完成并初始化了默认数据")


if __name__ == "__main__":
    init_card_tables()
