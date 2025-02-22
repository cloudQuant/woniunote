import os
from flask import Flask, redirect, render_template, session, request, url_for, flash
from flask_sslify import SSLify
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
from woniunote.common.database import db, ARTICLE_TYPES
from woniunote.common.utils import read_config, get_package_path
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
# 提取用户名和密码
user_info = SQLALCHEMY_DATABASE_URI.split("://")[1].split("@")[0]
MYSQL_USER = user_info.split(":")[0]
MYSQL_PASSWORD = user_info.split(":")[1]
# 提取主机地址
MYSQL_HOST = SQLALCHEMY_DATABASE_URI.split("@")[1].split(":")[0]
MYSQL_DB = SQLALCHEMY_DATABASE_URI.split("@")[1].split("/")[0].split("?")[0]
# 初始化数据库连接
def get_db_connection():
    return pymysql.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DB,
        cursorclass=DictCursor
    )
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


@app.route("/math_train", methods=["POST", "GET"])
def math_train():
    # file_path = os.path.join(package_path, 'template', 'math_train.html')
    file_path = "math_train.html"
    return render_template(file_path)


@app.route('/math_train_login', methods=['GET', 'POST'])
def math_train_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # 使用 pymysql 连接数据库
        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM math_train_users WHERE username = %s", (username,))
                user = cursor.fetchone()

            if user and check_password_hash(user['password'], password):
                session['username'] = username
                session['user_id'] = user['id']
                return redirect(url_for('math_train'))
            else:
                flash('用户名或密码错误', 'error')
        finally:
            connection.close()

    target_html = "math_train_login.html"
    return render_template(target_html)


# 注册页面
@app.route('/math_train_register', methods=['GET', 'POST'])
def math_train_register():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])

        # 使用 pymysql 连接数据库
        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute("INSERT INTO math_train_users (username, password) VALUES (%s, %s)", (username, password))
                connection.commit()
                flash('注册成功，请登录', 'success')
                return redirect(url_for('login'))
        except pymysql.Error as e:
            connection.rollback()
            flash('用户名已存在', 'error')
        finally:
            connection.close()

    target_html = 'math_train_register.html'
    return render_template(target_html)


# 算术训练页面
# @app.route('/math_train')
# def math_train():
#     if 'username' not in session:
#         return redirect(url_for('math_train_login'))
#     return render_template('math_train.html')


# 保存训练结果
@app.route('/math_train_save_result', methods=['POST'])
def math_train_save_result():
    if 'username' not in session:
        return redirect(url_for('login'))

    data = request.json
    math_level = data['math_level']
    correct_count = data['correct_count']
    total_questions = data['total_questions']
    time_spent = data['time_spent']

    # 使用 pymysql 连接数据库
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO math_train_results (user_id, math_level, correct_count, total_questions, time_spent, created_at)
                VALUES (%s, %s, %s, %s, %s, NOW())
            """, (session['user_id'], math_level, correct_count, total_questions, time_spent))
            connection.commit()
        return {'status': 'success'}
    except pymysql.Error as e:
        connection.rollback()
        return {'status': 'error', 'message': str(e)}
    finally:
        connection.close()


# 退出登录
@app.route('/math_train_logout')
def math_train_logout():
    session.pop('username', None)
    session.pop('user_id', None)
    return redirect(url_for('login'))

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
