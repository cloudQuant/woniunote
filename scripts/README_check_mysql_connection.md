# MySQL连接检测脚本

## 📝 脚本简介

`check_mysql_connection.py` 是一个用于检测当前配置的数据库连接状态的工具脚本。支持MySQL和SQLite数据库的连接检测。

## 🚀 功能特性

- ✅ **自动配置发现** - 自动查找并解析项目配置文件
- ✅ **多数据库支持** - 支持MySQL和SQLite数据库
- ✅ **连接测试** - 实际连接数据库并执行基本查询
- ✅ **配置验证** - 验证数据库配置的正确性
- ✅ **详细报告** - 提供详细的连接状态和数据库信息
- ✅ **依赖检查** - 自动检查所需的Python包
- ✅ **错误诊断** - 提供详细的错误信息和解决建议

## 🛠️ 使用方法

### 基本用法

```bash
# 检测当前配置的数据库连接
python scripts/check_mysql_connection.py

# 显示详细输出
python scripts/check_mysql_connection.py --verbose

# 仅测试配置解析，不实际连接
python scripts/check_mysql_connection.py --test-only
```

### 高级用法

```bash
# 指定配置文件
python scripts/check_mysql_connection.py --config-file configs/mysql_test_config.yaml

# 强制使用MySQL配置类型
python scripts/check_mysql_connection.py --config-type mysql

# 组合使用多个选项
python scripts/check_mysql_connection.py --verbose --config-file configs/mysql_test_config.yaml --test-only
```

## 📋 命令行参数

| 参数 | 简写 | 说明 | 默认值 |
|------|------|------|--------|
| `--verbose` | `-v` | 显示详细输出 | False |
| `--config-type` | - | 指定配置类型 (mysql/auto) | auto |
| `--config-file` | - | 指定配置文件路径 | 自动搜索 |
| `--test-only` | - | 仅测试配置解析 | False |
| `--help` | `-h` | 显示帮助信息 | - |

## 🔧 配置文件格式

### SQLAlchemy URI 格式

```yaml
database:
  SQLALCHEMY_DATABASE_URI: mysql://username:password@host:port/database
  SQLALCHEMY_TRACK_MODIFICATIONS: false
```

### 分离配置格式

```yaml
database:
  host: localhost
  port: 3306
  username: mysql_user
  password: mysql_password
  name: database_name
```

### SQLite 配置

```yaml
database:
  SQLALCHEMY_DATABASE_URI: sqlite:///path/to/database.db
```

## 📂 配置文件搜索路径

脚本会按以下顺序搜索配置文件：

1. `configs/user_password_config.yaml`
2. `woniunote/configs/user_password_config.yaml`
3. 用户指定的配置文件 (`--config-file`)

## 📊 输出示例

### 成功连接示例

```
[2025-08-21 09:13:42] INFO: === MySQL数据库连接检测开始 ===
[2025-08-21 09:13:42] INFO: ✓ pymysql 已安装
[2025-08-21 09:13:42] INFO: ✓ PyYAML 已安装
[2025-08-21 09:13:42] INFO: 找到配置文件: configs/user_password_config.yaml
[2025-08-21 09:13:42] SUCCESS: MySQL连接成功！
[2025-08-21 09:13:42] INFO: MySQL版本: 8.0.32
[2025-08-21 09:13:42] INFO: 当前数据库: woniunote
[2025-08-21 09:13:42] INFO: 数据库中的表数量: 15
[2025-08-21 09:13:42] SUCCESS: === 数据库连接检测成功 ===
```

### 配置解析测试示例

```
[2025-08-21 09:13:42] SUCCESS: === 配置解析测试完成 ===
[2025-08-21 09:13:42] INFO: 数据库类型: mysql
[2025-08-21 09:13:42] INFO: MySQL主机: localhost:3306
[2025-08-21 09:13:42] INFO: 数据库名: test_woniunote
[2025-08-21 09:13:42] INFO: 用户名: test_user
[2025-08-21 09:13:42] SUCCESS: 配置解析成功
```

