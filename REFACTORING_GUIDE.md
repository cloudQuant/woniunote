# WoniuNote 项目重构指南

## 重构概述

本次重构将原有的 Flask 单体应用重构为前后端分离架构：

- **前端**: Vue 3 + Vite + Element Plus + Pinia
- **后端**: FastAPI + SQLAlchemy + MySQL + Redis

## 新项目结构

```
woniunote/
├── backend/                 # FastAPI 后端
│   ├── app/
│   │   ├── api/            # API 路由
│   │   ├── core/           # 核心配置
│   │   ├── models/         # 数据库模型
│   │   └── schemas/        # Pydantic Schema
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                # Vue 3 前端
│   ├── src/
│   │   ├── api/            # API 封装
│   │   ├── components/     # 公共组件
│   │   ├── router/         # 路由配置
│   │   ├── stores/         # 状态管理
│   │   └── views/          # 页面视图
│   ├── package.json
│   └── Dockerfile.new
├── woniunote/               # 旧版 Flask 应用（待删除）
├── docker-compose.new.yml   # Docker 编排配置
└── REFACTORING_GUIDE.md     # 本指南
```

## 快速开始

### 1. 启动后端

```bash
cd backend

# 创建虚拟环境
python -m venv venv
.\venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件配置数据库等

# 启动服务
uvicorn app.main:app --reload --port 8000
```

### 2. 启动前端

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

### 3. 使用 Docker Compose

```bash
# 使用新的 docker-compose 配置
docker-compose -f docker-compose.new.yml up -d
```

## 功能对照

| 原功能 | 新前端路由 | 新API端点 |
|-------|-----------|----------|
| 首页 | `/` | `GET /api/articles/` |
| 文章详情 | `/article/:id` | `GET /api/articles/:id` |
| 分类浏览 | `/category/:type` | `GET /api/articles/?type=` |
| 搜索 | `/search?keyword=` | `GET /api/articles/?keyword=` |
| 登录 | `/login` | `POST /api/auth/login` |
| 注册 | `/register` | `POST /api/auth/register` |
| 个人中心 | `/user` | `GET /api/auth/me` |
| 写文章 | `/write` | `POST /api/articles/` |
| 评论 | - | `POST /api/comments/` |
| 收藏 | - | `POST /api/favorites/` |

## API 文档

启动后端后访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 数据库迁移

新系统使用相同的数据库表结构，可以直接复用现有数据。

主要表：
- `users` - 用户表
- `article` - 文章表
- `comment` - 评论表
- `favorite` - 收藏表
- `credit` - 积分表

## 认证方式变更

- **旧系统**: Flask Session + Cookie
- **新系统**: JWT Token (Bearer)

前端会自动在请求头中携带 Token：
```
Authorization: Bearer <token>
```

## 配置说明

### 后端配置 (`.env`)

```env
DATABASE_URL=mysql+asyncmy://user:pass@localhost:3306/woniunote
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=your-secret-key
JWT_SECRET_KEY=jwt-secret-key
CORS_ORIGINS=["http://localhost:5173"]
```

### 前端配置 (`vite.config.js`)

开发时 API 代理已配置，生产部署时通过 Nginx 代理。

## 待完成功能

- [ ] 富文本编辑器集成（替代 UEditor）
- [ ] 文件上传预览
- [ ] 管理后台
- [ ] 卡片中心
- [ ] Todo 中心
- [ ] 邮件通知

## 清理旧代码

完成迁移验证后，可删除以下目录：
- `woniunote/` - 旧 Flask 应用
- `tests/` - 旧测试（如需保留逻辑可迁移至 `backend/tests/`）

## 注意事项

1. **密码兼容**: 新系统同时支持 MD5 和 bcrypt 密码验证，确保旧用户可登录
2. **文章类型**: 类型配置保持不变，前端会动态获取
3. **静态资源**: 需要迁移 `woniunote/resource/` 中的上传文件
4. **缩略图**: 新系统支持自动生成默认缩略图
