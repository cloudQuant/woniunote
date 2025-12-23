# WoniuNote Frontend

基于 Vue 3 的前端应用

## 技术栈

- **Vue 3** - 渐进式 JavaScript 框架
- **Vite** - 下一代前端构建工具
- **Vue Router** - 官方路由
- **Pinia** - 状态管理
- **Element Plus** - UI 组件库
- **Axios** - HTTP 客户端

## 安装

```bash
# 安装依赖
npm install
```

## 开发

```bash
# 启动开发服务器
npm run dev
```

开发服务器将在 http://localhost:8888 启动

## 构建

```bash
# 构建生产版本
npm run build

# 预览生产构建
npm run preview
```

## 项目结构

```
frontend/
├── src/
│   ├── api/           # API 封装
│   ├── assets/        # 静态资源
│   ├── components/    # 公共组件
│   │   ├── layout/    # 布局组件
│   │   ├── article/   # 文章组件
│   │   └── sidebar/   # 侧边栏组件
│   ├── router/        # 路由配置
│   ├── stores/        # Pinia 状态管理
│   ├── views/         # 页面视图
│   │   └── user/      # 用户中心页面
│   ├── App.vue        # 根组件
│   └── main.js        # 入口文件
├── index.html         # HTML 模板
├── package.json       # 项目配置
└── vite.config.js     # Vite 配置
```

## 功能模块

- **首页** - 文章列表、热门文章
- **文章详情** - 阅读、评论、收藏
- **分类** - 按分类浏览文章
- **搜索** - 关键词搜索
- **用户认证** - 登录、注册
- **个人中心** - 资料管理、我的文章、我的收藏
- **写文章** - 创建和编辑文章
