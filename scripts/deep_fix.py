"""
深度修复 WoniuNote 中的所有控制器文件，解决视图函数返回整数的问题
"""

import os
import re
import sys

def find_and_fix_integer_returns(directory):
    """在所有控制器文件中查找并修复直接返回整数的问题"""
    controller_dir = os.path.join(directory, 'woniunote', 'controller')
    fixed_files = []
    patterns = [
        r'(\s+)return\s+(\d+)(\s*$|\s*#.*$)',  # 直接返回数字
        r'(\s+)return\s+(id|card_id|item_id|article_id|user_id|[\w_]+_id)(\s*$|\s*#.*$)',  # 返回ID变量
    ]
    
    print("开始深度检查并修复所有控制器文件...")
    
    for root, _, files in os.walk(controller_dir):
        for filename in files:
            if filename.endswith('.py'):
                file_path = os.path.join(root, filename)
                file_content = None
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    file_content = f.read()
                
                modified = False
                
                # 模式1: 直接返回数字
                for pattern in patterns:
                    def replace_func(match):
                        nonlocal modified
                        indent = match.group(1)
                        value = match.group(2)
                        comment = match.group(3) if len(match.groups()) > 2 else ''
                        modified = True
                        return f"{indent}return render_template('error-404.html'), 404{comment}"
                    
                    new_content, count = re.subn(pattern, replace_func, file_content)
                    if count > 0:
                        file_content = new_content
                        print(f"  在 {filename} 中找到并修复了 {count} 处返回整数的问题")
                
                # 模式2: 检查 before_request 钩子
                before_hook_pattern = r'(@\w+\.before_request\s*\n\s*def\s+\w+\([^)]*\):.*?)(return\s+["\'].*?["\'])'
                new_content, count = re.subn(
                    before_hook_pattern,
                    r'\1return jsonify({"error": "forbidden"}), 403',
                    file_content,
                    flags=re.DOTALL
                )
                if count > 0:
                    file_content = new_content
                    modified = True
                    print(f"  在 {filename} 中找到并修复了 {count} 处 before_request 钩子返回值问题")
                
                # 模式3: 检查可能返回None的函数
                none_return_pattern = r'(def\s+\w+\([^)]*\):.*?)(\s+return\s+None)'
                new_content, count = re.subn(
                    none_return_pattern,
                    r'\1\2 if request.method == "GET" else jsonify({"status": "ok"})',
                    file_content,
                    flags=re.DOTALL
                )
                if count > 0:
                    file_content = new_content
                    modified = True
                    print(f"  在 {filename} 中找到并修复了 {count} 处可能返回None的问题")
                
                if modified:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(file_content)
                    fixed_files.append(filename)
    
    if fixed_files:
        print(f"\n成功修复了以下 {len(fixed_files)} 个文件:")
        for file in fixed_files:
            print(f"  - {file}")
    else:
        print("\n未发现需要修复的控制器文件。")
    
    # 特殊处理: 检查app.py中所有路由定义
    app_path = os.path.join(directory, 'woniunote', 'app.py')
    if os.path.exists(app_path):
        print("\n正在检查主应用文件 app.py...")
        with open(app_path, 'r', encoding='utf-8') as f:
            app_content = f.read()
        
        # 查找所有路由函数
        route_pattern = r'(@app\.route\([^)]+\)\s*\n\s*def\s+\w+\([^)]*\):\s*.*?)(return\s+\d+)'
        new_content, count = re.subn(
            route_pattern,
            r'\1return render_template("error-404.html"), 404',
            app_content,
            flags=re.DOTALL
        )
        if count > 0:
            with open(app_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"  在 app.py 中修复了 {count} 处路由函数返回问题")
        else:
            print("  app.py 中未发现需要修复的路由函数。")

if __name__ == "__main__":
    project_dir = os.path.dirname(os.path.abspath(__file__))
    find_and_fix_integer_returns(project_dir)
    print("\n修复完成! 请重启Flask应用以应用更改。")
