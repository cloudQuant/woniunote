# 🔌 测试工具 API 文档

## 📋 概述

本文档详细介绍 WoniuNote 项目测试工具的 API 接口，包括测试管理器、覆盖率分析器、数据生成器等工具的使用方法和参数说明。

## 🧪 TestManager 类

### 初始化

```python
from scripts.test_manager import TestManager

# 创建测试管理器实例
manager = TestManager()
```

### 方法列表

#### `run_tests(test_type: str = "all", verbose: bool = False, coverage: bool = True) -> Dict`

运行指定类型的测试。

**参数:**
- `test_type` (str): 测试类型，可选值: "unit", "integration", "security", "performance", "e2e", "all"
- `verbose` (bool): 是否显示详细输出，默认 False
- `coverage` (bool): 是否生成覆盖率报告，默认 True

**返回值:**
```python
{
    "success": bool,
    "results": {
        "unit": {...},
        "integration": {...},
        "security": {...},
        "performance": {...}
    },
    "summary": {
        "total_tests": int,
        "passed": int,
        "failed": int,
        "coverage": float
    },
    "duration": float
}
```

**示例:**
```python
# 运行所有测试
result = manager.run_tests("all", verbose=True, coverage=True)

# 运行单元测试
result = manager.run_tests("unit")

# 检查结果
if result["success"]:
    print(f"测试通过: {result['summary']['passed']}")
    print(f"覆盖率: {result['summary']['coverage']}%")
```

#### `run_quality_checks() -> Dict`

运行代码质量检查。

**返回值:**
```python
{
    "success": bool,
    "checks": {
        "flake8": {
            "passed": bool,
            "issues": int,
            "details": str
        },
        "black": {
            "passed": bool,
            "changed_files": int
        },
        "isort": {
            "passed": bool,
            "changed_files": int
        },
        "mypy": {
            "passed": bool,
            "errors": int
        },
        "bandit": {
            "passed": bool,
            "issues": int,
            "severity": {
                "high": int,
                "medium": int,
                "low": int
            }
        }
    }
}
```

**示例:**
```python
# 运行质量检查
quality_result = manager.run_quality_checks()

# 检查 flake8 结果
if quality_result["checks"]["flake8"]["passed"]:
    print("✅ 代码风格检查通过")
else:
    print(f"❌ 发现 {quality_result['checks']['flake8']['issues']} 个风格问题")
```

## 📊 CoverageAnalyzer 类

### 初始化

```python
from scripts.coverage_analyzer import CoverageAnalyzer

# 创建覆盖率分析器实例
analyzer = CoverageAnalyzer()
```

### 方法列表

#### `run_coverage_analysis() -> bool`

运行完整的覆盖率分析。

**返回值:** bool - 分析是否成功

**示例:**
```python
# 运行覆盖率分析
success = analyzer.run_coverage_analysis()

if success:
    print("✅ 覆盖率分析完成")
else:
    print("❌ 覆盖率分析失败")
```

#### `analyze_coverage_gaps() -> Dict`

分析覆盖率空白点。

**返回值:**
```python
{
    "total_files": int,
    "files_with_gaps": int,
    "gaps": [
        {
            "file": str,
            "total_lines": int,
            "covered_lines": int,
            "missing_lines": [int],
            "coverage_percent": float
        }
    ],
    "summary": {
        "estimated_coverage": float,
        "high_priority_gaps": int,
        "medium_priority_gaps": int,
        "low_priority_gaps": int
    }
}
```

**示例:**
```python
# 分析覆盖率空白
gaps = analyzer.analyze_coverage_gaps()

print(f"发现 {gaps['files_with_gaps']} 个文件有覆盖空白")
print(f"估算覆盖率: {gaps['summary']['estimated_coverage']}%")

# 显示高优先级空白
for gap in gaps["gaps"]:
    if gap["coverage_percent"] < 80:
        print(f"🔴 {gap['file']}: {gap['coverage_percent']}%")
```

#### `generate_coverage_report(output_format: str = "json") -> str`

生成覆盖率报告。

**参数:**
- `output_format` (str): 输出格式，可选值: "json", "html", "markdown"

**返回值:** str - 报告文件路径

