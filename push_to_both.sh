#!/bin/bash

# 同时推送到Gitee和GitHub的脚本
# 使用方法: ./push_to_both.sh [commit_message]

echo "🚀 开始同时推送到Gitee和GitHub..."
echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"

# 获取提交信息
if [ $# -eq 0 ]; then
    commit_message="Auto commit at $(date '+%Y-%m-%d %H:%M:%S')"
else
    commit_message="$*"
fi

echo "提交信息: $commit_message"

# 添加所有文件
echo ""
echo "🔄 添加文件到暂存区..."
if git add .; then
    echo "✅ 添加文件成功"
else
    echo "❌ 添加文件失败"
    exit 1
fi

# 提交更改
echo ""
echo "🔄 提交更改..."
if git commit -m "$commit_message"; then
    echo "✅ 提交成功"
else
    echo "❌ 提交失败"
    exit 1
fi

# 推送到Gitee
echo ""
echo "🔄 推送到Gitee..."
if git push gitee; then
    echo "✅ Gitee推送成功"
else
    echo "⚠️  Gitee推送失败，但继续尝试GitHub..."
fi

# 推送到GitHub
echo ""
echo "🔄 推送到GitHub..."
if git push github; then
    echo "✅ GitHub推送成功"
else
    echo "⚠️  GitHub推送失败"
fi

echo ""
echo "🎉 推送操作完成！"
echo "📊 推送结果:"
echo "   - Gitee: https://gitee.com/yunjinqi/woniunote"
echo "   - GitHub: https://github.com/cloudQuant/woniunote"
