# WoniuNote Backend

基于 FastAPI 的后端 API 服务

## 技术栈

- **FastAPI** - 现代高性能 Python Web 框架
- **SQLAlchemy** - 异步 ORM
- **MySQL** - 数据库
- **Redis** - 缓存
- **JWT** - 认证

## 安装

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows
.\venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

## 配置

1. 复制环境配置文件
```bash
cp .env.example .env
```

2. 编辑 `.env` 文件，配置数据库和其他参数

## 运行

```bash
# 开发模式
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 生产模式
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## API 文档

启动后访问:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 项目结构

```
backend/
├── app/
│   ├── api/           # API 路由
│   │   ├── auth.py    # 认证相关
│   │   ├── articles.py # 文章管理
│   │   ├── comments.py # 评论管理
│   │   ├── favorites.py # 收藏管理
│   │   ├── users.py   # 用户管理
│   │   └── upload.py  # 文件上传
│   ├── core/          # 核心配置
│   │   ├── config.py  # 应用配置
│   │   ├── database.py # 数据库连接
│   │   ├── security.py # 安全工具
│   │   └── redis.py   # Redis连接
│   ├── models/        # 数据库模型
│   ├── schemas/       # Pydantic Schema
│   └── main.py        # 应用入口
├── .env.example       # 环境变量示例
└── requirements.txt   # 依赖列表
```
