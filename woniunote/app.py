import uuid, os, time, pymysql, json, hashlib, traceback
from datetime import datetime, timedelta
from flask import Flask, redirect, request, render_template, session, url_for, jsonify, g, make_response
from flask_caching import Cache
from flask_session import Session
from werkzeug.security import generate_password_hash, check_password_hash
import re

from woniunote.configs.config import config
from woniunote.common.utils import read_config, get_package_path, get_db_connection, parse_db_uri
from woniunote.common.database import db, ARTICLE_TYPES
# 使用相对导入方式
from woniunote.common.unified_logging import get_simple_logger
# 新增的优化模块导入
from woniunote.common.unified_cache import init_cache, get_cache_manager, cached
from woniunote.common.rate_limiter import init_rate_limiter, get_rate_limiter, rate_limit, bypass_rate_limit_if_whitelisted
from woniunote.common.async_tasks import init_task_executor, get_task_executor, async_send_email, async_compress_image
from woniunote.common.unified_monitoring import init_monitoring, get_performance_monitor, get_metrics_collector, monitor_function
# 新增Phase 4优化模块
from woniunote.common.unified_database_optimizer import init_database_monitoring, get_database_health, get_query_optimizer
from woniunote.common.static_optimizer import init_static_optimization, get_static_optimizer
from woniunote.common.unified_config import init_config_management, get_config_manager
# Phase 5增强优化模块
from woniunote.common.unified_security import init_security, get_security_manager, require_jwt_auth, require_csrf_token, admin_required
from woniunote.common.performance_enhanced import init_performance_enhancement, get_performance_manager, smart_cache, async_task, monitor_performance
from woniunote.common.user_experience_optimizer import init_user_experience_optimization, get_ux_optimizer, track_user_action, UserActionType, NotificationType
# Phase 6 深度优化模块
from woniunote.common.unified_database_optimizer import init_database_advanced_optimization, get_database_optimizer, cached_query
from woniunote.common.unified_security import init_api_security_enhancement, get_api_security_enhancer, require_api_key, require_signature
from woniunote.common.unified_monitoring import init_intelligent_ops_management, get_ops_manager, monitor_function_health
from woniunote.controller.admin import admin
from woniunote.controller.article import article
from woniunote.controller.card_center import card_center
from woniunote.controller.comment import comment
from woniunote.controller.favorite import favorite
from woniunote.controller.index import index
from woniunote.controller.todo_center import tcenter
from woniunote.controller.ueditor import ueditor
from woniunote.controller.ucenter import ucenter
from woniunote.controller.user import user
from woniunote.module.users import Users
pymysql.install_as_MySQLdb()

# 安全配置常量（移除X-Frame-Options，单独处理）
SECURITY_HEADERS = {
    'X-Content-Type-Options': 'nosniff',
    'X-XSS-Protection': '1; mode=block',
    'Referrer-Policy': 'strict-origin-when-cross-origin',
    # 更宽松的CSP以支持UEditor和跨域资源
    'Content-Security-Policy': "default-src 'self' data: blob:; script-src 'self' 'unsafe-inline' 'unsafe-eval' https:; style-src 'self' 'unsafe-inline' https: data:; font-src 'self' data: https:; img-src 'self' data: blob: https:; frame-src 'self'; connect-src 'self' https:",
}

# 允许的文件扩展名
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif', 'pdf', 'doc', 'docx', 'txt', 'zip', 'rar'}
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB

def validate_input(input_string, max_length=1000, allow_html=False):
    """输入验证函数"""
    if not input_string:
        return ""
    
    # 长度检查
    if len(input_string) > max_length:
        return input_string[:max_length]
    
    # HTML标签检查
    if not allow_html:
        # 移除HTML标签
        clean_text = re.sub(r'<[^>]+>', '', input_string)
        return clean_text.strip()
    
    return input_string.strip()

def is_safe_filename(filename):
    """检查文件名是否安全"""
    if not filename:
        return False
    
    # 检查文件名长度
    if len(filename) > 255:
        return False
    
    # 检查危险字符
    dangerous_chars = ['/', '\\', '..', '<', '>', ':', '"', '|', '?', '*']
    for char in dangerous_chars:
        if char in filename:
            return False
    
    return True

def get_file_extension(filename):
    """安全地获取文件扩展名"""
    if '.' not in filename:
        return ''
    return filename.rsplit('.', 1)[1].lower()


