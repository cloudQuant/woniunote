#!/usr/bin/env python3
"""
数据库索引优化脚本
为 WoniuNote 项目添加关键索引以提升查询性能
"""
import sys
import os
import logging
import time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import yaml

def _read_db_uri():
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    candidates = [
        os.path.join(repo_root, 'configs', 'user_password_config.yaml'),
        os.path.join(repo_root, 'woniunote', 'configs', 'user_password_config.yaml'),
    ]
    for p in candidates:
        if os.path.exists(p):
            with open(p, 'r', encoding='utf-8') as f:
                cfg = yaml.safe_load(f)
                return cfg['database']['SQLALCHEMY_DATABASE_URI']
    return os.environ.get('SQLALCHEMY_DATABASE_URI', '')
from woniunote.common.utils import get_db_connection, parse_db_uri

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 需要添加的索引定义
INDEXES_TO_ADD = [
    # 文章表索引
    {
        'table': 'article',
        'name': 'idx_article_userid',
        'columns': ['userid'],
        'description': '文章用户ID索引，用于查询用户的文章'
    },
    {
        'table': 'article',
        'name': 'idx_article_type',
        'columns': ['type'],
        'description': '文章类型索引，用于按类型查询文章'
    },
    {
        'table': 'article',
        'name': 'idx_article_createtime',
        'columns': ['createtime'],
        'description': '文章创建时间索引，用于按时间排序'
    },
    {
        'table': 'article',
        'name': 'idx_article_readcount',
        'columns': ['readcount'],
        'description': '文章阅读数索引，用于热门文章查询'
    },
    {
        'table': 'article',
        'name': 'idx_article_recommended',
        'columns': ['recommended'],
        'description': '推荐文章索引'
    },
    {
        'table': 'article',
        'name': 'idx_article_hidden_checked',
        'columns': ['hidden', 'checked'],
        'description': '文章状态复合索引，用于过滤显示文章'
    },
    {
        'table': 'article',
        'name': 'idx_article_type_createtime',
        'columns': ['type', 'createtime'],
        'description': '文章类型和时间复合索引'
    },
    
    # 评论表索引
    {
        'table': 'comment',
        'name': 'idx_comment_articleid',
        'columns': ['articleid'],
        'description': '评论文章ID索引，用于查询文章评论'
    },
    {
        'table': 'comment',
        'name': 'idx_comment_userid',
        'columns': ['userid'],
        'description': '评论用户ID索引，用于查询用户评论'
    },
    {
        'table': 'comment',
        'name': 'idx_comment_createtime',
        'columns': ['createtime'],
        'description': '评论创建时间索引'
    },
    {
        'table': 'comment',
        'name': 'idx_comment_replyid',
        'columns': ['replyid'],
        'description': '评论回复ID索引，用于查询回复关系'
    },
    
    # 用户表索引
    {
        'table': 'users',
        'name': 'idx_users_username',
        'columns': ['username'],
        'description': '用户名索引，用于登录验证'
    },
    {
        'table': 'users',
        'name': 'idx_users_role',
        'columns': ['role'],
        'description': '用户角色索引'
    },
    {
        'table': 'users',
        'name': 'idx_users_createtime',
        'columns': ['createtime'],
        'description': '用户注册时间索引'
    },
    
    # 收藏表索引
    {
        'table': 'favorite',
        'name': 'idx_favorite_userid',
        'columns': ['userid'],
        'description': '收藏用户ID索引'
    },
    {
        'table': 'favorite',
        'name': 'idx_favorite_articleid',
        'columns': ['articleid'],
        'description': '收藏文章ID索引'
    },
    {
        'table': 'favorite',
        'name': 'idx_favorite_user_article',
        'columns': ['userid', 'articleid'],
        'description': '用户文章收藏复合索引，防止重复收藏'
    },
    
    # 积分表索引
    {
        'table': 'credit',
        'name': 'idx_credit_userid',
        'columns': ['userid'],
        'description': '积分用户ID索引'
    },
    {
        'table': 'credit',
        'name': 'idx_credit_category',
        'columns': ['category'],
        'description': '积分类别索引'
    },
    {
        'table': 'credit',
        'name': 'idx_credit_createtime',
        'columns': ['createtime'],
        'description': '积分创建时间索引'
    },
    
    # 卡片相关索引（如果存在）
    {
        'table': 'card',
        'name': 'idx_card_categoryid',
        'columns': ['cardcategory_id'],
        'description': '卡片分类索引'
    },
    {
        'table': 'card',
        'name': 'idx_card_type',
        'columns': ['type'],
        'description': '卡片类型索引'
    },
    {
        'table': 'card',
        'name': 'idx_card_createtime',
        'columns': ['createtime'],
        'description': '卡片创建时间索引'
    }
]

