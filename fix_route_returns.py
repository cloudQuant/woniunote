import os
import re
import sys

def fix_direct_returns(directory):
    """修复所有控制器文件中直接返回整数的问题"""
    # 要检查的目录
    controllers_dir = os.path.join(directory, 'woniunote', 'controller')
    pattern = r'(\s+return\s+)(\d+)(\s*$|\s*#.*$)'
    replacement = r'\1render_template("error-404.html"), \2'
    
    found_issues = False
    
    print("开始检查并修复控制器文件中的错误返回...")
    
    for root, _, files in os.walk(controllers_dir):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 查找并修复错误
                new_content, count = re.subn(pattern, replacement, content)
                if count > 0:
                    print(f"在 {file} 中找到 {count} 处直接返回整数的问题")
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    found_issues = True
    
    if not found_issues:
        print("未发现直接返回整数的问题")
    else:
        print("修复完成！请重启Flask服务器。")

if __name__ == "__main__":
    # 获取项目根目录
    project_dir = os.path.dirname(os.path.abspath(__file__))
    fix_direct_returns(project_dir)
