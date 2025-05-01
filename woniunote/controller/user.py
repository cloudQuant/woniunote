import hashlib
import re
import traceback
import uuid
from flask import Blueprint, make_response, session, request, url_for, jsonify
from woniunote.common.redisdb import redis_connect
from woniunote.common.utils import ImageCode, gen_email_code, send_email
from woniunote.module.credits import Credits
from woniunote.module.users import Users
from woniunote.common.simple_logger import get_simple_logger

user = Blueprint('user', __name__)

# 初始化日志记录器
user_logger = get_simple_logger('user_controller')

# 生成跟踪ID
def generate_user_trace_id():
    return str(uuid.uuid4())

# 获取当前跟踪ID
_user_thread_local_trace_id = {}
def get_user_trace_id():
    if 'trace_id' not in _user_thread_local_trace_id:
        _user_thread_local_trace_id['trace_id'] = generate_user_trace_id()
    return _user_thread_local_trace_id['trace_id']


@user.route('/vcode')
def vcode():
    # 生成跟踪ID
    trace_id = get_user_trace_id()
    
    # 记录请求验证码
    user_logger.info("请求图形验证码", {
        'trace_id': trace_id,
        'remote_addr': request.remote_addr,
        'user_agent': request.user_agent.string
    })
    
    try:
        code, b_string = ImageCode().get_code()
        response = make_response(b_string)
        response.headers['Content-Type'] = 'image/jpeg'
        session['vcode'] = code.lower()
        
        # 记录生成验证码成功
        user_logger.info("生成图形验证码成功", {
            'trace_id': trace_id
        })
        
        return response
    except Exception as e:
        # 记录错误
        user_logger.error("生成图形验证码失败", {
            'trace_id': trace_id,
            'error': str(e),
            'traceback': traceback.format_exc()
        })
        return jsonify({"error": "生成验证码失败"}), 500


@user.route('/ecode', methods=['POST'])
def ecode():
    # 生成跟踪ID
    trace_id = get_user_trace_id()
    
    # 记录请求邮箱验证码
    user_logger.info("请求邮箱验证码", {
        'trace_id': trace_id,
        'remote_addr': request.remote_addr,
        'user_agent': request.user_agent.string
    })
    
    try:
        email = request.form.get('email')
        
        # 记录邮箱信息
        user_logger.info("邮箱验证码请求信息", {
            'trace_id': trace_id,
            'email': email
        })
        
        if not re.match(r'.+@.+\..+', email):
            # 记录邮箱格式错误
            user_logger.warning("邮箱格式错误", {
                'trace_id': trace_id,
                'email': email
            })
            return 'email-invalid'

        code = gen_email_code()
        try:
            send_email(email, code)
            session['ecode'] = code  # 将邮箱验证码保存在Session中
            
            # 记录发送邮箱验证码成功
            user_logger.info("发送邮箱验证码成功", {
                'trace_id': trace_id,
                'email': email
            })
            
            return 'send-pass'
        except Exception as e:
            # 记录发送邮箱验证码失败
            user_logger.error("发送邮箱验证码失败", {
                'trace_id': trace_id,
                'email': email,
                'error': str(e),
                'traceback': traceback.format_exc()
            })
            return 'send-fail'
    except Exception as e:
        # 记录处理邮箱验证码请求失败
        user_logger.error("处理邮箱验证码请求失败", {
            'trace_id': trace_id,
            'error': str(e),
            'traceback': traceback.format_exc()
        })
        return 'send-fail'