## ❌ 常见错误及解决方案

### 1. 缺少依赖包

**错误信息：**
```
[2025-08-21 09:13:42] ERROR: 缺少依赖包: pymysql
[2025-08-21 09:13:42] ERROR: 请运行: pip install pymysql
```

**解决方案：**
```bash
pip install pymysql PyYAML
```

### 2. 配置文件未找到

**错误信息：**
```
[2025-08-21 09:13:42] ERROR: 未找到配置文件
```

**解决方案：**
- 确保配置文件存在于正确路径
- 使用 `--config-file` 指定配置文件路径
- 检查配置文件权限

### 3. MySQL连接失败

**错误信息：**
```
[2025-08-21 09:13:42] ERROR: MySQL连接失败: (2003, "Can't connect to MySQL server")
```

**解决方案：**
- 检查MySQL服务是否运行
- 验证主机地址和端口号
- 确认用户名和密码正确
- 检查防火墙设置

### 4. 数据库不存在

**错误信息：**
```
[2025-08-21 09:13:42] ERROR: MySQL连接失败: (1049, "Unknown database 'database_name'")
```

**解决方案：**
- 创建目标数据库
- 检查数据库名称拼写
- 确认用户有访问该数据库的权限

## 🔍 检测内容

脚本会检测以下内容：

### 环境检查
- ✅ 检查必需的Python包 (`pymysql`, `PyYAML`)
- ✅ 检查配置文件是否存在和可读

### 配置验证
- ✅ 配置文件格式验证
- ✅ 数据库连接参数解析
- ✅ 配置完整性检查

### 连接测试
- ✅ 数据库连接建立
- ✅ 基本查询权限测试
- ✅ 数据库版本获取
- ✅ 表结构检查

### 信息收集
- ✅ 数据库版本信息
- ✅ 当前数据库名称
- ✅ 数据库表数量统计
- ✅ 表名列表 (详细模式)

## 🎯 使用场景

### 开发环境检查
```bash
# 快速检查开发环境数据库连接
python scripts/check_mysql_connection.py

# 详细检查开发环境配置
python scripts/check_mysql_connection.py --verbose
```

### 生产环境验证
```bash
# 验证生产环境配置但不实际连接
python scripts/check_mysql_connection.py --config-file configs/production_config.yaml --test-only

# 连接测试生产环境数据库
python scripts/check_mysql_connection.py --config-file configs/production_config.yaml --verbose
```

### 配置文件测试
```bash
# 测试新的MySQL配置
python scripts/check_mysql_connection.py --config-file configs/new_mysql_config.yaml --test-only

# 验证配置并连接测试
python scripts/check_mysql_connection.py --config-file configs/new_mysql_config.yaml
```

## 📦 依赖要求

- Python 3.6+
- PyMySQL (MySQL连接)
- PyYAML (配置文件解析)
- sqlite3 (内置, SQLite支持)

## 🔐 安全注意事项

- ❗ 配置文件包含敏感信息，请确保适当的文件权限
- ❗ 不要在日志中暴露数据库密码
- ❗ 生产环境使用时建议使用只读用户进行连接测试
- ❗ 定期更新数据库连接密码

## 🚀 集成建议

### CI/CD 集成
```bash
# 在部署前检查数据库连接
python scripts/check_mysql_connection.py --config-file $CONFIG_FILE
if [ $? -eq 0 ]; then
    echo "数据库连接正常，继续部署"
else
    echo "数据库连接失败，停止部署"
    exit 1
fi
```

### 健康检查
```bash
# 定期健康检查
*/5 * * * * /path/to/python /path/to/scripts/check_mysql_connection.py >/dev/null 2>&1 || echo "数据库连接异常" | mail admin@example.com
```

---

💡 **提示**: 如果您在使用过程中遇到问题，请先使用 `--verbose` 选项获取详细的错误信息，这将有助于快速定位和解决问题。