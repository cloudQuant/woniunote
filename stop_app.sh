#!/bin/bash

# WoniuNote 停止脚本

echo "========================================"
echo "  WoniuNote 应用停止脚本"
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

exit 0
