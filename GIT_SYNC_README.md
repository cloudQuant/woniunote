# Git 双仓库同步功能

本项目已配置同时推送到 Gitee 和 GitHub 的功能。

## 仓库配置

当前配置了两个远程仓库：
- **Gitee**: `https://gitee.com/yunjinqi/woniunote.git`
- **GitHub**: `https://github.com/cloudQuant/woniunote.git`

## 使用方法

### 方法一：使用推送脚本（推荐）

#### Windows 用户
```bash
# 使用批处理脚本
push_to_both.bat "你的提交信息"

# 或者使用Python脚本
python push_to_both.py "你的提交信息"
```

#### Linux/Mac 用户
```bash
# 使用Shell脚本
./push_to_both.sh "你的提交信息"

# 或者使用Python脚本
python3 push_to_both.py "你的提交信息"
```

### 方法二：手动推送

```bash
# 添加文件
git add .

# 提交更改
git commit -m "你的提交信息"

# 推送到Gitee
git push gitee

# 推送到GitHub
git push github
```

### 方法三：使用Git别名（可选）

可以设置Git别名来简化操作：

```bash
# 设置别名
git config alias.push-both '!f() { git push gitee && git push github; }; f'

# 使用别名
git push-both
```

## 脚本功能

### push_to_both.py
- Python脚本，跨平台兼容
- 自动添加所有文件
- 自动提交更改
- 同时推送到两个仓库
- 详细的错误处理和状态显示

### push_to_both.bat
- Windows批处理脚本
- 支持中文显示
- 自动处理提交信息

### push_to_both.sh
- Linux/Mac Shell脚本
- 支持命令行参数
- 错误处理机制

## 注意事项

1. **首次使用**：确保已经配置好Git的用户名和邮箱
2. **权限设置**：确保对两个仓库都有推送权限
3. **网络连接**：确保能够访问Gitee和GitHub
4. **分支同步**：建议在两个仓库中保持相同的分支结构

## 故障排除

### 推送失败
如果某个仓库推送失败，脚本会继续尝试推送另一个仓库，并在控制台显示错误信息。

### 权限问题
```bash
# 检查远程仓库配置
git remote -v

# 重新配置远程仓库（如果需要）
git remote set-url gitee https://gitee.com/yunjinqi/woniunote.git
git remote set-url github https://github.com/cloudQuant/woniunote.git
```

### 认证问题
确保已经配置好SSH密钥或者使用个人访问令牌。

## 仓库链接

- **Gitee**: https://gitee.com/yunjinqi/woniunote
- **GitHub**: https://github.com/cloudQuant/woniunote

## 更新日志

- 2025-01-18: 添加双仓库同步功能
- 支持Windows、Linux、Mac多平台
- 提供多种推送方式
