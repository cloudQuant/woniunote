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
# 注意: 使用 MariaDB 客户端库 (支持 Drogon 需要的非阻塞 MySQL API)
# libmysqlclient-dev 不支持 mysql_real_connect_start 等异步函数
apt-get install -y \
    libssl-dev \
    libmariadb-dev \
    libmariadb-dev-compat \
    libhiredis-dev \
    libjsoncpp-dev \
    zlib1g-dev \
    libc-ares-dev \
    libsqlite3-dev \
    uuid-dev \
    libpq-dev \
    libbrotli-dev \
    libcrypt-dev

# 创建 mysqlclient_r 符号链接 (Drogon FindMySQL 需要)
if [ ! -f /usr/lib/x86_64-linux-gnu/libmysqlclient_r.so ]; then
    ln -sf /usr/lib/x86_64-linux-gnu/libmariadb.so /usr/lib/x86_64-linux-gnu/libmysqlclient_r.so
fi

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
    libossp-uuid-dev \
    libyaml-cpp-dev

# 本地源码包目录 (优先使用本地包，避免联网下载)
REPOS_DIR="$PROJECT_DIR/repos"

# 辅助函数: 解压源码包 (支持 .tar.gz 和 .tar)
extract_package() {
    local file="$1"
    if [[ "$file" == *.tar.gz ]]; then
        tar -xzf "$file"
    elif [[ "$file" == *.tar ]]; then
        tar -xf "$file"
    fi
}

# 编译安装 c-ares (Ubuntu 20.04 自带版本太旧，不支持 ares_getaddrinfo)
CARES_VERSION="1.34.6"
if ! pkg-config --atleast-version=1.16.0 libcares 2>/dev/null; then
    log_info "编译 c-ares $CARES_VERSION (系统版本太旧)..."
    cd /tmp
    rm -rf c-ares-*
    
    # 优先使用本地源码包
    if [ -f "$REPOS_DIR/c-ares-${CARES_VERSION}.tar.gz" ]; then
        log_info "使用本地源码包: repos/c-ares-${CARES_VERSION}.tar.gz"
        cp "$REPOS_DIR/c-ares-${CARES_VERSION}.tar.gz" .
        tar -xzf c-ares-${CARES_VERSION}.tar.gz
    elif [ -f "$REPOS_DIR/c-ares-${CARES_VERSION}.tar" ]; then
        log_info "使用本地源码包: repos/c-ares-${CARES_VERSION}.tar"
        cp "$REPOS_DIR/c-ares-${CARES_VERSION}.tar" .
        tar -xf c-ares-${CARES_VERSION}.tar
    else
        log_info "尝试从网络下载 c-ares..."
        wget -q https://github.com/c-ares/c-ares/releases/download/v${CARES_VERSION}/c-ares-${CARES_VERSION}.tar.gz || {
            log_error "无法下载 c-ares，请手动下载到 repos 目录"
            log_error "下载地址: https://github.com/c-ares/c-ares/releases/download/v${CARES_VERSION}/c-ares-${CARES_VERSION}.tar.gz"
            exit 1
        }
        tar -xzf c-ares-${CARES_VERSION}.tar.gz
    fi
    
    cd c-ares-${CARES_VERSION}
    mkdir -p build && cd build
    cmake .. -DCMAKE_BUILD_TYPE=Release
    make -j$(nproc)
    make install
    ldconfig
    
    cd /tmp
    rm -rf c-ares-*
    log_info "c-ares 安装完成"
else
    log_info "c-ares 版本满足要求"
fi

