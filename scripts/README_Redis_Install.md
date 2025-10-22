# Windows Redis 自动安装配置脚本

## 概述

这个Python脚本用于在Windows系统上自动安装和配置Redis环境，解决WoniuNote项目中"Redis客户端未配置，Redis缓存功能不可用"的问题。

## 功能特性

- ✅ 自动下载Redis for Windows
- ✅ 自动安装Redis到系统目录
- ✅ 创建和配置Redis配置文件
- ✅ 安装Redis Windows服务
- ✅ 自动启动Redis服务
- ✅ 添加Redis到系统PATH
- ✅ 创建管理脚本
- ✅ 验证安装结果
- ✅ 测试Redis连接

## 系统要求

- Windows 10/11 或 Windows Server 2016+
- Python 3.7+
- 管理员权限（脚本会自动请求）
- 网络连接（用于下载Redis）

## 使用方法

### 1. 基本安装

```bash
# 以管理员身份运行PowerShell或命令提示符
cd F:\source_code\woniunote
python scripts/install_redis_windows.py
```

### 2. 脚本会自动执行以下步骤：

1. **权限检查** - 检查并请求管理员权限
2. **环境检测** - 检查是否已安装Redis
3. **下载Redis** - 从官方仓库下载Redis 5.0.14.1
4. **解压安装** - 解压并安装到 `C:\Program Files\Redis`
5. **配置文件** - 创建优化的Redis配置文件
6. **服务安装** - 安装Redis Windows服务
7. **服务启动** - 启动Redis服务
8. **环境配置** - 添加到系统PATH
9. **验证测试** - 验证安装和连接

## 安装后的文件结构

```
C:\Program Files\Redis\
├── redis-server.exe          # Redis服务器
├── redis-cli.exe            # Redis命令行客户端
├── redis.windows.conf       # Redis配置文件
├── redis.log               # Redis日志文件
├── dump.rdb                # Redis数据文件
├── start_redis.bat         # 启动服务脚本
├── stop_redis.bat          # 停止服务脚本
└── redis_status.bat        # 状态检查脚本
```

## Redis配置说明

脚本会创建优化的Redis配置，主要参数：

```ini
# 网络配置
port 6379                    # 端口
bind 127.0.0.1              # 绑定地址

# 内存管理
maxmemory 256mb              # 最大内存
maxmemory-policy allkeys-lru # 内存回收策略

# 持久化
save 900 1                   # 900秒内至少1个key变化时保存
save 300 10                  # 300秒内至少10个key变化时保存
save 60 10000               # 60秒内至少10000个key变化时保存

# 日志
loglevel notice              # 日志级别
logfile "C:\Program Files\Redis\redis.log"
```

## 服务管理

### 使用Windows服务管理器
```bash
# 启动服务
sc start Redis

# 停止服务
sc stop Redis

# 查看服务状态
sc query Redis
```

### 使用提供的批处理脚本
```bash
# 启动Redis
C:\Program Files\Redis\start_redis.bat

# 停止Redis
C:\Program Files\Redis\stop_redis.bat

# 检查状态
C:\Program Files\Redis\redis_status.bat
```

### 使用Redis CLI
```bash
# 测试连接
redis-cli ping

# 连接到Redis
redis-cli

# 查看信息
redis-cli info
```

## WoniuNote项目配置

安装完成后，WoniuNote项目会自动使用以下Redis配置：

```python
# configs/config.py 中的配置
REDIS_HOST = '127.0.0.1'     # 或环境变量 REDIS_HOST
REDIS_PORT = 6379            # 或环境变量 REDIS_PORT  
REDIS_DB = 0                 # 或环境变量 REDIS_DB
REDIS_PASSWORD = None        # 或环境变量 REDIS_PASSWORD
```

## 环境变量配置

可以通过以下环境变量自定义Redis连接：

```bash
# Windows环境变量设置
set REDIS_HOST=127.0.0.1
set REDIS_PORT=6379
set REDIS_DB=0
set REDIS_PASSWORD=
```

## 验证安装

安装完成后，脚本会自动验证以下项目：

- ✅ Redis文件安装
- ✅ 配置文件创建
- ✅ Windows服务运行
- ✅ Redis连接测试
- ✅ PATH环境变量

## 故障排除

### 1. 权限问题
```
错误：需要管理员权限
解决：右键"以管理员身份运行"PowerShell或命令提示符
```

### 2. 下载失败
```
错误：下载Redis失败
解决：检查网络连接，或手动下载Redis放到temp目录
```

### 3. 服务启动失败
```
错误：Redis服务启动失败
解决：
1. 检查端口6379是否被占用：netstat -an | findstr 6379
2. 检查防火墙设置
3. 查看Redis日志文件
```

### 4. 连接测试失败
```
错误：Redis连接测试失败
解决：
1. 确认服务正在运行：sc query Redis
2. 检查配置文件中的bind和port设置
3. 使用redis-cli ping测试
```

### 5. PATH配置问题
```
错误：redis-cli命令不可用
解决：
1. 重启命令提示符
2. 手动添加C:\Program Files\Redis到PATH
3. 使用完整路径：C:\Program Files\Redis\redis-cli.exe
```

## 卸载Redis

如需卸载Redis：

```bash
# 1. 停止服务
sc stop Redis

# 2. 删除服务
sc delete Redis

# 3. 删除安装目录
rmdir /s "C:\Program Files\Redis"

# 4. 从PATH中移除Redis路径（手动编辑环境变量）
```

## 高级配置

### 修改Redis配置

编辑配置文件：`C:\Program Files\Redis\redis.windows.conf`

常用配置项：
```ini
# 修改端口
port 6380

# 设置密码
requirepass your_password

# 修改最大内存
maxmemory 512mb

# 启用AOF持久化
appendonly yes
```

修改配置后重启服务：
```bash
sc stop Redis
sc start Redis
```

### 性能优化

对于生产环境，建议调整以下配置：

```ini
# 增加最大内存
maxmemory 1gb

# 调整保存策略
save 3600 1
save 300 100
save 60 10000

# 启用压缩
rdbcompression yes

# 优化网络
tcp-keepalive 300
timeout 0
```

## 安全建议

1. **设置密码**：在生产环境中设置Redis密码
2. **绑定地址**：仅绑定到需要的网络接口
3. **防火墙**：配置防火墙规则限制访问
4. **定期备份**：定期备份Redis数据文件

## 支持与反馈

如遇到问题或需要帮助：

1. 查看Redis日志：`C:\Program Files\Redis\redis.log`
2. 检查Windows事件日志
3. 运行状态检查脚本：`redis_status.bat`
4. 提交Issue到WoniuNote项目仓库

## 版本信息

- 脚本版本：1.0.0
- Redis版本：5.0.14.1
- 支持系统：Windows 10/11, Windows Server 2016+
- Python要求：3.7+

---

**注意**：此脚本专为WoniuNote项目设计，确保Redis缓存功能正常工作。安装完成后，项目的缓存功能将自动启用。
