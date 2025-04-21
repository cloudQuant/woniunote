"""
WoniuNote测试配置模块
提供pytest测试所需的fixtures和通用配置

遵循企业级测试标准设计，支持可重复、隔离的测试执行
"""

import os
import sys
import time
import logging
import pytest
import requests
import warnings
from typing import Dict, Any, Tuple, List, Optional
from datetime import datetime
from sqlalchemy import text
from urllib3.exceptions import InsecureRequestWarning

# 添加项目根目录到Python路径
project_root = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, project_root)

# 导入Flask应用上下文提供者
from tests.utils.test_base import FlaskAppContextProvider

# 导入测试数据辅助模块
from tests.utils.test_data_helper import TestDataManager, TestUserFactory, TestArticleFactory
from tests.utils import test_data_helper
from woniunote.common.database import dbconnect

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("test_fixtures")

# 禁用不安全HTTPS请求的警告
warnings.filterwarnings("ignore", category=InsecureRequestWarning)

# Playwright相关导入
from playwright.sync_api import Page, Browser, BrowserContext, Playwright, sync_playwright

# 创建app_context fixture，确保所有测试在Flask应用上下文中运行
app_context = FlaskAppContextProvider.with_app_context_fixture()

# ---------------------- 通用测试工具函数 ----------------------

def auto_login_steps(page: Page, username: str, password: str) -> None:
    """
    执行自动登录步骤
    
    Args:
        page: Playwright页面对象
        username: 用户名
        password: 密码
    """
    logger.info(f"执行自动登录: {username}")
    
    # 访问登录页面
    page.goto("/login")
    
    # 填写登录表单
    page.fill("input[name='username']", username)
    page.fill("input[name='password']", password)
    
    # 提交表单
    page.click("input[type='submit']")
    
    # 等待登录完成
    page.wait_for_selector("a:has-text('个人中心')")
    logger.info("登录成功")


def get_article_link_by_headline(page: Page, headline: str) -> Optional[str]:
    """
    通过文章标题获取文章链接
    
    Args:
        page: Playwright页面对象
        headline: 文章标题
    
    Returns:
        文章链接或None
    """
    logger.info(f"查找文章链接: '{headline}'")
    
    # 等待文章列表加载
    page.wait_for_selector(".article-list")
    
    # 查找指定标题的文章链接
    article_link = page.query_selector(f"a:has-text('{headline}')")
    
    if article_link:
        href = article_link.get_attribute("href")
        logger.info(f"找到文章链接: {href}")
        return href
    else:
        logger.warning(f"未找到标题为'{headline}'的文章链接")
        return None


def get_article_id_from_url(url: str) -> Optional[int]:
    """
    从URL中提取文章ID
    
    Args:
        url: 文章URL
    
    Returns:
        文章ID或None
    """
    import re
    match = re.search(r'/article/(\d+)', url)
    if match:
        article_id = int(match.group(1))
        logger.info(f"从URL '{url}' 提取到文章ID: {article_id}")
        return article_id
    else:
        logger.warning(f"无法从URL '{url}' 提取文章ID")
        return None


# ---------------------- Pytest Fixtures ----------------------

@pytest.fixture(scope="session")
def server_host():
    """返回服务器主机名"""
    from tests.utils.test_config import SERVER_CONFIG
    logger.info(f"使用服务器主机: {SERVER_CONFIG['host']}")
    return SERVER_CONFIG['host']

@pytest.fixture(scope="session")
def server_port():
    """返回服务器端口"""
    from tests.utils.test_config import SERVER_CONFIG
    logger.info(f"使用服务器端口: {SERVER_CONFIG['port']}")
    return SERVER_CONFIG['port']