# 安装 jwt-cpp (header-only)
# 注: picojson 已包含在项目 backend_cpp/third_party/picojson/ 目录中
JWT_CPP_VERSION="0.7.0"
JWT_CPP_DIR="/usr/local/include/jwt-cpp"
if [ ! -d "$JWT_CPP_DIR" ]; then
    log_info "安装 jwt-cpp $JWT_CPP_VERSION..."
    cd /tmp
    rm -rf jwt-cpp-*
    
    # 优先使用本地源码包
    if [ -f "$REPOS_DIR/jwt-cpp-${JWT_CPP_VERSION}.tar.gz" ]; then
        log_info "使用本地源码包: repos/jwt-cpp-${JWT_CPP_VERSION}.tar.gz"
        cp "$REPOS_DIR/jwt-cpp-${JWT_CPP_VERSION}.tar.gz" .
        tar -xzf jwt-cpp-${JWT_CPP_VERSION}.tar.gz
    elif [ -f "$REPOS_DIR/jwt-cpp-${JWT_CPP_VERSION}.tar" ]; then
        log_info "使用本地源码包: repos/jwt-cpp-${JWT_CPP_VERSION}.tar"
        cp "$REPOS_DIR/jwt-cpp-${JWT_CPP_VERSION}.tar" .
        tar -xf jwt-cpp-${JWT_CPP_VERSION}.tar
    else
        log_info "尝试从网络下载 jwt-cpp..."
        wget -q https://github.com/Thalhammer/jwt-cpp/archive/refs/tags/v${JWT_CPP_VERSION}.tar.gz -O jwt-cpp-${JWT_CPP_VERSION}.tar.gz || {
            log_warn "无法下载 jwt-cpp"
            exit 1
        }
        tar -xzf jwt-cpp-${JWT_CPP_VERSION}.tar.gz
    fi
    
    cp -r jwt-cpp-${JWT_CPP_VERSION}/include/jwt-cpp /usr/local/include/
    rm -rf jwt-cpp-*
    log_info "jwt-cpp 安装完成"
else
    log_info "jwt-cpp 已安装"
fi

# 编译安装 Drogon
DROGON_VERSION="1.9.8"
TRANTOR_VERSION="1.5.21"
DROGON_DIR="/tmp/drogon"

# Drogon 使用 CMake 配置文件，不是 pkg-config
if [ ! -f "/usr/local/lib/cmake/Drogon/DrogonConfig.cmake" ]; then
    log_info "编译 Drogon v$DROGON_VERSION ..."
    cd /tmp
    rm -rf drogon drogon-*
    
    # 优先使用本地源码包
    if [ -f "$REPOS_DIR/drogon-${DROGON_VERSION}.tar.gz" ]; then
        log_info "使用本地源码包: repos/drogon-${DROGON_VERSION}.tar.gz"
        cp "$REPOS_DIR/drogon-${DROGON_VERSION}.tar.gz" .
        tar -xzf drogon-${DROGON_VERSION}.tar.gz
    elif [ -f "$REPOS_DIR/drogon-${DROGON_VERSION}.tar" ]; then
        log_info "使用本地源码包: repos/drogon-${DROGON_VERSION}.tar"
        cp "$REPOS_DIR/drogon-${DROGON_VERSION}.tar" .
        tar -xf drogon-${DROGON_VERSION}.tar
    else
        log_info "尝试从网络下载 Drogon..."
        wget -q https://github.com/drogonframework/drogon/archive/refs/tags/v${DROGON_VERSION}.tar.gz -O drogon-${DROGON_VERSION}.tar.gz || {
            log_error "无法下载 Drogon，请手动下载到 repos 目录"
            log_error "下载地址: https://github.com/drogonframework/drogon/archive/refs/tags/v${DROGON_VERSION}.tar.gz"
            exit 1
        }
        tar -xzf drogon-${DROGON_VERSION}.tar.gz
    fi
    mv drogon-${DROGON_VERSION} drogon
    
    cd "$DROGON_DIR"
    rm -rf trantor
    
    # 优先使用本地 trantor 源码包
    if [ -f "$REPOS_DIR/trantor-${TRANTOR_VERSION}.tar.gz" ]; then
        log_info "使用本地源码包: repos/trantor-${TRANTOR_VERSION}.tar.gz"
        cp "$REPOS_DIR/trantor-${TRANTOR_VERSION}.tar.gz" .
        tar -xzf trantor-${TRANTOR_VERSION}.tar.gz
        mv trantor-${TRANTOR_VERSION} trantor
    elif [ -f "$REPOS_DIR/trantor-${TRANTOR_VERSION}.tar" ]; then
        log_info "使用本地源码包: repos/trantor-${TRANTOR_VERSION}.tar"
        cp "$REPOS_DIR/trantor-${TRANTOR_VERSION}.tar" .
        tar -xf trantor-${TRANTOR_VERSION}.tar
        mv trantor-${TRANTOR_VERSION} trantor
    else
        log_info "尝试从网络下载 Trantor..."
        wget -q https://github.com/an-tao/trantor/archive/refs/tags/v${TRANTOR_VERSION}.tar.gz -O trantor.tar.gz || {
            log_error "无法下载 trantor，请手动下载到 repos 目录"
            log_error "下载地址: https://github.com/an-tao/trantor/archive/refs/tags/v${TRANTOR_VERSION}.tar.gz"
            exit 1
        }
        tar -xzf trantor.tar.gz
        mv trantor-${TRANTOR_VERSION} trantor
    fi
    
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

