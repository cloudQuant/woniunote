# WoniuNote v2.0.0 — 发布说明草稿（迭代 20）

> 状态：**已发布**（`v2.0.0` @ `f2aaec6`，2026-10-14）。实际验收 run 链接、演练结果与
> 发布后回读见迭代 20 验收记录第八节及 GitHub Release：
> https://github.com/cloudQuant/woniunote/releases/tag/v2.0.0
> 上一可用部署基点：`dev_cpp` @ `8eab0a06cbf2af4edfc38d6baeaeb48bd839e040`
> （仓库此前没有 tag / Release；回滚基点见"回滚"一节）。

## 版本与范围

| 项 | 值 |
|---|---|
| 产品版本 | 2.0.0（前端 `package.json`、后端 `vcpkg.json`；C++ 版本响应 `2.0.0-cpp`） |
| 发布分支 | `dev_cpp` |
| 发布对象 | 源码发行（C++ Drogon 后端 + Vue 3 前端） |
| 版本单一来源 | `backend_cpp/CMakeLists.txt` 的 `project(... VERSION)`，由 `scripts/check_release_version.sh` 校验 |

## 相对上一可用基线的变更

**后端构建与 CI**

- 修复 Linux 上后端无法编译的问题：vcpkg 的 drogon 端口在存在系统 MySQL 8 头文件的机器上
  会选中缺少非阻塞 API 的 `/usr/include/mysql`，导致 `MYSQL_OPT_NONBLOCK` 等编译错误。
  现通过 overlay port（`backend_cpp/vcpkg-overlay-ports/drogon`，补丁 0006）让 drogon 优先使用
  vcpkg 的 `unofficial::libmariadb`。
- 修复 Linux 上后端与测试可执行文件链接失败：vcpkg 模式缺少 `libcrypt`（`crypt_r`），
  现在按平台探测后链接。
- CI 固定 vcpkg 工具修订（`e7b524242c8a5d718a7afa26794c3c19bb8b0c71`）并调整缓存键；
  `ctest` 使用 `--no-tests=error`，零测试不再算通过。

**前端与依赖治理**

- 安装路径统一为 `npm ci`（不再删除锁文件、不再回退 `npm install`、不使用 `--no-package-lock`）；
  `start_app.sh` 与 `scripts/setup_ubuntu.sh` 的构建退出码不再被 `| tail` 掩盖，
  失败时不会启动旧产物。
- 新增 Node 版本门禁：`frontend/package.json` 的 `engines`（>= 20.19.0）与
  `frontend/scripts/check-node-version.mjs`；CI 与部署脚本在安装/构建前校验。
- 跨浏览器 E2E 修复：WebKit 下 UEditor 编辑区 iframe（`javascript:` URL）无法用
  `frameLocator` 定位、Firefox 下切换焦点后键入丢失，均改为经同源 `contentDocument`
  聚焦 + 真实键盘输入（`e2e/support/editor.js`）。
- 修复"输入后立即点击保存/发布"偶发校验失败：提交前冲刷编辑器 300ms 防抖同步
  （`UEditor.vue` 暴露 `flushContent()`，`WriteArticle.vue` 在提交前调用）。

**集成测试可信性**

- `run_integration.sh`：新增隔离校验（库名必须是测试库、端口不得是开发端口）、
  Redis 预检改为真实 PING、`WONIUNOTE_TEST_PYTHON` 选择解释器、
  `WONIUNOTE_TEST_BASE_URL` 外部实例模式、运行日志按 PID 命名、Ctrl-C/失败都会清理。
- 严格模式 `WONIUNOTE_TEST_STRICT=1`（CI 使用）：限流用例必须观测到真实 429 与
  `Retry-After`，否则失败而不是 skip。

**发布演练修复（隔离 Ubuntu 22.04 部署验收发现，均为本迭代前的历史遗留）**

- 修复"保存草稿→再编辑→发布"无效：文章更新接口此前不写 `drafted` 字段，发布后
  仍是草稿、永不进入公开列表。
- 修复草稿/隐藏文章对匿名读者可见：文章详情接口此前无可见性过滤与鉴权，现在
  匿名请求草稿/隐藏文章返回 404（与"文章不存在"同响应），作者凭 token 仍可读。
- 修复图片/文件/头像上传后无法回显：上传接口返回的 `/static/...` 前缀没有任何路由
  提供，现改为与存储布局一致的 `/uploads/...`（后端 document_root 提供、Nginx 代理）。
- 修复 `stop_app.sh` 实际停不掉后端：`relaunch_on_error` 模式下监督进程会立刻拉起
  被杀死的工作进程，restart 会静默沿用旧二进制；现一并终止监督进程并确认端口释放。
- 修复 `setup_ubuntu.sh` 每次都重编译 Drogon：其 MySQL 支持检测用 `grep "mysql"`
  匹配 `DrogonTargets.cmake` 里的 `MySQL`（大小写），永远失配。

## 兼容性 / 最低环境

| 组件 | 要求 |
|---|---|
| Node.js | >= 20.19.0（CI 与部署验收版本 22.13.0） |
| npm | >= 10 |
| MySQL | 8.0 |
| Redis | 6.0+（限流与刷新令牌轮换需要） |
| 编译器 | GCC 10+ / Clang 13+ |
| CMake | 3.20+ |
| vcpkg | 固定基线 `e7b524242c8a5d718a7afa26794c3c19bb8b0c71` |

## 升级步骤（从上一可用部署）

1. 停止后端与前端服务（`bash stop_app.sh`）。
2. 拉取发布分支 / tag 对应提交。
3. 数据库：按 `scripts/sql/migrations/README.md` 的顺序执行未应用的 migration
   （两份现有 migration 均为幂等；先在恢复副本上演练）。
4. 后端：`cd backend_cpp && ./build.sh`（vcpkg 模式）或按 `scripts/setup_ubuntu.sh`
   的系统库路径构建；确认二进制更新（注意不要沿用旧产物）。
5. 前端：`cd frontend && npm ci && npm run check:node && npm run build`。
6. 启动：`bash start_app.sh prod`，确认 `/health` 与版本响应为 `2.0.0-cpp`。

## 已知限制

- 仓库此前没有 tag / Release；本次是首个候选发布，回滚基点为上一可用部署 SHA 与备份。
- 发布仓库为 GitHub（`github` 远端）与 Gitee（`origin`）双写；两者需要分别核验 tag SHA。
- Playwright 产物默认保留 7 天；发布证据需另行留存（见验收记录）。
- 覆盖率口径：前端四项阈值 >= 95%（vitest）；后端覆盖率脚本目前只统计 CTest 可达代码。
- `frontend/Dockerfile.new` 已废弃，不是支持的发布入口（见文件头说明）。

## 回滚

1. 应用回滚：切回上一可用部署 SHA 并重新构建/启动；数据库保留（migration 均为前向兼容的
   加宽/建表操作，不需要反向迁移）。
2. 若必须恢复数据库：先暂停写入，按备份恢复点恢复，并说明新增数据的处理方式；
   `database_transfer.sh import --replace` 不是无损反向迁移，不作为回滚手段。
3. 静态资源：前端 hash 资源随构建更新；回滚后浏览器缓存的旧 hash 不应产生 404
   （Nginx 直接服务 `frontend/dist`）。
