### 3.3 安全性增强

#### 3.3.1 密码存储升级

**问题**：当前系统使用简单的MD5哈希存储密码，存在严重安全隐患。

**解决方案**：

1. **使用现代密码哈希算法**：
   ```python
   from werkzeug.security import generate_password_hash, check_password_hash

   class User(BaseModel):
       # ...其他字段
       _password = Column('password', String(128), nullable=False)
       
       @property
       def password(self):
           """密码属性，不允许直接读取"""
           raise AttributeError('密码不可读')
           
       @password.setter
       def password(self, password):
           """设置密码，使用werkzeug提供的安全哈希函数"""
           self._password = generate_password_hash(password, method='pbkdf2:sha256:50000')
           
       def check_password(self, password):
           """验证密码"""
           return check_password_hash(self._password, password)
   ```

2. **密码重置流程改进**：
   ```python
   def generate_reset_token(user_id, expiration=3600):
       """生成密码重置令牌"""
       s = Serializer(current_app.config['SECRET_KEY'], expiration)
       return s.dumps({'user_id': user_id}).decode('utf-8')
       
   def verify_reset_token(token):
       """验证密码重置令牌"""
       s = Serializer(current_app.config['SECRET_KEY'])
       try:
           data = s.loads(token.encode('utf-8'))
       except:
           return None
       return UserRepository().get_by_id(data.get('user_id'))
   ```

3. **密码策略强化**：
   ```python
   def validate_password_strength(password):
       """验证密码强度"""
       if len(password) < 8:
           return False, "密码长度至少为8个字符"
           
       if not re.search(r'[A-Z]', password):
           return False, "密码必须包含至少一个大写字母"
           
       if not re.search(r'[a-z]', password):
           return False, "密码必须包含至少一个小写字母"
           
       if not re.search(r'[0-9]', password):
           return False, "密码必须包含至少一个数字"
           
       if not re.search(r'[!@#$%^&*]', password):
           return False, "密码必须包含至少一个特殊字符(!@#$%^&*)"
           
       return True, "密码强度合格"
   ```

4. **实施密码历史记录**：
   ```python
   class PasswordHistory(BaseModel):
       """密码历史记录"""
       __tablename__ = 'password_history'
       
       id = Column(Integer, primary_key=True)
       user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
       password_hash = Column(String(128), nullable=False)
       created_at = Column(DateTime, default=datetime.utcnow)
       
       user = relationship('User', back_populates='password_history')
       
   User.password_history = relationship('PasswordHistory', 
                                      back_populates='user',
                                      order_by='desc(PasswordHistory.created_at)',
                                      cascade='all, delete-orphan')
   ```

#### 3.3.2 CSRF保护

**问题**：系统缺乏全面的CSRF保护机制。

**解决方案**：

1. **启用Flask-WTF的CSRF保护**：
   ```python
   from flask_wtf.csrf import CSRFProtect

   csrf = CSRFProtect()

   def create_app():
       app = Flask(__name__)
       # ...其他配置
       
       # 启用CSRF保护
       csrf.init_app(app)
       
       return app
   ```

2. **在表单中添加CSRF令牌**：
   ```html
   <form method="post" action="/login">
       <input type="hidden" name="csrf_token" value="{{ csrf_token() }}"/>
       <!-- 其他表单字段 -->
   </form>
   ```

3. **处理AJAX请求的CSRF保护**：
   ```javascript
   // 前端JavaScript代码
   $.ajaxSetup({
       beforeSend: function(xhr, settings) {
           if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type) && !this.crossDomain) {
               xhr.setRequestHeader("X-CSRFToken", "{{ csrf_token() }}");
           }
       }
   });
   ```

4. **在API请求中豁免CSRF保护**：
   ```python
   @app.route('/api/v1/webhook', methods=['POST'])
   @csrf.exempt
   def webhook():
       """处理第三方webhook，豁免CSRF保护"""
       # ...处理逻辑
   ```

#### 3.3.3 输入验证与XSS防护

**问题**：系统缺乏统一的输入验证和XSS防护机制。

**解决方案**：

