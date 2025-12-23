#!/bin/bash

# WoniuNote 快速部署脚本
# 用于在已配置好环境的服务器上快速部署/更新项目

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
DEPLOY_DIR="${DEPLOY_DIR:-/var/www/woniunote}"
VCPKG_ROOT="${VCPKG_ROOT:-$HOME/vcpkg}"

echo "========================================"
echo "  WoniuNote 快速部署"
echo "========================================"
echo ""

# 检查是否需要 sudo
if [ "$EUID" -ne 0 ]; then
    log_warn "建议使用 sudo 运行此脚本"
fi

# 步骤 1: 停止现有服务
log_info "[1/6] 停止现有服务..."
if systemctl is-active --quiet woniunote 2>/dev/null; then
    systemctl stop woniunote
elif pgrep -f "woniunote_backend" > /dev/null; then
    pkill -f "woniunote_backend" || true
fi
sleep 1

# 步骤 2: 拉取最新代码 (如果是 git 仓库)
if [ -d "$PROJECT_DIR/.git" ]; then
    log_info "[2/6] 拉取最新代码..."
    cd "$PROJECT_DIR"
    git pull --ff-only || log_warn "Git pull 失败，继续使用当前代码"
else
    log_info "[2/6] 跳过 git pull (非 git 仓库)"
fi

# 步骤 3: 构建后端
log_info "[3/6] 构建 C++ 后端..."
cd "$PROJECT_DIR/backend_cpp"
mkdir -p build
cd build

if [ -f "$VCPKG_ROOT/scripts/buildsystems/vcpkg.cmake" ]; then
    cmake .. \
        -DCMAKE_TOOLCHAIN_FILE="$VCPKG_ROOT/scripts/buildsystems/vcpkg.cmake" \
        -DCMAKE_BUILD_TYPE=Release \
        -G "Unix Makefiles"
else
    log_warn "未找到 vcpkg，使用系统库"
    cmake .. -DCMAKE_BUILD_TYPE=Release
fi

cmake --build . --config Release -j$(nproc)
log_info "后端构建完成"

# 步骤 4: 构建前端
log_info "[4/6] 构建前端..."
if [ -d "$PROJECT_DIR/frontend" ]; then
    cd "$PROJECT_DIR/frontend"
    if [ ! -d "node_modules" ]; then
        npm install
    fi
    npm run build
    log_info "前端构建完成"
else
    log_warn "未找到前端目录，跳过"
fi

# 步骤 5: 部署文件
log_info "[5/6] 部署文件到 $DEPLOY_DIR..."
mkdir -p "$DEPLOY_DIR"
mkdir -p "$DEPLOY_DIR/logs"
mkdir -p "$DEPLOY_DIR/backend_cpp/build/logs"
mkdir -p "$DEPLOY_DIR/backend_cpp/build/uploads"

# 同步后端
rsync -av "$PROJECT_DIR/backend_cpp/build/woniunote_backend" "$DEPLOY_DIR/backend_cpp/build/"
rsync -av "$PROJECT_DIR/backend_cpp/build/config.json" "$DEPLOY_DIR/backend_cpp/build/" 2>/dev/null || true

# 如果有生产配置文件，优先使用
if [ -f "$PROJECT_DIR/backend_cpp/config.prod.json" ]; then
    cp "$PROJECT_DIR/backend_cpp/config.prod.json" "$DEPLOY_DIR/backend_cpp/build/config.json"
fi

# 同步前端
if [ -d "$PROJECT_DIR/frontend/dist" ]; then
    rsync -av --delete "$PROJECT_DIR/frontend/dist/" "$DEPLOY_DIR/frontend/dist/"
fi

# 同步脚本
rsync -av "$PROJECT_DIR/scripts/" "$DEPLOY_DIR/scripts/"
chmod +x "$DEPLOY_DIR/scripts/"*.sh

# 同步配置
rsync -av "$PROJECT_DIR/configs/" "$DEPLOY_DIR/configs/"

log_info "文件部署完成"

# 步骤 6: 启动服务
log_info "[6/6] 启动服务..."

# 确保依赖服务运行
systemctl start mysql 2>/dev/null || true
systemctl start redis-server 2>/dev/null || true

# 启动后端
if systemctl list-unit-files | grep -q "^woniunote.service"; then
    systemctl start woniunote
    log_info "通过 systemd 启动"
else
    cd "$DEPLOY_DIR/backend_cpp/build"
    nohup ./woniunote_backend >> "$DEPLOY_DIR/logs/backend.log" 2>&1 &
    log_info "通过 nohup 启动 (PID: $!)"
fi

# 重载 nginx
if systemctl is-active --quiet nginx; then
    nginx -t && systemctl reload nginx
fi

sleep 2

# 验证
echo ""
echo "========================================"
echo "  部署完成!"
echo "========================================"
echo ""

if pgrep -f "woniunote_backend" > /dev/null; then
    echo -e "  后端状态: ${GREEN}●${NC} 运行中"
else
    echo -e "  后端状态: ${RED}●${NC} 未运行"
    log_error "后端启动失败，请检查日志: $DEPLOY_DIR/logs/backend.log"
fi

if lsof -ti:5173 >/dev/null 2>&1; then
    echo -e "  端口 5173: ${GREEN}●${NC} 监听中"
else
    echo -e "  端口 5173: ${RED}●${NC} 未监听"
fi

echo ""
echo "  日志: tail -f $DEPLOY_DIR/logs/backend.log"
echo ""
