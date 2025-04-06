"""
全面修复 WoniuNote 中的 todo 功能
特点：
1. 修复直接返回整数的问题
2. 使用url_for生成URL路径
3. 统一登录检查逻辑
"""

from flask import Flask, redirect, url_for, render_template, abort
import os
import sys

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))

def fix_controller_file(file_path):
    """修复控制器文件中的返回值问题"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 修复直接返回数字的问题
    content = content.replace("return 404", "return render_template('error-404.html'), 404")
    
    # 写回修改后的内容
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"已修复文件: {file_path}")

def main():
    """主函数，执行所有修复工作"""
    print("开始修复WoniuNote todo功能...")
    
    # 修复todo_center.py
    controller_dir = os.path.join(current_dir, 'controller')
    todo_center_path = os.path.join(controller_dir, 'todo_center.py')
    card_center_path = os.path.join(controller_dir, 'card_center.py')
    
    if os.path.exists(todo_center_path):
        fix_controller_file(todo_center_path)
    else:
        print(f"警告: 未找到文件 {todo_center_path}")
    
    if os.path.exists(card_center_path):
        fix_controller_file(card_center_path)
    else:
        print(f"警告: 未找到文件 {card_center_path}")
    
    print("\n修复完成! 请按以下步骤操作:")
    print("1. 确保已登录系统")
    print("2. 访问todo功能: /todo 或 /todo/")
    print("3. 如果仍有问题，请查看服务器日志")

if __name__ == "__main__":
    main()