**示例:**
```python
# 生成 JSON 报告
json_report = analyzer.generate_coverage_report("json")
print(f"JSON 报告已保存: {json_report}")

# 生成 HTML 报告
html_report = analyzer.generate_coverage_report("html")
print(f"HTML 报告已保存: {html_report}")
```

## 🎲 TestDataManager 类

### 初始化

```python
from scripts.test_data_manager import TestDataManager

# 创建测试数据管理器实例
data_manager = TestDataManager()
```

### 方法列表

#### `generate_test_database(db_path: Optional[str] = None) -> str`

生成测试数据库。

**参数:**
- `db_path` (Optional[str]): 数据库文件路径，默认使用临时文件

**返回值:** str - 数据库文件路径

**示例:**
```python
# 生成测试数据库
db_path = data_manager.generate_test_database()
print(f"测试数据库已创建: {db_path}")

# 使用自定义路径
custom_db = data_manager.generate_test_database("/tmp/test.db")
```

#### `generate_test_data(db_path: str) -> Dict`

生成测试数据。

**参数:**
- `db_path` (str): 数据库文件路径

**返回值:**
```python
{
    "users": int,        # 生成的用户数
    "articles": int,     # 生成的文章数
    "comments": int,     # 生成的评论数
    "categories": int,   # 生成的分类数
    "cards": int,        # 生成的卡片数
    "todos": int         # 生成的待办事项数
}
```

**示例:**
```python
# 生成测试数据
stats = data_manager.generate_test_data(db_path)

print("生成的数据统计:")
for table, count in stats.items():
    print(f"  {table}: {count}")
```

#### `setup_test_environment() -> Dict`

设置完整的测试环境。

**返回值:**
```python
{
    "database": {
        "path": str,
        "size_mb": float,
        "tables": [str]
    },
    "files": {
        "test_dir": str,
        "config_file": str,
        "log_file": str
    },
    "config": {
        "env_file": str,
        "yaml_config": str
    }
}
```

**示例:**
```python
# 设置测试环境
env_setup = data_manager.setup_test_environment()

print("测试环境设置完成:")
print(f"数据库: {env_setup['database']['path']}")
print(f"测试目录: {env_setup['files']['test_dir']}")
```

#### `cleanup_test_data(older_than_days: int = 7) -> int`

清理旧的测试数据。

**参数:**
- `older_than_days` (int): 清理多少天前的文件，默认7天

**返回值:** int - 清理的文件数

**示例:**
```python
# 清理7天前的测试数据
cleaned_count = data_manager.cleanup_test_data(7)
print(f"清理了 {cleaned_count} 个旧测试文件")

# 清理30天前的测试数据
old_cleaned = data_manager.cleanup_test_data(30)
```

#### `get_test_data_stats() -> Dict`

获取测试数据统计信息。

**返回值:**
```python
{
    "database_stats": {
        "total_databases": int,
        "total_size_mb": float,
        "oldest_file_days": int
    },
    "file_stats": {
        "total_files": int,
        "total_size_mb": float,
        "by_type": {
            "images": int,
            "documents": int,
            "logs": int
        }
    },
    "recent_activity": [
        {
            "date": str,
            "databases_created": int,
            "files_generated": int
        }
    ]
}
```

**示例:**
```python
# 获取数据统计
stats = data_manager.get_test_data_stats()

print(f"总数据库数: {stats['database_stats']['total_databases']}")
print(f"总文件大小: {stats['database_stats']['total_size_mb']:.2f} MB")
```

## 📋 TestReportGenerator 类

### 初始化

```python
from scripts.generate_test_report import TestReportGenerator

# 创建报告生成器实例
report_generator = TestReportGenerator()
```

### 方法列表

#### `generate_comprehensive_report() -> str`

生成综合测试报告。

**返回值:** str - HTML 报告文件路径

**示例:**
```python
# 生成综合报告
report_path = report_generator.generate_comprehensive_report()
print(f"综合报告已生成: {report_path}")

# 在浏览器中打开
import webbrowser
webbrowser.open(f"file://{report_path}")
```

#### `generate_report_for_type(test_type: str) -> str`

生成特定类型的测试报告。

**参数:**
- `test_type` (str): 测试类型 ("unit", "integration", "security", "performance")