1. **使用表单验证**：
   ```python
   from flask_wtf import FlaskForm
   from wtforms import StringField, TextAreaField, SelectField
   from wtforms.validators import DataRequired, Length, Email

   class ArticleForm(FlaskForm):
       """文章表单"""
       title = StringField('标题', validators=[
           DataRequired('标题不能为空'),
           Length(min=5, max=100, message='标题长度须在5-100字符之间')
       ])
       content = TextAreaField('内容', validators=[
           DataRequired('内容不能为空')
       ])
       type = SelectField('分类', coerce=int, validators=[
           DataRequired('请选择分类')
       ])
       
       def __init__(self, *args, **kwargs):
           super(ArticleForm, self).__init__(*args, **kwargs)
           # 动态加载分类选项
           self.type.choices = [(t.id, t.name) for t in ArticleTypeRepository().get_all()]
   ```

2. **HTML内容安全处理**：
   ```python
   import bleach
   
   def sanitize_html(content):
       """清理HTML内容，防止XSS攻击"""
       allowed_tags = ['a', 'abbr', 'acronym', 'b', 'blockquote', 'code',
                      'em', 'i', 'li', 'ol', 'pre', 'strong', 'ul',
                      'h1', 'h2', 'h3', 'p', 'img']
       allowed_attrs = {
           '*': ['class'],
           'a': ['href', 'rel', 'target'],
           'img': ['src', 'alt', 'width', 'height'],
       }
       
       cleaned = bleach.clean(
           content,
           tags=allowed_tags,
           attributes=allowed_attrs,
           strip=True
       )
       
       return cleaned
   ```

3. **富文本编辑器安全配置**：
   ```javascript
   // UEditor 安全配置
   var ueditorConfig = {
       // 允许的标签
       allowDivTransToP: true,
       // 过滤粘贴内容
       pasteplain: false,
       // 禁用不安全的标签和属性
       filterTxtRules: {
           'script': {'$': {}}  // 移除所有script标签
       },
       // 设置只允许上传图片
       imageActionName: "uploadimage",
       imageFieldName: "upfile",
       imageAllowFiles: [".png", ".jpg", ".jpeg", ".gif"],
       // 禁用浏览服务器文件功能
       enableImageManager: false
   };
   ```

4. **API参数验证**：
   ```python
   from marshmallow import Schema, fields, ValidationError

   class CommentSchema(Schema):
       """评论数据验证模式"""
       article_id = fields.Integer(required=True)
       content = fields.String(required=True)
       parent_id = fields.Integer(required=False, allow_none=True)
       
   @comment.route('/add', methods=['POST'])
   @login_required
   def add_comment():
       """添加评论"""
       try:
           # 验证请求数据
           schema = CommentSchema()
           comment_data = schema.load(request.json)
           
           # ...处理逻辑
       except ValidationError as e:
           return jsonify({'success': False, 'errors': e.messages}), 400
   ```

#### 3.3.4 会话安全性增强

**问题**：会话管理不安全，易受会话劫持和固定攻击。

**解决方案**：

1. **提高会话安全性**：
   ```python
   # 配置安全的会话设置
   app.config.update({
       'SESSION_COOKIE_HTTPONLY': True,  # 防止JavaScript访问
       'SESSION_COOKIE_SECURE': True,    # 仅通过HTTPS发送
       'SESSION_COOKIE_SAMESITE': 'Lax', # 防止CSRF
       'PERMANENT_SESSION_LIFETIME': timedelta(days=7),  # 会话过期时间
       'SESSION_USE_SIGNER': True,       # 对会话数据进行签名
   })
   ```

2. **会话保护机制**：
   ```python
   def verify_session():
       """验证会话安全性"""
       user_agent = request.headers.get('User-Agent', '')
       session_agent = session.get('_ua')
       
       # 第一次访问，记录User-Agent
       if not session_agent:
           session['_ua'] = user_agent
           return True
           
       # 检查User-Agent是否变化
       if session_agent != user_agent:
           # 可能是会话被劫持
           session.clear()
           return False
           
       return True
   ```

3. **登录状态改变时重新生成会话ID**：
   ```python
   @user.route('/login', methods=['POST'])
   def login():
       """用户登录"""
       # ...验证用户凭据
       
       # 登录成功后重新生成会话ID，防止会话固定攻击
       session.regenerate()  # 假设Flask-Session扩展提供此功能
       
       # 设置会话数据
       session['main_islogin'] = 'true'
       session['main_userid'] = user.userid
       session['main_username'] = user.username
       # ...其他会话数据
       
       return jsonify({'success': True})
   ```

#### 3.3.5 权限系统重构

**问题**：当前权限检查分散且不一致。

**解决方案**：

