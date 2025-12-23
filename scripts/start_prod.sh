#!/bin/bash

# WoniuNote 生产环境启动脚本
# 用于在生产服务器上启动 WoniuNote 服务

set -e

echo "========================================"
echo "  WoniuNote 生产环境启动脚本"
echo "========================================"
echo ""

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# 配置变量
BACKEND_PORT=5173
FRONTEND_PORT=8888
BACKEND_LOG="$PROJECT_DIR/logs/backend.log"
FRONTEND_LOG="$PROJECT_DIR/logs/frontend.log"
PID_DIR="$PROJECT_DIR/pids"

# 创建必要的目录
mkdir -p "$PROJECT_DIR/logs"
mkdir -p "$PID_DIR"
mkdir -p "$PROJECT_DIR/backend_cpp/build/logs"
mkdir -p "$PROJECT_DIR/backend_cpp/build/uploads"

# 检查配置文件
CONFIG_FILE="$PROJECT_DIR/backend_cpp/config.prod.json"
if [ ! -f "$CONFIG_FILE" ]; then
    echo "[警告] 未找到生产环境配置文件 config.prod.json"
    echo "       使用默认配置文件 config.json"
    CONFIG_FILE="$PROJECT_DIR/backend_cpp/config.json"
fi

# 复制配置文件到 build 目录
cp "$CONFIG_FILE" "$PROJECT_DIR/backend_cpp/build/config.json"

# 停止现有进程
echo "[1/5] 停止现有服务..."
if [ -f "$PID_DIR/backend.pid" ]; then
    OLD_PID=$(cat "$PID_DIR/backend.pid")
    if kill -0 "$OLD_PID" 2>/dev/null; then
        echo "     停止后端进程 (PID: $OLD_PID)..."
        kill "$OLD_PID" 2>/dev/null || true
        sleep 2
    fi
    rm -f "$PID_DIR/backend.pid"
fi

# 也检查端口占用
PID_BACKEND=$(lsof -ti:$BACKEND_PORT 2>/dev/null || true)
if [ -n "$PID_BACKEND" ]; then
    echo "     发现进程占用端口 $BACKEND_PORT，正在停止..."
    kill -9 $PID_BACKEND 2>/dev/null || true
    sleep 1
fi

echo "[2/5] 检查依赖服务..."
# 检查 MySQL
if ! systemctl is-active --quiet mysql; then
    echo "     启动 MySQL..."
    systemctl start mysql
fi
echo "     MySQL: 运行中"

# 检查 Redis
if ! systemctl is-active --quiet redis-server; then
    echo "     启动 Redis..."
    systemctl start redis-server
fi
echo "     Redis: 运行中"

echo "[3/5] 生成文章缩略图..."
if [ -f "$PROJECT_DIR/backend_cpp/scripts/generate_thumbs.py" ]; then
    python3 "$PROJECT_DIR/backend_cpp/scripts/generate_thumbs.py" > /dev/null 2>&1 || true
    echo "     缩略图生成完成"
else
    echo "     跳过缩略图生成"
fi

echo "[4/5] 启动 C++ 后端服务..."
cd "$PROJECT_DIR/backend_cpp/build"

# 启动后端
nohup ./woniunote_backend >> "$BACKEND_LOG" 2>&1 &
BACKEND_PID=$!
echo $BACKEND_PID > "$PID_DIR/backend.pid"
echo "     后端服务已启动 (PID: $BACKEND_PID)"

# 等待后端启动
sleep 3

# 验证后端是否启动成功
if ! kill -0 $BACKEND_PID 2>/dev/null; then
    echo "[错误] 后端启动失败，请检查日志: $BACKEND_LOG"
    exit 1
fi

if ! lsof -ti:$BACKEND_PORT >/dev/null 2>&1; then
    echo "[警告] 后端可能未在端口 $BACKEND_PORT 上监听"
fi

echo "[5/5] 检查 Nginx 状态..."
if systemctl is-active --quiet nginx; then
    echo "     Nginx: 运行中"
    # 重新加载 Nginx 配置
    nginx -t && systemctl reload nginx
else
    echo "     启动 Nginx..."
    systemctl start nginx
fi

echo ""
echo "========================================"
echo "  启动成功!"
echo "========================================"
echo ""
echo "  服务状态:"
echo "  - 后端 API: http://localhost:$BACKEND_PORT"
echo "  - 后端 PID: $BACKEND_PID"
echo ""
echo "  日志文件:"
echo "  - 后端日志: $BACKEND_LOG"
echo "  - 后端应用日志: $PROJECT_DIR/backend_cpp/build/logs/"
echo ""
echo "  如果配置了 Nginx + HTTPS:"
echo "  - 网站地址: https://www.yunjinqi.top"
echo ""
echo "========================================"

cd "$PROJECT_DIR"
