# WoniuNote API 文档

## 📖 概述

WoniuNote API 提供完整的RESTful接口，支持文章管理、用户认证、卡片学习、待办管理等核心功能。

### API版本
- **当前版本**: v1.0
- **基础URL**: `https://api.yunjinqi.top/api/v1`
- **协议**: HTTPS
- **数据格式**: JSON

### 认证方式
- **Session认证**: 基于Cookie的会话认证
- **CSRF保护**: 所有POST/PUT/DELETE请求需要CSRF令牌

---

## 🔑 认证接口

### 用户登录
```http
POST /api/auth/login
Content-Type: application/json

{
    "username": "user@example.com",
    "password": "password123",
    "remember_me": false
}
```

**响应示例**:
```json
{
    "code": 200,
    "message": "登录成功",
    "data": {
        "user_id": 1,
        "username": "user@example.com",
        "nickname": "用户昵称",
        "role": "user",
        "avatar": "/static/avatars/default.png"
    },
    "timestamp": "2024-01-15T10:30:00Z"
}
```

### 用户注册
```http
POST /api/auth/register
Content-Type: application/json

{
    "username": "newuser",
    "email": "newuser@example.com",
    "password": "password123",
    "nickname": "新用户",
    "captcha": "ABCD"
}
```

### 用户登出
```http
POST /api/auth/logout
```

---

## 📝 文章接口

### 获取文章列表
```http
GET /api/articles?page=1&per_page=20&type=1&keyword=搜索词
```

**查询参数**:
- `page`: 页码，默认1
- `per_page`: 每页数量，默认20，最大100
- `type`: 文章类型，可选
- `keyword`: 搜索关键词，可选
- `user_id`: 指定用户ID，可选

**响应示例**:
```json
{
    "code": 200,
    "message": "success",
    "data": {
        "articles": [
            {
                "articleid": 1,
                "userid": 1,
                "type": 1,
                "headline": "示例文章标题",
                "content": "文章内容摘要...",
                "thumbnail": "/static/images/article1.jpg",
                "credit": 10,
                "readcount": 156,
                "replycount": 8,
                "recommended": 1,
                "hidden": 0,
                "drafted": 0,
                "checked": 1,
                "createtime": "2024-01-15T08:30:00Z",
                "updatetime": "2024-01-15T09:15:00Z",
                "author": {
                    "userid": 1,
                    "username": "author",
                    "nickname": "作者昵称",
                    "avatar": "/static/avatars/user1.png",
                    "role": "user"
                }
            }
        ],
        "pagination": {
            "page": 1,
            "per_page": 20,
            "total": 150,
            "pages": 8,
            "has_prev": false,
            "has_next": true
        }
    }
}
```

### 获取文章详情
```http
GET /api/articles/{article_id}
```

**响应示例**:
```json
{
    "code": 200,
    "message": "success",
    "data": {
        "articleid": 1,
        "userid": 1,
        "type": 1,
        "headline": "文章完整标题",
        "content": "文章完整内容...",
        "thumbnail": "/static/images/article1.jpg",
        "credit": 10,
        "readcount": 157,
        "replycount": 8,
        "recommended": 1,
        "hidden": 0,
        "drafted": 0,
        "checked": 1,
        "createtime": "2024-01-15T08:30:00Z",
        "updatetime": "2024-01-15T09:15:00Z",
        "author": {
            "userid": 1,
            "username": "author",
            "nickname": "作者昵称",
            "avatar": "/static/avatars/user1.png",
            "role": "user"
        },
        "comments": [
            {
                "commentid": 1,
                "content": "很好的文章！",
                "createtime": "2024-01-15T10:00:00Z",
                "user": {
                    "userid": 2,
                    "nickname": "评论者"
                }
            }
        ]
    }
}
```

### 创建文章
```http
POST /api/articles
Content-Type: application/json
X-CSRFToken: csrf_token_here

{
    "headline": "新文章标题",
    "content": "文章内容...",
    "type": 1,
    "thumbnail": "/static/images/new_article.jpg",
    "drafted": 0
}
```

