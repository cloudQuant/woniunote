#!/bin/bash

# WoniuNote 生产环境配置脚本 - Ubuntu 22.04
# 此脚本用于在全新的 Ubuntu 22.04 服务器上配置 WoniuNote 运行环境

set -e

echo "========================================"
echo "  WoniuNote 生产环境配置脚本"
echo "  目标系统: Ubuntu 22.04"
echo "========================================"
echo ""

# 检查是否为 root 用户
if [ "$EUID" -ne 0 ]; then
    echo "[警告] 建议使用 sudo 运行此脚本"
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
    python3 \
    python3-pip \
    python3-venv

echo "[3/10] 安装 C++ 编译依赖..."
apt-get install -y \
    libssl-dev \
    libmysqlclient-dev \
    libmariadb-dev \
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

echo "[7/10] 安装 Node.js 18.x..."
curl -fsSL https://deb.nodesource.com/setup_18.x | bash -
apt-get install -y nodejs

echo "[8/10] 安装 vcpkg..."
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

echo "[9/10] 安装 vcpkg 依赖包 (这可能需要较长时间)..."
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

echo "[10/10] 编译 WoniuNote C++ 后端..."
cd "$PROJECT_DIR/backend_cpp"

# 创建 build 目录
mkdir -p build
cd build

# 使用 vcpkg 工具链编译
cmake .. \
    -DCMAKE_TOOLCHAIN_FILE="$VCPKG_DIR/scripts/buildsystems/vcpkg.cmake" \
    -DCMAKE_BUILD_TYPE=Release

cmake --build . --config Release -j$(nproc)

echo ""
echo "========================================"
echo "  环境配置完成!"
echo "========================================"
echo ""
echo "后续步骤:"
echo "1. 配置 MySQL 数据库:"
echo "   mysql -u root -p"
echo "   CREATE DATABASE woniunote CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
echo "   CREATE USER 'woniunote_user'@'localhost' IDENTIFIED BY 'your_password';"
echo "   GRANT ALL PRIVILEGES ON woniunote.* TO 'woniunote_user'@'localhost';"
echo "   FLUSH PRIVILEGES;"
echo ""
echo "2. 修改生产环境配置文件:"
echo "   cp $PROJECT_DIR/backend_cpp/config.json $PROJECT_DIR/backend_cpp/config.prod.json"
echo "   nano $PROJECT_DIR/backend_cpp/config.prod.json"
echo ""
echo "3. 配置 SSL 证书 (如使用 HTTPS):"
echo "   - 使用 Let's Encrypt: certbot certonly --nginx -d your-domain.com"
echo "   - 或手动配置: 将证书放入 /etc/ssl/certs/"
echo ""
echo "4. 配置 Nginx:"
echo "   cp $PROJECT_DIR/configs/woniunote_nginx_prod.conf /etc/nginx/sites-available/woniunote"
echo "   ln -s /etc/nginx/sites-available/woniunote /etc/nginx/sites-enabled/"
echo "   nginx -t && systemctl reload nginx"
echo ""
echo "5. 安装前端依赖并构建:"
echo "   cd $PROJECT_DIR/frontend && npm install && npm run build"
echo ""
echo "6. 启动服务:"
echo "   $PROJECT_DIR/scripts/start_prod.sh"
echo ""
echo "========================================"
