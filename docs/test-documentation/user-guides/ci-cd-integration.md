# 🔄 CI/CD 集成指南

## 📋 概述

本指南介绍 WoniuNote 项目的持续集成和持续部署 (CI/CD) 配置，包括自动化测试、代码质量检查、部署流程等。

## 🏗️ CI/CD 架构

### 流水线阶段

```
代码提交 → 代码质量检查 → 单元测试 → 集成测试 → 安全测试 → 性能测试 → 部署
    ↓           ↓              ↓          ↓          ↓          ↓          ↓
触发条件   自动触发       并行执行   依赖通过   人工确认   基准对比   自动部署
```

### 工具栈

- **CI/CD 平台**: GitHub Actions
- **测试框架**: pytest
- **覆盖率工具**: pytest-cov
- **代码质量**: flake8, black, mypy, bandit
- **容器化**: Docker (可选)
- **部署**: 自动化脚本

## ⚙️ GitHub Actions 配置

### 完整流水线配置

项目已配置完整的 CI/CD 流水线：

```yaml
# .github/workflows/ci-cd.yml
name: CI/CD Pipeline

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]
  workflow_dispatch:
    inputs:
      test_level:
        description: 'Test level to run'
        required: true
        default: 'all'
        type: choice
        options:
        - unit
        - integration
        - all
        - performance
      environment:
        description: 'Deployment environment'
        required: true
        default: 'staging'
        type: choice
        options:
        - staging
        - production

jobs:
  # 代码质量检查
  code-quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.8'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements-test.txt

      - name: Run code quality checks
        run: |
          python scripts/test_manager.py --quality

      - name: Upload quality reports
        uses: actions/upload-artifact@v3
        with:
          name: quality-reports
          path: |
            quality-reports/
            test-results-quality.json

  # 单元测试
  unit-tests:
    runs-on: ubuntu-latest
    needs: code-quality
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_DB: woniunote_test
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379
        options: --entrypoint redis-server

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.8'

      - name: Cache pip dependencies
        uses: actions/cache@v3
        with:
          path: ~/.cache/pip
          key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements*.txt') }}
          restore-keys: |
            ${{ runner.os }}-pip-

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install -r requirements-test.txt

      - name: Set up test database
        run: |
          python scripts/test_data_manager.py

      - name: Run unit tests
        run: |
          python scripts/test_manager.py --type unit --coverage

      - name: Upload test results
        uses: actions/upload-artifact@v3
        with:
          name: unit-test-results
          path: |
            test-results-unit.xml
            htmlcov/
            coverage.xml

      - name: Upload coverage reports
        uses: actions/upload-artifact@v3
        with:
          name: coverage-reports
          path: |
            htmlcov/
            coverage.xml

  # 集成测试
  integration-tests:
    runs-on: ubuntu-latest
    needs: unit-tests
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_DB: woniunote_test
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379
        options: --entrypoint redis-server

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.8'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install -r requirements-test.txt

      - name: Run integration tests
        run: |
          python scripts/test_manager.py --type integration

      - name: Upload integration test results
        uses: actions/upload-artifact@v3
        with:
          name: integration-test-results
          path: test-results-integration.xml

  # 安全测试
  security-tests:
    runs-on: ubuntu-latest
    needs: integration-tests
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.8'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install -r requirements-test.txt

      - name: Run security tests
        run: |
          python scripts/test_manager.py --type security

      - name: Upload security test results
        uses: actions/upload-artifact@v3
        with:
          name: security-test-results
          path: test-results-security.xml

  # 性能测试
  performance-tests:
    runs-on: ubuntu-latest
    needs: security-tests
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_DB: woniunote_test
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379
        options: --entrypoint redis-server

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.8'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install -r requirements-test.txt

      - name: Run performance tests
        run: |
          python scripts/test_manager.py --type performance

      - name: Upload performance test results
        uses: actions/upload-artifact@v3
        with:
          name: performance-test-results
          path: |
            test-results-performance.xml
            performance-reports/

  # 测试报告生成
  test-report:
    runs-on: ubuntu-latest
    needs: [unit-tests, integration-tests, security-tests, performance-tests]
    if: always()
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.8'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements-test.txt

      - name: Download test results
        uses: actions/download-artifact@v3
        with:
          name: unit-test-results
      - uses: actions/download-artifact@v3
        with:
          name: integration-test-results
      - uses: actions/download-artifact@v3
        with:
          name: security-test-results
      - uses: actions/download-artifact@v3
        with:
          name: performance-test-results

      - name: Generate comprehensive report
        run: |
          python scripts/generate_test_report.py

      - name: Upload final test report
        uses: actions/upload-artifact@v3
        with:
          name: final-test-report
          path: |
            test-reports/
            test-results-*.xml
            htmlcov/

  # 部署到预发布环境
  deploy-to-staging:
    runs-on: ubuntu-latest
    needs: test-report
    if: github.ref == 'refs/heads/develop' && github.event_name == 'push'
    environment: staging
    steps:
      - uses: actions/checkout@v4

      - name: Deploy to staging
        run: |
          echo "Deploying to staging environment..."
          # 添加您的部署脚本
          # ./scripts/deploy.sh staging

  # 部署到生产环境
  deploy-to-production:
    runs-on: ubuntu-latest
    needs: test-report
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    environment: production
    steps:
      - uses: actions/checkout@v4

      - name: Deploy to production
        run: |
          echo "Deploying to production environment..."
          # 添加您的部署脚本
          # ./scripts/deploy.sh production

  # 通知
  notification:
    runs-on: ubuntu-latest
    needs: [test-report, deploy-to-staging, deploy-to-production]
    if: always()
    steps:
      - name: Send notification
        run: |
          if [ "${{ needs.test-report.result }}" == "success" ]; then
            echo "✅ All tests passed!"
            # 发送成功通知
          else
            echo "❌ Some tests failed!"
            # 发送失败通知
          fi

  # 清理
  cleanup:
    runs-on: ubuntu-latest
    needs: notification
    if: always()
    steps:
      - name: Clean up artifacts
        run: |
          echo "Cleaning up old artifacts..."
          # 清理过期构件
```