@pytest.fixture(scope="session")
def base_url(server_host, server_port):
    """返回服务器的基础URL"""
    # 使用 HTTP 协议进行测试，避免证书问题
    http_url = f"http://{server_host}:{server_port}"
    https_url = f"https://{server_host}:{server_port}"
    
    # 尝试HTTP和HTTPS连接，优先选择可用的连接
    urls_to_try = [http_url, https_url]
    working_url = None
    
    for url in urls_to_try:
        logger.info(f"尝试连接到服务器: {url}")
        max_attempts = 3
        for i in range(max_attempts):
            try:
                response = requests.get(url, verify=False, timeout=5)
                if response.status_code == 200:
                    logger.info(f"成功连接到服务器: {url}")
                    working_url = url
                    break
            except Exception as e:
                if i == max_attempts - 1:
                    logger.warning(f"无法连接到服务器 {url}: {str(e)}")
                else:
                    logger.warning(f"尝试连接服务器失败，将重试: {str(e)}")
                    time.sleep(2)  # 等待服务器启动
        
        if working_url:
            break
    
    # 如果没有找到工作的URL，启动一个HTTP服务器
    if not working_url:
        logger.warning("没有找到可用的服务器连接，将尝试启动服务器...")
        try:
            import subprocess
            import os
            
            # 构建启动服务器的命令
            cmd = [sys.executable, os.path.join(project_root, "start_server.py"), "--test", "--http", "--port", str(server_port)]
            
            # 以非阻塞方式启动服务器
            subprocess.Popen(cmd, cwd=project_root, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # 等待服务器启动
            logger.info(f"等待服务器启动...")
            time.sleep(5)
            
            # 再次尝试连接
            working_url = http_url
        except Exception as e:
            logger.error(f"尝试启动服务器时出错: {e}")
    
    # 仍然没有可用连接，但不跳过测试，而是返回HTTP URL并记录警告
    if not working_url:
        logger.warning("无法连接到服务器，测试可能会失败，但仍将继续执行")
        working_url = http_url
    
    return working_url

@pytest.fixture(scope="session")
def browser_type_launch_args() -> Dict[str, Any]:
    """
    定义浏览器启动参数
    """
    return {
        "headless": True,
        # 禁用沙箱以在某些CI环境中运行
        # 添加更多参数以支持HTTPS和忽略证书错误
        "ignore_default_args": ["--enable-automation"],
        "args": [
            "--no-sandbox",
            "--ignore-certificate-errors",
            "--allow-insecure-localhost",
            "--disable-web-security", 
            "--disable-features=IsolateOrigins,site-per-process",
            "--disable-site-isolation-trials",
            "--disable-gpu",
            "--disable-dev-shm-usage",
            "--disable-setuid-sandbox",
            "--no-first-run",
            "--no-zygote",
            "--deterministic-fetch",
            "--disable-features=BackForwardCache",
            "--disable-web-security",
            "--disable-features=IsolateOrigins",
            "--disable-site-isolation-trials"
        ],
        "timeout": 30000,  # 设置更长的超时时间
        "chromium_sandbox": False  # 禁用 Chromium 沙箱
    }

@pytest.fixture(scope="session")
def browser_context_args(base_url) -> Dict[str, Any]:
    """
    定义浏览器上下文参数
    """
    return {
        "viewport": {
            "width": 1280,
            "height": 720,
        },
        "ignore_https_errors": True,  # 忽略HTTPS错误
        "base_url": base_url,
        "bypass_csp": True,  # 绕过内容安全策略
        "extra_http_headers": {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
    }

@pytest.fixture(scope="session", autouse=True)
def prepare_test_database():
    """准备测试数据库环境，创建必要的视图以适配应用程序代码和数据库结构的不匹配"""
    # 在Flask应用上下文中进行数据库操作
    with FlaskAppContextProvider.get_app_context():
        try:
            session, engine = dbconnect()
            
            # 检查并创建 article 表（若不存在）
            from sqlalchemy import text
            result = session.execute(text("""
                SELECT COUNT(*) AS cnt
                FROM information_schema.tables
                WHERE table_schema = DATABASE() AND table_name = 'article'
            """))
            
            exists = result.fetchone()[0] > 0
            if not exists:
                logger.warning("article 表不存在，正在创建测试专用表 ...")
                session.execute(text("""
                    CREATE TABLE article (
                        articleid INT AUTO_INCREMENT PRIMARY KEY,
                        userid INT NULL,
                        type VARCHAR(10) NOT NULL DEFAULT '1',
                        headline VARCHAR(100) NOT NULL,
                        content TEXT,
                        readcount INT DEFAULT 0,
                        replycount INT DEFAULT 0,
                        hidden INT DEFAULT 0,
                        drafted INT DEFAULT 0,
                        checked INT DEFAULT 1,
                        recommended INT DEFAULT 0,
                        createtime DATETIME NULL,
                        updatetime DATETIME NULL
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                """))
                session.commit()
                logger.info("已创建 article 表 (测试环境)")
            
            # === 确保 comment 表存在 ===
            result = session.execute(text("""
                SELECT COUNT(*) AS cnt
                FROM information_schema.tables
                WHERE table_schema = DATABASE() AND table_name = 'comment'
            """))
            comment_exists = result.fetchone()[0] > 0
            if not comment_exists:
                logger.warning("comment 表不存在，正在创建测试专用表 ...")
                session.execute(text("""
                    CREATE TABLE comment (
                        commentid INT AUTO_INCREMENT PRIMARY KEY,
                        articleid INT NOT NULL,
                        userid INT NOT NULL,
                        content TEXT NOT NULL,
                        ipaddress VARCHAR(45) DEFAULT '127.0.0.1',
                        createtime DATETIME NULL,
                        hidden INT DEFAULT 0,
                        INDEX idx_article (articleid)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                """))
                session.commit()
                logger.info("已创建 comment 表 (测试环境)")
            
            # === 确保 users 表存在，便于登录相关测试 ===
            result = session.execute(text("""
                SELECT COUNT(*) FROM information_schema.tables
                WHERE table_schema = DATABASE() AND table_name = 'users'
            """))
            users_exists = result.fetchone()[0] > 0
            if not users_exists:
                logger.warning("users 表不存在，正在创建测试专用表 ...")
                session.execute(text("""
                    CREATE TABLE users (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        username VARCHAR(50) UNIQUE,
                        password VARCHAR(100),
                        nickname VARCHAR(100),
                        avatar VARCHAR(100),
                        role VARCHAR(20) DEFAULT 'common',
                        credit INT DEFAULT 0,
                        create_time DATETIME NULL
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                """))
                session.commit()
                logger.info("已创建 users 表 (测试环境)")
            
            # 生成一个默认管理员账户，供登录测试使用
            try:
                result = session.execute(text("SELECT COUNT(*) FROM users WHERE username = 'admin'"))
                if result.fetchone()[0] == 0:
                    session.execute(text("""
                        INSERT INTO users (username, password, nickname, role, credit, create_time)
                        VALUES ('admin', 'admin', '管理员', 'admin', 1000, NOW())
                    """))
                    session.commit()
                    logger.info("已插入默认管理员账户 admin/admin")
            except Exception as admin_e:
                logger.warning(f"插入默认管理员账户时出错: {admin_e}")
            
            # 确保关键列存在（兼容已有旧表结构）
            required_columns = {
                'readcount': "ALTER TABLE article ADD COLUMN readcount INT DEFAULT 0",
                'replycount': "ALTER TABLE article ADD COLUMN replycount INT DEFAULT 0",
                'hidden': "ALTER TABLE article ADD COLUMN hidden INT DEFAULT 0",
                'drafted': "ALTER TABLE article ADD COLUMN drafted INT DEFAULT 0",
                'checked': "ALTER TABLE article ADD COLUMN checked INT DEFAULT 1",
                'recommended': "ALTER TABLE article ADD COLUMN recommended INT DEFAULT 0"
            }
            for col, ddl in required_columns.items():
                try:
                    col_result = session.execute(text(f"""
                        SELECT COUNT(*) FROM information_schema.columns
                        WHERE table_schema = DATABASE() AND table_name = 'article' AND column_name = '{col}'
                    """))
                    if col_result.fetchone()[0] == 0:
                        logger.info(f"列 {col} 不存在，执行DDL: {ddl}")
                        session.execute(text(ddl))
                        session.commit()
                except Exception as col_e:
                    logger.warning(f"确保列 {col} 存在时出错: {col_e}")
            
            # 校验 type 字段类型，如不符则尝试调整视图
            try:
                result = session.execute(text("""
                    SELECT data_type FROM information_schema.columns
                    WHERE table_schema = DATABASE() AND table_name = 'article' AND column_name = 'type'
                """))
                column_info = result.fetchone()
                if column_info and column_info[0].lower() != 'varchar':
                    logger.warning("article.type 字段非 varchar，创建视图 article_view 以varchar暴露 ...")
                    session.execute(text("DROP VIEW IF EXISTS article_view"))
                    session.execute(text("""
                        CREATE VIEW article_view AS
                        SELECT articleid, userid, CAST(type AS CHAR(10)) AS type,
                               headline, content, createtime, updatetime
                        FROM article;
                    """))
                    session.commit()
            except Exception as e:
                logger.warning(f"处理 article.type 字段时出错: {e}")
            
            logger.info("测试数据库准备完毕")
            
        except Exception as e:
            logger.error(f"准备测试数据库时发生错误: {e}")
            pytest.fail(f"无法准备测试数据库环境: {e}")

@pytest.fixture
def user_browser_context(
    playwright: Playwright, 
    browser_type_launch_args, 
    browser_context_args, 
    base_url, 
    test_data
) -> BrowserContext:
    """
    创建一个已登录用户的浏览器上下文
    每个测试函数使用一个新的上下文
    
    Args:
        playwright: Playwright对象
        browser_type_launch_args: 浏览器启动参数
        browser_context_args: 浏览器上下文参数
        base_url: 测试基础URL
        test_data: 测试数据
    
    Returns:
        已登录的浏览器上下文
    """
    # 启动浏览器
    browser = playwright.chromium.launch(**browser_type_launch_args)
    
    # 创建上下文
    context = browser.new_context(**browser_context_args)
    
    # 创建页面并执行登录
    page = context.new_page()
    
    try:
        # 获取测试用户信息
        test_user = test_data["user"]
        username = test_user.username
        password = "test123"  # 测试用户密码
        
        # 执行登录
        page.goto(f"{base_url}/login")
        
        # 填写并提交登录表单
        page.fill("input[name='username']", username)
        page.fill("input[name='password']", password)
        
        # 修改验证码，绕过验证
        if page.query_selector("input[name='vcode']"):
            page.fill("input[name='vcode']", "1234")
        
        # 点击登录按钮
        submit_button = page.query_selector("button[type='submit'], input[type='submit']")
        if submit_button:
            submit_button.click()
        else:
            # 尝试查找可能的登录按钮
            page.click("text=登录")
        
        # 等待登录完成
        page.wait_for_url(f"{base_url}/")
        logger.info(f"成功登录测试用户: {username}")
        
    except Exception as e:
        logger.error(f"登录测试用户时出错: {e}")
        # 继续测试，某些测试可能不需要登录状态
    
    # 关闭这个页面，让测试使用新的页面
    page.close()
    
    # 返回上下文供测试使用
    yield context
    
    # 测试后关闭浏览器
    context.close()
    browser.close()

@pytest.fixture
def authenticated_page(user_browser_context: BrowserContext):
    """
    提供一个已通过身份验证的页面
    """
    # 创建新页面
    page = user_browser_context.new_page()
    
    # 返回页面供测试使用
    yield page
    
    # 测试后关闭页面
    page.close()

@pytest.fixture
def cleanup_test_data():
    """
    用于清理测试中创建的临时数据
    确保测试前后数据库处于一致状态
    """
    # 记录测试开始时间，用于标识测试期间创建的数据
    test_start_time = time.time()
    logger.info(f"记录测试开始时间戳: {test_start_time}")
    
    # 执行测试
    yield
    
    try:
        # 清理测试期间创建的文章
        logger.info("清理测试期间创建的数据...")
        with FlaskAppContextProvider.get_app_context():
            session = dbconnect()[0]
            
            # 查找并删除测试期间创建的文章
            # 通常这些文章标题中会包含"自动化测试"或"测试"，并且时间戳在测试开始之后
            test_str = "%测试%"
            create_time_threshold = datetime.fromtimestamp(test_start_time).strftime('%Y-%m-%d %H:%M:%S')
            
            try:
                # 先查找符合条件的文章
                result = session.execute(
                    text("SELECT articleid, headline FROM article WHERE headline LIKE :test_str AND createtime > :threshold"),
                    {"test_str": test_str, "threshold": create_time_threshold}
                )
                articles_to_delete = list(result)
                
                if articles_to_delete:
                    logger.info(f"找到 {len(articles_to_delete)} 篇测试期间创建的文章")
                    for article in articles_to_delete:
                        logger.info(f"删除测试文章: ID={article.articleid}, 标题={article.headline}")
                        
                    # 删除这些文章
                    result = session.execute(
                        text("DELETE FROM article WHERE headline LIKE :test_str AND createtime > :threshold"),
                        {"test_str": test_str, "threshold": create_time_threshold}
                    )
                    session.commit()
                    logger.info(f"成功删除 {result.rowcount} 篇测试文章")
                else:
                    logger.info("未找到需要清理的测试文章")
            except Exception as e:
                logger.error(f"清理测试文章时出错: {e}")
                session.rollback()
    except Exception as e:
        logger.error(f"清理测试数据时出错: {e}")


@pytest.fixture
def article(test_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    提供可用于测试的单个文章数据
    """
    with FlaskAppContextProvider.get_app_context():
        if not test_data["articles"]:
            # 如果没有现有的文章，创建一个
            user = test_data["user"]
            headline = f"测试文章 - 单独测试 - {int(time.time())}"
            content = "这是为单独测试创建的文章内容。"
            
            # 使用新的数据工厂创建文章
            try:
                from tests.utils.test_data_factory import TestDataFactory
                article_id = TestDataFactory.create_article(
                    user_id=user.id,
                    headline=headline,
                    content=content,
                    article_type="1"  # 使用字符串类型
                )
                
                # 查询文章数据
                session = dbconnect()[0]
                result = session.execute(
                    text("SELECT * FROM article WHERE articleid = :id"),
                    {"id": article_id}
                )
                article = result.fetchone()
                
                if not article:
                    pytest.fail("无法创建测试文章")
                
                article_data = {
                    "id": article.articleid,
                    "headline": article.headline,
                    "content": article.content,
                    # 确保type类型为字符串，与数据库一致
                    "type": str(article.type),
                    "user_id": article.userid
                }
            except ImportError:
                # 如果没有新的数据工厂，使用旧方法
                article = TestArticleFactory.create(user.id, headline, content, "1")
                if not article:
                    pytest.fail("无法创建测试文章")
                
                article_data = {
                    "id": article.id,
                    "headline": article.headline,
                    "content": article.content,
                    # 确保type类型与模型定义一致 (Integer)
                    "type": str(article.type) if not isinstance(article.type, str) else article.type,
                    "user_id": article.user_id
                }
        else:
            # 使用第一篇现有文章
            article = test_data["articles"][0]
            article_data = {
                "id": article.id,
                "headline": article.headline,
                "content": article.content,
                # 确保type类型与模型定义一致 (Integer)
                "type": str(article.type) if not isinstance(article.type, str) else article.type,
                "user_id": article.user_id
            }
        
        logger.info(f"使用测试文章: ID={article_data['id']}, 标题='{article_data['headline']}'")
        return article_data


@pytest.fixture(scope="module")
def clean_db():
    """
    在模块级别清理和准备数据库
    """
    with FlaskAppContextProvider.get_app_context():
        # 测试开始前清理旧的测试数据
        logger.info("模块开始前清理旧测试数据...")
        TestDataManager.clean_test_data()
        
        yield
        
        # 测试完成后再次清理
        logger.info("模块结束后清理测试数据...")
        TestDataManager.clean_test_data()

# 在测试会话开始时初始化测试数据
def pytest_configure(config):
    """在所有测试开始前执行初始化"""
    # 在Flask应用上下文中初始化测试数据
    with FlaskAppContextProvider.get_app_context():
        try:
            # 导入数据工厂
            from tests.utils.test_data_factory import TestDataFactory
            
            # 确保测试数据存在
            TestDataFactory.ensure_test_data_exists()
            logger.info("已通过测试数据工厂初始化测试数据")
        except ImportError:
            logger.warning("未找到测试数据工厂模块，使用默认方法初始化测试数据")
            # 使用默认方法初始化
            test_user = TestUserFactory.get_or_create_test_user()
            articles = TestArticleFactory.get_test_articles()
            if len(articles) == 0:
                # 创建一些测试文章
                for i in range(5):
                    TestArticleFactory.create(
                        user_id=test_user.id,
                        headline=f"初始化测试文章 {i+1}",
                        content=f"这是第 {i+1} 篇初始化测试文章",
                        article_type=str(random.randint(1, 4))  # 使用字符串类型
                    )
                logger.info("已创建初始化测试文章")
