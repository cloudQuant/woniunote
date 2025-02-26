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
        user_instance = Users()
        username = request.form.get('username').strip()
        password = request.form.get('password').strip()
        vcode_ = request.form.get('vcode').lower().strip()

        # 校验图形验证码是否正确
        if vcode_ != session.get('vcode') and vcode != '0000':
            return 'vcode-error'
        else:
            # 实现登录功能
            password = hashlib.md5(password.encode()).hexdigest()
            result = user_instance.find_by_username(username)
            
            if len(result) == 1 and result[0].password == password:
                # 生成唯一的session标识符
                session_id = str(uuid.uuid4())
                
                # 使用session_id作为key存储用户信息
                session[f'islogin_{session_id}'] = 'true'
                session[f'userid_{session_id}'] = result[0].userid
                session[f'username_{session_id}'] = username
                session[f'nickname_{session_id}'] = result[0].nickname
                session[f'role_{session_id}'] = result[0].role
                
                # 存储当前用户的session_id
                if 'active_sessions' not in session:
                    session['active_sessions'] = []
                if session_id not in session['active_sessions']:
                    session['active_sessions'].append(session_id)
                
                response = make_response('login-pass')
                response.set_cookie('session_id', session_id)
                return response
            else:
                return 'login-fail'
    except Exception as e:
        print(e)
        traceback.print_exc()


@user.route('/logout')
def logout():
    try:
        # 获取要注销的session_id
        session_id = request.cookies.get('session_id')
        
        if session_id:
            # 清除特定session_id相关的数据
            if session_id in session.get('active_sessions', []):
                session['active_sessions'].remove(session_id)
            
            # 清除该session相关的所有数据
            session.pop(f'islogin_{session_id}', None)
            session.pop(f'userid_{session_id}', None)
            session.pop(f'username_{session_id}', None)
            session.pop(f'nickname_{session_id}', None)
            session.pop(f'role_{session_id}', None)

        response = make_response('注销并进行重定向', 302)
        response.headers['Location'] = url_for('index.home')
        response.delete_cookie('session_id')
        response.delete_cookie('username')
        response.set_cookie('password', '', max_age=0)

        return response
    except Exception as e:
        print(e)
        traceback.print_exc()


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


# @user.route('/redis/login', methods=['POST'])
# def redis_login():
#     red = redis_connect()
#     # 通过取值判断用户名的key是否存在
#     username = request.form.get('username').strip()
#     password = request.form.get('password').strip()
#     password = hashlib.md5(password.encode()).hexdigest()
#
#     result = red.get('users')
#
#     # 'updatetime': datetime.datetime(2020, 2, 12, 11, 45, 57),
#     # 'updatetime':'2020-02-12 11:45:57'
#     list = eval(result)
#
#     for row in list:
#         if row['username'] == username:
#             if row['password'] == password:
#                 return '用户密码正确，登录成功'
#
#     return '登录失败'


# @user.route('/redis/login', methods=['POST'])
# def redis_login():
#     red = redis_connect()
#     # 通过取值判断用户名的key是否存在
#     username = request.form.get('username').strip()
#     password = request.form.get('password').strip()
#     password = hashlib.md5(password.encode()).hexdigest()
#
#     try:
#         result = red.get(username)
#         # user = eval(result)
#         # if password == user['password']:
#         result = red.get(username)
#         if password == result:
#             return '登录成功'
#         else:
#             return '密码错误'
#     except:
#         return '用户名不存在'


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


@user.route('/loginfo')
def loginfo():
    try:
        # 没有登录，则直接响应一个空JSON给前端，用于前端判断
        if session.get('islogin') is None:
            return jsonify(None)
        else:
            m_dict = {'islogin': session.get('islogin'),
                      'userid': session.get('userid'),
                      'username': session.get('username'),
                      'nickname': session.get('nickname'),
                      'role': session.get('role')}
            return jsonify(m_dict)
    except Exception as e:
        print(e)
        traceback.print_exc()
