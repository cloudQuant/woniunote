import pytest
from playwright.sync_api import expect
import time
import sys
import os

# 添加项目根目录到Python路径
project_root = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
sys.path.insert(0, project_root)

# 导入Flask应用上下文提供者
from tests.utils.test_base import FlaskAppContextProvider

# 创建app_context fixture
app_context = FlaskAppContextProvider.with_app_context_fixture()

"""
评论功能测试
测试查看、添加和管理评论的功能
"""

# 确保在Flask应用上下文中运行
@pytest.mark.browser
def test_view_comments(app_context, page, base_url, browser_name):
    """测试查看文章评论"""
    # 访问一篇已有评论的文章
    # 假设ID为1的文章存在且有评论
    page.goto(f"{base_url}/article/1")
    
    # 等待页面加载
    page.wait_for_load_state("networkidle")
    
    # 检查评论区域可见
    comments_section = page.locator(".comment-area")
    expect(comments_section).to_be_visible()
    
    # 检查评论列表可见
    comments_list = page.locator(".comment-list")
    expect(comments_list).to_be_visible()

# 确保在Flask应用上下文中运行
@pytest.mark.browser
def test_add_comment_authenticated(app_context, authenticated_page, base_url, browser_name):
    """测试已登录用户添加评论"""
    page = authenticated_page
    
    # 访问一篇文章
    page.goto(f"{base_url}/article/1")
    
    # 等待页面加载
    page.wait_for_load_state("networkidle")
    
    # 确保评论区域可见
    comments_section = page.locator(".comment-area")
    expect(comments_section).to_be_visible()
    
    # 填写评论内容
    comment_text = f"这是一条测试评论 {int(time.time())}"
    page.fill("textarea[name='content']", comment_text)
    
    # 提交评论
    page.click("button.submit-comment")
    
    # 等待页面刷新或评论显示
    page.wait_for_load_state("networkidle")
    
    # 验证评论显示
    expect(page.locator(".comment-list")).to_contain_text(comment_text)

# 确保在Flask应用上下文中运行
@pytest.mark.browser
def test_add_comment_unauthenticated(app_context, page, base_url, browser_name):
    """测试未登录用户尝试添加评论"""
    # 访问一篇文章
    page.goto(f"{base_url}/article/1")
    
    # 等待页面加载
    page.wait_for_load_state("networkidle")
    
    # 尝试填写评论
    comment_text = f"这是一条未登录测试评论 {int(time.time())}"
    
    # 如果评论框可见，尝试提交
    comment_input = page.locator("textarea[name='content']")
    if comment_input.count() > 0:
        comment_input.fill(comment_text)
        page.click("button.submit-comment")
        
        # 应该被重定向到登录页或显示错误消息
        expect(page).to_have_url(re.compile(f"{base_url}/login"))
    else:
        # 如果评论框不可见，验证有登录提示
        expect(page.locator(".login-required-message")).to_be_visible()

# 确保在Flask应用上下文中运行
@pytest.mark.browser
def test_delete_own_comment(app_context, authenticated_page, base_url, browser_name):
    """测试用户删除自己的评论"""
    page = authenticated_page
    
    # 首先发表一条评论
    page.goto(f"{base_url}/article/1")
    comment_text = f"即将删除的评论 {int(time.time())}"
    page.fill("textarea[name='content']", comment_text)
    page.click("button.submit-comment")
    
    # 等待评论显示
    page.wait_for_load_state("networkidle")
    
    # 找到并点击刚发表评论的删除按钮
    # 假设有一个包含评论内容和删除按钮的列表项
    comment_item = page.locator(f".comment-item:has-text('{comment_text}')")
    delete_button = comment_item.locator(".delete-comment")
    delete_button.click()
    
    # 处理确认对话框
    page.on("dialog", lambda dialog: dialog.accept())
    
    # 等待页面重新加载或评论列表更新
    page.wait_for_load_state("networkidle")
    
    # 验证评论已被删除
    expect(page.locator(f".comment-list:has-text('{comment_text}')")).to_have_count(0)

# 确保在Flask应用上下文中运行
@pytest.mark.browser
def test_reply_to_comment(app_context, authenticated_page, base_url, browser_name):
    """测试回复评论功能"""
    page = authenticated_page
    
    # 访问一篇有评论的文章
    page.goto(f"{base_url}/article/1")
    
    # 找到第一条评论并点击回复按钮
    first_comment = page.locator(".comment-item").first
    first_comment.locator(".reply-button").click()
    
    # 填写回复内容
    reply_text = f"这是一条回复 {int(time.time())}"
    page.fill("textarea.reply-textarea", reply_text)
    
    # 提交回复
    page.click("button.submit-reply")
    
    # 等待页面刷新或回复显示
    page.wait_for_load_state("networkidle")
    
    # 验证回复显示
    expect(page.locator(".comment-replies")).to_contain_text(reply_text)
