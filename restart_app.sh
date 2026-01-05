#!/bin/bash

# WoniuNote 重启脚本 - 简化版，直接使用项目目录
# 用法: bash restart_app.sh [prod|dev]
#   prod (默认): 生产模式
#   dev: 开发模式

MODE="${1:-prod}"

if [ "$MODE" != "prod" ] && [ "$MODE" != "dev" ]; then
    echo "用法: bash restart_app.sh [prod|dev]"
    exit 1
fi

echo "========================================"
echo "  WoniuNote 应用重启脚本"
echo "  运行模式: $MODE"
echo "========================================"
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "[1/6] 更新代码..."
git pull origin dev_cpp
if [ $? -ne 0 ]; then
    echo "[错误] Git pull 失败，终止重启"
    exit 1
fi
echo "     代码已更新"

echo "[2/6] 停止服务..."
bash "$SCRIPT_DIR/stop_app.sh"

echo "[3/6] 清理缓存..."
rm -rf "$SCRIPT_DIR/frontend/dist"
rm -rf "$SCRIPT_DIR/frontend/node_modules/.vite"
: > "$SCRIPT_DIR/backend.log"
: > "$SCRIPT_DIR/frontend.log"
echo "     缓存已清理"

echo "[4/6] 更新 Nginx 配置..."
NGINX_CONF_SRC="$SCRIPT_DIR/configs/woniunote_nginx_prod.conf"
NGINX_CONF_DST="/etc/nginx/nginx.conf"

if [ ! -f "$NGINX_CONF_SRC" ]; then
    echo "[错误] Nginx 配置文件不存在: $NGINX_CONF_SRC"
    exit 1
fi

sudo cp "$NGINX_CONF_SRC" "$NGINX_CONF_DST"
if [ $? -ne 0 ]; then
    echo "[错误] 复制 Nginx 配置失败，请检查 sudo 权限"
    exit 1
fi

sudo nginx -t
if [ $? -eq 0 ]; then
    sudo systemctl reload nginx
    echo "     Nginx 配置已更新并重载"
else
    echo "[错误] Nginx 配置检查失败，请手动检查"
    sudo nginx -t
    exit 1
fi

echo "[5/6] 删除旧的同步目录（如果存在）..."
if [ -d "/var/www/woniunote/frontend" ]; then
    sudo rm -rf /var/www/woniunote/frontend
    echo "     旧目录已删除"
else
    echo "     无需删除"
fi

echo "[6/6] 启动服务..."
bash "$SCRIPT_DIR/start_app.sh" "$MODE"

echo ""
echo "========================================"
echo "  重启完成!"
echo "========================================"
echo "  前端: https://www.yunjinqi.top"
echo "  后端: http://localhost:5173"
echo ""
echo "  重要提示："
echo "  浏览器按 Ctrl+Shift+R (Mac: Cmd+Shift+R) 强制刷新"
echo "========================================"

exit 0
