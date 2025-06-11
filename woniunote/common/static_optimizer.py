#!/usr/bin/env python3
"""
静态资源优化模块
提供文件压缩、CDN支持、缓存策略等功能
"""

import os
import gzip
import time
import hashlib
import mimetypes
import logging
import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path
from flask import Flask, request, make_response, current_app, url_for
from werkzeug.serving import WSGIRequestHandler
import threading

logger = logging.getLogger(__name__)

class StaticFileOptimizer:
    """静态文件优化器"""
    
    def __init__(self, app: Flask = None):
        self.app = app
        self.compression_enabled = True
        self.cache_duration = 31536000  # 1年缓存
        self.gzip_threshold = 1024  # 1KB以上的文件才压缩
        self.supported_extensions = {'.js', '.css', '.html', '.json', '.xml', '.txt', '.svg'}
        self.compressed_files_cache = {}
        self.file_etag_cache = {}
        self.lock = threading.Lock()
        
        if app:
            self.init_app(app)
    
    def init_app(self, app: Flask):
        """初始化应用"""
        self.app = app
        
        # 注册静态文件处理器
        app.before_request(self.before_request)
        app.after_request(self.after_request)
        
        # 添加模板全局函数
        app.jinja_env.globals['static_versioned'] = self.static_versioned
        app.jinja_env.globals['css_bundle'] = self.css_bundle
        app.jinja_env.globals['js_bundle'] = self.js_bundle
        
        logger.info("Static file optimizer initialized")
    
    def before_request(self):
        """请求前处理"""
        # 为静态文件请求添加压缩支持
        if request.path.startswith(('/static/', '/resource/')):
            # 检查客户端是否支持gzip
            accept_encoding = request.headers.get('Accept-Encoding', '')
            if 'gzip' in accept_encoding:
                request.supports_gzip = True
            else:
                request.supports_gzip = False
    
    def after_request(self, response):
        """请求后处理"""
        # 为静态文件添加缓存头
        if request.path.startswith(('/static/', '/resource/')):
            self.add_cache_headers(response)
            
            # 尝试压缩响应
            if (hasattr(request, 'supports_gzip') and 
                request.supports_gzip and 
                self.should_compress(response)):
                response = self.compress_response(response)
        
        return response
    
    def should_compress(self, response) -> bool:
        """判断是否应该压缩响应"""
        # 检查内容类型
        content_type = response.headers.get('Content-Type', '')
        compressible_types = [
            'text/', 'application/javascript', 'application/json',
            'application/xml', 'image/svg+xml'
        ]
        
        if not any(content_type.startswith(ct) for ct in compressible_types):
            return False
        
        # 检查文件大小
        content_length = response.headers.get('Content-Length')
        if content_length and int(content_length) < self.gzip_threshold:
            return False
        
        # 检查是否已经压缩
        if response.headers.get('Content-Encoding'):
            return False
        
        return True
    
    def compress_response(self, response):
        """压缩响应内容"""
        try:
            if response.data:
                compressed_data = gzip.compress(response.data)
                
                # 只有压缩效果明显时才使用
                if len(compressed_data) < len(response.data) * 0.9:
                    response.data = compressed_data
                    response.headers['Content-Encoding'] = 'gzip'
                    response.headers['Content-Length'] = str(len(compressed_data))
                    response.headers['Vary'] = 'Accept-Encoding'
        except Exception as e:
            logger.error(f"Compression error: {e}")
        
        return response
    
    def add_cache_headers(self, response):
        """添加缓存头"""
        try:
            # 设置缓存控制
            response.headers['Cache-Control'] = f'public, max-age={self.cache_duration}'
            response.headers['Expires'] = (
                datetime.utcnow() + timedelta(seconds=self.cache_duration)
            ).strftime('%a, %d %b %Y %H:%M:%S GMT')
            
            # 添加ETag
            if request.path and not response.headers.get('ETag'):
                etag = self.get_file_etag(request.path)
                if etag:
                    response.headers['ETag'] = etag
            
            # 检查条件请求
            if_none_match = request.headers.get('If-None-Match')
            if if_none_match and response.headers.get('ETag'):
                if if_none_match == response.headers['ETag']:
                    response.status_code = 304
                    response.data = b''
        
        except Exception as e:
            logger.error(f"Cache headers error: {e}")
    
    def get_file_etag(self, file_path: str) -> Optional[str]:
        """获取文件ETag"""
        with self.lock:
            if file_path in self.file_etag_cache:
                return self.file_etag_cache[file_path]
        
        try:
            # 构建实际文件路径
            if file_path.startswith('/static/'):
                real_path = os.path.join(self.app.static_folder, file_path[8:])
            elif file_path.startswith('/resource/'):
                real_path = os.path.join(self.app.static_folder, file_path[10:])
            else:
                return None
            
            if os.path.exists(real_path):
                # 基于文件修改时间和大小生成ETag
                stat = os.stat(real_path)
                etag_data = f"{stat.st_mtime}-{stat.st_size}"
                etag = f'"{hashlib.md5(etag_data.encode()).hexdigest()}"'
                
                with self.lock:
                    self.file_etag_cache[file_path] = etag
                
                return etag
        
        except Exception as e:
            logger.error(f"ETag generation error for {file_path}: {e}")
        
        return None
    
    def static_versioned(self, filename: str) -> str:
        """生成带版本号的静态文件URL"""
        try:
            # 获取文件修改时间作为版本号
            file_path = os.path.join(self.app.static_folder, filename)
            if os.path.exists(file_path):
                mtime = int(os.path.getmtime(file_path))
                return url_for('static', filename=filename, v=mtime)
            else:
                return url_for('static', filename=filename)
        except Exception as e:
            logger.error(f"Static versioned URL error: {e}")
            return url_for('static', filename=filename)
    
    def css_bundle(self, files: List[str], bundle_name: str = None) -> str:
        """CSS文件打包"""
        if not bundle_name:
            bundle_name = hashlib.md5(''.join(files).encode()).hexdigest()[:8]
        
        bundle_file = f"bundles/{bundle_name}.css"
        bundle_path = os.path.join(self.app.static_folder, bundle_file)
        
        # 检查是否需要重新生成bundle
        if self.should_rebuild_bundle(files, bundle_path):
            self.create_css_bundle(files, bundle_path)
        
        return self.static_versioned(bundle_file)
    
    def js_bundle(self, files: List[str], bundle_name: str = None) -> str:
        """JavaScript文件打包"""
        if not bundle_name:
            bundle_name = hashlib.md5(''.join(files).encode()).hexdigest()[:8]
        
        bundle_file = f"bundles/{bundle_name}.js"
        bundle_path = os.path.join(self.app.static_folder, bundle_file)
        
        # 检查是否需要重新生成bundle
        if self.should_rebuild_bundle(files, bundle_path):
            self.create_js_bundle(files, bundle_path)
        
        return self.static_versioned(bundle_file)
    
    def should_rebuild_bundle(self, source_files: List[str], bundle_path: str) -> bool:
        """检查是否需要重新构建bundle"""
        if not os.path.exists(bundle_path):
            return True
        
        bundle_mtime = os.path.getmtime(bundle_path)
        
        for file in source_files:
            file_path = os.path.join(self.app.static_folder, file)
            if os.path.exists(file_path):
                if os.path.getmtime(file_path) > bundle_mtime:
                    return True
        
        return False
    
    def create_css_bundle(self, files: List[str], output_path: str):
        """创建CSS bundle"""
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as bundle_file:
                for file in files:
                    file_path = os.path.join(self.app.static_folder, file)
                    if os.path.exists(file_path):
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            # 简单的CSS压缩
                            content = self.minify_css(content)
                            bundle_file.write(content + '\n')
                    else:
                        logger.warning(f"CSS file not found: {file}")
            
            logger.info(f"CSS bundle created: {output_path}")
        
        except Exception as e:
            logger.error(f"CSS bundle creation error: {e}")
    
    def create_js_bundle(self, files: List[str], output_path: str):
        """创建JavaScript bundle"""
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as bundle_file:
                for file in files:
                    file_path = os.path.join(self.app.static_folder, file)
                    if os.path.exists(file_path):
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            # 简单的JS压缩
                            content = self.minify_js(content)
                            bundle_file.write(content + ';\n')
                    else:
                        logger.warning(f"JS file not found: {file}")
            
            logger.info(f"JS bundle created: {output_path}")
        
        except Exception as e:
            logger.error(f"JS bundle creation error: {e}")
    
    def minify_css(self, css_content: str) -> str:
        """简单的CSS压缩"""
        try:
            import re
            
            # 移除注释
            css_content = re.sub(r'/\*.*?\*/', '', css_content, flags=re.DOTALL)
            
            # 移除多余空白
            css_content = re.sub(r'\s+', ' ', css_content)
            css_content = re.sub(r';\s*}', '}', css_content)
            css_content = re.sub(r'{\s*', '{', css_content)
            css_content = re.sub(r'}\s*', '}', css_content)
            css_content = re.sub(r':\s*', ':', css_content)
            css_content = re.sub(r';\s*', ';', css_content)
            
            return css_content.strip()
        
        except Exception as e:
            logger.error(f"CSS minification error: {e}")
            return css_content
    
    def minify_js(self, js_content: str) -> str:
        """简单的JavaScript压缩"""
        try:
            import re
            
            # 移除单行注释
            js_content = re.sub(r'//.*$', '', js_content, flags=re.MULTILINE)
            
            # 移除多行注释
            js_content = re.sub(r'/\*.*?\*/', '', js_content, flags=re.DOTALL)
            
            # 移除多余空白
            js_content = re.sub(r'\s+', ' ', js_content)
            js_content = re.sub(r';\s*', ';', js_content)
            js_content = re.sub(r'{\s*', '{', js_content)
            js_content = re.sub(r'}\s*', '}', js_content)
            
            return js_content.strip()
        
        except Exception as e:
            logger.error(f"JS minification error: {e}")
            return js_content

