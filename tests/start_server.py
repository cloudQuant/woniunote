#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
启动 WoniuNote 服务器

此脚本用于启动 WoniuNote Flask 服务器，支持测试模式
"""

import sys
import os
import argparse
import pymysql

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='启动 WoniuNote 服务器')
    parser.add_argument('--host', type=str, default='127.0.0.1', help='服务器主机地址')
    parser.add_argument('--port', type=int, default=5001, help='服务器端口')
    parser.add_argument('--debug', action='store_true', help='启用调试模式')
    parser.add_argument('--test', action='store_true', help='测试模式，使用测试数据库')
    parser.add_argument('--http', action='store_true', help='使用HTTP协议而非HTTPS')
    return parser.parse_args()

# ---------------------------------------------------------------------------
# 数据库准备逻辑（仅限测试）
# ---------------------------------------------------------------------------

def ensure_article_table():
    """确保测试数据库中存在 article 表，并且 type 字段是 VARCHAR(10)"""
    try:
        # 动态导入测试数据库配置
        from tests.utils.test_config import DATABASE_CONFIG

        conn = pymysql.connect(
            host=DATABASE_CONFIG["host"],
            port=DATABASE_CONFIG["port"],
            user=DATABASE_CONFIG["user"],
            password=DATABASE_CONFIG["password"],
            database=DATABASE_CONFIG["database"],
            charset="utf8mb4",
            autocommit=True,
        )

        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS article (
                    articleid INT AUTO_INCREMENT PRIMARY KEY,
                    userid INT NULL,
                    type VARCHAR(10) NOT NULL DEFAULT '1',
                    headline VARCHAR(100) NOT NULL,
                    content TEXT,
                    createtime DATETIME NULL,
                    updatetime DATETIME NULL
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                """
            )

            # 确保 type 字段为 varchar(10)
            cur.execute(
                """
                SELECT DATA_TYPE, CHARACTER_MAXIMUM_LENGTH
                FROM information_schema.columns
                WHERE table_schema = DATABASE() AND table_name = 'article' AND column_name = 'type';
                """
            )
            dtype, length = cur.fetchone()
            if dtype.lower() != "varchar" or length != 10:
                # 修改字段类型
                cur.execute("ALTER TABLE article MODIFY COLUMN type VARCHAR(10) NOT NULL DEFAULT '1';")

        conn.close()
    except Exception as exc:
        print(f"[WARN] 准备 article 表时发生错误: {exc}")

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
    
    # 在导入 Flask 应用前确保数据库准备就绪
    ensure_article_table()
    
    # 现在导入 Flask 应用
    from woniunote.app import app
    
    # 启动 Flask 应用
    app.run(
        host=args.host,
        port=args.port,
        debug=args.debug,
        ssl_context=ssl_context
    )

if __name__ == "__main__":
    sys.exit(main())
