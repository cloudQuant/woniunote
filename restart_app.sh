#!/bin/bash

# WoniuNote 重启脚本 - 仅使用 C++ 后端

echo "========================================"
echo "  WoniuNote 应用重启脚本"
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
bash "$SCRIPT_DIR/start_app.sh"

exit 0
