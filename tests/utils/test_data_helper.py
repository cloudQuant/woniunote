"""
WoniuNote测试数据助手模块
提供测试数据的创建、管理和清理功能

遵循企业级测试标准设计，支持可重复、隔离的测试执行
"""

import os
import sys
import time
import random
import logging
from datetime import datetime
from typing import Tuple, List, Dict, Any, Optional, Union

# 添加项目根目录到Python路径
project_root = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
sys.path.insert(0, project_root)

# 导入应用模型和数据库连接
from woniunote.common.database import dbconnect
from sqlalchemy import text

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 测试数据标识符 - 用于标记测试创建的数据
TEST_DATA_MARKER = f"TEST_{int(time.time())}"

class TestUserFactory:
    """测试用户工厂类"""
    
    @staticmethod
    def generate_username() -> str:
        """生成测试用户名"""
        return f"test_user_{TEST_DATA_MARKER}_{random.randint(1000, 9999)}"
    
    @staticmethod
    def create(username: Optional[str] = None, 
               password: str = "Test@12345",
               role: str = "common") -> Optional[Any]:
        """
        创建测试用户
        
        Args:
            username: 用户名，如果为None则自动生成
            password: 密码
            role: 用户角色
            
        Returns:
            用户对象或None（如果创建失败）
        """
        if username is None:
            username = TestUserFactory.generate_username()
        
        try:
            # 获取数据库会话
            session = dbconnect()[0]
            
            # 检查用户是否已存在
            result = session.execute(
                text("SELECT * FROM users WHERE username = :username"),
                {"username": username}
            )
            user = result.fetchone()
            
            if user:
                logger.info(f"测试用户已存在: {username}")
                return user
            
            # 创建新用户
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            result = session.execute(
                text("""
                    INSERT INTO users 
                    (username, password, nickname, avatar, role, credit, create_time) 
                    VALUES (:username, :password, :nickname, :avatar, :role, :credit, :create_time)
                """),
                {
                    "username": username,
                    "password": password,
                    "nickname": f"测试用户_{username}",
                    "avatar": "default.png",
                    "role": role,
                    "credit": 100,
                    "create_time": now
                }
            )
            
            # 获取新用户ID
            result = session.execute(
                text("SELECT * FROM users WHERE username = :username"),
                {"username": username}
            )
            user = result.fetchone()
            
            session.commit()
            logger.info(f"已创建测试用户: {username}, ID={user.id if user else 'unknown'}")
            return user
        except Exception as e:
            logger.error(f"创建测试用户出错: {e}")
            if 'session' in locals():
                session.rollback()
            return None


class TestArticleFactory:
    """测试文章工厂类"""
    
    @staticmethod
    def generate_headline() -> str:
        """生成测试文章标题"""
        return f"测试文章 {TEST_DATA_MARKER} {random.randint(1000, 9999)}"
    
    @staticmethod
    def create(user_id: int, 
               headline: Optional[str] = None, 
               content: str = "这是测试文章的内容", 
               article_type: str = "1") -> Optional[Any]:
        """
        创建测试文章
        
        Args:
            user_id: 作者用户ID
            headline: 文章标题，如果为None则自动生成
            content: 文章内容
            article_type: 文章类型
            
        Returns:
            文章对象或None（如果创建失败）
        """
        if headline is None:
            headline = TestArticleFactory.generate_headline()
        
        try:
            # 获取数据库会话
            session = dbconnect()[0]
            engine = session.get_bind()
            from sqlalchemy import inspect
            inspector = inspect(engine)
            columns = [col['name'] for col in inspector.get_columns('article')]
            
            # 构造待插入的数据字典
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            data_dict = {
                'headline': headline,
                'content': content,
                'type': article_type,
                'userid': user_id,
                'readcount': 0,
                'createtime': now,
                'hidden': 0,
                'drafted': 0,
                'checked': 1,
                'recommended': random.randint(0, 1)
            }
            
            # 仅保留表中存在的列
            filtered_data = {k: v for k, v in data_dict.items() if k in columns}
            if not filtered_data:
                raise RuntimeError("无法匹配到 article 表字段进行插入")
            
            col_names = ", ".join(filtered_data.keys())
            placeholders = ", ".join(f":{k}" for k in filtered_data.keys())
            
            sql_text = text(f"INSERT INTO article ({col_names}) VALUES ({placeholders})")
            result = session.execute(sql_text, filtered_data)
            
            # 获取新文章ID
            result = session.execute(
                text("SELECT * FROM article WHERE headline = :headline AND userid = :userid ORDER BY articleid DESC LIMIT 1"),
                {"headline": headline, "userid": user_id}
            )
            article = result.fetchone()
            
            session.commit()
            logger.info(f"已创建测试文章: {headline}, ID={article.articleid if article else 'unknown'}")
            return article
        except Exception as e:
            logger.error(f"创建测试文章出错: {e}")
            if 'session' in locals():
                session.rollback()
            return None
    
    @staticmethod
    def create_batch(user_id: int, count: int = 5) -> List[Any]:
        """
        批量创建测试文章
        
        Args:
            user_id: 作者用户ID
            count: 要创建的文章数量
            
        Returns:
            创建的文章对象列表
        """
        articles = []
        for i in range(count):
            headline = f"测试文章 {TEST_DATA_MARKER} #{i+1}"
            content = f"这是第{i+1}篇测试文章的内容。包含一些测试数据。{TEST_DATA_MARKER}"
            article_type = str(random.randint(1, 4))  # 随机类型，作为字符串，在create方法中会转换为整数
            
            article = TestArticleFactory.create(user_id, headline, content, article_type)
            if article:
                articles.append(article)
        
        logger.info(f"已批量创建{len(articles)}篇测试文章")
        return articles


