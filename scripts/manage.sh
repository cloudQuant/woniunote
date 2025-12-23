#!/bin/bash

# WoniuNote 统一管理脚本
# 用法: ./manage.sh [命令]
# 命令: start | stop | restart | status | logs | build | deploy | install-service

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 获取项目目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# 配置
BACKEND_PORT=5173
SERVICE_NAME="woniunote"
DEPLOY_DIR="/var/www/woniunote"

# 辅助函数
log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

print_banner() {
    echo -e "${BLUE}"
    echo "========================================"
    echo "  WoniuNote 管理工具"
    echo "========================================"
    echo -e "${NC}"
}

# 检查服务状态
check_status() {
    echo ""
    log_info "服务状态检查:"
    echo ""
    
    # 检查 systemd 服务
    if systemctl is-active --quiet $SERVICE_NAME 2>/dev/null; then
        echo -e "  后端服务:  ${GREEN}●${NC} 运行中 (systemd)"
    elif pgrep -f "woniunote_backend" > /dev/null; then
        echo -e "  后端服务:  ${GREEN}●${NC} 运行中 (手动启动)"
    else
        echo -e "  后端服务:  ${RED}●${NC} 未运行"
    fi
    
    # 检查端口
    if lsof -ti:$BACKEND_PORT >/dev/null 2>&1; then
        echo -e "  端口 $BACKEND_PORT: ${GREEN}●${NC} 监听中"
    else
        echo -e "  端口 $BACKEND_PORT: ${RED}●${NC} 未监听"
    fi
    
    # 检查依赖服务
    if systemctl is-active --quiet mysql 2>/dev/null; then
        echo -e "  MySQL:     ${GREEN}●${NC} 运行中"
    else
        echo -e "  MySQL:     ${RED}●${NC} 未运行"
    fi
    
    if systemctl is-active --quiet redis-server 2>/dev/null; then
        echo -e "  Redis:     ${GREEN}●${NC} 运行中"
    else
        echo -e "  Redis:     ${RED}●${NC} 未运行"
    fi
    
    if systemctl is-active --quiet nginx 2>/dev/null; then
        echo -e "  Nginx:     ${GREEN}●${NC} 运行中"
    else
        echo -e "  Nginx:     ${RED}●${NC} 未运行"
    fi
    echo ""
}

# 启动服务
start_service() {
    log_info "启动 WoniuNote 服务..."
    
    # 确保依赖服务运行
    systemctl start mysql 2>/dev/null || true
    systemctl start redis-server 2>/dev/null || true
    
    # 优先使用 systemd
    if systemctl list-unit-files | grep -q "^$SERVICE_NAME.service"; then
        systemctl start $SERVICE_NAME
        log_info "通过 systemd 启动成功"
    else
        # 回退到脚本启动
        bash "$SCRIPT_DIR/start_prod.sh"
    fi
    
    # 启动 nginx
    systemctl start nginx 2>/dev/null || true
    
    sleep 2
    check_status
}

# 停止服务
stop_service() {
    log_info "停止 WoniuNote 服务..."
    
    if systemctl list-unit-files | grep -q "^$SERVICE_NAME.service"; then
        systemctl stop $SERVICE_NAME 2>/dev/null || true
    fi
    
    # 也清理手动启动的进程
    pkill -f "woniunote_backend" 2>/dev/null || true
    
    # 清理端口
    PID_PORT=$(lsof -ti:$BACKEND_PORT 2>/dev/null || true)
    if [ -n "$PID_PORT" ]; then
        kill -9 $PID_PORT 2>/dev/null || true
    fi
    
    log_info "服务已停止"
}

# 重启服务
restart_service() {
    log_info "重启 WoniuNote 服务..."
    stop_service
    sleep 2
    start_service
}

# 查看日志
view_logs() {
    LOG_TYPE=${1:-"all"}
    
    case $LOG_TYPE in
        backend)
            if [ -f "$DEPLOY_DIR/logs/backend.log" ]; then
                tail -f "$DEPLOY_DIR/logs/backend.log"
            elif [ -f "$PROJECT_DIR/logs/backend.log" ]; then
                tail -f "$PROJECT_DIR/logs/backend.log"
            else
                log_error "未找到后端日志文件"
            fi
            ;;
        nginx)
            tail -f /var/log/nginx/woniunote_*.log
            ;;
        systemd)
            journalctl -u $SERVICE_NAME -f
            ;;
        *)
            log_info "可用的日志类型: backend, nginx, systemd"
            log_info "用法: ./manage.sh logs [类型]"
            ;;
    esac
}