1. **实现基于角色的访问控制(RBAC)**：
   ```python
   class Role(BaseModel):
       """角色模型"""
       __tablename__ = 'role'
       
       id = Column(Integer, primary_key=True)
       name = Column(String(50), unique=True)
       description = Column(String(255))
       
       permissions = relationship('Permission', 
                                secondary='role_permission', 
                                back_populates='roles')
                                
   class Permission(BaseModel):
       """权限模型"""
       __tablename__ = 'permission'
       
       id = Column(Integer, primary_key=True)
       code = Column(String(50), unique=True)
       name = Column(String(50))
       description = Column(String(255))
       
       roles = relationship('Role', 
                          secondary='role_permission', 
                          back_populates='permissions')
                          
   class RolePermission(BaseModel):
       """角色权限关联"""
       __tablename__ = 'role_permission'
       
       role_id = Column(Integer, ForeignKey('role.id'), primary_key=True)
       permission_id = Column(Integer, ForeignKey('permission.id'), primary_key=True)
   ```

2. **权限检查装饰器**：
   ```python
   def permission_required(permission_code):
       """检查用户是否具有指定权限"""
       def decorator(f):
           @wraps(f)
           def decorated_function(*args, **kwargs):
               if not current_user.is_authenticated:
                   return redirect(url_for('user.login'))
                   
               if not current_user.has_permission(permission_code):
                   abort(403)
                   
               return f(*args, **kwargs)
           return decorated_function
       return decorator
   ```

3. **用户权限检查方法**：
   ```python
   class User(BaseModel):
       # ...其他字段和方法
       
       roles = relationship('Role', secondary='user_role', back_populates='users')
       
       def has_role(self, role_name):
           """检查用户是否具有指定角色"""
           return any(role.name == role_name for role in self.roles)
           
       def has_permission(self, permission_code):
           """检查用户是否具有指定权限"""
           for role in self.roles:
               for permission in role.permissions:
                   if permission.code == permission_code:
                       return True
           return False
   ```

4. **权限模板助手**：
   ```python
   @app.context_processor
   def inject_permissions():
       """向模板注入权限检查函数"""
       def user_has_permission(permission_code):
           if 'main_userid' not in session:
               return False
               
           user = UserRepository().get_by_id(session['main_userid'])
           if not user:
               return False
               
           return user.has_permission(permission_code)
           
       return dict(has_permission=user_has_permission)
   ```

#### 3.3.6 API安全性增强

**问题**：API缺乏适当的认证和授权机制。

**解决方案**：

1. **实现JWT认证**：
   ```python
   from flask_jwt_extended import JWTManager, create_access_token, jwt_required

   jwt = JWTManager()

   def create_app():
       app = Flask(__name__)
       # ...其他配置
       
       # 配置JWT
       app.config['JWT_SECRET_KEY'] = config_manager.get('jwt.secret_key', os.urandom(24))
       app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(minutes=30)
       jwt.init_app(app)
       
       return app
   ```

2. **API认证端点**：
   ```python
   @auth.route('/api/auth', methods=['POST'])
   def api_auth():
       """API认证端点，返回JWT令牌"""
       username = request.json.get('username', None)
       password = request.json.get('password', None)
       
       if not username or not password:
           return jsonify({'error': '用户名和密码不能为空'}), 400
           
       user = UserRepository().find_by_username(username)
       if not user or not user.check_password(password):
           return jsonify({'error': '用户名或密码错误'}), 401
           
       # 创建访问令牌
       access_token = create_access_token(
           identity=user.id,
           additional_claims={
               'username': user.username,
               'roles': [role.name for role in user.roles]
           }
       )
       
       return jsonify({'access_token': access_token})
   ```

3. **API路由保护**：
   ```python
   @api.route('/api/v1/articles', methods=['GET'])
   @jwt_required()
   def get_articles():
       """获取文章列表API"""
       # ...处理逻辑
   ```

4. **API请求限流**：
   ```python
   from flask_limiter import Limiter
   from flask_limiter.util import get_remote_address

   limiter = Limiter(
       key_func=get_remote_address,
       default_limits=["200 per day", "50 per hour"]
   )

   def create_app():
       app = Flask(__name__)
       # ...其他配置
       
       # 初始化限流器
       limiter.init_app(app)
       
       return app
       
   # 在路由上应用限流
   @api.route('/api/v1/login', methods=['POST'])
   @limiter.limit("10 per minute")
   def api_login():
       """API登录端点，应用较严格的限流规则"""
       # ...处理逻辑
   ```
