# WoniuNote Playwright 测试套件

本测试套件使用 Playwright 和 pytest 为 WoniuNote 应用提供端到端功能测试。

## 测试架构

测试套件按功能模块划分为多个文件：

- `test_basic_navigation.py` - 基本页面导航测试
- `test_user_auth.py` - 用户注册、登录和认证测试
- `test_article_features.py` - 文章查看、创建和编辑测试
- `test_comment_features.py` - 评论相关功能测试
- `test_favorite_features.py` - 收藏功能测试

## 前置需求

1. Python 3.7+ 已安装
2. WoniuNote 项目依赖已安装：`pip install -r requirements.txt`
3. MySQL 数据库已配置并运行
4. 浏览器已安装（Chrome、Firefox 或 Safari）

## 安装 Playwright

运行以下命令安装 Playwright 和必要的浏览器：

```bash
pip install playwright
playwright install
```

## 运行测试

### 方法一：使用提供的脚本

我们提供了一个便捷的脚本自动启动Flask服务器并运行测试：

```bash
# 运行所有测试（可视模式）
python tests/run_tests.py

# 运行所有测试（无头模式）
python tests/run_tests.py --headless

# 运行特定测试文件
python tests/run_tests.py --test-file test_user_auth.py

# 使用自定义端口运行
python tests/run_tests.py --port 5001

# 如果服务器已在运行，跳过启动服务器
python tests/run_tests.py --skip-server
```

### 方法二：手动运行

1. 首先启动 Flask 服务器：

```bash
cd d:\source_code\woniunote
set FLASK_APP=woniunote.app
set FLASK_ENV=testing
flask run
```

2. 然后在另一个终端中运行测试：

```bash
cd d:\source_code\woniunote
pytest tests/test_basic_navigation.py -v
```

## 测试数据准备

某些测试假设数据库中存在以下数据：

1. 至少一个用户账号（如 administrator/admin123）
2. 至少一篇文章（ID为1）
3. 至少有一些评论和收藏

如果您的数据库是空的，有些测试可能会失败。您可以先手动创建一些测试数据，或修改测试以创建所需数据。

## 验证码处理

本测试套件中的验证码处理有两种方式：

1. **测试环境中禁用验证码**：理想情况下，测试环境应配置为接受任何验证码（如"1234"）
2. **OCR识别**：或集成OCR服务识别验证码

## 常见问题解决

1. **元素选择器不匹配**：如果测试失败，显示元素无法找到，请检查您的HTML元素类名和ID是否与测试中使用的选择器匹配。
2. **验证码问题**：确保测试环境中验证码处理得当，或调整测试绕过验证码。
3. **数据库依赖**：某些测试假设特定数据存在，请确保数据库状态与测试预期一致。

## 定制测试

您可以根据项目的实际HTML结构和功能流程，调整选择器和测试步骤。每个测试文件都有清晰的注释说明其目的和假设条件。

## 持续集成

这些测试可以集成到CI/CD流程中：

```yaml
# 示例GitHub Actions配置
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          playwright install
      - name: Run tests
        run: python tests/run_tests.py --headless
```