### 更新文章
```http
PUT /api/articles/{article_id}
Content-Type: application/json
X-CSRFToken: csrf_token_here

{
    "headline": "更新后的标题",
    "content": "更新后的内容...",
    "type": 1
}
```

### 删除文章
```http
DELETE /api/articles/{article_id}
X-CSRFToken: csrf_token_here
```

---

## 👤 用户接口

### 获取用户信息
```http
GET /api/users/{user_id}
```

**响应示例**:
```json
{
    "code": 200,
    "message": "success",
    "data": {
        "userid": 1,
        "username": "user123",
        "nickname": "用户昵称",
        "email": "user@example.com",
        "avatar": "/static/avatars/user1.png",
        "role": "user",
        "createtime": "2024-01-01T00:00:00Z",
        "status": 1,
        "stats": {
            "article_count": 25,
            "comment_count": 48,
            "credit_total": 1250
        }
    }
}
```

### 更新用户资料
```http
PUT /api/users/{user_id}
Content-Type: application/json
X-CSRFToken: csrf_token_here

{
    "nickname": "新昵称",
    "email": "newemail@example.com",
    "avatar": "/static/avatars/new_avatar.png"
}
```

### 修改密码
```http
POST /api/users/{user_id}/change-password
Content-Type: application/json
X-CSRFToken: csrf_token_here

{
    "old_password": "old_password123",
    "new_password": "new_password456",
    "confirm_password": "new_password456"
}
```

---

## 🎴 卡片学习接口

### 获取卡片列表
```http
GET /api/cards?category_id=1&page=1&per_page=20
```

**响应示例**:
```json
{
    "code": 200,
    "message": "success",
    "data": {
        "cards": [
            {
                "id": 1,
                "user_id": 1,
                "category_id": 1,
                "question": "什么是Python?",
                "answer": "Python是一种高级编程语言...",
                "difficulty": "medium",
                "next_review": "2024-01-16T10:00:00Z",
                "review_count": 3,
                "success_rate": 0.85,
                "created_at": "2024-01-10T08:00:00Z",
                "updated_at": "2024-01-15T10:30:00Z",
                "category": {
                    "id": 1,
                    "name": "编程基础",
                    "description": "编程相关基础知识"
                }
            }
        ],
        "pagination": {
            "page": 1,
            "per_page": 20,
            "total": 85,
            "pages": 5
        }
    }
}
```

### 创建卡片
```http
POST /api/cards
Content-Type: application/json
X-CSRFToken: csrf_token_here

{
    "category_id": 1,
    "question": "新问题?",
    "answer": "答案内容...",
    "difficulty": "medium"
}
```

### 复习卡片
```http
POST /api/cards/{card_id}/review
Content-Type: application/json
X-CSRFToken: csrf_token_here

{
    "quality": 4,
    "time_spent": 15
}
```

**quality评级**:
- 0: 完全不记得
- 1: 错误，但有印象
- 2: 错误，容易想起
- 3: 正确，但困难
- 4: 正确，有些犹豫
- 5: 完全正确，轻松

### 获取卡片分类
```http
GET /api/card-categories
```

---

## ✅ 待办管理接口

### 获取待办列表
```http
GET /api/todos?status=pending&priority=high&page=1
```

**响应示例**:
```json
{
    "code": 200,
    "message": "success",
    "data": {
        "todos": [
            {
                "id": 1,
                "user_id": 1,
                "title": "完成项目文档",
                "description": "编写API文档和用户手册",
                "status": "in_progress",
                "priority": "high",
                "due_date": "2024-01-20T18:00:00Z",
                "completed_at": null,
                "created_at": "2024-01-15T09:00:00Z",
                "updated_at": "2024-01-15T10:00:00Z",
                "category": {
                    "id": 1,
                    "name": "工作",
                    "color": "#ff6b6b"
                }
            }
        ],
        "stats": {
            "total": 25,
            "pending": 8,
            "in_progress": 5,
            "completed": 12,
            "overdue": 2
        }
    }
}
```

