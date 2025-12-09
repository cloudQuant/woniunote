#!/usr/bin/env python3
"""
双端推送脚本

用于将代码同时推送到 Gitee 和 GitHub 仓库。
支持自动添加、提交和推送操作。

使用方法:
    python push_to_both.py [commit_message]

参数:
    commit_message: 提交信息（可选，默认为 Auto commit at YYYY-MM-DD HH:MM:SS）
"""

import subprocess
import sys
import os
from datetime import datetime

def run_command(command: str, description: str) -> bool:
    """
    执行命令并处理结果
    
    Args:
        command: 要执行的 shell 命令
        description: 命令描述（用于日志显示）
        
    Returns:
        bool: 命令是否执行成功
    """
    print(f"\n🔄 {description}...")
    print(f"执行命令: {command}")
    
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, encoding='utf-8')
        
        if result.returncode == 0:
            print(f"✅ {description}成功")
            if result.stdout.strip():
                print(f"输出: {result.stdout.strip()}")
        else:
            print(f"❌ {description}失败")
            print(f"错误: {result.stderr.strip()}")
            return False
            
    except Exception as e:
        print(f"❌ {description}异常: {str(e)}")
        return False
    
    return True

def main():
    """
    主函数
    
    执行 git add, commit, push 流程。
    """
    print("🚀 开始同时推送到Gitee和GitHub...")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 获取提交信息
    if len(sys.argv) > 1:
        commit_message = " ".join(sys.argv[1:])
    else:
        commit_message = f"Auto commit at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    
    print(f"提交信息: {commit_message}")
    
    # 检查当前分支
    if not run_command("git branch --show-current", "获取当前分支"):
        return
    
    # 添加所有文件
    if not run_command("git add .", "添加文件到暂存区"):
        return
    
    # 提交更改
    if not run_command(f'git commit -m "{commit_message}"', "提交更改"):
        return
    
    # 推送到Gitee
    if not run_command("git push gitee", "推送到Gitee"):
        print("⚠️  Gitee推送失败，但继续尝试GitHub...")
    
    # 推送到GitHub
    if not run_command("git push github", "推送到GitHub"):
        print("⚠️  GitHub推送失败")
    
    print("\n🎉 推送操作完成！")
    print("📊 推送结果:")
    print("   - Gitee: https://gitee.com/yunjinqi/woniunote")
    print("   - GitHub: https://github.com/cloudQuant/woniunote")

if __name__ == "__main__":
    main()