**返回值:** str - 报告文件路径

**示例:**
```python
# 生成单元测试报告
unit_report = report_generator.generate_report_for_type("unit")

# 生成安全测试报告
security_report = report_generator.generate_report_for_type("security")
```

## 🔧 实用工具函数

### 数据库工具

```python
from woniunote.common.database import get_db, init_db

# 获取数据库会话
db_session = get_db()

# 初始化数据库
init_db(app)
```

### Mock 工具

```python
from unittest.mock import Mock, patch, MagicMock

# 创建 Mock 对象
mock_user = Mock()
mock_user.id = 1
mock_user.username = "testuser"

# 使用 patch 装饰器
@patch('woniunote.services.user_service.User')
def test_user_creation(mock_user_class):
    mock_instance = Mock()
    mock_user_class.return_value = mock_instance

    # 测试代码
    pass

# 使用上下文管理器
with patch('module.function') as mock_func:
    mock_func.return_value = expected_value
    # 测试代码
```

### 断言工具

```python
# 基本断言
assert result == expected
assert len(items) > 0
assert user.is_active is True

# 异常断言
with pytest.raises(ValueError):
    invalid_operation()

# 近似断言
assert abs(result - expected) < 0.01

# 集合断言
assert set(results) == set(expected)
```

### 测试夹具

```python
# conftest.py 中的常用夹具
@pytest.fixture
def app():
    """应用实例"""
    app = create_app('testing')
    with app.app_context():
        yield app

@pytest.fixture
def client(app):
    """测试客户端"""
    return app.test_client()

@pytest.fixture
def db_session(app):
    """数据库会话"""
    # 数据库设置代码
    yield session
    # 清理代码

@pytest.fixture
def test_user(db_session):
    """测试用户"""
    user = User(username="testuser", email="test@example.com")
    db_session.add(user)
    db_session.commit()
    return user
```

## 🚀 使用示例

### 完整测试流程

```python
from scripts.test_manager import TestManager
from scripts.coverage_analyzer import CoverageAnalyzer
from scripts.test_data_manager import TestDataManager

def run_complete_test_suite():
    """运行完整的测试套件"""

    # 1. 设置测试环境
    data_manager = TestDataManager()
    env = data_manager.setup_test_environment()
    print(f"✅ 测试环境已设置: {env['database']['path']}")

    # 2. 运行所有测试
    test_manager = TestManager()
    test_results = test_manager.run_tests("all", verbose=True, coverage=True)

    if test_results["success"]:
        print(f"✅ 测试通过: {test_results['summary']['passed']}")
        print(f"📊 覆盖率: {test_results['summary']['coverage']}%")
    else:
        print(f"❌ 测试失败: {test_results['summary']['failed']}")
        return False

    # 3. 分析覆盖率
    analyzer = CoverageAnalyzer()
    gaps = analyzer.analyze_coverage_gaps()

    if gaps["summary"]["high_priority_gaps"] > 0:
        print(f"⚠️ 发现 {gaps['summary']['high_priority_gaps']} 个高优先级覆盖空白")
        return False

    # 4. 生成报告
    report_path = analyzer.generate_coverage_report("html")
    print(f"📋 报告已生成: {report_path}")

    return True

# 执行完整测试
if __name__ == "__main__":
    success = run_complete_test_suite()
    exit(0 if success else 1)
```

### CI/CD 集成

```yaml
# .github/workflows/ci-cd.yml
- name: Run complete test suite
  run: python -c "from examples.complete_test import run_complete_test_suite; run_complete_test_suite()"

- name: Generate test report
  run: |
    python scripts/generate_test_report.py
    python scripts/coverage_analyzer.py --report html

- name: Upload test artifacts
  uses: actions/upload-artifact@v3
  with:
    name: test-results
    path: |
      test-reports/
      htmlcov/
      coverage.xml
```

## 📚 相关文档

- [测试环境设置指南](../user-guides/test-environment-setup.md)
- [测试执行指南](../user-guides/test-execution-guide.md)
- [测试编写指南](../user-guides/test-writing-guide.md)
- [CI/CD 集成指南](../user-guides/ci-cd-integration.md)

---

*API 文档会随着工具更新而持续维护。*