def check_table_exists(cursor, table_name):
    """检查表是否存在"""
    cursor.execute("""
        SELECT COUNT(*) AS cnt
        FROM information_schema.tables 
        WHERE table_schema = DATABASE() 
          AND table_name = %s
    """, (table_name,))
    row = cursor.fetchone()
    return (row.get('cnt') if isinstance(row, dict) else row[0]) > 0

def check_index_exists(cursor, table_name, index_name):
    """检查索引是否存在"""
    cursor.execute("""
        SELECT COUNT(*) AS cnt
        FROM information_schema.statistics 
        WHERE table_schema = DATABASE() 
          AND table_name = %s 
          AND index_name = %s
    """, (table_name, index_name))
    row = cursor.fetchone()
    return (row.get('cnt') if isinstance(row, dict) else row[0]) > 0

def create_index(cursor, index_info):
    """创建索引"""
    table = index_info['table']
    name = index_info['name']
    columns = index_info['columns']
    description = index_info['description']
    
    # 检查表是否存在
    if not check_table_exists(cursor, table):
        logger.warning(f"表 {table} 不存在，跳过索引 {name}")
        return False
    
    # 检查索引是否已存在
    if check_index_exists(cursor, table, name):
        logger.info(f"索引 {name} 已存在，跳过")
        return True
    
    # 构建创建索引的SQL
    columns_str = ', '.join([f"`{col}`" for col in columns])
    sql = f"CREATE INDEX `{name}` ON `{table}` ({columns_str})"
    
    try:
        logger.info(f"创建索引: {name} ({description})")
        start_time = time.time()
        
        cursor.execute(sql)
        
        end_time = time.time()
        logger.info(f"索引 {name} 创建成功，耗时 {end_time - start_time:.2f} 秒")
        return True
        
    except Exception as e:
        logger.error(f"创建索引 {name} 失败: {str(e)}")
        return False

def analyze_table_performance(cursor):
    """分析表性能统计"""
    logger.info("分析表性能统计...")
    
    tables = ['article', 'users', 'comment', 'favorite', 'credit']
    
    for table in tables:
        if not check_table_exists(cursor, table):
            continue
            
        # 获取表行数
        cursor.execute(f"SELECT COUNT(*) AS cnt FROM `{table}`")
        rc = cursor.fetchone()
        row_count = rc.get('cnt') if isinstance(rc, dict) else rc[0]
        
        # 获取表大小
        cursor.execute("""
            SELECT 
                ROUND(((data_length + index_length) / 1024 / 1024), 2) AS total_size_mb,
                ROUND((data_length / 1024 / 1024), 2) AS data_size_mb,
                ROUND((index_length / 1024 / 1024), 2) AS index_size_mb
            FROM information_schema.tables 
            WHERE table_schema = DATABASE() 
              AND table_name = %s
        """, (table,))
        
        size_info = cursor.fetchone()
        if size_info:
            if isinstance(size_info, dict):
                total_size = size_info.get('total_size_mb')
                data_size = size_info.get('data_size_mb')
                index_size = size_info.get('index_size_mb')
            else:
                total_size, data_size, index_size = size_info
            logger.info(f"表 {table}: {row_count} 行, 总大小 {total_size}MB (数据 {data_size}MB, 索引 {index_size}MB)")

