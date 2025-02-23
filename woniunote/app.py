import os
from flask import Flask, redirect, render_template, session, request, url_for, jsonify
from flask_sslify import SSLify
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
app.config['SESSION_PERMANENT'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=1)
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


@app.route("/math_train", methods=["POST", "GET"])
def math_train():
    # file_path = os.path.join(package_path, 'template', 'math_train.html')
    file_path = "math_train.html"
    return render_template(file_path)


@app.route('/math_train_login', methods=['POST'])
def math_train_login():
    try:
        # 添加请求内容类型验证
        if not request.is_json:
            print("错误请求格式，收到内容类型:", request.content_type)
            return jsonify({'success': False, 'message': '请求必须为JSON格式'}), 400

        data = request.get_json()
        username = data.get('username')
        password = data.get('password')

        # 调试打印（生产环境应移除）
        print("[调试] 登录尝试 - 用户名:", username)
        print("[调试] 登录尝试 - 密码:", password)

        if not username or not password:
            print("缺少用户名或密码字段")
            return jsonify({'success': False, 'message': '用户名和密码不能为空'}), 400

        connection = get_db_connection(DATABASE_INFO)
        with connection.cursor() as cursor:
            # cursor.execute("SELECT * FROM math_train_users")
            # user_dict_test = cursor.fetchall()
            # print("math_train_test:", user_dict_test)
            cursor.execute("SELECT * FROM math_train_users WHERE username = %s", (username,))
            user_dict = cursor.fetchone()

            # 调试数据库查询结果
            print("[调试] 数据库查询结果:", user_dict)

            if not user_dict:
                print("用户不存在:", username)
                return jsonify({'success': False, 'message': '用户不存在'}), 401

            # 调试密码哈希对比
            print("[调试] 数据库存储的哈希:", user_dict['password'])
            print("[调试] 密码验证结果:", check_password_hash(user_dict['password'], password))

            if check_password_hash(user_dict['password'], password):
                session['username'] = username
                session['user_id'] = user_dict['id']
                print("登录成功，用户ID:", user_dict['id'])
                return jsonify({
                    'success': True,
                    'redirect': url_for('math_train_user'),  # 修正跳转地址
                    'username': username
                })
            else:
                print("密码验证失败")
                return jsonify({'success': False, 'message': '密码错误'}), 401

    except pymysql.Error as e:
        print("数据库错误:", str(e))
        return jsonify({'success': False, 'message': '数据库操作失败'}), 500
    except KeyError as e:
        print("字段缺失错误:", str(e))
        return jsonify({'success': False, 'message': '数据字段不完整'}), 400
    except Exception as e:
        print("服务器未知错误:", str(e))
        traceback.print_exc()  # 打印完整堆栈信息
        return jsonify({'success': False, 'message': '服务器内部错误'}), 500
    finally:
        if 'connection' in locals():
            connection.close()

@app.route('/math_train_register', methods=['POST'])
def math_train_register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    email = data.get('email')
    hashed_password = generate_password_hash(password)
    connection = get_db_connection(DATABASE_INFO)
    # 测试连接是否有效
    try:
        connection.ping(reconnect=True)  # 检查连接是否可用，若不可用则尝试重新连接
        print("数据库连接成功")
    except pymysql.MySQLError as e:
        print(f"数据库连接失败: {e}")
        return jsonify({'success': False, 'message': '数据库连接失败'})
    print("开始查询所有用户数据")
    # 执行查询所有用户数据
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM math_train_users")  # 查询所有数据
        users = cursor.fetchall()  # 获取所有记录
        print("数据库中的所有用户数据:")
        print(users)

    try:
        print("开始注册")
        print("DATABASE_INFO", DATABASE_INFO)
        print("username:", username)
        print("password:", password)
        with connection.cursor() as cursor:
            cursor.execute("INSERT INTO math_train_users (username, password, email) VALUES (%s, %s, %s)", (username, hashed_password, email))
            connection.commit()
            return jsonify({'success': True, 'message': '注册成功，请登录'})
    except pymysql.IntegrityError:  # 捕获唯一性约束错误
        connection.rollback()
        return jsonify({'success': False, 'message': '用户名已存在'})
    except Exception as e:
        connection.rollback()
        return jsonify({'success': False, 'message': '注册失败'})
    finally:
        connection.close()


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
    connection = get_db_connection(DATABASE_INFO)

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
# 退出路由
@app.route('/math_train_logout')
def math_train_logout():
    session.clear()  # 确保清除所有session数据
    return redirect(url_for('math_train'))

# 登录状态检查
@app.route('/math_train_check_login')
def math_train_check_login():
    return jsonify({
        'loggedIn': 'user_id' in session,
        'username': session.get('username', '')
    })


# 用户中心页面
@app.route("/math_train_user")
def math_train_user():
    if 'user_id' not in session:
        return redirect(url_for('math_train'))
    target_html = "math_train_user.html"
    return render_template(target_html)


# 获取用户训练数据
@app.route('/math_train_user_data')
def math_train_user_data():
    if 'user_id' not in session:
        return jsonify({'error': '未登录'}), 401

    connection = get_db_connection(DATABASE_INFO)
    try:
        with connection.cursor() as cursor:
            # 获取历史记录
            cursor.execute("""
                SELECT math_level, correct_count, total_questions, time_spent, created_at 
                FROM math_train_results 
                WHERE user_id = %s 
                ORDER BY created_at DESC 
                LIMIT 10
            """, (session['user_id'],))
            history = cursor.fetchall()

            # 获取统计数据
            cursor.execute("""
                SELECT 
                    COUNT(*) AS total_sessions,
                    ROUND(AVG(correct_count/total_questions)*100, 1) AS avg_accuracy,
                    MIN(time_spent) AS best_time
                FROM math_train_results 
                WHERE user_id = %s
            """, (session['user_id'],))
            stats = cursor.fetchone()

        return jsonify({
            'history': history,
            'total_sessions': stats['total_sessions'],
            'avg_accuracy': stats['avg_accuracy'] or 0,
            'best_time': f"{stats['best_time'] // 60:02d}:{stats['best_time'] % 60:02d}" if stats[
                'best_time'] else "00:00"
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        connection.close()

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
