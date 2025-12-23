#!/bin/bash

# WoniuNote 生产环境配置脚本 - Ubuntu 20.04/22.04
# 此脚本用于在 Ubuntu 服务器上配置 WoniuNote 运行环境

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 检测 Ubuntu 版本
UBUNTU_VERSION=$(lsb_release -rs 2>/dev/null || echo "unknown")

echo "========================================"
echo "  WoniuNote 生产环境配置脚本"
echo "  检测到系统: Ubuntu $UBUNTU_VERSION"
echo "========================================"
echo ""

# 检查是否为 root 用户
if [ "$EUID" -ne 0 ]; then
    log_error "请使用 sudo 运行此脚本"
    echo "用法: sudo bash $0"
    exit 1
fi

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "[1/10] 更新系统包..."
apt-get update -y
apt-get upgrade -y

echo "[2/10] 安装基础依赖..."
apt-get install -y \
    build-essential \
    cmake \
    ninja-build \
    git \
    curl \
    wget \
    zip \
    unzip \
    tar \
    pkg-config \
    autoconf \
    automake \
    libtool \
    rsync \
    lsof \
    python3 \
    python3-pip \
    python3-venv

echo "[3/10] 安装 C++ 编译依赖..."
# 注意: libmysqlclient-dev 和 libmariadb-dev 互相冲突，只能选择其一
# 这里选择 libmysqlclient-dev (MySQL 官方客户端库)
apt-get install -y \
    libssl-dev \
    libmysqlclient-dev \
    libhiredis-dev \
    libjsoncpp-dev \
    zlib1g-dev \
    libc-ares-dev \
    libsqlite3-dev \
    uuid-dev \
    libpq-dev \
    libbrotli-dev

echo "[4/10] 安装 MySQL..."
apt-get install -y mysql-server mysql-client
systemctl enable mysql
systemctl start mysql

echo "[5/10] 安装 Redis..."
apt-get install -y redis-server
systemctl enable redis-server
systemctl start redis-server

echo "[6/10] 安装 Nginx..."
apt-get install -y nginx
systemctl enable nginx

echo "[7/10] 安装 Node.js 22.x (LTS)..."
curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
apt-get install -y nodejs
log_info "Node.js 版本: $(node -v)"
log_info "npm 版本: $(npm -v)"

echo "[8/10] 安装 Drogon 框架及 C++ 依赖 (从源码编译)..."
# 安装 Drogon 编译所需的额外依赖
apt-get install -y \
    libjsoncpp-dev \
    libfmt-dev \
    libspdlog-dev \
    libbrotli-dev \
    libossp-uuid-dev

# 编译安装 c-ares (Ubuntu 20.04 自带版本太旧，不支持 ares_getaddrinfo)
CARES_VERSION="1.27.0"
if ! pkg-config --atleast-version=1.16.0 libcares 2>/dev/null; then
    log_info "编译 c-ares $CARES_VERSION (系统版本太旧)..."
    cd /tmp
    rm -rf c-ares-*
    
    wget -q https://github.com/c-ares/c-ares/releases/download/v${CARES_VERSION}/c-ares-${CARES_VERSION}.tar.gz -O c-ares.tar.gz || {
        log_error "无法下载 c-ares，请手动下载"
        log_error "下载地址: https://github.com/c-ares/c-ares/releases/download/v${CARES_VERSION}/c-ares-${CARES_VERSION}.tar.gz"
        exit 1
    }
    tar -xzf c-ares.tar.gz
    cd c-ares-${CARES_VERSION}
    
    mkdir -p build && cd build
    cmake .. -DCMAKE_BUILD_TYPE=Release
    make -j$(nproc)
    make install
    ldconfig
    
    cd /tmp
    rm -rf c-ares-* c-ares.tar.gz
    log_info "c-ares 安装完成"
else
    log_info "c-ares 版本满足要求"
fi

# 安装 jwt-cpp (header-only)
JWT_CPP_DIR="/usr/local/include/jwt-cpp"
if [ ! -d "$JWT_CPP_DIR" ]; then
    log_info "安装 jwt-cpp..."
    cd /tmp
    wget -q https://github.com/Thalhammer/jwt-cpp/archive/refs/tags/v0.7.0.tar.gz -O jwt-cpp.tar.gz || {
        log_warn "无法下载 jwt-cpp，尝试从项目目录复制..."
    }
    if [ -f jwt-cpp.tar.gz ]; then
        tar -xzf jwt-cpp.tar.gz
        cp -r jwt-cpp-0.7.0/include/jwt-cpp /usr/local/include/
        rm -rf jwt-cpp.tar.gz jwt-cpp-0.7.0
    fi
else
    log_info "jwt-cpp 已安装"
fi

