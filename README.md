# Woniunote - 现代化个人博客系统

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-2.0+-green.svg)](https://flask.palletsprojects.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Version](https://img.shields.io/badge/Version-0.1.4-orange.svg)](setup.py)

> 一个基于Python Flask框架构建的现代化、高性能个人博客系统，集成了丰富的功能模块和优化特性。

## 🌟 项目特色

- **现代化架构**: 采用MVC设计模式，模块化架构，易于维护和扩展
- **高性能优化**: 集成缓存系统、数据库优化、异步任务处理
- **安全防护**: 完善的权限管理、CSRF保护、输入验证、安全会话
- **用户体验**: 响应式设计、智能缓存、性能监控、用户行为分析
- **开发友好**: 完整的测试框架、代码质量检查、自动化部署支持

## 🏗️ 系统架构

```
woniunote/
├── 📁 woniunote/                 # 核心应用包
│   ├── 📁 controller/            # 控制器层 (MVC中的C)
│   │   ├── admin.py             # 管理员控制器
│   │   ├── article.py           # 文章管理控制器
│   │   ├── card_center.py       # 卡片中心控制器
│   │   ├── comment.py           # 评论管理控制器
│   │   ├── favorite.py          # 收藏管理控制器
│   │   ├── index.py             # 首页控制器
│   │   ├── todo_center.py       # 待办事项控制器
│   │   ├── ucenter.py           # 用户中心控制器
│   │   ├── ueditor.py           # 富文本编辑器控制器
│   │   └── user.py              # 用户管理控制器
│   ├── 📁 models/               # 数据模型层 (MVC中的M)
│   │   ├── card.py              # 卡片模型
│   │   └── todo.py              # 待办事项模型
│   ├── 📁 common/               # 公共模块
│   │   ├── 📁 核心功能
│   │   │   ├── database.py      # 数据库连接管理
│   │   │   ├── utils.py         # 通用工具函数
│   │   │   └── simple_logger.py # 日志系统
│   │   ├── 📁 安全模块
│   │   │   ├── security_enhanced.py    # 安全增强
│   │   │   ├── api_security.py         # API安全
│   │   │   ├── csrf_protection.py      # CSRF保护
│   │   │   └── secure_password.py      # 密码安全
│   │   ├── 📁 性能优化
│   │   │   ├── cache_utils.py          # 缓存工具
│   │   │   ├── database_optimizer.py   # 数据库优化
│   │   │   ├── performance_monitor.py  # 性能监控
│   │   │   └── rate_limiter.py        # 限流控制
│   │   ├── 📁 用户体验
│   │   │   ├── user_experience_optimizer.py # 用户体验优化
│   │   │   └── async_tasks.py         # 异步任务
│   │   └── 📁 运维管理
│   │       ├── monitoring.py           # 系统监控
│   │       └── intelligent_ops_manager.py # 智能运维
│   ├── 📁 services/             # 业务服务层
│   │   └── article_service.py   # 文章服务
│   ├── 📁 template/             # 模板文件 (MVC中的V)
│   │   ├── base.html            # 基础模板
│   │   ├── index.html           # 首页模板
│   │   ├── article-*.html       # 文章相关模板
│   │   └── user-*.html          # 用户相关模板
│   ├── 📁 resource/             # 静态资源
│   │   ├── css/                 # 样式文件
│   │   ├── js/                  # JavaScript文件
│   │   ├── img/                 # 图片资源
│   │   └── ueditor/             # 富文本编辑器
│   ├── app.py                   # 主应用文件
│   ├── app_factory.py           # 应用工厂
│   └── __init__.py              # 包初始化文件
├── 📁 configs/                  # 配置文件
│   ├── config.py                # Python配置类
│   ├── user_password_config.yaml # 主配置文件
│   └── development_config.yaml  # 开发环境配置
├── 📁 tests/                    # 测试文件
├── 📁 docs/                     # 文档
├── requirements.txt              # Python依赖
├── setup.py                     # 安装配置
└── README.md                    # 项目说明
```

## 🚀 核心功能

### 📝 内容管理
- **文章系统**: 支持原创、转载、翻译等多种类型
- **富文本编辑**: 集成UEditor编辑器，支持图片上传
- **分类标签**: 灵活的文章分类和标签系统
- **草稿功能**: 支持文章草稿保存和编辑

### 👥 用户系统
- **用户注册**: 安全的用户注册和验证
- **权限管理**: 多角色权限控制（用户、管理员）
- **个人中心**: 用户信息管理、头像上传
- **积分系统**: 用户活跃度积分机制

### 💬 互动功能
- **评论系统**: 文章评论和回复
- **收藏功能**: 用户收藏管理
- **点赞系统**: 内容点赞和推荐

### 📊 管理功能
- **内容审核**: 文章审核和发布控制
- **用户管理**: 用户信息查看和管理
- **系统监控**: 性能监控和日志管理
- **数据统计**: 访问统计和用户行为分析

### 🎯 特色功能
- **待办事项**: 个人任务管理
- **卡片中心**: 信息卡片展示
- **数学训练**: 数学练习工具
- **文件上传**: 安全的文件上传和管理

## 🛠️ 技术栈

### 后端技术
- **Python 3.8+**: 核心编程语言
- **Flask 2.0+**: Web框架
- **SQLAlchemy**: ORM数据库操作
- **PyMySQL**: MySQL数据库驱动
- **Redis**: 缓存和会话存储
- **Jinja2**: 模板引擎

### 前端技术
- **HTML5/CSS3**: 页面结构和样式
- **JavaScript**: 交互功能
- **Bootstrap**: 响应式UI框架
- **Vue.js**: 前端框架
- **jQuery**: DOM操作和AJAX

### 数据库
- **MySQL**: 主数据库
- **SQLite**: 开发环境数据库
- **Redis**: 缓存数据库

### 部署和运维
- **Gunicorn**: WSGI服务器
- **Nginx**: 反向代理
- **Docker**: 容器化部署
- **Git**: 版本控制

## 📦 安装部署

### 环境要求
- Python 3.8+
- MySQL 5.7+ 或 SQLite 3
- Redis 4.0+ (可选)
- 现代浏览器支持

### 快速开始

#### 1. 克隆项目
```bash
# 国内用户
git clone https://gitee.com/yunjinqi/woniunote.git

# 国外用户
git clone https://github.com/cloudQuant/woniunote.git

cd woniunote
```

#### 2. 安装依赖
```bash
# 安装Python依赖
pip install -r requirements.txt

# 或者使用conda
conda install --file requirements.txt
```

#### 3. 配置数据库
```bash
# 复制配置文件
cp configs/user_password_config.yaml.example configs/user_password_config.yaml

# 编辑配置文件
nano configs/user_password_config.yaml
```

配置文件示例：
```yaml
# 数据库配置
database:
  SQLALCHEMY_DATABASE_URI: mysql://username:password@localhost:3306/woniunote
  SQLALCHEMY_TRACK_MODIFICATIONS: false

# 安全配置
SECRET_KEY: 'your-secret-key-here'
WTF_CSRF_SECRET_KEY: 'your-csrf-key-here'
```

#### 4. 初始化数据库
```bash
cd woniunote/woniunote
python common/create_database.py
```

#### 5. 启动应用
```bash
# 开发环境
python app.py

# 生产环境
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### 开发环境配置

#### 使用SQLite (推荐开发环境)
```yaml
database:
  SQLALCHEMY_DATABASE_URI: sqlite:///woniunote_dev.db
```

#### 使用MySQL (生产环境)
```yaml
database:
  SQLALCHEMY_DATABASE_URI: mysql://user:pass@localhost:3306/woniunote
```

## 🧪 测试

### 运行测试
```bash
# 安装测试依赖
pip install -r requirements.txt

# 安装Playwright浏览器
playwright install

# 运行功能测试
pytest . -v --cov=woniunote --cov-report=html

# 运行性能测试
locust -f tests/test_performance.py --host=http://localhost:5000
```

### 测试覆盖率
- 单元测试: 核心功能模块
- 集成测试: API接口和数据库操作
- 性能测试: 负载和压力测试
- 安全测试: 权限和输入验证

## 🔧 配置说明

### 环境变量
```bash
export FLASK_ENV=development
export FLASK_DEBUG=1
export DATABASE_URL=sqlite:///woniunote_dev.db
export SECRET_KEY=your-secret-key
```

### 配置文件结构
- **configs/config.py**: Python配置类
- **configs/user_password_config.yaml**: 主配置文件
- **configs/development_config.yaml**: 开发环境配置

## 🚀 性能优化

### 缓存策略
- **Redis缓存**: 热点数据缓存
- **内存缓存**: 快速访问缓存
- **智能缓存**: 基于访问模式的缓存策略

### 数据库优化
- **连接池**: 数据库连接复用
- **查询优化**: N+1查询问题解决
- **索引优化**: 数据库性能提升

### 前端优化
- **静态资源**: CDN加速和压缩
- **懒加载**: 图片和内容懒加载
- **代码分割**: JavaScript模块化

## 🔒 安全特性

### 认证授权
- **JWT令牌**: 安全的身份验证
- **权限控制**: 基于角色的访问控制
- **会话管理**: 安全的会话处理

### 数据保护
- **CSRF保护**: 跨站请求伪造防护
- **XSS防护**: 跨站脚本攻击防护
- **SQL注入防护**: 参数化查询

### 输入验证
- **数据清洗**: 输入数据安全处理
- **文件上传**: 安全的文件上传验证
- **API限流**: 防止API滥用

## 📊 监控和日志

### 系统监控
- **性能监控**: 响应时间和吞吐量
- **资源监控**: CPU、内存、磁盘使用
- **错误监控**: 异常和错误统计

### 日志系统
- **结构化日志**: JSON格式日志输出
- **日志级别**: 可配置的日志级别
- **日志轮转**: 自动日志文件管理

## 🌐 部署指南

### Docker部署
```bash
# 构建镜像
docker build -t woniunote .

# 运行容器
docker run -d -p 5000:5000 woniunote
```

### 生产环境部署
```bash
# 使用Gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 --timeout 120 app:app

# 使用Nginx反向代理
# 配置nginx.conf文件
```

### 环境配置
- **开发环境**: 调试模式，SQLite数据库
- **测试环境**: 测试数据，MySQL数据库
- **生产环境**: 生产配置，MySQL数据库

## 🤝 贡献指南

### 开发流程
1. Fork项目
2. 创建功能分支
3. 提交代码
4. 创建Pull Request

### 代码规范
- 遵循PEP 8 Python代码规范
- 添加适当的注释和文档
- 编写单元测试
- 确保代码质量

### 问题反馈
- 使用GitHub Issues报告问题
- 提供详细的错误信息和复现步骤
- 标注问题类型和优先级

## 📚 文档

- [API文档](docs/api.md)
- [部署指南](docs/deployment.md)
- [开发指南](docs/development.md)
- [故障排除](TROUBLESHOOTING.md)

## 📄 许可证

本项目采用 [MIT License](LICENSE) 许可证。

## 👨‍💻 作者

- **作者**: cloudQuant (云金杞)
- **邮箱**: yunjinqi@gmail.com
- **网站**: https://www.yunjinqi.top
- **GitHub**: https://github.com/cloudQuant

## 🙏 致谢

感谢所有为这个项目做出贡献的开发者和用户。

## 📞 联系方式

- **项目主页**: https://github.com/cloudQuant/woniunote
- **在线演示**: https://www.yunjinqi.top
- **问题反馈**: https://github.com/cloudQuant/woniunote/issues
- **技术交流**: 欢迎提交Issue和Pull Request

---

⭐ 如果这个项目对你有帮助，请给它一个星标！