def create_app(config_name='production'):
    # 初始化日志系统
    app_logger = get_simple_logger('app')
    app_logger.info("正在初始化应用程序...")
    
    app = Flask(__name__, template_folder='template',
                static_url_path='/', static_folder='resource')
    
    # 加载配置
    config_class = config[config_name]
    
    # 如果是生产环境，验证必需的环境变量
    if config_name == 'production':
        try:
            config_class.validate_environment()
        except ValueError as e:
            app_logger.error(f"生产环境配置验证失败: {e}")
            raise
    
    app.config.from_object(config_class)
    app_logger.info("应用程序配置已加载")
    
    # 确保始终有静态的SECRET_KEY
    app.config['SECRET_KEY'] = config[config_name].SECRET_KEY
    app_logger.info("已设置静态SECRET_KEY")
    
    # 读取自定义配置
    custom_config = read_config()
    
    # 如果配置文件不存在，使用默认测试配置
    if custom_config is None:
        custom_config = {
            'database': {
                'SQLALCHEMY_DATABASE_URI': 'sqlite:///woniunote_dev.db'
            },
            'SECRET_KEY': 'dev-woniunote-secret-key-2025'
        }
    
    # 从配置文件更新SECRET_KEY
    if custom_config.get('SECRET_KEY'):
        app.config['SECRET_KEY'] = custom_config['SECRET_KEY']
        app_logger.info("已从配置文件更新SECRET_KEY")
    
    # 配置数据库
    if custom_config.get('database', {}).get('SQLALCHEMY_DATABASE_URI'):
        db_uri = custom_config['database']['SQLALCHEMY_DATABASE_URI']
        app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
        
        # 判断数据库类型并输出详细信息
        if db_uri.startswith('mysql://'):
            app_logger.info("✅ 配置MySQL数据库连接")
            app_logger.info(f"数据库URI: {db_uri}")
            print(f"[INFO] ✅ 使用MySQL数据库: {db_uri.split('@')[1].split('/')[0]}/数据库名: {db_uri.split('/')[-1].split('?')[0]}")
        elif db_uri.startswith('sqlite://'):
            app_logger.info("配置SQLite数据库连接")
            app_logger.info(f"数据库URI: {db_uri}")
            print(f"[INFO] 使用SQLite数据库: {db_uri}")
        else:
            app_logger.info(f"数据库URI已配置: {db_uri}")
            print(f"[INFO] 数据库已配置: {db_uri}")
    else:
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///woniunote_dev.db'
        app_logger.warning("使用默认SQLite数据库配置")
        print("[WARNING] 使用默认SQLite数据库配置")
    
    # 从配置文件更新其他数据库配置
    if custom_config.get('database'):
        db_config = custom_config['database']
        for key, value in db_config.items():
            if key.startswith('SQLALCHEMY_'):
                app.config[key] = value
                app_logger.info(f"数据库配置 {key}: {value}")
    
    # 设置默认数据库配置
    app.config.setdefault('SQLALCHEMY_TRACK_MODIFICATIONS', False)
    app.config.setdefault('SQLALCHEMY_POOL_SIZE', 10)
    app.config.setdefault('SQLALCHEMY_POOL_TIMEOUT', 30)
    app.config.setdefault('SQLALCHEMY_POOL_RECYCLE', 1800)
    app.config.setdefault('SQLALCHEMY_MAX_OVERFLOW', 20)
    
    # 添加请求大小限制
    app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE
    
    # 初始化SQLAlchemy
    db.init_app(app)
    
    # 在应用上下文中创建所有数据库表
    with app.app_context():
        try:
            db.create_all()
            app_logger.info("数据库表创建成功")
        except Exception as e:
            app_logger.error(f"数据库表创建失败: {str(e)}")
    
    # 配置Session
    session_dir = app.config.get('SESSION_FILE_DIR')
    if not session_dir:
        session_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sessions')
        if config_name == 'testing':
            session_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test_sessions')
    
    # 确保session目录存在且安全
    if not os.path.exists(session_dir):
        os.makedirs(session_dir, mode=0o700)
    
    # 更新Session配置 - 增强安全性
    session_config = {
        'SESSION_TYPE': 'filesystem',
        'SESSION_FILE_DIR': session_dir,
        'SESSION_FILE_THRESHOLD': 500,
        'SESSION_FILE_MODE': 0o600,
        'SESSION_PERMANENT': True,
        'PERMANENT_SESSION_LIFETIME': timedelta(hours=4),  # 缩短为4小时
        'SESSION_COOKIE_NAME': 'woniunote_session',
        'SESSION_COOKIE_HTTPONLY': True,
        'SESSION_COOKIE_SECURE': False if config_name in ['development', 'testing'] else True,
        'SESSION_COOKIE_SAMESITE': 'Lax',
        'SESSION_COOKIE_PATH': '/',
        'SESSION_COOKIE_DOMAIN': None,
        'SESSION_USE_SIGNER': True,  # 启用session签名
        'SESSION_KEY_PREFIX': 'woniunote:',  # 添加前缀
    }
    app.config.update(session_config)
    
    # 初始化Flask-Session
    Session(app)
    
    # 初始化优化系统
    try:
        # 先初始化动态配置管理
        app_logger.info("初始化动态配置管理...")
        
        # 查找正确的配置文件路径
        current_dir = os.getcwd()
        config_paths = [
            os.path.join(current_dir, "configs", "user_password_config.yaml"),
            os.path.join(os.path.dirname(current_dir), "configs", "user_password_config.yaml"),
            os.path.join(os.path.dirname(__file__), "..", "..", "configs", "user_password_config.yaml"),
        ]
        
        # 找到存在的配置文件
        existing_config_files = []
        for config_path in config_paths:
            abs_path = os.path.abspath(config_path)
            if os.path.exists(abs_path):
                existing_config_files.append(abs_path)
                break
        
        # 如果没有找到配置文件，使用默认配置
        if not existing_config_files:
            app_logger.warning("未找到配置文件，将使用内置默认配置")
            existing_config_files = []
        
        # 初始化配置管理，只传入配置目录
        init_config_management("configs")
        config_manager = get_config_manager()
        
        # 初始化缓存系统
        from woniunote.common.unified_cache import CacheConfig
        cache_config = CacheConfig(
            ttl=config_manager.get('cache.default_ttl', 300) if config_manager else 300,
            max_size=config_manager.get('cache.memory.max_size', 2000) if config_manager else 2000
        )
        app_logger.info("初始化缓存系统...")
        init_cache(config=cache_config)
        
        # 初始化限流系统
        rate_limit_config = {
            'api': {
                'type': 'token_bucket',
                'capacity': config_manager.get('rate_limit.api.capacity', 100) if config_manager else 100,
                'refill_rate': config_manager.get('rate_limit.api.refill_rate', 20) if config_manager else 20,
                'refill_period': config_manager.get('rate_limit.api.refill_period', 1) if config_manager else 1
            },
            'upload': {
                'type': 'token_bucket',
                'capacity': config_manager.get('rate_limit.upload.capacity', 10) if config_manager else 10,
                'refill_rate': config_manager.get('rate_limit.upload.refill_rate', 2) if config_manager else 2,
                'refill_period': config_manager.get('rate_limit.upload.refill_period', 60) if config_manager else 60
            },
            'strict': {
                'type': 'sliding_window',
                'max_requests': config_manager.get('rate_limit.strict.max_requests', 30) if config_manager else 30,
                'window_size': config_manager.get('rate_limit.strict.window_size', 60) if config_manager else 60
            }
        }
        app_logger.info("初始化限流系统...")
        init_rate_limiter(rate_limit_config)
        
        # 初始化异步任务系统
        app_logger.info("初始化异步任务系统...")
        init_task_executor(
            max_workers=config_manager.get('async_tasks.max_workers', 6) if config_manager else 6, 
            queue_size=config_manager.get('async_tasks.queue_size', 2000) if config_manager else 2000
        )
        
        # 初始化监控系统
        monitoring_config = {
            'system_monitoring': config_manager.get('monitoring.system_monitoring', True) if config_manager else True,
            'collect_interval': config_manager.get('monitoring.collect_interval', 30) if config_manager else 30
        }
        app_logger.info("初始化监控系统...")
        init_monitoring(monitoring_config)
        
        # 初始化数据库监控 (Phase 4新增)
        app_logger.info("初始化数据库监控系统...")
        init_database_monitoring(app)
        
        # 初始化静态资源优化 (Phase 4新增)
        app_logger.info("初始化静态资源优化...")
        init_static_optimization(app)
        
        # 初始化安全增强模块
        app_logger.info("初始化安全增强模块...")
        init_security(app)
        
        # 初始化性能增强模块
        app_logger.info("初始化性能增强模块...")
        init_performance_enhancement(app)
        
        # 初始化用户体验优化模块
        app_logger.info("初始化用户体验优化模块...")
        init_user_experience_optimization(app)
        
        # Phase 6 深度优化模块初始化
        app_logger.info("初始化高级数据库优化模块...")
        init_database_advanced_optimization(app, slow_query_threshold=1.0)
        
        app_logger.info("初始化API安全增强模块...")
        init_api_security_enhancement(app)
        
        app_logger.info("初始化智能运维管理模块...")
        init_intelligent_ops_management(app)
        
        app_logger.info("所有优化系统初始化完成")
        
    except Exception as e:
        app_logger.error(f"优化系统初始化失败: {str(e)}")
        # 不阻止应用启动，但记录错误
    
    # 添加安全头中间件
    @app.after_request
    def add_security_headers(response):
        # 设置标准安全头（X-Frame-Options现在由security_enhanced.py处理）
        for header, value in SECURITY_HEADERS.items():
            response.headers[header] = value
        
        # 添加全面的CORS支持，允许跨域访问UEditor资源
        if ('ueditor' in request.path.lower() or 
            request.path.endswith('/uedit')):
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With, Accept, Origin'
            response.headers['Access-Control-Expose-Headers'] = 'Content-Length, Content-Range, Content-Type'
            response.headers['Access-Control-Allow-Credentials'] = 'false'
            response.headers['Access-Control-Max-Age'] = '86400'  # 24小时
        
        # 添加请求ID用于调试
        if hasattr(g, 'request_id'):
            response.headers['X-Request-ID'] = g.request_id
        
        return response
    
    # 处理CORS预检请求
    @app.before_request
    def handle_preflight():
        if request.method == "OPTIONS":
            # 为UEditor资源和API端点处理预检请求
            if ('ueditor' in request.path.lower() or 
                request.path.endswith('/uedit')):
                response = make_response()
                response.headers['Access-Control-Allow-Origin'] = '*'
                response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
                response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With, Accept, Origin'
                response.headers['Access-Control-Expose-Headers'] = 'Content-Length, Content-Range, Content-Type'
                response.headers['Access-Control-Allow-Credentials'] = 'false'
                response.headers['Access-Control-Max-Age'] = '86400'
                return response
    
    # 添加性能监控中间件
    @app.before_request
    def performance_before_request():
        g.start_time = time.time()
        g.request_id = str(uuid.uuid4())[:8]
        
        # 记录请求开始
        performance_monitor = get_performance_monitor()
        metrics_collector = get_metrics_collector()
        
        # 记录基本请求信息
        metrics_collector.record_counter('app.requests.started', 1, {
            'method': request.method,
            'endpoint': request.endpoint or 'unknown'
        })
        
        app_logger.info(f"Request {g.request_id}: {request.method} {request.path} from {request.remote_addr}")
        
        # 检查请求大小
        if request.content_length and request.content_length > MAX_FILE_SIZE:
            app_logger.warning(f"Request {g.request_id}: Request too large ({request.content_length} bytes)")
            return jsonify({'error': 'Request too large'}), 413
    
    @app.after_request
    def performance_after_request(response):
        # 记录请求完成和性能指标
        if hasattr(g, 'start_time'):
            duration = time.time() - g.start_time
            
            performance_monitor = get_performance_monitor()
            metrics_collector = get_metrics_collector()
            
            # 记录请求指标
            performance_monitor.record_request(
                endpoint=request.endpoint or request.path,
                method=request.method,
                status_code=response.status_code,
                duration=duration,
                user_id=session.get('userid')
            )
            
            # 记录性能指标
            metrics_collector.record_timer('app.request.duration', duration)
            metrics_collector.record_counter('app.requests.completed', 1)
            
            if duration > 1.0:  # 记录慢请求
                app_logger.warning(f"Slow request {g.request_id}: {duration:.2f}s")
                metrics_collector.record_counter('app.requests.slow', 1)
            
            # 添加性能头信息
            response.headers['X-Response-Time'] = f"{duration:.3f}s"
            response.headers['X-Request-ID'] = g.request_id
        
        return response
    
    # 添加UEditor资源路径映射 - 直接服务文件而不是重定向
    @app.route('/ueditor/<path:filename>')
    def ueditor_resources(filename):
        """将/ueditor/路径直接映射到resource文件夹"""
        from flask import send_from_directory
        import os
        try:
            resource_path = os.path.join(app.root_path, 'resource', 'ueditor')
            return send_from_directory(resource_path, filename)
        except:
            # 如果文件不存在，返回404
            from flask import abort
            abort(404)
    
    # 注册蓝图
    app.register_blueprint(article)
    app.register_blueprint(admin)
    app.register_blueprint(card_center)
    app.register_blueprint(comment)
    app.register_blueprint(favorite)
    app.register_blueprint(index)
    app.register_blueprint(tcenter)
    app.register_blueprint(ucenter)
    app.register_blueprint(ueditor)
    app.register_blueprint(user)
    
    # 改进错误处理
    @app.errorhandler(404)
    def page_not_found(e):
        app_logger.warning(f"404 Error: {request.path} from {request.remote_addr}")
        if request.headers.get('Content-Type') == 'application/json':
            return jsonify({'error': 'Resource not found'}), 404
        return render_template('error-404.html'), 404
    
    @app.errorhandler(500)
    def internal_server_error(e):
        app_logger.error(f"500 Error: {request.path} - {str(e)} from {request.remote_addr}")
        if request.headers.get('Content-Type') == 'application/json':
            return jsonify({'error': 'Internal server error'}), 500
        return render_template('error-500.html'), 500
    
    @app.errorhandler(403)
    def forbidden(e):
        app_logger.warning(f"403 Error: {request.path} from {request.remote_addr}")
        if request.headers.get('Content-Type') == 'application/json':
            return jsonify({'error': 'Access forbidden'}), 403
        return render_template('error-403.html'), 403
    
    @app.errorhandler(413)
    def request_entity_too_large(e):
        app_logger.warning(f"413 Error: Request too large from {request.remote_addr}")
        return jsonify({'error': 'Request entity too large'}), 413

    # 添加请求预处理
    @app.before_request
    def before():
        # 只在生产环境强制HTTPS
        if config_name == 'production' and request.url.startswith('http://'):
            url = request.url.replace('http://', 'https://', 1)
            return redirect(url, code=301)

        url = request.path
        pass_list = ['/user', '/login', '/logout', '/vcode', '/health', '/metrics', '/task']
        
        if url in pass_list or url.endswith('.js') or url.endswith('.jpg') or url.endswith('.css') or url.endswith('.png') or url.startswith('/task/'):
            return
            
        # 检查session是否存在
        # 先检查基于 session_id 的会话
        session_id = request.cookies.get('session_id')
        if session_id and session.get(f'islogin_{session_id}') == 'true':
            # 用户已登录，不需要进一步处理
            return
            
        # 再检查普通的会话
        if session.get('islogin') is None:
            username = request.cookies.get('username')
            password = request.cookies.get('password')
            
            if username is not None and password is not None:
                # 验证输入
                username = validate_input(username, 50)
                if not username:
                    return
                
                try:
                    user_ = Users()
                    result = user_.find_by_username(username)
                    
                    if len(result) == 1 and hashlib.md5(password.encode()).hexdigest() == result[0].password:
                        # 设置session
                        session['islogin'] = 'true'
                        session['userid'] = result[0].userid
                        session['username'] = username
                        session['nickname'] = result[0].nickname
                        session['role'] = result[0].role
                        # 确保session被保存
                        session.modified = True
                        app_logger.info(f"Auto-login successful for user: {username}")
                        
                        # 记录登录指标
                        get_metrics_collector().record_counter('app.auto_login.success', 1)
                except Exception as e:
                    app_logger.error(f"Auto-login error: {str(e)}")
                    get_metrics_collector().record_counter('app.auto_login.error', 1)
                return

    # 通过自定义过滤器来重构truncate原生过滤器
    def mytruncate(s, length, end='...'):
        count = 0
        new = ''
        for c in s:
            new += c  # 每循环一次，将一个字符添加到new字符串后面
            if ord(c) <= 128:
                count += 0.5
            else:
                count += 1
            if count > length:
                break
        return new + end

    # 定义文章类型函数，供模板页面直接调用
    @app.context_processor
    def get_type():
        content = dict(article_type=ARTICLE_TYPES)
        return content

    # app.jinja_env.globals.update(my_article_type=get_type)
    @app.route('/preupload')
    @rate_limit('moderate')
    def pre_upload():
        file_path = "file-upload.html"
        return render_template(file_path)

    @app.route('/upload', methods=['POST'])
    @rate_limit('upload')
    @monitor_function('upload.file')
    def do_upload():
        try:
            headline = validate_input(request.form.get('headline', ''), 200)
            content = validate_input(request.form.get('content', ''), 5000, allow_html=True)
            file = request.files.get('upfile')
            
            if not headline:
                return jsonify({'error': 'Invalid headline'}), 400
            
            if not file or file.filename == '':
                return jsonify({'error': 'No file selected'}), 400
            
            # 验证文件名安全性
            if not is_safe_filename(file.filename):
                return jsonify({'error': 'Invalid filename'}), 400
            
            # 获取文件扩展名
            file_ext = get_file_extension(file.filename)
            if file_ext not in ALLOWED_EXTENSIONS:
                return jsonify({'error': f'File type not allowed. Allowed types: {", ".join(ALLOWED_EXTENSIONS)}'}), 400
            
            # 检查文件大小
            file.seek(0, os.SEEK_END)
            file_size = file.tell()
            file.seek(0)  # 重置文件指针
            
            if file_size > MAX_FILE_SIZE:
                return jsonify({'error': 'File too large'}), 413
            
            # 生成安全的文件名
            safe_filename = f"{uuid.uuid4().hex}.{file_ext}"
            
            # 异步处理图片压缩（如果是图片）
            if file_ext.lower() in ['jpg', 'jpeg', 'png', 'gif']:
                temp_path = f"/tmp/{safe_filename}"
                compressed_path = f"/tmp/compressed_{safe_filename}"
                
                # 保存原文件
                file.save(temp_path)
                
                # 提交异步压缩任务
                task_id = async_compress_image(temp_path, compressed_path, 800)
                
                app_logger.info(f"Image compression task submitted: {task_id}")
            
            app_logger.info(f"File upload: {headline}, size: {file_size}, type: {file_ext}")
            
            return jsonify({
                'message': 'Upload successful',
                'filename': safe_filename,
                'size': file_size
            })
            
        except Exception as e:
            app_logger.error(f"Upload error: {str(e)}")
            return jsonify({'error': 'Upload failed'}), 500

    @app.route("/math_train", methods=["GET"])
    @rate_limit('moderate')
    @cached(ttl=300)  # 缓存5分钟
    def math_train():
        """训练页面"""
        try:
            target_file = "math_train.html"
            return render_template(target_file)
        except Exception as e:
            app_logger.error(f"Math train page error: {str(e)}")
            return render_template('error-500.html'), 500

    @app.route('/math_train_login', methods=['POST'])
    @rate_limit('api')
    @monitor_function('math_train.login')
    def math_train_login():
        """数学训练登录"""
        try:
            data = request.get_json()
            if not data:
                get_metrics_collector().record_counter('math_train.login.invalid_request', 1)
                return jsonify({'success': False, 'message': 'Invalid request'}), 400
            
            username = validate_input(data.get('username', ''), 50)
            password = data.get('password', '')
            
            if not username or not password:
                get_metrics_collector().record_counter('math_train.login.missing_credentials', 1)
                return jsonify({'success': False, 'message': 'Username and password required'}), 400
            
            # 密码长度检查
            if len(password) < 6 or len(password) > 128:
                get_metrics_collector().record_counter('math_train.login.invalid_password', 1)
                return jsonify({'success': False, 'message': 'Invalid password length'}), 400
            
            # 生成session ID
            session_id = str(uuid.uuid4())
            
            # 存储到session中
            session[f'math_username_{session_id}'] = username
            session[f'math_login_time_{session_id}'] = time.time()
            session[f'islogin_{session_id}'] = 'true'
            session['session_id'] = session_id
            session.modified = True
            
            get_metrics_collector().record_counter('math_train.login.success', 1)
            app_logger.info(f"Math train login successful: {username}")
            
            return jsonify({
                'success': True,
                'message': 'Login successful',
                'sessionId': session_id,
                'username': username
            })
            
        except Exception as e:
            get_metrics_collector().record_counter('math_train.login.error', 1)
            app_logger.error(f"Math train login error: {str(e)}")
            return jsonify({'success': False, 'message': 'Login failed'}), 500

    @app.route('/math_train_save_result', methods=['POST'])
    def math_train_save_result():
        """保存训练结果"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'message': 'Invalid request'}), 400
            
            session_id = data.get('sessionId')
            if not session_id or session.get('session_id') != session_id:
                return jsonify({'success': False, 'message': 'Invalid session'}), 401
            
            username = session.get(f'math_username_{session_id}')
            if not username:
                return jsonify({'success': False, 'message': 'User not logged in'}), 401
            
            # 验证输入数据
            score = data.get('score', 0)
            time_used = data.get('timeUsed', 0)
            correct_count = data.get('correctCount', 0)
            total_count = data.get('totalCount', 0)
            
            # 数据验证
            if not isinstance(score, (int, float)) or score < 0 or score > 100:
                return jsonify({'success': False, 'message': 'Invalid score'}), 400
            
            if not isinstance(time_used, (int, float)) or time_used < 0:
                return jsonify({'success': False, 'message': 'Invalid time'}), 400
            
            if not isinstance(correct_count, int) or correct_count < 0:
                return jsonify({'success': False, 'message': 'Invalid correct count'}), 400
            
            if not isinstance(total_count, int) or total_count < 0 or total_count < correct_count:
                return jsonify({'success': False, 'message': 'Invalid total count'}), 400
            
            # TODO: 保存到数据库
            result_data = {
                'username': username,
                'score': score,
                'time_used': time_used,
                'correct_count': correct_count,
                'total_count': total_count,
                'timestamp': time.time()
            }
            
            app_logger.info(f"Math train result saved: {username}, score: {score}")
            
            return jsonify({
                'success': True,
                'message': 'Result saved successfully'
            })
            
        except Exception as e:
            app_logger.error(f"Save result error: {str(e)}")
            return jsonify({'success': False, 'message': 'Save failed'}), 500

    @app.route('/math_train_register', methods=['POST'])
    def math_train_register():
        """数学训练注册"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'message': 'Invalid request'}), 400
            
            username = validate_input(data.get('username', ''), 50)
            password = data.get('password', '')
            
            if not username or not password:
                return jsonify({'success': False, 'message': 'Username and password required'}), 400
            
            # 用户名验证
            if len(username) < 3:
                return jsonify({'success': False, 'message': 'Username too short'}), 400
            
            if not re.match(r'^[a-zA-Z0-9_]+$', username):
                return jsonify({'success': False, 'message': 'Username contains invalid characters'}), 400
            
            # 密码强度检查
            if len(password) < 6:
                return jsonify({'success': False, 'message': 'Password too short'}), 400
            
            if len(password) > 128:
                return jsonify({'success': False, 'message': 'Password too long'}), 400
            
            # TODO: 检查用户名是否已存在
            # TODO: 保存用户到数据库
            
            app_logger.info(f"Math train registration: {username}")
            
            return jsonify({
                'success': True,
                'message': 'Registration successful'
            })
            
        except Exception as e:
            app_logger.error(f"Math train registration error: {str(e)}")
            return jsonify({'success': False, 'message': 'Registration failed'}), 500

    @app.route('/math_train_logout', methods=['POST'])
    def math_train_logout():
        """数学训练登出"""
        try:
            data = request.get_json()
            session_id = data.get('sessionId') if data else None
            
            if session_id:
                # 清除相关session数据
                keys_to_remove = [
                    f'math_username_{session_id}',
                    f'math_login_time_{session_id}',
                    f'islogin_{session_id}'
                ]
                
                for key in keys_to_remove:
                    session.pop(key, None)
                
                if session.get('session_id') == session_id:
                    session.pop('session_id', None)
                
                session.modified = True
                
                app_logger.info(f"Math train logout: session {session_id}")
            
            return jsonify({'success': True, 'message': 'Logout successful'})
            
        except Exception as e:
            app_logger.error(f"Math train logout error: {str(e)}")
            return jsonify({'success': False, 'message': 'Logout failed'}), 500

    @app.route('/math_train_check_login')
    def math_train_check_login():
        """检查数学训练登录状态"""
        try:
            session_id = request.args.get('sessionId') or session.get('session_id')
            
            if not session_id:
                return jsonify({
                    'loggedIn': False,
                    'username': ''
                })
            
            username = session.get(f'math_username_{session_id}')
            login_time = session.get(f'math_login_time_{session_id}')
            is_logged_in = session.get(f'islogin_{session_id}') == 'true'
            
            # 检查session是否过期（4小时）
            if login_time and time.time() - login_time > 14400:
                # 清除过期session
                keys_to_remove = [
                    f'math_username_{session_id}',
                    f'math_login_time_{session_id}',
                    f'islogin_{session_id}'
                ]
                for key in keys_to_remove:
                    session.pop(key, None)
                session.modified = True
                
                return jsonify({
                    'loggedIn': False,
                    'username': '',
                    'message': 'Session expired'
                })
            
            return jsonify({
                'loggedIn': is_logged_in and bool(username),
                'username': username or '',
                'sessionId': session_id if is_logged_in else ''
            })
            
        except Exception as e:
            app_logger.error(f"Check login error: {str(e)}")
            return jsonify({
                'loggedIn': False,
                'username': '',
                'error': 'Check failed'
            })

    @app.route("/math_train_user", methods=["GET"])
    def math_train_user():
        """数学训练用户页面"""
        try:
            session_id = request.args.get('sessionId') or session.get('session_id')
            
            if not session_id:
                return redirect(url_for('math_train'))
            
            username = session.get(f'math_username_{session_id}')
            is_logged_in = session.get(f'islogin_{session_id}') == 'true'
            
            if not is_logged_in or not username:
                return redirect(url_for('math_train'))
            
            return render_template("math_train_user.html", username=username, session_id=session_id)
            
        except Exception as e:
            app_logger.error(f"Math train user page error: {str(e)}")
            return render_template('error-500.html'), 500

    @app.route('/math_train_user_data', methods=['GET'])
    def math_train_user_data():
        """获取用户训练数据"""
        try:
            session_id = request.args.get('sessionId') or session.get('session_id')
            
            if not session_id:
                return jsonify({'error': 'No session'}), 401
            
            username = session.get(f'math_username_{session_id}')
            is_logged_in = session.get(f'islogin_{session_id}') == 'true'
            
            if not is_logged_in or not username:
                return jsonify({'error': 'Not logged in'}), 401
            
            # TODO: 从数据库获取用户数据
            user_data = {
                'username': username,
                'total_sessions': 0,
                'best_score': 0,
                'total_time': 0,
                'recent_results': []
            }
            
            return jsonify({
                'success': True,
                'data': user_data
            })
            
        except Exception as e:
            app_logger.error(f"Get user data error: {str(e)}")
            return jsonify({'error': 'Failed to get data'}), 500

    @app.route('/math_train_reset_password', methods=['POST'])
    def math_train_reset_password():
        """重置密码"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'message': 'Invalid request'}), 400
            
            session_id = data.get('sessionId')
            old_password = data.get('oldPassword', '')
            new_password = data.get('newPassword', '')
            
            if not session_id or session.get('session_id') != session_id:
                return jsonify({'success': False, 'message': 'Invalid session'}), 401
            
            username = session.get(f'math_username_{session_id}')
            if not username:
                return jsonify({'success': False, 'message': 'User not logged in'}), 401
            
            if not old_password or not new_password:
                return jsonify({'success': False, 'message': 'Passwords required'}), 400
            
            # 密码强度检查
            if len(new_password) < 6:
                return jsonify({'success': False, 'message': 'New password too short'}), 400
            
            if len(new_password) > 128:
                return jsonify({'success': False, 'message': 'New password too long'}), 400
            
            if old_password == new_password:
                return jsonify({'success': False, 'message': 'New password must be different'}), 400
            
            # TODO: 验证旧密码并更新新密码
            
            app_logger.info(f"Password reset for user: {username}")
            
            return jsonify({
                'success': True,
                'message': 'Password reset successful'
            })
            
        except Exception as e:
            app_logger.error(f"Reset password error: {str(e)}")
            return jsonify({'success': False, 'message': 'Reset failed'}), 500

    @app.route('/favicon.ico')
    def favicon():
        """Favicon请求处理"""
        try:
            return app.send_static_file('favicon.ico')
        except Exception as e:
            app_logger.warning(f"Favicon not found: {str(e)}")
            return '', 204

    @app.route('/health')
    @bypass_rate_limit_if_whitelisted
    def health_check():
        """健康检查端点"""
        try:
            health_data = {
                'status': 'healthy',
                'timestamp': datetime.now().isoformat(),
                'version': '4.0',  # 更新版本号为4.0
                'checks': {}
            }
            
            # 检查数据库连接
            try:
                with app.app_context():
                    # 使用新的SQLAlchemy语法
                    from sqlalchemy import text
                    with db.engine.connect() as connection:
                        connection.execute(text('SELECT 1'))
                health_data['checks']['database'] = 'ok'
            except Exception as e:
                health_data['checks']['database'] = f'error: {str(e)[:100]}'
                health_data['status'] = 'unhealthy'
                app_logger.error(f"Database health check failed: {str(e)}")
            
            # 检查缓存系统
            try:
                cache_manager = get_cache_manager()
                cache_manager.set('health_check', 'ok', 10)
                if cache_manager.get('health_check') == 'ok':
                    health_data['checks']['cache'] = 'ok'
                else:
                    health_data['checks']['cache'] = 'not responding'
            except Exception as e:
                health_data['checks']['cache'] = f'error: {str(e)[:100]}'
            
            # 检查异步任务系统
            try:
                task_executor = get_task_executor()
                task_stats = task_executor.get_stats()
                if task_stats['queue_size'] < 1000:  # 队列不满
                    health_data['checks']['async_tasks'] = 'ok'
                else:
                    health_data['checks']['async_tasks'] = 'queue full'
                    health_data['status'] = 'degraded'
            except Exception as e:
                health_data['checks']['async_tasks'] = f'error: {str(e)[:100]}'
            
            # Phase 4新增：数据库监控健康检查
            try:
                db_health = get_database_health()
                health_data['checks']['database_monitor'] = db_health['status']
                health_data['database_stats'] = {
                    'slow_queries': db_health.get('slow_queries_count', 0),
                    'cache_hit_rate': db_health.get('cache_stats', {}).get('hit_rate', 0),
                    'total_queries': db_health.get('total_unique_queries', 0)
                }
                
                if db_health['status'] == 'warning':
                    health_data['status'] = 'degraded'
            except Exception as e:
                health_data['checks']['database_monitor'] = f'error: {str(e)[:100]}'
            
            # 检查静态资源优化
            try:
                static_optimizer = get_static_optimizer()
                health_data['checks']['static_optimization'] = 'ok'
            except Exception as e:
                health_data['checks']['static_optimization'] = f'error: {str(e)[:100]}'
            
            # 检查配置管理
            try:
                config_manager = get_config_manager()
                config_info = config_manager.get_config_info()
                health_data['checks']['config_management'] = 'ok'
                health_data['config_info'] = {
                    'environment': config_info['environment'],
                    'config_keys_count': len(config_info['config_keys']),
                    'validation_errors': len(config_info['validation_errors'])
                }
                
                if config_info['validation_errors']:
                    health_data['status'] = 'degraded'
            except Exception as e:
                health_data['checks']['config_management'] = f'error: {str(e)[:100]}'
            
            # 检查系统资源
            try:
                import psutil
                memory = psutil.virtual_memory()
                cpu = psutil.cpu_percent(interval=0.1)
                
                if memory.percent < 90 and cpu < 90:
                    health_data['checks']['system_resources'] = 'ok'
                else:
                    health_data['checks']['system_resources'] = f'high usage: CPU {cpu}%, Memory {memory.percent}%'
                    if health_data['status'] == 'healthy':
                        health_data['status'] = 'degraded'
                
                health_data['system_info'] = {
                    'memory_usage': f"{memory.percent:.1f}%",
                    'cpu_usage': f"{cpu:.1f}%",
                    'available_memory': f"{memory.available / 1024 / 1024:.0f}MB"
                }
            except ImportError:
                health_data['checks']['system_resources'] = 'psutil not available'
            except Exception as e:
                health_data['checks']['system_resources'] = f'error: {str(e)[:100]}'
            
            # 检查会话存储
            session_dir = app.config.get('SESSION_FILE_DIR')
            if session_dir and os.path.exists(session_dir):
                health_data['checks']['session_storage'] = 'ok'
            else:
                health_data['checks']['session_storage'] = 'session directory missing'
            
            # 记录健康检查指标
            get_metrics_collector().record_counter('health_check.requests', 1)
            
            # 确定HTTP状态码
            status_code = 200
            if health_data['status'] == 'unhealthy':
                status_code = 503
            elif health_data['status'] == 'degraded':
                status_code = 200  # 仍然可用，但性能降级
            
            health_data['uptime'] = time.time() - app.config.get('_app_start_time', time.time())
            
            return jsonify(health_data), status_code
            
        except Exception as e:
            app_logger.error(f"Health check error: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': 'Health check failed',
                'timestamp': datetime.now().isoformat()
            }), 500

    # 新增任务状态查询接口
    @app.route('/task/<task_id>/status')
    @rate_limit('api')
    def get_task_status(task_id):
        """获取异步任务状态"""
        try:
            executor = get_task_executor()
            status = executor.get_task_status(task_id)
            
            if status:
                return jsonify(status)
            else:
                return jsonify({'error': 'Task not found'}), 404
                
        except Exception as e:
            app_logger.error(f"Task status query error: {str(e)}")
            return jsonify({'error': 'Query failed'}), 500

    # 新增监控指标接口
    @app.route('/metrics')
    @rate_limit('strict')
    def get_metrics():
        """获取应用指标"""
        try:
            # 检查权限（可以添加管理员验证）
            if not session.get('role') == 'admin':
                return jsonify({'error': 'Unauthorized'}), 403
            
            performance_monitor = get_performance_monitor()
            metrics_collector = get_metrics_collector()
            
            # 获取性能摘要
            performance_summary = performance_monitor.get_performance_summary()
            
            # 获取最近的指标
            recent_metrics = metrics_collector.get_metrics(since=time.time() - 3600)  # 最近1小时
            
            # 获取异步任务统计
            task_executor = get_task_executor()
            task_stats = task_executor.get_stats()
            
            # Phase 4新增：数据库性能指标
            db_health = get_database_health()
            query_optimizer = get_query_optimizer()
            
            return jsonify({
                'performance': performance_summary,
                'recent_metrics': recent_metrics,
                'task_stats': task_stats,
                'database_performance': {
                    'health': db_health,
                    'slow_queries': query_optimizer.get_slow_queries(20),
                    'query_stats': query_optimizer.get_query_stats(10),
                    'index_suggestions': query_optimizer.suggest_indexes()
                },
                'timestamp': time.time()
            })
            
        except Exception as e:
            app_logger.error(f"Metrics query error: {str(e)}")
            return jsonify({'error': 'Query failed'}), 500

    # Phase 4新增：数据库性能管理端点
    @app.route('/admin/database/performance')
    @rate_limit('strict')
    def database_performance():
        """数据库性能管理页面"""
        try:
            if not session.get('role') == 'admin':
                return redirect(url_for('user.login'))
            
            return render_template('admin/database_performance.html')
            
        except Exception as e:
            app_logger.error(f"Database performance page error: {str(e)}")
            return render_template('error-500.html'), 500
    
    @app.route('/admin/database/clear-stats', methods=['POST'])
    @rate_limit('strict')
    def clear_database_stats():
        """清空数据库统计"""
        try:
            if not session.get('role') == 'admin':
                return jsonify({'error': 'Unauthorized'}), 403
            
            query_optimizer = get_query_optimizer()
            query_optimizer.clear_stats()
            
            app_logger.info("Database statistics cleared by admin")
            return jsonify({'success': True, 'message': 'Database statistics cleared'})
            
        except Exception as e:
            app_logger.error(f"Clear database stats error: {str(e)}")
            return jsonify({'error': 'Failed to clear statistics'}), 500
    
    # Phase 4新增：配置管理端点
    @app.route('/admin/config')
    @rate_limit('strict')
    def config_management():
        """配置管理页面"""
        try:
            if not session.get('role') == 'admin':
                return redirect(url_for('user.login'))
            
            config_manager = get_config_manager()
            config_info = config_manager.get_config_info()
            
            return render_template('admin/config_management.html', config_info=config_info)
            
        except Exception as e:
            app_logger.error(f"Config management page error: {str(e)}")
            return render_template('error-500.html'), 500
    
    @app.route('/admin/config/reload', methods=['POST'])
    @rate_limit('strict')
    def reload_config():
        """重新加载配置"""
        try:
            if not session.get('role') == 'admin':
                return jsonify({'error': 'Unauthorized'}), 403
            
            config_manager = get_config_manager()
            config_manager.reload_config()
            
            app_logger.info("Configuration reloaded by admin")
            return jsonify({'success': True, 'message': 'Configuration reloaded'})
            
        except Exception as e:
            app_logger.error(f"Config reload error: {str(e)}")
            return jsonify({'error': 'Failed to reload configuration'}), 500
    
    @app.route('/admin/config/export')
    @rate_limit('strict')
    def export_config():
        """导出配置"""
        try:
            config_manager = get_config_manager()
            config_data = config_manager.export_config()
            
            response = app.response_class(
                response=json.dumps(config_data, indent=2, ensure_ascii=False),
                status=200,
                mimetype='application/json',
                headers={'Content-Disposition': 'attachment; filename="config_export.json"'}
            )
            
            # 定义一个装饰器来在响应后删除文件
            from flask import after_this_request
            
            @after_this_request
            def remove_file(response):
                return response
            
            return response
            
        except Exception as e:
            app_logger.error(f"Export config error: {e}")
            return jsonify({'status': 'error', 'message': str(e)}), 500

    # Phase 5 增强功能API端点
    
    @app.route('/admin/security/summary')
    @admin_required
    @rate_limit('strict')
    def security_summary():
        """安全摘要"""
        try:
            security_manager = get_security_manager()
            summary = security_manager.get_security_summary()
            
            return jsonify({
                'status': 'success',
                'data': summary,
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            app_logger.error(f"Security summary error: {e}")
            return jsonify({'status': 'error', 'message': str(e)}), 500
    
    @app.route('/admin/security/events')
    @admin_required
    @rate_limit('strict')
    def security_events():
        """安全事件列表"""
        try:
            security_manager = get_security_manager()
            hours = request.args.get('hours', 24, type=int)
            severity = request.args.get('severity')
            
            from woniunote.common.unified_security import SecurityLevel
            severity_filter = None
            if severity and hasattr(SecurityLevel, severity.upper()):
                severity_filter = getattr(SecurityLevel, severity.upper())
            
            events = security_manager.audit_logger.get_recent_events(hours, severity_filter)
            
            # 转换为可序列化的格式
            events_data = []
            for event in events:
                events_data.append({
                    'event_id': event.event_id,
                    'timestamp': event.timestamp.isoformat(),
                    'event_type': event.event_type.value,
                    'severity': event.severity.value,
                    'source_ip': event.source_ip,
                    'user_id': event.user_id,
                    'endpoint': event.endpoint,
                    'description': event.description,
                    'details': event.details,
                    'action_taken': event.action_taken
                })
            
            return jsonify({
                'status': 'success',
                'data': events_data,
                'count': len(events_data),
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            app_logger.error(f"Security events error: {e}")
            return jsonify({'status': 'error', 'message': str(e)}), 500
    
    @app.route('/admin/performance/comprehensive')
    @admin_required
    @rate_limit('strict')
    def performance_comprehensive():
        """综合性能报告"""
        try:
            performance_manager = get_performance_manager()
            report = performance_manager.get_comprehensive_report()
            
            return jsonify({
                'status': 'success',
                'data': report,
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            app_logger.error(f"Performance comprehensive report error: {e}")
            return jsonify({'status': 'error', 'message': str(e)}), 500
    
    @app.route('/admin/performance/cache/clear', methods=['POST'])
    @admin_required
    @rate_limit('strict')
    def clear_performance_cache():
        """清空性能缓存"""
        try:
            performance_manager = get_performance_manager()
            performance_manager.smart_cache.clear()
            
            return jsonify({
                'status': 'success',
                'message': 'Performance cache cleared successfully',
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            app_logger.error(f"Clear performance cache error: {e}")
            return jsonify({'status': 'error', 'message': str(e)}), 500
    
    @app.route('/admin/ux/analytics')
    @admin_required
    @rate_limit('strict')
    def ux_analytics():
        """用户体验分析"""
        try:
            user_id = request.args.get('user_id')
            if not user_id:
                return jsonify({'status': 'error', 'message': 'User ID required'}), 400
            
            ux_optimizer = get_ux_optimizer()
            analytics = ux_optimizer.get_user_analytics(user_id)
            
            return jsonify({
                'status': 'success',
                'data': analytics,
                'user_id': user_id,
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            app_logger.error(f"UX analytics error: {e}")
            return jsonify({'status': 'error', 'message': str(e)}), 500
    
    @app.route('/api/recommendations')
    @rate_limit('api')
    def get_recommendations():
        """获取个性化推荐"""
        try:
            user_id = session.get('userid')
            if not user_id:
                return jsonify({'status': 'error', 'message': 'User not logged in'}), 401
            
            content_type = request.args.get('type', 'article')
            limit = request.args.get('limit', 10, type=int)
            
            ux_optimizer = get_ux_optimizer()
            recommendations = ux_optimizer.get_recommendations(str(user_id), content_type, limit)
            
            return jsonify({
                'status': 'success',
                'data': recommendations,
                'count': len(recommendations),
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            app_logger.error(f"Get recommendations error: {e}")
            return jsonify({'status': 'error', 'message': str(e)}), 500
    
    @app.route('/api/search/smart', methods=['GET', 'POST'])
    @rate_limit('api')
    def smart_search():
        """智能搜索"""
        try:
            query = request.args.get('q') if request.method == 'GET' else request.form.get('q')
            if not query:
                return jsonify({'status': 'error', 'message': 'Query parameter required'}), 400
            
            user_id = session.get('userid')
            content_type = request.args.get('type', 'all')
            limit = request.args.get('limit', 20, type=int)
            offset = request.args.get('offset', 0, type=int)
            
            ux_optimizer = get_ux_optimizer()
            search_results = ux_optimizer.search_engine.search(
                query, str(user_id) if user_id else None, content_type, limit, offset
            )
            
            return jsonify({
                'status': 'success',
                'data': search_results,
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            app_logger.error(f"Smart search error: {e}")
            return jsonify({'status': 'error', 'message': str(e)}), 500
    
    @app.route('/api/notifications')
    @rate_limit('api')
    def get_notifications():
        """获取用户通知"""
        try:
            user_id = session.get('userid')
            if not user_id:
                return jsonify({'status': 'error', 'message': 'User not logged in'}), 401
            
            ux_optimizer = get_ux_optimizer()
            unread_notifications = ux_optimizer.notification_manager.get_unread_notifications(str(user_id))
            counts = ux_optimizer.notification_manager.get_notification_count(str(user_id))
            
            # 转换为可序列化的格式
            notifications_data = []
            for notification in unread_notifications:
                notifications_data.append({
                    'id': notification.id,
                    'type': notification.notification_type.value,
                    'title': notification.title,
                    'content': notification.content,
                    'created_at': notification.created_at.isoformat(),
                    'action_url': notification.action_url,
                    'metadata': notification.metadata
                })
            
            return jsonify({
                'status': 'success',
                'data': {
                    'notifications': notifications_data,
                    'counts': counts
                },
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            app_logger.error(f"Get notifications error: {e}")
            return jsonify({'status': 'error', 'message': str(e)}), 500
    
    @app.route('/api/notifications/<notification_id>/read', methods=['POST'])
    @rate_limit('api')
    def mark_notification_read(notification_id):
        """标记通知为已读"""
        try:
            user_id = session.get('userid')
            if not user_id:
                return jsonify({'status': 'error', 'message': 'User not logged in'}), 401
            
            ux_optimizer = get_ux_optimizer()
            ux_optimizer.notification_manager.mark_as_read(str(user_id), notification_id)
            
            return jsonify({
                'status': 'success',
                'message': 'Notification marked as read',
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            app_logger.error(f"Mark notification read error: {e}")
            return jsonify({'status': 'error', 'message': str(e)}), 500
    
    @app.route('/api/jwt/generate', methods=['POST'])
    @rate_limit('api')
    def generate_jwt():
        """生成JWT令牌"""
        try:
            user_id = session.get('userid')
            if not user_id:
                return jsonify({'status': 'error', 'message': 'User not logged in'}), 401
            
            security_manager = get_security_manager()
            
            payload = {
                'user_id': str(user_id),
                'username': session.get('username', ''),
                'role': session.get('role', 'user')
            }
            
            token = security_manager.jwt_manager.generate_token(payload)
            
            return jsonify({
                'status': 'success',
                'data': {
                    'token': token,
                    'expires_in': security_manager.jwt_manager.default_expires_in
                },
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            app_logger.error(f"Generate JWT error: {e}")
            return jsonify({'status': 'error', 'message': str(e)}), 500
    
    @app.route('/api/user/activity')
    @rate_limit('api')
    def user_activity():
        """用户活动统计"""
        try:
            user_id = session.get('userid')
            if not user_id:
                return jsonify({'status': 'error', 'message': 'User not logged in'}), 401
            
            days = request.args.get('days', 7, type=int)
            
            ux_optimizer = get_ux_optimizer()
            activity_summary = ux_optimizer.behavior_analyzer.get_user_activity_summary(str(user_id), days)
            
            return jsonify({
                'status': 'success',
                'data': activity_summary,
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            app_logger.error(f"User activity error: {e}")
            return jsonify({'status': 'error', 'message': str(e)}), 500

    # Phase 6 新增 API 端点
    
    @app.route('/admin/database/advanced')
    @admin_required
    @rate_limit('strict')
    def database_advanced_optimization():
        """高级数据库优化报告"""
        try:
            db_optimizer = get_database_optimizer()
            if not db_optimizer:
                return jsonify({'error': 'Database optimizer not available'}), 503
            
            optimization_report = db_optimizer.get_optimization_report()
            
            return jsonify({
                'status': 'success',
                'report': optimization_report,
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            app_logger.error(f"Failed to get database optimization report: {str(e)}")
            return jsonify({'error': 'Failed to get database optimization report'}), 500
    
    @app.route('/admin/database/auto-optimize', methods=['POST'])
    @admin_required
    @rate_limit('strict')
    def apply_database_auto_optimizations():
        """应用数据库自动优化"""
        try:
            db_optimizer = get_database_optimizer()
            if not db_optimizer:
                return jsonify({'error': 'Database optimizer not available'}), 503
            
            applied_optimizations = db_optimizer.apply_automatic_optimizations()
            
            return jsonify({
                'status': 'success',
                'applied_optimizations': applied_optimizations,
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            app_logger.error(f"Failed to apply auto optimizations: {str(e)}")
            return jsonify({'error': 'Failed to apply auto optimizations'}), 500
    
    @app.route('/admin/api-security/summary')
    @admin_required
    @rate_limit('strict')
    def api_security_summary():
        """API安全摘要"""
        try:
            api_security = get_api_security_enhancer()
            if not api_security:
                return jsonify({'error': 'API security enhancer not available'}), 503
            
            security_summary = api_security.get_security_summary()
            
            return jsonify({
                'status': 'success',
                'summary': security_summary,
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            app_logger.error(f"Failed to get API security summary: {str(e)}")
            return jsonify({'error': 'Failed to get API security summary'}), 500
    
    @app.route('/admin/system/overview')
    @admin_required
    @rate_limit('strict')
    def system_overview():
        """系统概览"""
        try:
            ops_manager = get_ops_manager()
            if not ops_manager:
                return jsonify({'error': 'Ops manager not available'}), 503
            
            overview = ops_manager.get_system_overview()
            
            return jsonify({
                'status': 'success',
                'overview': overview,
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            app_logger.error(f"Failed to get system overview: {str(e)}")
            return jsonify({'error': 'Failed to get system overview'}), 500
    
    @app.route('/admin/system/capacity-analysis')
    @admin_required
    @rate_limit('strict')
    def capacity_analysis():
        """容量分析"""
        try:
            ops_manager = get_ops_manager()
            if not ops_manager:
                return jsonify({'error': 'Ops manager not available'}), 503
            
            analysis = ops_manager.run_capacity_analysis()
            
            return jsonify({
                'status': 'success',
                'analysis': analysis,
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            app_logger.error(f"Failed to get capacity analysis: {str(e)}")
            return jsonify({'error': 'Failed to get capacity analysis'}), 500
    
    # API示例端点 - 展示API安全功能
    @app.route('/api/secure/test')
    @require_api_key
    @rate_limit('api')
    def secure_api_test():
        """安全API测试端点"""
        return jsonify({
            'message': 'This is a secure API endpoint',
            'timestamp': datetime.now().isoformat(),
            'api_key_used': True
        })

    # 记录应用启动时间
    app.config['_app_start_time'] = time.time()
    
    return app

   

# 创建应用实例
if __name__ == '__main__':
    # 创建应用实例
    app = create_app('development')
    
    # 检查SSL证书文件是否存在
    path = get_package_path("woniunote")
    cert_file = os.path.join(path, "configs", "cert.pem")
    key_file = os.path.join(path, "configs", "key.pem")
    
    if os.path.exists(cert_file) and os.path.exists(key_file):
        # 如果SSL证书存在，使用HTTPS
        app.run(host="127.0.0.1",
                debug=True,
                port=5000,
                ssl_context=(cert_file, key_file))
    else:
        # 如果SSL证书不存在，使用HTTP
        app.run(host="127.0.0.1",
                debug=True,
                port=5000)
        