class TestDataManager:
    """测试数据管理器"""
    
    @staticmethod
    def clean_test_data() -> None:
        """清理所有测试数据"""
        try:
            # 获取数据库会话
            session = dbconnect()[0]
            
            # 清理测试文章
            try:
                # 清理标题中包含TEST_标记的文章
                marker = TEST_DATA_MARKER.split('_')[0] + '_%'  # TEST_%
                result = session.execute(
                    text("DELETE FROM article WHERE headline LIKE :marker"),
                    {"marker": marker}
                )
                logger.info(f"已清理{result.rowcount}篇测试文章")
            except Exception as e:
                logger.error(f"清理测试文章时出错: {e}")
            
            # 清理测试用户
            try:
                result = session.execute(
                    text("DELETE FROM users WHERE username LIKE :marker"),
                    {"marker": "test_user_TEST_%"}
                )
                logger.info(f"已清理{result.rowcount}个测试用户")
            except Exception as e:
                logger.error(f"清理测试用户时出错: {e}")
            
            # 提交事务
            session.commit()
        except Exception as e:
            logger.error(f"清理测试数据时出错: {e}")
            if 'session' in locals():
                session.rollback()
    
    @staticmethod
    def prepare_test_data(article_count: int = 5) -> Dict[str, Any]:
        """
        准备测试数据
        
        Args:
            article_count: 要创建的文章数量
            
        Returns:
            包含测试用户和文章的字典
        """
        # 创建测试用户
        test_user = TestUserFactory.create()
        if not test_user:
            logger.error("无法创建测试用户")
            return {"user": None, "articles": [], "test_marker": TEST_DATA_MARKER}
        
        # 检查是否有现有的测试文章
        try:
            session = dbconnect()[0]
            result = session.execute(
                text("SELECT * FROM article WHERE userid = :userid"),
                {"userid": test_user.id}
            )
            existing_articles = result.fetchall()
            
            if existing_articles and len(existing_articles) >= 3:
                logger.info(f"发现{len(existing_articles)}篇现有测试文章")
                return {
                    "user": test_user, 
                    "articles": existing_articles,
                    "test_marker": TEST_DATA_MARKER
                }
        except Exception as e:
            logger.error(f"获取现有测试文章出错: {e}")
        
        # 创建测试文章
        articles = TestArticleFactory.create_batch(test_user.id, count=article_count)
        
        return {
            "user": test_user,
            "articles": articles,
            "test_marker": TEST_DATA_MARKER
        }


# 为兼容现有代码提供的简化接口
def get_or_create_test_data(article_count: int = 5) -> Tuple[Any, List[Any]]:
    """获取或创建测试数据"""
    data = TestDataManager.prepare_test_data(article_count)
    return data["user"], data["articles"]

def clean_test_data() -> None:
    """清理所有测试数据"""
    TestDataManager.clean_test_data()

# 为测试框架添加可测试函数
import pytest

@pytest.mark.unit
def test_test_data_manager():
    """测试数据管理器基本测试"""
    assert TestDataManager is not None
    assert hasattr(TestDataManager, 'prepare_test_data')
    assert hasattr(TestDataManager, 'clean_test_data')
    logger.info("测试数据管理器基本功能测试通过")

@pytest.mark.unit
def test_test_data_constants():
    """测试数据常量检查"""
    assert TEST_DATA_MARKER is not None
    assert isinstance(TEST_DATA_MARKER, str)
    assert TEST_DATA_MARKER.startswith("TEST_")
    logger.info(f"测试数据标记符有效: {TEST_DATA_MARKER}")


if __name__ == "__main__":
    # 当直接运行此脚本时，创建测试数据
    data = TestDataManager.prepare_test_data()
    print(f"已创建测试用户: {data['user'].username if data['user'] else 'None'}")
    print(f"已创建{len(data['articles'])}篇测试文章")
