import os
import sys

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath('.'))

from woniunote.app import create_app
from woniunote.controller.todo_center import Item, Category
from woniunote.common.database import db

def fix_todo():
    """修复todo功能的数据库表和默认分类"""
    # 创建应用上下文
    app = create_app()
    
    with app.app_context():
        # 确保数据库表存在
        print("正在确保todo相关数据库表已创建...")
        db.create_all()
        
        # 检查是否有默认分类，如果没有则创建
        default_category = Category.query.filter_by(id=1).first()
        if not default_category:
            print("创建默认分类...")
            default_category = Category(name="默认分类")
            db.session.add(default_category)
            db.session.commit()
            print(f"默认分类创建成功，ID: {default_category.id}")
        else:
            print(f"默认分类已存在，ID: {default_category.id}")
        
        # 检查模板文件是否存在
        template_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                                   'woniunote', 'template', 'todo_index.html')
        if os.path.exists(template_path):
            print(f"模板文件存在: {template_path}")
        else:
            print(f"警告: 模板文件不存在: {template_path}")
        
        print("\n访问 Todo 功能的步骤:")
        print("1. 确保已登录系统")
        print("2. 访问URL: /todo/ (注意末尾的斜杠)")
        
        print("\nTodo功能应该可以正常工作了！")

if __name__ == "__main__":
    fix_todo()
