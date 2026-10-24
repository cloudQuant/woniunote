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
SETUP_SCRIPT="$SCRIPT_DIR/$(basename "${BASH_SOURCE[0]}")"
if [ "${WONIUNOTE_SETUP_LOCKED:-}" = yes ]; then
    bash "$PROJECT_DIR/scripts/deploy_release.sh" assert-locked
else
    DEPLOY_MANAGER="$PROJECT_DIR/scripts/deploy_release.sh"
    if [ -n "${DEPLOY_DIR:-}" ] && [ -f "$DEPLOY_DIR/scripts/deploy_release.sh" ]; then
        DEPLOY_MANAGER="$DEPLOY_DIR/scripts/deploy_release.sh"
    fi
    exec env WONIUNOTE_SETUP_SCRIPT="$SETUP_SCRIPT" bash "$DEPLOY_MANAGER" setup
fi

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
    util-linux \
    coreutils \
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
if command -v mysql &> /dev/null && systemctl is-active --quiet mysql; then
    log_info "MySQL 已安装并运行中，跳过安装"
else
    apt-get install -y mysql-server mysql-client
    systemctl enable mysql
    systemctl start mysql
    log_info "MySQL 安装完成"
fi

echo "[5/10] 安装 Redis..."
if command -v redis-server &> /dev/null && systemctl is-active --quiet redis-server; then
    log_info "Redis 已安装并运行中，跳过安装"
else
    apt-get install -y redis-server
    systemctl enable redis-server
    systemctl start redis-server
    log_info "Redis 安装完成"
fi

echo "[6/10] 安装 Nginx..."
if command -v nginx &> /dev/null; then
    log_info "Nginx 已安装，跳过安装"
else
    apt-get install -y nginx
    log_info "Nginx 安装完成"
fi
# Serialize the service configuration change with deploy/start/stop/rollback.
bash "$PROJECT_DIR/scripts/deploy_release.sh" run-locked timeout 5s systemctl enable nginx

echo "[7/10] 安装 Node.js 22.x (LTS)..."
# 版本门禁复用前端脚本：锁文件要求 Node >= 20.19.0（unplugin-* 的 engines）。
# 只判断主版本 >= 18 会放过不满足要求的解释器（迭代20 / Epic 20.3A）。
NODE_CHECK="$PROJECT_DIR/frontend/scripts/check-node-version.mjs"
node_satisfies_engines() {
    command -v node &> /dev/null && node "$NODE_CHECK" >/dev/null 2>&1
}
if node_satisfies_engines; then
    log_info "Node.js 已安装且满足前端要求 ($(node -v))，跳过安装"
else
    log_info "Node.js 未安装或版本不满足前端要求，安装/升级到 22.x..."
    curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
    apt-get install -y nodejs
fi
log_info "Node.js 版本: $(node -v)"
if ! node_satisfies_engines; then
    log_warn "Node.js 版本仍不满足前端 engines 要求，前端安装/构建将失败"
fi
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

# 检查 Drogon 是否已安装且包含 MySQL 支持
NEED_DROGON_INSTALL=false
if [ ! -f "/usr/local/lib/cmake/Drogon/DrogonConfig.cmake" ]; then
    NEED_DROGON_INSTALL=true
    log_info "Drogon 未安装"
# 大小写不敏感：DrogonTargets.cmake 里写的是 "MySQL"，此前用 "mysql" 匹配永远失败，
# 于是每次部署都误判“缺少 MySQL 支持”并重编译 Drogon（约 10-20 分钟）
# （迭代20 隔离环境演练发现）。
elif ! grep -qi "mysql" /usr/local/lib/cmake/Drogon/DrogonTargets.cmake 2>/dev/null; then
    NEED_DROGON_INSTALL=true
    log_warn "Drogon 已安装但缺少 MySQL 支持，将重新编译"
fi

if [ "$NEED_DROGON_INSTALL" = true ]; then
    log_info "编译 Drogon v$DROGON_VERSION (包含 MySQL 支持)..."
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
    
    log_info "Drogon 安装完成 (包含 MySQL 支持)"
    rm -rf "$DROGON_DIR"
else
    log_info "Drogon 已安装且包含 MySQL 支持"
fi

echo "[9/10] 部署构建由受保护的候选发布事务完成..."

echo "[10/10] 准备服务环境并交接到统一发布事务..."
# 部署目录 (可通过环境变量覆盖，默认使用源码目录)
DEPLOY_DIR="${DEPLOY_DIR:-$PROJECT_DIR}"
mkdir -p "$DEPLOY_DIR"
mkdir -p "$DEPLOY_DIR/logs"

