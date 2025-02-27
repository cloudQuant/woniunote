import hashlib
import re
import traceback
import uuid
from flask import Blueprint, make_response, session, request, url_for, jsonify
from woniunote.common.redisdb import redis_connect
from woniunote.common.utils import ImageCode, gen_email_code, send_email
from woniunote.module.credits import Credits
from woniunote.module.users import Users

user = Blueprint('user', __name__)


@user.route('/vcode')
def vcode():
    try:
        code, b_string = ImageCode().get_code()
        response = make_response(b_string)
        response.headers['Content-Type'] = 'image/jpeg'
        session['vcode'] = code.lower()
        return response
    except Exception as e:
        print(e)
        traceback.print_exc()


@user.route('/ecode', methods=['POST'])
def ecode():
    try:
        email = request.form.get('email')
        if not re.match(r'.+@.+\..+', email):
            return 'email-invalid'

        code = gen_email_code()
        try:
            send_email(email, code)
            session['ecode'] = code  # 将邮箱验证码保存在Session中
            return 'send-pass'
        except Exception as e:
            print('ecode', e)
            return 'send-fail'
    except Exception as e:
        print(e)
        traceback.print_exc()


@user.route('/user', methods=['POST'])
def register():
    try:
        user_instance = Users()
        username = request.form.get('username').strip()
        password = request.form.get('password').strip()
        ecode_ = request.form.get('ecode').strip()

        # 校验邮箱验证码是否正确
        if ecode_ != session.get('ecode'):
            return 'ecode-error'

        # 验证邮箱地址的正确性和密码的有效性
        elif not re.match(r'.+@.+\..+', username) or len(password) < 5:
            return 'up-invalid'

        # 验证用户是否已经注册
        elif len(user_instance.find_by_username(username)) > 0:
            return 'user-repeated'

        else:
            # 实现注册功能
            password = hashlib.md5(password.encode()).hexdigest()
            result = user_instance.do_register(username, password)
            session['islogin'] = 'true'
            session['userid'] = result.userid
            session['username'] = username
            session['nickname'] = result.nickname
            session['role'] = result.role
            # 更新积分详情表
            Credits().insert_detail(credit_type='用户注册', target='0', credit=50)
            return 'reg-pass'
    except Exception as e:
        print(e)
        traceback.print_exc()


@user.route('/login', methods=['POST'])
def login():
    try:
        # 接收前端传递的参数
        username = request.form.get('username')
        password = request.form.get('password')
        vcode = request.form.get('vcode')
        print("Login attempt - username:", username)

        # 验证码验证
        if session.get('vcode') != vcode:
            print("Invalid vcode")
            return 'vcode-error'

        # 查询数据库，验证用户名和密码是否正确
        user_ = Users()
        result = user_.find_by_username(username)
        print("Database query result:", result)

        if len(result) > 0:
            password = hashlib.md5(password.encode()).hexdigest()
            if result[0].password == password:
                print("Login successful")
                session_id = str(uuid.uuid4())
                session['main_session_id'] = session_id
                session['main_islogin'] = 'true'
                session['main_userid'] = result[0].userid
                session['main_username'] = username
                session['main_nickname'] = result[0].nickname
                session['main_role'] = result[0].role
                return 'login-pass'
        print("Login failed")
        return 'login-fail'
    except Exception as e:
        print("Login error:", e)
        traceback.print_exc()
        return 'login-fail'


@user.route('/logout', methods=['GET', 'POST'])
def logout():
    try:
        print("Logout request received")
        print("Session before logout:", dict(session))
        
        # 清除主系统的session
        session.pop('main_session_id', None)
        session.pop('main_islogin', None)
        session.pop('main_userid', None)
        session.pop('main_username', None)
        session.pop('main_nickname', None)
        session.pop('main_role', None)
        
        # 确保session被修改
        session.modified = True
        
        print("Session after logout:", dict(session))
        return jsonify({'success': True})
    except Exception as e:
        print("Logout error:", e)
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)})


@user.route('/loginfo')
def loginfo():
    try:
        if session.get('main_islogin') == 'true':
            print("User is logged in")
            user_info = {
                'userid': session.get('main_userid'),
                'username': session.get('main_username'),
                'nickname': session.get('main_nickname'),
                'role': session.get('main_role')
            }
            print("User info:", user_info)
            return jsonify(user_info)
        print("User is not logged in")
        return jsonify(None)
    except Exception as e:
        print("Loginfo error:", e)
        traceback.print_exc()
        return jsonify(None)


# 用户注册时生成邮箱验证码并保存到缓存中
@user.route('/redis/code', methods=['POST'])
def redis_code():
    try:
        username = request.form.get('username').strip()
        code = gen_email_code()
        red = redis_connect()  # 连接到Redis服务器
        red.set(username, code)
        red.expire(username, 30)  # 设置username变量的有效期为30秒
        # 设置好缓存变量的过期时间后，发送邮件完成处理，此处代码略
        return 'done'
    except Exception as e:
        print(e)
        traceback.print_exc()


# 根据用户的注册邮箱去缓存中查找验证码进行验证
@user.route('/redis/reg', methods=['POST'])
def redis_reg():
    try:
        username = request.form.get('username').strip()
        _password = request.form.get('password').strip()
        ecode_ = request.form.get('ecode').lower().strip()
        try:
            red = redis_connect()  # 连接到Redis服务器
            code = red.get(username).lower()
            if code == ecode_:
                return '验证码正确.'
                # 开始进行注册，此处代码略
            else:
                return '验证码错误.'
        except Exception as e:
            print('redis_reg', e)
            return '验证码已经失效.'
    except Exception as e:
        print(e)
        traceback.print_exc()


@user.route('/redis/login', methods=['POST'])
def redis_login():
    try:
        red = redis_connect()
        # 通过取值判断用户名的key是否存在
        username = request.form.get('username').strip()
        password = request.form.get('password').strip()
        password = hashlib.md5(password.encode()).hexdigest()

        try:
            result = red.hget('users_hash', username)
            user_result = eval(result)
            if password == user_result['password']:
                return '登录成功'
            else:
                return '密码错误'
        except Exception as e:
            print('redis_login', e)
            return '用户名不存在'
    except Exception as e:
        print(e)
        traceback.print_exc()
