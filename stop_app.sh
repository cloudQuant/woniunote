#!/bin/bash

# WoniuNote 停止脚本

echo "========================================"
echo "  WoniuNote 应用停止脚本"
echo "========================================"
echo ""

# 关闭占用端口5173的进程（后端）
echo "[1/2] 停止后端服务 (端口 5173)..."
PID_5173=$(lsof -ti:5173 2>/dev/null)
if [ -n "$PID_5173" ]; then
    # 配置里的 relaunch_on_error=true 让后端以「监督进程 + 工作进程」运行。
    # 只杀掉持有端口的工作进程时，监督进程会立刻拉起一个新的，端口仍被占用：
    # 停止看似成功、实则无效，restart 随后会静默沿用旧二进制（迭代20 演练发现）。
    # 因此一并终止父进程——仅当父进程与端口进程是同一个可执行文件时才终止，
    # 避免误杀 shell/systemd——并在之后确认端口确实释放。
    PARENTS=""
    for pid in $PID_5173; do
        ppid=$(ps -o ppid= -p "$pid" 2>/dev/null | tr -d ' ')
        if [ -n "$ppid" ] && [ "$ppid" != "1" ] && \
           [ "$(ps -o comm= -p "$ppid" 2>/dev/null)" = "$(ps -o comm= -p "$pid" 2>/dev/null)" ]; then
            PARENTS="$PARENTS $ppid"
        fi
    done
    echo "     正在关闭进程 $PID_5173..."
    kill -9 $PARENTS $PID_5173 2>/dev/null
    sleep 1
    if lsof -ti:5173 >/dev/null 2>&1; then
        echo "     [错误] 端口 5173 仍被占用，后端未停止"
        exit 1
    fi
    echo "     后端服务已停止"
else
    echo "     后端服务未运行"
fi

# 关闭占用端口8888的进程（前端）
echo "[2/2] 停止前端服务 (端口 8888)..."
PID_8888=$(lsof -ti:8888 2>/dev/null)
if [ -n "$PID_8888" ]; then
    echo "     正在关闭进程 $PID_8888..."
    kill -9 $PID_8888 2>/dev/null
    echo "     前端服务已停止"
else
    echo "     前端服务未运行"
fi

echo ""
echo "========================================"
echo "  所有服务已停止"
echo "========================================"

exit 0