# 编译安装 Drogon
DROGON_VERSION="v1.9.8"
DROGON_DIR="/tmp/drogon"
if ! pkg-config --exists drogon 2>/dev/null; then
    log_info "编译 Drogon $DROGON_VERSION ..."
    cd /tmp
    rm -rf drogon drogon-*
    
    # 尝试下载，如果失败则提示用户手动下载
    wget -q https://github.com/drogonframework/drogon/archive/refs/tags/$DROGON_VERSION.tar.gz -O drogon.tar.gz || {
        log_error "无法下载 Drogon，请手动下载并放到 /tmp/drogon 目录"
        log_error "下载地址: https://github.com/drogonframework/drogon/archive/refs/tags/$DROGON_VERSION.tar.gz"
        exit 1
    }
    tar -xzf drogon.tar.gz
    mv drogon-${DROGON_VERSION#v} drogon
    rm -f drogon.tar.gz
    
    cd "$DROGON_DIR"
    
    # 手动下载 trantor (匹配的版本)
    TRANTOR_VERSION="v1.5.21"
    log_info "下载 Trantor $TRANTOR_VERSION ..."
    wget -q https://github.com/an-tao/trantor/archive/refs/tags/$TRANTOR_VERSION.tar.gz -O trantor.tar.gz || {
        log_error "无法下载 trantor"
        log_error "下载地址: https://github.com/an-tao/trantor/archive/refs/tags/$TRANTOR_VERSION.tar.gz"
        exit 1
    }
    tar -xzf trantor.tar.gz
    rm -rf trantor
    mv trantor-${TRANTOR_VERSION#v} trantor
    rm -f trantor.tar.gz
    
    mkdir -p build && cd build
    cmake .. \
        -DCMAKE_BUILD_TYPE=Release \
        -DBUILD_MYSQL=ON \
        -DBUILD_REDIS=ON \
        -DBUILD_POSTGRESQL=OFF \
        -DBUILD_SQLITE=OFF
    
    make -j$(nproc)
    make install
    ldconfig
    
    log_info "Drogon 安装完成"
    rm -rf "$DROGON_DIR"
else
    log_info "Drogon 已安装"
fi

echo "[9/10] 编译 WoniuNote C++ 后端..."
cd "$PROJECT_DIR/backend_cpp"

mkdir -p build
cd build

# 使用系统库编译 (不使用 vcpkg)
cmake .. \
    -DCMAKE_BUILD_TYPE=Release \
    -DUSE_SYSTEM_LIBS=ON

cmake --build . --config Release -j$(nproc)

echo "[10/10] 安装 systemd 服务并部署..."
DEPLOY_DIR="/var/www/woniunote"
mkdir -p "$DEPLOY_DIR"
mkdir -p "$DEPLOY_DIR/logs"

# 复制项目文件
rsync -av --exclude='.git' \
          --exclude='node_modules' \
          --exclude='__pycache__' \
          --exclude='*.pyc' \
          "$PROJECT_DIR/" "$DEPLOY_DIR/"

# 安装 systemd 服务
bash "$PROJECT_DIR/scripts/install_service.sh" << EOF
n
EOF

echo "配置 Nginx..."
cp "$PROJECT_DIR/configs/woniunote_nginx_prod.conf" /etc/nginx/sites-available/woniunote
ln -sf /etc/nginx/sites-available/woniunote /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx

echo ""
echo "========================================"
echo "  环境配置完成!"  
echo "========================================"
echo ""
echo "后续步骤:"
echo ""
echo "1. 配置 MySQL 数据库:"
echo "   sudo mysql"
echo "   CREATE DATABASE woniunote CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
echo "   CREATE USER 'woniunote'@'localhost' IDENTIFIED BY 'your_password';"
echo "   GRANT ALL PRIVILEGES ON woniunote.* TO 'woniunote'@'localhost';"
echo "   FLUSH PRIVILEGES;"
echo "   EXIT;"
echo ""
echo "2. 修改生产环境配置文件:"
echo "   cp $DEPLOY_DIR/backend_cpp/config.json $DEPLOY_DIR/backend_cpp/config.prod.json"
echo "   nano $DEPLOY_DIR/backend_cpp/config.prod.json"
echo "   # 修改数据库连接信息、密钥等"
echo ""
echo "3. 配置 SSL 证书 (使用 Let's Encrypt):"
echo "   apt install certbot python3-certbot-nginx"
echo "   certbot --nginx -d your-domain.com"
echo ""
echo "4. 启动服务:"
echo "   sudo systemctl start woniunote"
echo "   sudo systemctl status woniunote"
echo ""
echo "管理命令:"
echo "  sudo bash $DEPLOY_DIR/scripts/manage.sh start    # 启动"
echo "  sudo bash $DEPLOY_DIR/scripts/manage.sh stop     # 停止"
echo "  sudo bash $DEPLOY_DIR/scripts/manage.sh restart  # 重启"
echo "  sudo bash $DEPLOY_DIR/scripts/manage.sh status   # 状态"
echo "  sudo bash $DEPLOY_DIR/scripts/manage.sh logs backend  # 日志"
echo ""
echo "========================================"
