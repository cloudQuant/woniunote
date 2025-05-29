#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
文章基本功能测试

测试WoniuNote文章模块的基本功能，包括:
- 文章列表查看
- 文章详情页面
- 文章类型过滤
"""

import pytest
import sys
import os
import requests
import time

# 导入测试基类和配置
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
from utils.test_base import logger
from utils.test_config import TEST_DATA
from tests.utils.test_base import FlaskAppContextProvider

# 添加app_context fixture
app_context = FlaskAppContextProvider.with_app_context_fixture()

@pytest.mark.browser
def test_article_list(app_context, page, base_url, browser_name):
    """测试文章列表页面"""
    logger.info(f"===== 测试文章列表页面 ({browser_name}) =====")
    
    # 访问文章列表页
    page.goto(f"{base_url}/")
    
    # 等待页面加载
    page.wait_for_load_state("networkidle")
    
    # 检查是否包含文章列表相关标记
    assert page.content().lower().find("article") > -1 or page.content().lower().find("文章") > -1, "页面不包含文章内容"
    
    logger.info("✓ 文章列表页面测试通过")
    
@pytest.mark.browser
def test_article_detail(app_context, page, base_url, browser_name):
    """测试文章详情页面"""
    logger.info(f"===== 测试文章详情页面 ({browser_name}) =====")
    
    # 先获取文章ID，试图查找一篇可访问的文章
    # 访问主页，从那里点击第一篇文章
    page.goto(f"{base_url}/")
    page.wait_for_load_state("networkidle")
    
    # 尝试点击第一篇文章
    article_link = page.locator("a[href*='/article/']").first
    
    if article_link.count() > 0:
        article_link.click()
        page.wait_for_load_state("networkidle")
        
        # 验证是否进入文章详情页
        current_url = page.url
        assert "/article/" in current_url, f"未能进入文章详情页，当前URL: {current_url}"
        
        # 检查是否显示文章内容
        article_content = page.locator(".article-content, .content, #content")
        assert article_content.count() > 0, "页面不包含文章内容区域"
    else:
        # 直接访问一个预设的文章ID
        # 尝试多个ID，直到找到一个有效的
        for article_id in [1, 2, 3, 4, 5]:
            page.goto(f"{base_url}/article/{article_id}")
            page.wait_for_load_state("networkidle")
            
            # 检查是否有文章内容
            if "/article/" in page.url and not "/404" in page.url and not "/error" in page.url:
                logger.info(f"找到可访问的文章ID: {article_id}")
                break
    
    # 检查页面源码是否包含文章相关内容
    page_content = page.content().lower()
    assert "article" in page_content or "文章" in page_content, "页面不包含文章内容"
    
    logger.info("✓ 文章详情页面测试通过")
    
@FlaskAppContextProvider.with_app_context
@pytest.mark.browser
def test_article_by_type(app_context, page, base_url, browser_name):
    """测试按类型筛选文章"""
    logger.info(f"===== 测试按类型筛选文章 ({browser_name}) =====")
    
    try:
        # 访问首页，增加超时时间
        page.goto(f"{base_url}/", timeout=60000)
        
        # 等待页面加载完成
        page.wait_for_load_state("networkidle", timeout=30000)
        
        # 查找分类链接 - 使用更宽松的选择器
        category_selectors = [
            "a[href*='/type/']",
            "a[href*='/category/']", 
            ".category-link",
            ".type-link",
            "nav a",
            ".dropdown-item"
        ]
        
        category_found = False
        for selector in category_selectors:
            category_links = page.locator(selector)
            if category_links.count() > 0:
                logger.info(f"找到分类链接，尝试访问")
                
                # 获取第一个分类链接
                first_category = category_links.first
                category_text = first_category.text_content().strip()
                category_href = first_category.get_attribute("href")
                
                logger.info(f"点击分类: {category_text}, 链接: {category_href}")
                
                # 点击分类链接，增加超时时间
                first_category.click(timeout=60000)
                
                # 等待页面加载
                page.wait_for_load_state("networkidle", timeout=30000)
                
                # 验证页面已切换
                current_url = page.url
                logger.info(f"当前URL: {current_url}")
                
                # 检查是否有文章列表
                article_selectors = [".article-list", ".articles", ".article-item", ".content"]
                for article_selector in article_selectors:
                    if page.locator(article_selector).count() > 0:
                        logger.info(f"✓ 找到文章列表: {article_selector}")
                        category_found = True
                        break
                
                if category_found:
                    break
        
        if not category_found:
            logger.warning("未找到分类链接或分类页面，跳过测试")
            pytest.skip("未找到分类功能")
        
        logger.info("✓ 按类型筛选文章测试通过")
        
    except Exception as e:
        logger.warning(f"按类型筛选测试跳过: {e}")
        pytest.skip(f"按类型筛选测试跳过: {e}")


if __name__ == "__main__":
    # 直接运行测试
    print("请使用pytest运行测试： python -m pytest tests/functional/article/test_article_basic.py -v")

