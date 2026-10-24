# 端到端测试（Playwright E2E）

本目录是 WoniuNote 前端的端到端测试套件，使用 [Playwright](https://playwright.dev/) 驱动真实浏览器（Chromium）验证关键用户流程。

## 设计原则

- **无需真实后端**：所有 `/api/**` 请求由 `support/mockApi.js` 通过 Playwright 的路由拦截返回确定性数据（后端 `{code, message, data}` 信封格式）。因此套件**无需** C++ Drogon 后端、MySQL、Redis 即可运行，结果稳定、可在 CI 跑。
- **跑的是真实前端**：真实的 Vue Router 守卫、组件渲染、Pinia store、Axios 拦截器、localStorage 持久化等单元测试覆盖不到的集成路径。
- **mock 出口有硬边界**：Playwright 启动专用 Vite preview 配置，`/api/**` 与 `/uploads/**` 没有代理，并由拒绝中间件记录每次漏网请求。全局 teardown 要求该次运行的审计记录存在且拒绝数为零。
- **真实后端隔离运行**：mock 配置拒绝 `E2E_BASE_URL` 和真实后端代理变量。真实后端测试应使用独立的 real Playwright 配置，不得复用本目录的 route mocks 或 mock preview。

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

# 跑全部 mock E2E（自动构建 + 无 API 代理的专用 vite preview，再跑测试）
npm run test:e2e

# 交互式 UI 模式（调试用）
npm run test:e2e:ui
```

## 环境变量

| 变量 | 作用 |
|------|------|
| `E2E_BASE_URL` | mock Playwright 配置拒绝此变量，避免绕过出口保护；真实后端配置单独管理 |
| `E2E_PORT` | 内置 preview 服务端口（默认 4173） |
| `PW_CHROMIUM_PATH` | 指定 Chromium 可执行文件路径（当只装了完整 Chromium 而非 headless-shell 时使用） |

每轮 mock E2E 会在系统临时目录生成唯一的出口审计记录。preview 启动时写入 ready 标记；任何未被页面 mock 拦截的 `/api` 或 `/uploads` 请求都会被返回 503、记录 method/path，并使全局 teardown 失败。查询参数、请求头和请求体不会写入该记录。

## 新增一个 E2E 用例

1. 在本目录新建 `xxx.spec.js`。
2. `import { mockApi, loginAs } from './support/mockApi'`，在 `beforeEach` 里 `await mockApi(page)`。
3. 需要登录态时 `await loginAs(page, 'user' | 'admin')`（写入 localStorage，应在 `page.goto` 之前调用）。
4. 需要自定义某个接口返回时，给 `mockApi(page, { overrides: { 'GET /articles': {...} } })` 传 overrides。
