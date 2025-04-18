"""
简单的连接验证脚本，不依赖测试框架
"""

import requests
import time
import sys

def test_server_connectivity(port=5001):
    """测试服务器连接性"""
    url = f"http://localhost:{port}"
    
    print(f"尝试连接到 {url}")
    max_retries = 5
    
    for i in range(max_retries):
        try:
            print(f"尝试 {i+1}/{max_retries}...")
            response = requests.get(url, timeout=5)
            print(f"连接成功！状态码: {response.status_code}")
            print(f"响应头: {dict(response.headers)}")
            print(f"响应内容前100个字符: {response.text[:100]}")
            return True
        except Exception as e:
            print(f"连接失败: {type(e).__name__}: {e}")
            if i < max_retries - 1:
                print(f"等待2秒后重试...")
                time.sleep(2)
    
    print("所有尝试都失败了")
    return False

if __name__ == "__main__":
    # 允许通过命令行参数传入端口
    port = 5001
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print(f"无效的端口参数: {sys.argv[1]}")
    
    success = test_server_connectivity(port)
    if success:
        print("连接测试成功")
        sys.exit(0)
    else:
        print("连接测试失败")
        sys.exit(1)
