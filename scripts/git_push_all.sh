#!/bin/bash

# 简单的推送脚本，利用git配置的多个push URL
# 使用方法: ./git_push_all.sh 或 git push (直接使用git push即可)

echo "🚀 推送到所有配置的远程仓库..."
echo "当前配置的推送目标："
git remote -v | grep push

echo ""
echo "📌 提示: 现在可以直接使用 'git push' 命令同时推送到："
echo "   - Gitee:  https://gitee.com/yunjinqi/woniunote.git"
echo "   - GitHub: https://github.com/cloudQuant/woniunote.git"
echo ""

# 执行推送
if [ $# -eq 0 ]; then
    # 没有参数，推送当前分支
    git push
else
    # 有参数，传递给git push
    git push "$@"
fi

# 检查推送结果
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ 成功推送到所有远程仓库！"
else
    echo ""
    echo "⚠️  推送过程中出现问题，请检查错误信息"
fi