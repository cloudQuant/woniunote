import os
from flask import Flask, redirect, render_template, session, request, url_for, jsonify
from flask_sslify import SSLify
from flask_session import Session
from werkzeug.security import generate_password_hash, check_password_hash
from woniunote.common.database import db, ARTICLE_TYPES
from woniunote.common.utils import read_config, get_package_path, get_db_connection, parse_db_uri
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
from woniunote.module.articles import Articles
from woniunote.common.timer import can_use_minute
from datetime import timedelta
import pymysql
from pymysql.cursors import DictCursor
pymysql.install_as_MySQLdb()
# import MySQLdb
import math
import traceback
config_result = read_config()

SQLALCHEMY_DATABASE_URI = config_result['database']["SQLALCHEMY_DATABASE_URI"]
app = Flask(__name__, template_folder='template',
            static_url_path='/', static_folder='resource')
app.config['SECRET_KEY'] = os.urandom(24)
# 启动调试功能，生产环境注释掉
app.debug = True  # 启用调试模式

# 使用集成方式处理SQLAlchemy
app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # True: 跟踪数据库的修改，及时发送信号
app.config['SQLALCHEMY_POOL_SIZE'] = 100  # 数据库连接池的大小。默认是数据库引擎的默认值（通常是 5）
# app.config['SQLALCHEMY_POOL_RECYCLE'] = -1
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_PERMANENT'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=1)
# Session(app)
# app.config.update(
#     SESSION_COOKIE_SECURE=True,
#     SESSION_COOKIE_HTTPONLY=True,
#     SESSION_COOKIE_SAMESITE='Lax'
# )
DATABASE_INFO = parse_db_uri(SQLALCHEMY_DATABASE_URI)
# 实例化db对象
# db = SQLAlchemy(app)
db.init_app(app)
sslify = SSLify(app)

app.register_blueprint(index)
app.register_blueprint(user)
app.register_blueprint(article)
app.register_blueprint(favorite)
app.register_blueprint(comment)
app.register_blueprint(ueditor)
app.register_blueprint(admin)
app.register_blueprint(ucenter)
app.register_blueprint(tcenter)
app.register_blueprint(card_center)

package_path = get_package_path("woniunote")


# 定义404错误页面
@app.errorhandler(404)
def page_not_found(e):
    print(e)
    # file_path = os.path.join(package_path, 'template', 'error-404.html')
    file_path = "error-404.html"
    return render_template(file_path)


# 定义500错误页面
@app.errorhandler(500)
def server_error(e):
    print(e)
    # file_path = os.path.join(package_path, 'template', 'error-500.html')
    file_path = "error-500.html"
    return render_template(file_path)


# 定义全局拦截器，实现自动登录
@app.before_request
def before():
    if request.url.startswith('http://'):
        url = request.url.replace('http://', 'https://', 1)
        return redirect(url, code=301)

    url = request.path

    pass_list = ['/user', '/login', '/logout']
    if url in pass_list or url.endswith('.js') or url.endswith('.jpg'):
        pass

    elif session.get('islogin') is None:
        username = request.cookies.get('username')
        password = request.cookies.get('password')
        if username is not None and password is not None:
            user_ = Users()
            result = user_.find_by_username(username)
            if len(result) == 1 and result[0].password == password:
                session['islogin'] = 'true'
                session['userid'] = result[0].userid
                session['username'] = username
                session['nickname'] = result[0].nickname
                session['role'] = result[0].role


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
    # file_path = os.path.join(package_path, 'template', 'file-upload.html')
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
    return render_template("math_train.html")


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
            user_dict = cur.fetchone()
            print("user_dict", user_dict)
            print("user_name", username)
            print("password", password)
            if not user or not check_password_hash(user_dict['password'], password):
                return jsonify({'success': False, 'message': '用户名或密码错误'}), 401

            # 设置持久会话
            session.permanent = True
            session['user_id'] = user_dict['id']
            session['username'] = user_dict['username']

            return jsonify({
                'success': True,
                'username': user_dict['username'],
                'redirect': url_for('math_train_user')
            })

    except Exception as e:
        traceback.print_exception(e)
        return jsonify({'success': False, 'message': '服务器错误'}), 500


# 保存训练结果路由
@app.route('/math_train_save_result', methods=['POST'])
def math_train_save_result():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '未登录'}), 401

    try:
        data = request.get_json()
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
            return jsonify({'success': True})

    except pymysql.Error as e:
        connection.rollback()
        return jsonify({'success': False, 'message': f'数据库错误: {e}'}), 500
    except Exception as e:
        traceback.print_exception(e)
        return jsonify({'success': False, 'message': '服务器错误'}), 500

@app.route('/math_train_register', methods=['POST'])
def math_train_register():
    """用户注册"""
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        email = data.get('email')

        if not username or not password or not email:
            return jsonify({'success': False, 'message': '用户名、密码和邮箱不能为空'}), 400

        hashed_password = generate_password_hash(password)

        with get_db_connection() as connection:
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
    session.clear()
    return jsonify({
        'success': True,
        'redirect': url_for('math_train')
    })

# 登录状态检查
@app.route('/math_train_check_login')
def math_train_check_login():
    return jsonify({
        'loggedIn': 'user_id' in session,
        'username': session.get('username', '')
    })

@app.route("/math_train_user", methods=["GET"])
def math_train_user():
    print("进入用户中心界面")
    print("session", session)
    # """用户中心页面"""
    if 'user_id' not in session:
        return redirect(url_for('math_train'))
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
                "MIN(time_spent) AS best_time "
                "FROM math_train_results WHERE user_id = %s",
                (session['user_id'],)
            )
            stats = cursor.fetchone()

            return jsonify({
                'history': history,
                'total_sessions': stats['total_sessions'],
                'avg_accuracy': stats['avg_accuracy'] or 0,
                'best_time': f"{stats['best_time'] // 60:02d}:{stats['best_time'] % 60:02d}" if stats['best_time'] else "00:00"
            })

    except Exception as e:
        print(f"获取用户数据错误: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': '服务器内部错误'}), 500

# todo why need @app.route('/favicon.ico')
@app.route('/favicon.ico')
def favicon():
    # 打印请求头信息
    # print("Request Headers:", request.headers)
    return '/static/favicon.ico'


if __name__ == '__main__':
    path = get_package_path("woniunote")
    # 本地测试
    app.run(host="127.0.0.1",
            debug=True,
            port=5000,
            ssl_context=(path + "/configs/cert.pem", path + "/configs/key.pem"))
