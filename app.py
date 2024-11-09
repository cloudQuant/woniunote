import os
from flask import Flask, redirect, render_template, session, request
from flask_sslify import SSLify
from woniunote.common.database import db, ARTICLE_TYPES
from woniunote.utils import read_config, get_package_path
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
import pymysql
pymysql.install_as_MySQLdb()


config_result = read_config()
SQLALCHEMY_DATABASE_URI = config_result['database']["SQLALCHEMY_DATABASE_URI"]
app = Flask(__name__, template_folder='template',
            static_url_path='/', static_folder='resource')
app.config['SECRET_KEY'] = os.urandom(24)

# 使用集成方式处理SQLAlchemy
app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # True: 跟踪数据库的修改，及时发送信号
app.config['SQLALCHEMY_POOL_SIZE'] = 100  # 数据库连接池的大小。默认是数据库引擎的默认值（通常是 5）
# app.config['SQLALCHEMY_POOL_RECYCLE'] = -1
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


# 定义404错误页面
@app.errorhandler(404)
def page_not_found(e):
    print(e)
    return render_template('error-404.html')


# 定义500错误页面
@app.errorhandler(500)
def server_error(e):
    print(e)
    return render_template('error-500.html')


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
            user = Users()
            result = user.find_by_username(username)
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
    return dict(article_type=ARTICLE_TYPES)


# app.jinja_env.globals.update(my_article_type=get_type)
@app.route('/preupload')
def pre_upload():
    return render_template('file-upload.html')


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
    return render_template("math_train.html")


if __name__ == '__main__':
    path = get_package_path("woniunote")
    app.run(host="127.0.0.1", debug=False, ssl_context=(path+"/cert.pem", path+"/key.pem"))
    # app.run(host="127.0.0.1", debug=True)