# 复制项目文件 (仅当部署目录与源码目录不同时)
if [ "$DEPLOY_DIR" != "$PROJECT_DIR" ]; then
    log_info "复制项目文件到 $DEPLOY_DIR..."
    # package-lock.json 必须随源码部署：npm ci 依赖它做可复现安装。
    rsync -av --exclude='.git' \
              --exclude='node_modules' \
              --exclude='config.local.json' \
              --exclude='frontend/dist/' \
              --exclude='backend_cpp/build/' \
              --exclude='backend_cpp/uploads/' \
              --exclude='backend_cpp/resource/thumb/' \
              --exclude='__pycache__' \
              --exclude='*.pyc' \
              "$PROJECT_DIR/" "$DEPLOY_DIR/"
else
    log_info "部署目录与源码目录相同，跳过复制"
fi

# 生产二进制、静态文件和 systemd unit 只由 deploy_release.sh 创建与切换。

echo "配置防火墙 (ufw)..."
if command -v ufw &> /dev/null; then
    # 检查 ufw 是否启用
    if ufw status | grep -q "Status: active"; then
        log_info "ufw 已启用，配置端口规则..."
        ufw allow 22/tcp comment 'SSH' 2>/dev/null || true
        ufw allow 80/tcp comment 'HTTP' 2>/dev/null || true
        ufw allow 443/tcp comment 'HTTPS' 2>/dev/null || true
        ufw allow 8888/tcp comment 'Frontend Dev' 2>/dev/null || true
        ufw allow 5173/tcp comment 'Backend API' 2>/dev/null || true
        log_info "防火墙端口配置完成"
    else
        log_info "ufw 未启用，跳过防火墙配置"
        log_warn "建议启用防火墙: ufw enable"
    fi
else
    log_warn "ufw 未安装，跳过防火墙配置"
fi

echo "配置 SSL 证书..."
SSL_CERT_DIR="/etc/ssl/woniunote"
mkdir -p "$SSL_CERT_DIR"

# 检查是否有自定义 SSL 证书
if [ -d "$PROJECT_DIR/configs/yunjinqi.top_nginx" ]; then
    log_info "使用项目中的 SSL 证书..."
    cp "$PROJECT_DIR/configs/yunjinqi.top_nginx/yunjinqi.top_bundle.crt" "$SSL_CERT_DIR/fullchain.pem"
    cp "$PROJECT_DIR/configs/yunjinqi.top_nginx/yunjinqi.top.key" "$SSL_CERT_DIR/privkey.pem"
    chmod 600 "$SSL_CERT_DIR/privkey.pem"
    chmod 644 "$SSL_CERT_DIR/fullchain.pem"
    log_info "SSL 证书已安装到 $SSL_CERT_DIR"
    USE_SSL=true
else
    log_error "未找到生产 HTTPS 证书，发布事务无法通过 Nginx 配置校验"
    exit 1
fi

WONIUNOTE_STATE_DIR="$WONIUNOTE_STATE_DIR"
if [ -z "$WONIUNOTE_STATE_DIR" ]; then WONIUNOTE_STATE_DIR=/var/lib/woniunote; fi
WONIUNOTE_DATA_DIR="$DEPLOY_DIR/backend_cpp"
WONIUNOTE_RUNTIME_CONFIG="$WONIUNOTE_RUNTIME_CONFIG"
if [ -z "$WONIUNOTE_RUNTIME_CONFIG" ]; then
    if [ -f "$DEPLOY_DIR/backend_cpp/config.local.json" ]; then WONIUNOTE_RUNTIME_CONFIG="$DEPLOY_DIR/backend_cpp/config.local.json"
    elif [ -f "$PROJECT_DIR/backend_cpp/config.local.json" ]; then WONIUNOTE_RUNTIME_CONFIG="$PROJECT_DIR/backend_cpp/config.local.json"
    elif [ -f /etc/woniunote/config.json ]; then WONIUNOTE_RUNTIME_CONFIG=/etc/woniunote/config.json
    else WONIUNOTE_RUNTIME_CONFIG="$PROJECT_DIR/backend_cpp/config.prod.json"; fi
fi
if [ "$DEPLOY_DIR" != "$PROJECT_DIR" ]; then
    printf '%s\n' "$PROJECT_DIR" > "$DEPLOY_DIR/.woniunote-source-repo"
