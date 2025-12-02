# WoniuNote - 云子量化博客系统

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-2.0+-green.svg)](https://flask.palletsprojects.com/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688.svg)](https://fastapi.tiangolo.com/)
[![Vue](https://img.shields.io/badge/Vue-3.0+-4FC08D.svg)](https://vuejs.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**一个功能丰富的个人博客系统，支持传统 Flask 架构和现代化前后端分离架构**

🌐 **在线演示**: [yunjinqi.top](http://yunjinqi.top)

[中文](#-项目简介) | [English](#-english-version)

</div>

---

## 📖 项目简介

WoniuNote（蜗牛笔记）是一个面向量化投资领域的个人博客系统，提供文章发布、用户管理、评论互动等完整的博客功能。

### 🎯 双轨架构

项目采用**双轨架构**设计，两套架构共享同一数据库：

| 架构 | 目录 | 技术栈 | 适用场景 |
|------|------|--------|----------|
| **传统架构** | `woniunote/` | Flask + Jinja2 + Bootstrap | 快速部署、SEO友好、服务端渲染 |
| **现代架构** | `backend/` + `frontend/` | FastAPI + Vue 3 + Element Plus | 前后端分离、高性能API、SPA体验 |

---

## 🌟 项目特色

- **双轨架构** - 同时支持传统 Flask 和现代 FastAPI + Vue 3 架构
- **高性能优化** - Redis 缓存、数据库连接池、异步任务处理
- **安全防护** - JWT 认证、CSRF 保护、输入验证、限流保护
- **用户体验** - 响应式设计、Element Plus UI、智能搜索
- **开发友好** - 完整测试套件（100+ 测试用例）、API 文档自动生成
- **运维支持** - 统一日志系统、性能监控、数据库优化器

---

## 🏗️ 项目结构

```
woniunote/
├── 📁 backend/                      # FastAPI 后端 (现代架构)
│   ├── app/
│   │   ├── api/                     # API 路由 (auth, articles, comments, users...)
│   │   ├── core/                    # 核心配置 (config, database, security)
│   │   ├── models/                  # SQLAlchemy 模型
│   │   ├── schemas/                 # Pydantic Schema
│   │   └── main.py                  # FastAPI 入口
│   └── requirements.txt
│
├── 📁 frontend/                     # Vue 3 前端 (现代架构)
│   ├── src/
│   │   ├── api/                     # Axios API 封装
│   │   ├── components/              # Vue 组件 (layout, article, sidebar)
│   │   ├── views/                   # 页面视图 (Home, ArticleDetail, UserCenter, admin/)
│   │   ├── stores/                  # Pinia 状态管理
│   │   └── router/                  # Vue Router
│   └── package.json
│
├── 📁 woniunote/                    # Flask 后端 (传统架构)
│   ├── app.py                       # Flask 应用入口
│   ├── controller/                  # 控制器 (admin, article, user, ucenter...)
│   ├── module/                      # 业务逻辑 (articles, users, comments...)
│   ├── common/                      # 公共模块 (缓存、日志、安全、监控...)
│   ├── template/                    # Jinja2 模板
│   └── resource/                    # 静态资源 (css, js, ueditor)
│
├── 📁 tests/                        # 测试套件 (unit, integration, security)
├── 📁 configs/                      # 配置文件
├── 📁 docs/                         # 项目文档
├── 📁 scripts/                      # 开发脚本
├── start_app.bat / .sh              # 启动脚本
└── stop_app.bat / .sh               # 停止脚本
```

---

## 🚀 快速开始

### 环境要求

| 组件 | 版本 | 必需 |
|------|------|------|
| Python | 3.8+ | ✅ |
| Node.js | 16+ | ✅ (现代架构) |
| MySQL | 5.7+ | ✅ |
| Redis | 4.0+ | ❌ (可选) |

### 方式一：一键启动（推荐）

```bash
# Windows
start_app.bat

# Linux/Mac
chmod +x start_app.sh && ./start_app.sh
```

### 方式二：手动启动

#### 传统架构 (Flask)

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置数据库
cp configs/user_password_config.yaml.example configs/user_password_config.yaml
# 编辑配置文件...

# 3. 启动应用
cd woniunote && python app.py
# 访问: http://localhost:5000
```

#### 现代架构 (FastAPI + Vue)

```bash
# 后端
cd backend
pip install -r requirements.txt
cp .env.example .env  # 编辑配置
uvicorn app.main:app --reload --port 8001
# API文档: http://localhost:8001/docs

# 前端 (新终端)
cd frontend
npm install
npm run dev
# 访问: http://localhost:5173
```

---

## 🔧 核心功能

### 📝 内容管理
- 文章发布（原创/转载/翻译）
- 富文本编辑器（UEditor）
- 分类管理、标签系统
- 草稿箱、定时发布

### 👥 用户系统
- 注册登录（邮箱验证）
- JWT Token 认证
- 角色权限管理（用户/编辑/管理员）
- 个人中心、头像上传

### 💬 互动功能
- 文章评论、回复
- 收藏文章
- 点赞推荐

### 🛠️ 管理后台
- 文章审核管理
- 用户管理
- 系统监控
- 数据统计

---

## 🛠️ 技术栈

### 后端

| 传统架构 | 现代架构 |
|----------|----------|
| Flask 2.0+ | FastAPI 0.100+ |
| Jinja2 模板 | Pydantic Schema |
| Flask-Session | JWT 认证 |
| SQLAlchemy ORM | Async SQLAlchemy |

### 前端

| 传统架构 | 现代架构 |
|----------|----------|
| Bootstrap 4 | Vue 3 |
| jQuery | Element Plus |
| 服务端渲染 | Vite + SPA |

### 基础设施

- **数据库**: MySQL / SQLite
- **缓存**: Redis
- **文件存储**: 本地 / 对象存储
- **部署**: Docker / Gunicorn + Nginx

---

## 🧪 测试

```bash
# 运行所有测试
pytest tests/ -v

# 运行单元测试
pytest tests/unit/ -v

# 查看覆盖率
pytest tests/ --cov=woniunote --cov-report=html
```

---

## 📚 API 文档

现代架构启动后自动生成：
- **Swagger UI**: http://localhost:8001/docs
- **ReDoc**: http://localhost:8001/redoc

主要 API 端点：

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/auth/login` | POST | 用户登录 |
| `/api/auth/register` | POST | 用户注册 |
| `/api/articles/` | GET | 文章列表 |
| `/api/articles/{id}` | GET | 文章详情 |
| `/api/articles/` | POST | 创建文章 |
| `/api/comments/` | GET/POST | 评论管理 |
| `/api/favorites/` | GET/POST | 收藏管理 |

---

## 🤝 贡献指南

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 提交 Pull Request

---

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

---

## 📧 联系方式

- **作者**: yunjinqi
- **邮箱**: yunjinqi@qq.com
- **网站**: [yunjinqi.top](http://yunjinqi.top)

---

## 🌐 English Version

### Overview

WoniuNote is a feature-rich personal blog system for quantitative investment, supporting both traditional Flask architecture and modern FastAPI + Vue 3 architecture.

### Quick Start

```bash
# Clone
git clone https://github.com/cloudQuant/woniunote.git
cd woniunote

# Option 1: Traditional (Flask)
pip install -r requirements.txt
cd woniunote && python app.py

# Option 2: Modern (FastAPI + Vue)
cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload --port 8001
cd frontend && npm install && npm run dev
```

### Tech Stack

- **Backend**: Flask / FastAPI + SQLAlchemy + Redis
- **Frontend**: Bootstrap / Vue 3 + Element Plus
- **Database**: MySQL / SQLite
- **Auth**: Session / JWT

### License

MIT License - see [LICENSE](LICENSE) for details.