### 创建待办
```http
POST /api/todos
Content-Type: application/json
X-CSRFToken: csrf_token_here

{
    "title": "新任务",
    "description": "任务描述...",
    "priority": "medium",
    "due_date": "2024-01-25T15:00:00Z",
    "category_id": 1
}
```

### 更新待办状态
```http
PUT /api/todos/{todo_id}
Content-Type: application/json
X-CSRFToken: csrf_token_here

{
    "status": "completed",
    "completed_at": "2024-01-15T14:30:00Z"
}
```

---

## 💬 评论接口

### 获取评论列表
```http
GET /api/articles/{article_id}/comments?page=1&per_page=20
```

### 创建评论
```http
POST /api/articles/{article_id}/comments
Content-Type: application/json
X-CSRFToken: csrf_token_here

{
    "content": "这是一条评论",
    "parent_id": null
}
```

### 删除评论
```http
DELETE /api/comments/{comment_id}
X-CSRFToken: csrf_token_here
```

---

## 📊 统计接口

### 用户统计
```http
GET /api/stats/user/{user_id}
```

**响应示例**:
```json
{
    "code": 200,
    "message": "success",
    "data": {
        "articles": {
            "total": 25,
            "published": 23,
            "drafted": 2,
            "total_views": 15420,
            "total_comments": 89
        },
        "cards": {
            "total": 150,
            "reviewed_today": 8,
            "mastered": 45,
            "learning": 105
        },
        "todos": {
            "total": 68,
            "completed": 45,
            "pending": 18,
            "in_progress": 5,
            "completion_rate": 0.66
        }
    }
}
```

### 系统统计（管理员）
```http
GET /api/stats/system
```

---

## 🔍 搜索接口

### 全局搜索
```http
GET /api/search?q=关键词&type=all&page=1&per_page=20
```

**type参数**:
- `all`: 搜索所有内容
- `articles`: 仅搜索文章
- `users`: 仅搜索用户
- `cards`: 仅搜索卡片

**响应示例**:
```json
{
    "code": 200,
    "message": "success",
    "data": {
        "results": {
            "articles": [
                {
                    "type": "article",
                    "id": 1,
                    "title": "包含关键词的文章",
                    "summary": "...关键词...",
                    "url": "/articles/1",
                    "score": 0.95
                }
            ],
            "users": [],
            "cards": []
        },
        "total": 15,
        "query_time": 0.045
    }
}
```

---

## 📤 文件上传接口

### 上传图片
```http
POST /api/upload/image
Content-Type: multipart/form-data

file: [binary data]
type: article|avatar|thumbnail
```

**响应示例**:
```json
{
    "code": 200,
    "message": "上传成功",
    "data": {
        "url": "/static/uploads/images/20240115_143052_image.jpg",
        "filename": "20240115_143052_image.jpg",
        "size": 256789,
        "type": "image/jpeg"
    }
}
```

---

## 🎯 验证码接口

### 获取图形验证码
```http
GET /api/captcha/image
```

**响应**: 返回PNG图片数据

### 验证图形验证码
```http
POST /api/captcha/verify
Content-Type: application/json

{
    "captcha": "ABCD",
    "session_id": "captcha_session_id"
}
```

---

## ⚠️ 错误码说明

### HTTP状态码
- `200`: 成功
- `201`: 创建成功
- `400`: 请求参数错误
- `401`: 未认证
- `403`: 权限不足
- `404`: 资源不存在
- `409`: 资源冲突
- `422`: 数据验证失败
- `429`: 请求频率限制
- `500`: 服务器内部错误

### 业务错误码
```json
{
    "code": 40001,
    "message": "用户名已存在",
    "error": "username_exists",
    "timestamp": "2024-01-15T10:30:00Z"
}
```

