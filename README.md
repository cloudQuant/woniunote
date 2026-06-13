# WoniuNote - 云子量化博客系统

<div align="center">

[![C++](https://img.shields.io/badge/C++-17+-00599C.svg)](https://isocpp.org/)
[![Drogon](https://img.shields.io/badge/Drogon-1.9+-blue.svg)](https://github.com/drogonframework/drogon)
[![Vue](https://img.shields.io/badge/Vue-3.4+-4FC08D.svg)](https://vuejs.org/)
[![Element Plus](https://img.shields.io/badge/Element%20Plus-2.5+-409EFF.svg)](https://element-plus.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**高性能前后端分离的个人博客系统，基于 C++ Drogon + Vue 3 + Element Plus**

🌐 **在线演示**: [https://www.yunjinqi.top](https://www.yunjinqi.top)

[中文](#-项目简介) | [English](#-english-version)

</div>

---

## 📖 项目简介

WoniuNote（蜗牛笔记）是一个博客系统，采用**前后端分离架构**，使用高性能 C++ 后端，提供文章发布、用户管理、评论互动、数学训练等完整功能。

### 🎯 技术架构

| 层级 | 技术栈 | 说明 |
|------|--------|------|
| **前端** | Vue 3 + Vite 5 + Element Plus + Pinia | 现代化 SPA 单页应用 |
| **后端** | C++ 17 + Drogon + JWT + bcrypt | 高性能异步 API 服务 |
| **数据库** | MySQL 8.0 + Redis | 持久化存储 + 缓存加速 |
| **部署** | Nginx + HTTPS + systemd | 生产环境部署 |

---

## 🌟 项目特色

- **高性能后端** - C++ Drogon 框架，比 Python 快 5-10 倍，低延迟高吞吐
- **前后端分离** - Vue 3 SPA + RESTful API，开发部署灵活
- **安全防护** - JWT 认证、bcrypt 密码加密、CORS 保护、API 限流
- **现代 UI** - Element Plus 组件库、响应式设计
- **丰富功能** - 文章管理、用户系统、评论互动、数学训练
- **生产就绪** - Nginx + HTTPS、systemd 服务管理、完整部署脚本

---

## 🏗️ 项目结构

```
woniunote/
├── 📁 backend_cpp/                  # C++ 后端服务 (Drogon)
│   ├── main.cc                      # 应用入口
│   ├── config.json                  # 开发环境配置
│   ├── config.prod.json             # 生产环境配置
│   ├── CMakeLists.txt               # CMake 构建配置
│   ├── vcpkg.json                   # vcpkg 依赖清单
│   ├── controllers/                 # API 控制器
│   │   ├── AuthController           # 认证 (登录/注册/登出)
│   │   ├── ArticleController        # 文章 (CRUD/搜索/分类)
│   │   ├── CommentController        # 评论 (评论/回复/投票)
│   │   ├── FavoriteController       # 收藏管理
│   │   ├── UserController           # 用户信息
│   │   ├── AdminController          # 管理后台
│   │   ├── UploadController         # 文件上传
│   │   ├── CreditController         # 积分系统
│   │   ├── CaptchaController        # 验证码
│   │   ├── MathTrainingController   # 数学训练
│   │   └── SystemController         # 系统状态
│   ├── core/                        # 核心模块
│   │   ├── config.h/cc              # 配置加载
│   │   ├── database.h/cc            # 数据库工具
│   │   ├── security.h/cc            # JWT + bcrypt
│   │   └── logger.h/cc              # 日志工具
│   ├── models/                      # 数据模型
│   └── filters/                     # 中间件 (认证/限流)
│
├── 📁 frontend/                     # Vue 3 前端应用
│   ├── src/
│   │   ├── api/                     # Axios API 封装
│   │   ├── components/              # 公共组件
│   │   ├── views/                   # 页面视图
│   │   │   ├── Home.vue             # 首页
│   │   │   ├── ArticleDetail.vue    # 文章详情
│   │   │   ├── Category.vue         # 分类页
│   │   │   ├── Search.vue           # 搜索页
│   │   │   ├── WriteArticle.vue     # 写文章
│   │   │   ├── UserCenter.vue       # 用户中心
│   │   │   ├── MathTraining.vue     # 数学训练
│   │   │   ├── Login.vue            # 登录
│   │   │   ├── Register.vue         # 注册
│   │   │   └── admin/               # 管理后台
│   │   ├── stores/                  # Pinia 状态管理
│   │   ├── router/                  # Vue Router 路由
│   │   └── main.js                  # 入口文件
│   ├── package.json                 # Node.js 依赖
│   └── vite.config.js               # Vite 构建配置
│
├── 📁 scripts/                      # 部署和管理脚本
│   ├── setup_ubuntu.sh              # Ubuntu 环境配置
│   ├── start_prod.sh                # 启动生产服务
│   ├── stop_prod.sh                 # 停止服务
│   ├── update_nginx_ssl.sh          # 更新 Nginx 配置
│   └── sql/                         # 数据库脚本
│
├── 📁 configs/                      # 配置文件
│   ├── woniunote_nginx_prod.conf    # Nginx 生产配置
│   └── yunjinqi.top_nginx/          # 本地/服务器 SSL 证书目录（不入库）
│
├── 📁 tests/                        # 旧 Flask 测试归档（非当前主线门禁）
├── 📁 docs/                         # 项目文档
├── start_app.sh                     # 一键启动脚本
├── stop_app.sh                      # 停止脚本
└── restart_app.sh                   # 重启脚本
```

---

## 🚀 快速开始

### 环境要求

| 组件 | 版本 | 必需 |
|------|------|------|
| C++ 编译器 | GCC 10+ / Clang 13+ / MSVC 2019+ | ✅ |
| CMake | 3.20+ | ✅ |
| vcpkg | 最新版 | ✅ |
| Node.js | 18+ | ✅ |
| MySQL | 8.0+ | ✅ |
| Redis | 6.0+ | ❌ (可选，推荐) |

### 方式一：一键启动（推荐）

```bash
# 克隆项目
git clone https://github.com/cloudQuant/woniunote.git
cd woniunote

# 开发模式 (前端热重载)
bash start_app.sh dev

# 生产模式 (构建前端 + Nginx 服务)
bash start_app.sh prod

# 访问
# 前端: http://localhost:8888
# 后端 API: http://localhost:5173
```

### 方式二：手动启动

#### 1. 编译并启动后端

```bash
cd backend_cpp

# 安装 vcpkg (如未安装)
git clone https://github.com/microsoft/vcpkg.git ~/vcpkg
~/vcpkg/bootstrap-vcpkg.sh

# 编译
mkdir build && cd build
cmake .. -DCMAKE_TOOLCHAIN_FILE=~/vcpkg/scripts/buildsystems/vcpkg.cmake
cmake --build . --config Release -j8

# 配置数据库连接
cp ../config.json .
# 编辑 config.json 设置数据库密码等

# 启动
./woniunote_backend
# 后端运行在 http://localhost:5173
```

#### 2. 启动前端

```bash
cd frontend

# 安装依赖
npm install

# 开发模式
npm run dev
# 访问: http://localhost:8888

# 生产构建
npm run build
```

### 方式三：生产环境部署 (Ubuntu 22.04 + HTTPS)

#### 1. 运行环境配置脚本

```bash
# 需要 root 权限
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
mysql -u root -p

CREATE DATABASE woniunote CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'woniunote_user'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON woniunote.* TO 'woniunote_user'@'localhost';
FLUSH PRIVILEGES;
```

#### 3. 配置并启动

```bash
# 编辑生产配置
nano backend_cpp/config.prod.json

# 更新 Nginx 配置
sudo bash scripts/update_nginx_ssl.sh

# 启动服务
bash restart_app.sh prod
```

**访问地址**: https://www.yunjinqi.top

---

## 🔧 核心功能

### 📝 内容管理
- **文章系统** - 支持原创/转载/翻译，富文本编辑器 (UEditor)
- **分类管理** - 多级分类、灵活的文章归类
- **搜索功能** - 关键词搜索、分类筛选

### 👥 用户系统
- **认证授权** - JWT Token 认证、bcrypt 密码加密
- **用户注册** - 验证码保护
- **个人中心** - 资料管理、头像上传、密码修改
- **角色权限** - 普通用户/管理员

### 💬 互动功能
- **评论系统** - 文章评论、多级回复、点赞
- **收藏功能** - 收藏文章、收藏管理
- **积分系统** - 用户活跃度积分

### 🧮 数学训练
- **口算练习** - 加减乘除四则运算
- **难度分级** - 多难度级别
- **成绩记录** - 答题统计

### 🛠️ 管理后台
- **文章审核** - 待审核文章管理
- **用户管理** - 用户列表、权限控制
- **系统监控** - 健康检查、数据库状态
- **数据统计** - 访问量、文章统计

---

## 🛠️ 技术栈

### 后端技术 (C++)

| 技术 | 说明 |
|------|------|
| **Drogon** | 高性能 C++ 异步 Web 框架 |
| **jwt-cpp** | JWT Token 认证 |
| **OpenSSL** | 加密、bcrypt 密码哈希 |
| **jsoncpp** | JSON 解析 |
| **hiredis** | Redis 客户端 |
| **libmariadb** | MySQL 客户端 |
| **spdlog** | 高性能日志库 |

### 前端技术

| 技术 | 说明 |
|------|------|
| **Vue 3.4** | 渐进式 JavaScript 框架 |
| **Vite 5** | 下一代前端构建工具 |
| **Element Plus 2.5** | Vue 3 UI 组件库 |
| **Pinia** | Vue 3 状态管理 |
| **Vue Router** | 官方路由管理器 |
| **Axios** | HTTP 请求库 |

### 基础设施

| 组件 | 说明 |
|------|------|
| **MySQL 8.0** | 主数据库 |
| **Redis 6.0+** | 缓存、限流 |
| **Nginx** | 反向代理、HTTPS、静态资源 |
| **vcpkg** | C++ 包管理器 |

---

## 🧪 测试

当前发布门禁以 C++ Drogon 后端与 Vue 前端为准。根目录 `tests/` 是旧 Flask 栈测试归档，不再作为当前主线覆盖率来源。

```bash
# 后端 C++ 单元测试
cd backend_cpp/build
ctest --output-on-failure

# 后端 HTTP 集成测试（需要测试 MySQL/Redis）
cd ../..
bash backend_cpp/tests/integration/run_integration.sh

# 前端 lint / 单测覆盖率 / 构建 / E2E
cd frontend
npm run lint:ci
npm run test:coverage
npm run build
npm run test:e2e

# 前端生产依赖安全审计
npm audit --omit=dev --audit-level=moderate
```

---

## 📚 API 文档

### 主要 API 端点

| 模块 | 端点 | 说明 |
|------|------|------|
| **认证** | `/api/auth/login`, `/api/auth/register`, `/api/auth/logout` | 登录/注册/登出 |
| **用户** | `/api/auth/me`, `/api/users/{id}`, `/api/users/profile`, `/api/users/password` | 用户信息/资料/密码 |
| **文章** | `/api/articles`, `/api/articles/{id}`, `/api/articles/hot`, `/api/articles/types` | 文章 CRUD/列表/分类 |
| **评论** | `/api/comments/article/{id}`, `/api/comments`, `/api/comments/{id}/vote` | 评论/回复/点赞 |
| **收藏** | `/api/favorites`, `/api/favorites/{articleId}`, `/api/favorites/check/{articleId}` | 收藏管理 |
| **积分** | `/api/credits/balance`, `/api/credits/history`, `/api/credits/pay-article/{id}` | 积分查询/支付 |
| **数学** | `/api/math-training/records`, `/api/math-training/wrong-answers`, `/api/math-training/summary` | 数学训练 |
| **上传** | `/api/upload/image`, `/api/upload/file`, `/api/upload/avatar` | 文件上传 |
| **验证码** | `/api/captcha/generate`, `/api/captcha/verify` | 验证码 |
| **管理** | `/api/admin/stats`, `/api/admin/users`, `/api/admin/articles` | 管理后台 |
| **系统** | `/api/system/health`, `/api/system/status` | 健康检查 |

---

## 🤝 贡献指南

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 提交 Pull Request

### 开发规范

- 后端遵循 C++17 / Drogon 现有控制器、模型、过滤器组织方式
- 前端遵循 Vue 3 Composition API 风格
- 提交前运行当前主线测试和代码检查（见“测试”章节）
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

WoniuNote is a high-performance personal blog system for quantitative investment, built with **C++ Drogon + Vue 3 + Element Plus** using a frontend-backend separation architecture.

### Features

- **High Performance** - C++ Drogon framework, 5-10x faster than Python
- **Modern Frontend** - Vue 3 SPA + Element Plus
- **Security** - JWT authentication, bcrypt password hashing, rate limiting
- **Rich Features** - Articles, comments, favorites, math training
- **Production Ready** - Nginx + HTTPS, systemd service management

### Quick Start

```bash
# Clone
git clone https://github.com/cloudQuant/woniunote.git
cd woniunote

# Development mode
bash start_app.sh dev

# Production mode
bash start_app.sh prod

# Frontend: http://localhost:8888
# Backend API: http://localhost:5173
```

### Tech Stack

| Layer | Technologies |
|-------|-------------|
| **Frontend** | Vue 3.4 + Vite 5 + Element Plus + Pinia |
| **Backend** | C++ 17 + Drogon + JWT + bcrypt |
| **Database** | MySQL 8.0 + Redis |
| **Deployment** | Nginx + HTTPS + systemd |

### API Endpoints

| Module | Endpoints | Description |
|--------|-----------|-------------|
| Auth | `/api/auth/*` | Login, Register, Logout |
| Articles | `/api/article/*` | CRUD, Search, Categories |
| Comments | `/api/comment/*` | Comment, Reply, Vote |
| Favorites | `/api/favorite/*` | Bookmark management |
| Users | `/api/user/*` | User profile |
| Math | `/api/math/*` | Math training |
| Admin | `/api/admin/*` | Admin dashboard |

### License

MIT License - see [LICENSE](LICENSE) for details.

---

⭐ 如果这个项目对你有帮助，请给一个 Star！

⭐ If this project helps you, please give it a star!