@user.route('/user', methods=['POST'])
def register():
    # 生成跟踪ID
    trace_id = get_user_trace_id()
    
    # 记录用户注册请求
    user_logger.info("用户注册请求", {
        'trace_id': trace_id,
        'remote_addr': request.remote_addr,
        'user_agent': request.user_agent.string
    })
    
    try:
        user_instance = Users()
        username = request.form.get('username').strip()
        password = request.form.get('password').strip()
        ecode_ = request.form.get('ecode').strip()
        
        # 记录注册信息（不记录密码）
        user_logger.info("用户注册信息", {
            'trace_id': trace_id,
            'username': username,
            'password_length': len(password)
        })

        # 校验邮箱验证码是否正确
        if ecode_ != session.get('ecode'):
            # 记录验证码错误
            user_logger.warning("邮箱验证码错误", {
                'trace_id': trace_id,
                'username': username,
                'input_code': ecode_,
                'session_code': session.get('ecode')
            })
            return 'ecode-error'

        # 验证邮箱地址的正确性和密码的有效性
        elif not re.match(r'.+@.+\..+', username) or len(password) < 5:
            # 记录邮箱或密码格式错误
            user_logger.warning("邮箱或密码格式无效", {
                'trace_id': trace_id,
                'username': username,
                'email_valid': bool(re.match(r'.+@.+\..+', username)),
                'password_length': len(password)
            })
            return 'up-invalid'

        # 验证用户是否已经注册
        elif len(user_instance.find_by_username(username)) > 0:
            # 记录用户已存在
            user_logger.warning("用户已存在", {
                'trace_id': trace_id,
                'username': username
            })
            return 'user-repeated'

        else:
            # 实现注册功能
            password = hashlib.md5(password.encode()).hexdigest()
            result = user_instance.do_register(username, password)
            
            # 记录注册成功
            user_logger.info("用户注册成功", {
                'trace_id': trace_id,
                'username': username,
                'userid': result.userid,
                'nickname': result.nickname,
                'role': result.role
            })
            
            session['islogin'] = 'true'
            session['userid'] = result.userid
            session['username'] = username
            session['nickname'] = result.nickname
            session['role'] = result.role
            
            # 更新积分详情表
            Credits().insert_detail(credit_type='用户注册', target='0', credit=50)
            
            # 记录积分更新
            user_logger.info("用户注册积分更新", {
                'trace_id': trace_id,
                'username': username,
                'userid': result.userid,
                'credit_type': '用户注册',
                'credit': 50
            })
            
            return 'reg-pass'
    except Exception as e:
        # 记录注册异常
        user_logger.error("用户注册异常", {
            'trace_id': trace_id,
            'error': str(e),
            'traceback': traceback.format_exc()
        })
        return 'reg-error'


@user.route('/login', methods=['POST'])
def login():
    # 生成跟踪ID
    trace_id = get_user_trace_id()
    
    # 记录登录请求
    user_logger.info("用户登录请求", {
        'trace_id': trace_id,
        'remote_addr': request.remote_addr,
        'user_agent': request.user_agent.string
    })
    
    try:
        # 接收前端传递的参数
        username = request.form.get('username')
        password = request.form.get('password')
        vcode = request.form.get('vcode')
        
        # 记录登录尝试（不记录密码）
        user_logger.info("登录尝试", {
            'trace_id': trace_id,
            'username': username,
            'has_password': bool(password),
            'has_vcode': bool(vcode)
        })

        # 验证码验证
        if session.get('vcode') != vcode:
            # 记录验证码错误
            user_logger.warning("验证码错误", {
                'trace_id': trace_id,
                'username': username,
                'input_vcode': vcode,
                'session_vcode': session.get('vcode')
            })
            return 'vcode-error'

        # 查询数据库，验证用户名和密码是否正确
        user_ = Users()
        result = user_.find_by_username(username)
        
        # 记录数据库查询结果
        user_logger.info("用户数据库查询结果", {
            'trace_id': trace_id,
            'username': username,
            'user_found': len(result) > 0
        })

        if len(result) > 0:
            password = hashlib.md5(password.encode()).hexdigest()
            if result[0].password == password:
                # 记录登录成功
                session_id = str(uuid.uuid4())
                user_logger.info("登录成功", {
                    'trace_id': trace_id,
                    'username': username,
                    'userid': result[0].userid,
                    'nickname': result[0].nickname,
                    'role': result[0].role,
                    'session_id': session_id
                })
                
                # 设置session
                session['main_session_id'] = session_id
                session['main_islogin'] = 'true'
                session['main_userid'] = result[0].userid
                session['main_username'] = username
                session['main_nickname'] = result[0].nickname
                session['main_role'] = result[0].role
                return 'login-pass'
            else:
                # 记录密码错误
                user_logger.warning("密码错误", {
                    'trace_id': trace_id,
                    'username': username
                })
        
        # 记录登录失败
        user_logger.warning("登录失败", {
            'trace_id': trace_id,
            'username': username,
            'reason': 'user_not_found' if len(result) == 0 else 'wrong_password'
        })
        return 'login-fail'
    except Exception as e:
        # 记录登录异常
        user_logger.error("登录异常", {
            'trace_id': trace_id,
            'error': str(e),
            'traceback': traceback.format_exc()
        })
        return 'login-fail'


