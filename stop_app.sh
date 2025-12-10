#!/bin/bash

# Parse command line arguments
# Usage: stop_app.sh [python|cpp|all]
# Default: all (stops any backend on port 8888)

BACKEND_TYPE="all"
case "${1,,}" in
    python|py)
        BACKEND_TYPE="python"
        ;;
    cpp|c++)
        BACKEND_TYPE="cpp"
        ;;
    all)
        BACKEND_TYPE="all"
        ;;
esac

echo "========================================"
echo "  WoniuNote 应用停止脚本"
if [ "$BACKEND_TYPE" != "all" ]; then
    echo "  后端类型: $BACKEND_TYPE"
fi
echo "========================================"
echo ""

# 关闭占用端口8888的进程（后端）
echo "[1/2] 停止后端服务 (端口 8888)..."
PID_8888=$(lsof -ti:8888 2>/dev/null)
if [ -n "$PID_8888" ]; then
    echo "     正在关闭进程 $PID_8888..."
    kill -9 $PID_8888 2>/dev/null
    echo "     后端服务已停止"
else
    echo "     后端服务未运行"
fi

# 关闭占用端口5173的进程（前端）
echo "[2/2] 停止前端服务 (端口 5173)..."
PID_5173=$(lsof -ti:5173 2>/dev/null)
if [ -n "$PID_5173" ]; then
    echo "     正在关闭进程 $PID_5173..."
    kill -9 $PID_5173 2>/dev/null
    echo "     前端服务已停止"
else
    echo "     前端服务未运行"
fi

echo ""
echo "========================================"
echo "  所有服务已停止"
echo "========================================"
echo ""
echo "  用法: ./stop_app.sh [python|cpp|all]"
echo "  (注意: 所有后端都使用端口 8888)"
echo "========================================"

exit 0