class CDNManager:
    """CDN管理器"""
    
    def __init__(self, app: Flask = None):
        self.app = app
        self.cdn_enabled = False
        self.cdn_domain = None
        self.fallback_enabled = True
        self.cdn_paths = {
            'css': '/static/css/',
            'js': '/static/js/',
            'images': '/static/images/',
            'fonts': '/static/fonts/'
        }
        
        if app:
            self.init_app(app)
    
    def init_app(self, app: Flask):
        """初始化应用"""
        self.app = app
        
        # 从配置读取CDN设置
        self.cdn_enabled = app.config.get('CDN_ENABLED', False)
        self.cdn_domain = app.config.get('CDN_DOMAIN')
        self.fallback_enabled = app.config.get('CDN_FALLBACK', True)
        
        if self.cdn_enabled:
            app.jinja_env.globals['cdn_url'] = self.cdn_url
            logger.info(f"CDN manager initialized with domain: {self.cdn_domain}")
    
    def cdn_url(self, filename: str) -> str:
        """生成CDN URL"""
        if not self.cdn_enabled or not self.cdn_domain:
            return url_for('static', filename=filename)
        
        try:
            # 确定文件类型
            file_type = self.get_file_type(filename)
            cdn_path = self.cdn_paths.get(file_type, '/static/')
            
            # 生成CDN URL
            cdn_url = f"{self.cdn_domain.rstrip('/')}{cdn_path}{filename}"
            
            # 添加回退机制
            if self.fallback_enabled:
                fallback_url = url_for('static', filename=filename)
                return f"{cdn_url}||{fallback_url}"
            
            return cdn_url
        
        except Exception as e:
            logger.error(f"CDN URL generation error: {e}")
            return url_for('static', filename=filename)
    
    def get_file_type(self, filename: str) -> str:
        """获取文件类型"""
        ext = os.path.splitext(filename)[1].lower()
        
        if ext in ['.css']:
            return 'css'
        elif ext in ['.js']:
            return 'js'
        elif ext in ['.jpg', '.jpeg', '.png', '.gif', '.svg', '.webp']:
            return 'images'
        elif ext in ['.woff', '.woff2', '.ttf', '.eot']:
            return 'fonts'
        else:
            return 'other'

