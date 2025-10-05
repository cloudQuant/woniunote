'''
应用工厂模块
将大型的 create_app 函数分解为更小的专用函数
'''
import os
import uuid
import logging
from flask import Flask, request, session, g
from woniunote.configs.config import config
from woniunote.common.utils import read_config
from woniunote.common.unified_logging import get_simple_logger
from woniunote.common.database import db
from woniunote.common.unified_security import csrf
from woniunote.common.unified_session import migrate_legacy_session
from woniunote.common.unified_config import secure_config
from woniunote.common.redisdb import redis_connect
from woniunote.common.unified_cache import init_unified_cache_manager
from woniunote.common.rate_limiter import init_rate_limiter

app_logger = get_simple_logger('app_factory')

class AppFactory:
    def __init__(self):
        self.app = None
        self.custom_config = None
    
    def create_app(self, config_name='production'):
        app_logger.info(f"开始创建应用 (环境: {config_name})")
        try:
            from woniunote.common.unified_config import validate_environment
            if not validate_environment():
                app_logger.error("环境验证失败")
                if config_name == 'production':
                    raise RuntimeError("生产环境验证失败，应用启动中止")
                else:
                    app_logger.warning("非生产环境验证失败，继续启动...")
        except ImportError:
            app_logger.warning("环境验证器不可用，跳过验证")
        self.app = self._create_flask_instance()
        self._load_configurations(config_name)
        self._init_extensions()
        with self.app.app_context():
            redis_client = redis_connect()
            if redis_client:
                self.app.extensions['redis_client'] = redis_client
            init_unified_cache_manager(redis_client=redis_client)
            # 读取Flask配置中的限流规则，如果不存在则使用默认配置
            flask_rate_config = self.app.config.get('RATELIMIT_RULES', {})
            
            # 构建完整的限流配置，合并Flask配置和默认值
            rate_limit_config = {}
            
            # API限流配置
            api_config = flask_rate_config.get('api', {})
            rate_limit_config['api'] = {
                'type': api_config.get('type', 'token_bucket'),
                'capacity': api_config.get('capacity', 1000),
                'refill_rate': api_config.get('refill_rate', 200),
                'refill_period': api_config.get('refill_period', 3600)
            }
            
            # Upload限流配置
            upload_config = flask_rate_config.get('upload', {})
            rate_limit_config['upload'] = {
                'type': upload_config.get('type', 'token_bucket'),
                'capacity': upload_config.get('capacity', 100),
                'refill_rate': upload_config.get('refill_rate', 50),
                'refill_period': upload_config.get('refill_period', 3600)
            }
            
            # Strict限流配置
            strict_config = flask_rate_config.get('strict', {})
            rate_limit_config['strict'] = {
                'type': strict_config.get('type', 'sliding_window'),
                'max_requests': strict_config.get('max_requests', 10),
                'window_size': strict_config.get('window_size', 60)
            }
            
            # Moderate限流配置
            moderate_config = flask_rate_config.get('moderate', {})
            rate_limit_config['moderate'] = {
                'type': moderate_config.get('type', 'sliding_window'),
                'max_requests': moderate_config.get('max_requests', 50),
                'window_size': moderate_config.get('window_size', 60)
            }
            
            # Lenient限流配置
            lenient_config = flask_rate_config.get('lenient', {})
            rate_limit_config['lenient'] = {
                'type': lenient_config.get('type', 'sliding_window'),
                'max_requests': lenient_config.get('max_requests', 100),
                'window_size': lenient_config.get('window_size', 60)
            }
            
            # 记录实际使用的限流配置
            print(f"[DEBUG] 限流配置加载完成: {rate_limit_config}")
            init_rate_limiter(rate_limit_config)
        self._configure_session()
        self._register_blueprints()
        self._setup_request_handlers()
        self._initialize_optimization_systems()
        self._configure_templates_and_static()
        self._setup_error_handlers()
        app_logger.info("应用创建完成")
        return self.app
    
    def _create_flask_instance(self):
        app = Flask(__name__, template_folder='template', static_url_path='/resource', static_folder='resource')
        app_logger.info("Flask 实例创建成功")
        return app
    
    def _load_configurations(self, config_name):
        config_class = config[config_name]
        if config_name == 'production':
            try:
                config_class.validate_environment()
            except ValueError as e:
                app_logger.error(f"生产环境配置验证失败: {e}")
                raise
        self.app.config.from_object(config_class)
        self.app.config['SECRET_KEY'] = config[config_name].SECRET_KEY
        self._initialize_config_management()
        self.custom_config = read_config()
        if self.custom_config is None:
            self.custom_config = {
                'database': {
                    'SQLALCHEMY_DATABASE_URI': 'sqlite:///test_database.db'
                }
            }
        self._configure_database()
        secure_config.init_app(self.app)
        app_logger.info("应用配置加载完成")
    
    def _initialize_config_management(self):
        try:
            from woniunote.common.unified_config import init_config_management
            config_manager = init_config_management("configs")
            if config_manager:
                app_logger.info("动态配置管理初始化成功")
            else:
                app_logger.warning("动态配置管理初始化失败，使用默认配置")
        except ImportError:
            app_logger.warning("配置管理模块不可用，使用静态配置")
        except Exception as e:
            app_logger.error(f"配置管理初始化失败: {e}")
    
    def _configure_database(self):
        database_uri = self.custom_config['database']['SQLALCHEMY_DATABASE_URI']
        self.app.config['SQLALCHEMY_DATABASE_URI'] = database_uri
        self.app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        try:
            from woniunote.common.unified_database_optimizer import pool_optimizer
            optimized_options = pool_optimizer.get_optimized_engine_options(database_uri)
            self.app.config['SQLALCHEMY_ENGINE_OPTIONS'] = optimized_options
            app_logger.info("使用优化的数据库连接池配置")
        except ImportError:
            self.app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
                'pool_pre_ping': True,
                'pool_recycle': 1800,
                'pool_size': 20,
                'max_overflow': 10,
                'pool_timeout': 30,
                'connect_args': {
                    'connect_timeout': 10,
                    'read_timeout': 30,
                    'write_timeout': 30
                }
            }
            app_logger.warning("数据库连接池优化器不可用，使用默认配置")
        MAX_FILE_SIZE = 16 * 1024 * 1024
        self.app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE
        app_logger.info("数据库配置完成")
    
    def _init_extensions(self):
        db.init_app(self.app)
        csrf.init_app(self.app)
        with self.app.app_context():
            try:
                db.create_all()
                app_logger.info("数据库表创建成功")
                try:
                    from woniunote.common.unified_database_optimizer import init_database_monitoring
                    pool_optimizer = init_database_monitoring(db.engine)
                    if pool_optimizer:
                        app_logger.info("数据库连接池优化初始化成功")
                except Exception as e:
                    app_logger.warning(f"数据库连接池优化初始化失败: {e}")
            except Exception as e:
                app_logger.error(f"数据库表创建失败: {str(e)}")
        app_logger.info("扩展初始化完成")
    
    def _configure_session(self):
        session_dir = self.app.config.get('SESSION_FILE_DIR')
        if not session_dir:
            session_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sessions')
            if self.app.config.get('TESTING'):
                session_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test_sessions')
        os.makedirs(session_dir, mode=0o700, exist_ok=True)
        self.app.config['SESSION_FILE_DIR'] = session_dir
        app_logger.info(f"会话配置完成，目录: {session_dir}")
    
    def _register_blueprints(self):
        from woniunote.controller.index import index
        from woniunote.controller.user import user
        from woniunote.controller.article import article
        from woniunote.controller.admin import admin
        from woniunote.controller.ucenter import ucenter
        from woniunote.controller.ueditor import ueditor
        from woniunote.controller.comment import comment
        from woniunote.controller.favorite import favorite
        from woniunote.controller.card_center import card_center
        from woniunote.controller.todo_center import tcenter
        blueprints = [
            (index, '/'),
            (user, '/user'),
            (article, '/article'),
            (admin, '/admin'),
            (ucenter, '/ucenter'),
            (ueditor, '/ueditor'),
            (comment, '/comment'),
            (favorite, '/favorite'),
            (card_center, '/card'),
            (tcenter, '/todo')
        ]
        for blueprint, url_prefix in blueprints:
            self.app.register_blueprint(blueprint, url_prefix=url_prefix)
        app_logger.info(f"已注册 {len(blueprints)} 个蓝图")
        @self.app.route('/login', methods=['POST'])
        def redirect_login():
            from flask import request, redirect, url_for
            return redirect(url_for('user.login'), code=307)
        @self.app.route('/loginfo', methods=['GET'])
        def redirect_loginfo():
            from flask import request, redirect, url_for
            return redirect(url_for('user.loginfo'), code=307)
    
    def _setup_request_handlers(self):
        @self.app.before_request
        def before_request():
            g.request_id = str(uuid.uuid4())
            self._security_checks()
            migrate_legacy_session()
            self._auto_login_check()
        @self.app.after_request
        def after_request(response):
            self._add_security_headers(response)
            return response
        app_logger.info("请求处理器设置完成")
    
    def _security_checks(self):
        user_agent = request.headers.get('User-Agent', '')
        if not user_agent or len(user_agent) > 1000:
            app_logger.warning(f"异常 User-Agent: {user_agent[:100]}...")
        if request.method in ['POST', 'PUT', 'DELETE']:
            referer = request.headers.get('Referer', '')
            if referer and not referer.startswith(request.host_url):
                app_logger.warning(f"外部 Referer 检测: {referer}")
    
    def _auto_login_check(self):
        pass_list = [
            '/user/login', '/user/do_register', '/user/logout',
            '/user/get_verification_code', '/static/', '/favicon.ico'
        ]
        url = request.path
        if any(url.startswith(p) for p in pass_list) or any(url.endswith(ext) for ext in ['.js', '.css', '.png', '.jpg']):
            return
        from woniunote.common.unified_session import is_user_logged_in
        if not is_user_logged_in():
            self._attempt_cookie_login()
    
    def _attempt_cookie_login(self):
        username = request.cookies.get('username')
        password = request.cookies.get('password')
        if username and password:
            try:
                from woniunote.module.users import Users
                from woniunote.common.password_utils import verify_password
                from woniunote.common.unified_session import create_user_session
                user_ = Users()
                result = user_.find_by_username(username)
                if len(result) == 1 and verify_password(password, result[0].password):
                    create_user_session(
                        user_id=result[0].userid,
                        username=username,
                        nickname=result[0].nickname,
                        role=result[0].role
                    )
                    app_logger.info(f"Cookie 自动登录成功: {username}")
            except Exception as e:
                app_logger.error(f"Cookie 自动登录失败: {str(e)}")
    
    def _add_security_headers(self, response):
        security_headers = self.app.config.get('SECURITY_HEADERS', {})
        for header, value in security_headers.items():
            response.headers[header] = value
        return response
    
    def _initialize_optimization_systems(self):
        try:
            from woniunote.common.unified_cache import init_cache
            init_cache()
            # Rate limiter already initialized in _init_extensions
            from woniunote.common.unified_monitoring import init_monitoring
            init_monitoring()
            try:
                from woniunote.common.unified_monitoring import init_performance_monitoring
                perf_monitor = init_performance_monitoring(self.app)
                if perf_monitor:
                    app_logger.info("增强性能监控初始化成功")
            except ImportError:
                app_logger.warning("增强性能监控模块不可用")
            try:
                from woniunote.common.unified_cache import init_static_cache_optimization
                cache_optimizer = init_static_cache_optimization(self.app)
                if cache_optimizer:
                    app_logger.info("静态资源缓存优化初始化成功")
            except ImportError:
                app_logger.warning("静态资源缓存优化器不可用")
            app_logger.info("优化系统初始化完成")
        except ImportError as e:
            app_logger.warning(f"优化模块导入失败，使用基础功能: {e}")
        except Exception as e:
            app_logger.error(f"优化系统初始化失败: {e}")
    
    def _configure_templates_and_static(self):
        @self.app.template_filter('truncate_custom')
        def truncate_custom(text, length=100):
            if not text:
                return ""
            if len(text) <= length:
                return text
            truncated = text[:length]
            last_space = truncated.rfind(' ')
            if last_space > length * 0.8:
                truncated = truncated[:last_space]
            return truncated + "..."
        @self.app.context_processor
        def inject_globals():
            return {
                'app_version': '2.1.0',
                'debug_mode': self.app.config.get('DEBUG', False)
            }
        app_logger.info("模板和静态文件配置完成")
    
    def _setup_error_handlers(self):
        try:
            from woniunote.common.unified_error_handler import init_error_handling
            error_handler = init_error_handling(self.app)
            self._register_recovery_handlers(error_handler)
            app_logger.info("增强错误处理器设置完成")
        except ImportError as e:
            app_logger.warning(f"增强错误处理模块不可用，使用基础错误处理: {e}")
            self._setup_basic_error_handlers()
    
    def _register_recovery_handlers(self, error_handler):
        def database_recovery(error):
            try:
                app_logger.info("尝试数据库错误恢复")
                from woniunote.common.database import db
                from woniunote.common.db_connection_manager import get_connection_manager
                try:
                    db.session.rollback()
                    db.session.close()
                except:
                    pass
                connection_manager = get_connection_manager()
                connection_manager.reset_connections()
                with connection_manager.get_session() as session:
                    session.execute("SELECT 1").fetchone()
                app_logger.info("数据库连接恢复成功")
                from flask import jsonify, render_template_string
                if request.is_json:
                    return jsonify({
                        'success': False,
                        'message': '数据库连接已恢复，请重试',
                        'error_code': 1001
                    }), 503
                else:
                    return render_template_string('''
                    <h2>系统维护中</h2>
                    <p>数据库连接已恢复，请刷新页面重试。</p>
                    <script>setTimeout(function(){ location.reload(); }, 2000);</script>
                    '''), 503
            except Exception as recovery_error:
                app_logger.error(f"数据库恢复失败: {recovery_error}")
                return None
        def redis_recovery(error):
            try:
                app_logger.info("尝试Redis错误恢复")
                from woniunote.common.secure_redis_manager import secure_redis_manager
                secure_redis_manager.set_fallback_mode(True)
                app_logger.info("已切换到内存缓存备用方案")
                import threading
                def try_reconnect():
                    import time
                    time.sleep(5)
                    try:
                        secure_redis_manager.test_connection()
                        secure_redis_manager.set_fallback_mode(False)
                        app_logger.info("Redis连接已恢复")
                    except:
                        app_logger.warning("Redis重连失败，继续使用内存缓存")
                threading.Thread(target=try_reconnect, daemon=True).start()
                return None
            except Exception as recovery_error:
                app_logger.error(f"Redis恢复失败: {recovery_error}")
                return None
        def memory_recovery(error):
            try:
                app_logger.warning("检测到内存问题，启动内存清理")
                import gc
                gc.collect()
                try:
                    from woniunote.common.unified_cache import cache_manager
                    cache_manager.invalidate_cache('default')
                    app_logger.info("缓存已清理")
                except:
                    pass
                from flask import jsonify
                if request.is_json:
                    return jsonify({
                        'success': False,
                        'message': '系统负载较高，请稍后重试',
                        'error_code': 1002
                    }), 503
                return None
            except Exception as recovery_error:
                app_logger.error(f"内存恢复失败: {recovery_error}")
                return None
        def filesystem_recovery(error):
            try:
                app_logger.warning("文件系统错误，检查磁盘空间")
                import shutil
                total, used, free = shutil.disk_usage('/')
                free_percent = free / total * 100
                if free_percent < 5:
                    app_logger.error(f"磁盘空间不足: {free_percent:.1f}% 可用")
                    from flask import jsonify
                    return jsonify({
                        'success': False,
                        'message': '系统存储空间不足，请联系管理员',
                        'error_code': 1003
                    }), 507
                return None
            except Exception as recovery_error:
                app_logger.error(f"文件系统恢复失败: {recovery_error}")
                return None
        error_handler.register_recovery_handler('DatabaseError', database_recovery)
        error_handler.register_recovery_handler('ExternalServiceError', redis_recovery)
        error_handler.register_recovery_handler('MemoryError', memory_recovery)
        error_handler.register_recovery_handler('OSError', filesystem_recovery)
        error_handler.register_recovery_handler('IOError', filesystem_recovery)
        app_logger.info("错误恢复处理器注册完成")
    
    def _setup_basic_error_handlers(self):
        @self.app.errorhandler(404)
        def not_found_error(error):
            app_logger.warning(f"404 错误: {request.url}")
            return "页面未找到", 404
        @self.app.errorhandler(500)
        def internal_error(error):
            app_logger.error(f"500 错误: {str(error)}")
            return "服务器内部错误", 500
        @self.app.errorhandler(403)
        def forbidden_error(error):
            app_logger.warning(f"403 错误: {request.url}")
            return "访问被拒绝", 403
        app_logger.info("基础错误处理器设置完成")

app_factory = AppFactory()

def create_app(config_name='production'):
    return app_factory.create_app(config_name)
