#!/bin/bash

# WoniuNote 生产环境管理脚本
# 使用 systemd 管理后端，Nginx 服务前端静态文件

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 自动检测部署目录 (脚本所在目录的父目录)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOY_DIR="${DEPLOY_DIR:-$(dirname "$SCRIPT_DIR")}"
SERVICE_NAME="woniunote"

# 检查是否为 root
check_root() {
    if [ "$EUID" -ne 0 ]; then
        log_error "请使用 sudo 运行此脚本"
        exit 1
    fi
}

# 启动服务
start() {
    log_info "启动 WoniuNote 服务..."
    
    # 启动后端 (systemd)
    if systemctl is-active --quiet $SERVICE_NAME; then
        log_info "后端服务已在运行"
    else
        systemctl start $SERVICE_NAME
        log_info "后端服务已启动"
    fi
    
    # 确保 Nginx 运行
    if systemctl is-active --quiet nginx; then
        log_info "Nginx 已在运行"
    else
        systemctl start nginx
        log_info "Nginx 已启动"
    fi
    
    # 检查服务状态
    sleep 2
    status
}

# 停止服务
stop() {
    log_info "停止 WoniuNote 服务..."
    
    if systemctl is-active --quiet $SERVICE_NAME; then
        systemctl stop $SERVICE_NAME
        log_info "后端服务已停止"
    else
        log_info "后端服务未在运行"
    fi
}

# 重启服务
restart() {
    log_info "重启 WoniuNote 服务..."
    systemctl restart $SERVICE_NAME
    systemctl reload nginx
    sleep 2
    status
}

# 查看状态
status() {
    echo ""
    echo "========================================"
    echo "  WoniuNote 服务状态"
    echo "========================================"
    echo ""
    
    # 后端状态
    echo -n "后端服务 ($SERVICE_NAME): "
    if systemctl is-active --quiet $SERVICE_NAME; then
        echo -e "${GREEN}运行中${NC}"
    else
        echo -e "${RED}已停止${NC}"
    fi
    
    # Nginx 状态
    echo -n "Nginx: "
    if systemctl is-active --quiet nginx; then
        echo -e "${GREEN}运行中${NC}"
    else
        echo -e "${RED}已停止${NC}"
    fi
    
    # MySQL 状态
    echo -n "MySQL: "
    if systemctl is-active --quiet mysql; then
        echo -e "${GREEN}运行中${NC}"
    else
        echo -e "${RED}已停止${NC}"
    fi
    
    # Redis 状态
    echo -n "Redis: "
    if systemctl is-active --quiet redis-server; then
        echo -e "${GREEN}运行中${NC}"
    else
        echo -e "${RED}已停止${NC}"
    fi
    
    echo ""
    
    # 检查端口
    echo "端口监听状态:"
    echo -n "  5173 (后端API): "
    if ss -tlnp | grep -q ":5173 "; then
        echo -e "${GREEN}监听中${NC}"
    else
        echo -e "${RED}未监听${NC}"
    fi
    
    echo -n "  80 (HTTP): "
    if ss -tlnp | grep -q ":80 "; then
        echo -e "${GREEN}监听中${NC}"
    else
        echo -e "${RED}未监听${NC}"
    fi
    
    echo -n "  443 (HTTPS): "
    if ss -tlnp | grep -q ":443 "; then
        echo -e "${GREEN}监听中${NC}"
    else
        echo -e "${RED}未监听${NC}"
    fi
    
    echo ""
}

# 查看日志
logs() {
    local target="${1:-backend}"
    case "$target" in
        backend)
            tail -f "$DEPLOY_DIR/logs/backend.log"
            ;;
        error)
            tail -f "$DEPLOY_DIR/logs/backend_error.log"
            ;;
        nginx)
            tail -f /var/log/nginx/woniunote_access.log
            ;;
        nginx-error)
            tail -f /var/log/nginx/woniunote_error.log
            ;;
        systemd)
            journalctl -u $SERVICE_NAME -f
            ;;
        *)
            log_error "未知日志类型: $target"
            echo "可用选项: backend, error, nginx, nginx-error, systemd"
            ;;
    esac
}

# 重新构建前端
rebuild_frontend() {
    log_info "重新构建前端..."
    cd "$DEPLOY_DIR/frontend"
    
    if [ ! -f "package.json" ]; then
        log_error "未找到 package.json"
        exit 1
    fi
    
    # 安装依赖
    if [ ! -d "node_modules" ] || [ ! -f "node_modules/vite/dist/node/cli.js" ]; then
        log_info "安装前端依赖..."
        rm -rf node_modules package-lock.json
        npm install --no-package-lock
        npm install
    fi
    
    # 构建
    log_info "执行 npm run build..."
    npm run build
    
    log_info "前端构建完成"
    
    # 重载 Nginx
    systemctl reload nginx
}

# 重新编译后端
rebuild_backend() {
    log_info "重新编译后端..."
    cd "$DEPLOY_DIR/backend_cpp/build"
    
    cmake .. -DCMAKE_BUILD_TYPE=Release -DUSE_SYSTEM_LIBS=ON
    cmake --build . --config Release -j$(nproc)
    
    log_info "后端编译完成"
    
    # 重启服务
    systemctl restart $SERVICE_NAME
    log_info "后端服务已重启"
}

# 显示帮助
usage() {
    echo "WoniuNote 生产环境管理脚本"
    echo ""
    echo "用法: sudo bash $0 <命令>"
    echo ""
    echo "命令:"
    echo "  start             启动服务"
    echo "  stop              停止服务"
    echo "  restart           重启服务"
    echo "  status            查看状态"
    echo "  logs [target]     查看日志 (backend/error/nginx/nginx-error/systemd)"
    echo "  rebuild-frontend  重新构建前端"
    echo "  rebuild-backend   重新编译后端"
    echo ""
}

# 主逻辑
case "${1:-}" in
    start)
        check_root
        start
        ;;
    stop)
        check_root
        stop
        ;;
    restart)
        check_root
        restart
        ;;
    status)
        status
        ;;
    logs)
        logs "$2"
        ;;
    rebuild-frontend)
        check_root
        rebuild_frontend
        ;;
    rebuild-backend)
        check_root
        rebuild_backend
        ;;
    *)
        usage
        ;;
esac
