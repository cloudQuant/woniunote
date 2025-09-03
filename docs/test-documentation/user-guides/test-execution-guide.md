# ▶️ 测试执行指南

## 📋 概述

本指南介绍如何在 WoniuNote 项目中运行各种类型的测试，包括单元测试、集成测试、性能测试等。

## 🎯 测试类型概览

| 测试类型 | 位置 | 目的 | 执行时间 |
|----------|------|------|----------|
| 单元测试 | `tests/unit/` | 测试单个函数/方法 | ~30秒 |
| 集成测试 | `tests/integration/` | 测试模块间交互 | ~2分钟 |
| 安全测试 | `tests/security/` | 测试安全漏洞 | ~1分钟 |
| 性能测试 | `tests/performance/` | 测试性能指标 | ~5分钟 |
| 端到端测试 | `tests/e2e/` | 测试完整流程 | ~10分钟 |

## 🚀 快速开始

### 使用测试管理器 (推荐)

```bash
# 运行所有测试
python scripts/test_manager.py --type all

# 运行单元测试
python scripts/test_manager.py --type unit

# 运行集成测试
python scripts/test_manager.py --type integration
```

### 使用 pytest 直接运行

```bash
# 运行所有测试
pytest

# 运行单元测试
pytest tests/unit/

# 运行特定测试文件
pytest tests/unit/test_user_controller_comprehensive.py

# 运行特定测试方法
pytest tests/unit/test_user_controller_comprehensive.py::TestUserController::test_login_success
```

## 🔧 详细执行选项

### 基本选项

```bash
# 详细输出
pytest -v

# 显示测试执行过程
pytest -s

# 只运行失败的测试
pytest --lf

# 只运行上次失败后的测试
pytest --lf --tb=short

# 并行执行 (需要 pytest-xdist)
pytest -n 4
```

### 覆盖率选项

```bash
# 生成覆盖率报告
pytest --cov=woniunote

# 生成 HTML 覆盖率报告
pytest --cov=woniunote --cov-report=html

# 生成终端覆盖率报告
pytest --cov=woniunote --cov-report=term-missing

# 设置覆盖率阈值
pytest --cov=woniunote --cov-fail-under=95
```

### 性能和调试选项

```bash
# 显示最慢的测试
pytest --durations=10

# 超时控制
pytest --timeout=300

# 内存使用分析
pytest --memray

# 生成性能报告
pytest --benchmark-only
```

## 📊 测试报告生成

### 自动报告生成

```bash
# 使用测试管理器生成完整报告
python scripts/test_manager.py --type all --coverage --report

# 生成覆盖率分析
python scripts/coverage_analyzer.py

# 生成综合测试报告
python scripts/generate_test_report.py
```

### 自定义报告配置

```bash
# 生成多种格式的报告
pytest --cov=woniunote \
       --cov-report=html \
       --cov-report=xml \
       --cov-report=json \
       --junitxml=test-results.xml \
       --html=test-report.html
```

## 🎯 特定测试场景

### 用户控制器测试

```bash
# 测试用户注册功能
pytest tests/unit/test_user_controller_comprehensive.py::TestUserRegistration -v

# 测试用户登录功能
pytest tests/unit/test_user_controller_comprehensive.py::TestUserLogin -v

# 测试验证码功能
pytest tests/unit/test_user_controller_comprehensive.py::TestVerificationCode -v
```

### 文章控制器测试

```bash
# 测试文章发布
pytest tests/unit/test_article_controller_comprehensive.py::TestArticlePublishing -v

# 测试文章编辑
pytest tests/unit/test_article_controller_comprehensive.py::TestArticleEditing -v

# 测试权限控制
pytest tests/unit/test_article_controller_comprehensive.py::TestPermissions -v
```

### 模型层测试

```bash
# 测试卡片模型
pytest tests/unit/test_models_comprehensive.py::TestCardModel -v

# 测试待办事项模型
pytest tests/unit/test_models_comprehensive.py::TestTodoModel -v

# 测试数据库操作
pytest tests/unit/test_models_comprehensive.py::TestDatabaseOperations -v
```

### 集成测试

```bash
# 用户完整流程
pytest tests/integration/test_user_workflow_integration.py -v

# 管理员流程
pytest tests/integration/test_admin_workflow_integration.py -v
```

