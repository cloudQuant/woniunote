# 端到端测试（Playwright E2E）

本目录是 WoniuNote 前端的端到端测试套件，使用 [Playwright](https://playwright.dev/) 驱动真实浏览器（Chromium）验证关键用户流程。

## 设计原则

- **无需真实后端**：所有 `/api/**` 请求由 `support/mockApi.js` 通过 Playwright 的路由拦截返回确定性数据（后端 `{code, message, data}` 信封格式）。因此套件**无需** C++ Drogon 后端、MySQL、Redis 即可运行，结果稳定、可在 CI 跑。
- **跑的是真实前端**：真实的 Vue Router 守卫、组件渲染、Pinia store、Axios 拦截器、localStorage 持久化等单元测试覆盖不到的集成路径。
- **可切真实后端**：设置 `E2E_BASE_URL` 指向真实服务地址即可（届时应移除 mock 或让其放行真实请求）。

## 覆盖的关键流程

| 文件 | 流程 |
|------|------|
| `home.spec.js` | 首页加载、文章列表、进入详情、分类路由、404、搜索 |
| `auth.spec.js` | 登录表单、登录成功/失败、注册、密码校验、已登录重定向 |
| `protected-routes.spec.js` | 路由守卫：未登录拦截、管理员权限、用户中心准入 |
| `article-detail.spec.js` | 文章详情渲染、评论展示、匿名收藏拦截、登录后发评论 |
| `theme-switch.spec.js` | 主题默认值、切换暗色主题、持久化、刷新保持 |
| `user-center.spec.js` | 用户中心各子路由（资料/文章/收藏/积分） |

## 运行

```bash
# 安装浏览器（首次）
npx playwright install chromium

# 跑全部 E2E（自动构建 + vite preview，再跑测试）
npm run test:e2e

# 交互式 UI 模式（调试用）
npm run test:e2e:ui
```

### 针对已运行的服务跑（更快迭代）

```bash
# 终端 A：构建并起预览服务
npm run build && npm run preview -- --port 4173 --strictPort

# 终端 B：指向该服务，跳过内置 webServer
E2E_BASE_URL=http://localhost:4173 npm run test:e2e
```

## 环境变量

| 变量 | 作用 |
|------|------|
| `E2E_BASE_URL` | 指向已运行的服务地址；设置后跳过内置的 build+preview webServer |
| `E2E_PORT` | 内置 preview 服务端口（默认 4173） |
| `PW_CHROMIUM_PATH` | 指定 Chromium 可执行文件路径（当只装了完整 Chromium 而非 headless-shell 时使用） |

## 新增一个 E2E 用例

1. 在本目录新建 `xxx.spec.js`。
2. `import { mockApi, loginAs } from './support/mockApi'`，在 `beforeEach` 里 `await mockApi(page)`。
3. 需要登录态时 `await loginAs(page, 'user' | 'admin')`（写入 localStorage，应在 `page.goto` 之前调用）。
4. 需要自定义某个接口返回时，给 `mockApi(page, { overrides: { 'GET /articles': {...} } })` 传 overrides。
