# 🛠️ 测试环境设置指南

## 📋 概述

本指南将帮助您快速设置 WoniuNote 项目的完整测试环境，包括依赖安装、数据库配置、测试数据准备等。

## 🎯 前置要求

### 系统要求
- **操作系统**: macOS 10.15+, Ubuntu 18.04+, Windows 10+
- **Python**: 3.8 - 3.11
- **内存**: 至少 4GB RAM
- **磁盘空间**: 至少 2GB 可用空间

### 依赖软件
- **Git**: 版本控制
- **SQLite**: 测试数据库 (默认)
- **Redis**: 缓存服务 (可选，用于缓存测试)

## 🚀 快速开始

### 1. 克隆项目
```bash
git clone <repository-url>
cd woniunote
```

### 2. 创建虚拟环境
```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
source venv/bin/activate  # Linux/macOS
# 或
venv\Scripts\activate     # Windows
```

### 3. 安装依赖
```bash
# 安装核心依赖
pip install -r requirements.txt

# 安装测试依赖
pip install -r requirements-test.txt

# 验证安装
python -c "import flask, pytest, sqlalchemy; print('✅ 所有依赖安装成功')"
```

## 🔧 详细配置

### 测试配置文件

项目已包含预配置的测试文件：

```
├── pytest.ini              # pytest 配置
├── conftest.py             # 测试夹具和配置
├── requirements-test.txt   # 测试依赖
└── tests/                  # 测试文件目录
    ├── conftest.py
    └── ...
```

### 环境变量配置

创建 `.env.test` 文件用于测试环境：

```bash
# 复制环境变量模板
cp .env.example .env.test

# 编辑测试环境变量
vim .env.test
```

`.env.test` 内容示例：
```bash
# Flask 配置
FLASK_ENV=testing
SECRET_KEY=test-secret-key-12345
TESTING=True

# 数据库配置
DATABASE_URL=sqlite:///test.db

# Redis 配置 (可选)
REDIS_URL=redis://localhost:6379/1

# 测试配置
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
COVERAGE_PROCESS_START=.coveragerc
```

## 🗄️ 数据库设置

### SQLite 测试数据库 (推荐)

项目默认使用 SQLite 进行测试，无需额外配置：

```bash
# 初始化测试数据库
python scripts/test_data_manager.py

# 验证数据库
python -c "from woniunote.common.database import db; print('✅ 数据库连接成功')"
```

### PostgreSQL 测试数据库 (可选)

如果需要使用 PostgreSQL：

```bash
# 安装 PostgreSQL
brew install postgresql    # macOS
sudo apt install postgresql # Ubuntu

# 启动服务
brew services start postgresql  # macOS
sudo systemctl start postgresql # Ubuntu

# 创建测试数据库
createdb woniunote_test

# 更新环境变量
echo "DATABASE_URL=postgresql://localhost/woniunote_test" >> .env.test
```

## 📊 测试数据准备

### 自动生成测试数据

使用内置脚本生成测试数据：

```bash
# 生成完整测试数据集
python scripts/test_data_manager.py

# 生成特定类型数据
python scripts/test_data_manager.py --type users --count 100
python scripts/test_data_manager.py --type articles --count 500
```

### 手动创建测试数据

如果需要自定义测试数据：

```python
# tests/conftest.py 中添加自定义夹具
@pytest.fixture
def custom_user(db_session):
    user = User(username="testuser", email="test@example.com")
    db_session.add(user)
    db_session.commit()
    return user
```

## 🧪 验证测试环境

### 运行基本测试

```bash
# 运行单个测试文件
pytest tests/unit/test_user_controller_comprehensive.py -v

# 运行所有单元测试
pytest tests/unit/ -v

# 运行带覆盖率的测试
pytest --cov=woniunote --cov-report=html
```

### 验证测试工具

```bash
# 验证测试管理器
python scripts/test_manager.py --help

# 验证覆盖率分析器
python scripts/coverage_analyzer.py

# 验证报告生成器
python scripts/generate_test_report.py
```

### 检查测试环境健康状态

```bash
# 运行环境检查
python -c "
import sys
print(f'Python 版本: {sys.version}')
import flask
print(f'Flask 版本: {flask.__version__}')
import pytest
print('✅ 核心依赖正常')
"
```

## 🔍 故障排除

### 常见问题

#### 1. 导入错误
```bash
# 错误: ModuleNotFoundError
pip install -r requirements-test.txt
```

#### 2. 数据库连接失败
```bash
# 检查数据库文件权限
ls -la test.db

# 重新生成测试数据库
rm test.db
python scripts/test_data_manager.py
```

#### 3. 测试超时
```bash
# 增加超时时间
pytest --timeout=300

# 或在 pytest.ini 中配置
# pytest.ini
# [tool:pytest]
# timeout = 300
```

#### 4. 内存不足
```bash
# 减少并发测试数量
pytest -n 2

# 或使用内存更少的配置
export PYTHONDONTWRITEBYTECODE=1
```

### 调试技巧

```bash
# 详细输出
pytest -v -s

# 调试特定测试
pytest tests/unit/test_user_controller_comprehensive.py::TestUserController::test_login_success -v -s

# 生成调试报告
pytest --tb=long --pdbrc=.pdbrc
```

## 🌐 CI/CD 环境

### GitHub Actions 配置

项目已包含 GitHub Actions 工作流：

```yaml
# .github/workflows/ci-cd.yml
name: CI/CD Pipeline
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
        with:
          python-version: '3.8'
      - name: Install dependencies
        run: pip install -r requirements-test.txt
      - name: Run tests
        run: python scripts/test_manager.py --type all --coverage
```

### 本地 CI/CD 模拟

```bash
# 模拟 CI 环境
export CI=true
export GITHUB_ACTIONS=true

# 运行完整流水线
python scripts/test_manager.py --type all --coverage --quality
```

## 📚 相关文档

- [测试执行指南](test-execution-guide.md)
- [测试编写指南](test-writing-guide.md)
- [CI/CD 集成指南](ci-cd-integration.md)
- [问题排查指南](troubleshooting.md)

## 🎯 下一步

环境设置完成后，您可以：

1. [运行您的第一个测试](test-execution-guide.md)
2. [学习编写测试用例](test-writing-guide.md)
3. [查看测试覆盖率报告](test-reports/coverage-report.md)

---

*如遇问题，请查看 [问题排查指南](troubleshooting.md) 或提交 Issue。*
