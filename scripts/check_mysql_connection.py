#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MySQL连接检测脚本
检测当前是否能够连接到MySQL数据库

使用方法:
    python scripts/check_mysql_connection.py
    python scripts/check_mysql_connection.py --config-type mysql
    python scripts/check_mysql_connection.py --verbose
"""

import os
import sys
import yaml
import argparse
import pymysql
import sqlite3
from urllib.parse import urlparse
from datetime import datetime
import json

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

class DatabaseConnectionChecker:
    """数据库连接检测器"""
    
    def __init__(self, verbose=False):
        self.verbose = verbose
        self.config_dir = os.path.join(project_root, 'configs')
        self.woniunote_config_dir = os.path.join(project_root, 'woniunote', 'configs')
        
    def log(self, message, level="INFO"):
        """日志输出"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if self.verbose or level in ["ERROR", "SUCCESS", "WARNING"]:
            print(f"[{timestamp}] {level}: {message}")
    
    def load_config(self, config_file_path=None):
        """加载配置文件"""
        if config_file_path:
            # 使用指定的配置文件
            config_files = [config_file_path]
        else:
            # 使用默认配置文件搜索路径
            config_files = [
                os.path.join(self.config_dir, 'user_password_config.yaml'),
                os.path.join(self.woniunote_config_dir, 'user_password_config.yaml')
            ]
        
        for config_file in config_files:
            if os.path.exists(config_file):
                self.log(f"找到配置文件: {config_file}")
                try:
                    with open(config_file, 'r', encoding='utf-8') as f:
                        config = yaml.safe_load(f)
                    return config, config_file
                except Exception as e:
                    self.log(f"解析配置文件失败: {e}", "ERROR")
                    continue
        
        self.log("未找到配置文件", "ERROR")
        return None, None
    
    def parse_database_config(self, config):
        """解析数据库配置"""
        if not config or 'database' not in config:
            self.log("配置中未找到数据库配置", "ERROR")
            return None
            
        db_config = config['database']
        self.log(f"数据库配置: {json.dumps(db_config, ensure_ascii=False, indent=2)}")
        
        # 处理SQLALCHEMY_DATABASE_URI格式
        if 'SQLALCHEMY_DATABASE_URI' in db_config:
            uri = db_config['SQLALCHEMY_DATABASE_URI']
            self.log(f"数据库URI: {uri}")
            
            if uri.startswith('sqlite:'):
                return {
                    'type': 'sqlite',
                    'uri': uri,
                    'path': uri.replace('sqlite:///', '').replace('sqlite://', '')
                }
            elif uri.startswith('mysql:'):
                # 解析MySQL URI: mysql://username:password@host:port/database
                parsed = urlparse(uri)
                return {
                    'type': 'mysql',
                    'host': parsed.hostname,
                    'port': parsed.port or 3306,
                    'username': parsed.username,
                    'password': parsed.password,
                    'database': parsed.path.lstrip('/'),
                    'uri': uri
                }
        
        # 处理分离配置格式
        if all(key in db_config for key in ['host', 'username', 'password', 'name']):
            return {
                'type': 'mysql',
                'host': db_config['host'],
                'port': db_config.get('port', 3306),
                'username': db_config['username'],
                'password': db_config['password'],
                'database': db_config['name']
            }
        
        self.log("无法解析数据库配置格式", "ERROR")
        return None
    
    def check_mysql_connection(self, db_config):
        """检测MySQL连接"""
        self.log("开始检测MySQL连接...")
        
        try:
            # 创建连接
            connection = pymysql.connect(
                host=db_config['host'],
                port=db_config['port'],
                user=db_config['username'],
                password=db_config['password'],
                database=db_config['database'],
                charset='utf8mb4',
                connect_timeout=10,
                read_timeout=10,
                write_timeout=10
            )
            
            self.log("MySQL连接成功！", "SUCCESS")
            
            # 执行基本查询测试
            with connection.cursor() as cursor:
                # 测试数据库版本
                cursor.execute("SELECT VERSION()")
                version = cursor.fetchone()[0]
                self.log(f"MySQL版本: {version}")
                
                # 测试当前数据库
                cursor.execute("SELECT DATABASE()")
                current_db = cursor.fetchone()[0]
                self.log(f"当前数据库: {current_db}")
                
                # 测试表数量
                cursor.execute("SHOW TABLES")
                tables = cursor.fetchall()
                self.log(f"数据库中的表数量: {len(tables)}")
                
                if self.verbose and tables:
                    self.log("数据库表列表:")
                    for table in tables:
                        self.log(f"  - {table[0]}")
                
                # 测试基本权限
                cursor.execute("SELECT 1")
                self.log("基本查询权限: 正常")
            
            connection.close()
            return True
            
        except pymysql.Error as e:
            self.log(f"MySQL连接失败: {e}", "ERROR")
            self.log(f"错误码: {e.args[0] if e.args else 'N/A'}", "ERROR")
            return False
        except Exception as e:
            self.log(f"连接过程中发生错误: {e}", "ERROR")
            return False
    
    def check_sqlite_connection(self, db_config):
        """检测SQLite连接"""
        self.log("检测到SQLite配置，进行连接测试...")
        
        try:
            db_path = db_config['path']
            
            # 检查文件是否存在
            if not os.path.exists(db_path):
                self.log(f"SQLite数据库文件不存在: {db_path}", "WARNING")
                self.log("尝试创建数据库文件...")
                
            # 尝试连接
            connection = sqlite3.connect(db_path, timeout=10)
            self.log("SQLite连接成功！", "SUCCESS")
            
            # 基本测试
            cursor = connection.cursor()
            cursor.execute("SELECT sqlite_version()")
            version = cursor.fetchone()[0]
            self.log(f"SQLite版本: {version}")
            
            # 检查表
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            self.log(f"数据库中的表数量: {len(tables)}")
            
            if self.verbose and tables:
                self.log("数据库表列表:")
                for table in tables:
                    self.log(f"  - {table[0]}")
            
            connection.close()
            return True
            
        except sqlite3.Error as e:
            self.log(f"SQLite连接失败: {e}", "ERROR")
            return False
        except Exception as e:
            self.log(f"连接过程中发生错误: {e}", "ERROR")
            return False
    
    def check_dependencies(self):
        """检查依赖包"""
        self.log("检查依赖包...")
        
        missing_deps = []
        
        try:
            import pymysql
            self.log("✓ pymysql 已安装")
        except ImportError:
            missing_deps.append("pymysql")
            self.log("✗ pymysql 未安装", "WARNING")
        
        try:
            import yaml
            self.log("✓ PyYAML 已安装")
        except ImportError:
            missing_deps.append("PyYAML")
            self.log("✗ PyYAML 未安装", "WARNING")
        
        if missing_deps:
            self.log(f"缺少依赖包: {', '.join(missing_deps)}", "ERROR")
            self.log(f"请运行: pip install {' '.join(missing_deps)}", "ERROR")
            return False
        
        return True
    
    def run_check(self, config_type=None, config_file_path=None, test_only=False):
        """运行连接检查"""
        self.log("=== MySQL数据库连接检测开始 ===")
        
        # 检查依赖
        if not self.check_dependencies():
            return False
        
        # 加载配置
        config, config_file = self.load_config(config_file_path)
        if not config:
            return False
        
        self.log(f"使用配置文件: {config_file}")
        
        # 解析数据库配置
        db_config = self.parse_database_config(config)
        if not db_config:
            return False
        
        # 如果只是测试配置解析
        if test_only:
            self.log("=== 配置解析测试完成 ===", "SUCCESS")
            self.log(f"数据库类型: {db_config['type']}")
            if db_config['type'] == 'mysql':
                self.log(f"MySQL主机: {db_config['host']}:{db_config['port']}")
                self.log(f"数据库名: {db_config['database']}")
                self.log(f"用户名: {db_config['username']}")
                self.log("配置解析成功", "SUCCESS")
            return True
        
        # 根据配置类型进行检测
        if config_type == 'mysql' or db_config['type'] == 'mysql':
            if db_config['type'] != 'mysql':
                self.log("强制使用MySQL配置类型，但当前配置不是MySQL", "ERROR")
                return False
            return self.check_mysql_connection(db_config)
        elif db_config['type'] == 'sqlite':
            self.log("检测到SQLite配置", "INFO")
            return self.check_sqlite_connection(db_config)
        else:
            self.log(f"不支持的数据库类型: {db_config['type']}", "ERROR")
            return False