### 安全测试

```bash
# SQL 注入测试
pytest tests/security/test_security_vulnerabilities.py::TestSQLInjectionProtection -v

# XSS 防护测试
pytest tests/security/test_security_vulnerabilities.py::TestXSSProtection -v

# 认证安全测试
pytest tests/security/test_security_vulnerabilities.py::TestAuthenticationSecurity -v
```

## 🔄 持续集成执行

### GitHub Actions

项目配置了自动 CI/CD 流水线：

```yaml
# 自动触发条件
on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

# 测试阶段
- name: Run unit tests
  run: python scripts/test_manager.py --type unit --coverage

- name: Run integration tests
  run: python scripts/test_manager.py --type integration

- name: Run security tests
  run: python scripts/test_manager.py --type security
```

### 本地 CI 模拟

```bash
# 模拟 CI 环境
export CI=true
export GITHUB_ACTIONS=true

# 运行完整 CI 流程
python scripts/test_manager.py --type all --coverage --quality
```

## 📈 性能监控

### 测试执行时间监控

```bash
# 显示执行时间
pytest --durations=0

# 生成性能报告
pytest --benchmark-json=benchmark.json

# 内存使用监控
pytest --memray --memray-bin-path=/usr/local/bin/memray
```

### 资源使用分析

```bash
# CPU 使用率
pytest --cpu-profiling

# 内存分析
pytest --memory-profiling

# 生成资源报告
python scripts/generate_performance_report.py
```

## 🔍 调试和故障排除

### 调试选项

```bash
# 进入调试模式
pytest --pdb

# 失败时停止
pytest -x

# 显示详细错误信息
pytest --tb=long

# 重新运行失败测试
pytest --lf
```

### 常见问题解决

#### 测试失败排查

```bash
# 查看详细错误
pytest -v --tb=long

# 只运行失败测试
pytest --lf

# 清理测试缓存
pytest --cache-clear
```

#### 数据库问题

```bash
# 重新创建测试数据库
rm test.db
python scripts/test_data_manager.py

# 检查数据库连接
python -c "from woniunote.common.database import db; print('DB OK')"
```

#### 依赖问题

```bash
# 重新安装依赖
pip install -r requirements-test.txt --force-reinstall

# 检查依赖版本
pip list | grep pytest
```

## 📊 结果分析

### 覆盖率分析

```bash
# 生成覆盖率报告
python scripts/coverage_analyzer.py

# 查看 HTML 报告
open htmlcov/index.html

# 分析未覆盖代码
python scripts/coverage_analyzer.py --analyze-gaps
```

### 测试结果统计

```bash
# 生成测试统计
python scripts/generate_test_report.py

# 查看测试趋势
python scripts/generate_test_report.py --trend

# 导出测试指标
python scripts/generate_test_report.py --export json
```

## 🎯 最佳实践

### 日常开发

```bash
# 提交前运行快速测试
python scripts/test_manager.py --type unit --fast

# 功能开发完成后运行完整测试
python scripts/test_manager.py --type all --coverage

# 定期检查覆盖率
python scripts/coverage_analyzer.py --weekly
```

### 持续改进

```bash
# 设置覆盖率阈值
pytest --cov=woniunote --cov-fail-under=95

# 自动化质量检查
python scripts/test_manager.py --quality

# 生成改进建议
python scripts/generate_test_report.py --recommendations
```

## 📚 相关文档

- [测试环境设置指南](test-environment-setup.md)
- [测试编写指南](test-writing-guide.md)
- [CI/CD 集成指南](ci-cd-integration.md)
- [问题排查指南](troubleshooting.md)

## 🔧 高级配置

### 自定义 pytest 配置

```ini
# pytest.ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short --strict-markers
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    integration: marks tests as integration tests
    unit: marks tests as unit tests
```

### 环境变量配置

```bash
# 测试配置
export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
export TEST_DATABASE_URL=sqlite:///test.db
export TEST_REDIS_URL=redis://localhost:6379/1

# 覆盖率配置
export COVERAGE_PROCESS_START=.coveragerc
export COVERAGE_FILE=.coverage.test
```

---

*测试执行过程中遇到问题？查看 [问题排查指南](troubleshooting.md)*
