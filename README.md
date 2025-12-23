# WoniuNote - 云子量化博客系统

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688.svg)](https://fastapi.tiangolo.com/)
[![Vue](https://img.shields.io/badge/Vue-3.0+-4FC08D.svg)](https://vuejs.org/)
[![Element Plus](https://img.shields.io/badge/Element%20Plus-2.0+-409EFF.svg)](https://element-plus.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**现代化前后端分离的个人博客系统，基于 FastAPI + Vue 3 + Element Plus**

🌐 **在线演示**: [yunjinqi.top](http://yunjinqi.top)

[中文](#-项目简介) | [English](#-english-version)

</div>

---

## 📖 项目简介

WoniuNote（蜗牛笔记）是一个面向量化投资领域的个人博客系统，采用**前后端分离架构**，提供文章发布、用户管理、评论互动、待办事项、卡片管理等完整功能。

### 🎯 技术架构

| 层级 | 技术栈 | 说明 |
|------|--------|------|
| **前端** | Vue 3 + Vite + Element Plus + Pinia | 现代化 SPA 单页应用 |
| **后端** | FastAPI + SQLAlchemy + Pydantic | 高性能异步 API 服务 |
| **数据库** | MySQL 8.0 + Redis | 持久化存储 + 缓存加速 |
| **部署** | Docker + Nginx | 容器化部署 |

---

## 🌟 项目特色

- **前后端分离** - Vue 3 SPA + FastAPI RESTful API，开发效率高
- **高性能优化** - 异步 SQLAlchemy、Redis 缓存、数据库连接池
- **安全防护** - JWT 认证、CORS 保护、输入验证、API 限流
- **现代 UI** - Element Plus 组件库、响应式设计、深色模式支持
- **丰富功能** - 文章管理、用户系统、评论互动、待办事项、卡片系统
- **开发友好** - 自动生成 API 文档、完整测试套件、Docker 一键部署

---

## 🏗️ 项目结构

```
woniunote/
├── 📁 backend/                      # FastAPI 后端服务
│   ├── app/
│   │   ├── api/                     # API 路由模块
│   │   │   ├── auth.py              # 认证接口 (登录/注册/登出)
│   │   │   ├── articles.py          # 文章接口 (CRUD/搜索/分类)
│   │   │   ├── comments.py          # 评论接口 (评论/回复)
│   │   │   ├── favorites.py         # 收藏接口
│   │   │   ├── users.py             # 用户接口 (个人信息)
│   │   │   ├── admin.py             # 管理接口 (后台管理)
│   │   │   ├── todos.py             # 待办事项接口
│   │   │   ├── cards.py             # 卡片管理接口
│   │   │   ├── credits.py           # 积分系统接口
│   │   │   ├── upload.py            # 文件上传接口
│   │   │   └── ueditor.py           # 富文本编辑器接口
│   │   ├── core/                    # 核心模块
│   │   │   ├── config.py            # 应用配置
│   │   │   ├── database.py          # 数据库连接
│   │   │   ├── security.py          # 安全工具 (JWT/密码)
│   │   │   └── redis.py             # Redis 连接
│   │   ├── models/                  # SQLAlchemy 数据模型
│   │   ├── schemas/                 # Pydantic 请求/响应模型
│   │   └── main.py                  # FastAPI 应用入口
│   ├── requirements.txt             # Python 依赖
│   └── Dockerfile                   # 后端容器配置
│
├── 📁 frontend/                     # Vue 3 前端应用
│   ├── src/
│   │   ├── api/                     # Axios API 封装
│   │   ├── components/              # 公共组件
│   │   │   ├── layout/              # 布局组件 (Header/Footer/Sidebar)
│   │   │   ├── article/             # 文章组件 (列表/卡片/详情)
│   │   │   └── sidebar/             # 侧边栏组件
│   │   ├── views/                   # 页面视图
│   │   │   ├── Home.vue             # 首页
│   │   │   ├── ArticleDetail.vue    # 文章详情
│   │   │   ├── Category.vue         # 分类页
│   │   │   ├── Search.vue           # 搜索页
│   │   │   ├── WriteArticle.vue     # 写文章
│   │   │   ├── UserCenter.vue       # 用户中心
│   │   │   ├── Todo.vue             # 待办事项
│   │   │   ├── Cards.vue            # 卡片管理
│   │   │   ├── user/                # 用户相关页面
│   │   │   └── admin/               # 管理后台页面
│   │   ├── stores/                  # Pinia 状态管理
│   │   ├── router/                  # Vue Router 路由配置
│   │   ├── App.vue                  # 根组件
│   │   └── main.js                  # 入口文件
│   ├── package.json                 # Node.js 依赖
│   ├── vite.config.js               # Vite 构建配置
│   └── Dockerfile.new               # 前端容器配置
│
├── 📁 tests/                        # 测试套件
│   ├── unit/                        # 单元测试
│   ├── integration/                 # 集成测试
│   ├── functional/                  # 功能测试
│   └── security/                    # 安全测试
│
├── 📁 configs/                      # 配置文件
├── 📁 docs/                         # 项目文档
├── 📁 scripts/                      # 工具脚本
├── docker-compose.new.yml           # Docker 编排文件
└── README.md                        # 项目说明
```

---

## 🚀 快速开始

### 环境要求

| 组件 | 版本 | 必需 |
|------|------|------|
| Python | 3.8+ | ✅ |
| Node.js | 16+ | ✅ |
| MySQL | 5.7+ | ✅ |
| Redis | 4.0+ | ❌ (可选，推荐) |

### 方式一：Docker 部署（推荐）

```bash
# 克隆项目
git clone https://github.com/cloudQuant/woniunote.git
cd woniunote

# 一键启动所有服务
docker-compose -f docker-compose.new.yml up -d

# 访问
# 前端: http://localhost
# 后端 API: http://localhost:5173
# API 文档: http://localhost:5173/docs
```

### 方式二：本地开发

#### 1. 启动后端

```bash
cd backend

# 创建虚拟环境
python -m venv venv
# Windows
.\venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件配置数据库连接等

# 启动开发服务器
uvicorn app.main:app --reload --host 0.0.0.0 --port 5173

# API 文档: http://localhost:5173/docs
```

#### 2. 启动前端

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev

# 访问: http://localhost:8888
```

### 方式三：传统一键启动

```bash
# Windows
start_app.bat

# Linux/Mac
chmod +x start_app.sh && ./start_app.sh
```

### 方式四：生产环境部署 (Ubuntu 22.04 + HTTPS)

#### 1. 配置生产环境

```bash
# 运行环境配置脚本 (需要 root 权限)
sudo bash scripts/setup_ubuntu.sh
```

此脚本会自动安装:
- 系统依赖 (build-essential, cmake, nginx 等)
- MySQL 8.0 和 Redis
- Node.js 18.x
- vcpkg 和 C++ 依赖包
- 编译 C++ 后端

#### 2. 配置数据库

```bash
# 登录 MySQL
mysql -u root -p

# 创建数据库和用户
CREATE DATABASE woniunote CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'woniunote_user'@'localhost' IDENTIFIED BY 'your_secure_password';
GRANT ALL PRIVILEGES ON woniunote.* TO 'woniunote_user'@'localhost';
FLUSH PRIVILEGES;
```

#### 3. 配置 SSL 证书 (HTTPS)

```bash
# 使用 Let's Encrypt 获取免费证书
sudo apt install certbot python3-certbot-nginx
sudo certbot certonly --nginx -d yunjinqi.top -d www.yunjinqi.top
```

#### 4. 配置 Nginx

```bash
# 复制生产环境 Nginx 配置
sudo cp configs/woniunote_nginx_prod.conf /etc/nginx/sites-available/woniunote
sudo ln -s /etc/nginx/sites-available/woniunote /etc/nginx/sites-enabled/

# 测试并重载配置
sudo nginx -t && sudo systemctl reload nginx
```

#### 5. 修改生产配置

```bash
# 编辑生产配置文件
nano backend_cpp/config.prod.json
# 修改数据库密码、JWT 密钥等敏感信息
```

#### 6. 构建前端

```bash
cd frontend
npm install
npm run build
# 将 dist 目录部署到 /var/www/woniunote/frontend/dist
sudo mkdir -p /var/www/woniunote/frontend
sudo cp -r dist /var/www/woniunote/frontend/
```

#### 7. 启动服务

```bash
# 启动生产服务
sudo bash scripts/start_prod.sh

# 停止服务
sudo bash scripts/stop_prod.sh

# 重启服务
sudo bash scripts/restart_prod.sh
```

**访问地址**: https://www.yunjinqi.top

---

## 🔧 核心功能

### 📝 内容管理
- **文章系统** - 支持原创/转载/翻译，Markdown 和富文本编辑
- **分类管理** - 多级分类、灵活的文章归类
- **搜索功能** - 关键词搜索、分类筛选

### 👥 用户系统
- **认证授权** - JWT Token 认证、安全登录登出
- **用户注册** - 邮箱验证、验证码保护
- **个人中心** - 资料管理、头像上传、密码修改
- **角色权限** - 普通用户/编辑/管理员多角色

### 💬 互动功能
- **评论系统** - 文章评论、多级回复
- **收藏功能** - 收藏文章、收藏管理
- **积分系统** - 用户活跃度积分

### � 扩展功能
- **待办事项** - 个人任务管理、完成状态追踪
- **卡片系统** - 信息卡片管理、快捷记录

### �️ 管理后台
- **文章审核** - 待审核文章管理
- **用户管理** - 用户列表、权限控制
- **系统监控** - 运行状态监控
- **数据统计** - 访问量、文章统计

---

## 🛠️ 技术栈

### 后端技术

| 技术 | 说明 |
|------|------|
| **FastAPI** | 高性能异步 Python Web 框架 |
| **SQLAlchemy** | ORM 数据库操作 |
| **Pydantic** | 数据验证和序列化 |
| **PyJWT** | JWT Token 认证 |
| **asyncmy** | MySQL 异步驱动 |
| **aioredis** | Redis 异步客户端 |

### 前端技术

| 技术 | 说明 |
|------|------|
| **Vue 3** | 渐进式 JavaScript 框架 |
| **Vite** | 下一代前端构建工具 |
| **Element Plus** | Vue 3 UI 组件库 |
| **Pinia** | Vue 3 状态管理 |
| **Vue Router** | 官方路由管理器 |
| **Axios** | HTTP 请求库 |

### 基础设施

| 组件 | 说明 |
|------|------|
| **MySQL 8.0** | 主数据库 |
| **Redis** | 缓存、会话存储 |
| **Nginx** | 反向代理、静态资源服务 |
| **Docker** | 容器化部署 |

---

## 🧪 测试

```bash
# 运行所有测试
pytest tests/ -v

# 运行单元测试
pytest tests/unit/ -v

# 运行集成测试
pytest tests/integration/ -v

# 查看覆盖率报告
pytest tests/ --cov=backend --cov-report=html
```

---

## 📚 API 文档

后端启动后自动生成交互式 API 文档：

- **Swagger UI**: http://localhost:5173/docs
- **ReDoc**: http://localhost:5173/redoc

### 主要 API 端点

| 模块 | 端点 | 方法 | 说明 |
|------|------|------|------|
| **认证** | `/api/auth/login` | POST | 用户登录 |
| | `/api/auth/register` | POST | 用户注册 |
| | `/api/auth/logout` | POST | 用户登出 |
| **文章** | `/api/articles/` | GET | 文章列表 |
| | `/api/articles/{id}` | GET | 文章详情 |
| | `/api/articles/` | POST | 创建文章 |
| | `/api/articles/{id}` | PUT | 更新文章 |
| | `/api/articles/{id}` | DELETE | 删除文章 |
| **评论** | `/api/comments/` | GET | 评论列表 |
| | `/api/comments/` | POST | 发表评论 |
| **收藏** | `/api/favorites/` | GET | 收藏列表 |
| | `/api/favorites/` | POST | 添加收藏 |
| **用户** | `/api/users/me` | GET | 当前用户信息 |
| | `/api/users/me` | PUT | 更新用户信息 |
| **待办** | `/api/todos/` | GET/POST | 待办事项管理 |
| **卡片** | `/api/cards/` | GET/POST | 卡片管理 |
| **管理** | `/api/admin/*` | - | 管理后台接口 |

---

## 🤝 贡献指南

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 提交 Pull Request

### 开发规范

- 遵循 PEP 8 Python 代码规范
- 前端遵循 Vue 3 Composition API 风格
- 提交前运行测试和代码检查
- 添加适当的注释和文档

---

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

---

## 📧 联系方式

- **作者**: yunjinqi (云金杞)
- **邮箱**: yunjinqi@gmail.com
- **网站**: [yunjinqi.top](http://yunjinqi.top)
- **GitHub**: [github.com/cloudQuant](https://github.com/cloudQuant)

---

## 🌐 English Version

### Overview

WoniuNote is a modern personal blog system for quantitative investment, built with **FastAPI + Vue 3 + Element Plus** using a frontend-backend separation architecture.

### Features

- **Modern Architecture** - Vue 3 SPA + FastAPI RESTful API
- **High Performance** - Async SQLAlchemy, Redis caching
- **Security** - JWT authentication, CORS protection, input validation
- **Rich Features** - Articles, comments, favorites, todos, cards management
- **Developer Friendly** - Auto-generated API docs, Docker deployment

### Quick Start

```bash
# Clone
git clone https://github.com/cloudQuant/woniunote.git
cd woniunote

# Option 1: Docker (Recommended)
docker-compose -f docker-compose.new.yml up -d
# Frontend: http://localhost
# API Docs: http://localhost:5173/docs

# Option 2: Local Development
# Backend
cd backend && pip install -r requirements.txt
uvicorn app.main:app --reload --port 5173

# Frontend (new terminal)
cd frontend && npm install && npm run dev
# Visit: http://localhost:8888
```

### Tech Stack

| Layer | Technologies |
|-------|-------------|
| **Frontend** | Vue 3 + Vite + Element Plus + Pinia |
| **Backend** | FastAPI + SQLAlchemy + Pydantic + JWT |
| **Database** | MySQL 8.0 + Redis |
| **Deployment** | Docker + Nginx |

### API Endpoints

| Module | Endpoint | Description |
|--------|----------|-------------|
| Auth | `/api/auth/*` | Login, Register, Logout |
| Articles | `/api/articles/*` | CRUD, Search, Categories |
| Comments | `/api/comments/*` | Comment, Reply |
| Favorites | `/api/favorites/*` | Bookmark management |
| Users | `/api/users/*` | User profile |
| Todos | `/api/todos/*` | Task management |
| Cards | `/api/cards/*` | Card management |

### License

MIT License - see [LICENSE](LICENSE) for details.

---

⭐ 如果这个项目对你有帮助，请给一个 Star！

⭐ If this project helps you, please give it a star!