@user.route('/logout', methods=['GET', 'POST'])
def logout():
    # 生成跟踪ID
    trace_id = get_user_trace_id()
    
    # 记录登出请求
    user_logger.info("用户登出请求", {
        'trace_id': trace_id,
        'remote_addr': request.remote_addr,
        'user_agent': request.user_agent.string,
        'method': request.method
    })
    
    try:
        # 记录登出前的会话信息
        user_info = {
            'userid': session.get('main_userid'),
            'username': session.get('main_username'),
            'nickname': session.get('main_nickname'),
            'role': session.get('main_role'),
            'session_id': session.get('main_session_id')
        }
        
        user_logger.info("登出前的会话信息", {
            'trace_id': trace_id,
            'user_info': user_info,
            'is_logged_in': session.get('main_islogin') == 'true'
        })
        
        # 清除主系统的session
        session.pop('main_session_id', None)
        session.pop('main_islogin', None)
        session.pop('main_userid', None)
        session.pop('main_username', None)
        session.pop('main_nickname', None)
        session.pop('main_role', None)
        
        # 确保 session 被修改
        session.modified = True
        
        # 记录登出成功
        user_logger.info("用户登出成功", {
            'trace_id': trace_id,
            'previous_user_info': user_info
        })
        
        return jsonify({'success': True})
    except Exception as e:
        # 记录登出异常
        user_logger.error("用户登出异常", {
            'trace_id': trace_id,
            'error': str(e),
            'traceback': traceback.format_exc()
        })
        return jsonify({'success': False, 'message': str(e)})


@user.route('/loginfo')
def loginfo():
    # 生成跟踪ID
    trace_id = get_user_trace_id()
    
    # 记录查询登录信息请求
    user_logger.info("查询登录信息请求", {
        'trace_id': trace_id,
        'remote_addr': request.remote_addr,
        'user_agent': request.user_agent.string
    })
    
    try:
        if session.get('main_islogin') == 'true':
            user_info = {
                'userid': session.get('main_userid'),
                'username': session.get('main_username'),
                'nickname': session.get('main_nickname'),
                'role': session.get('main_role')
            }
            
            # 记录已登录用户信息
            user_logger.info("用户已登录", {
                'trace_id': trace_id,
                'user_info': user_info
            })
            
            return jsonify(user_info)
        
        # 记录用户未登录
        user_logger.info("用户未登录", {
            'trace_id': trace_id
        })
        
        return jsonify(None)
    except Exception as e:
        # 记录查询登录信息异常
        user_logger.error("查询登录信息异常", {
            'trace_id': trace_id,
            'error': str(e),
            'traceback': traceback.format_exc()
        })
        return jsonify(None)


# 用户注册时生成邮箱验证码并保存到缓存中
@user.route('/redis/code', methods=['POST'])
def redis_code():
    # 生成跟踪ID
    trace_id = get_user_trace_id()
    
    # 记录Redis验证码请求
    user_logger.info("Redis验证码请求", {
        'trace_id': trace_id,
        'remote_addr': request.remote_addr,
        'user_agent': request.user_agent.string
    })
    
    try:
        username = request.form.get('username').strip()
        
        # 记录用户名信息
        user_logger.info("Redis验证码用户信息", {
            'trace_id': trace_id,
            'username': username
        })
        
        code = gen_email_code()
        red = redis_connect()  # 连接到Redis服务器
        red.set(username, code)
        red.expire(username, 30)  # 设置username变量的有效期为30秒
        
        # 记录Redis操作成功
        user_logger.info("Redis验证码设置成功", {
            'trace_id': trace_id,
            'username': username,
            'expire_seconds': 30
        })
        
        # 设置好缓存变量的过期时间后，发送邮件完成处理，此处代码略
        return 'done'
    except Exception as e:
        # 记录Redis操作异常
        user_logger.error("Redis验证码设置异常", {
            'trace_id': trace_id,
            'error': str(e),
            'traceback': traceback.format_exc()
        })
        return 'error'


