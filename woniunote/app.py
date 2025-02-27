from flask import Flask, render_template, request, redirect, session, make_response, jsonify, url_for
from werkzeug.security import generate_password_hash, check_password_hash
import uuid, os, time, pymysql, json, hashlib, traceback
from datetime import datetime, timedelta

from flask import Flask, redirect, request, render_template, session, url_for, jsonify
from werkzeug.security import generate_password_hash
import os
import pymysql
pymysql.install_as_MySQLdb()
import traceback
import hashlib

from woniunote.configs.config import config
from woniunote.common.utils import read_config, get_package_path, get_db_connection, parse_db_uri
from flask_caching import Cache
from woniunote.common.database import db, ARTICLE_TYPES
from woniunote.controller.admin import admin
from woniunote.controller.article import article
from woniunote.controller.card_center import card_center
from woniunote.controller.comment import comment
from woniunote.controller.favorite import favorite
from woniunote.controller.index import index
from woniunote.controller.todo_center import tcenter
from woniunote.controller.ucenter import ucenter
from woniunote.controller.ueditor import ueditor
from woniunote.controller.user import user
from woniunote.module.users import Users

def create_app(config_name='production'):
    app = Flask(__name__, template_folder='template',
                static_url_path='/', static_folder='resource')
    
    # 加载配置
    app.config.from_object(config[config_name])
    
    # 设置安全的SECRET_KEY
    if not app.config.get('SECRET_KEY'):
        app.config['SECRET_KEY'] = os.urandom(24)
    
    # 配置Session
    is_production = config_name == 'production'
    app.config.update(
        # 基本配置
        SECRET_KEY=os.environ.get('SECRET_KEY', os.urandom(24)),
        SESSION_COOKIE_NAME='math_train_session',
        
        # Cookie配置
        SESSION_COOKIE_SECURE=False,  # 即使在生产环境也暂时设为False，除非确认使用了HTTPS
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
        SESSION_COOKIE_PATH='/',
        SESSION_COOKIE_DOMAIN=None,  # 让浏览器自动处理
        
        # Session配置
        PERMANENT_SESSION_LIFETIME=timedelta(days=7),
        SESSION_TYPE='filesystem',  # 使用文件系统存储session
        SESSION_FILE_DIR=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sessions'),  # session文件存储路径
        SESSION_FILE_THRESHOLD=500,  # 最大session文件数
        SESSION_FILE_MODE=384,  # 0o600 文件权限
    )
    
    # 确保session目录存在
    session_dir = app.config['SESSION_FILE_DIR']
    if not os.path.exists(session_dir):
        os.makedirs(session_dir, mode=0o700)  # 创建目录，设置严格的权限
    
    SQLALCHEMY_DATABASE_URI = None
    # 读取自定义配置
    custom_config = read_config()
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
    app.register_blueprint(admin)
    app.register_blueprint(article)
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
        print(e)
        file_path = "error-404.html"
        return render_template(file_path)

    # 定义500错误页面
    @app.errorhandler(500)
    def server_error(e):
        print(e)
        file_path = "error-500.html"
        return render_template(file_path)

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

    @app.route('/math_train_login', methods=['POST'])
    def math_train_login():
        print("begin to login")
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
                print("user found:", user)
                
                if user is None:
                    return jsonify({'success': False, 'message': '用户名或密码错误'}), 401
                
                # 确保密码字段存在
                if not user.get('password'):
                    return jsonify({'success': False, 'message': '账户数据错误'}), 500
                
                # 验证密码
                if check_password_hash(user['password'], password):
                    try:
                        # 生成会话数据
                        session_data = {
                            'user_id': user['id'],
                            'username': user['username'],
                            'login_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            'session_id': str(uuid.uuid4())
                        }
                        
                        # 设置session
                        session.permanent = True
                        for key, value in session_data.items():
                            session[key] = value
                        
                        # 强制保存session
                        session.modified = True
                        
                        # 创建响应
                        response = jsonify({
                            'success': True,
                            'username': user['username'],
                            'redirect': url_for('math_train_user')
                        })
                        
                        # 设置cookie
                        response.set_cookie(
                            'math_train_session',
                            session_data['session_id'],
                            max_age=7 * 24 * 60 * 60,  # 7天有效期
                            httponly=True,
                            samesite='Lax',
                            secure=app.config['SESSION_COOKIE_SECURE'],
                            domain=app.config['SESSION_COOKIE_DOMAIN']
                        )
                        
                        print("Login successful, session data:", dict(session))
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
        if 'user_id' not in session:
            return jsonify({'success': False, 'message': '未登录'}), 401

        try:
            data = request.get_json()
            print("result_data", data)
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
                    session['user_id'],
                    data['math_level'],
                    data['correct_count'],
                    data['total_questions'],
                    data['time_spent']
                ))
                connection.commit()
                print("保存数据成功")
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
        session.clear()
        return jsonify({
            'success': True,
            'redirect': url_for('math_train')
        })

    # 登录状态检查
    @app.route('/math_train_check_login')
    def math_train_check_login():
        # 打印session信息用于调试
        print("Check login session:", dict(session))
        print("Check login cookies:", request.cookies)
        
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
            'loggedIn': 'user_id' in session,
            'username': session.get('username', '')
        })

    @app.route("/math_train_user", methods=["GET"])
    def math_train_user():
        # 检查session是否存在
        print("now session:", dict(session))
        if 'user_id' not in dict(session):
            print("No user_id in session")
            return redirect(url_for('math_train'))
            
        # 打印session信息用于调试
        print("Current session:", dict(session))
        print("Cookies:", request.cookies)
        
        # # 验证session_id
        # session_id = request.cookies.get('math_train_session')
        # if not session_id or session_id != session.get('session_id'):
        #     print("Invalid session_id")
        #     session.clear()
        #     return redirect(url_for('math_train'))
            
        try:
            connection = get_db_connection(DATABASE_INFO)
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT math_level, correct_count, total_questions, time_spent, created_at "
                    "FROM math_train_results WHERE user_id = %s ORDER BY created_at DESC LIMIT 10",
                    (session['user_id'],)
                )
                history_result = cursor.fetchall()
        except Exception as e:
            print(f"获取用户数据错误: {str(e)}")
            traceback.print_exc()
            return jsonify({'error': '服务器内部错误'}), 500
        target_html = "math_train_user.html"
        print(history_result)
        return render_template(target_html, history_result=history_result)

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
                    (session['user_id'],)
                )
                history = cursor.fetchall()

                cursor.execute(
                    "SELECT COUNT(*) AS total_sessions, "
                    "ROUND(AVG(correct_count/total_questions)*100, 1) AS avg_accuracy, "
                    "SUM(time_spent) AS total_time "  # 改为SUM
                    "FROM math_train_results WHERE user_id = %s",
                    (session['user_id'],)
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
