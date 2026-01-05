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
# 删除旧的构建产物和缓存
rm -rf "$SCRIPT_DIR/frontend/dist"
rm -rf "$SCRIPT_DIR/frontend/node_modules/.vite"
# 清理 nginx 缓存（如果存在）
sudo rm -rf /var/cache/nginx/* 2>/dev/null || true
: > "$SCRIPT_DIR/backend.log"
: > "$SCRIPT_DIR/frontend.log"
echo "     缓存已清理（包括 nginx 缓存）"

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
echo ""

# 验证前端构建文件是否正确部署
echo "[验证] 检查前端构建文件..."
if [ -f "$SCRIPT_DIR/frontend/dist/index.html" ]; then
    CSS_FILE=$(grep -o 'href="/assets/[^"]*\.css"' "$SCRIPT_DIR/frontend/dist/index.html" | head -1 | sed 's/href="\/assets\///;s/"//')
    JS_FILE=$(grep -o 'src="/assets/[^"]*\.js"' "$SCRIPT_DIR/frontend/dist/index.html" | head -1 | sed 's/src="\/assets\///;s/"//')
    echo "  index.html 引用的 CSS: $CSS_FILE"
    echo "  index.html 引用的 JS: $JS_FILE"

    # 检查文件是否实际存在
    if [ -f "$SCRIPT_DIR/frontend/dist/assets/$CSS_FILE" ] && [ -f "$SCRIPT_DIR/frontend/dist/assets/$JS_FILE" ]; then
        echo "  ✓ 所有引用文件存在"
    else
        echo "  ✗ 警告: 部分引用文件不存在，可能构建不完整"
    fi

    # 检查 nginx root 目录是否正确
    NGINX_ROOT=$(grep -A 20 "server_name yunjinqi.top" "$NGINX_CONF_DST" 2>/dev/null | grep "root" | head -1 | awk '{print $2}' | sed 's/;//')
    if [ -n "$NGINX_ROOT" ]; then
        echo "  Nginx root 目录: $NGINX_ROOT"
        if [ "$NGINX_ROOT" != "$SCRIPT_DIR/frontend/dist" ]; then
            echo "  ✗ 警告: Nginx root 与项目目录不一致"
        fi
    fi
else
    echo "  ✗ 警告: dist/index.html 不存在"
fi
echo "========================================"

exit 0
