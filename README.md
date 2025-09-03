# Woniunote - 现代化个人博客系统

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-2.0+-green.svg)](https://flask.palletsprojects.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Version](https://img.shields.io/badge/Version-4.0-orange.svg)](setup.py)

<!-- Language Switcher -->
<div id="language-switcher" style="margin: 20px 0;">
  <button id="btn-cn" onclick="showLanguage('cn')" style="background: #1890ff; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; margin: 0 5px;">🇨🇳 中文</button>
  <button id="btn-en" onclick="showLanguage('en')" style="background: #f0f0f0; color: #333; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; margin: 0 5px;">🇺🇸 English</button>
</div>

<!-- JavaScript for Language Switching -->
<script>
function showLanguage(lang) {
  // Hide all content sections
  const allSections = document.querySelectorAll('.content-section');
  allSections.forEach(section => section.style.display = 'none');

  // Hide all title spans
  const allTitles = document.querySelectorAll('span[id$="-cn"], span[id$="-en"]');
  allTitles.forEach(title => title.style.display = 'none');

  // Update button styles
  document.getElementById('btn-cn').style.background = lang === 'cn' ? '#1890ff' : '#f0f0f0';
  document.getElementById('btn-cn').style.color = lang === 'cn' ? 'white' : '#333';
  document.getElementById('btn-en').style.background = lang === 'en' ? '#1890ff' : '#f0f0f0';
  document.getElementById('btn-en').style.color = lang === 'en' ? 'white' : '#333';

  // Show selected language content
  const selectedSections = document.querySelectorAll(`[id*="-${lang}-content"], [id*="-${lang}"]`);
  selectedSections.forEach(section => {
    if (section.id.endsWith(`-${lang}`) || section.id.endsWith(`-${lang}-content`)) {
      section.style.display = 'block';
    }
  });

  // Update page title
  document.title = lang === 'cn' ? 'WoniuNote - 现代化个人博客系统' : 'WoniuNote - Modern Personal Blog System';

  // Store language preference
  localStorage.setItem('readme-language', lang);
}

// Load language preference on page load
document.addEventListener('DOMContentLoaded', function() {
  const savedLang = localStorage.getItem('readme-language') || 'cn';
  showLanguage(savedLang);
});
</script>

<!-- Chinese Version -->
<div id="content-cn" class="content-section">
  <p align="center">
    一个基于Python Flask框架构建的现代化、高性能个人博客系统，集成了丰富的功能模块和优化特性。
  </p>
</div>

<!-- English Version -->
<div id="content-en" class="content-section" style="display: none;">
  <p align="center">
    A modern, high-performance personal blog system built with Python Flask framework, featuring rich functional modules and optimization characteristics.
  </p>
</div>

</div>

## 🌟 <span id="features-cn">项目特色</span><span id="features-en" style="display: none;">Features</span>

<!-- Chinese Features -->
<div id="features-cn-content" class="content-section">
- **现代化架构**: 采用MVC设计模式，模块化架构，易于维护和扩展
- **高性能优化**: 集成缓存系统、数据库优化、异步任务处理
- **安全防护**: 完善的权限管理、CSRF保护、输入验证、安全会话
- **用户体验**: 响应式设计、智能缓存、性能监控、用户行为分析
- **开发友好**: 完整的测试框架、代码质量检查、自动化部署支持
- **智能运维**: 统一监控、数据库优化、性能增强、用户体验优化
- **多语言支持**: 支持中英文界面，国际化设计
</div>

<!-- English Features -->
<div id="features-en-content" class="content-section" style="display: none;">
- **Modern Architecture**: Uses MVC design pattern, modular architecture, easy to maintain and extend
- **High Performance**: Integrated caching system, database optimization, asynchronous task processing
- **Security Protection**: Comprehensive permission management, CSRF protection, input validation, secure sessions
- **User Experience**: Responsive design, intelligent caching, performance monitoring, user behavior analysis
- **Developer Friendly**: Complete testing framework, code quality checks, automated deployment support
- **Intelligent Operations**: Unified monitoring, database optimization, performance enhancement, UX optimization
- **Multi-language**: Support Chinese and English interfaces, internationalized design
</div>

## 🏗️ <span id="architecture-cn">系统架构</span><span id="architecture-en" style="display: none;">System Architecture</span>

### 📁 <span id="project-structure-cn">项目结构</span><span id="project-structure-en" style="display: none;">Project Structure</span>

<!-- Chinese Project Structure -->
<div id="project-structure-cn-content" class="content-section">
```
woniunote/                        # 根目录
├── 📄 README.md                 # 项目文档
├── 📄 LICENSE                   # MIT许可证
├── 📄 requirements.txt          # Python依赖列表
├── 📄 setup.py                  # 包安装配置
├── 📄 pytest.ini               # 测试配置
├── 📄 CLAUDE.md                 # AI助手指南
├── 📁 configs/                  # 配置文件目录
│   ├── config.py                # Flask配置类
│   ├── user_password_config.yaml # 主配置文件
│   └── *.yaml                   # 其他配置文件
├── 📁 docs/                     # 文档目录
├── 📁 scripts/                  # 开发脚本目录
├── 📁 tests/                    # 测试套件 (100% 通过率)
├── 📁 logs/                     # 日志目录
└── 📁 woniunote/                # 核心应用包
    ├── 📄 app.py                # Flask应用入口
    ├── 📄 app_factory.py        # 应用工厂模式
    ├── 📁 controller/           # 控制器层 (MVC-C)
    │   ├── admin.py             # 管理员控制器
    │   ├── article.py           # 文章管理
    │   ├── card_center.py       # 卡片中心
    │   ├── comment.py           # 评论管理
    │   ├── favorite.py          # 收藏管理
    │   ├── index.py             # 首页控制器
    │   ├── todo_center.py       # 待办事项
    │   ├── ucenter.py           # 用户中心
    │   ├── ueditor.py           # 富文本编辑器
    │   └── user.py              # 用户管理
    ├── 📁 module/               # 业务逻辑层
    │   ├── articles.py          # 文章业务逻辑
    │   ├── users.py             # 用户业务逻辑
    │   ├── comments.py          # 评论业务逻辑
    │   ├── credits.py           # 积分系统
    │   └── favorites.py         # 收藏业务逻辑
    ├── 📁 models/               # 数据模型层
    │   ├── card.py              # 卡片数据模型
    │   └── todo.py              # 待办事项模型
    ├── 📁 common/               # 统一基础模块
    │   ├── unified_session.py   # 🔐 统一会话管理
    │   ├── unified_error_handler.py # ⚠️ 统一错误处理
    │   ├── unified_database_optimizer.py # 🗄️ 数据库优化
    │   ├── unified_monitoring.py # 📊 统一监控系统
    │   ├── unified_security.py  # 🛡️ 统一安全管理
    │   ├── unified_cache.py     # ⚡ 统一缓存管理
    │   ├── unified_logging.py   # 📝 统一日志系统
    │   ├── unified_config.py    # ⚙️ 统一配置管理
    │   ├── unified_validator.py # ✅ 统一验证器
    │   ├── unified_utils.py     # 🛠️ 统一工具集
    │   ├── rate_limiter.py      # 🚦 限流系统
    │   ├── async_tasks.py       # 🔄 异步任务
    │   ├── static_optimizer.py  # 🎨 静态资源优化
    │   └── *.py                 # 其他工具模块
    ├── 📁 services/             # 服务层
    │   └── article_service.py   # 文章业务服务
    ├── 📁 template/             # 视图模板
    │   ├── base.html            # 基础模板
    │   ├── index.html           # 首页模板
    │   ├── article-*.html       # 文章相关模板
    │   ├── user-*.html          # 用户相关模板
    │   └── *.html               # 其他模板
    ├── 📁 resource/             # 静态资源
    │   ├── css/                 # 样式文件
    │   ├── js/                  # JavaScript文件
    │   ├── img/                 # 图片资源
    │   ├── ueditor/             # 富文本编辑器
    │   └── upload/              # 用户上传文件
    └── 📁 static/               # 静态文件
        └── favicon.ico          # 网站图标
```
</div>

<!-- English Project Structure -->
<div id="project-structure-en-content" class="content-section" style="display: none;">
```
woniunote/                        # Root Directory
├── 📄 README.md                 # Project Documentation
├── 📄 LICENSE                   # MIT License
├── 📄 requirements.txt          # Python Dependencies
├── 📄 setup.py                  # Package Setup
├── 📄 pytest.ini               # Test Configuration
├── 📄 CLAUDE.md                 # AI Assistant Guide
├── 📁 configs/                  # Configuration Directory
│   ├── config.py                # Flask Configuration Class
│   ├── user_password_config.yaml # Main Configuration File
│   └── *.yaml                   # Other Config Files
├── 📁 docs/                     # Documentation Directory
├── 📁 scripts/                  # Development Scripts
├── 📁 tests/                    # Test Suite (100% Pass Rate)
├── 📁 logs/                     # Logs Directory
└── 📁 woniunote/                # Core Application Package
    ├── 📄 app.py                # Flask App Entry
    ├── 📄 app_factory.py        # App Factory Pattern
    ├── 📁 controller/           # Controllers (MVC-C)
    │   ├── admin.py             # Admin Controller
    │   ├── article.py           # Article Management
    │   ├── card_center.py       # Card Center
    │   ├── comment.py           # Comment Management
    │   ├── favorite.py          # Favorites Management
    │   ├── index.py             # Home Controller
    │   ├── todo_center.py       # Todo Center
    │   ├── ucenter.py           # User Center
    │   ├── ueditor.py           # Rich Text Editor
    │   └── user.py              # User Management
    ├── 📁 module/               # Business Logic Layer
    │   ├── articles.py          # Article Business Logic
    │   ├── users.py             # User Business Logic
    │   ├── comments.py          # Comment Business Logic
    │   ├── credits.py           # Credit System
    │   └── favorites.py         # Favorites Business Logic
    ├── 📁 models/               # Data Models Layer
    │   ├── card.py              # Card Data Model
    │   └── todo.py              # Todo Data Model
    ├── 📁 common/               # Unified Common Modules
    │   ├── unified_session.py   # 🔐 Unified Session Management
    │   ├── unified_error_handler.py # ⚠️ Unified Error Handling
    │   ├── unified_database_optimizer.py # 🗄️ Database Optimizer
    │   ├── unified_monitoring.py # 📊 Unified Monitoring
    │   ├── unified_security.py  # 🛡️ Unified Security
    │   ├── unified_cache.py     # ⚡ Unified Cache Management
    │   ├── unified_logging.py   # 📝 Unified Logging
    │   ├── unified_config.py    # ⚙️ Unified Configuration
    │   ├── unified_validator.py # ✅ Unified Validator
    │   ├── unified_utils.py     # 🛠️ Unified Utilities
    │   ├── rate_limiter.py      # 🚦 Rate Limiting
    │   ├── async_tasks.py       # 🔄 Asynchronous Tasks
    │   ├── static_optimizer.py  # 🎨 Static Resource Optimization
    │   └── *.py                 # Other Utility Modules
    ├── 📁 services/             # Service Layer
    │   └── article_service.py   # Article Service
    ├── 📁 template/             # View Templates
    │   ├── base.html            # Base Template
    │   ├── index.html           # Home Template
    │   ├── article-*.html       # Article Templates
    │   ├── user-*.html          # User Templates
    │   └── *.html               # Other Templates
    ├── 📁 resource/             # Static Resources
    │   ├── css/                 # CSS Files
    │   ├── js/                  # JavaScript Files
    │   ├── img/                 # Images
    │   ├── ueditor/             # Rich Text Editor
    │   └── upload/              # User Uploads
    └── 📁 static/               # Static Files
        └── favicon.ico          # Website Favicon
```
</div>

### 🎯 <span id="architecture-design-cn">架构设计</span><span id="architecture-design-en" style="display: none;">Architecture Design</span>

<!-- Chinese Architecture Design -->
<div id="architecture-design-cn-content" class="content-section">
#### 架构层级
- **表现层 (Presentation Layer)**
  - Flask路由控制器
  - Jinja2模板引擎
  - RESTful API接口
- **业务逻辑层 (Business Logic Layer)**
  - 业务规则处理
  - 数据验证逻辑
  - 业务流程控制
- **数据访问层 (Data Access Layer)**
  - SQLAlchemy ORM
  - 数据库连接池
  - 查询优化器
- **基础设施层 (Infrastructure Layer)**
  - 缓存系统 (Redis)
  - 消息队列
  - 文件存储
  - 监控告警
</div>

<!-- English Architecture Design -->
<div id="architecture-design-en-content" class="content-section" style="display: none;">
#### Architecture Layers
- **Presentation Layer**
  - Flask Route Controllers
  - Jinja2 Template Engine
  - RESTful API Interfaces
- **Business Logic Layer**
  - Business Rules Processing
  - Data Validation Logic
  - Business Process Control
- **Data Access Layer**
  - SQLAlchemy ORM
  - Database Connection Pool
  - Query Optimizer
- **Infrastructure Layer**
  - Caching System (Redis)
  - Message Queue
  - File Storage
  - Monitoring & Alerting
</div>

## 🚀 <span id="core-features-cn">核心功能</span><span id="core-features-en" style="display: none;">Core Features</span>

### 📝 <span id="content-management-cn">内容管理系统</span><span id="content-management-en" style="display: none;">Content Management System</span>

<!-- Chinese Content Management -->
<div id="content-management-cn-content" class="content-section">
- **文章系统**: 支持原创、转载、翻译等多种类型文章
- **富文本编辑**: 集成UEditor编辑器，支持图片上传和多媒体
- **分类标签**: 灵活的文章分类和标签系统
- **草稿功能**: 支持文章草稿保存和编辑
- **搜索功能**: 智能搜索和关键词高亮
- **分页浏览**: 高效的分页加载和浏览
</div>

<!-- English Content Management -->
<div id="content-management-en-content" class="content-section" style="display: none;">
- **Article System**: Support original, repost, translation and other article types
- **Rich Text Editor**: Integrated UEditor with image upload and multimedia support
- **Categories & Tags**: Flexible article categorization and tagging system
- **Draft System**: Support article draft saving and editing
- **Search**: Intelligent search with keyword highlighting
- **Pagination**: Efficient pagination loading and browsing
</div>

### 👥 <span id="user-management-cn">用户管理系统</span><span id="user-management-en" style="display: none;">User Management System</span>

<!-- Chinese User Management -->
<div id="user-management-cn-content" class="content-section">
- **用户注册**: 安全的用户注册和邮箱验证
- **用户登录**: 多重身份验证和自动登录
- **权限管理**: 基于角色的访问控制 (RBAC)
- **个人中心**: 用户资料管理、头像上传
- **积分系统**: 用户活跃度积分和奖励机制
- **密码安全**: 密码加密存储和重置功能
</div>

<!-- English User Management -->
<div id="user-management-en-content" class="content-section" style="display: none;">
- **Registration**: Secure user registration with email verification
- **Authentication**: Multi-factor authentication and auto-login
- **Authorization**: Role-based access control (RBAC)
- **Profile Center**: User profile management, avatar upload
- **Credit System**: User activity points and reward system
- **Password Security**: Encrypted password storage and reset
</div>

### 💬 <span id="social-interaction-cn">社交互动系统</span><span id="social-interaction-en" style="display: none;">Social Interaction System</span>

<!-- Chinese Social Interaction -->
<div id="social-interaction-cn-content" class="content-section">
- **评论系统**: 文章评论、回复和嵌套评论
- **收藏功能**: 用户文章收藏和收藏夹管理
- **点赞系统**: 内容点赞、推荐和热度排序
</div>

<!-- English Social Interaction -->
<div id="social-interaction-en-content" class="content-section" style="display: none;">
- **Comment System**: Article comments, replies and nested comments
- **Favorites**: User article favorites and collection management
- **Like System**: Content likes, recommendations and popularity sorting
</div>

### 🎯 <span id="special-features-cn">特色功能模块</span><span id="special-features-en" style="display: none;">Special Features</span>

<!-- Chinese Special Features -->
<div id="special-features-cn-content" class="content-section">
- **待办事项**: 个人任务管理、提醒和进度跟踪
- **卡片中心**: 信息卡片展示和管理
- **数学训练**: 数学练习工具和成绩统计
- **文件上传**: 安全的文件上传、验证和管理
</div>

<!-- English Special Features -->
<div id="special-features-en-content" class="content-section" style="display: none;">
- **Todo Center**: Personal task management, reminders and progress tracking
- **Card Center**: Information card display and management
- **Math Training**: Math practice tools and score statistics
- **File Upload**: Secure file upload, validation and management
</div>

### 🔧 <span id="admin-panel-cn">管理后台</span><span id="admin-panel-en" style="display: none;">Admin Panel</span>

<!-- Chinese Admin Panel -->
<div id="admin-panel-cn-content" class="content-section">
- **内容审核**: 文章审核、发布控制和内容管理
- **用户管理**: 用户信息查看、编辑和权限管理
- **系统监控**: 实时性能监控、告警和日志管理
- **数据统计**: 访问统计、用户行为分析和报表
- **数据库优化**: 查询优化、索引管理和性能调优
- **安全审计**: 安全事件监控、审计日志和威胁检测
</div>

<!-- English Admin Panel -->
<div id="admin-panel-en-content" class="content-section" style="display: none;">
- **Content Moderation**: Article review, publishing control and content management
- **User Management**: User information view, edit and permission management
- **System Monitoring**: Real-time performance monitoring, alerts and log management
- **Data Analytics**: Access statistics, user behavior analysis and reports
- **Database Optimization**: Query optimization, index management and performance tuning
- **Security Audit**: Security event monitoring, audit logs and threat detection
</div>

### 🔌 <span id="api-interfaces-cn">API接口</span><span id="api-interfaces-en" style="display: none;">API Interfaces</span>

<!-- Chinese API Interfaces -->
<div id="api-interfaces-cn-content" class="content-section">
- **RESTful API**: 标准的REST API设计
- **JWT认证**: JSON Web Token身份验证
- **API限流**: 防止API滥用和DoS攻击
- **API文档**: 自动生成的API文档
- **版本控制**: API版本管理和向后兼容
</div>

<!-- English API Interfaces -->
<div id="api-interfaces-en-content" class="content-section" style="display: none;">
- **RESTful API**: Standard REST API design
- **JWT Authentication**: JSON Web Token authentication
- **Rate Limiting**: Prevent API abuse and DoS attacks
- **API Documentation**: Auto-generated API documentation
- **Version Control**: API versioning and backward compatibility
</div>

## 🛠️ <span id="tech-stack-cn">技术栈</span><span id="tech-stack-en" style="display: none;">Technology Stack</span>

### 🔧 <span id="backend-stack-cn">后端技术栈</span><span id="backend-stack-en" style="display: none;">Backend Stack</span>

<!-- Chinese Backend Stack -->
<div id="backend-stack-cn-content" class="content-section">
| 技术组件 | 版本要求 | 说明 |
|---------|----------|------|
| **Python** | 3.8+ | 核心编程语言 |
| **Flask** | 2.0+ | Web框架 |
| **SQLAlchemy** | 1.4+ | ORM数据库操作 |
| **PyMySQL** | 1.0+ | MySQL数据库驱动 |
| **Redis** | 4.0+ | 缓存和会话存储 |
| **Jinja2** | 3.0+ | 模板引擎 |
| **Werkzeug** | 2.0+ | WSGI工具包 |
| **Flask-Caching** | 2.0+ | 缓存扩展 |
| **Flask-WTF** | 1.1+ | 表单和CSRF保护 |
| **Flask-Session** | 0.4+ | 会话管理 |
</div>

<!-- English Backend Stack -->
<div id="backend-stack-en-content" class="content-section" style="display: none;">
| Technology | Version | Description |
|------------|---------|-------------|
| **Python** | 3.8+ | Core programming language |
| **Flask** | 2.0+ | Web framework |
| **SQLAlchemy** | 1.4+ | ORM database operations |
| **PyMySQL** | 1.0+ | MySQL database driver |
| **Redis** | 4.0+ | Caching and session storage |
| **Jinja2** | 3.0+ | Template engine |
| **Werkzeug** | 2.0+ | WSGI toolkit |
| **Flask-Caching** | 2.0+ | Caching extension |
| **Flask-WTF** | 1.1+ | Forms and CSRF protection |
| **Flask-Session** | 0.4+ | Session management |
</div>

### 🎨 <span id="frontend-stack-cn">前端技术栈</span><span id="frontend-stack-en" style="display: none;">Frontend Stack</span>

<!-- Chinese Frontend Stack -->
<div id="frontend-stack-cn-content" class="content-section">
| 前端技术 | 说明 |
|---------|------|
| **HTML5** | 语义化页面结构 |
| **CSS3** | 现代化样式和动画 |
| **JavaScript** | ES6+ 交互功能 |
| **Bootstrap** | 响应式UI框架 |
| **jQuery** | DOM操作和AJAX |
| **UEditor** | 富文本编辑器 |
</div>

<!-- English Frontend Stack -->
<div id="frontend-stack-en-content" class="content-section" style="display: none;">
| Frontend Tech | Description |
|---------------|-------------|
| **HTML5** | Semantic page structure |
| **CSS3** | Modern styling and animations |
| **JavaScript** | ES6+ interactive features |
| **Bootstrap** | Responsive UI framework |
| **jQuery** | DOM manipulation and AJAX |
| **UEditor** | Rich text editor |
</div>

### 🗄️ <span id="database-stack-cn">数据库技术栈</span><span id="database-stack-en" style="display: none;">Database Stack</span>

<!-- Chinese Database Stack -->
<div id="database-stack-cn-content" class="content-section">
| 数据库类型 | 用途 |
|-----------|------|
| **MySQL** | 主数据库，关系型数据存储 |
| **SQLite** | 开发环境和测试数据库 |
| **Redis** | 缓存、会话存储、消息队列 |
</div>

<!-- English Database Stack -->
<div id="database-stack-en-content" class="content-section" style="display: none;">
| Database Type | Usage |
|---------------|-------|
| **MySQL** | Primary database, relational data storage |
| **SQLite** | Development and testing database |
| **Redis** | Caching, session storage, message queue |
</div>

### 🚀 <span id="deployment-stack-cn">部署和运维</span><span id="deployment-stack-en" style="display: none;">Deployment & Operations</span>

<!-- Chinese Deployment Stack -->
<div id="deployment-stack-cn-content" class="content-section">
| 部署工具 | 功能 |
|---------|------|
| **Gunicorn** | WSGI应用服务器 |
| **Nginx** | 反向代理和静态文件服务 |
| **Docker** | 容器化部署 |
| **Git** | 版本控制 |
| **Supervisor** | 进程管理 |
</div>

<!-- English Deployment Stack -->
<div id="deployment-stack-en-content" class="content-section" style="display: none;">
| Deployment Tools | Features |
|------------------|----------|
| **Gunicorn** | WSGI application server |
| **Nginx** | Reverse proxy and static file serving |
| **Docker** | Containerized deployment |
| **Git** | Version control |
| **Supervisor** | Process management |
</div>

### 🧪 <span id="testing-stack-cn">测试技术栈</span><span id="testing-stack-en" style="display: none;">Testing Stack</span>

<!-- Chinese Testing Stack -->
<div id="testing-stack-cn-content" class="content-section">
| 测试工具 | 覆盖范围 |
|---------|----------|
| **pytest** | 单元测试、集成测试 |
| **pytest-cov** | 代码覆盖率分析 |
| **pytest-flask** | Flask应用测试 |
| **pytest-playwright** | E2E浏览器测试 |
| **Locust** | 性能负载测试 |
</div>

<!-- English Testing Stack -->
<div id="testing-stack-en-content" class="content-section" style="display: none;">
| Testing Tools | Coverage |
|---------------|----------|
| **pytest** | Unit testing, integration testing |
| **pytest-cov** | Code coverage analysis |
| **pytest-flask** | Flask app testing |
| **pytest-playwright** | E2E browser testing |
| **Locust** | Performance load testing |
</div>

### 📊 <span id="monitoring-stack-cn">监控和分析</span><span id="monitoring-stack-en" style="display: none;">Monitoring & Analytics</span>

<!-- Chinese Monitoring Stack -->
<div id="monitoring-stack-cn-content" class="content-section">
| 监控工具 | 功能 |
|---------|------|
| **psutil** | 系统资源监控 |
| **Flask-Monitoring** | 应用性能监控 |
| **自定义监控** | 业务指标监控 |
| **日志系统** | 结构化日志记录 |
</div>

<!-- English Monitoring Stack -->
<div id="monitoring-stack-en-content" class="content-section" style="display: none;">
| Monitoring Tools | Features |
|------------------|----------|
| **psutil** | System resource monitoring |
| **Flask-Monitoring** | Application performance monitoring |
| **Custom Monitoring** | Business metrics monitoring |
| **Logging System** | Structured logging |
</div>

### 🔒 <span id="security-stack-cn">安全技术栈</span><span id="security-stack-en" style="display: none;">Security Stack</span>

<!-- Chinese Security Stack -->
<div id="security-stack-cn-content" class="content-section">
| 安全组件 | 保护范围 |
|---------|----------|
| **Werkzeug** | 密码哈希和安全工具 |
| **Flask-WTF** | CSRF保护 |
| **自定义安全** | 输入验证、XSS防护 |
| **JWT** | API身份验证 |
| **限流器** | API访问控制 |
</div>

<!-- English Security Stack -->
<div id="security-stack-en-content" class="content-section" style="display: none;">
| Security Components | Protection Scope |
|---------------------|-----------------|
| **Werkzeug** | Password hashing and security utilities |
| **Flask-WTF** | CSRF protection |
| **Custom Security** | Input validation, XSS protection |
| **JWT** | API authentication |
| **Rate Limiter** | API access control |
</div>

## 📦 <span id="installation-cn">安装部署</span><span id="installation-en" style="display: none;">Installation & Deployment</span>

### 💻 <span id="requirements-cn">环境要求</span><span id="requirements-en" style="display: none;">System Requirements</span>

<!-- Chinese Requirements -->
<div id="requirements-cn-content" class="content-section">
| 组件 | 版本要求 | 是否必需 | 说明 |
|------|----------|----------|------|
| **Python** | 3.8+ | ✅ | 核心编程语言 |
| **MySQL** | 5.7+ | ❌ | 主数据库（可选） |
| **SQLite** | 3+ | ✅ | 开发/测试数据库 |
| **Redis** | 4.0+ | ❌ | 缓存和会话存储 |
| **Git** | 2.0+ | ✅ | 版本控制 |
| **现代浏览器** | Chrome 80+ | ✅ | 前端界面显示 |
</div>

<!-- English Requirements -->
<div id="requirements-en-content" class="content-section" style="display: none;">
| Component | Version | Required | Description |
|-----------|---------|----------|-------------|
| **Python** | 3.8+ | ✅ | Core programming language |
| **MySQL** | 5.7+ | ❌ | Primary database (optional) |
| **SQLite** | 3+ | ✅ | Development/testing database |
| **Redis** | 4.0+ | ❌ | Caching and session storage |
| **Git** | 2.0+ | ✅ | Version control |
| **Modern Browser** | Chrome 80+ | ✅ | Frontend interface display |
</div>

### 🚀 <span id="quick-start-cn">快速开始</span><span id="quick-start-en" style="display: none;">Quick Start</span>

<!-- Chinese Quick Start -->
<div id="quick-start-cn-content" class="content-section">
#### 1. 📥 克隆项目 | Clone Project
```bash
# 国内用户
git clone https://gitee.com/yunjinqi/woniunote.git

# 国外用户
git clone https://github.com/cloudQuant/woniunote.git

cd woniunote
```

#### 2. 📦 安装依赖 | Install Dependencies
```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/macOS
# 或
venv\Scripts\activate     # Windows

# 安装Python依赖
pip install -r requirements.txt

# 安装项目包 (开发模式)
pip install -e .

# 可选：安装Playwright浏览器驱动
playwright install
```

#### 3. ⚙️ 配置数据库 | Database Configuration
```bash
# 复制配置文件模板
cp configs/user_password_config.yaml.example configs/user_password_config.yaml

# 编辑配置文件
nano configs/user_password_config.yaml
```

**配置文件示例:**
```yaml
# 数据库配置
database:
  SQLALCHEMY_DATABASE_URI: mysql://username:password@localhost:3306/woniunote
  SQLALCHEMY_TRACK_MODIFICATIONS: false

# 安全配置
SECRET_KEY: 'your-secret-key-here-change-in-production'
WTF_CSRF_SECRET_KEY: 'your-csrf-key-here'

# Redis配置 (可选)
redis:
  REDIS_URL: redis://localhost:6379/0

# 监控配置
monitoring:
  system_monitoring: true
  collect_interval: 30

# 缓存配置
cache:
  default_ttl: 300
  memory_max_size: 2000
```

#### 4. 🗄️ 初始化数据库 | Initialize Database
```bash
# 使用自动化脚本
python scripts/init_db_direct.py
```

#### 5. ▶️ 启动应用 | Start Application
```bash
# 开发环境
python scripts/start_server.py

# 或直接启动
cd woniunote
python app.py

# 生产环境
gunicorn -w 4 -b 0.0.0.0:5000 --timeout 120 app:app
```

#### 6. ✅ 验证安装 | Verify Installation
```bash
# 基本导入测试
python -c "import woniunote.common.utils; print('✅ Installation successful!')"

# 运行快速测试
pytest tests/unit/test_common_utils.py::TestUtils::test_generate_id -v

# 访问应用
curl http://localhost:5000/health
```
</div>

<!-- English Quick Start -->
<div id="quick-start-en-content" class="content-section" style="display: none;">
#### 1. 📥 Clone Project
```bash
# Chinese users
git clone https://gitee.com/yunjinqi/woniunote.git

# International users
git clone https://github.com/cloudQuant/woniunote.git

cd woniunote
```

#### 2. 📦 Install Dependencies
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate     # Windows

# Install Python dependencies
pip install -r requirements.txt

# Install project package (development mode)
pip install -e .

# Optional: Install Playwright browser drivers
playwright install
```

#### 3. ⚙️ Database Configuration
```bash
# Copy configuration template
cp configs/user_password_config.yaml.example configs/user_password_config.yaml

# Edit configuration file
nano configs/user_password_config.yaml
```

**Configuration Example:**
```yaml
# Database Configuration
database:
  SQLALCHEMY_DATABASE_URI: mysql://username:password@localhost:3306/woniunote
  SQLALCHEMY_TRACK_MODIFICATIONS: false

# Security Configuration
SECRET_KEY: 'your-secret-key-here-change-in-production'
WTF_CSRF_SECRET_KEY: 'your-csrf-key-here'

# Redis Configuration (Optional)
redis:
  REDIS_URL: redis://localhost:6379/0

# Monitoring Configuration
monitoring:
  system_monitoring: true
  collect_interval: 30

# Cache Configuration
cache:
  default_ttl: 300
  memory_max_size: 2000
```

#### 4. 🗄️ Initialize Database
```bash
# Use automated script
python scripts/init_db_direct.py
```

#### 5. ▶️ Start Application
```bash
# Development environment
python scripts/start_server.py

# Or start directly
cd woniunote
python app.py

# Production environment
gunicorn -w 4 -b 0.0.0.0:5000 --timeout 120 app:app
```

#### 6. ✅ Verify Installation
```bash
# Basic import test
python -c "import woniunote.common.utils; print('✅ Installation successful!')"

# Run quick test
pytest tests/unit/test_common_utils.py::TestUtils::test_generate_id -v

# Access application
curl http://localhost:5000/health
```
</div>

## 🧪 测试 | Testing (100% Pass Rate)

| 🇨🇳 测试概况 | 🇺🇸 Test Overview |
|-------------|------------------|
| **测试用例数**: 300+ 个测试用例 | **Test Cases**: 300+ test cases |
| **通过率**: 100% 测试通过 | **Pass Rate**: 100% pass rate |
| **代码覆盖率**: 85%+ 代码覆盖 | **Coverage**: 85%+ code coverage |
| **测试类型**: 单元测试、集成测试、E2E测试 | **Test Types**: Unit, Integration, E2E |
| **测试框架**: pytest + 插件生态 | **Framework**: pytest + plugins |

### 🚀 快速测试 | Quick Testing
```bash
# 安装项目依赖和测试环境 | Install dependencies and test environment
pip install -r requirements.txt
pip install -e .  # 安装项目包 | Install project package

# 安装Playwright浏览器驱动 | Install Playwright browser drivers
playwright install

# 运行所有测试 | Run all tests
pytest . -v

# 运行测试并生成报告 | Run tests with reports
pytest . -v --cov=woniunote --cov-report=html --cov-report=term
```

### 测试分类运行

#### 1. 单元测试
```bash
# 运行单元测试
pytest tests/unit/ -v

# 运行特定模块测试
pytest tests/unit/test_common_utils.py -v
pytest tests/unit/test_articles_comprehensive.py -v
pytest tests/unit/test_users_comprehensive.py -v

# 运行指定测试函数
pytest tests/unit/test_common_utils.py::TestUtils::test_generate_id -v
```

#### 2. 集成测试
```bash
# 运行数据库集成测试
pytest tests/unit/test_complete_coverage.py -v

# 运行控制器集成测试
pytest tests/unit/test_*_controller_comprehensive.py -v
```

#### 3. 使用自定义测试运行器
```bash
# 使用项目自定义测试脚本
python scripts/run_tests.py

# 只运行单元测试
python scripts/run_tests.py --unit-only

# 运行特定功能测试
python scripts/run_tests.py --cards-only    # 卡片系统测试
python scripts/run_tests.py --todos-only    # 待办事项测试
python scripts/run_tests.py --model-only    # 模型验证测试
```

#### 4. 测试覆盖率报告
```bash
# 生成详细覆盖率报告
pytest . -v --cov=woniunote --cov-report=html --cov-report=term

# 生成HTML覆盖率报告
pytest . --cov=woniunote --cov-report=html
# 查看报告: open htmlcov/index.html

# 生成XML格式报告
pytest . --cov=woniunote --cov-report=xml
```

#### 5. 性能测试
```bash
# 运行性能测试
locust -f tests/test_performance.py --host=http://localhost:5000

# 运行并发测试
pytest tests/ -k "performance" -v
```

#### 6. 测试标记和过滤
```bash
# 跳过慢速测试
pytest -m "not slow" -v

# 跳过浏览器测试
pytest -m "not browser" -v

# 只运行单元测试标记
pytest -m unit -v

# 运行包含特定关键词的测试
pytest -k "test_user" -v
pytest -k "test_article" -v
pytest -k "test_cache" -v
```

### 📊 测试架构详情 | Test Architecture Details

#### 📁 测试目录结构 | Test Directory Structure
```
tests/
├── 📄 conftest.py                     # 测试配置和全局fixtures | Test config & fixtures
├── 📁 unit/                           # 单元测试 | Unit Tests
│   ├── 📄 test_common_utils.py       # 通用工具测试 (55个测试) | Utils tests
│   ├── 📄 test_articles_comprehensive.py # 文章模块测试 | Article module tests
│   ├── 📄 test_users_comprehensive.py    # 用户模块测试 | User module tests
│   ├── 📄 test_*_controller_comprehensive.py # 控制器测试 | Controller tests
│   └── 📄 test_complete_coverage.py  # 完整覆盖率测试 | Complete coverage tests
├── 📁 utils/                          # 测试工具 | Test Utilities
│   ├── 📄 app_launcher.py            # 测试应用启动器 | Test app launcher
│   ├── 📄 server_manager.py          # 测试服务器管理 | Test server manager
│   └── 📄 verify_*.py                # 验证工具 | Verification tools
└── 📁 configs/                        # 测试配置 | Test Configurations
    ├── 📄 test_config.yaml           # 测试环境配置 | Test environment config
    └── 📄 user_password_config.yaml  # 测试数据库配置 | Test database config
```

#### 🎯 测试覆盖范围 | Test Coverage Scope

| 🇨🇳 测试类型 | 🇺🇸 Test Type | 🇨🇳 覆盖内容 | 🇺🇸 Coverage | 🇨🇳 状态 | 🇺🇸 Status |
|-------------|--------------|-------------|-------------|---------|-----------|
| **单元测试** | Unit Tests | 核心模块和功能 | Core modules & functions | ✅ 100% | ✅ 100% |
| **集成测试** | Integration Tests | 数据库操作和API接口 | DB operations & APIs | ✅ 100% | ✅ 100% |
| **控制器测试** | Controller Tests | Flask路由和蓝图 | Flask routes & blueprints | ✅ 100% | ✅ 100% |
| **模型测试** | Model Tests | SQLAlchemy模型和验证 | SQLAlchemy models & validation | ✅ 100% | ✅ 100% |
| **工具测试** | Utility Tests | 缓存、日志、安全工具 | Cache, logging, security utils | ✅ 100% | ✅ 100% |
| **错误处理测试** | Error Handling Tests | 异常和边界情况 | Exceptions & edge cases | ✅ 100% | ✅ 100% |
| **性能测试** | Performance Tests | 负载测试和响应时间 | Load testing & response time | ✅ 100% | ✅ 100% |
| **安全测试** | Security Tests | 权限验证和输入检查 | Permission validation & input checks | ✅ 100% | ✅ 100% |

#### 📈 测试质量指标 | Test Quality Metrics

| 🇨🇳 指标 | 🇺🇸 Metric | 🇨🇳 值 | 🇺🇸 Value | 🇨🇳 说明 | 🇺🇸 Description |
|---------|-----------|-------|----------|---------|---------------|
| **测试用例数** | Test Cases | 300+ | 300+ | 全面覆盖所有功能 | Comprehensive coverage |
| **代码覆盖率** | Code Coverage | 85%+ | 85%+ | 核心代码高覆盖 | High core coverage |
| **通过率** | Pass Rate | 100% | 100% | 所有测试通过 | All tests pass |
| **测试速度** | Test Speed | <1s | <1s | 大部分测试快速完成 | Most tests fast |
| **Mock使用** | Mock Usage | 广泛 | Extensive | 避免外部依赖 | Avoid external deps |

#### Bug修复验证
测试套件包含对以下关键bug修复的验证:
1. **安全漏洞修复**: eval() → json.loads()
2. **线程安全修复**: 全局dict → threading.local()  
3. **资源泄漏修复**: Redis连接自动清理
4. **会话管理修复**: 安全会话处理
5. **输入验证修复**: 严格参数验证
6. **错误处理修复**: 优雅错误降级

### 测试最佳实践

#### 运行测试前的准备
```bash
# 1. 确保环境变量设置
export TESTING=1
export FLASK_ENV=testing

# 2. 安装项目包(重要!)
pip install -e .

# 3. 检查配置文件
ls configs/user_password_config.yaml

# 4. 运行基本导入测试
python -c "import woniunote.common.utils; print('导入成功')"
```

#### 调试测试
```bash
# 详细输出模式
pytest tests/unit/test_common_utils.py -v -s

# 在第一个失败时停止
pytest tests/unit/ -x

# 显示本地变量
pytest tests/unit/ --tb=long

# 运行特定失败的测试
pytest tests/unit/test_common_utils.py::TestUtils::test_generate_id --pdb
```

#### 持续集成
```bash
# CI环境测试命令
pytest . -v --cov=woniunote --cov-report=xml --junit-xml=test-results.xml

# 代码质量检查
flake8 woniunote/ tests/
black --check woniunote/ tests/
isort --check-only woniunote/ tests/
```

### 贡献测试代码

编写新测试时请遵循：
1. **命名规范**: test_功能_具体行为.py
2. **Mock使用**: 避免外部依赖，使用Mock
3. **断言清晰**: 使用描述性的断言消息
4. **测试独立**: 每个测试可独立运行
5. **覆盖边界**: 包含正常和异常情况

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

## 🎉 项目特色亮点 | Project Highlights

### 🏆 技术成就 | Technical Achievements

| 🇨🇳 成就 | 🇺🇸 Achievement | 🇨🇳 说明 | 🇺🇸 Description |
|---------|----------------|---------|---------------|
| **统一架构** | Unified Architecture | 10个统一模块，消除代码重复 | 10 unified modules, eliminate code duplication |
| **智能运维** | Intelligent Operations | 实时监控、自动优化、容量分析 | Real-time monitoring, auto optimization, capacity analysis |
| **安全防护** | Security Protection | 多层安全、JWT认证、CSRF防护 | Multi-layer security, JWT auth, CSRF protection |
| **性能优化** | Performance Optimization | 缓存系统、数据库优化、异步处理 | Caching system, DB optimization, async processing |
| **测试覆盖** | Test Coverage | 300+测试用例，100%通过率 | 300+ test cases, 100% pass rate |
| **用户体验** | User Experience | 响应式设计、智能推荐、个性化 | Responsive design, smart recommendations, personalization |

### 📈 项目统计 | Project Statistics

| 🇨🇳 统计项目 | 🇺🇸 Statistics | 🇨🇳 值 | 🇺🇸 Value |
|-------------|---------------|-------|----------|
| **总代码行数** | Total Lines of Code | 20,000+ | 20,000+ |
| **Python文件数** | Python Files | 100+ | 100+ |
| **测试用例数** | Test Cases | 300+ | 300+ |
| **功能模块数** | Feature Modules | 15+ | 15+ |
| **API端点数** | API Endpoints | 50+ | 50+ |
| **文档页面数** | Documentation Pages | 10+ | 10+ |

## 🤝 贡献指南 | Contributing

### 🚀 开发流程 | Development Workflow
1. **Fork项目** | Fork the project
2. **创建功能分支** | Create feature branch (`git checkout -b feature/AmazingFeature`)
3. **提交代码** | Commit changes (`git commit -m 'Add AmazingFeature'`)
4. **推送分支** | Push to branch (`git push origin feature/AmazingFeature`)
5. **创建Pull Request** | Open Pull Request

### 📝 代码规范 | Code Standards
- **遵循PEP 8**: Python代码规范 | Follow PEP 8 Python standards
- **类型注解**: 使用类型提示 | Use type hints
- **文档字符串**: 完整的函数文档 | Complete function documentation
- **单元测试**: 新功能必须有测试 | New features must have tests
- **代码质量**: 通过所有linting检查 | Pass all linting checks

### 🐛 问题反馈 | Issue Reporting
- **GitHub Issues**: 报告问题 | Report issues via GitHub Issues
- **详细描述**: 提供错误信息和复现步骤 | Provide detailed error info and reproduction steps
- **环境信息**: 操作系统、Python版本等 | Include OS, Python version, etc.
- **优先级标注**: 标注问题严重程度 | Label issue priority

## 📚 文档资源 | Documentation

| 🇨🇳 文档类型 | 🇺🇸 Document Type | 🇨🇳 链接 | 🇺🇸 Link |
|-------------|------------------|---------|---------|
| **API文档** | API Documentation | `docs/API_DOCUMENTATION.md` | API docs |
| **部署指南** | Deployment Guide | `docs/DEPLOYMENT_GUIDE.md` | Deployment guide |
| **迁移指南** | Migration Guide | `docs/migration_guide_*.md` | Migration guides |
| **优化计划** | Optimization Plan | `docs/common_folder_optimization_plan.md` | Optimization plan |
| **故障排除** | Troubleshooting | `TROUBLESHOOTING.md` | Troubleshooting |

## 📄 许可证 | License

本项目采用 **[MIT License](LICENSE)** 许可证开源。

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

## 👨‍💻 作者信息 | Author

| 🇨🇳 信息 | 🇺🇸 Information | 🇨🇳 值 | 🇺🇸 Value |
|---------|----------------|-------|----------|
| **作者** | Author | cloudQuant (云金杞) | cloudQuant (Yun Jinqi) |
| **邮箱** | Email | yunjinqi@gmail.com | yunjinqi@gmail.com |
| **网站** | Website | https://www.yunjinqi.top | https://www.yunjinqi.top |
| **GitHub** | GitHub | https://github.com/cloudQuant | https://github.com/cloudQuant |
| **Gitee** | Gitee | https://gitee.com/yunjinqi | https://gitee.com/yunjinqi |

## 🙏 致谢 | Acknowledgments

### ❤️ 核心贡献者 | Core Contributors
感谢所有为 WoniuNote 项目做出贡献的开发者和用户！

Special thanks to all developers and users who have contributed to the WoniuNote project!

### 🛠️ 技术栈致谢 | Technology Stack Thanks
- **Flask**: 优秀的Python Web框架 | Excellent Python web framework
- **SQLAlchemy**: 强大的ORM工具 | Powerful ORM tool
- **Redis**: 高性能缓存数据库 | High-performance caching database
- **pytest**: 完善的测试框架 | Comprehensive testing framework

## 📞 联系方式 | Contact

| 🇨🇳 联系方式 | 🇺🇸 Contact Methods | 🇨🇳 链接 | 🇺🇸 Link |
|-------------|---------------------|---------|---------|
| **项目主页** | Project Homepage | https://github.com/cloudQuant/woniunote | GitHub Repo |
| **在线演示** | Live Demo | https://www.yunjinqi.top | Live Demo |
| **问题反馈** | Issue Tracker | https://github.com/cloudQuant/woniunote/issues | GitHub Issues |
| **技术交流** | Technical Discussion | 欢迎提交PR和Issue | Welcome PRs and Issues |

---

## 🎊 总结 | Summary

**WoniuNote** 是一个功能完整、架构优良、性能优异的现代化个人博客系统。通过精心设计的统一模块架构、智能运维系统和全面的测试覆盖，项目展现了企业级应用开发的优秀实践。

**WoniuNote** is a modern personal blog system with complete features, excellent architecture, and superior performance. Through carefully designed unified modular architecture, intelligent operations system, and comprehensive test coverage, the project demonstrates excellent practices in enterprise-level application development.

---

---

## 🎊 <span id="summary-cn">总结</span><span id="summary-en" style="display: none;">Summary</span>

<!-- Chinese Summary -->
<div id="summary-cn-content" class="content-section">
**WoniuNote** 是一个功能完整、架构优良、性能优异的现代化个人博客系统。通过精心设计的统一模块架构、智能运维系统和全面的测试覆盖，项目展现了企业级应用开发的优秀实践。

**主要亮点：**
- 🏗️ **统一架构**：10个统一模块，消除代码重复
- 📊 **智能运维**：实时监控、自动优化、容量分析
- 🛡️ **安全防护**：多层安全、JWT认证、CSRF防护
- ⚡ **性能优化**：缓存系统、数据库优化、异步处理
- 🧪 **测试覆盖**：300+测试用例，100%通过率
- 🎨 **用户体验**：响应式设计、智能推荐、个性化

**技术成就：**
- 20,000+ 行代码，100+ Python文件
- 15+ 功能模块，50+ API端点
- 85%+ 代码覆盖率，100% 测试通过
- 支持MySQL/SQLite/Redis多数据库
- 完整的CI/CD和自动化部署支持

如果这个项目对你有帮助，欢迎给它一个 ⭐ 星标！

📧 **联系我们**: [yunjinqi@gmail.com](mailto:yunjinqi@gmail.com)
🌐 **项目主页**: [GitHub](https://github.com/cloudQuant/woniunote) | [Gitee](https://gitee.com/yunjinqi)
</div>

<!-- English Summary -->
<div id="summary-en-content" class="content-section" style="display: none;">
**WoniuNote** is a modern personal blog system with complete features, excellent architecture, and superior performance. Through carefully designed unified modular architecture, intelligent operations system, and comprehensive test coverage, the project demonstrates excellent practices in enterprise-level application development.

**Key Highlights:**
- 🏗️ **Unified Architecture**: 10 unified modules, eliminate code duplication
- 📊 **Intelligent Operations**: Real-time monitoring, auto optimization, capacity analysis
- 🛡️ **Security Protection**: Multi-layer security, JWT authentication, CSRF protection
- ⚡ **Performance Optimization**: Caching system, database optimization, async processing
- 🧪 **Test Coverage**: 300+ test cases, 100% pass rate
- 🎨 **User Experience**: Responsive design, smart recommendations, personalization

**Technical Achievements:**
- 20,000+ lines of code, 100+ Python files
- 15+ feature modules, 50+ API endpoints
- 85%+ code coverage, 100% test pass rate
- Support MySQL/SQLite/Redis multi-database
- Complete CI/CD and automated deployment support

If this project helps you, please give it a ⭐ star!

📧 **Contact Us**: [yunjinqi@gmail.com](mailto:yunjinqi@gmail.com)
🌐 **Project Homepage**: [GitHub](https://github.com/cloudQuant/woniunote) | [Gitee](https://gitee.com/yunjinqi)
</div>

---

⭐ **如果这个项目对你有帮助，请给它一个星标！**  
⭐ **If this project helps you, please give it a star!**



