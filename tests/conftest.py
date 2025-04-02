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
from typing import Dict, Any, Tuple, List, Optional

# 添加项目根目录到Python路径
project_root = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, project_root)

# 导入测试数据辅助模块
from tests.utils.test_data_helper import TestDataManager, TestUserFactory, TestArticleFactory
from tests.utils import test_data_helper

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("test_fixtures")

# Playwright相关导入
from playwright.sync_api import Page, Browser, BrowserContext, Playwright, sync_playwright


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
def base_url() -> str:
    """
    提供测试基础URL
    
    Returns:
        测试服务器基础URL
    """
    from tests.utils.test_base import get_base_url
    url = get_base_url()
    logger.info(f"使用基础URL: {url}")
    return url

@pytest.fixture
def browser_name():
    """
    提供浏览器名称
    
    Returns:
        浏览器名称，默认为chromium
    """
    return "chromium"

@pytest.fixture(scope="session")
def browser_type_launch_args() -> Dict[str, Any]:
    """
    定义浏览器启动参数
    """
    return {
        # 减慢执行速度，方便观察 (毫秒)
        "slow_mo": 100,
        # 启用无头模式（测试时不显示浏览器窗口）
        "headless": True
    }


@pytest.fixture(scope="session")
def browser_context_args() -> Dict[str, Any]:
    """
    定义浏览器上下文参数
    """
    return {
        # 模拟设备类型
        "user_agent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) WoniuNote Test Agent',
        # 忽略HTTPS错误
        "ignore_https_errors": True,
        # 允许下载文件
        "accept_downloads": True,
        # 启用JavaScript
        "java_script_enabled": True,
    }


@pytest.fixture(scope="session")
def test_data() -> Dict[str, Any]:
    """
    准备测试所需的数据，包括测试用户和文章
    在整个测试会话期间共享
    
    Returns:
        包含测试数据的字典
    """
    logger.info("准备测试数据...")
    
    # 准备测试数据
    data = TestDataManager.prepare_test_data(article_count=5)
    
    # 确保数据创建成功
    if not data["user"] or not data["articles"]:
        logger.error("测试数据准备失败")
        pytest.fail("无法创建必要的测试数据")
    
    logger.info(f"测试数据准备完成: 用户={data['user'].username}, 文章数量={len(data['articles'])}")
    
    # 自定义数据字段以供测试使用
    data["password"] = "Test@12345"  # 用于登录的密码
    data["test_marker"] = data["test_marker"]  # 用于清理的标记
    
    yield data
    
    # 在所有测试完成后清理测试数据
    logger.info("清理测试数据...")
    TestDataManager.clean_test_data()


@pytest.fixture
def browser(playwright: Playwright) -> Browser:
    """
    启动浏览器
    
    Args:
        playwright: Playwright对象
    
    Returns:
        浏览器实例
    """
    browser = playwright[browser_name()].launch(headless=True)
    yield browser
    browser.close()


@pytest.fixture
def page(browser, base_url):
    """
    创建一个Playwright页面
    
    Args:
        browser: Browser实例
        base_url: 测试基础URL
    
    Returns:
        Playwright页面
    """
    page = browser.new_page()
    yield page
    page.close()


@pytest.fixture
def user_browser_context(playwright: Playwright, base_url: str, test_data: Dict[str, Any]) -> BrowserContext:
    """
    创建一个已登录用户的浏览器上下文
    每个测试函数使用一个新的上下文
    
    Args:
        playwright: Playwright对象
        base_url: 测试基础URL
        test_data: 测试数据
    
    Returns:
        已登录的浏览器上下文
    """
    browser = playwright[browser_name()].launch(headless=True)
    context = browser.new_context(
        base_url=base_url,
        viewport={"width": 1280, "height": 720}
    )
    
    # 使用上下文创建页面并登录
    page = context.new_page()
    username = test_data["user"].username
    password = test_data["password"]
    
    auto_login_steps(page, username, password)
    
    # 存储cookies以验证登录状态
    storage_state = context.storage_state()
    logger.info(f"用户 {username} 登录成功，存储了 {len(storage_state['cookies'])} 个cookies")
    
    # 关闭初始页面
    page.close()
    
    yield context
    
    # 测试完成后关闭浏览器
    context.close()
    browser.close()


@pytest.fixture
def authenticated_page(user_browser_context: BrowserContext) -> Page:
    """
    提供一个已通过身份验证的页面
    """
    page = user_browser_context.new_page()
    
    yield page
    
    # 测试完成后关闭页面
    page.close()


@pytest.fixture
def article(test_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    提供可用于测试的单个文章数据
    """
    if not test_data["articles"]:
        # 如果没有现有的文章，创建一个
        user = test_data["user"]
        headline = f"测试文章 - 单独测试 - {int(time.time())}"
        content = "这是为单独测试创建的文章内容。"
        
        article = TestArticleFactory.create(user.id, headline, content, "1")
        if not article:
            pytest.fail("无法创建测试文章")
        
        article_data = {
            "id": article.id,
            "headline": article.headline,
            "content": article.content,
            "type": article.type,
            "user_id": article.user_id
        }
    else:
        # 使用第一篇现有文章
        article = test_data["articles"][0]
        article_data = {
            "id": article.id,
            "headline": article.headline,
            "content": article.content,
            "type": article.type,
            "user_id": article.user_id
        }
    
    logger.info(f"使用测试文章: ID={article_data['id']}, 标题='{article_data['headline']}'")
    return article_data


@pytest.fixture(scope="module")
def clean_db():
    """
    在模块级别清理和准备数据库
    """
    # 测试开始前清理旧的测试数据
    logger.info("模块开始前清理旧测试数据...")
    TestDataManager.clean_test_data()
    
    yield
    
    # 测试完成后再次清理
    logger.info("模块结束后清理测试数据...")
    TestDataManager.clean_test_data()
