# 🧪 测试命令速查表

## 🚀 快速命令

```bash
# 默认（推荐）- 并行 + 覆盖率
python tests/run_all_tests.py

# 快速验证 - 2-3分钟
python tests/run_all_tests.py --fast --no-coverage

# 完整测试 - 5-10分钟
python tests/run_all_tests.py

# 调试模式 - 详细日志
python tests/run_all_tests.py --debug

# 顺序执行 - 无并行
python tests/run_all_tests.py --sequential

# 仅覆盖率分析
python tests/run_all_tests.py --coverage
```

## 📊 输出说明

```
🖥️  系统资源检测              ← 显示CPU/内存/workers数
📊 测试分布分析               ← 显示测试文件分类
🚀 执行测试                   ← 实时测试执行
📊 测试执行报告               ← 执行结果汇总
```

## 📈 覆盖率查看

```bash
# HTML报告（推荐）
open htmlcov/index.html        # macOS
start htmlcov\index.html       # Windows
xdg-open htmlcov/index.html    # Linux

# JSON数据
cat coverage.json
```

## 🎯 常见场景

| 场景 | 命令 | 耗时 |
|-----|------|------|
| 快速验证 | `--fast --no-coverage` | 2-3分钟 |
| 日常开发 | 默认（无参数） | 5-10分钟 |
| 问题诊断 | `--debug` | 5-10分钟 |
| 深度调试 | `--sequential --verbose` | 10-30分钟 |
| 覆盖率分析 | `--coverage` | 5-10分钟 |

## 🔧 传统pytest命令

```bash
# 基础
pytest tests/ -v
pytest tests/ -v -n auto                          # 并行

# 覆盖率
pytest tests/ --cov=woniunote --cov-report=html   # HTML报告
pytest tests/ --cov=woniunote --cov-report=term   # 终端报告

# 特定测试
pytest tests/unit/test_file.py -v                 # 特定文件
pytest tests/ -k "test_name" -v                   # 特定函数
pytest tests/ -k "not slow" -v                    # 排除某些测试

# 调试
pytest tests/ -v -s                               # 显示print
pytest tests/ -x                                  # 第一个失败后停止
pytest tests/ --tb=long                           # 详细错误信息
pytest tests/ --pdb                               # 进入debugger
```

## 📝 参数说明

| 参数 | 说明 | 影响 |
|-----|------|------|
| `--parallel` | 显式并行 | 自动计算workers |
| `--fast` | 快速模式 | 跳过慢速测试 |
| `--debug` | 调试模式 | 详细日志 |
| `--verbose` | 详细输出 | 所有细节 |
| `--sequential` | 顺序执行 | 无并行 |
| `--coverage` | 仅覆盖率 | 专注分析 |
| `--no-coverage` | 无覆盖率 | 快速模式 |

## ⏱️ 执行时间参考

```
快速测试：    < 1秒
常规测试：    1-10秒
集成测试：    10-120秒
慢速测试：    > 120秒

并行模式：    5-10分钟（所有测试）
快速模式：    2-3分钟（快速 + 常规）
顺序执行：    15-30分钟（单线程）
```

## 🛠️ 故障排除

```bash
# 并行失败 → 顺序执行
python tests/run_all_tests.py --sequential

# 覆盖率问题 → 清除缓存
rm -rf .coverage htmlcov/ coverage.json
python tests/run_all_tests.py

# 超时问题 → 快速模式
python tests/run_all_tests.py --fast

# 内存问题 → 减少worker
pytest tests/ -n 2
```

## 📚 详细文档

- **完整指南**: `docs/TEST_GUIDE.md`
- **快速参考**: `tests/README.md`
- **优化总结**: `docs/TEST_OPTIMIZATION_SUMMARY.md`

## 💡 使用技巧

1. **第一次运行较慢** - 等待缓存初始化
2. **查看详细信息** - 加 `--verbose` 或 `--debug`
3. **加快执行** - 使用 `--fast` 跳过慢速测试
4. **自动并行** - 脚本会自动优化worker数
5. **覆盖率报告** - 打开 `htmlcov/index.html` 查看

---

**版本**: v3.0 | **更新**: 2025-01-10