## 🚀 本地 CI/CD 模拟

### 使用测试管理器

```bash
# 运行完整 CI 流程
python scripts/test_manager.py --type all --coverage --quality

# 运行特定阶段
python scripts/test_manager.py --type unit --coverage
python scripts/test_manager.py --type integration
python scripts/test_manager.py --type security
```

### 模拟 GitHub Actions 环境

```bash
# 设置环境变量
export CI=true
export GITHUB_ACTIONS=true
export GITHUB_REF=refs/heads/main
export GITHUB_EVENT_NAME=push

# 运行测试
python scripts/test_manager.py --type all --coverage --quality
```

## 📊 监控和报告

### 测试结果监控

```bash
# 生成测试报告
python scripts/generate_test_report.py

# 查看覆盖率报告
python scripts/coverage_analyzer.py

# 生成质量报告
python scripts/test_manager.py --quality
```

### 性能基准监控

```bash
# 运行性能测试
python scripts/test_manager.py --type performance

# 比较性能基准
python scripts/generate_performance_report.py --compare
```

## 🔧 自定义配置

### 分支策略

```yaml
# 不同分支的 CI 策略
on:
  push:
    branches:
      - main          # 生产分支 - 完整测试
      - develop       # 开发分支 - 完整测试
      - 'feature/*'   # 功能分支 - 快速测试
  pull_request:
    branches:
      - main
      - develop
```

### 条件部署

```yaml
# 只有在所有测试通过时才部署
deploy-to-production:
  needs: test-report
  if: |
    github.ref == 'refs/heads/main' &&
    github.event_name == 'push' &&
    needs.test-report.result == 'success'
```

### 矩阵测试

