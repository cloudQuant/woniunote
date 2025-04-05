
# HTTP协议强制修正插件
# 注册这个插件来确保Pytest和Playwright使用HTTP连接

import os
import sys
from urllib.parse import urlparse, urlunparse

# 强制使用HTTP
def force_http(url):
    if not url or not isinstance(url, str):
        return url
    
    # 解析URL
    parsed = urlparse(url)
    
    # 如果是HTTPS，则转换为HTTP
    if parsed.scheme == 'https':
        components = list(parsed)
        components[0] = 'http'
        return urlunparse(tuple(components))
    return url

# 覆盖playwright的goto方法
def patch_playwright_methods():
    try:
        # 尝试导入playwright
        from playwright.sync_api import Page
        
        # 修补Page.goto方法
        if not hasattr(Page, '_original_goto'):
            Page._original_goto = Page.goto
            
            def patched_goto(self, url, **kwargs):
                patched_url = force_http(url)
                print(f"Playwright: 将URL从 {url} 更改为 {patched_url}")
                return self._original_goto(patched_url, **kwargs)
            
            Page.goto = patched_goto
            print("Playwright goto方法已被覆盖以强制使用HTTP")
    except ImportError:
        print("Playwright模块不可用")
        pass

# 注册插件函数
def pytest_configure(config):
    print("
启用HTTP协议强制插件...")
    
    # 确保base_url使用HTTP
    if hasattr(config.option, 'base_url'):
        original_base_url = getattr(config.option, 'base_url', None)
        if original_base_url and original_base_url.startswith('https'):
            setattr(config.option, 'base_url', force_http(original_base_url))
            print(f"Base URL已从 {original_base_url} 更改为 {config.option.base_url}")
    
    # 修补 Playwright 方法
    patch_playwright_methods()
    
    print("HTTP协议强制插件加载完成!")