# 根据用户的注册邮箱去缓存中查找验证码进行验证
@user.route('/redis/reg', methods=['POST'])
def redis_reg():
    # 生成跟踪ID
    trace_id = get_user_trace_id()
    
    # 记录Redis验证注册请求
    user_logger.info("Redis验证注册请求", {
        'trace_id': trace_id,
        'remote_addr': request.remote_addr,
        'user_agent': request.user_agent.string
    })
    
    try:
        username = request.form.get('username').strip()
        _password = request.form.get('password').strip()
        ecode_ = request.form.get('ecode').lower().strip()
        
        # 记录注册信息（不记录密码）
        user_logger.info("Redis验证注册信息", {
            'trace_id': trace_id,
            'username': username,
            'password_length': len(_password),
            'ecode_length': len(ecode_)
        })
        
        try:
            red = redis_connect()  # 连接到Redis服务器
            code = red.get(username).lower()
            
            # 记录Redis获取验证码成功
            user_logger.info("Redis获取验证码成功", {
                'trace_id': trace_id,
                'username': username,
                'code_match': code == ecode_
            })
            
            if code == ecode_:
                # 记录验证码正确
                user_logger.info("Redis验证码验证成功", {
                    'trace_id': trace_id,
                    'username': username
                })
                return '验证码正确.'
                # 开始进行注册，此处代码略
            else:
                # 记录验证码错误
                user_logger.warning("Redis验证码错误", {
                    'trace_id': trace_id,
                    'username': username,
                    'input_code': ecode_,
                    'stored_code': code
                })
                return '验证码错误.'
        except Exception as e:
            # 记录Redis获取验证码异常
            user_logger.error("Redis获取验证码异常", {
                'trace_id': trace_id,
                'username': username,
                'error': str(e),
                'traceback': traceback.format_exc()
            })
            return '验证码已经失效.'
    except Exception as e:
        # 记录注册异常
        user_logger.error("Redis验证注册异常", {
            'trace_id': trace_id,
            'error': str(e),
            'traceback': traceback.format_exc()
        })
        return '系统异常，请稍后再试.'


@user.route('/redis/login', methods=['POST'])
def redis_login():
    # 生成跟踪ID
    trace_id = get_user_trace_id()
    
    # 记录Redis登录请求
    user_logger.info("Redis登录请求", {
        'trace_id': trace_id,
        'remote_addr': request.remote_addr,
        'user_agent': request.user_agent.string
    })
    
    try:
        red = redis_connect()
        # 通过取值判断用户名的key是否存在
        username = request.form.get('username').strip()
        password = request.form.get('password').strip()
        
        # 记录登录尝试（不记录密码）
        user_logger.info("Redis登录尝试", {
            'trace_id': trace_id,
            'username': username,
            'has_password': bool(password)
        })
        
        password = hashlib.md5(password.encode()).hexdigest()

        try:
            result = red.hget('users_hash', username)
            
            # 记录Redis查询结果
            user_logger.info("Redis用户查询结果", {
                'trace_id': trace_id,
                'username': username,
                'user_found': bool(result)
            })
            
            if not result:
                # 记录用户不存在
                user_logger.warning("Redis用户不存在", {
                    'trace_id': trace_id,
                    'username': username
                })
                return '用户名不存在'
            
            user_result = eval(result)
            if password == user_result['password']:
                # 记录登录成功
                user_logger.info("Redis登录成功", {
                    'trace_id': trace_id,
                    'username': username
                })
                return '登录成功'
            else:
                # 记录密码错误
                user_logger.warning("Redis密码错误", {
                    'trace_id': trace_id,
                    'username': username
                })
                return '密码错误'
        except Exception as e:
            # 记录Redis查询异常
            user_logger.error("Redis用户查询异常", {
                'trace_id': trace_id,
                'username': username,
                'error': str(e),
                'traceback': traceback.format_exc()
            })
            return '用户名不存在'
    except Exception as e:
        # 记录Redis登录异常
        user_logger.error("Redis登录异常", {
            'trace_id': trace_id,
            'error': str(e),
            'traceback': traceback.format_exc()
        })
        return '系统异常，请稍后再试'