# 安装前端依赖
log_info "安装前端依赖..."
cd "$DEPLOY_DIR/frontend"
if [ -f "package.json" ]; then
    # 清理可能损坏的 node_modules
    if [ -d "node_modules" ]; then
        log_info "清理旧的 node_modules..."
        rm -rf node_modules package-lock.json
    fi
    
    # 清理 npm 缓存
    npm cache clean --force 2>/dev/null || true
    
    # 安装依赖
    log_info "执行 npm install..."
    if npm install 2>&1 | tail -10; then
        log_info "前端依赖安装完成"
    else
        log_warn "前端依赖安装可能有问题，尝试使用 npm ci..."
        npm ci 2>&1 | tail -10 || log_warn "npm ci 也失败，请手动检查"
    fi
else
    log_warn "未找到 package.json，跳过前端依赖安装"
fi
cd "$PROJECT_DIR"

# 安装 systemd 服务
bash "$PROJECT_DIR/scripts/install_service.sh" << EOF
n
EOF

echo "配置 Nginx..."
# 使用初始配置 (HTTP-only)，SSL 证书需要后续配置
if [ -f "$PROJECT_DIR/configs/woniunote_nginx_initial.conf" ]; then
    cp "$PROJECT_DIR/configs/woniunote_nginx_initial.conf" /etc/nginx/sites-available/woniunote
else
    cp "$PROJECT_DIR/configs/woniunote_nginx_prod.conf" /etc/nginx/sites-available/woniunote
fi
ln -sf /etc/nginx/sites-available/woniunote /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx || log_warn "Nginx 配置测试失败，请手动检查"

echo ""
echo "========================================"
echo "  初始化数据库..."
echo "========================================"