def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='检测MySQL数据库连接状态',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python scripts/check_mysql_connection.py
  python scripts/check_mysql_connection.py --verbose
  python scripts/check_mysql_connection.py --config-type mysql
        """
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='显示详细输出'
    )
    
    parser.add_argument(
        '--config-type',
        choices=['mysql', 'auto'],
        default='auto',
        help='指定配置类型 (default: auto)'
    )
    
    parser.add_argument(
        '--config-file',
        help='指定配置文件路径'
    )
    
    parser.add_argument(
        '--test-only',
        action='store_true',
        help='仅测试配置解析，不实际连接数据库'
    )
    
    args = parser.parse_args()
    
    # 创建检测器
    checker = DatabaseConnectionChecker(verbose=args.verbose)
    
    # 运行检测
    try:
        success = checker.run_check(
            config_type=args.config_type if args.config_type != 'auto' else None,
            config_file_path=args.config_file,
            test_only=args.test_only
        )
        
        if success:
            checker.log("=== 数据库连接检测成功 ===", "SUCCESS")
            sys.exit(0)
        else:
            checker.log("=== 数据库连接检测失败 ===", "ERROR")
            sys.exit(1)
            
    except KeyboardInterrupt:
        checker.log("检测被用户中断", "WARNING")
        sys.exit(1)
    except Exception as e:
        checker.log(f"检测过程中发生未预期的错误: {e}", "ERROR")
        sys.exit(1)

if __name__ == '__main__':
    main()