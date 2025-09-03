#!/usr/bin/env python3
"""
Test Data Management System for WoniuNote
Automated test data generation, management, and cleanup
"""

import os
import sys
import json
import shutil
import sqlite3
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
import faker
import random

# 确保项目根目录在Python路径中
project_root = Path("/Users/yunjinqi/Documents/woniunote")
if project_root not in sys.path:
    sys.path.insert(0, str(project_root))

class TestDataManager:
    """测试数据管理器"""

    def __init__(self):
        self.project_root = project_root
        self.test_data_dir = project_root / "test-data"
        self.test_data_dir.mkdir(exist_ok=True)
        self.faker = faker.Faker('zh_CN')  # 使用中文数据

    def generate_test_database(self, db_path: Optional[str] = None) -> str:
        """生成测试数据库"""
        if db_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            db_path = str(self.test_data_dir / f"test_db_{timestamp}.db")

        print(f"🗄️ Generating test database: {db_path}")

        # 创建数据库连接
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        try:
            # 创建测试表结构
            self._create_test_tables(cursor)

            # 生成测试数据
            self._generate_test_data(cursor)

            # 提交事务
            conn.commit()

            print(f"✅ Test database generated successfully: {db_path}")
            return db_path

        except Exception as e:
            print(f"❌ Failed to generate test database: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()

    def _create_test_tables(self, cursor):
        """创建测试表结构"""
        # 用户表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username VARCHAR(50) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                email VARCHAR(100) UNIQUE,
                nickname VARCHAR(50),
                role VARCHAR(20) DEFAULT 'user',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1
            )
        ''')

        # 文章表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title VARCHAR(200) NOT NULL,
                content TEXT,
                author_id INTEGER,
                category_id INTEGER,
                views INTEGER DEFAULT 0,
                likes INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                is_published BOOLEAN DEFAULT 1,
                FOREIGN KEY (author_id) REFERENCES users(id),
                FOREIGN KEY (category_id) REFERENCES categories(id)
            )
        ''')

        # 评论表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                article_id INTEGER,
                author_id INTEGER,
                parent_id INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                is_deleted BOOLEAN DEFAULT 0,
                FOREIGN KEY (article_id) REFERENCES articles(id),
                FOREIGN KEY (author_id) REFERENCES users(id),
                FOREIGN KEY (parent_id) REFERENCES comments(id)
            )
        ''')

        # 分类表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(50) UNIQUE NOT NULL,
                description TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 卡片表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title VARCHAR(200) NOT NULL,
                content TEXT,
                user_id INTEGER,
                category_id INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                is_deleted BOOLEAN DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (category_id) REFERENCES card_categories(id)
            )
        ''')

        # 卡片分类表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS card_categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(50) UNIQUE NOT NULL,
                description TEXT,
                user_id INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')

        # 待办事项表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS todos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title VARCHAR(200) NOT NULL,
                description TEXT,
                user_id INTEGER,
                category_id INTEGER,
                priority INTEGER DEFAULT 3,
                status VARCHAR(20) DEFAULT 'pending',
                due_date DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                is_deleted BOOLEAN DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (category_id) REFERENCES todo_categories(id)
            )
        ''')

        # 待办事项分类表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS todo_categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(50) UNIQUE NOT NULL,
                description TEXT,
                user_id INTEGER,
                color VARCHAR(7) DEFAULT '#007bff',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')

    def _generate_test_data(self, cursor):
        """生成测试数据"""
        print("📝 Generating test data...")

        # 生成用户数据
        users = self._generate_users(20)
        cursor.executemany('''
            INSERT INTO users (username, password, email, nickname, role, is_active)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', users)

        # 生成分类数据
        categories = self._generate_categories(10)
        cursor.executemany('''
            INSERT INTO categories (name, description)
            VALUES (?, ?)
        ''', categories)

        # 获取用户ID列表
        cursor.execute("SELECT id FROM users")
        user_ids = [row[0] for row in cursor.fetchall()]

        # 获取分类ID列表
        cursor.execute("SELECT id FROM categories")
        category_ids = [row[0] for row in cursor.fetchall()]

        # 生成文章数据
        articles = self._generate_articles(50, user_ids, category_ids)
        cursor.executemany('''
            INSERT INTO articles (title, content, author_id, category_id, views, likes, is_published)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', articles)

        # 获取文章ID列表
        cursor.execute("SELECT id FROM articles")
        article_ids = [row[0] for row in cursor.fetchall()]

        # 生成评论数据
        comments = self._generate_comments(100, article_ids, user_ids)
        cursor.executemany('''
            INSERT INTO comments (content, article_id, author_id, parent_id, is_deleted)
            VALUES (?, ?, ?, ?, ?)
        ''', comments)

        # 生成卡片分类数据
        card_categories = self._generate_card_categories(8, user_ids)
        cursor.executemany('''
            INSERT INTO card_categories (name, description, user_id)
            VALUES (?, ?, ?)
        ''', card_categories)

        # 获取卡片分类ID列表
        cursor.execute("SELECT id FROM card_categories")
        card_category_ids = [row[0] for row in cursor.fetchall()]

        # 生成卡片数据
        cards = self._generate_cards(30, user_ids, card_category_ids)
        cursor.executemany('''
            INSERT INTO cards (title, content, user_id, category_id, is_deleted)
            VALUES (?, ?, ?, ?, ?)
        ''', cards)

        # 生成待办事项分类数据
        todo_categories = self._generate_todo_categories(6, user_ids)
        cursor.executemany('''
            INSERT INTO todo_categories (name, description, user_id, color)
            VALUES (?, ?, ?, ?)
        ''', todo_categories)

        # 获取待办事项分类ID列表
        cursor.execute("SELECT id FROM todo_categories")
        todo_category_ids = [row[0] for row in cursor.fetchall()]

        # 生成待办事项数据
        todos = self._generate_todos(40, user_ids, todo_category_ids)
        cursor.executemany('''
            INSERT INTO todos (title, description, user_id, category_id, priority, status, due_date, is_deleted)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', todos)

        print("✅ Test data generated successfully")

    def _generate_users(self, count: int) -> List[tuple]:
        """生成用户数据"""
        users = []
        roles = ['user', 'admin', 'moderator']

        for i in range(count):
            username = f"testuser_{i+1}"
            password = f"hashed_password_{i+1}"
            email = self.faker.email()
            nickname = self.faker.name()
            role = random.choice(roles) if i < 3 else 'user'  # 前3个用户可能是管理员
            is_active = random.choice([True, False]) if i > 15 else True  # 最后5个用户可能是非活跃用户

            users.append((username, password, email, nickname, role, is_active))

        return users

    def _generate_categories(self, count: int) -> List[tuple]:
        """生成分类数据"""
        categories = [
            ('技术分享', '分享技术经验和知识'),
            ('生活随笔', '记录日常生活点滴'),
            ('学习笔记', '学习过程中的笔记整理'),
            ('项目经验', '项目开发经验分享'),
            ('工具推荐', '实用工具和资源推荐'),
            ('行业资讯', '行业最新动态和资讯'),
            ('问答交流', '技术问题讨论和解答'),
            ('资源分享', '学习资源和资料分享'),
            ('经验总结', '工作和学习经验总结'),
            ('其他', '其他类型的内容')
        ]

        return categories[:count]

    def _generate_articles(self, count: int, user_ids: List[int], category_ids: List[int]) -> List[tuple]:
        """生成文章数据"""
        articles = []

        for i in range(count):
            title = self.faker.sentence(nb_words=random.randint(5, 15)).rstrip('.')
            content = self.faker.text(max_nb_chars=1000)
            author_id = random.choice(user_ids)
            category_id = random.choice(category_ids) if category_ids else None
            views = random.randint(0, 1000)
            likes = random.randint(0, 100)
            is_published = random.choice([True, False]) if i > count - 5 else True  # 最后5篇文章可能是草稿

            articles.append((title, content, author_id, category_id, views, likes, is_published))

        return articles

    def _generate_comments(self, count: int, article_ids: List[int], user_ids: List[int]) -> List[tuple]:
        """生成评论数据"""
        comments = []

        for i in range(count):
            content = self.faker.text(max_nb_chars=200)
            article_id = random.choice(article_ids)
            author_id = random.choice(user_ids)
            parent_id = random.choice([None] + list(range(1, i + 1))) if i > 0 and random.random() < 0.3 else None
            is_deleted = random.choice([True, False]) if i > count - 10 else False  # 最后10条评论可能已被删除

            comments.append((content, article_id, author_id, parent_id, is_deleted))

        return comments

    def _generate_card_categories(self, count: int, user_ids: List[int]) -> List[tuple]:
        """生成卡片分类数据"""
        card_categories = [
            ('学习笔记', '学习过程中的重要笔记', random.choice(user_ids)),
            ('工作任务', '工作相关的任务和提醒', random.choice(user_ids)),
            ('个人目标', '个人发展目标和计划', random.choice(user_ids)),
            ('创意想法', '创意想法和灵感记录', random.choice(user_ids)),
            ('读书笔记', '读书时的感悟和摘录', random.choice(user_ids)),
            ('旅行计划', '旅行计划和攻略', random.choice(user_ids)),
            ('健康习惯', '健康生活习惯记录', random.choice(user_ids)),
            ('财务管理', '财务收支和预算管理', random.choice(user_ids))
        ]

        return card_categories[:count]

    def _generate_cards(self, count: int, user_ids: List[int], category_ids: List[int]) -> List[tuple]:
        """生成卡片数据"""
        cards = []

        for i in range(count):
            title = self.faker.sentence(nb_words=random.randint(3, 8)).rstrip('.')
            content = self.faker.text(max_nb_chars=300)
            user_id = random.choice(user_ids)
            category_id = random.choice(category_ids) if category_ids else None
            is_deleted = random.choice([True, False]) if i > count - 5 else False  # 最后5张卡片可能已被删除

            cards.append((title, content, user_id, category_id, is_deleted))

        return cards

    def _generate_todo_categories(self, count: int, user_ids: List[int]) -> List[tuple]:
        """生成待办事项分类数据"""
        todo_categories = [
            ('工作任务', '工作相关的任务', random.choice(user_ids), '#dc3545'),
            ('学习计划', '学习和培训计划', random.choice(user_ids), '#28a745'),
            ('个人事务', '个人生活事务', random.choice(user_ids), '#007bff'),
            ('健康管理', '健康和运动计划', random.choice(user_ids), '#ffc107'),
            ('家庭事务', '家庭相关事务', random.choice(user_ids), '#6f42c1'),
            ('娱乐休闲', '娱乐和休闲活动', random.choice(user_ids), '#e83e8c')
        ]

        return todo_categories[:count]

    def _generate_todos(self, count: int, user_ids: List[int], category_ids: List[int]) -> List[tuple]:
        """生成待办事项数据"""
        todos = []
        statuses = ['pending', 'in_progress', 'completed', 'cancelled']
        priorities = [1, 2, 3, 4, 5]  # 1最高，5最低

        for i in range(count):
            title = self.faker.sentence(nb_words=random.randint(4, 10)).rstrip('.')
            description = self.faker.text(max_nb_chars=150)
            user_id = random.choice(user_ids)
            category_id = random.choice(category_ids) if category_ids else None
            priority = random.choice(priorities)
            status = random.choice(statuses)
            due_date = self.faker.date_time_this_year() if random.random() < 0.7 else None
            is_deleted = random.choice([True, False]) if i > count - 8 else False  # 最后8个任务可能已被删除

            todos.append((title, description, user_id, category_id, priority, status, due_date, is_deleted))

        return todos

    def generate_test_files(self) -> str:
        """生成测试文件数据"""
        print("📁 Generating test files...")

        # 创建测试文件目录
        test_files_dir = self.test_data_dir / "files"
        test_files_dir.mkdir(exist_ok=True)

        # 生成各种类型的测试文件
        test_files = []

        # 生成图片文件
        for i in range(5):
            img_path = test_files_dir / f"test_image_{i+1}.png"
            # 创建一个简单的PNG文件头
            png_header = b'\x89PNG\r\n\x1a\n' + b'\x00' * 100  # PNG文件头 + 填充数据
            with open(img_path, 'wb') as f:
                f.write(png_header)
            test_files.append(str(img_path))

        # 生成文本文件
        for i in range(3):
            txt_path = test_files_dir / f"test_document_{i+1}.txt"
            content = self.faker.text(max_nb_chars=500)
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write(content)
            test_files.append(str(txt_path))

        # 生成JSON配置文件
        config_path = test_files_dir / "test_config.json"
        config_data = {
            "app_name": "WoniuNote",
            "version": "1.0.0",
            "database": {
                "host": "localhost",
                "port": 5432,
                "name": "woniunote_test"
            },
            "features": {
                "articles": True,
                "comments": True,
                "cards": True,
                "todos": True
            }
        }
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)
        test_files.append(str(config_path))

        print(f"✅ Generated {len(test_files)} test files in {test_files_dir}")
        return str(test_files_dir)

    def setup_test_environment(self) -> Dict[str, Any]:
        """设置完整的测试环境"""
        print("🔧 Setting up test environment...")

        # 生成测试数据库
        db_path = self.generate_test_database()

        # 生成测试文件
        files_dir = self.generate_test_files()

        # 生成测试配置
        config_path = self.test_data_dir / "test_config.yaml"
        test_config = {
            "app": {
                "name": "WoniuNote Test",
                "debug": True,
                "testing": True
            },
            "database": {
                "url": f"sqlite:///{db_path}",
                "pool_size": 5,
                "max_overflow": 10
            },
            "redis": {
                "host": "localhost",
                "port": 6379,
                "db": 1
            },
            "files": {
                "upload_dir": str(files_dir),
                "max_size": "10MB",
                "allowed_types": [".png", ".jpg", ".txt", ".json"]
            },
            "security": {
                "secret_key": "test-secret-key-for-testing-only",
                "session_timeout": 3600,
                "password_min_length": 6
            }
        }

        with open(config_path, 'w', encoding='utf-8') as f:
            import yaml
            yaml.dump(test_config, f, default_flow_style=False, allow_unicode=True)

        # 创建环境变量文件
        env_file = self.test_data_dir / ".env.test"
        env_content = f"""# Test Environment Variables
TESTING=True
FLASK_ENV=testing
SECRET_KEY=test-secret-key-for-testing-only
DATABASE_URL=sqlite:///{db_path}
REDIS_URL=redis://localhost:6379/1
UPLOAD_FOLDER={files_dir}
"""
        with open(env_file, 'w', encoding='utf-8') as f:
            f.write(env_content)

        environment_info = {
            "database_path": db_path,
            "files_directory": files_dir,
            "config_path": str(config_path),
            "env_file": str(env_file),
            "timestamp": datetime.now().isoformat()
        }

        # 保存环境信息
        env_info_file = self.test_data_dir / "environment_info.json"
        with open(env_info_file, 'w', encoding='utf-8') as f:
            json.dump(environment_info, f, indent=2, ensure_ascii=False)

        print("✅ Test environment setup completed")
        print(f"📊 Environment info saved to: {env_info_file}")

        return environment_info

    def cleanup_test_data(self, older_than_days: int = 7):
        """清理旧的测试数据"""
        print(f"🧹 Cleaning up test data older than {older_than_days} days...")

        cutoff_time = datetime.now().timestamp() - (older_than_days * 24 * 60 * 60)
        cleaned_files = 0
        cleaned_dirs = 0

        # 清理旧的数据库文件
        for db_file in self.test_data_dir.glob("test_db_*.db"):
            if db_file.stat().st_mtime < cutoff_time:
                db_file.unlink()
                cleaned_files += 1

        # 清理旧的测试结果文件
        test_results_dir = project_root / "test-results"
        if test_results_dir.exists():
            for result_file in test_results_dir.glob("*.json"):
                if result_file.stat().st_mtime < cutoff_time:
                    result_file.unlink()
                    cleaned_files += 1

            for result_file in test_results_dir.glob("*.xml"):
                if result_file.stat().st_mtime < cutoff_time:
                    result_file.unlink()
                    cleaned_files += 1

        # 清理空的目录
        for dir_path in [self.test_data_dir, test_results_dir]:
            if dir_path.exists():
                for subdir in dir_path.iterdir():
                    if subdir.is_dir() and not any(subdir.iterdir()):
                        subdir.rmdir()
                        cleaned_dirs += 1

        print(f"✅ Cleanup completed: {cleaned_files} files and {cleaned_dirs} directories removed")

    def get_test_data_stats(self) -> Dict[str, Any]:
        """获取测试数据统计信息"""
        stats = {
            "databases": len(list(self.test_data_dir.glob("test_db_*.db"))),
            "config_files": len(list(self.test_data_dir.glob("*.yaml"))) + len(list(self.test_data_dir.glob("*.json"))),
            "test_files": len(list(self.test_data_dir.rglob("*"))),
            "total_size_mb": 0,
            "last_updated": None
        }

        # 计算总大小
        total_size = 0
        latest_mtime = 0

        for file_path in self.test_data_dir.rglob("*"):
            if file_path.is_file():
                total_size += file_path.stat().st_size
                latest_mtime = max(latest_mtime, file_path.stat().st_mtime)

        stats["total_size_mb"] = round(total_size / (1024 * 1024), 2)
        stats["last_updated"] = datetime.fromtimestamp(latest_mtime).isoformat() if latest_mtime > 0 else None

        return stats


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="WoniuNote Test Data Manager")
    parser.add_argument("action", choices=["generate", "setup", "cleanup", "stats"],
                       help="Action to perform")
    parser.add_argument("--db-path", help="Custom database path")
    parser.add_argument("--days", type=int, default=7,
                       help="Days to keep test data (for cleanup)")

    args = parser.parse_args()

    manager = TestDataManager()

    if args.action == "generate":
        db_path = manager.generate_test_database(args.db_path)
        print(f"Database generated: {db_path}")

    elif args.action == "setup":
        env_info = manager.setup_test_environment()
        print("Environment setup completed:")
        for key, value in env_info.items():
            print(f"  {key}: {value}")

    elif args.action == "cleanup":
        manager.cleanup_test_data(args.days)

    elif args.action == "stats":
        stats = manager.get_test_data_stats()
        print("Test Data Statistics:")
        for key, value in stats.items():
            print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
