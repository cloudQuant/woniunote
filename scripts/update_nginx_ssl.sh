#!/bin/bash

# Nginx 配置更新脚本
# 简单实现：复制配置 -> 检查状态 -> 测试 -> 重载 -> 检查状态

set -e

# 获取脚本和项目目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# 配置文件路径
CONFIG_SOURCE="$PROJECT_DIR/configs/woniunote_nginx_prod.conf"
CONFIG_DEST="/etc/nginx/nginx.conf"

echo "========================================"
echo "  Nginx 配置更新脚本"
echo "========================================"
echo ""

# 检查 root 权限
if [ "$EUID" -ne 0 ]; then
    echo "[错误] 请使用 sudo 运行此脚本"
    exit 1
fi

# 检查配置源文件
if [ ! -f "$CONFIG_SOURCE" ]; then
    echo "[错误] 配置文件不存在: $CONFIG_SOURCE"
    exit 1
fi

# 步骤 1: 备份并复制配置
echo "[1/5] 备份当前配置..."
if [ -f "$CONFIG_DEST" ]; then
    cp "$CONFIG_DEST" "$CONFIG_DEST.bak"
    echo "      已备份到: $CONFIG_DEST.bak"
fi

echo "[2/5] 复制新配置..."
cp "$CONFIG_SOURCE" "$CONFIG_DEST"
echo "      已复制: $CONFIG_SOURCE -> $CONFIG_DEST"

# 步骤 2: 检查状态（重载前）
echo ""
echo "[3/5] 检查 Nginx 状态（重载前）..."
systemctl status nginx --no-pager | head -5 || true

# 步骤 3: 测试配置
echo ""
echo "[4/5] 测试 Nginx 配置..."
if nginx -t; then
    echo "      配置测试通过"
else
    echo "[错误] 配置测试失败，正在回滚..."
    cp "$CONFIG_DEST.bak" "$CONFIG_DEST"
    exit 1
fi

# 步骤 4: 重载 Nginx
echo ""
echo "[5/5] 重载 Nginx..."
systemctl reload nginx
sleep 2

# 步骤 5: 检查状态（重载后）
echo ""
echo "========================================"
echo "  重载后 Nginx 状态"
echo "========================================"
systemctl status nginx --no-pager | head -10

echo ""
echo "========================================"
echo "  完成!"
echo "========================================"
