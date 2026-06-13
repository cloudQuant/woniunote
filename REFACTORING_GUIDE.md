# WoniuNote 重构现状指南

## 当前结论

WoniuNote 已从早期 Flask 单体架构演进到当前主线：

- **前端**：Vue 3 + Vite + Element Plus + Pinia
- **后端**：C++17 + Drogon + JWT + MySQL + Redis
- **部署**：Nginx + HTTPS + systemd

历史上的 FastAPI 方案和根目录旧 Python/Flask 测试仅作为迁移背景参考，不是当前 `dev_cpp` 分支的开发目标。

## 当前项目结构

```text
woniunote/
├── backend_cpp/                 # 当前 C++ Drogon 后端
│   ├── controllers/             # API 控制器
│   ├── core/                    # 配置、数据库、安全、日志
│   ├── filters/                 # 鉴权、管理员、限流过滤器
│   ├── models/                  # 数据模型
│   └── tests/                   # C++ 单元测试与 HTTP 集成测试
├── frontend/                    # 当前 Vue 3 前端
│   ├── src/
│   └── e2e/                     # Playwright 端到端测试
├── scripts/sql/                 # MySQL 表结构与迁移脚本
├── configs/                     # Nginx/systemd/示例配置
├── tests/                       # legacy Flask 测试归档
└── _bmad-output/                # BMad 规划与实施产物
```

## 当前开发与验证命令

### 后端

```bash
cd backend_cpp
./build.sh

cd build
ctest --output-on-failure
```

后端 HTTP 集成测试需要测试 MySQL 和 Redis：

```bash
bash backend_cpp/tests/integration/run_integration.sh
```

如本机 MySQL root 需要密码，先设置：

```bash
export WONIUNOTE_TEST_DB_USER=root
export WONIUNOTE_TEST_DB_PASSWORD='<password>'
```

### 前端

```bash
cd frontend
npm install
npm run lint:ci
npm run test:coverage
npm run build
npm run test:e2e
```

## 配置与密钥策略

- 真实证书、私钥、数据库密码、JWT secret 不入库。
- `configs/yunjinqi.top_nginx/` 是本地/服务器证书目录，部署时由运维环境提供。
- C++ 后端本地私有覆盖配置使用 `backend_cpp/config.local.json`，该文件不入库。
- 生产环境必须通过环境变量提供强随机 `WONIUNOTE_JWT_SECRET`。

如果证书或私钥曾经被提交到远端仓库，应按泄露处理：轮换证书/私钥，并评估是否需要重写 Git 历史。

## Legacy 边界

以下内容仅供迁移背景或历史维护参考：

- 根目录 `tests/` 中的旧 Flask 测试。
- `requirements.txt` / `setup.py` 中面向旧 Python 包的配置。
- `docs/others/` 中大量旧 Flask 性能、覆盖率和部署报告。

当前新功能和质量门禁应以 `backend_cpp/`、`frontend/`、`.github/workflows/cpp-vue-ci.yml` 为准。
