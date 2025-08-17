"""
静态资源缓存优化模块
提供静态文件缓存策略、压缩和CDN优化
"""
import os
import hashlib
import gzip
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from flask import Flask, request, Response, send_from_directory, current_app
from woniunote.common.simple_logger import get_simple_logger

logger = get_simple_logger('static_cache')

class StaticCacheOptimizer:
    """静态资源缓存优化器"""
    
    def __init__(self, app: Flask = None):
        self.app = app
        self.cache_headers = {}
        self.compressed_files = {}
        self.file_hashes = {}
        self.last_modified_times = {}
        
        # 缓存配置
        self.cache_config = {
            # 文件类型到缓存时长的映射 (秒)
            '.css': 31536000,      # 1年
            '.js': 31536000,       # 1年
            '.png': 2592000,       # 30天
            '.jpg': 2592000,       # 30天
            '.jpeg': 2592000,      # 30天
            '.gif': 2592000,       # 30天
            '.ico': 31536000,      # 1年
            '.woff': 31536000,     # 1年
            '.woff2': 31536000,    # 1年
            '.ttf': 31536000,      # 1年
            '.eot': 31536000,      # 1年
            '.svg': 2592000,       # 30天
            '.webp': 2592000,      # 30天
            'default': 86400,      # 1天
        }
        
        # 需要压缩的文件类型
        self.compressible_types = {
            '.css', '.js', '.html', '.htm', '.xml', '.json', '.svg', '.txt'
        }
        
        if app:
            self.init_app(app)
    
    def init_app(self, app: Flask):
        """初始化Flask应用"""
        self.app = app
        
        # 设置静态文件处理器
        self._setup_static_handlers()
        
        # 预处理静态文件
        self._preprocess_static_files()
        
        logger.info("静态资源缓存优化器初始化完成")
    
    def _setup_static_handlers(self):
        """设置静态文件处理器"""
        @self.app.route('/css/<path:filename>')
        def optimized_css(filename):
            return self._serve_optimized_static('css', filename)
        
        @self.app.route('/js/<path:filename>')
        def optimized_js(filename):
            return self._serve_optimized_static('js', filename)
        
        @self.app.route('/img/<path:filename>')
        def optimized_img(filename):
            return self._serve_optimized_static('img', filename)
        
        @self.app.route('/fonts/<path:filename>')
        def optimized_fonts(filename):
            return self._serve_optimized_static('fonts', filename)
        
        # 覆盖默认的静态文件处理
        @self.app.route('/static/<path:filename>')
        def optimized_static(filename):
            return self._serve_optimized_static('static', filename)
    
    def _serve_optimized_static(self, folder: str, filename: str):
        """服务优化的静态文件"""
        try:
            # 构建文件路径
            if folder == 'static':
                static_dir = self.app.static_folder
                file_path = os.path.join(static_dir, filename)
            else:
                static_dir = os.path.join(self.app.static_folder, folder)
                file_path = os.path.join(static_dir, filename)
            
            # 检查文件是否存在
            if not os.path.exists(file_path):
                return "File not found", 404
            
            # 获取文件扩展名
            file_ext = os.path.splitext(filename)[1].lower()
            
            # 检查If-Modified-Since头
            if self._check_not_modified(file_path):
                return Response(status=304)
            
            # 检查If-None-Match头 (ETag)
            if self._check_etag_match(file_path):
                return Response(status=304)
            
            # 创建响应
            response = self._create_optimized_response(file_path, filename, file_ext)
            
            return response
            
        except Exception as e:
            logger.error(f"静态文件服务失败 {filename}: {e}")
            return "Internal server error", 500
    
    def _check_not_modified(self, file_path: str) -> bool:
        """检查文件是否未修改"""
        if_modified_since = request.headers.get('If-Modified-Since')
        if not if_modified_since:
            return False
        
        try:
            file_mtime = os.path.getmtime(file_path)
            request_time = time.mktime(time.strptime(
                if_modified_since, '%a, %d %b %Y %H:%M:%S GMT'
            ))
            
            return file_mtime <= request_time
            
        except (ValueError, OSError):
            return False
    
    def _check_etag_match(self, file_path: str) -> bool:
        """检查ETag是否匹配"""
        if_none_match = request.headers.get('If-None-Match')
        if not if_none_match:
            return False
        
        current_etag = self._get_file_etag(file_path)
        return if_none_match == current_etag
    
    def _get_file_etag(self, file_path: str) -> str:
        """获取文件ETag"""
        if file_path in self.file_hashes:
            return self.file_hashes[file_path]
        
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
                etag = f'"{hashlib.md5(content).hexdigest()}"'
                self.file_hashes[file_path] = etag
                return etag
        except (OSError, IOError):
            return '"unknown"'
    
    def _create_optimized_response(self, file_path: str, filename: str, file_ext: str) -> Response:
        """创建优化的响应"""
        # 检查是否支持gzip压缩
        accept_encoding = request.headers.get('Accept-Encoding', '')
        supports_gzip = 'gzip' in accept_encoding.lower()
        
        # 获取文件内容
        if supports_gzip and file_ext in self.compressible_types:
            content, content_encoding = self._get_compressed_content(file_path)
        else:
            with open(file_path, 'rb') as f:
                content = f.read()
            content_encoding = None
        
        # 创建响应
        response = Response(content)
        
        # 设置内容类型
        content_type = self._get_content_type(file_ext)
        response.headers['Content-Type'] = content_type
        
        # 设置缓存头
        self._set_cache_headers(response, file_path, file_ext)
        
        # 设置压缩头
        if content_encoding:
            response.headers['Content-Encoding'] = content_encoding
            response.headers['Vary'] = 'Accept-Encoding'
        
        # 设置ETag
        response.headers['ETag'] = self._get_file_etag(file_path)
        
        # 设置Last-Modified
        mtime = os.path.getmtime(file_path)
        response.headers['Last-Modified'] = time.strftime(
            '%a, %d %b %Y %H:%M:%S GMT', time.gmtime(mtime)
        )
        
        return response
    
    def _get_compressed_content(self, file_path: str) -> Tuple[bytes, Optional[str]]:
        """获取压缩后的内容"""
        # 检查缓存
        if file_path in self.compressed_files:
            cached_data = self.compressed_files[file_path]
            file_mtime = os.path.getmtime(file_path)
            
            if cached_data['mtime'] >= file_mtime:
                return cached_data['content'], 'gzip'
        
        # 读取并压缩文件
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
            
            compressed_content = gzip.compress(content)
            
            # 只有压缩效果显著时才使用压缩版本
            if len(compressed_content) < len(content) * 0.9:
                # 缓存压缩结果
                self.compressed_files[file_path] = {
                    'content': compressed_content,
                    'mtime': os.path.getmtime(file_path)
                }
                return compressed_content, 'gzip'
            else:
                return content, None
                
        except (OSError, IOError) as e:
            logger.error(f"文件压缩失败 {file_path}: {e}")
            with open(file_path, 'rb') as f:
                return f.read(), None
    
    def _get_content_type(self, file_ext: str) -> str:
        """获取内容类型"""
        content_types = {
            '.css': 'text/css',
            '.js': 'application/javascript',
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.ico': 'image/x-icon',
            '.svg': 'image/svg+xml',
            '.woff': 'font/woff',
            '.woff2': 'font/woff2',
            '.ttf': 'font/ttf',
            '.eot': 'application/vnd.ms-fontobject',
            '.webp': 'image/webp',
            '.html': 'text/html',
            '.htm': 'text/html',
            '.xml': 'application/xml',
            '.json': 'application/json',
            '.txt': 'text/plain',
        }
        
        return content_types.get(file_ext, 'application/octet-stream')
    
    def _set_cache_headers(self, response: Response, file_path: str, file_ext: str):
        """设置缓存头"""
        # 获取缓存时长
        cache_duration = self.cache_config.get(file_ext, self.cache_config['default'])
        
        # 设置Cache-Control
        response.headers['Cache-Control'] = f'public, max-age={cache_duration}'
        
        # 设置Expires
        expires_time = time.time() + cache_duration
        response.headers['Expires'] = time.strftime(
            '%a, %d %b %Y %H:%M:%S GMT', time.gmtime(expires_time)
        )
        
        # 静态资源设置immutable（对于有版本号的文件）
        if self._is_versioned_file(file_path):
            response.headers['Cache-Control'] += ', immutable'
    
    def _is_versioned_file(self, file_path: str) -> bool:
        """检查是否为带版本号的文件"""
        filename = os.path.basename(file_path)
        
        # 检查常见的版本号模式
        version_patterns = [
            r'\d+\.\d+\.\d+',  # 1.2.3
            r'v\d+',           # v1, v2
            r'\d{8,}',         # 时间戳
            r'[a-f0-9]{8,}',   # hash
        ]
        
        import re
        for pattern in version_patterns:
            if re.search(pattern, filename):
                return True
        
        return False
    
    def _preprocess_static_files(self):
        """预处理静态文件"""
        if not self.app.static_folder:
            return
        
        static_path = Path(self.app.static_folder)
        if not static_path.exists():
            return
        
        # 遍历静态文件目录
        processed_count = 0
        for file_path in static_path.rglob('*'):
            if file_path.is_file():
                try:
                    # 预计算ETag
                    self._get_file_etag(str(file_path))
                    
                    # 预压缩可压缩文件
                    file_ext = file_path.suffix.lower()
                    if file_ext in self.compressible_types:
                        self._get_compressed_content(str(file_path))
                    
                    processed_count += 1
                    
                except Exception as e:
                    logger.warning(f"预处理文件失败 {file_path}: {e}")
        
        logger.info(f"预处理了 {processed_count} 个静态文件")
    
    def get_cache_stats(self) -> Dict:
        """获取缓存统计信息"""
        return {
            'cached_etags': len(self.file_hashes),
            'compressed_files': len(self.compressed_files),
            'cache_config': self.cache_config.copy(),
            'compressible_types': list(self.compressible_types),
            'total_compressed_size': sum(
                len(data['content']) for data in self.compressed_files.values()
            )
        }
    
    def clear_cache(self):
        """清空缓存"""
        self.file_hashes.clear()
        self.compressed_files.clear()
        self.last_modified_times.clear()
        logger.info("静态资源缓存已清空")
    
    def update_cache_config(self, new_config: Dict[str, int]):
        """更新缓存配置"""
        self.cache_config.update(new_config)
        logger.info(f"缓存配置已更新: {new_config}")

# 全局静态缓存优化器实例
static_cache_optimizer = StaticCacheOptimizer()

def init_static_cache_optimization(app: Flask):
    """初始化静态资源缓存优化"""
    try:
        static_cache_optimizer.init_app(app)
        logger.info("静态资源缓存优化初始化成功")
        return static_cache_optimizer
    except Exception as e:
        logger.error(f"静态资源缓存优化初始化失败: {e}")
        return None

def get_cache_optimizer():
    """获取缓存优化器实例"""
    return static_cache_optimizer