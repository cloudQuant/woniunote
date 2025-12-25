#!/bin/bash

# WoniuNote 重启脚本 - 仅使用 C++ 后端
# 用法: bash restart_app.sh [prod|dev]
#   prod (默认): 生产模式，使用 npm run build + Nginx 服务静态文件
#   dev: 开发模式，使用 npm run dev 热重载

# 解析参数
MODE="${1:-prod}"

if [ "$MODE" != "prod" ] && [ "$MODE" != "dev" ]; then
    echo "用法: bash restart_app.sh [prod|dev]"
    echo "  prod (默认): 生产模式"
    echo "  dev: 开发模式"
    exit 1
fi

echo "========================================"
echo "  WoniuNote 应用重启脚本"
echo "  运行模式: $MODE"
echo "========================================"
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "[1/3] 停止前后端服务..."
bash "$SCRIPT_DIR/stop_app.sh"

echo "[2/3] 清空日志..."
: > "$SCRIPT_DIR/backend.log"
: > "$SCRIPT_DIR/frontend.log"

if [ -f "$SCRIPT_DIR/route_debug.log" ]; then
    : > "$SCRIPT_DIR/route_debug.log"
fi

if [ -d "$SCRIPT_DIR/backend_cpp/build/logs" ]; then
    rm -f "$SCRIPT_DIR/backend_cpp/build/logs"/*.log 2>/dev/null
fi

echo "     日志已清空"

echo "[3/3] 启动前后端服务..."
bash "$SCRIPT_DIR/start_app.sh" "$MODE"

exit 0
