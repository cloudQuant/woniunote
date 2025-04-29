import uuid, os, time, pymysql, json, hashlib, traceback
from datetime import datetime, timedelta
from flask import Flask, redirect, request, render_template, session, url_for, jsonify
from flask_caching import Cache
from flask_session import Session
from werkzeug.security import generate_password_hash, check_password_hash

from woniunote.configs.config import config
from woniunote.common.utils import read_config, get_package_path, get_db_connection, parse_db_uri
from woniunote.common.database import db, ARTICLE_TYPES
# 使用相对导入方式
from woniunote.common.simple_logger import get_simple_logger
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


def create_app(config_name='production'):
    # 初始化日志系统
    app_logger = get_simple_logger('app')
    app_logger.info("正在初始化应用程序...")
    
    app = Flask(__name__, template_folder='template',
                static_url_path='/', static_folder='resource')
    
    # 加载配置
    app.config.from_object(config[config_name])
    app_logger.info("应用程序配置已加载")
    
    # 设置安全的SECRET_KEY
    if not app.config.get('SECRET_KEY'):
        app.config['SECRET_KEY'] = os.urandom(24)
    
    # 读取自定义配置
    custom_config = read_config()
    
    # 配置Session
    session_dir = app.config.get('SESSION_FILE_DIR')
    if not session_dir:
        session_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sessions')
        if config_name == 'testing':
            session_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test_sessions')
    
    # 确保session目录存在
    if not os.path.exists(session_dir):
        os.makedirs(session_dir, mode=0o700)
    
    # 更新Session配置
    session_config = {
        'SESSION_TYPE': 'filesystem',
        'SESSION_FILE_DIR': session_dir,
        'SESSION_FILE_THRESHOLD': 500,
        'SESSION_FILE_MODE': 0o600,
        'SESSION_PERMANENT': True,
        'PERMANENT_SESSION_LIFETIME': timedelta(days=7),
        'SESSION_COOKIE_NAME': 'woniunote_session',
        'SESSION_COOKIE_HTTPONLY': True,
        'SESSION_COOKIE_SECURE': False if config_name in ['development', 'testing'] else True,
        'SESSION_COOKIE_SAMESITE': 'Lax',
        'SESSION_COOKIE_PATH': '/',
        'SESSION_COOKIE_DOMAIN': None
    }
    app.config.update(session_config)
    
    # 初始化Flask-Session
    Session(app)
    
    # 数据库配置
    SQLALCHEMY_DATABASE_URI = None
    if custom_config:
        SQLALCHEMY_DATABASE_URI = custom_config['database']["SQLALCHEMY_DATABASE_URI"]
        app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
        if 'redis' in custom_config:
            app.config['CACHE_REDIS_URL'] = custom_config['redis']['REDIS_URL']
            
        # 如果自定义配置中有session配置，则使用自定义配置
        if 'session' in custom_config:
            app.config.update(custom_config['session'])
            
    DATABASE_INFO = parse_db_uri(SQLALCHEMY_DATABASE_URI)
    
    # 初始化扩展
    cache = Cache(app)
    db.init_app(app)
    
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
    
    # 定义404错误页面
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('error-404.html'), 404
    
    # 定义500错误页面
    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('error-500.html'), 500
    
    @app.before_request
    def before():
        # 只在生产环境强制HTTPS
        if request.url.startswith('http://'):
            url = request.url.replace('http://', 'https://', 1)
            return redirect(url, code=301)

        url = request.path
        pass_list = ['/user', '/login', '/logout', '/vcode']
        
        if url in pass_list or url.endswith('.js') or url.endswith('.jpg'):
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
    def pre_upload():
        file_path = "file-upload.html"
        return render_template(file_path)

    @app.route('/upload', methods=['POST'])
    def do_upload():
        headline = request.form.get('headline')
        content = request.form.get('content')
        file = request.files.get('upfile')
        print(headline, content)  # 可以正常获取表单元素的值

        suffix = file.filename.split('.')[-1]  # 取得文件的后缀名
        # 也可以根据文件的后缀名对文件类型进行过滤，如：
        if suffix.lower() not in ['jpg', 'jpeg', 'png', 'rar', 'zip', 'doc', 'docx']:
            return 'Invalid'

        # 将文件保存到某个目录中
        # file.save('D:/test001.' + suffix)
        return 'Done'

    @app.route("/math_train", methods=["GET"])
    def math_train():
        """训练页面"""
        target_file = "math_train.html"
        return render_template(target_file)

    # @app.after_request
    # def log_route(response):
    #     print(f"📡 实际处理路由: {request.endpoint}")
    #     return response

    @app.route('/math_train_login', methods=['POST'])
    def math_train_login():
        try:
            data = request.get_json()
            username = data.get('username', '').strip()
            password = data.get('password', '').strip()

            if not username or not password:
                return jsonify({'success': False, 'message': '用户名和密码不能为空'}), 400
            
            connection = get_db_connection(DATABASE_INFO)
            with connection.cursor() as cur:
                cur.execute("SELECT id, username, password FROM math_train_users WHERE username = %s", (username,))
                user = cur.fetchone()
                
                if user is None:
                    return jsonify({'success': False, 'message': '用户名或密码错误'}), 401
                
                if not user.get('password'):
                    return jsonify({'success': False, 'message': '账户数据错误'}), 500
                
                if check_password_hash(user['password'], password):
                    try:
                        # 生成会话数据
                        session_data = {
                            'math_train_user_id': user['id'],  # 使用特定的key
                            'math_train_username': user['username'],  # 使用特定的key
                            'math_train_login_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            'math_train_session_id': str(uuid.uuid4())
                        }
                        
                        # 只清除math_train相关的session数据
                        for key in list(session.keys()):
                            if key.startswith('math_train_'):
                                session.pop(key, None)
                        
                        # 设置新session
                        session.permanent = True
                        for key, value in session_data.items():
                            session[key] = value
                        
                        session.modified = True
                        
                        response = jsonify({
                            'success': True,
                            'username': user['username'],
                            'redirect': url_for('math_train_user')
                        })
                        
                        return response
                        
                    except Exception as e:
                        print("Session error:", e)
                        traceback.print_exc()
                        return jsonify({'success': False, 'message': 'Session错误'}), 500
                else:
                    return jsonify({'success': False, 'message': '用户名或密码错误'}), 401

        except Exception as e:
            traceback.print_exc()
            return jsonify({'success': False, 'message': '服务器错误'}), 500

    # 保存训练结果路由
    @app.route('/math_train_save_result', methods=['POST'])
    def math_train_save_result():
        print("开始保存结果")
        if 'math_train_user_id' not in session:
            return jsonify({'success': False, 'message': '未登录'}), 401

        try:
            data = request.get_json()
            # print("result_data", data)
            required_fields = ['math_level', 'correct_count', 'total_questions', 'time_spent']
            if not all(field in data for field in required_fields):
                return jsonify({'success': False, 'message': '数据不完整'}), 400

            connection = get_db_connection(DATABASE_INFO)
            with connection.cursor() as cur:
                cur.execute("""
                    INSERT INTO math_train_results 
                    (user_id, math_level, correct_count, total_questions, time_spent)
                    VALUES (%s, %s, %s, %s, %s)
                """, (
                    session['math_train_user_id'],
                    data['math_level'],
                    data['correct_count'],
                    data['total_questions'],
                    data['time_spent']
                ))
                connection.commit()
                # print("保存数据成功")
                return jsonify({'success': True})

        except pymysql.Error as e:
            connection.rollback()
            return jsonify({'success': False, 'message': f'数据库错误: {e}'}), 500
        except Exception as e:
            traceback.print_exc()
            return jsonify({'success': False, 'message': '服务器错误'}), 500

    @app.route('/math_train_register', methods=['POST'])
    def math_train_register():
        """用户注册"""
        print("开始进行注册")
        try:
            data = request.get_json()
            username = data.get('username')
            password = data.get('password')
            email = data.get('email')

            if not username or not password or not email:
                return jsonify({'success': False, 'message': '用户名、密码和邮箱不能为空'}), 400

            hashed_password = generate_password_hash(password)

            with get_db_connection(DATABASE_INFO) as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        "INSERT INTO math_train_users (username, password, email) VALUES (%s, %s, %s)",
                        (username, hashed_password, email)
                    )
                    connection.commit()
                    return jsonify({'success': True, 'message': '注册成功，请登录'})

        except pymysql.IntegrityError:
            return jsonify({'success': False, 'message': '用户名或邮箱已存在'}), 400
        except Exception as e:
            print(f"注册错误: {str(e)}")
            traceback.print_exc()
            return jsonify({'success': False, 'message': '注册失败'}), 500

    @app.route('/math_train_logout', methods=['POST'])
    def math_train_logout():
        print("begin math_train_logout")
        # 只清除math_train相关的session数据
        for key in list(session.keys()):
            if key.startswith('math_train_'):
                session.pop(key, None)
        return jsonify({
            'success': True,
            'redirect': url_for('math_train')
        })

    # 登录状态检查
    @app.route('/math_train_check_login')
    def math_train_check_login():
        # 打印session信息用于调试
        # print("Check login session:", dict(session))
        # print("Check login cookies:", request.cookies)
        
        # 验证session完整性
        # session_id = request.cookies.get('math_train_session')
        # if not session_id or session_id != session.get('session_id'):
        #     print("Invalid session in check_login")
        #     session.clear()
        #     return jsonify({
        #         'loggedIn': False,
        #         'username': ''
        #     })
        #
        return jsonify({
            'loggedIn': 'math_train_user_id' in session,
            'username': session.get('math_train_username', '')
        })

    @app.route("/math_train_user", methods=["GET"])
    def math_train_user():
        try:
            # 打印完整的请求信息
            # print("Request headers:", dict(request.headers))
            # print("Request cookies:", dict(request.cookies))
            # print("Current session:", dict(session))
            
            # 检查math_train专用的session
            if 'math_train_user_id' not in session:
                return redirect(url_for('math_train'))
            
            # 获取用户信息
            connection = get_db_connection(DATABASE_INFO)
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT id, username FROM math_train_users WHERE id = %s",
                    (session['math_train_user_id'],)
                )
                user = cursor.fetchone()
                
                if not user:
                    # 只清除math_train相关的session
                    for key in list(session.keys()):
                        if key.startswith('math_train_'):
                            session.pop(key, None)
                    return redirect(url_for('math_train'))
                
                return render_template('math_train_user.html')
                
        except Exception as e:
            print("Error in math_train_user:", e)
            traceback.print_exc()
            return redirect(url_for('math_train'))

    @app.route('/math_train_user_data', methods=['GET'])
    def math_train_user_data():
        """获取用户训练数据"""
        # if 'user_id' not in session:
        #     return jsonify({'error': '未登录'}), 401
        try:
            connection = get_db_connection(DATABASE_INFO)
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT math_level, correct_count, total_questions, time_spent, created_at "
                    "FROM math_train_results WHERE user_id = %s ORDER BY created_at DESC LIMIT 10",
                    (session['math_train_user_id'],)
                )
                history = cursor.fetchall()

                cursor.execute(
                    "SELECT COUNT(*) AS total_sessions, "
                    "ROUND(AVG(correct_count/total_questions)*100, 1) AS avg_accuracy, "
                    "SUM(time_spent) AS total_time "  # 改为SUM
                    "FROM math_train_results WHERE user_id = %s",
                    (session['math_train_user_id'],)
                )
                stats = cursor.fetchone()

                return jsonify({
                    'history': history,
                    'total_sessions': stats['total_sessions'],
                    'avg_accuracy': stats['avg_accuracy'] or 0,
                    'total_time': stats['total_time'] or 0,
                })

        except Exception as e:
            print(f"获取用户数据错误: {str(e)}")
            traceback.print_exc()
            return jsonify({'error': '服务器内部错误'}), 500

    @app.route('/math_train_reset_password', methods=['POST'])
    def math_train_reset_password():
        """重置用户密码"""
        try:
            data = request.get_json()
            username = data.get('username')
            old_password = data.get('old_password')
            new_password = data.get('new_password')

            if not all([username, old_password, new_password]):
                return jsonify({'success': False, 'message': '所有字段都必须填写'}), 400

            connection = get_db_connection(DATABASE_INFO)
            with connection.cursor() as cursor:
                # 先检查用户是否存在
                cursor.execute("SELECT id, password FROM math_train_users WHERE username = %s", (username,))
                user = cursor.fetchone()

                if not user:
                    return jsonify({'success': False, 'message': '用户不存在'}), 404

                # 验证旧密码
                if not check_password_hash(user['password'], old_password):
                    return jsonify({'success': False, 'message': '原密码错误'}), 401

                # 生成新密码的哈希值
                hashed_password = generate_password_hash(new_password)

                # 更新密码
                cursor.execute(
                    "UPDATE math_train_users SET password = %s WHERE id = %s",
                    (hashed_password, user['id'])
                )
                connection.commit()

                return jsonify({'success': True, 'message': '密码已成功更新'})

        except Exception as e:
            traceback.print_exc()
            return jsonify({'success': False, 'message': '服务器错误'}), 500

    # todo why need @app.route('/favicon.ico')
    @app.route('/favicon.ico')
    def favicon():
        # 打印请求头信息
        # print("Request Headers:", request.headers)
        return '/static/favicon.ico'

    @app.route('/health')
    def health_check():
        return {'status': 'ok', 'timestamp': time.time()}, 200

    return app

   

# 创建应用实例
app = create_app()

if __name__ == '__main__':
    # app = create_app(config_name='development')
    path = get_package_path("woniunote")
    app.run(host="127.0.0.1",
            debug=True,
            port=5000,
            ssl_context=(path + "/configs/cert.pem", path + "/configs/key.pem"))
        