**常见错误码**:
- `40001`: 用户名已存在
- `40002`: 邮箱已存在
- `40003`: 验证码错误
- `40004`: 密码不符合要求
- `40101`: 登录失败，用户名或密码错误
- `40102`: 账户已被禁用
- `40301`: 权限不足
- `40401`: 文章不存在
- `40402`: 用户不存在
- `42201`: 数据验证失败

---

## 🔧 请求限制

### 频率限制
- **普通用户**: 100请求/分钟
- **认证用户**: 300请求/分钟
- **管理员**: 1000请求/分钟

### 文件上传限制
- **图片**: 最大5MB，支持JPG/PNG/GIF
- **文档**: 最大10MB，支持PDF/DOC/DOCX
- **单次**: 最多上传3个文件

---

## 📱 移动端适配

### 响应式设计
API返回的所有数据都支持移动端显示，包括：
- 自适应图片URL
- 简化的数据结构
- 压缩的内容摘要

### 移动端专用参数
```http
GET /api/articles?mobile=true&compact=true
```

- `mobile=true`: 返回移动端优化数据
- `compact=true`: 返回紧凑的数据结构

---

## 🔗 Webhook支持

### 配置Webhook
```http
POST /api/webhooks
Content-Type: application/json
X-CSRFToken: csrf_token_here

{
    "url": "https://your-app.com/webhook",
    "events": ["article.created", "comment.created"],
    "secret": "webhook_secret"
}
```

### 支持的事件
- `article.created`: 文章创建
- `article.updated`: 文章更新
- `comment.created`: 评论创建
- `user.registered`: 用户注册

---

## 📈 API使用示例

### JavaScript示例
```javascript
// 获取文章列表
async function getArticles(page = 1) {
    try {
        const response = await fetch(`/api/articles?page=${page}`, {
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            }
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const data = await response.json();
        return data.data.articles;
    } catch (error) {
        console.error('获取文章失败:', error);
        throw error;
    }
}

// 创建文章
async function createArticle(articleData) {
    const csrfToken = document.querySelector('meta[name=csrf-token]').content;
    
    try {
        const response = await fetch('/api/articles', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify(articleData)
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.message);
        }
        
        return await response.json();
    } catch (error) {
        console.error('创建文章失败:', error);
        throw error;
    }
}
```

### Python示例
```python
import requests
import json

class WoniuNoteAPI:
    def __init__(self, base_url, session=None):
        self.base_url = base_url.rstrip('/')
        self.session = session or requests.Session()
    
    def login(self, username, password):
        """用户登录"""
        url = f"{self.base_url}/api/auth/login"
        data = {
            "username": username,
            "password": password
        }
        
        response = self.session.post(url, json=data)
        response.raise_for_status()
        return response.json()
    
    def get_articles(self, page=1, per_page=20, **params):
        """获取文章列表"""
        url = f"{self.base_url}/api/articles"
        params.update({"page": page, "per_page": per_page})
        
        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json()
    
    def create_article(self, article_data):
        """创建文章"""
        url = f"{self.base_url}/api/articles"
        
        # 获取CSRF令牌
        csrf_token = self._get_csrf_token()
        headers = {"X-CSRFToken": csrf_token}
        
        response = self.session.post(url, json=article_data, headers=headers)
        response.raise_for_status()
        return response.json()

# 使用示例
api = WoniuNoteAPI("https://api.yunjinqi.top")
api.login("username", "password")
articles = api.get_articles(page=1, type=1)
```

---

## 🔄 版本更新

### v1.1.0 (计划中)
- GraphQL支持
- WebSocket实时通信
- 批量操作接口
- 高级搜索功能

### v1.0.1 (当前)
- 基础CRUD操作
- 用户认证
- 文件上传
- 搜索功能

---

## 📞 技术支持

- **API文档**: [https://docs.yunjinqi.top/api](https://docs.yunjinqi.top/api)
- **问题反馈**: [GitHub Issues](https://github.com/cloudQuant/woniunote/issues)
- **技术交流**: [GitHub Discussions](https://github.com/cloudQuant/woniunote/discussions)

---

*API文档最后更新: 2024年1月15日*