# 构建项目
build_project() {
    log_info "构建 C++ 后端..."
    
    cd "$PROJECT_DIR/backend_cpp"
    mkdir -p build
    cd build
    
    # 检测 vcpkg
    VCPKG_ROOT="${VCPKG_ROOT:-$HOME/vcpkg}"
    if [ -f "$VCPKG_ROOT/scripts/buildsystems/vcpkg.cmake" ]; then
        cmake .. \
            -DCMAKE_TOOLCHAIN_FILE="$VCPKG_ROOT/scripts/buildsystems/vcpkg.cmake" \
            -DCMAKE_BUILD_TYPE=Release
    else
        cmake .. -DCMAKE_BUILD_TYPE=Release
    fi
    
    cmake --build . --config Release -j$(nproc)
    
    log_info "后端构建完成"
    
    # 构建前端
    if [ -d "$PROJECT_DIR/frontend" ]; then
        log_info "构建前端..."
        cd "$PROJECT_DIR/frontend"
        npm install
        npm run build
        log_info "前端构建完成"
    fi
}

# 部署到生产目录
deploy_project() {
    log_info "部署到 $DEPLOY_DIR..."
    
    # 创建部署目录
    mkdir -p "$DEPLOY_DIR"
    mkdir -p "$DEPLOY_DIR/logs"
    
    # 停止服务
    stop_service
    
    # 同步文件
    rsync -av --exclude='.git' \
              --exclude='node_modules' \
              --exclude='__pycache__' \
              --exclude='*.pyc' \
              "$PROJECT_DIR/" "$DEPLOY_DIR/"
    
    # 复制配置
    if [ -f "$PROJECT_DIR/backend_cpp/config.prod.json" ]; then
        cp "$PROJECT_DIR/backend_cpp/config.prod.json" "$DEPLOY_DIR/backend_cpp/build/config.json"
    fi
    
    # 设置权限
    chmod +x "$DEPLOY_DIR/backend_cpp/build/woniunote_backend"
    chmod +x "$DEPLOY_DIR/scripts/"*.sh
    
    log_info "部署完成"
    
    # 重启服务
    start_service
}

# 安装 systemd 服务
install_service() {
    log_info "安装 systemd 服务..."
    
    # 复制服务文件
    cp "$PROJECT_DIR/configs/woniunote.service" /etc/systemd/system/
    
    # 更新服务文件中的路径
    sed -i "s|/var/www/woniunote|$DEPLOY_DIR|g" /etc/systemd/system/woniunote.service
    
    # 重新加载 systemd
    systemctl daemon-reload
    
    # 启用开机自启
    systemctl enable $SERVICE_NAME
    
    log_info "systemd 服务安装完成"
    log_info "使用以下命令管理服务:"
    echo "  systemctl start $SERVICE_NAME"
    echo "  systemctl stop $SERVICE_NAME"
    echo "  systemctl restart $SERVICE_NAME"
    echo "  systemctl status $SERVICE_NAME"
}

# 快速更新 (git pull + 重新构建 + 重启)
quick_update() {
    log_info "快速更新..."
    
    cd "$PROJECT_DIR"
    
    # 拉取最新代码
    log_info "拉取最新代码..."
    git pull
    
    # 构建
    build_project
    
    # 部署
    deploy_project
    
    log_info "更新完成!"
}

# 显示帮助
show_help() {
    print_banner
    echo "用法: $0 <命令>"
    echo ""
    echo "命令:"
    echo "  start           启动服务"
    echo "  stop            停止服务"
    echo "  restart         重启服务"
    echo "  status          查看服务状态"
    echo "  logs [类型]     查看日志 (backend/nginx/systemd)"
    echo "  build           构建项目"
    echo "  deploy          部署到生产环境"
    echo "  install-service 安装 systemd 服务"
    echo "  update          快速更新 (git pull + build + deploy)"
    echo "  help            显示帮助"
    echo ""
}

# 主入口
main() {
    case "${1:-help}" in
        start)
            print_banner
            start_service
            ;;
        stop)
            print_banner
            stop_service
            ;;
        restart)
            print_banner
            restart_service
            ;;
        status)
            print_banner
            check_status
            ;;
        logs)
            view_logs "$2"
            ;;
        build)
            print_banner
            build_project
            ;;
        deploy)
            print_banner
            deploy_project
            ;;
        install-service)
            print_banner
            install_service
            ;;
        update)
            print_banner
            quick_update
            ;;
        help|*)
            show_help
            ;;
    esac
}

main "$@"