def optimize_database_indexes():
    """优化数据库索引"""
    try:
        # 获取数据库连接
        db_info = parse_db_uri(_read_db_uri())
        conn = get_db_connection(db_info)
        cursor = conn.cursor()
        try:
            cursor.execute('SET SESSION sql_mode=""')
        except Exception:
            pass
        
        logger.info("开始数据库索引优化...")
        
        # 分析当前表性能
        analyze_table_performance(cursor)
        
        # 创建索引
        success_count = 0
        skip_count = 0
        error_count = 0
        
        for index_info in INDEXES_TO_ADD:
            result = create_index(cursor, index_info)
            if result is True:
                success_count += 1
            elif result is None:
                skip_count += 1
            else:
                error_count += 1
        
        # 提交更改
        conn.commit()
        
        logger.info(f"索引优化完成: 成功 {success_count}, 跳过 {skip_count}, 失败 {error_count}")
        
        # 索引后修复可能受影响的用户密码数据
        try:
            import subprocess, sys as _sys
            subprocess.run([_sys.executable, os.path.join(os.path.dirname(__file__), 'repair_user_passwords.py')], check=True)
            logger.info("已执行用户密码修复脚本")
        except Exception as e:
            logger.warning(f"修复脚本执行失败: {e}")
        
        # 重新分析表性能
        logger.info("索引创建后的表性能:")
        analyze_table_performance(cursor)
        
        # 分析查询计划（可选）
        logger.info("建议运行 ANALYZE TABLE 命令更新表统计信息:")
        for table in ['article', 'users', 'comment', 'favorite', 'credit']:
            if check_table_exists(cursor, table):
                logger.info(f"ANALYZE TABLE `{table}`;")
        
        return True
        
    except Exception as e:
        logger.error(f"索引优化过程中发生错误: {str(e)}")
        if 'conn' in locals():
            conn.rollback()
        return False
        
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

def show_existing_indexes():
    """显示现有索引"""
    try:
        db_info = parse_db_uri(_read_db_uri())
        conn = get_db_connection(db_info)
        cursor = conn.cursor()
        try:
            cursor.execute('SET SESSION sql_mode=""')
        except Exception:
            pass
        
        logger.info("显示现有索引:")
        
        cursor.execute("""
            SELECT 
                table_name,
                index_name,
                GROUP_CONCAT(column_name ORDER BY seq_in_index) as columns,
                index_type,
                non_unique
            FROM information_schema.statistics 
            WHERE table_schema = DATABASE()
            AND table_name IN ('article', 'users', 'comment', 'favorite', 'credit', 'card')
            GROUP BY table_name, index_name, index_type, non_unique
            ORDER BY table_name, index_name
        """)
        
        results = cursor.fetchall()
        current_table = None
        
        for row in results:
            if isinstance(row, dict):
                table_name = row.get('table_name')
                index_name = row.get('index_name')
                columns = row.get('columns')
                index_type = row.get('index_type')
                non_unique = row.get('non_unique')
            else:
                table_name, index_name, columns, index_type, non_unique = row
            if table_name != current_table:
                logger.info(f"\n表 {table_name}:")
                current_table = table_name
            unique_str = "UNIQUE" if (non_unique == 0 or str(non_unique) == '0') else "NON-UNIQUE"
            logger.info(f"  {index_name}: {columns} ({unique_str}, {index_type})")
            
    except Exception as e:
        logger.error(f"显示索引时发生错误: {str(e)}")
        
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

def remove_unused_indexes():
    """移除不必要的索引（慎用）"""
    logger.warning("移除索引功能需要谨慎使用，请手动分析后执行")
    # 这里可以添加移除特定索引的逻辑

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='数据库索引优化工具')
    parser.add_argument('--show', action='store_true', help='显示现有索引')
    parser.add_argument('--optimize', action='store_true', help='执行索引优化')
    parser.add_argument('--analyze', action='store_true', help='只分析表性能，不创建索引')
    
    args = parser.parse_args()
    
    if args.show:
        show_existing_indexes()
    elif args.analyze:
        try:
            db_info = parse_db_uri(_read_db_uri())
            conn = get_db_connection(db_info)
            cursor = conn.cursor()
            try:
                cursor.execute('SET SESSION sql_mode=""')
            except Exception:
                pass
            analyze_table_performance(cursor)
        except Exception as e:
            logger.error(f"分析表性能失败: {str(e)}")
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()
    elif args.optimize:
        success = optimize_database_indexes()
        if success:
            logger.info("索引优化成功完成！")
            sys.exit(0)
        else:
            logger.error("索引优化失败！")
            sys.exit(1)
    else:
        parser.print_help()