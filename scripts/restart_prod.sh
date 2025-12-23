#!/bin/bash

# WoniuNote 生产环境重启脚本

echo "========================================"
echo "  WoniuNote 生产环境重启脚本"
echo "========================================"
echo ""

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "[1/2] 停止服务..."
bash "$SCRIPT_DIR/stop_prod.sh"

echo "[2/2] 启动服务..."
bash "$SCRIPT_DIR/start_prod.sh"
