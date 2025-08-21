# Git 双仓库推送配置说明

## 配置概述

本项目已配置为同时推送到以下两个远程仓库：
- **Gitee**: https://gitee.com/yunjinqi/woniunote.git
- **GitHub**: https://github.com/cloudQuant/woniunote.git

## 当前配置

### Remote 配置
```bash
# 查看当前remote配置
git remote -v

# 输出：
origin  https://gitee.com/yunjinqi/woniunote.git (fetch)
origin  https://github.com/cloudQuant/woniunote.git (push)
origin  https://gitee.com/yunjinqi/woniunote.git (push)
github  https://github.com/cloudQuant/woniunote.git (fetch)
github  https://github.com/cloudQuant/woniunote.git (push)
```

## 使用方法

### 方法1：使用标准git命令（推荐）
```bash
# 添加文件
git add .

# 提交更改
git commit -m "你的提交信息"

# 推送到所有远程仓库（自动推送到Gitee和GitHub）
git push

# 或者推送特定分支
git push origin main
git push origin phase2-development
```

### 方法2：使用提供的脚本
```bash
# 使用push_to_both脚本（包含add和commit）
./scripts/push_to_both.sh "你的提交信息"

# 使用git_push_all脚本（仅推送）
./scripts/git_push_all.sh
```

## 单独推送到特定仓库

如果需要单独推送到某个仓库：

```bash
# 仅推送到GitHub
git push github

# 仅推送到Gitee（需要手动指定URL）
git push https://gitee.com/yunjinqi/woniunote.git
```

## 配置原理

Git支持为同一个remote设置多个push URL。当执行`git push origin`时，Git会依次推送到所有配置的push URL。

### 如何配置（已完成）
```bash
# 1. 添加GitHub作为额外的push URL
git remote set-url --add --push origin https://github.com/cloudQuant/woniunote.git

# 2. 重新添加Gitee的push URL（因为第一次set-url会覆盖原有的）
git remote set-url --add --push origin https://gitee.com/yunjinqi/woniunote.git

# 3. （可选）添加单独的github remote
git remote add github https://github.com/cloudQuant/woniunote.git
```

## 故障排除

### 如果推送失败
1. 检查网络连接
2. 确认是否有推送权限
3. 检查是否需要先pull最新更改：
   ```bash
   git pull origin main
   ```

### 如果只有一个仓库推送成功
脚本会显示哪个仓库失败，可以单独处理：
```bash
# 查看具体错误
git push github --verbose

# 或强制推送（谨慎使用）
git push github --force
```

## 注意事项

1. **首次推送**：确保两个仓库都有相应的权限
2. **分支一致性**：两个仓库的分支应保持同步
3. **冲突处理**：如果两个仓库有不同的提交历史，需要先解决冲突

## 验证配置

运行以下命令验证配置是否正确：
```bash
git remote -v | grep push
```

应该看到origin有两个push URL，分别指向Gitee和GitHub。