fi
DEPLOY_ENV="$DEPLOY_DIR/.woniunote-deploy.env"
if [ ! -f "$DEPLOY_ENV" ]; then
    cat > "$DEPLOY_ENV" <<EOF
WONIUNOTE_PROJECT_DIR=$PROJECT_DIR
WONIUNOTE_STATE_DIR=$WONIUNOTE_STATE_DIR
WONIUNOTE_DATA_DIR=$WONIUNOTE_DATA_DIR
WONIUNOTE_RUNTIME_CONFIG=$WONIUNOTE_RUNTIME_CONFIG
WONIUNOTE_NGINX_CONFIG=/etc/nginx/nginx.conf
WONIUNOTE_SSL_CERT=$SSL_CERT_DIR/fullchain.pem
WONIUNOTE_SSL_KEY=$SSL_CERT_DIR/privkey.pem
WONIUNOTE_SMOKE_HOST=$WONIUNOTE_SMOKE_HOST
WONIUNOTE_SMOKE_SCHEME=$WONIUNOTE_SMOKE_SCHEME
WONIUNOTE_SMOKE_PORT=$WONIUNOTE_SMOKE_PORT
WONIUNOTE_SMOKE_READONLY_API=$WONIUNOTE_SMOKE_READONLY_API
WONIUNOTE_SMOKE_THUMB_PATH=$WONIUNOTE_SMOKE_THUMB_PATH
WONIUNOTE_SMOKE_UPLOAD_PATH=$WONIUNOTE_SMOKE_UPLOAD_PATH
WONIUNOTE_SMOKE_UPLOAD_FILE=$WONIUNOTE_SMOKE_UPLOAD_FILE
WONIUNOTE_SMOKE_UPLOAD_SHA256=$WONIUNOTE_SMOKE_UPLOAD_SHA256
WONIUNOTE_COMPATIBILITY_RECORD=$WONIUNOTE_COMPATIBILITY_RECORD
WONIUNOTE_ROLLBACK_COMPATIBILITY_RECORD=$WONIUNOTE_ROLLBACK_COMPATIBILITY_RECORD
EOF
    chmod 0600 "$DEPLOY_ENV"
fi

log_info "Nginx 生产配置将在候选通过独立 nginx -t 后由发布事务原子切换"

echo ""
echo "========================================"
echo "  检查数据库..."
echo "========================================"

# 数据库初始化函数
init_database() {
    local DB_NAME="woniunote"
    local DB_USER="woniunote"
    # 数据库密码必须由环境变量提供（迭代19：移除内置默认密码）
    if [ -z "${DB_PASS:-}" ]; then
        log_error "未提供数据库密码：请以 DB_PASS=<密码> 方式运行本脚本（迭代19 起不再内置默认密码）"
        return 1
    fi
    local SQL_DIR="$PROJECT_DIR/scripts/sql"
    
    log_info "检查 MySQL 服务状态..."
    if ! systemctl is-active --quiet mysql; then
        log_warn "MySQL 服务未运行，正在启动..."
        systemctl start mysql
    fi
    
    # 尝试多种方式检查数据库是否存在
    DB_EXISTS=false
    
    # 方式1: 使用 woniunote 用户连接
    if mysql -u"$DB_USER" -p"$DB_PASS" -e "USE $DB_NAME" 2>/dev/null; then
        DB_EXISTS=true
        log_info "数据库 $DB_NAME 已存在 (使用 $DB_USER 用户验证)"
    # 方式2: 使用 sudo mysql (适用于 auth_socket)
    elif sudo mysql -e "USE $DB_NAME" 2>/dev/null; then
        DB_EXISTS=true
        log_info "数据库 $DB_NAME 已存在 (使用 root 验证)"
    fi
    
    if [ "$DB_EXISTS" = true ]; then
        # 检查表是否存在
        TABLE_COUNT=$(mysql -u"$DB_USER" -p"$DB_PASS" -N -e "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='$DB_NAME'" 2>/dev/null || echo "0")
        if [ "$TABLE_COUNT" -gt 0 ] 2>/dev/null; then
            log_info "数据库已有 $TABLE_COUNT 个表，跳过初始化"
            return 0
        fi
    fi
    
    # 数据库不存在，需要创建
    log_info "需要初始化数据库..."
    log_warn "如果数据库已存在，请确保 MySQL 用户 $DB_USER 密码为 $DB_PASS"
    log_warn "或者手动运行: bash $PROJECT_DIR/scripts/import_db.sh"
}