class ImageOptimizer:
    """图片优化器"""
    
    def __init__(self, app: Flask = None):
        self.app = app
        self.webp_enabled = True
        self.quality_levels = {
            'thumbnail': 60,
            'medium': 75,
            'high': 85
        }
        self.responsive_breakpoints = [320, 768, 1024, 1920]
        
        if app:
            self.init_app(app)
    
    def init_app(self, app: Flask):
        """初始化应用"""
        self.app = app
        
        # 添加模板函数
        app.jinja_env.globals['responsive_image'] = self.responsive_image
        app.jinja_env.globals['webp_image'] = self.webp_image
        
        logger.info("Image optimizer initialized")
    
    def responsive_image(self, filename: str, alt: str = "", 
                        sizes: str = "100vw", loading: str = "lazy") -> str:
        """生成响应式图片HTML"""
        try:
            base_name, ext = os.path.splitext(filename)
            
            # 生成不同尺寸的图片URL
            srcset_webp = []
            srcset_original = []
            
            for width in self.responsive_breakpoints:
                webp_file = f"{base_name}_{width}w.webp"
                original_file = f"{base_name}_{width}w{ext}"
                
                srcset_webp.append(f"{url_for('static', filename=webp_file)} {width}w")
                srcset_original.append(f"{url_for('static', filename=original_file)} {width}w")
            
            # 生成HTML
            html = f'''
            <picture>
                <source srcset="{', '.join(srcset_webp)}" sizes="{sizes}" type="image/webp">
                <img src="{url_for('static', filename=filename)}" 
                     srcset="{', '.join(srcset_original)}" 
                     sizes="{sizes}" 
                     alt="{alt}" 
                     loading="{loading}">
            </picture>
            '''
            
            return html.strip()
        
        except Exception as e:
            logger.error(f"Responsive image error: {e}")
            return f'<img src="{url_for("static", filename=filename)}" alt="{alt}">'
    
    def webp_image(self, filename: str, fallback: bool = True) -> str:
        """生成WebP图片URL或HTML"""
        try:
            base_name, ext = os.path.splitext(filename)
            webp_file = f"{base_name}.webp"
            
            if fallback:
                # 生成带回退的HTML
                return f'''
                <picture>
                    <source srcset="{url_for('static', filename=webp_file)}" type="image/webp">
                    <img src="{url_for('static', filename=filename)}">
                </picture>
                '''.strip()
            else:
                # 直接返回WebP URL
                return url_for('static', filename=webp_file)
        
        except Exception as e:
            logger.error(f"WebP image error: {e}")
            return url_for('static', filename=filename)

