#!/bin/bash

# WoniuNote systemd 服务安装脚本
# 用于安装 systemd 服务实现开机自启

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
SERVICE_FILE="/etc/systemd/system/woniunote.service"

echo "========================================"
echo "  WoniuNote 服务安装脚本"
echo "========================================"
echo ""

# 检查 root 权限
if [ "$EUID" -ne 0 ]; then
    log_error "请使用 sudo 运行此脚本"
    exit 1
fi

# 检查部署目录
if [ ! -d "$DEPLOY_DIR" ]; then
    log_warn "部署目录 $DEPLOY_DIR 不存在"
    log_info "创建部署目录..."
    mkdir -p "$DEPLOY_DIR"
    
    log_info "请先运行 quick_deploy.sh 部署项目"
    exit 1
fi

# 检查可执行文件
if [ ! -f "$DEPLOY_DIR/backend_cpp/build/woniunote_backend" ]; then
    log_error "未找到后端可执行文件"
    log_info "请先构建项目: cd backend_cpp/build && cmake .. && make"
    exit 1
fi

log_info "[1/4] 创建必要目录..."
mkdir -p "$DEPLOY_DIR/logs"
mkdir -p "$DEPLOY_DIR/backend_cpp/build/logs"
mkdir -p "$DEPLOY_DIR/backend_cpp/build/uploads"

log_info "[2/4] 安装 systemd 服务文件..."

# 创建服务文件
cat > "$SERVICE_FILE" << EOF
[Unit]
Description=WoniuNote C++ Backend Service
After=network.target mysql.service redis-server.service
Wants=mysql.service redis-server.service

[Service]
Type=simple
User=root
WorkingDirectory=$DEPLOY_DIR/backend_cpp/build
ExecStart=$DEPLOY_DIR/backend_cpp/build/woniunote_backend
ExecReload=/bin/kill -HUP \$MAINPID
Restart=always
RestartSec=5
StandardOutput=append:$DEPLOY_DIR/logs/backend.log
StandardError=append:$DEPLOY_DIR/logs/backend_error.log

# 环境变量
Environment=LANG=en_US.UTF-8
Environment=LC_ALL=en_US.UTF-8
# 使用系统库避免 GLIBCXX 版本冲突 (如有 Anaconda)
Environment=LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu:/usr/local/lib

# 资源限制
LimitNOFILE=65536
LimitNPROC=4096

[Install]
WantedBy=multi-user.target
EOF

log_info "[3/4] 重新加载 systemd..."
systemctl daemon-reload

log_info "[4/4] 启用开机自启..."
systemctl enable woniunote

echo ""
echo "========================================"
echo "  服务安装完成!"
echo "========================================"
echo ""
echo "  管理命令:"
echo "    启动服务:   sudo systemctl start woniunote"
echo "    停止服务:   sudo systemctl stop woniunote"
echo "    重启服务:   sudo systemctl restart woniunote"
echo "    查看状态:   sudo systemctl status woniunote"
echo "    查看日志:   sudo journalctl -u woniunote -f"
echo ""
echo "  或使用管理脚本:"
echo "    sudo bash $DEPLOY_DIR/scripts/manage.sh start"
echo "    sudo bash $DEPLOY_DIR/scripts/manage.sh status"
echo ""

# 提示是否立即启动
read -p "是否立即启动服务? [Y/n] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]] || [[ -z $REPLY ]]; then
    log_info "启动服务..."
    systemctl start woniunote
    sleep 2
    systemctl status woniunote --no-pager
fi
