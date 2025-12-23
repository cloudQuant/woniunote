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

echo "[1/12] 更新系统包..."
apt-get update -y
apt-get upgrade -y

echo "[2/12] 安装基础依赖..."
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

echo "[3/12] 安装 C++ 编译依赖..."
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

echo "[4/12] 安装 MySQL..."
apt-get install -y mysql-server mysql-client
systemctl enable mysql
systemctl start mysql

echo "[5/12] 安装 Redis..."
apt-get install -y redis-server
systemctl enable redis-server
systemctl start redis-server

echo "[6/12] 安装 Nginx..."
apt-get install -y nginx
systemctl enable nginx

echo "[7/12] 安装 Node.js 18.x..."
curl -fsSL https://deb.nodesource.com/setup_18.x | bash -
apt-get install -y nodejs

echo "[8/12] 安装 vcpkg..."
VCPKG_DIR="$HOME/vcpkg"
if [ ! -d "$VCPKG_DIR" ]; then
    git clone https://github.com/microsoft/vcpkg.git "$VCPKG_DIR"
    cd "$VCPKG_DIR"
    ./bootstrap-vcpkg.sh
else
    echo "     vcpkg 已存在，跳过安装"
    cd "$VCPKG_DIR"
    git pull
    ./bootstrap-vcpkg.sh
fi

# 添加 vcpkg 到 PATH
echo 'export VCPKG_ROOT="$HOME/vcpkg"' >> ~/.bashrc
echo 'export PATH="$VCPKG_ROOT:$PATH"' >> ~/.bashrc
export VCPKG_ROOT="$HOME/vcpkg"
export PATH="$VCPKG_ROOT:$PATH"

echo "[9/12] 安装 vcpkg 依赖包 (这可能需要较长时间)..."
cd "$VCPKG_DIR"

# 安装项目所需的依赖
./vcpkg install drogon[mysql,redis]
./vcpkg install openssl
./vcpkg install jsoncpp
./vcpkg install jwt-cpp
./vcpkg install picojson
./vcpkg install hiredis
./vcpkg install libmariadb
./vcpkg install fmt
./vcpkg install spdlog

echo "[10/12] 编译 WoniuNote C++ 后端..."
cd "$PROJECT_DIR/backend_cpp"

# 创建 build 目录
mkdir -p build
cd build

# 使用 vcpkg 工具链编译
cmake .. \
    -DCMAKE_TOOLCHAIN_FILE="$VCPKG_DIR/scripts/buildsystems/vcpkg.cmake" \
    -DCMAKE_BUILD_TYPE=Release

cmake --build . --config Release -j$(nproc)

echo "[11/12] 安装 systemd 服务..."
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

echo "[12/12] 配置 Nginx..."
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
