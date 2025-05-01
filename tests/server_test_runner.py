#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
WoniuNote测试专用服务器启动脚本

此脚本专门用于测试环境，自动配置测试数据库和测试环境
"""

import os
import sys
import argparse
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)
logger = logging.getLogger('test_server')

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='WoniuNote Test Server')
    parser.add_argument('--port', type=int, default=5001, help='Server port')
    parser.add_argument('--host', type=str, default='127.0.0.1', help='Server host')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    return parser.parse_args()

def main():
    """主函数"""
    args = parse_args()
    
    # 1. 设置项目路径
    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, project_dir)
    logger.info(f"项目路径: {project_dir}")
    
    # 2. 设置测试环境变量
    os.environ['FLASK_ENV'] = 'testing'
    os.environ['TESTING'] = 'true'
    os.environ['FLASK_DEBUG'] = '1' if args.debug else '0'
    os.environ['PYTHONPATH'] = project_dir
    
    # 3. 设置测试数据库配置
    os.environ['WONIUNOTE_TEST_MODE'] = 'true'
    os.environ['WONIUNOTE_DB_TEST'] = 'true'
    
    # 4. 导入应用
    try:
        logger.info("导入Flask应用...")
        from woniunote.app import app
        
        # 5. 配置应用为测试模式
        app.config['TESTING'] = True
        app.config['DEBUG'] = args.debug
        app.config['SERVER_NAME'] = f"{args.host}:{args.port}"
        
        # 设置测试数据库配置
        app.config['DATABASE'] = {
            'host': '127.0.0.1',
            'port': 3306,
            'user': 'woniunote_test',
            'password': 'test123',
            'database': 'woniunote_test'
        }
        
        # 6. 启动服务器
        logger.info(f"启动服务器 {args.host}:{args.port}...")
        app.run(
            host=args.host,
            port=args.port,
            debug=args.debug,
            use_reloader=False  # 测试模式下禁用reloader以避免重复创建进程
        )
        
    except ImportError as e:
        logger.error(f"导入Flask应用失败: {e}")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"启动服务器时出错: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