```yaml
# 在多个 Python 版本和操作系统上测试
strategy:
  matrix:
    python-version: ['3.8', '3.9', '3.10']
    os: [ubuntu-latest, windows-latest, macos-latest]
    exclude:
      - os: windows-latest
        python-version: '3.10'
```

## 🔐 安全配置

### 密钥管理

```yaml
# 使用 GitHub Secrets
- name: Deploy to production
  env:
    API_KEY: ${{ secrets.API_KEY }}
    DATABASE_URL: ${{ secrets.DATABASE_URL }}
  run: |
    ./scripts/deploy.sh production
```

### 代码扫描

```yaml
# 添加安全扫描
- name: Security scan
  uses: github/codeql-action/init@v2
  with:
    languages: python

- name: Perform CodeQL Analysis
  uses: github/codeql-action/analyze@v2
```

## 📈 持续改进

### 流水线优化

```bash
# 并行执行优化
jobs:
  test-parallel:
    strategy:
      matrix:
        test-type: [unit, integration, security]
    steps:
      - name: Run ${{ matrix.test-type }} tests
        run: python scripts/test_manager.py --type ${{ matrix.test-type }}
```

### 缓存策略

```yaml
# 依赖缓存
- name: Cache pip dependencies
  uses: actions/cache@v3
  with:
    path: ~/.cache/pip
    key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements*.txt') }}

# 测试数据缓存
- name: Cache test data
  uses: actions/cache@v3
  with:
    path: test-data/
    key: ${{ runner.os }}-test-data-${{ hashFiles('**/test_data_manager.py') }}
```

## 🚨 故障排除

### 常见问题

#### 1. 测试超时

```yaml
# 增加超时时间
jobs:
  integration-tests:
    timeout-minutes: 30
    steps:
      - name: Run tests with timeout
        run: timeout 1800 python scripts/test_manager.py --type integration
```

#### 2. 依赖冲突

```yaml
# 使用具体版本
- name: Install specific versions
  run: |
    pip install pytest==7.1.3
    pip install pytest-cov==4.0.0
```

#### 3. 数据库连接问题

```yaml
# 等待数据库就绪
- name: Wait for database
  run: |
    for i in {1..30}; do
      if pg_isready -h localhost -p 5432; then
        break
      fi
      sleep 2
    done
```

#### 4. 内存不足

```yaml
# 增加运行器资源
jobs:
  performance-tests:
    runs-on: ubuntu-latest
    # 增加内存
    container:
      image: ubuntu:latest
      options: --memory 8g
```

## 📊 指标和报告

### CI/CD 指标

- **构建成功率**: 目标 > 95%
- **平均构建时间**: 目标 < 10分钟
- **测试覆盖率**: 目标 > 95%
- **部署频率**: 目标每日多次

### 报告生成

```bash
# 生成 CI/CD 报告
python scripts/generate_ci_report.py

# 查看构建历史
python scripts/ci_history_analyzer.py

# 性能趋势分析
python scripts/performance_trends.py
```

## 🎯 最佳实践

### 1. 分支管理
- `main`: 生产就绪代码
- `develop`: 开发主分支
- `feature/*`: 功能开发分支
- `hotfix/*`: 紧急修复分支

### 2. 提交规范
```bash
# 好的提交消息
feat: add user authentication
fix: resolve login timeout issue
test: add unit tests for user service
docs: update API documentation
refactor: optimize database queries
```

### 3. 代码审查
- 所有 PR 都需要代码审查
- 至少一人 approve 才能合并
- 自动化检查必须全部通过

### 4. 回滚策略
- 保留最近 5 个版本的部署包
- 准备回滚脚本
- 监控部署后的系统状态

## 📚 相关文档

- [测试环境设置指南](test-environment-setup.md)
- [测试执行指南](test-execution-guide.md)
- [测试编写指南](test-writing-guide.md)
- [问题排查指南](troubleshooting.md)

---

*CI/CD 配置应根据项目规模和需求进行调整。*
