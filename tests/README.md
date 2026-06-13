# WoniuNote 测试说明

## 当前主线测试

当前 `dev_cpp` 分支的发布门禁是 C++ Drogon 后端与 Vue 3 前端：

```bash
# C++ 后端单元测试
cd backend_cpp/build
ctest --output-on-failure

# C++ 后端 HTTP 集成测试（需要测试 MySQL/Redis）
cd ../..
bash backend_cpp/tests/integration/run_integration.sh

# Vue 前端
cd frontend
npm run lint:ci
npm run test:coverage
npm run build
npm run test:e2e
npm audit --omit=dev --audit-level=moderate
```

后端集成测试默认使用：

```bash
WONIUNOTE_TEST_DB_HOST=127.0.0.1
WONIUNOTE_TEST_DB_PORT=3306
WONIUNOTE_TEST_DB_USER=root
WONIUNOTE_TEST_DB_PASSWORD=
WONIUNOTE_TEST_DB_NAME=woniunote_test
WONIUNOTE_TEST_REDIS_HOST=127.0.0.1
WONIUNOTE_TEST_REDIS_PORT=6379
```

如果本机 MySQL root 需要密码，先导出 `WONIUNOTE_TEST_DB_PASSWORD`。脚本会在建库前检查 MySQL/Redis 可达性，避免误操作真实库。

## Legacy Flask 测试

本目录下的大量 Python 测试文件来自旧 Flask 后端，仅用于历史参考或 legacy 维护，不再计入当前 C++/Vue 主线覆盖率，也不应由当前 CI 自动执行。

如确实需要验证旧 Flask 代码，可手动运行：

```bash
python tests/run_all_tests.py
pytest tests/unit/ -v
pytest tests/integration/ -v
```

这些命令可能依赖旧 Python 包、旧配置和本地测试数据库。若维护旧栈，请在单独分支中处理，不要把结果作为当前 Drogon 后端的质量信号。

## 生成物策略

以下文件属于本地生成物，不应提交：

- `coverage.json`
- `coverage.xml`
- `htmlcov/`
- `.coverage*`
- `tests/test_db/`
- `tests/configs/user_password_config.yaml`
- `__pycache__/`