# 全局实例
_static_optimizer = None
_cdn_manager = None
_image_optimizer = None

def get_static_optimizer() -> StaticFileOptimizer:
    """获取静态文件优化器实例"""
    global _static_optimizer
    if _static_optimizer is None:
        _static_optimizer = StaticFileOptimizer()
    return _static_optimizer

def get_cdn_manager() -> CDNManager:
    """获取CDN管理器实例"""
    global _cdn_manager
    if _cdn_manager is None:
        _cdn_manager = CDNManager()
    return _cdn_manager

def get_image_optimizer() -> ImageOptimizer:
    """获取图片优化器实例"""
    global _image_optimizer
    if _image_optimizer is None:
        _image_optimizer = ImageOptimizer()
    return _image_optimizer

def init_static_optimization(app: Flask):
    """初始化静态资源优化"""
    try:
        # 初始化各个优化器
        static_optimizer = get_static_optimizer()
        cdn_manager = get_cdn_manager()
        image_optimizer = get_image_optimizer()
        
        static_optimizer.init_app(app)
        cdn_manager.init_app(app)
        image_optimizer.init_app(app)
        
        logger.info("Static resource optimization initialized")
        
    except Exception as e:
        logger.error(f"Failed to initialize static optimization: {e}")

def preload_critical_resources(app: Flask, critical_css: List[str] = None, 
                             critical_js: List[str] = None):
    """预加载关键资源"""
    @app.before_first_request
    def setup_preload():
        try:
            preload_links = []
            
            # 预加载关键CSS
            if critical_css:
                for css_file in critical_css:
                    preload_links.append(
                        f'<link rel="preload" href="{url_for("static", filename=css_file)}" as="style">'
                    )
            
            # 预加载关键JS
            if critical_js:
                for js_file in critical_js:
                    preload_links.append(
                        f'<link rel="preload" href="{url_for("static", filename=js_file)}" as="script">'
                    )
            
            # 添加到模板全局变量
            app.jinja_env.globals['preload_links'] = '\n'.join(preload_links)
            
            logger.info(f"Critical resources preload setup: {len(preload_links)} resources")
            
        except Exception as e:
            logger.error(f"Critical resources preload error: {e}") 