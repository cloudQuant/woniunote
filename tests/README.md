# 🧪 WoniuNote 测试系统

完整的、优化的测试执行和覆盖率分析系统。

> ⚠️ **迭代 8 归档标注：本目录测试仅适用于旧版 Python Flask 后端（`woniunote/` 模块）。**
> 这些用例依赖 Flask 应用上下文，**无法用于当前 dev_cpp 分支的 C++ Drogon 后端**，
> 也不应计入新栈覆盖率。新栈测试：C++ 见 `backend_cpp/tests/`（`ctest`），
> 前端见 `frontend/src/**/*.spec.js`（`npm test`），CI 见
> `.github/workflows/cpp-vue-ci.yml`。保留本目录用于历史参考与 legacy 维护。

## 🚀 快速开始

### 最简单的方式

```bash
python tests/run_all_tests.py
```

这会：
- ✅ 自动并行执行所有测试
- ✅ 智能分类测试文件
- ✅ 生成代码覆盖率报告
- 📊 输出详细的执行统计

### 完整的安装步骤

```bash
# 1. 安装项目
pip install -e .

# 2. 安装测试依赖
pip install -r requirements.txt
playwright install

# 3. 运行测试
python tests/run_all_tests.py
```

## 📚 使用方法

| 命令 | 说明 | 用途 |
|------|------|------|
| `python tests/run_all_tests.py` | 默认：并行 + 覆盖率 | 日常开发（推荐） |
| `python tests/run_all_tests.py --fast` | 快速模式 | 快速验证改动 |
| `python tests/run_all_tests.py --debug` | 调试模式 | 问题诊断 |
| `python tests/run_all_tests.py --sequential` | 顺序执行 | 深度调试 |
| `python tests/run_all_tests.py --coverage` | 仅覆盖率 | 覆盖率分析 |

## 📊 测试统计

```
📊 测试分布分析:
   总计: 50 个测试文件
   ⚡ 快速测试: 15 个
   🔧 常规测试: 25 个
   🔗 集成测试: 8 个
   🐢 慢速测试: 2 个
```

## 📈 覆盖率报告

执行后生成的报告：

- **HTML报告**: `htmlcov/index.html` - 详细的web界面
- **JSON数据**: `coverage.json` - 机器可读格式
- **终端输出**: 实时的覆盖率统计

## ⚙️ 执行模式

### 并行执行（默认）
自动计算最优worker数量，充分利用系统资源。

### 快速模式
```bash
python tests/run_all_tests.py --fast
```
- 跳过慢速和集成测试
- 执行时间：2-5分钟

### 调试模式
```bash
python tests/run_all_tests.py --debug
```
- 详细的执行日志
- 完整的错误信息
- 适合问题诊断

### 顺序执行
```bash
python tests/run_all_tests.py --sequential
```
- 逐个运行测试
- 便于定位复杂问题

## 🎯 常用场景

### 场景1：快速验证改动
```bash
python tests/run_all_tests.py --fast --no-coverage
```
耗时：2-3分钟

### 场景2：提交前完整测试
```bash
python tests/run_all_tests.py
```
耗时：5-10分钟

### 场景3：调试测试失败
```bash
python tests/run_all_tests.py --debug
pytest tests/unit/test_specific.py -v -s  # 针对特定文件
```

### 场景4：分析覆盖率
```bash
python tests/run_all_tests.py --coverage
# 然后打开 htmlcov/index.html
```

## 🛠️ 传统pytest命令

如果不想使用新脚本，也可以直接用pytest：

```bash
# 运行所有测试
pytest tests/ -v

# 并行执行
pytest tests/ -v -n auto

# 生成覆盖率
pytest tests/ -v --cov=woniunote --cov-report=html

# 运行特定测试
pytest tests/unit/test_common_utils.py -v

# 显示print输出
pytest tests/ -v -s

# 在第一个失败时停止
pytest tests/ -x
```

## 📋 配置文件

- `pytest.ini` - pytest配置
- `conftest.py` - pytest fixtures和hooks
- `.coveragerc` 或 `setup.cfg` - coverage配置

## 🔧 故障排除

**问题：并行执行失败**
```bash
# 尝试顺序执行
python tests/run_all_tests.py --sequential
```

**问题：覆盖率收集失败**
```bash
# 清除旧数据
rm -rf .coverage htmlcov/ coverage.json

# 重新运行
python tests/run_all_tests.py
```

**问题：测试超时**
```bash
# 使用快速模式
python tests/run_all_tests.py --fast
```

## 📖 详细文档

更多详细的使用说明见：[TEST_GUIDE.md](../docs/TEST_GUIDE.md)

包含内容：
- 详细的执行模式说明
- 报告生成和解读
- 最佳实践
- 进阶用法
- CI/CD集成

## 📊 测试质量指标

- **测试总数**: 300+
- **通过率**: 100%
- **代码覆盖率**: 85%+
- **执行时间**: 5-15分钟

## 💡 提示

1. **首次运行会较慢**（缓存初始化），后续会加快
2. **确保有4GB+内存**用于并行执行
3. **SSD会显著提升速度**
4. **使用 `--verbose` 查看详细信息**
5. **覆盖率报告在 `htmlcov/index.html`**

## 🎓 学习资源

- [pytest官方文档](https://docs.pytest.org/)
- [pytest-xdist并行插件](https://pytest-xdist.readthedocs.io/)
- [coverage.py文档](https://coverage.readthedocs.io/)

---

**版本**: v3.0 (2025-01-10)
**状态**: ✅ 生产就绪
