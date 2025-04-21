#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
启动 WoniuNote 服务器

此脚本用于启动 WoniuNote Flask 服务器，支持测试模式
"""

import sys
import os
import argparse
from woniunote.app import app

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='启动 WoniuNote 服务器')
    parser.add_argument('--host', type=str, default='127.0.0.1', help='服务器主机地址')
    parser.add_argument('--port', type=int, default=5001, help='服务器端口')
    parser.add_argument('--debug', action='store_true', help='启用调试模式')
    parser.add_argument('--test', action='store_true', help='测试模式，使用测试数据库')
    parser.add_argument('--http', action='store_true', help='使用HTTP协议而非HTTPS')
    return parser.parse_args()

def main():
    """主函数"""
    args = parse_args()
    
    # 设置测试模式环境变量，如果需要的话
    if args.test:
        os.environ['WONIUNOTE_TEST_MODE'] = 'true'
        print(f"[INFO] 以测试模式运行服务器，使用测试数据库")
    
    print(f"[INFO] 启动服务器: {args.host}:{args.port}")
    
    # 去除 HTTPS 设置，方便测试
    ssl_context = None
    protocol = "HTTP"
    
    # 除非明确要求HTTP，否则使用HTTPS
    if not args.http:
        ssl_context = 'adhoc'  # 使用自签名证书启用 HTTPS
        protocol = "HTTPS"
    
    print(f"[INFO] 使用{protocol}协议")
    
    # 启动 Flask 应用
    app.run(
        host=args.host,
        port=args.port,
        debug=args.debug,
        ssl_context=ssl_context
    )

if __name__ == "__main__":
    sys.exit(main())