# 数据库表结构核对函数
verify_database_schema() {
    local DB_NAME="woniunote"
    local DB_USER="woniunote"
    # 数据库密码必须由环境变量提供（迭代19：移除内置默认密码）
    if [ -z "${DB_PASS:-}" ]; then
        log_error "未提供数据库密码：请以 DB_PASS=<密码> 方式运行本脚本（迭代19 起不再内置默认密码）"
        return 1
    fi
    local LOG_DIR="$PROJECT_DIR/logs"
    local LOG_FILE="$LOG_DIR/db_schema_verify_$(date +%Y%m%d_%H%M%S).log"
    
    # 检查数据库是否存在 (使用用户认证)
    if ! mysql -u"$DB_USER" -p"$DB_PASS" -e "USE $DB_NAME" 2>/dev/null && ! sudo mysql -e "USE $DB_NAME" 2>/dev/null; then
        log_warn "数据库不存在或无法连接，跳过表结构核对"
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
    
    # 设置 MySQL 命令 (优先使用用户认证)
    local MYSQL_CMD="mysql -u$DB_USER -p$DB_PASS"
    if ! $MYSQL_CMD -e "SELECT 1" &>/dev/null; then
        MYSQL_CMD="sudo mysql"
    fi
    
    # 获取实际表列表
    local ACTUAL_TABLES=$($MYSQL_CMD -N -e "USE $DB_NAME; SHOW TABLES;" 2>/dev/null)
    
    for table in "${!EXPECTED_TABLES[@]}"; do
        if ! echo "$ACTUAL_TABLES" | grep -q "^${table}$"; then
            echo "[缺失表] $table" >> "$LOG_FILE"
            ((TOTAL_ISSUES++))
            continue
        fi
        
        # 获取实际列
        local ACTUAL_COLUMNS=$($MYSQL_CMD -N -e "USE $DB_NAME; SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA='$DB_NAME' AND TABLE_NAME='$table' ORDER BY ORDINAL_POSITION;" 2>/dev/null | tr '\n' ',' | sed 's/,$//')
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

# Fail closed before setup hands off to the release transaction. Unlike the
# general compatibility report below, this one field is a hard prerequisite
# because the backend persists complete public upload URLs in it.
check_article_thumbnail_schema() {
    local DB_NAME="woniunote"
    local DB_USER="woniunote"
    local MIGRATION="$PROJECT_DIR/scripts/sql/migrations/2026-10-24_article_thumbnail.sql"
    local query="SELECT CONCAT(DATA_TYPE, '|', CHARACTER_MAXIMUM_LENGTH, '|', IS_NULLABLE) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA='$DB_NAME' AND TABLE_NAME='article' AND COLUMN_NAME='thumbnail';"
    local actual=""

    if [ -z "${DB_PASS:-}" ]; then
        log_error "无法验证 article.thumbnail：未提供数据库密码。"
        log_error "请先备份数据库并按迁移说明处理：$MIGRATION"
        return 1
    fi

    if ! actual="$(mysql -u"$DB_USER" -p"$DB_PASS" --database="$DB_NAME" \
        --batch --raw --skip-column-names --execute="$query" 2>/dev/null)"; then
        if ! actual="$(sudo mysql --database="$DB_NAME" --batch --raw \
            --skip-column-names --execute="$query" 2>/dev/null)"; then
            log_error "无法查询 article.thumbnail；停止安装/升级，未切换服务。"
            log_error "请先备份数据库并按迁移说明处理：$MIGRATION"
            return 1
        fi
    fi

    if [ "$actual" != "varchar|512|YES" ]; then
        log_error "article.thumbnail 不兼容 (实际: ${actual:-missing})；停止安装/升级，未切换服务。"
        log_error "请先备份数据库并按迁移说明处理：$MIGRATION"
        return 1
    fi
    log_info "article.thumbnail schema 已满足 varchar(512) NULL。"
}

# 执行数据库初始化
init_database

# This read-only thumbnail precheck runs before the advisory full-schema report;
# it does not apply the migration or modify the existing thumbnail column.
if ! check_article_thumbnail_schema; then
    exit 1
fi

# 执行表结构核对
echo ""
echo "========================================"
echo "  核对数据库表结构..."
echo "========================================"
verify_database_schema || true

# 启动服务
echo ""
echo "========================================"
echo "  启动服务..."
echo "========================================"

# Nginx start/reload and the first release switch run under deploy_release.sh's
# lock after the candidate has been built and its config has passed nginx -t.
# setup 的升级/首次部署路径与 start/restart 共用候选构建、部署锁和恢复流程。
CANDIDATE_SHA="$(git -C "$PROJECT_DIR" rev-parse HEAD)"
WONIUNOTE_PROJECT_DIR="$PROJECT_DIR" \
WONIUNOTE_STATE_DIR="$WONIUNOTE_STATE_DIR" \
WONIUNOTE_DATA_DIR="$WONIUNOTE_DATA_DIR" \
WONIUNOTE_RUNTIME_CONFIG="$WONIUNOTE_RUNTIME_CONFIG" \
WONIUNOTE_NGINX_CONFIG=/etc/nginx/nginx.conf \
WONIUNOTE_SSL_CERT="$SSL_CERT_DIR/fullchain.pem" \
WONIUNOTE_SSL_KEY="$SSL_CERT_DIR/privkey.pem" \
WONIUNOTE_COMPATIBILITY_RECORD="$WONIUNOTE_COMPATIBILITY_RECORD" \
WONIUNOTE_ROLLBACK_COMPATIBILITY_RECORD="$WONIUNOTE_ROLLBACK_COMPATIBILITY_RECORD" \
WONIUNOTE_SMOKE_HOST="$WONIUNOTE_SMOKE_HOST" \
WONIUNOTE_SMOKE_SCHEME="$WONIUNOTE_SMOKE_SCHEME" \
WONIUNOTE_SMOKE_PORT="$WONIUNOTE_SMOKE_PORT" \
WONIUNOTE_SMOKE_READONLY_API="$WONIUNOTE_SMOKE_READONLY_API" \
WONIUNOTE_SMOKE_THUMB_PATH="$WONIUNOTE_SMOKE_THUMB_PATH" \
WONIUNOTE_SMOKE_UPLOAD_PATH="$WONIUNOTE_SMOKE_UPLOAD_PATH" \
WONIUNOTE_SMOKE_UPLOAD_FILE="$WONIUNOTE_SMOKE_UPLOAD_FILE" \
WONIUNOTE_SMOKE_UPLOAD_SHA256="$WONIUNOTE_SMOKE_UPLOAD_SHA256" \
    bash "$DEPLOY_DIR/scripts/deploy_release.sh" deploy --sha "$CANDIDATE_SHA"
WONIUNOTE_PROJECT_DIR="$PROJECT_DIR" \
WONIUNOTE_STATE_DIR="$WONIUNOTE_STATE_DIR" \
    bash "$DEPLOY_DIR/scripts/deploy_release.sh" run-locked timeout 5s systemctl enable woniunote

# 检查服务状态
echo ""
echo "========================================"
echo "  服务状态检查"
echo "========================================"

echo -n "后端服务: "
if systemctl is-active --quiet woniunote; then
    echo -e "${GREEN}运行中${NC}"
else
    echo -e "${RED}未运行${NC}"
fi

echo -n "Nginx: "
if systemctl is-active --quiet nginx; then
    echo -e "${GREEN}运行中${NC}"
else
    echo -e "${RED}未运行${NC}"
fi

echo -n "MySQL: "
if systemctl is-active --quiet mysql; then
    echo -e "${GREEN}运行中${NC}"
else
    echo -e "${RED}未运行${NC}"
fi

echo -n "Redis: "
if systemctl is-active --quiet redis-server; then
    echo -e "${GREEN}运行中${NC}"
else
    echo -e "${RED}未运行${NC}"
fi

echo ""
echo "========================================"
echo "  部署完成!"  
echo "========================================"
echo ""
echo "访问地址:"
echo "  HTTP:  http://your-domain.com"
echo "  HTTPS: https://your-domain.com (如已配置SSL证书)"
echo ""
echo "管理命令:"
echo "  sudo bash $DEPLOY_DIR/scripts/prod_manage.sh start    # 启动"
echo "  sudo bash $DEPLOY_DIR/scripts/prod_manage.sh stop     # 停止"
echo "  sudo bash $DEPLOY_DIR/scripts/prod_manage.sh restart  # 重启"
echo "  sudo bash $DEPLOY_DIR/scripts/prod_manage.sh status   # 状态"
echo "  sudo bash $DEPLOY_DIR/scripts/prod_manage.sh logs backend  # 日志"
echo ""
echo "日志位置:"
echo "  后端日志: $DEPLOY_DIR/logs/backend.log"
echo "  Nginx日志: /var/log/nginx/woniunote_access.log"
echo ""
echo "========================================"
