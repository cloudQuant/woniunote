import hashlib
import re

from flask import Blueprint, make_response, session, request, url_for, jsonify
from woniunote.common.redisdb import redis_connect
from woniunote.common.utils import ImageCode, gen_email_code, send_email
from woniunote.module.credits import Credits
from woniunote.module.users import Users

user = Blueprint('user', __name__)


@user.route('/vcode')
def vcode():
    code, bstring = ImageCode().get_code()
    response = make_response(bstring)
    response.headers['Content-Type'] = 'image/jpeg'
    session['vcode'] = code.lower()
    return response


@user.route('/ecode', methods=['POST'])
def ecode():
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


@user.route('/user', methods=['POST'])
def register():
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


@user.route('/login', methods=['POST'])
def login():
    user_instance = Users()
    username = request.form.get('username').strip()
    password = request.form.get('password').strip()
    vcode_ = request.form.get('vcode').lower().strip()
    # print(username,password,vcode)
    # 校验图形验证码是否正确
    if vcode_ != session.get('vcode') and vcode != '0000':
        return 'vcode-error'

    else:
        # 实现登录功能
        password = hashlib.md5(password.encode()).hexdigest()
        result = user_instance.find_by_username(username)
        # print(result,result[0])
        if len(result) == 1 and result[0].password == password:
            session['islogin'] = 'true'
            session['userid'] = result[0].userid
            session['username'] = username
            session['nickname'] = result[0].nickname
            session['role'] = result[0].role
            # 更新积分详情表
            Credits().insert_detail(credit_type='正常登录', target='0', credit=1)
            user_instance.update_credit(1)
            # 将Cookie写入浏览器
            response = make_response('login-pass')
            response.set_cookie('username', username, max_age=30 * 24 * 3600)
            response.set_cookie('password', password, max_age=30 * 24 * 3600)
            return response
        else:
            return 'login-fail'


@user.route('/logout')
def logout():
    # 清空Session，页面跳转
    session.clear()

    response = make_response('注销并进行重定向', 302)
    response.headers['Location'] = url_for('index.home')
    response.delete_cookie('username')
    response.set_cookie('password', '', max_age=0)

    return response


# 用户注册时生成邮箱验证码并保存到缓存中
@user.route('/redis/code', methods=['POST'])
def redis_code():
    username = request.form.get('username').strip()
    code = gen_email_code()
    red = redis_connect()  # 连接到Redis服务器
    red.set(username, code)
    red.expire(username, 30)  # 设置username变量的有效期为30秒
    # 设置好缓存变量的过期时间后，发送邮件完成处理，此处代码略
    return 'done'


# 根据用户的注册邮箱去缓存中查找验证码进行验证
@user.route('/redis/reg', methods=['POST'])
def redis_reg():
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


@user.route('/loginfo')
def loginfo():
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