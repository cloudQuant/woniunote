#!/bin/bash

# WoniuNote 生产环境停止脚本

echo "========================================"
echo "  WoniuNote 生产环境停止脚本"
echo "========================================"
echo ""

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

BACKEND_PORT=5173
PID_DIR="$PROJECT_DIR/pids"

echo "[1/2] 停止后端服务..."

# 通过 PID 文件停止
if [ -f "$PID_DIR/backend.pid" ]; then
    PID=$(cat "$PID_DIR/backend.pid")
    if kill -0 "$PID" 2>/dev/null; then
        echo "     停止后端进程 (PID: $PID)..."
        kill "$PID" 2>/dev/null
        sleep 2
        # 如果还在运行，强制终止
        if kill -0 "$PID" 2>/dev/null; then
            kill -9 "$PID" 2>/dev/null
        fi
        echo "     后端服务已停止"
    else
        echo "     后端进程不存在"
    fi
    rm -f "$PID_DIR/backend.pid"
else
    echo "     未找到 PID 文件"
fi

# 确保端口释放
PID_PORT=$(lsof -ti:$BACKEND_PORT 2>/dev/null || true)
if [ -n "$PID_PORT" ]; then
    echo "     清理端口 $BACKEND_PORT 上的进程..."
    kill -9 $PID_PORT 2>/dev/null || true
fi

echo "[2/2] 检查服务状态..."
if lsof -ti:$BACKEND_PORT >/dev/null 2>&1; then
    echo "     [警告] 端口 $BACKEND_PORT 仍被占用"
else
    echo "     端口 $BACKEND_PORT 已释放"
fi

echo ""
echo "========================================"
echo "  所有服务已停止"
echo "========================================"
echo ""
echo "注意: Nginx 和数据库服务未停止，如需停止请手动执行:"
echo "  sudo systemctl stop nginx"
echo "  sudo systemctl stop mysql"
echo "  sudo systemctl stop redis-server"
echo ""