# 数据库初始化函数
init_database() {
    local DB_NAME="woniunote"
    local DB_USER="woniunote"
    local DB_PASS="woniunote_password"  # 默认密码，生产环境应修改
    local SQL_DIR="$PROJECT_DIR/scripts/sql"
    
    log_info "检查 MySQL 服务状态..."
    if ! systemctl is-active --quiet mysql; then
        log_warn "MySQL 服务未运行，正在启动..."
        systemctl start mysql
    fi
    
    # 检查数据库是否存在，不存在则创建
    if ! mysql -e "USE $DB_NAME" 2>/dev/null; then
        log_info "创建数据库 $DB_NAME..."
        mysql -e "CREATE DATABASE IF NOT EXISTS $DB_NAME CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
        
        # 创建数据库用户
        log_info "创建数据库用户 $DB_USER..."
        mysql -e "CREATE USER IF NOT EXISTS '$DB_USER'@'localhost' IDENTIFIED BY '$DB_PASS';"
        mysql -e "GRANT ALL PRIVILEGES ON $DB_NAME.* TO '$DB_USER'@'localhost';"
        mysql -e "FLUSH PRIVILEGES;"
        
        log_info "数据库和用户创建成功"
        log_warn "默认密码: $DB_PASS (请在生产环境中修改)"
    else
        log_info "数据库 $DB_NAME 已存在"
    fi
    
    # 执行所有 SQL 文件 (按文件名排序)
    if [ -d "$SQL_DIR" ]; then
        log_info "执行 SQL 初始化脚本..."
        for sql_file in $(ls "$SQL_DIR"/*.sql 2>/dev/null | sort); do
            if [ -f "$sql_file" ]; then
                log_info "  执行: $(basename $sql_file)"
                mysql "$DB_NAME" < "$sql_file" 2>/dev/null || log_warn "  警告: $(basename $sql_file) 执行时有警告"
            fi
        done
        log_info "SQL 脚本执行完成"
    else
        log_warn "SQL 目录不存在: $SQL_DIR"
    fi
}

# 数据库表结构核对函数
verify_database_schema() {
    local DB_NAME="woniunote"
    local LOG_DIR="$PROJECT_DIR/logs"
    local LOG_FILE="$LOG_DIR/db_schema_verify_$(date +%Y%m%d_%H%M%S).log"
    
    # 检查数据库是否存在
    if ! mysql -e "USE $DB_NAME" 2>/dev/null; then
        log_warn "数据库不存在，跳过表结构核对"
        return 1
    fi
    
    log_info "核对数据库表结构..."
    mkdir -p "$LOG_DIR"
    
    # 预期的表和列定义
    declare -A EXPECTED_TABLES
    EXPECTED_TABLES=(
        ["users"]="userid,username,password,nickname,avatar,qq,role,credit,createtime,updatetime"
        ["article"]="articleid,userid,type,headline,content,thumbnail,credit,readcount,replycount,recommended,hidden,drafted,checked,createtime,updatetime"
        ["comment"]="commentid,userid,articleid,content,ipaddr,replyid,agreecount,opposecount,hidden,createtime,updatetime"
        ["favorite"]="favoriteid,userid,articleid,canceled,createtime,updatetime"
        ["credit"]="creditid,userid,category,target,credit,createtime,updatetime"
        ["category"]="id,name"
        ["cardcategory"]="id,name"
        ["card"]="id,type,headline,content,createtime,updatetime,donetime,usedtime,begintime,endtime,cardcategory_id"
        ["item"]="id,body,category_id"
        ["math_training_records"]="id,user_id,difficulty,total_questions,correct_count,wrong_count,accuracy,start_time,end_time,duration_seconds,created_at"
        ["math_training_wrong_answers"]="id,record_id,user_id,question,correct_answer,user_answer,operation,difficulty,created_at"
    )
    
    local TOTAL_ISSUES=0
    
    # 写入日志头
    {
        echo "=========================================="
        echo "WoniuNote 数据库表结构核对报告"
        echo "时间: $(date)"
        echo "数据库: $DB_NAME"
        echo "=========================================="
        echo ""
    } > "$LOG_FILE"
    
    # 获取实际表列表
    local ACTUAL_TABLES=$(mysql -N -e "USE $DB_NAME; SHOW TABLES;" 2>/dev/null)
    
    for table in "${!EXPECTED_TABLES[@]}"; do
        if ! echo "$ACTUAL_TABLES" | grep -q "^${table}$"; then
            echo "[缺失表] $table" >> "$LOG_FILE"
            ((TOTAL_ISSUES++))
            continue
        fi
        
        # 获取实际列
        local ACTUAL_COLUMNS=$(mysql -N -e "USE $DB_NAME; SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA='$DB_NAME' AND TABLE_NAME='$table' ORDER BY ORDINAL_POSITION;" 2>/dev/null | tr '\n' ',' | sed 's/,$//')
        local EXPECTED_COLUMNS="${EXPECTED_TABLES[$table]}"
        
        IFS=',' read -ra EXPECTED_ARR <<< "$EXPECTED_COLUMNS"
        IFS=',' read -ra ACTUAL_ARR <<< "$ACTUAL_COLUMNS"
        
        # 检查缺失的列
        for col in "${EXPECTED_ARR[@]}"; do
            if [[ ! " ${ACTUAL_ARR[*]} " =~ " ${col} " ]]; then
                echo "[缺失列] $table.$col" >> "$LOG_FILE"
                ((TOTAL_ISSUES++))
            fi
        done
        
        # 检查额外的列
        for col in "${ACTUAL_ARR[@]}"; do
            if [[ ! " ${EXPECTED_ARR[*]} " =~ " ${col} " ]]; then
                echo "[额外列] $table.$col" >> "$LOG_FILE"
            fi
        done
    done
    
    if [ $TOTAL_ISSUES -eq 0 ]; then
        log_info "表结构核对通过"
    else
        log_warn "发现 $TOTAL_ISSUES 个差异，详见日志: $LOG_FILE"
    fi
    
    return $TOTAL_ISSUES
}

# 执行数据库初始化
init_database

# 执行表结构核对
echo ""
echo "========================================"
echo "  核对数据库表结构..."
echo "========================================"
verify_database_schema || true

echo ""
echo "========================================"
echo "  环境配置完成!"  
echo "========================================"
echo ""
echo "后续步骤:"
echo ""
echo "1. 配置 MySQL 数据库 (如尚未配置):"
echo "   sudo mysql"
echo "   CREATE DATABASE woniunote CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
echo "   CREATE USER 'woniunote'@'localhost' IDENTIFIED BY 'your_password';"
echo "   GRANT ALL PRIVILEGES ON woniunote.* TO 'woniunote'@'localhost';"
echo "   FLUSH PRIVILEGES;"
echo "   EXIT;"
echo ""
echo "   然后初始化数据库表:"
echo "   sudo bash $PROJECT_DIR/scripts/init_db.sh"
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
